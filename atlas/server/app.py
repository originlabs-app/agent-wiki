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
)

if TYPE_CHECKING:
    from atlas.server.deps import EngineSet, EventBus


def create_app(
    engines: EngineSet | None = None,
    event_bus: EventBus | None = None,
    root: Path | str | None = None,
) -> FastAPI:
    """Create and configure the FastAPI app.

    Either pass pre-built `engines` + `event_bus` (for testing),
    or pass `root` to auto-create them.
    """
    from atlas.server.deps import create_engine_set, EventBus as _EventBus

    if engines is None:
        if root is None:
            root = Path.cwd()
        engines = create_engine_set(root)

    if event_bus is None:
        event_bus = _EventBus()

    app = FastAPI(
        title="Atlas — Knowledge Engine",
        version="2.0.0a1",
        description="REST API for Atlas: scan, query, wiki, audit, ingest.",
    )
    add_middleware(app)

    # Store engines on app state for access in routes
    app.state.engines = engines
    app.state.event_bus = event_bus

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

    # --- Query ---

    @app.post("/api/query", response_model=QueryResponse)
    def query(req: QueryRequest):
        subgraph = engines.graph.query(req.question, mode=req.mode, depth=req.depth)
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
    from atlas.server.deps import create_engine_set, EventBus
    from atlas.server.ws import WebSocketManager, mount_websocket

    root = Path(root).resolve()
    engines = create_engine_set(root)
    event_bus = EventBus()

    app = create_app(engines=engines, event_bus=event_bus)

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
