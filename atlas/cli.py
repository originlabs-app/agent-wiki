"""Atlas CLI — knowledge engine for AI agents."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="atlas",
    help="Atlas — Scan anything. Know everything. Remember forever.",
    no_args_is_help=True,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_OUT = "atlas-out"


def _resolve_root(path: str) -> Path:
    """Resolve the target directory and validate it exists."""
    p = Path(path).resolve()
    if not p.exists():
        typer.echo(f"Error: path does not exist: {p}", err=True)
        raise typer.Exit(code=1)
    return p


def _out_dir(root: Path) -> Path:
    """Return the atlas-out directory for a given root, creating it if needed."""
    out = root / _DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)
    return out


def _load_graph(root: Path):
    """Load an existing graph.json or return a fresh GraphEngine."""
    from atlas.core.graph import GraphEngine

    graph_path = _out_dir(root) / "graph.json"
    if graph_path.exists():
        return GraphEngine.load(graph_path)
    return GraphEngine()


def _save_graph(graph, root: Path) -> Path:
    """Save graph to atlas-out/graph.json and return the path."""
    out = _out_dir(root)
    dest = out / "graph.json"
    graph.save(dest)
    return dest


# ---------------------------------------------------------------------------
# atlas scan
# ---------------------------------------------------------------------------

@app.command()
def scan(
    path: str = typer.Argument(..., help="Directory or file to scan."),
    update: bool = typer.Option(False, "--update", "-u", help="Incremental scan — only re-extract changed files."),
    force: bool = typer.Option(False, "--force", "-f", help="Force full re-extraction, ignore cache."),
) -> None:
    """Scan a directory, extract a knowledge graph, sync wiki."""
    from atlas.core.cache import CacheEngine
    from atlas.core.graph import GraphEngine
    from atlas.core.linker import Linker
    from atlas.core.scanner import Scanner
    from atlas.core.storage import LocalStorage
    from atlas.core.wiki import WikiEngine

    root = _resolve_root(path)
    out = _out_dir(root)

    storage = LocalStorage(root=root)
    cache = None if force else CacheEngine(storage)
    scanner = Scanner(storage=storage, cache=cache)

    incremental = update and not force
    typer.echo(f"Scanning {root} ({'incremental' if incremental else 'full'})...")

    extraction = scanner.scan(root, incremental=incremental)
    typer.echo(f"Extracted {len(extraction.nodes)} nodes, {len(extraction.edges)} edges.")

    # Build / update graph
    graph_path = out / "graph.json"
    if graph_path.exists() and incremental:
        graph = GraphEngine.load(graph_path)
    else:
        graph = GraphEngine()
    graph.merge(extraction)
    graph.save(graph_path)

    # Sync wiki if it exists
    wiki_dir = root / "wiki"
    if wiki_dir.is_dir():
        wiki = WikiEngine(storage)
        linker = Linker(wiki=wiki, graph=graph)
        changes = linker.sync_wiki_to_graph()
        suggestions = linker.sync_graph_to_wiki()
        graph.save(graph_path)
        typer.echo(f"Wiki sync: {len(changes)} graph changes, {len(suggestions)} suggestions.")

    stats = graph.stats()
    typer.echo(f"Graph: {stats.nodes} nodes, {stats.edges} edges, {stats.communities} communities.")
    typer.echo(f"Health score: {stats.health_score}")
    typer.echo(f"Saved to {graph_path}")


# ---------------------------------------------------------------------------
# atlas query
# ---------------------------------------------------------------------------

@app.command()
def query(
    question: str = typer.Argument(..., help="Start node ID or search term."),
    mode: str = typer.Option("bfs", "--mode", "-m", help="Traversal mode: bfs or dfs."),
    depth: int = typer.Option(3, "--depth", "-d", help="Max traversal depth."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Query the knowledge graph from a start node."""
    r = _resolve_root(root)
    graph = _load_graph(r)
    subgraph = graph.query(question, mode=mode, depth=depth)
    typer.echo(f"Query '{question}' ({mode}, depth={depth}): {len(subgraph.nodes)} nodes, {len(subgraph.edges)} edges")
    typer.echo(f"Estimated tokens: {subgraph.estimated_tokens}")
    for node in subgraph.nodes:
        typer.echo(f"  [{node.type}] {node.id}: {node.label}")


@app.command()
def path(
    source: str = typer.Argument(..., help="Source node ID."),
    target: str = typer.Argument(..., help="Target node ID."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Find the shortest path between two concepts."""
    r = _resolve_root(root)
    graph = _load_graph(r)
    edges = graph.path(source, target)
    if edges is None:
        typer.echo(f"No path found between '{source}' and '{target}'.")
        raise typer.Exit(code=1)
    typer.echo(f"Path from '{source}' to '{target}' ({len(edges)} hops):")
    for e in edges:
        typer.echo(f"  {e.source} --[{e.relation}]--> {e.target}")


@app.command()
def explain(
    concept: str = typer.Argument(..., help="Node ID to explain."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Explain a concept — its type, summary, and neighbors."""
    r = _resolve_root(root)
    graph = _load_graph(r)
    node = graph.get_node(concept)
    if node is None:
        typer.echo(f"Concept '{concept}' not found in the graph.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"{node.label} [{node.type}]")
    if node.summary:
        typer.echo(f"  {node.summary}")
    neighbors = graph.get_neighbors(concept)
    if neighbors:
        typer.echo(f"  {len(neighbors)} neighbors:")
        for n, e in neighbors:
            typer.echo(f"    {e.relation} → {n.label} [{n.type}]")


@app.command(name="god-nodes")
def god_nodes(
    top_n: int = typer.Option(10, "--top", "-n", help="Number of top nodes."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Show the most connected nodes in the graph."""
    from atlas.core.analyzer import Analyzer

    r = _resolve_root(root)
    graph = _load_graph(r)
    analyzer = Analyzer(graph=graph)
    gods = analyzer.god_nodes(top_n=top_n)
    typer.echo(f"Top {len(gods)} most connected nodes:")
    for node_id, degree in gods:
        node = graph.get_node(node_id)
        label = node.label if node else node_id
        typer.echo(f"  {label}: {degree} connections")


@app.command()
def surprises(
    top_n: int = typer.Option(10, "--top", "-n", help="Number of surprise edges."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Show the most surprising edges in the graph."""
    from atlas.core.analyzer import Analyzer

    r = _resolve_root(root)
    graph = _load_graph(r)
    analyzer = Analyzer(graph=graph)
    edges = analyzer.surprises(top_n=top_n)
    typer.echo(f"Top {len(edges)} surprise edges:")
    for e in edges:
        typer.echo(f"  {e.source} --[{e.relation}]--> {e.target} ({e.confidence})")


# ---------------------------------------------------------------------------
# atlas ingest
# ---------------------------------------------------------------------------

@app.command()
def ingest(
    source: str = typer.Argument(..., help="URL or local file path to ingest."),
    title: str = typer.Option(None, "--title", "-t", help="Optional title."),
    author: str = typer.Option(None, "--author", "-a", help="Optional author."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Ingest a URL or local file into the knowledge base."""
    import asyncio
    from atlas.core.ingest import IngestEngine, detect_url_type
    from atlas.core.storage import LocalStorage

    r = _resolve_root(root)
    storage = LocalStorage(root=r)
    engine = IngestEngine(storage)

    if source.startswith("http://") or source.startswith("https://"):
        url_type = detect_url_type(source)
        typer.echo(f"Ingesting URL ({url_type}): {source}")
        path = asyncio.run(engine.ingest_url(source, title=title, author=author))
    else:
        typer.echo(f"Ingesting file: {source}")
        path = engine.ingest_file(source, title=title)

    if path:
        typer.echo(f"Saved to: {path}")
    else:
        typer.echo("Ingestion failed.", err=True)
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# atlas audit
# ---------------------------------------------------------------------------

@app.command()
def audit(
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Run a full audit of the knowledge base."""
    from atlas.core.analyzer import Analyzer
    from atlas.core.storage import LocalStorage
    from atlas.core.wiki import WikiEngine

    r = _resolve_root(root)
    graph = _load_graph(r)
    storage = LocalStorage(root=r)
    wiki = WikiEngine(storage)
    analyzer = Analyzer(graph=graph, wiki=wiki)
    report = analyzer.audit()

    typer.echo(f"Health score: {report.health_score}")
    if report.stats:
        typer.echo(f"Graph: {report.stats.nodes} nodes, {report.stats.edges} edges")
    if report.orphan_pages:
        typer.echo(f"Orphan pages ({len(report.orphan_pages)}):")
        for p in report.orphan_pages:
            typer.echo(f"  {p}")
    if report.broken_links:
        typer.echo(f"Broken links ({len(report.broken_links)}):")
        for page, link in report.broken_links:
            typer.echo(f"  {page} → {link}")
    if report.stale_pages:
        typer.echo(f"Stale pages ({len(report.stale_pages)}):")
        for p in report.stale_pages:
            typer.echo(f"  {p}")
    if report.god_nodes:
        typer.echo(f"God nodes ({len(report.god_nodes)}):")
        for nid, deg in report.god_nodes[:5]:
            typer.echo(f"  {nid}: {deg} connections")


# ---------------------------------------------------------------------------
# atlas serve
# ---------------------------------------------------------------------------

@app.command()
def serve(
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind."),
    port: int = typer.Option(7100, "--port", "-p", help="Port to listen on."),
) -> None:
    """Start the Atlas REST API + WebSocket + Dashboard server."""
    from atlas.server.app import run_server
    run_server(root=root, host=host, port=port)


# ---------------------------------------------------------------------------
# atlas stats
# ---------------------------------------------------------------------------

@app.command()
def stats(
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Show graph statistics."""
    r = _resolve_root(root)
    graph = _load_graph(r)
    s = graph.stats()
    typer.echo(f"Nodes:       {s.nodes}")
    typer.echo(f"Edges:       {s.edges}")
    typer.echo(f"Communities: {s.communities}")
    typer.echo(f"Health:      {s.health_score}")
    for conf, count in sorted(s.confidence_breakdown.items()):
        typer.echo(f"  {conf}: {count}")


# ---------------------------------------------------------------------------
# atlas export
# ---------------------------------------------------------------------------

@app.command()
def export(
    fmt: str = typer.Argument("json", help="Export format: json"),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Export the knowledge graph to a file."""
    import json as _json

    r = _resolve_root(root)
    graph = _load_graph(r)
    out = _out_dir(r)

    data = graph.to_dict()
    dest = out / f"graph.{fmt}"
    dest.write_text(_json.dumps(data, indent=2, default=str))
    typer.echo(f"Exported graph to {dest}")


# ---------------------------------------------------------------------------
# atlas migrate
# ---------------------------------------------------------------------------

@app.command()
def migrate_cmd(
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
    no_skills: bool = typer.Option(False, "--no-skills", help="Skip Atlas skills installation."),
) -> None:
    """Migrate from agent-wiki v1 to Atlas v2."""
    from atlas.migrate import migrate as do_migrate

    r = _resolve_root(root)
    report = do_migrate(r, install_skills=not no_skills)
    
    typer.echo(f"Migrated: {report.get('project', 'unknown') or 'unknown project'}")
    typer.echo(f"Pages migrated: {report.get('pages_migrated', 0)}")
    typer.echo(f"Sources: {report.get('sources', 0)}")
    typer.echo(f"Graph nodes: {report.get('graph_nodes', 0)}")
    if not report.get('success'):
        typer.echo("Migration completed with warnings:", err=True)
        for w in report.get("warnings", []):
            typer.echo(f"  ⚠ {w}", err=True)
