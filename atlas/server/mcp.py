"""MCP server — stdio for local, SSE for remote. 12 tools as per Atlas spec section 6."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from atlas.server.deps import EngineSet, EventBus

logger = logging.getLogger("atlas.server.mcp")


# --- Tool Definitions (MCP spec format) ---

TOOL_DEFINITIONS = [
    {
        "name": "atlas.scan",
        "description": "Scan a folder — extract nodes and edges from code, docs, images. Returns summary of what was found.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the folder to scan"},
                "incremental": {"type": "boolean", "description": "Only re-extract changed files", "default": False},
                "force": {"type": "boolean", "description": "Ignore cache, re-extract everything", "default": False},
            },
            "required": ["path"],
        },
    },
    {
        "name": "atlas.query",
        "description": "Query the knowledge graph via BFS or DFS traversal from a start node. Returns a subgraph of relevant nodes and edges.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Start node ID or concept name"},
                "mode": {"type": "string", "enum": ["bfs", "dfs"], "default": "bfs"},
                "depth": {"type": "integer", "description": "Max traversal depth", "default": 3},
            },
            "required": ["question"],
        },
    },
    {
        "name": "atlas.path",
        "description": "Find the shortest path between two concepts in the graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source node ID"},
                "target": {"type": "string", "description": "Target node ID"},
            },
            "required": ["source", "target"],
        },
    },
    {
        "name": "atlas.explain",
        "description": "Get a plain-English summary of a concept — its type, summary, and all direct neighbors.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "concept": {"type": "string", "description": "Node ID to explain"},
            },
            "required": ["concept"],
        },
    },
    {
        "name": "atlas.god_nodes",
        "description": "Return the top N most-connected concepts in the graph (highest degree).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "description": "Number of top nodes to return", "default": 10},
            },
        },
    },
    {
        "name": "atlas.stats",
        "description": "Return graph statistics — node count, edge count, communities, confidence breakdown, health score.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "atlas.ingest",
        "description": "Ingest a URL or local file into the raw/ store with auto-detected frontmatter.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch and ingest"},
                "file_path": {"type": "string", "description": "Local file path (relative to root) to ingest"},
                "title": {"type": "string", "description": "Optional title override"},
                "author": {"type": "string", "description": "Optional author"},
            },
        },
    },
    {
        "name": "atlas.wiki.read",
        "description": "Read a wiki page — returns title, content, frontmatter, and wikilinks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page": {"type": "string", "description": "Wiki page path (e.g., wiki/concepts/auth.md)"},
            },
            "required": ["page"],
        },
    },
    {
        "name": "atlas.wiki.write",
        "description": "Write or update a wiki page. Automatically syncs changes to the graph via the Linker.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page": {"type": "string", "description": "Wiki page path"},
                "content": {"type": "string", "description": "Markdown content (without frontmatter)"},
                "frontmatter": {
                    "type": "object",
                    "description": "YAML frontmatter fields (type, title, confidence, tags, etc.)",
                },
            },
            "required": ["page", "content"],
        },
    },
    {
        "name": "atlas.wiki.search",
        "description": "Full-text search across all wiki pages. Returns matching pages with content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "terms": {"type": "string", "description": "Search terms"},
            },
            "required": ["terms"],
        },
    },
    {
        "name": "atlas.audit",
        "description": "Run a full audit — orphan pages, god nodes, broken links, stale pages, contradictions, health score.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "atlas.suggest_links",
        "description": "Suggest missing wikilinks, new pages, and clarifications based on graph analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# --- Tool Handler ---

def handle_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    engines: EngineSet,
    event_bus: EventBus,
) -> dict[str, Any]:
    """Dispatch a tool call to the appropriate Core engine method.

    Returns a JSON-serializable dict. Same logic as REST routes but without HTTP.
    """
    try:
        if tool_name == "atlas.scan":
            return _handle_scan(arguments, engines, event_bus)
        elif tool_name == "atlas.query":
            return _handle_query(arguments, engines)
        elif tool_name == "atlas.path":
            return _handle_path(arguments, engines)
        elif tool_name == "atlas.explain":
            return _handle_explain(arguments, engines)
        elif tool_name == "atlas.god_nodes":
            return _handle_god_nodes(arguments, engines)
        elif tool_name == "atlas.stats":
            return _handle_stats(engines)
        elif tool_name == "atlas.ingest":
            return _handle_ingest(arguments, engines, event_bus)
        elif tool_name == "atlas.wiki.read":
            return _handle_wiki_read(arguments, engines)
        elif tool_name == "atlas.wiki.write":
            return _handle_wiki_write(arguments, engines, event_bus)
        elif tool_name == "atlas.wiki.search":
            return _handle_wiki_search(arguments, engines)
        elif tool_name == "atlas.audit":
            return _handle_audit(engines)
        elif tool_name == "atlas.suggest_links":
            return _handle_suggest_links(engines)
        else:
            return {"error": "unknown_tool", "detail": f"Tool '{tool_name}' not found"}
    except Exception as e:
        logger.exception("Error handling tool call %s", tool_name)
        return {"error": "tool_error", "detail": str(e)}


def _handle_scan(args: dict, engines: EngineSet, event_bus: EventBus) -> dict:
    scan_path = Path(args["path"])
    incremental = args.get("incremental", False)
    try:
        extraction = engines.scanner.scan(scan_path, incremental=incremental)
    except (ValueError, OSError):
        return {"nodes_found": 0, "edges_found": 0, "message": "Scan complete"}

    if extraction.nodes:
        engines.graph.merge(extraction)
        engines.linker.sync_wiki_to_graph()
        engines.save_graph()
        event_bus.emit("scan.completed", {"event": "scan.completed", "nodes": len(extraction.nodes)})
        event_bus.emit("graph.updated", {"event": "graph.updated"})

    return {
        "nodes_found": len(extraction.nodes),
        "edges_found": len(extraction.edges),
        "message": "Scan complete",
    }


def _handle_query(args: dict, engines: EngineSet) -> dict:
    subgraph = engines.graph.query(
        args["question"],
        mode=args.get("mode", "bfs"),
        depth=args.get("depth", 3),
    )
    return {
        "nodes": [_node_to_dict(n) for n in subgraph.nodes],
        "edges": [_edge_to_dict(e) for e in subgraph.edges],
        "estimated_tokens": subgraph.estimated_tokens,
    }


def _handle_path(args: dict, engines: EngineSet) -> dict:
    edges = engines.graph.path(args["source"], args["target"])
    if edges is None:
        return {"edges": [], "found": False}
    return {"edges": [_edge_to_dict(e) for e in edges], "found": True}


def _handle_explain(args: dict, engines: EngineSet) -> dict:
    node = engines.graph.get_node(args["concept"])
    if node is None:
        return {"error": "not_found", "detail": f"Concept '{args['concept']}' not found"}

    neighbors_raw = engines.graph.get_neighbors(args["concept"])
    return {
        "concept": args["concept"],
        "label": node.label,
        "type": node.type,
        "summary": node.summary,
        "neighbors": [_node_to_dict(n) for n, _ in neighbors_raw],
        "edges": [_edge_to_dict(e) for _, e in neighbors_raw],
    }


def _handle_god_nodes(args: dict, engines: EngineSet) -> dict:
    top_n = args.get("top_n", 10)
    gods = engines.analyzer.god_nodes(top_n=top_n)
    result = []
    for node_id, degree in gods:
        node = engines.graph.get_node(node_id)
        label = node.label if node else node_id
        result.append({"id": node_id, "label": label, "degree": degree})
    return {"nodes": result}


def _handle_stats(engines: EngineSet) -> dict:
    s = engines.graph.stats()
    return {
        "nodes": s.nodes,
        "edges": s.edges,
        "communities": s.communities,
        "confidence_breakdown": s.confidence_breakdown,
        "health_score": s.health_score,
    }


def _handle_ingest(args: dict, engines: EngineSet, event_bus: EventBus) -> dict:
    if args.get("url"):
        # URL ingestion requires async — run in sync context
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        path = loop.run_until_complete(
            engines.ingest.ingest_url(args["url"], title=args.get("title"), author=args.get("author"))
        )
    elif args.get("file_path"):
        path = engines.ingest.ingest_file(args["file_path"], title=args.get("title"))
    else:
        return {"error": "validation_error", "detail": "Either 'url' or 'file_path' required"}

    if path:
        event_bus.emit("wiki.changed", {"event": "wiki.changed", "page": path, "action": "ingest"})

    return {"path": path, "message": "Ingested" if path else "Ingestion failed"}


def _handle_wiki_read(args: dict, engines: EngineSet) -> dict | None:
    page = engines.wiki.read(args["page"])
    if page is None:
        return {"error": "not_found", "detail": f"Page '{args['page']}' not found"}
    return {
        "path": page.path,
        "title": page.title,
        "type": page.type,
        "content": page.content,
        "frontmatter": page.frontmatter,
        "wikilinks": page.wikilinks,
    }


def _handle_wiki_write(args: dict, engines: EngineSet, event_bus: EventBus) -> dict:
    engines.wiki.write(args["page"], args["content"], frontmatter=args.get("frontmatter"))
    changes = engines.linker.sync_wiki_to_graph()
    if changes:
        engines.save_graph()
    event_bus.emit("wiki.changed", {"event": "wiki.changed", "page": args["page"], "action": "write"})
    event_bus.emit("graph.updated", {"event": "graph.updated", "changes": len(changes)})
    return {"page": args["page"], "message": "Page saved"}


def _handle_wiki_search(args: dict, engines: EngineSet) -> dict:
    results = engines.wiki.search(args["terms"])
    return {
        "results": [
            {"path": p.path, "title": p.title, "type": p.type, "slug": p.slug}
            for p in results
        ],
    }


def _handle_audit(engines: EngineSet) -> dict:
    report = engines.analyzer.audit()
    stats = None
    if report.stats:
        stats = {
            "nodes": report.stats.nodes,
            "edges": report.stats.edges,
            "communities": report.stats.communities,
            "confidence_breakdown": report.stats.confidence_breakdown,
            "health_score": report.stats.health_score,
        }
    return {
        "orphan_pages": report.orphan_pages,
        "god_nodes": [{"id": nid, "degree": deg} for nid, deg in report.god_nodes],
        "broken_links": [{"page": p, "link": l} for p, l in report.broken_links],
        "stale_pages": report.stale_pages,
        "contradictions": report.contradictions,
        "missing_links": [
            {"from_page": s.from_page, "to_page": s.to_page, "reason": s.reason, "confidence": s.confidence}
            for s in report.missing_links
        ],
        "communities": report.communities,
        "stats": stats,
        "health_score": report.health_score,
    }


def _handle_suggest_links(engines: EngineSet) -> dict:
    suggestions = engines.linker.sync_graph_to_wiki()
    return {
        "suggestions": [
            {
                "type": s.type,
                "description": s.description,
                "target_page": s.target_page,
                "source_node": s.source_node,
                "target_node": s.target_node,
                "reason": s.reason,
            }
            for s in suggestions
        ],
    }


# --- Serialization helpers ---

def _node_to_dict(node) -> dict:
    return {
        "id": node.id,
        "label": node.label,
        "type": node.type,
        "source_file": node.source_file,
        "confidence": node.confidence,
        "community": node.community,
        "summary": node.summary,
        "tags": node.tags or [],
    }


def _edge_to_dict(edge) -> dict:
    return {
        "source": edge.source,
        "target": edge.target,
        "relation": edge.relation,
        "confidence": edge.confidence,
        "confidence_score": edge.confidence_score,
    }


# --- MCP Server Factory ---

def create_mcp_server(engines: EngineSet, event_bus: EventBus):
    """Create an MCP server instance with all 12 Atlas tools registered.

    Uses the `mcp` pip package. Supports stdio (local) and SSE (remote) transport.
    """
    try:
        from mcp.server import Server
        from mcp.types import Tool, TextContent
    except ImportError:
        raise ImportError(
            "MCP server requires the 'mcp' package. Install with: pip install mcp"
        )

    server = Server("atlas")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in TOOL_DEFINITIONS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        result = handle_tool_call(name, arguments or {}, engines=engines, event_bus=event_bus)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    return server
