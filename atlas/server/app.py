"""FastAPI application — REST API for all Atlas operations."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from atlas.server.middleware import add_middleware, AtlasNotFoundError, AtlasValidationError

DASHBOARD_DIR = Path(__file__).parent.parent / "dashboard"
from atlas.server.schemas import (
    AuditResponse,
    ErrorResponse,
    ExplainRequest,
    ExplainResponse,
    GodNodesRequest,
    GodNodesResponse,
    IngestRequest,
    IngestResponse,
    NodeSchema,
    EdgeSchema,
    PageSchema,
    PathRequest,
    PathResponse,
    QueryRequest,
    QueryResponse,
    ScanRequest,
    ScanResponse,
    StatsResponse,
    GraphStatsSchema,
    SuggestLinksResponse,
    SurprisesRequest,
    SurprisesResponse,
    WikiReadRequest,
    WikiReadResponse,
    WikiSearchRequest,
    WikiSearchResponse,
    WikiSuggestionSchema,
    WikiWriteRequest,
    WikiWriteResponse,
    LinkSuggestionSchema,
    FileTreeNode,
    CommunitySchema,
    FileReadResponse,
    ProjectEntrySchema,
    ProjectOpenRequest,
    ProjectSwitchRequest,
)

if TYPE_CHECKING:
    from atlas.server.deps import EngineSet, EventBus


def create_app(
    engines: EngineSet | None = None,
    event_bus: EventBus | None = None,
    root: Path | str | None = None,
    registry: "ProjectRegistry | None" = None,
    scan_status: "ScanStatus | None" = None,
) -> FastAPI:
    """Create and configure the FastAPI app.

    Either pass pre-built `engines` + `event_bus` (for testing),
    or pass `root` to auto-create them.
    """
    from atlas.core.registry import ProjectRegistry
    from atlas.server.deps import create_engine_set, EventBus, ScanStatus as _ScanStatus

    if engines is None:
        if root is None:
            root = Path.cwd()
        engines = create_engine_set(root)

    if event_bus is None:
        event_bus = EventBus()

    if registry is None:
        registry = ProjectRegistry()
    if scan_status is None:
        scan_status = _ScanStatus()

    app = FastAPI(
        title="Atlas — Knowledge Engine",
        version="2.0.0a1",
        description="REST API for Atlas: scan, query, wiki, audit, ingest.",
    )
    add_middleware(app)

    # Store engines on app state for access in routes
    app.state.engines = engines
    app.state.event_bus = event_bus
    app.state.registry = registry
    app.state.scan_status = scan_status

    # --- Health ---

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "2.0.0a1"}

    # --- Scan ---

    @app.post("/api/scan", response_model=ScanResponse)
    def scan(req: ScanRequest):
        scan_path = Path(req.path)
        try:
            extraction = engines.scanner.scan(scan_path, incremental=req.incremental)
        except (ValueError, OSError):
            # Path traversal blocked or invalid path
            return ScanResponse(nodes_found=0, edges_found=0, message="Scan complete")

        if extraction.nodes:
            engines.graph.merge(extraction)
            changes = engines.linker.sync_wiki_to_graph()
            engines.save_graph()

            event_bus.emit("scan.completed", {
                "event": "scan.completed",
                "path": req.path,
                "nodes": len(extraction.nodes),
                "edges": len(extraction.edges),
            })
            event_bus.emit("graph.updated", {
                "event": "graph.updated",
                "changes": len(changes),
            })

        return ScanResponse(
            nodes_found=len(extraction.nodes),
            edges_found=len(extraction.edges),
        )

    # --- Stats ---

    @app.get("/api/stats", response_model=StatsResponse)
    def stats():
        s = engines.graph.stats()
        return StatsResponse(stats=GraphStatsSchema(
            nodes=s.nodes,
            edges=s.edges,
            communities=s.communities,
            confidence_breakdown=s.confidence_breakdown,
            health_score=s.health_score,
        ))

    # --- Graph (full dump for dashboard) ---

    @app.get("/api/graph")
    def get_graph():
        """Return all nodes and edges for the dashboard visualization."""
        all_nodes = [NodeSchema.from_core(engines.graph.get_node(nid)) for nid in engines.graph.iter_node_ids()]
        all_edges = []
        for u, v in engines.graph.iter_edges(data=False):
            d = engines.graph.get_edge_data(u, v)
            all_edges.append(EdgeSchema(source=u, target=v, type=d.get("type", "calls"), confidence=d.get("confidence", "INFERRED"), relation=d.get("type", "calls"), weight=d.get("weight", 1.0)))
        return {"nodes": all_nodes, "edges": all_edges}

    # --- Query ---

    @app.post("/api/query", response_model=QueryResponse)
    @app.post("/api/graph/query", response_model=QueryResponse, include_in_schema=False)
    def query(req: QueryRequest):
        subgraph = engines.graph.query(req.effective_question, mode=req.mode, depth=req.depth)
        return QueryResponse(
            nodes=[NodeSchema.from_core(n) for n in subgraph.nodes],
            edges=[EdgeSchema.from_core(e) for e in subgraph.edges],
            estimated_tokens=subgraph.estimated_tokens,
        )

    # --- Path ---

    @app.post("/api/path", response_model=PathResponse)
    def path(req: PathRequest):
        edges = engines.graph.path(req.source, req.target)
        if edges is None:
            return PathResponse(edges=[], found=False)
        return PathResponse(
            edges=[EdgeSchema.from_core(e) for e in edges],
            found=True,
        )

    # --- Explain ---

    @app.post("/api/explain", response_model=ExplainResponse)
    def explain(req: ExplainRequest):
        node = engines.graph.get_node(req.concept)
        if node is None:
            raise AtlasNotFoundError(f"Concept '{req.concept}' not found in the graph")

        neighbors_raw = engines.graph.get_neighbors(req.concept)
        neighbor_nodes = [NodeSchema.from_core(n) for n, _ in neighbors_raw]
        neighbor_edges = [EdgeSchema.from_core(e) for _, e in neighbors_raw]

        return ExplainResponse(
            concept=req.concept,
            label=node.label,
            type=node.type,
            summary=node.summary,
            neighbors=neighbor_nodes,
            edges=neighbor_edges,
        )

    # --- God Nodes ---

    @app.post("/api/god-nodes", response_model=GodNodesResponse)
    def god_nodes(req: GodNodesRequest):
        gods = engines.analyzer.god_nodes(top_n=req.top_n)
        result = []
        for node_id, degree in gods:
            node = engines.graph.get_node(node_id)
            label = node.label if node else node_id
            result.append({"id": node_id, "label": label, "degree": degree})
        return GodNodesResponse(nodes=result)

    # --- Surprises ---

    @app.post("/api/surprises", response_model=SurprisesResponse)
    def surprises(req: SurprisesRequest):
        edges = engines.analyzer.surprises(top_n=req.top_n)
        return SurprisesResponse(edges=[EdgeSchema.from_core(e) for e in edges])

    # --- Wiki CRUD ---

    @app.post("/api/wiki/read", response_model=WikiReadResponse)
    def wiki_read(req: WikiReadRequest):
        page = engines.wiki.read(req.page)
        if page is None:
            return WikiReadResponse(page=None)
        return WikiReadResponse(page=PageSchema.from_core(page))

    @app.post("/api/wiki/write", response_model=WikiWriteResponse)
    def wiki_write(req: WikiWriteRequest):
        engines.wiki.write(req.page, req.content, frontmatter=req.frontmatter or None)

        # Sync changes to graph
        changes = engines.linker.sync_wiki_to_graph()
        if changes:
            engines.save_graph()

        event_bus.emit("wiki.changed", {
            "event": "wiki.changed",
            "page": req.page,
            "action": "write",
        })
        event_bus.emit("graph.updated", {
            "event": "graph.updated",
            "changes": len(changes),
        })

        return WikiWriteResponse(page=req.page)

    @app.post("/api/wiki/search", response_model=WikiSearchResponse)
    def wiki_search(req: WikiSearchRequest):
        results = engines.wiki.search(req.terms)
        return WikiSearchResponse(results=[PageSchema.from_core(p) for p in results])

    @app.get("/api/wiki/search")
    def wiki_search_get(q: str = ""):
        """GET variant for dashboard — searches wiki pages by query string.
        Returns array directly (dashboard expects raw array, not {results: []})."""
        if not q:
            return []
        results = engines.wiki.search(q)
        return [PageSchema.from_core(p).model_dump() for p in results]

    @app.get("/api/wiki/pages")
    def wiki_pages(type: str | None = None):
        """List all wiki pages, optionally filtered by type. Returns array directly."""
        pages = engines.wiki.list_pages(type=type)
        return [PageSchema.from_core(p).model_dump() for p in pages]

    @app.get("/api/log")
    def get_log(limit: int = 50, offset: int = 0):
        """Read the wiki operation log. Returns array directly for dashboard compatibility."""
        log_content = engines.storage.read("wiki/log.md")
        if log_content is None:
            return []
        # Parse log entries (format: [YYYY-MM-DD] agent | op | description)
        import re
        entries = []
        for line in log_content.splitlines():
            m = re.match(r"\[(\d{4}-\d{2}-\d{2})\]\s+(\S+)\s+\|\s+(\S+)\s+\|\s+(.*)", line)
            if m:
                entries.append({
                    "date": m.group(1),
                    "agent": m.group(2),
                    "operation": m.group(3),
                    "description": m.group(4).strip(),
                })
        entries.reverse()  # newest first
        return entries[offset:offset + limit]

    # --- Audit ---

    @app.get("/api/audit", response_model=AuditResponse)
    def audit():
        report = engines.analyzer.audit()
        stats_schema = None
        if report.stats:
            stats_schema = GraphStatsSchema(
                nodes=report.stats.nodes,
                edges=report.stats.edges,
                communities=report.stats.communities,
                confidence_breakdown=report.stats.confidence_breakdown,
                health_score=report.stats.health_score,
            )
        return AuditResponse(
            orphan_pages=report.orphan_pages,
            god_nodes=[{"id": nid, "degree": deg} for nid, deg in report.god_nodes],
            broken_links=[{"page": p, "link": l} for p, l in report.broken_links],
            stale_pages=report.stale_pages,
            contradictions=report.contradictions,
            missing_links=[
                LinkSuggestionSchema(
                    from_page=s.from_page,
                    to_page=s.to_page,
                    reason=s.reason,
                    confidence=s.confidence,
                )
                for s in report.missing_links
            ],
            communities=report.communities,
            stats=stats_schema,
            health_score=report.health_score,
        )

    # --- Explorer: Files ---

    @app.get("/api/files", response_model=list[FileTreeNode])
    def get_files():
        """Return the scanned file tree with degree counts.

        Builds a hierarchical tree from all graph nodes that have a source_file.
        Each file node includes its degree (connection count) from the graph.
        """
        # Collect all unique source files from graph nodes
        file_set: dict[str, dict] = {}  # path -> {type, degree}
        for nid in engines.graph.iter_node_ids():
            data = engines.graph.get_node_data(nid)
            sf = data.get("source_file", "")
            if not sf:
                continue
            node_type = data.get("type", "unknown")
            degree = engines.graph.degree(nid)
            # Keep highest degree if multiple nodes map to same file
            if sf not in file_set or degree > file_set[sf]["degree"]:
                file_set[sf] = {"type": node_type, "degree": degree}

        # Build tree structure
        tree: dict = {}  # nested dict: {name: {__children__: {...}, __meta__: ...}}
        for path, meta in sorted(file_set.items()):
            parts = path.split("/")
            current = tree
            for i, part in enumerate(parts):
                if part not in current:
                    current[part] = {"__children__": {}, "__meta__": None}
                if i == len(parts) - 1:
                    # Leaf file
                    current[part]["__meta__"] = {
                        "path": path,
                        "type": meta["type"],
                        "degree": meta["degree"],
                    }
                current = current[part]["__children__"]

        def to_tree_nodes(subtree: dict, prefix: str = "") -> list[dict]:
            nodes = []
            for name, entry in sorted(subtree.items()):
                full_path = f"{prefix}{name}" if not prefix else f"{prefix}/{name}"
                meta = entry["__meta__"]
                children_dict = entry["__children__"]

                if children_dict:
                    # Directory
                    children = to_tree_nodes(children_dict, full_path)
                    # Sum degrees of all children for the directory
                    total_degree = sum(c.get("degree", 0) for c in children)
                    nodes.append({
                        "path": full_path,
                        "name": name,
                        "type": "directory",
                        "degree": total_degree,
                        "children": children,
                    })
                elif meta:
                    # File
                    nodes.append({
                        "path": meta["path"],
                        "name": name,
                        "type": meta["type"],
                        "degree": meta["degree"],
                        "children": None,
                    })
            return nodes

        return to_tree_nodes(tree)

    # --- Explorer: Communities ---

    @app.get("/api/communities", response_model=list[CommunitySchema])
    def get_communities():
        """Return detected communities with labels, sizes, cohesion scores.

        Groups nodes by their `community` attribute, computes internal edge
        density (cohesion), and labels each community by its highest-degree
        member node's label.
        """
        # Group nodes by community
        communities: dict[int, list[str]] = {}
        for nid in engines.graph.iter_node_ids():
            data = engines.graph.get_node_data(nid)
            comm = data.get("community")
            if comm is not None:
                communities.setdefault(comm, []).append(nid)

        result = []
        for comm_id, members in sorted(communities.items()):
            member_set = set(members)
            # Count internal edges
            internal_edges = 0
            for u, v in engines.graph.iter_edges(data=False):
                if u in member_set and v in member_set:
                    internal_edges += 1

            # Cohesion = internal edges / max possible edges
            n = len(members)
            max_edges = n * (n - 1) if n > 1 else 1
            cohesion = round(internal_edges / max_edges, 2) if max_edges > 0 else 0.0

            # Label = highest-degree member's label
            best_member = max(members, key=lambda m: engines.graph.degree(m))
            best_data = engines.graph.get_node_data(best_member)
            label = best_data.get("label", best_member)

            # Enrich members with type and source_file for routing
            enriched_members = []
            for mid in members:
                mdata = engines.graph.get_node_data(mid)
                enriched_members.append({
                    "id": mid,
                    "label": mdata.get("label", mid),
                    "type": mdata.get("type", "unknown"),
                    "source_file": mdata.get("source_file", ""),
                    "degree": engines.graph.degree(mid),
                })

            result.append(CommunitySchema(
                id=comm_id,
                label=label,
                size=n,
                cohesion=cohesion,
                members=enriched_members,
            ))

        # Sort by size descending
        result.sort(key=lambda c: -c.size)
        return result

    # --- Explorer: File Read ---

    @app.get("/api/file/read", response_model=FileReadResponse)
    def read_file(path: str):
        """Read raw content of a scanned file (non-wiki files).

        Only serves files that exist as nodes in the graph (i.e., were scanned).
        Blocks hidden files (.env, .git, etc.) and path traversal.
        """
        # Block hidden files
        if any(part.startswith(".") for part in path.split("/")):
            raise AtlasValidationError(f"Access denied: {path}")

        # Only serve files that are in the graph (were scanned)
        scanned_files = {data.get("source_file", "") for _, data in engines.graph._g.nodes(data=True)}
        if path not in scanned_files and not path.startswith("wiki/"):
            raise AtlasNotFoundError(f"File not scanned: {path}")

        try:
            content = engines.storage.read(path)
        except ValueError:
            # Path traversal blocked
            raise AtlasValidationError(f"Invalid path: {path}")

        if content is None:
            raise AtlasNotFoundError(f"File not found: {path}")

        # Guess type from extension
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        type_map = {
            "py": "code", "js": "code", "ts": "code", "rs": "code",
            "go": "code", "java": "code", "rb": "code", "c": "code",
            "cpp": "code", "h": "code", "sh": "code", "yaml": "code",
            "yml": "code", "toml": "code", "json": "code",
            "md": "document", "txt": "document", "rst": "document",
            "pdf": "paper", "png": "image", "jpg": "image",
            "jpeg": "image", "gif": "image", "svg": "image",
        }
        file_type = type_map.get(ext, "unknown")

        return FileReadResponse(path=path, content=content, type=file_type)

    # --- Suggest Links ---

    @app.get("/api/suggest-links", response_model=SuggestLinksResponse)
    def suggest_links():
        suggestions = engines.linker.sync_graph_to_wiki()
        return SuggestLinksResponse(suggestions=[
            WikiSuggestionSchema(
                type=s.type,
                description=s.description,
                target_page=s.target_page,
                source_node=s.source_node,
                target_node=s.target_node,
                reason=s.reason,
            )
            for s in suggestions
        ])

    # --- Ingest ---

    @app.post("/api/ingest", response_model=IngestResponse)
    async def ingest(req: IngestRequest):
        if req.url:
            path = await engines.ingest.ingest_url(req.url, title=req.title, author=req.author)
        elif req.file_path:
            path = engines.ingest.ingest_file(req.file_path, title=req.title)
        else:
            raise AtlasValidationError("Either 'url' or 'file_path' must be provided")

        if path:
            event_bus.emit("wiki.changed", {
                "event": "wiki.changed",
                "page": path,
                "action": "ingest",
            })

        return IngestResponse(path=path)

    # --- Project Management ---

    @app.get("/api/projects")
    def list_projects():
        projects = app.state.registry.list()
        return {
            "projects": [
                ProjectEntrySchema.from_registry(p).model_dump()
                for p in projects
            ]
        }

    @app.post("/api/projects/open")
    def open_project(req: ProjectOpenRequest):
        path = Path(req.path).resolve()
        if not path.is_dir():
            raise AtlasValidationError(f"Path is not a directory: {req.path}")

        registry = app.state.registry
        scan_status = app.state.scan_status
        engines = app.state.engines

        # Register (or update) the project
        entry = registry.register(str(path))

        # Check if scan is needed
        scanned = False
        if registry.needs_rescan(str(path)):
            scan_status.start(f"Scanning {entry.name}")
            try:
                # Rebuild engines for the new project
                new_engines = create_engine_set(path)
                extraction = new_engines.scanner.scan(path, incremental=False)
                if extraction.nodes:
                    new_engines.graph.merge(extraction)
                    new_engines.linker.sync_wiki_to_graph()
                    new_engines.save_graph()

                # Update stats in registry
                stats = new_engines.graph.stats()
                registry.update_stats(
                    str(path),
                    nodes=stats.nodes,
                    edges=stats.edges,
                    communities=stats.communities,
                    health=stats.health_score,
                )
                entry = registry.get(str(path))

                # Replace active engines
                engines.graph = new_engines.graph
                engines.scanner = new_engines.scanner
                engines.linker = new_engines.linker
                engines.analyzer = new_engines.analyzer
                engines.wiki = new_engines.wiki
                engines.storage = new_engines.storage
                engines.cache = new_engines.cache
                engines.ingest = new_engines.ingest
                engines.root = new_engines.root
                app.state.engines = engines
                scanned = True
            finally:
                scan_status.finish()

            event_bus.emit("scan.completed", {
                "event": "scan.completed",
                "path": str(path),
                "nodes": entry.nodes,
                "edges": entry.edges,
            })
        else:
            # Load existing graph without rescan
            new_engines = create_engine_set(path)
            new_engines.load_graph()
            new_engines.linker.sync_wiki_to_graph()
            stats = new_engines.graph.stats()
            registry.update_stats(
                str(path),
                nodes=stats.nodes,
                edges=stats.edges,
                communities=stats.communities,
                health=stats.health_score,
            )
            entry = registry.get(str(path))
            engines.graph = new_engines.graph
            engines.scanner = new_engines.scanner
            engines.linker = new_engines.linker
            engines.analyzer = new_engines.analyzer
            engines.wiki = new_engines.wiki
            engines.storage = new_engines.storage
            engines.cache = new_engines.cache
            engines.ingest = new_engines.ingest
            engines.root = new_engines.root
            app.state.engines = engines

        event_bus.emit("project.switched", {
            "event": "project.switched",
            "path": str(path),
            "name": entry.name,
            "nodes": entry.nodes,
            "edges": entry.edges,
            "communities": entry.communities,
        })

        return {
            "project": ProjectEntrySchema.from_registry(entry).model_dump(),
            "scanned": scanned,
        }

    @app.post("/api/projects/switch")
    def switch_project(req: ProjectSwitchRequest):
        path = Path(req.path).resolve()
        if not path.is_dir():
            raise AtlasValidationError(f"Path is not a directory: {req.path}")

        registry = app.state.registry
        scan_status = app.state.scan_status
        engines = app.state.engines
        event_bus = app.state.event_bus

        entry = registry.get(str(path))
        if entry is None:
            # Auto-register on switch
            entry = registry.register(str(path))

        # Rebuild engines
        new_engines = create_engine_set(path)

        # Load graph or scan if needed
        if registry.needs_rescan(str(path)):
            scan_status.start(f"Scanning {entry.name}")
            try:
                extraction = new_engines.scanner.scan(path, incremental=True)
                if extraction.nodes:
                    new_engines.graph.merge(extraction)
                    new_engines.linker.sync_wiki_to_graph()
                    new_engines.save_graph()
            finally:
                scan_status.finish()
        else:
            new_engines.load_graph()
            new_engines.linker.sync_wiki_to_graph()

        # Update stats
        stats = new_engines.graph.stats()
        registry.update_stats(
            str(path),
            nodes=stats.nodes,
            edges=stats.edges,
            communities=stats.communities,
            health=stats.health_score,
        )
        entry = registry.get(str(path))

        # Swap engines
        engines.graph = new_engines.graph
        engines.scanner = new_engines.scanner
        engines.linker = new_engines.linker
        engines.analyzer = new_engines.analyzer
        engines.wiki = new_engines.wiki
        engines.storage = new_engines.storage
        engines.cache = new_engines.cache
        engines.ingest = new_engines.ingest
        engines.root = new_engines.root
        app.state.engines = engines

        event_bus.emit("project.switched", {
            "event": "project.switched",
            "path": str(path),
            "name": entry.name,
            "nodes": entry.nodes,
            "edges": entry.edges,
            "communities": entry.communities,
        })

        return {"project": ProjectEntrySchema.from_registry(entry).model_dump()}

    @app.delete("/api/projects/{path:path}")
    def remove_project(path: str):
        import urllib.parse
        decoded = urllib.parse.unquote(path)
        registry = app.state.registry
        removed = registry.remove(decoded)
        return {"removed": removed}

    @app.get("/api/scan/status")
    def get_scan_status():
        return app.state.scan_status.to_dict()

    # --- Lifecycle ---

    @app.on_event("startup")
    async def startup():
        """Load graph from disk on server startup."""
        engines.load_graph()
        # Sync wiki state to graph to catch any changes made while server was down
        engines.linker.sync_wiki_to_graph()

    # --- Dashboard serving ---
    if DASHBOARD_DIR.is_dir():
        app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR), name="dashboard")

        @app.get("/")
        async def root():
            return FileResponse(DASHBOARD_DIR / "index.html")

    return app


def run_server(
    root: Path | str = ".",
    host: str = "127.0.0.1",
    port: int = 7100,
    reload: bool = False,
) -> None:
    """Start the Atlas server — REST API + WebSocket + optional MCP.

    This is the entry point for `atlas serve`.
    """
    import uvicorn
    from atlas.core.registry import ProjectRegistry
    from atlas.server.deps import create_engine_set, EventBus, ScanStatus
    from atlas.server.ws import WebSocketManager, mount_websocket

    root = Path(root).resolve()
    engines = create_engine_set(root)
    event_bus = EventBus()
    registry = ProjectRegistry()
    scan_status = ScanStatus()

    # Register the current project
    registry.register(str(root))

    app = create_app(
        engines=engines,
        event_bus=event_bus,
        registry=registry,
        scan_status=scan_status,
    )

    # Mount WebSocket
    ws_manager = WebSocketManager()
    mount_websocket(app, ws_manager, event_bus)

    print(f"Atlas server starting on http://{host}:{port}")
    print(f"  Root: {root}")
    print(f"  Graph: {engines.graph_path}")
    print(f"  Wiki pages: {len(engines.wiki.list_pages())}")
    print(f"  WebSocket: ws://{host}:{port}/ws")

    uvicorn.run(app, host=host, port=port, log_level="info")


def run_mcp(
    root: Path | str = ".",
    transport: str = "stdio",
    host: str = "0.0.0.0",
    port: int = 7200,
) -> None:
    """Start the Atlas MCP server.

    transport: "stdio" for local (Claude Code, Codex), "sse" for remote (ARA).
    """
    from atlas.server.deps import create_engine_set, EventBus
    from atlas.server.mcp import create_mcp_server

    root = Path(root).resolve()
    engines = create_engine_set(root)
    event_bus = EventBus()
    engines.load_graph()
    engines.linker.sync_wiki_to_graph()

    server = create_mcp_server(engines=engines, event_bus=event_bus)

    if transport == "stdio":
        print("Atlas MCP server (stdio) starting...")
        import asyncio
        asyncio.run(server.run_stdio())
    elif transport == "sse":
        print(f"Atlas MCP server (SSE) starting on http://{host}:{port}")
        import asyncio
        asyncio.run(server.run_sse(host=host, port=port))
    else:
        raise ValueError(f"Unknown transport: {transport}. Use 'stdio' or 'sse'.")
