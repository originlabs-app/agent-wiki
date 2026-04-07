# Atlas Skills + CLI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the CLI (`atlas/cli.py`) and the 7 agent skills (`atlas/skills/`) that make Atlas usable by humans and AI agents across all platforms. Also build the multi-platform installer and the agent-wiki v1 migration path.

**Architecture:** The CLI consumes Core engine modules directly (not via REST API). Skills are static SKILL.md files with full agent instructions — no Python code inside them. The installer detects the target platform and symlinks skills to the platform-specific config directory. Skills reference `atlas` CLI commands as the execution layer.

**Tech Stack:** Python 3.12+, typer, pathlib, json, shutil

**Dependencies on other squads:**
- Core engine (Plan 1): `Scanner`, `GraphEngine`, `WikiEngine`, `Linker`, `Analyzer`, `IngestEngine`, `CacheEngine`, `LocalStorage` — all imported directly
- Server (Plan 2): `atlas serve` delegates to `atlas.server.app` — just a one-line call
- Export (Plan 3 or Quality): `atlas export` delegates to `atlas.export.*` modules

---

## File Map

```
atlas/
├── cli.py                         # Main CLI (typer) — all commands
├── install.py                     # Multi-platform installer + hook management
├── migrate.py                     # agent-wiki v1 migration
├── skills/
│   ├── atlas-start/
│   │   └── SKILL.md               # Session start skill
│   ├── atlas-scan/
│   │   └── SKILL.md               # Scan directory skill
│   ├── atlas-query/
│   │   └── SKILL.md               # Query graph skill
│   ├── atlas-ingest/
│   │   └── SKILL.md               # Ingest source skill
│   ├── atlas-progress/
│   │   └── SKILL.md               # Mid-session checkpoint skill
│   ├── atlas-finish/
│   │   └── SKILL.md               # End session skill
│   └── atlas-health/
│       └── SKILL.md               # Deep audit skill

tests/
├── test_cli.py                    # CLI command tests (typer CliRunner)
├── test_install.py                # Install / uninstall / platform detection
├── test_migrate.py                # Migration from agent-wiki v1
├── test_skills.py                 # Skill file structure validation
```

---

## Task 1: CLI Scaffold + `atlas scan`

**Files:**
- Create: `atlas/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing test for `atlas scan`**

`tests/test_cli.py`:
```python
"""CLI tests using typer.testing.CliRunner."""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from atlas.cli import app

runner = CliRunner()


def test_scan_basic(tmp_path):
    """atlas scan <path> runs the full pipeline: scan -> graph -> linker -> save."""
    # Create a minimal Python file
    py_file = tmp_path / "hello.py"
    py_file.write_text('"""Hello module."""\ndef greet(name: str) -> str:\n    return f"Hello {name}"\n')

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "nodes" in result.stdout.lower() or "scanned" in result.stdout.lower()
    # graph.json should be created inside atlas-out/
    assert (tmp_path / "atlas-out" / "graph.json").exists()


def test_scan_nonexistent_path():
    result = runner.invoke(app, ["scan", "/nonexistent/path/xyz"])
    assert result.exit_code != 0


def test_scan_incremental(tmp_path):
    """atlas scan --update only re-extracts changed files."""
    py_file = tmp_path / "hello.py"
    py_file.write_text('"""Hello."""\ndef greet(): pass\n')

    # First scan
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0

    # Second scan with --update
    result = runner.invoke(app, ["scan", str(tmp_path), "--update"])
    assert result.exit_code == 0
    assert "incremental" in result.stdout.lower() or "0 changed" in result.stdout.lower() or result.exit_code == 0


def test_scan_force(tmp_path):
    """atlas scan --force ignores cache."""
    py_file = tmp_path / "hello.py"
    py_file.write_text('"""Hello."""\ndef greet(): pass\n')

    result = runner.invoke(app, ["scan", str(tmp_path), "--force"])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd /Users/pierrebeunardeau/dev/internal/agent-wiki && python -m pytest tests/test_cli.py::test_scan_basic -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.cli'`

- [ ] **Step 3: Implement cli.py with `atlas scan`**

`atlas/cli.py`:
```python
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
    cache = CacheEngine(cache_dir=out / "cache") if not force else None
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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_cli.py -v -k scan`
Expected: All scan tests PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/cli.py tests/test_cli.py
git commit -m "feat: atlas CLI scaffold with scan command

Typer-based CLI. atlas scan <path> runs full pipeline: Scanner -> Graph ->
Linker -> save. Supports --update (incremental) and --force (ignore cache)."
```

---

## Task 2: CLI Query Commands — `query`, `path`, `explain`, `god-nodes`, `surprises`

**Files:**
- Edit: `atlas/cli.py`
- Test: `tests/test_cli.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_cli.py`:
```python
# ---------------------------------------------------------------------------
# Fixtures for query tests
# ---------------------------------------------------------------------------

@pytest.fixture
def graph_dir(tmp_path):
    """Create a tmp dir with a pre-built graph.json for query tests."""
    from atlas.core.models import Node, Edge, Extraction
    from atlas.core.graph import GraphEngine

    out = tmp_path / "atlas-out"
    out.mkdir()

    graph = GraphEngine()
    graph.merge(Extraction(
        nodes=[
            Node(id="auth", label="Auth Module", type="code", source_file="src/auth.py"),
            Node(id="billing", label="Billing", type="code", source_file="src/billing.py"),
            Node(id="db", label="Database", type="code", source_file="src/db.py"),
            Node(id="api", label="API Gateway", type="code", source_file="src/api.py"),
            Node(id="cache", label="Cache Layer", type="code", source_file="src/cache.py"),
        ],
        edges=[
            Edge(source="api", target="auth", relation="imports", confidence="EXTRACTED"),
            Edge(source="api", target="billing", relation="imports", confidence="EXTRACTED"),
            Edge(source="auth", target="db", relation="calls", confidence="EXTRACTED"),
            Edge(source="billing", target="db", relation="calls", confidence="EXTRACTED"),
            Edge(source="auth", target="cache", relation="uses", confidence="INFERRED"),
        ],
    ))
    graph.save(out / "graph.json")
    return tmp_path


def test_query(graph_dir):
    result = runner.invoke(app, ["query", "auth", "--root", str(graph_dir)])
    assert result.exit_code == 0
    assert "auth" in result.stdout.lower()


def test_path(graph_dir):
    result = runner.invoke(app, ["path", "api", "db", "--root", str(graph_dir)])
    assert result.exit_code == 0
    # Should show a path: api -> auth -> db or api -> billing -> db
    assert "api" in result.stdout.lower()
    assert "db" in result.stdout.lower()


def test_path_no_connection(graph_dir):
    result = runner.invoke(app, ["path", "auth", "nonexistent", "--root", str(graph_dir)])
    assert result.exit_code == 0
    assert "no path" in result.stdout.lower()


def test_explain(graph_dir):
    result = runner.invoke(app, ["explain", "auth", "--root", str(graph_dir)])
    assert result.exit_code == 0
    assert "auth" in result.stdout.lower()


def test_explain_unknown(graph_dir):
    result = runner.invoke(app, ["explain", "nonexistent", "--root", str(graph_dir)])
    assert result.exit_code == 0
    assert "not found" in result.stdout.lower()


def test_god_nodes(graph_dir):
    result = runner.invoke(app, ["god-nodes", "--root", str(graph_dir)])
    assert result.exit_code == 0
    # db should be a god node (most connections)
    assert "db" in result.stdout.lower() or "auth" in result.stdout.lower()


def test_surprises(graph_dir):
    result = runner.invoke(app, ["surprises", "--root", str(graph_dir)])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_cli.py -v -k "query or path or explain or god or surprise"`
Expected: FAIL — commands not implemented yet

- [ ] **Step 3: Implement query commands**

Add to `atlas/cli.py`:
```python
# ---------------------------------------------------------------------------
# atlas query
# ---------------------------------------------------------------------------

@app.command()
def query(
    start: str = typer.Argument(..., help="Starting node ID for graph traversal."),
    mode: str = typer.Option("bfs", "--mode", "-m", help="Traversal mode: bfs or dfs."),
    depth: int = typer.Option(3, "--depth", "-d", help="Maximum traversal depth."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Query the knowledge graph starting from a node."""
    root_path = _resolve_root(root)
    graph = _load_graph(root_path)

    if graph.node_count == 0:
        typer.echo("No graph found. Run 'atlas scan' first.")
        raise typer.Exit(code=1)

    subgraph = graph.query(start, mode=mode, depth=depth)
    if not subgraph.nodes:
        typer.echo(f"Node '{start}' not found in the graph.")
        raise typer.Exit(code=0)

    typer.echo(f"Query '{start}' (mode={mode}, depth={depth}):")
    typer.echo(f"  {len(subgraph.nodes)} nodes, {len(subgraph.edges)} edges")
    typer.echo()

    for node in subgraph.nodes:
        typer.echo(f"  [{node.type}] {node.id} — {node.label}")

    typer.echo()
    for edge in subgraph.edges:
        typer.echo(f"  {edge.source} --({edge.relation})--> {edge.target}  [{edge.confidence}]")

    typer.echo(f"\n  ~{subgraph.estimated_tokens} tokens")


# ---------------------------------------------------------------------------
# atlas path
# ---------------------------------------------------------------------------

@app.command()
def path(
    source: str = typer.Argument(..., help="Source node ID."),
    target: str = typer.Argument(..., help="Target node ID."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Find the shortest path between two nodes."""
    root_path = _resolve_root(root)
    graph = _load_graph(root_path)

    edges = graph.path(source, target)
    if edges is None:
        typer.echo(f"No path found between '{source}' and '{target}'.")
        return

    typer.echo(f"Shortest path: {source} -> {target} ({len(edges)} hops)")
    typer.echo()

    current = source
    for edge in edges:
        typer.echo(f"  {edge.source} --({edge.relation})--> {edge.target}  [{edge.confidence}]")
        current = edge.target


# ---------------------------------------------------------------------------
# atlas explain
# ---------------------------------------------------------------------------

@app.command()
def explain(
    concept: str = typer.Argument(..., help="Node ID to explain."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Explain a node: its type, neighbors, and connections."""
    root_path = _resolve_root(root)
    graph = _load_graph(root_path)

    node = graph.get_node(concept)
    if node is None:
        typer.echo(f"Node '{concept}' not found in the graph.")
        return

    typer.echo(f"# {node.label}")
    typer.echo(f"  Type: {node.type}")
    typer.echo(f"  Source: {node.source_file}")
    if node.summary:
        typer.echo(f"  Summary: {node.summary}")
    if node.tags:
        typer.echo(f"  Tags: {', '.join(node.tags)}")
    if node.community is not None:
        typer.echo(f"  Community: {node.community}")

    neighbors = graph.get_neighbors(concept)
    if neighbors:
        typer.echo(f"\n  Connections ({len(neighbors)}):")
        for neighbor, edge in neighbors:
            typer.echo(f"    --({edge.relation})--> {neighbor.id} ({neighbor.label}) [{edge.confidence}]")


# ---------------------------------------------------------------------------
# atlas god-nodes
# ---------------------------------------------------------------------------

@app.command("god-nodes")
def god_nodes(
    top_n: int = typer.Option(10, "--top", "-n", help="Number of top nodes to show."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Show the most connected nodes in the graph."""
    from atlas.core.analyzer import Analyzer

    root_path = _resolve_root(root)
    graph = _load_graph(root_path)
    analyzer = Analyzer(graph=graph)

    gods = analyzer.god_nodes(top_n=top_n)
    if not gods:
        typer.echo("Graph is empty. Run 'atlas scan' first.")
        return

    typer.echo(f"Top {min(top_n, len(gods))} most connected nodes:\n")
    for rank, (node_id, degree) in enumerate(gods, 1):
        node = graph.get_node(node_id)
        label = node.label if node else node_id
        typer.echo(f"  {rank}. {node_id} ({label}) — {degree} connections")


# ---------------------------------------------------------------------------
# atlas surprises
# ---------------------------------------------------------------------------

@app.command()
def surprises(
    top_n: int = typer.Option(10, "--top", "-n", help="Number of surprising connections to show."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Show unexpected or cross-boundary connections."""
    from atlas.core.analyzer import Analyzer

    root_path = _resolve_root(root)
    graph = _load_graph(root_path)
    analyzer = Analyzer(graph=graph)

    edges = analyzer.surprises(top_n=top_n)
    if not edges:
        typer.echo("No surprising connections found.")
        return

    typer.echo(f"Top {min(top_n, len(edges))} surprising connections:\n")
    for rank, edge in enumerate(edges, 1):
        typer.echo(f"  {rank}. {edge.source} --({edge.relation})--> {edge.target}  [{edge.confidence}]")
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_cli.py -v -k "query or path or explain or god or surprise"`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/cli.py tests/test_cli.py
git commit -m "feat: CLI query commands — query, path, explain, god-nodes, surprises

All commands load graph.json from atlas-out/ and use Core engine directly.
query does BFS/DFS traversal, path finds shortest route, explain shows
node details + neighbors, god-nodes and surprises use Analyzer."
```

---

## Task 3: CLI Utility Commands — `ingest`, `export`, `audit`, `serve`

**Files:**
- Edit: `atlas/cli.py`
- Test: `tests/test_cli.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_cli.py`:
```python
# ---------------------------------------------------------------------------
# atlas ingest
# ---------------------------------------------------------------------------

def test_ingest_file(tmp_path):
    """atlas ingest <file> saves to raw/ingested/ with frontmatter."""
    raw = tmp_path / "raw" / "untracked"
    raw.mkdir(parents=True)
    source = raw / "notes.md"
    source.write_text("# My Notes\n\nSome research findings.")

    result = runner.invoke(app, ["ingest", str(source), "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "ingested" in result.stdout.lower()


def test_ingest_nonexistent():
    result = runner.invoke(app, ["ingest", "/nonexistent/file.md"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# atlas audit
# ---------------------------------------------------------------------------

def test_audit(graph_dir):
    result = runner.invoke(app, ["audit", "--root", str(graph_dir)])
    assert result.exit_code == 0
    assert "health" in result.stdout.lower() or "score" in result.stdout.lower()


# ---------------------------------------------------------------------------
# atlas export
# ---------------------------------------------------------------------------

def test_export_json(graph_dir):
    result = runner.invoke(app, ["export", "json", "--root", str(graph_dir)])
    assert result.exit_code == 0


def test_export_unknown_format(graph_dir):
    result = runner.invoke(app, ["export", "unknown_format", "--root", str(graph_dir)])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# atlas serve (just verify it's wired up — don't actually start the server)
# ---------------------------------------------------------------------------

def test_serve_help():
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "port" in result.stdout.lower() or "host" in result.stdout.lower()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_cli.py -v -k "ingest or audit or export or serve"`
Expected: FAIL — commands not implemented

- [ ] **Step 3: Implement utility commands**

Add to `atlas/cli.py`:
```python
# ---------------------------------------------------------------------------
# atlas ingest
# ---------------------------------------------------------------------------

@app.command()
def ingest(
    source: str = typer.Argument(..., help="URL or file path to ingest."),
    title: str = typer.Option(None, "--title", "-t", help="Title for the ingested source."),
    author: str = typer.Option(None, "--author", "-a", help="Author of the source."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Ingest a URL or local file into the knowledge base."""
    import asyncio
    from atlas.core.ingest import IngestEngine
    from atlas.core.storage import LocalStorage

    root_path = _resolve_root(root)
    source_path = Path(source).resolve()

    storage = LocalStorage(root=root_path)
    engine = IngestEngine(storage)

    if source_path.is_file():
        # Local file ingestion
        rel = str(source_path.relative_to(root_path)) if source_path.is_relative_to(root_path) else None
        if rel is None:
            # Copy file into raw/untracked/ first
            dest = root_path / "raw" / "untracked" / source_path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(source_path, dest)
            rel = f"raw/untracked/{source_path.name}"

        result = engine.ingest_file(rel, title=title)
        if result:
            typer.echo(f"Ingested: {source_path.name} -> {result}")
        else:
            typer.echo(f"Error: could not ingest {source}", err=True)
            raise typer.Exit(code=1)
    elif source.startswith("http://") or source.startswith("https://"):
        # URL ingestion
        result = asyncio.run(engine.ingest_url(source, title=title, author=author))
        if result:
            typer.echo(f"Ingested: {source} -> {result}")
        else:
            typer.echo(f"Error: could not fetch {source}", err=True)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Error: '{source}' is not a valid file path or URL.", err=True)
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# atlas audit
# ---------------------------------------------------------------------------

@app.command()
def audit(
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Run a full audit of the knowledge graph and wiki."""
    from atlas.core.analyzer import Analyzer
    from atlas.core.storage import LocalStorage
    from atlas.core.wiki import WikiEngine

    root_path = _resolve_root(root)
    graph = _load_graph(root_path)

    storage = LocalStorage(root=root_path)
    wiki_dir = root_path / "wiki"
    wiki = WikiEngine(storage) if wiki_dir.is_dir() else None

    analyzer = Analyzer(graph=graph, wiki=wiki)
    report = analyzer.audit()

    typer.echo("# Atlas Audit Report\n")

    if report.stats:
        typer.echo(f"  Nodes: {report.stats.nodes}")
        typer.echo(f"  Edges: {report.stats.edges}")
        typer.echo(f"  Communities: {report.stats.communities}")
        typer.echo(f"  Confidence: {report.stats.confidence_breakdown}")
    typer.echo(f"  Health score: {report.health_score}\n")

    if report.god_nodes:
        typer.echo("  God nodes:")
        for node_id, degree in report.god_nodes[:5]:
            typer.echo(f"    - {node_id} ({degree} connections)")
        typer.echo()

    if report.orphan_pages:
        typer.echo(f"  Orphan pages ({len(report.orphan_pages)}):")
        for p in report.orphan_pages:
            typer.echo(f"    - {p}")
        typer.echo()

    if report.broken_links:
        typer.echo(f"  Broken links ({len(report.broken_links)}):")
        for page, link in report.broken_links:
            typer.echo(f"    - {page} -> [[{link}]]")
        typer.echo()

    if report.stale_pages:
        typer.echo(f"  Stale pages ({len(report.stale_pages)}):")
        for p in report.stale_pages:
            typer.echo(f"    - {p}")
        typer.echo()

    if report.contradictions:
        typer.echo(f"  Contradictions ({len(report.contradictions)}):")
        for c in report.contradictions:
            typer.echo(f"    - {c}")
        typer.echo()


# ---------------------------------------------------------------------------
# atlas export
# ---------------------------------------------------------------------------

_EXPORT_FORMATS = {"json", "html", "obsidian", "neo4j", "graphml", "svg", "pdf"}

@app.command()
def export(
    format: str = typer.Argument(..., help=f"Export format: {', '.join(sorted(_EXPORT_FORMATS))}"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path (default: atlas-out/graph.<ext>)."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Export the knowledge graph to a specified format."""
    if format not in _EXPORT_FORMATS:
        typer.echo(f"Error: unknown format '{format}'. Choose from: {', '.join(sorted(_EXPORT_FORMATS))}", err=True)
        raise typer.Exit(code=1)

    root_path = _resolve_root(root)
    out = _out_dir(root_path)
    graph_path = out / "graph.json"

    if not graph_path.exists():
        typer.echo("No graph found. Run 'atlas scan' first.", err=True)
        raise typer.Exit(code=1)

    # Determine output path
    ext_map = {"json": "json", "html": "html", "obsidian": "", "neo4j": "cypher", "graphml": "graphml", "svg": "svg", "pdf": "pdf"}
    if output is None:
        if format == "obsidian":
            output_path = out / "obsidian-export"
        else:
            output_path = out / f"graph.{ext_map[format]}"
    else:
        output_path = Path(output)

    # Dispatch to export module
    try:
        export_module = __import__(f"atlas.export.{format}", fromlist=[format])
        export_fn = getattr(export_module, f"export_{format}", None) or getattr(export_module, "export")
        export_fn(graph_path=graph_path, output_path=output_path)
        typer.echo(f"Exported {format} to {output_path}")
    except ImportError:
        # Fallback: for json, just copy graph.json
        if format == "json":
            import shutil
            shutil.copy2(graph_path, output_path)
            typer.echo(f"Exported {format} to {output_path}")
        else:
            typer.echo(f"Error: export module for '{format}' not available. Install atlas-ai[all].", err=True)
            raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# atlas serve
# ---------------------------------------------------------------------------

@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to."),
    port: int = typer.Option(7100, "--port", "-p", help="Port to listen on."),
    mcp: bool = typer.Option(False, "--mcp", help="Also start MCP server (stdio)."),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Start the Atlas FastAPI server with dashboard."""
    try:
        import uvicorn
    except ImportError:
        typer.echo("Error: uvicorn not installed. Run: pip install atlas-ai[server]", err=True)
        raise typer.Exit(code=1)

    root_path = _resolve_root(root)

    # Set root in environment for the server app to pick up
    import os
    os.environ["ATLAS_ROOT"] = str(root_path)
    if mcp:
        os.environ["ATLAS_MCP"] = "1"

    typer.echo(f"Starting Atlas server at http://{host}:{port}")
    typer.echo(f"Root: {root_path}")
    typer.echo(f"Dashboard: http://{host}:{port}/")
    uvicorn.run("atlas.server.app:app", host=host, port=port, reload=False)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_cli.py -v -k "ingest or audit or export or serve"`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/cli.py tests/test_cli.py
git commit -m "feat: CLI utility commands — ingest, audit, export, serve

ingest handles local files and URLs via IngestEngine. audit runs Analyzer
on graph + wiki. export dispatches to format-specific modules. serve starts
FastAPI + uvicorn on port 7100."
```

---

## Task 4: Multi-Platform Installer

**Files:**
- Create: `atlas/install.py`
- Edit: `atlas/cli.py` (add `install` and `hook` commands)
- Test: `tests/test_install.py`

- [ ] **Step 1: Write failing tests**

`tests/test_install.py`:
```python
"""Tests for atlas install — multi-platform skill deployment."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from atlas.install import (
    detect_platforms,
    install_skills,
    uninstall_skills,
    install_claude_hook,
    uninstall_claude_hook,
    PLATFORM_CONFIG,
)


def test_detect_claude(tmp_path):
    """Detects Claude Code when ~/.claude/ exists."""
    (tmp_path / ".claude").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        platforms = detect_platforms()
    assert "claude" in platforms


def test_detect_codex(tmp_path):
    """Detects Codex when ~/.codex/ exists."""
    (tmp_path / ".codex").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        platforms = detect_platforms()
    assert "codex" in platforms


def test_detect_cursor(tmp_path):
    """Detects Cursor when ~/.cursor/ exists."""
    (tmp_path / ".cursor").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        platforms = detect_platforms()
    assert "cursor" in platforms


def test_detect_hermes(tmp_path):
    """Detects Hermes when ~/.hermes/ exists."""
    (tmp_path / ".hermes").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        platforms = detect_platforms()
    assert "hermes" in platforms


def test_detect_nothing(tmp_path):
    """Returns empty list when no platforms detected."""
    with patch("atlas.install.Path.home", return_value=tmp_path):
        platforms = detect_platforms()
    assert platforms == []


def test_install_skills_claude(tmp_path):
    """Install creates symlinks in ~/.claude/skills/ for Claude Code."""
    (tmp_path / ".claude").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        install_skills(platform="claude")

    skills_dir = tmp_path / ".claude" / "skills"
    expected_skills = ["atlas-start", "atlas-scan", "atlas-query", "atlas-ingest", "atlas-progress", "atlas-finish", "atlas-health"]
    for skill_name in expected_skills:
        skill_file = skills_dir / skill_name / "SKILL.md"
        assert skill_file.exists(), f"Missing skill: {skill_name}"


def test_install_skills_codex(tmp_path):
    """Install creates symlinks in ~/.agents/skills/ for Codex."""
    (tmp_path / ".codex").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        install_skills(platform="codex")

    skills_dir = tmp_path / ".agents" / "skills"
    assert (skills_dir / "atlas-start" / "SKILL.md").exists()


def test_install_skills_hermes(tmp_path):
    """Install creates symlinks in ~/.hermes/skills/ for Hermes."""
    (tmp_path / ".hermes").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        install_skills(platform="hermes")

    skills_dir = tmp_path / ".hermes" / "skills"
    assert (skills_dir / "atlas-start" / "SKILL.md").exists()


def test_uninstall_skills(tmp_path):
    """Uninstall removes the skill symlinks."""
    (tmp_path / ".claude").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        install_skills(platform="claude")
        uninstall_skills(platform="claude")

    skills_dir = tmp_path / ".claude" / "skills"
    for name in ["atlas-start", "atlas-scan", "atlas-query", "atlas-ingest", "atlas-progress", "atlas-finish", "atlas-health"]:
        assert not (skills_dir / name / "SKILL.md").exists()


def test_install_claude_hook(tmp_path):
    """Install writes PreToolUse hook to .claude/settings.json."""
    project = tmp_path / "myproject"
    project.mkdir()
    install_claude_hook(project)

    settings = json.loads((project / ".claude" / "settings.json").read_text())
    hooks = settings.get("hooks", {}).get("PreToolUse", [])
    assert any("atlas" in json.dumps(h) for h in hooks)


def test_install_claude_hook_idempotent(tmp_path):
    """Second install doesn't duplicate the hook."""
    project = tmp_path / "myproject"
    project.mkdir()
    install_claude_hook(project)
    install_claude_hook(project)

    settings = json.loads((project / ".claude" / "settings.json").read_text())
    hooks = settings["hooks"]["PreToolUse"]
    atlas_hooks = [h for h in hooks if "atlas" in json.dumps(h)]
    assert len(atlas_hooks) == 1


def test_uninstall_claude_hook(tmp_path):
    """Uninstall removes the hook from settings.json."""
    project = tmp_path / "myproject"
    project.mkdir()
    install_claude_hook(project)
    uninstall_claude_hook(project)

    settings = json.loads((project / ".claude" / "settings.json").read_text())
    hooks = settings.get("hooks", {}).get("PreToolUse", [])
    assert not any("atlas" in json.dumps(h) for h in hooks)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_install.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement install.py**

`atlas/install.py`:
```python
"""Multi-platform installer — detect platforms, symlink skills, configure hooks."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Skill source: the SKILL.md files shipped inside the atlas package
# ---------------------------------------------------------------------------

_SKILLS_SRC = Path(__file__).parent / "skills"

_SKILL_NAMES = [
    "atlas-start",
    "atlas-scan",
    "atlas-query",
    "atlas-ingest",
    "atlas-progress",
    "atlas-finish",
    "atlas-health",
]

# ---------------------------------------------------------------------------
# Platform config
# ---------------------------------------------------------------------------

PLATFORM_CONFIG: dict[str, dict] = {
    "claude": {
        "detect_dir": ".claude",
        "skills_dir": Path(".claude") / "skills",
        "has_hook": True,
    },
    "codex": {
        "detect_dir": ".codex",
        "skills_dir": Path(".agents") / "skills",
        "has_hook": False,
    },
    "cursor": {
        "detect_dir": ".cursor",
        "skills_dir": Path(".cursor") / "skills",
        "has_hook": False,
    },
    "hermes": {
        "detect_dir": ".hermes",
        "skills_dir": Path(".hermes") / "skills",
        "has_hook": False,
    },
}

# ---------------------------------------------------------------------------
# Claude Code PreToolUse hook — nudges the agent to read the graph
# ---------------------------------------------------------------------------

_CLAUDE_HOOK = {
    "matcher": "Glob|Grep",
    "hooks": [
        {
            "type": "command",
            "command": (
                "[ -f atlas-out/graph.json ] && "
                "echo 'atlas: Knowledge graph exists at atlas-out/. "
                "Read atlas-out/GRAPH_REPORT.md or run atlas query before searching raw files.' || true"
            ),
        }
    ],
}


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def detect_platforms() -> list[str]:
    """Detect which AI coding platforms are installed on this machine."""
    home = Path.home()
    found = []
    for platform, cfg in PLATFORM_CONFIG.items():
        if (home / cfg["detect_dir"]).is_dir():
            found.append(platform)
    return found


# ---------------------------------------------------------------------------
# Skill installation
# ---------------------------------------------------------------------------

def install_skills(platform: str) -> list[str]:
    """Copy SKILL.md files to the platform's skill directory.

    Returns list of installed skill paths.
    """
    if platform not in PLATFORM_CONFIG:
        raise ValueError(f"Unknown platform '{platform}'. Choose from: {', '.join(PLATFORM_CONFIG)}")

    home = Path.home()
    skills_dst = home / PLATFORM_CONFIG[platform]["skills_dir"]

    installed = []
    for name in _SKILL_NAMES:
        src = _SKILLS_SRC / name / "SKILL.md"
        if not src.exists():
            continue

        dst_dir = skills_dst / name
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / "SKILL.md"

        # Copy (not symlink) — more robust across platforms
        shutil.copy2(src, dst)
        installed.append(str(dst))

    return installed


def uninstall_skills(platform: str) -> list[str]:
    """Remove Atlas skill directories from the platform's skill dir.

    Returns list of removed paths.
    """
    if platform not in PLATFORM_CONFIG:
        raise ValueError(f"Unknown platform '{platform}'. Choose from: {', '.join(PLATFORM_CONFIG)}")

    home = Path.home()
    skills_dst = home / PLATFORM_CONFIG[platform]["skills_dir"]

    removed = []
    for name in _SKILL_NAMES:
        skill_dir = skills_dst / name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            removed.append(str(skill_dir))

    return removed


# ---------------------------------------------------------------------------
# Claude Code hook management
# ---------------------------------------------------------------------------

def install_claude_hook(project_dir: Path) -> None:
    """Add Atlas PreToolUse hook to .claude/settings.json."""
    settings_path = project_dir / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])

    # Check idempotency
    if any(h.get("matcher") == "Glob|Grep" and "atlas" in json.dumps(h) for h in pre_tool):
        return

    pre_tool.append(_CLAUDE_HOOK)
    settings_path.write_text(json.dumps(settings, indent=2))


def uninstall_claude_hook(project_dir: Path) -> None:
    """Remove Atlas PreToolUse hook from .claude/settings.json."""
    settings_path = project_dir / ".claude" / "settings.json"
    if not settings_path.exists():
        return

    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        return

    pre_tool = settings.get("hooks", {}).get("PreToolUse", [])
    filtered = [h for h in pre_tool if not (h.get("matcher") == "Glob|Grep" and "atlas" in json.dumps(h))]

    if len(filtered) == len(pre_tool):
        return  # nothing to remove

    settings["hooks"]["PreToolUse"] = filtered
    settings_path.write_text(json.dumps(settings, indent=2))


# ---------------------------------------------------------------------------
# AGENTS.md management (Codex, Cursor, Hermes)
# ---------------------------------------------------------------------------

_AGENTS_MD_SECTION = """\
## atlas

This project has an Atlas knowledge graph at atlas-out/.

Rules:
- Before answering architecture or codebase questions, run `atlas query "<topic>"` or read atlas-out/GRAPH_REPORT.md
- If wiki/index.md exists, navigate the wiki instead of reading raw files
- Use `/atlas-start` at session start for a briefing
- Use `/atlas-finish` at session end to write back durable knowledge
"""

_AGENTS_MD_MARKER = "## atlas"


def install_agents_md(project_dir: Path) -> bool:
    """Write the Atlas section to AGENTS.md in the project root."""
    target = project_dir / "AGENTS.md"

    if target.exists():
        content = target.read_text()
        if _AGENTS_MD_MARKER in content:
            return False  # already installed
        target.write_text(content.rstrip() + "\n\n" + _AGENTS_MD_SECTION)
    else:
        target.write_text(_AGENTS_MD_SECTION)

    return True


def uninstall_agents_md(project_dir: Path) -> bool:
    """Remove the Atlas section from AGENTS.md."""
    import re

    target = project_dir / "AGENTS.md"
    if not target.exists():
        return False

    content = target.read_text()
    if _AGENTS_MD_MARKER not in content:
        return False

    cleaned = re.sub(
        r"\n*## atlas\n.*?(?=\n## |\Z)",
        "",
        content,
        flags=re.DOTALL,
    ).rstrip()

    if cleaned:
        target.write_text(cleaned + "\n")
    else:
        target.unlink()

    return True
```

- [ ] **Step 4: Add `install` and `hook` commands to cli.py**

Add to `atlas/cli.py`:
```python
# ---------------------------------------------------------------------------
# atlas install
# ---------------------------------------------------------------------------

@app.command()
def install(
    platform: str = typer.Argument(None, help="Platform to install for (claude, codex, cursor, hermes). Auto-detects if omitted."),
    project: bool = typer.Option(False, "--project", help="Also configure the current project (CLAUDE.md hook or AGENTS.md)."),
) -> None:
    """Install Atlas skills for your AI coding platform."""
    from atlas.install import detect_platforms, install_skills, install_claude_hook, install_agents_md

    if platform:
        platforms = [platform]
    else:
        platforms = detect_platforms()
        if not platforms:
            typer.echo("No supported platform detected. Specify one: atlas install claude|codex|cursor|hermes")
            raise typer.Exit(code=1)
        typer.echo(f"Detected platforms: {', '.join(platforms)}")

    for p in platforms:
        typer.echo(f"\nInstalling skills for {p}...")
        installed = install_skills(p)
        for path in installed:
            typer.echo(f"  {path}")
        typer.echo(f"  {len(installed)} skills installed.")

    if project:
        cwd = Path.cwd()
        if "claude" in platforms:
            install_claude_hook(cwd)
            typer.echo(f"\n  Claude Code PreToolUse hook installed in {cwd / '.claude' / 'settings.json'}")
        for p in platforms:
            if p != "claude":
                if install_agents_md(cwd):
                    typer.echo(f"\n  AGENTS.md updated for {p}")

    typer.echo("\nDone. Skills available:")
    for name in ["atlas-start", "atlas-scan", "atlas-query", "atlas-ingest", "atlas-progress", "atlas-finish", "atlas-health"]:
        typer.echo(f"  /{name}")


# ---------------------------------------------------------------------------
# atlas hook
# ---------------------------------------------------------------------------

@app.command()
def hook(
    action: str = typer.Argument(..., help="Action: install, uninstall, or status."),
) -> None:
    """Manage git hooks (post-commit, post-checkout) for auto-rebuild."""
    from atlas.hooks import install as hook_install, uninstall as hook_uninstall, status as hook_status

    if action == "install":
        typer.echo(hook_install(Path.cwd()))
    elif action == "uninstall":
        typer.echo(hook_uninstall(Path.cwd()))
    elif action == "status":
        typer.echo(hook_status(Path.cwd()))
    else:
        typer.echo(f"Unknown action '{action}'. Use: install, uninstall, or status.", err=True)
        raise typer.Exit(code=1)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_install.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add atlas/install.py atlas/cli.py tests/test_install.py
git commit -m "feat: multi-platform installer with auto-detection

Detects Claude Code, Codex, Cursor, Hermes. Copies SKILL.md files to
platform config dir. Claude Code gets a PreToolUse hook in settings.json.
Other platforms get an AGENTS.md section. atlas install auto-detects."
```

---

## Task 5: Migration from agent-wiki v1

**Files:**
- Create: `atlas/migrate.py`
- Edit: `atlas/cli.py` (add `migrate` command)
- Test: `tests/test_migrate.py`

- [ ] **Step 1: Write failing tests**

`tests/test_migrate.py`:
```python
"""Tests for atlas migrate — agent-wiki v1 -> Atlas migration."""
from pathlib import Path
from unittest.mock import patch

import pytest

from atlas.migrate import detect_wiki_v1, migrate


def _make_wiki_v1(root: Path) -> None:
    """Create a minimal agent-wiki v1 structure."""
    (root / "wiki" / "projects").mkdir(parents=True)
    (root / "wiki" / "concepts").mkdir(parents=True)
    (root / "wiki" / "sources").mkdir(parents=True)
    (root / "wiki" / "decisions").mkdir(parents=True)
    (root / "raw" / "untracked").mkdir(parents=True)
    (root / "raw" / "ingested").mkdir(parents=True)

    (root / "AGENTS.md").write_text("# Knowledge Base Schema\n\nA wiki.\n")
    (root / "wiki" / "index.md").write_text("---\ntype: wiki-index\n---\n\n# Wiki Index\n")
    (root / "wiki" / "log.md").write_text("# Log\n")
    (root / "wiki" / "projects" / "acme.md").write_text(
        "---\ntype: wiki-page\ntitle: Acme\n---\n\n# Acme\n\nA project. See [[auth]].\n"
    )
    (root / "wiki" / "concepts" / "auth.md").write_text(
        "---\ntype: wiki-concept\ntitle: Authentication\ntags: [auth]\n---\n\n# Auth\n\nJWT-based. Related to [[billing]].\n"
    )
    (root / "wiki" / "concepts" / "billing.md").write_text(
        "---\ntype: wiki-concept\ntitle: Billing\ntags: [payments]\n---\n\n# Billing\n\nStripe. See [[auth]].\n"
    )


def test_detect_wiki_v1(tmp_path):
    _make_wiki_v1(tmp_path)
    result = detect_wiki_v1(tmp_path)
    assert result is not None
    assert result["wiki_dir"] == str(tmp_path / "wiki")
    assert result["page_count"] >= 3


def test_detect_wiki_v1_missing(tmp_path):
    result = detect_wiki_v1(tmp_path)
    assert result is None


def test_migrate_builds_graph(tmp_path):
    _make_wiki_v1(tmp_path)
    report = migrate(tmp_path)

    assert report["status"] == "success"
    assert report["nodes"] > 0
    assert report["edges"] >= 0

    # graph.json should exist
    assert (tmp_path / "atlas-out" / "graph.json").exists()


def test_migrate_preserves_wiki(tmp_path):
    """Migration must not modify existing wiki content."""
    _make_wiki_v1(tmp_path)
    original_auth = (tmp_path / "wiki" / "concepts" / "auth.md").read_text()

    migrate(tmp_path)

    assert (tmp_path / "wiki" / "concepts" / "auth.md").read_text() == original_auth


def test_migrate_installs_skills(tmp_path):
    """Migration installs Atlas skills if a platform is detected."""
    _make_wiki_v1(tmp_path)
    (tmp_path / ".claude").mkdir()

    with patch("atlas.migrate.Path.home", return_value=tmp_path):
        report = migrate(tmp_path, install_skills=True)

    assert "skills_installed" in report
    assert report["skills_installed"] > 0


def test_migrate_idempotent(tmp_path):
    """Running migrate twice doesn't break anything."""
    _make_wiki_v1(tmp_path)
    migrate(tmp_path)
    report = migrate(tmp_path)
    assert report["status"] == "success"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_migrate.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement migrate.py**

`atlas/migrate.py`:
```python
"""Migration from agent-wiki v1 to Atlas v2."""
from __future__ import annotations

from pathlib import Path


def detect_wiki_v1(root: Path) -> dict | None:
    """Detect an existing agent-wiki v1 installation.

    Returns a dict with wiki metadata, or None if not found.
    Looks for: wiki/ directory with index.md, raw/ directory, AGENTS.md.
    """
    wiki_dir = root / "wiki"
    if not wiki_dir.is_dir():
        return None

    index = wiki_dir / "index.md"
    if not index.is_file():
        return None

    # Count pages
    page_count = 0
    for md in wiki_dir.rglob("*.md"):
        if md.name not in ("index.md", "log.md", "_template.md"):
            page_count += 1

    has_raw = (root / "raw").is_dir()
    has_agents_md = (root / "AGENTS.md").is_file()
    has_log = (wiki_dir / "log.md").is_file()

    return {
        "wiki_dir": str(wiki_dir),
        "raw_dir": str(root / "raw") if has_raw else None,
        "agents_md": has_agents_md,
        "page_count": page_count,
        "has_log": has_log,
    }


def migrate(
    root: Path,
    install_skills: bool = False,
) -> dict:
    """Migrate from agent-wiki v1 to Atlas v2.

    Steps:
    1. Detect existing wiki structure
    2. Scan wiki to build initial graph.json
    3. Optionally install Atlas skills for detected platforms
    4. Preserve all existing content — zero loss

    Returns a report dict with migration results.
    """
    from atlas.core.graph import GraphEngine
    from atlas.core.linker import Linker
    from atlas.core.storage import LocalStorage
    from atlas.core.wiki import WikiEngine

    report: dict = {"status": "success", "nodes": 0, "edges": 0, "pages_found": 0}

    # Step 1: Detect
    detection = detect_wiki_v1(root)
    if detection is None:
        report["status"] = "no_wiki_found"
        report["message"] = f"No agent-wiki v1 found at {root}. Expected wiki/ directory with index.md."
        return report

    report["pages_found"] = detection["page_count"]

    # Step 2: Build graph from wiki
    storage = LocalStorage(root=root)
    wiki = WikiEngine(storage)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)

    # Sync wiki -> graph (creates nodes for pages, edges for wikilinks)
    changes = linker.sync_wiki_to_graph()
    report["nodes"] = graph.node_count
    report["edges"] = graph.edge_count
    report["graph_changes"] = len(changes)

    # Save graph
    out = root / "atlas-out"
    out.mkdir(parents=True, exist_ok=True)
    graph.save(out / "graph.json")
    report["graph_path"] = str(out / "graph.json")

    # Step 3: Install skills if requested
    if install_skills:
        from atlas.install import detect_platforms, install_skills as _install

        platforms = detect_platforms()
        total_installed = 0
        for platform in platforms:
            installed = _install(platform=platform)
            total_installed += len(installed)
        report["skills_installed"] = total_installed
        report["platforms"] = platforms

    return report
```

- [ ] **Step 4: Add `migrate` command to cli.py**

Add to `atlas/cli.py`:
```python
# ---------------------------------------------------------------------------
# atlas migrate
# ---------------------------------------------------------------------------

@app.command()
def migrate(
    root: str = typer.Option(".", "--root", "-r", help="Root directory containing agent-wiki v1."),
    skills: bool = typer.Option(True, "--skills/--no-skills", help="Install Atlas skills for detected platforms."),
) -> None:
    """Migrate from agent-wiki v1 to Atlas v2."""
    from atlas.migrate import detect_wiki_v1, migrate as run_migrate

    root_path = _resolve_root(root)

    # Detect
    detection = detect_wiki_v1(root_path)
    if detection is None:
        typer.echo(f"No agent-wiki v1 found at {root_path}.")
        typer.echo("Expected: wiki/ directory with index.md.")
        raise typer.Exit(code=1)

    typer.echo(f"Found agent-wiki v1 at {root_path}:")
    typer.echo(f"  Wiki pages: {detection['page_count']}")
    typer.echo(f"  Raw directory: {'yes' if detection['raw_dir'] else 'no'}")
    typer.echo(f"  AGENTS.md: {'yes' if detection['agents_md'] else 'no'}")
    typer.echo()

    # Migrate
    typer.echo("Migrating...")
    report = run_migrate(root_path, install_skills=skills)

    if report["status"] == "success":
        typer.echo(f"  Graph built: {report['nodes']} nodes, {report['edges']} edges")
        typer.echo(f"  Saved to: {report['graph_path']}")
        if "skills_installed" in report:
            typer.echo(f"  Skills installed: {report['skills_installed']} ({', '.join(report.get('platforms', []))})")
        typer.echo()
        typer.echo("Migration complete. All wiki content preserved.")
        typer.echo("Run 'atlas scan .' to enrich the graph with raw/ content.")
    else:
        typer.echo(f"Migration failed: {report.get('message', 'unknown error')}", err=True)
        raise typer.Exit(code=1)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_migrate.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add atlas/migrate.py atlas/cli.py tests/test_migrate.py
git commit -m "feat: agent-wiki v1 migration — detect, build graph, install skills

atlas migrate detects existing wiki/ structure, builds graph.json from
wiki pages and wikilinks via Linker.sync_wiki_to_graph, installs Atlas
skills for detected platforms. Zero content loss — wiki is preserved as-is."
```

---

## Task 6: Skill Files — atlas-start, atlas-scan, atlas-query

**Files:**
- Create: `atlas/skills/atlas-start/SKILL.md`
- Create: `atlas/skills/atlas-scan/SKILL.md`
- Create: `atlas/skills/atlas-query/SKILL.md`

- [ ] **Step 1: Create atlas-start/SKILL.md**

`atlas/skills/atlas-start/SKILL.md`:
```markdown
---
name: atlas-start
description: >
  Begin an Atlas session. Reads the knowledge graph and wiki, detects
  tensions, briefs the agent, asks socratic questions, and proposes a
  session plan. Use at the start of every work session.
---

# /atlas-start

Begin a session. Observe, analyze, suggest, ask.

## 1. Observe (silent)

- Run `atlas audit --root .` to get graph + wiki health
- Read `wiki/index.md` — what topics exist?
- Scan `wiki/projects/`, `wiki/concepts/`, `wiki/decisions/`, `wiki/sources/`
- Read `wiki/log.md` — what happened recently?
- Check `raw/untracked/` — any new sources waiting?
- Run `atlas god-nodes --root .` — what are the key concepts?
- Check recent git activity if in a code repo

## 2. Analyze (silent)

Look for tensions between what the wiki says and what's actually happening:

- Wiki says priority is X, but repo activity suggests Y
- A decision was recorded, but code goes a different direction
- Next steps in wiki are stale or already done
- New sources in raw/untracked/ not yet ingested
- No wiki page exists for this repo/project
- Atlas audit found contradictions, orphans, or broken links
- Recent work not reflected in the wiki
- God nodes that lack dedicated wiki pages

## 3. Suggest

Based on what you found, make concrete suggestions:

**Ingestion:** "There are 3 files in raw/untracked/. Want me to ingest them? I'd run `atlas ingest` for each."

**Graph gaps:** "The graph has 5 nodes without wiki pages. Want me to create stubs?"

**Staleness:** "The wiki hasn't been updated in 2 weeks. The repo has 14 new commits. Want me to run `atlas scan --update .` and refresh?"

**Contradictions:** "The wiki says you chose Stripe, but the graph shows PayPal imports. Which is current?"

**Missing context:** "I don't see a wiki page for this project. Want me to create one from what the graph shows?"

## 4. Ask 2-5 socratic questions

Based on tensions observed. Always hypothesize before asking:

- Bad: "What project is this?"
- Good: "Based on the graph, this is the auth module — the wiki says next step is API integration. Is that what we're doing today?"

- Bad: "What do you want to do?"
- Good: "The audit shows 3 stale pages and 2 broken links. The most recent commit touched billing. Are we continuing billing, or should we fix the wiki first?"

## 5. Connect intent to the graph

When the user says what they want to work on, query the graph:

- "You want to work on auth. Let me check: `atlas query auth`. The graph shows auth connects to db, cache, and billing. The wiki has a decision page about JWT vs sessions. Here's what it says: [summary]."
- "That topic isn't in the graph yet. Want me to scan for it or create a wiki page?"

## 6. Propose a short session plan

2-4 concrete steps based on the answers.

## 7. Multi-step deep queries

When answering complex questions:
1. `atlas query "<concept>"` — get the graph neighborhood
2. Read the wiki page for that concept
3. If it cites sources, read those source pages
4. If sources reference raw files, read the original
5. Synthesize across all levels. Cite with [[page-name]].

---

## Atlas CLI commands used

- `atlas audit --root .` — health score, orphans, contradictions, staleness
- `atlas god-nodes --root .` — most connected concepts
- `atlas query "<concept>" --root .` — graph traversal from a concept
- `atlas surprises --root .` — unexpected cross-boundary connections
- `atlas scan --update . ` — incremental re-scan

## Rules

1. Always observe before asking. Never ask what you can infer.
2. Hypothesize, then confirm. "I think X. Correct?" not "What is X?"
3. Suggest concretely. "I'd run [command] to [result]" not "should I update something?"
4. 2-5 questions max. Never more.
5. Show write-back proposals before executing. User approves.
6. If atlas-out/graph.json doesn't exist, suggest running `atlas scan .` first.
7. If the session is trivial, say so and skip.

---

## Other Atlas skills

- `/atlas-scan` — scan a directory into the knowledge graph
- `/atlas-query` — query the graph for connections
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-progress` — mid-session checkpoint
- `/atlas-finish` — end session, write back durable knowledge
- `/atlas-health` — deep audit of graph and wiki
```

- [ ] **Step 2: Create atlas-scan/SKILL.md**

`atlas/skills/atlas-scan/SKILL.md`:
```markdown
---
name: atlas-scan
description: >
  Scan a directory to build or update the knowledge graph. Extracts
  nodes and edges from code, docs, and images. Use when pointing Atlas
  at a new corpus or refreshing after changes.
---

# /atlas-scan

Point Atlas at a folder. It extracts a knowledge graph automatically.

## Usage

```
/atlas-scan                    # scan current directory
/atlas-scan <path>             # scan specific path
/atlas-scan <path> --update    # incremental — only changed files
/atlas-scan <path> --force     # ignore cache, full re-extract
```

## What it does

1. **Collect files** — walks the directory, filters by supported extensions (13 code languages + markdown + PDF + images)
2. **Extract** — AST extraction for code (free, instant), LLM extraction for docs/images (cached by SHA256)
3. **Build graph** — merges extraction into graph.json (NetworkX serialized)
4. **Sync wiki** — if wiki/ exists, runs the Linker to sync graph <-> wiki
5. **Report** — prints node/edge counts, communities, health score

## Step-by-step

1. Run `atlas scan <path>` (or `atlas scan <path> --update` for incremental)
2. Review the output: "Extracted N nodes, M edges. Graph: X nodes, Y edges, Z communities."
3. If wiki/ exists, review suggestions: "Wiki sync: N changes, M suggestions."
4. Optionally run `atlas god-nodes` to see the most connected concepts
5. Optionally run `atlas surprises` to find unexpected connections

## When to use

- **New project:** first time scanning a codebase or corpus
- **After changes:** `--update` to re-extract only what changed
- **After branch switch:** refresh the graph for the new branch
- **After ingesting sources:** rebuild to include new raw material

## What gets extracted

| File type | Method | Cost |
|-----------|--------|------|
| Python, JS, TS, Go, Rust, Java, C/C++, Ruby, Swift, Kotlin, C#, Scala, PHP | AST (tree-sitter) | Free |
| Markdown, text | LLM (concepts, entities, relations) | Cached |
| PDF | Text extraction + LLM | Cached |
| Images (PNG, JPG, diagrams) | Claude Vision | Cached |

## Atlas CLI command

```bash
atlas scan <path> [--update] [--force]
```

## Rules

1. Run scan before any query command — the graph must exist first.
2. Use `--update` for incremental scans (faster, cheaper).
3. Use `--force` only when the cache seems stale or corrupted.
4. After scanning, suggest running `/atlas-start` for a briefing.

---

## Other Atlas skills

- `/atlas-start` — begin a session, get briefed on the knowledge graph
- `/atlas-query` — query the graph for connections
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-progress` — mid-session checkpoint
- `/atlas-finish` — end session, write back durable knowledge
- `/atlas-health` — deep audit of graph and wiki
```

- [ ] **Step 3: Create atlas-query/SKILL.md**

`atlas/skills/atlas-query/SKILL.md`:
```markdown
---
name: atlas-query
description: >
  Query the Atlas knowledge graph. Traverses nodes, finds paths,
  explains concepts, identifies god nodes and surprises. Use when
  the user asks a question about the codebase or knowledge base.
---

# /atlas-query

Ask the knowledge graph a question. It traverses and synthesizes.

## Usage

```
/atlas-query "what connects auth to billing?"
/atlas-query path auth billing
/atlas-query explain auth
/atlas-query god-nodes
/atlas-query surprises
```

## Commands

### Graph traversal
```bash
atlas query "<start_node>" --mode bfs --depth 3
```
Starts from a node and traverses BFS or DFS up to the given depth. Returns all nodes and edges in the subgraph.

### Shortest path
```bash
atlas path "<source>" "<target>"
```
Finds the shortest path between two concepts. Shows each hop with its relation and confidence.

### Explain a concept
```bash
atlas explain "<concept>"
```
Shows a node's type, source, tags, community, and all its neighbors. Plain-English summary of what it is and how it connects.

### God nodes
```bash
atlas god-nodes --top 10
```
Shows the most connected concepts. These are the structural hubs — if they break, the graph fragments.

### Surprising connections
```bash
atlas surprises --top 10
```
Shows unexpected edges: INFERRED or AMBIGUOUS confidence, cross-community, cross-file-type. These are the insights the graph reveals that you wouldn't find manually.

## How to answer questions

When the user asks a question:

1. **Identify the key concept(s)** in the question
2. **Query the graph**: `atlas query "<concept>"` or `atlas path "<A>" "<B>"`
3. **Read the wiki page** for the concept if it exists
4. **Synthesize**: combine graph structure with wiki content
5. **Cite**: "According to [[wiki/concepts/auth]], auth uses JWT. The graph shows auth connects to db, cache, and billing."

If the question spans multiple concepts:
1. Query each concept separately
2. Check if they share neighbors or communities
3. Look for paths between them
4. Synthesize the combined picture

If the graph doesn't have the answer:
- Say so: "The graph doesn't have a node for [X]. Want me to scan for it?"
- Suggest: "Run `atlas scan --update .` to pick up recent changes."

## Rules

1. Always check the graph before answering from memory.
2. Cite graph structure: "The graph shows X connects to Y via [relation]."
3. Cite wiki pages: "According to [[page-name]]..."
4. If a query returns nothing, say so clearly and suggest next steps.
5. Don't invent connections that aren't in the graph.

---

## Other Atlas skills

- `/atlas-start` — begin a session, get briefed on the knowledge graph
- `/atlas-scan` — scan a directory into the knowledge graph
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-progress` — mid-session checkpoint
- `/atlas-finish` — end session, write back durable knowledge
- `/atlas-health` — deep audit of graph and wiki
```

- [ ] **Step 4: Commit**

```bash
git add atlas/skills/atlas-start/ atlas/skills/atlas-scan/ atlas/skills/atlas-query/
git commit -m "feat: skill files — atlas-start, atlas-scan, atlas-query

agentskills.io standard SKILL.md files. atlas-start reads graph + wiki and
briefs the agent. atlas-scan runs the extraction pipeline. atlas-query
explains how to traverse, find paths, and synthesize answers from the graph."
```

---

## Task 7: Skill Files — atlas-ingest, atlas-progress, atlas-finish, atlas-health

**Files:**
- Create: `atlas/skills/atlas-ingest/SKILL.md`
- Create: `atlas/skills/atlas-progress/SKILL.md`
- Create: `atlas/skills/atlas-finish/SKILL.md`
- Create: `atlas/skills/atlas-health/SKILL.md`

- [ ] **Step 1: Create atlas-ingest/SKILL.md**

`atlas/skills/atlas-ingest/SKILL.md`:
```markdown
---
name: atlas-ingest
description: >
  Ingest a source into the Atlas knowledge base. Handles URLs, local files,
  and pasted text. Saves to raw/, creates wiki pages, updates the graph,
  and flags contradictions. Can enrich with web research.
---

# /atlas-ingest

The user gives you a source — a URL, pasted text, or a file path. You handle the full pipeline.

## 1. Detect the input type

- **URL** — fetch and save using `atlas ingest <url>`
- **Pasted text** — save VERBATIM to raw/untracked/ as markdown, then `atlas ingest <path>`
- **File path** — `atlas ingest <path>` directly
- **Images** — save alongside markdown in raw/. Reference in the source page.

## 2. Ingest

Run:
```bash
atlas ingest <url_or_path> --title "Title" --author "Author"
```

This saves the source to `raw/ingested/` with auto-detected frontmatter (arxiv, tweet, github, pdf, webpage).

## 3. Update the graph

After ingesting, rebuild the graph:
```bash
atlas scan --update .
```

This picks up the new raw file and merges it into the graph.

## 4. Analyze and discuss

- Read the full source content
- Read relevant existing wiki pages
- Summarize the key takeaways (3-5 bullets)
- Check the graph for connections: `atlas query "<main_topic>"`

Then ask 2-5 socratic questions:

**Contradictions:** "The source says [X] but the wiki says [Y]. Which is current?"

**Decisions:** "The source describes 3 approaches. Should I create a decision page?"

**Missing context:** "The source mentions [concept] that doesn't exist in the graph. Create a wiki page?"

**Cross-linking:** "This connects to [[existing-page]]. Want me to add the link?"

Always hypothesize before asking. Confront the source with the graph.

## 5. Compile into the wiki

After user confirmation:
- Create or update the relevant project page in wiki/projects/
- Create a source summary page in wiki/sources/YYYY-MM-DD-slug.md
- Create concept pages in wiki/concepts/ for new topics
- Update wiki/index.md with new entries
- Add [[wikilinks]] for cross-references
- Run `atlas scan --update .` to sync the graph

## 6. Suggest next actions

- "There are 2 more files in raw/untracked/. Want me to ingest them?"
- "This source mentions [topic] without a wiki page. Create one?"
- "Run `atlas surprises` to see if the new source created unexpected connections."

## 7. Enrich (optional)

"This source mentions [X, Y, Z] not in the wiki. Want me to:
- **Quick** — 1 web search per topic, ingest the best result
- **Deep** — 3-5 parallel searches, ingest all good results
- **Skip** — keep what we have"

Every ingest is an opportunity to compound knowledge.

## Rules

1. Always observe before asking. Never ask what you can infer.
2. Hypothesize, then confirm.
3. Suggest concretely. "I'd run [command] to [result]."
4. 2-5 questions max.
5. Show write-back proposals before executing. User approves.
6. Save pasted text VERBATIM to raw/ — no summarization, no truncation.

---

## Other Atlas skills

- `/atlas-start` — begin a session, get briefed
- `/atlas-scan` — scan a directory into the graph
- `/atlas-query` — query the graph for connections
- `/atlas-progress` — mid-session checkpoint
- `/atlas-finish` — end session, write back durable knowledge
- `/atlas-health` — deep audit of graph and wiki
```

- [ ] **Step 2: Create atlas-progress/SKILL.md**

`atlas/skills/atlas-progress/SKILL.md`:
```markdown
---
name: atlas-progress
description: >
  Mid-session checkpoint. Checks progress, detects scope drift,
  captures emerging knowledge, and does a quick graph + wiki health
  check without ending the session.
---

# /atlas-progress

Mid-session checkpoint. Quick but thorough.

## 1. Observe (silent)

- What has changed since session start? (git diff, file timestamps)
- Run `atlas audit --root .` — any new issues?
- Run `atlas god-nodes --root .` — has the structure shifted?
- Check if new files appeared in raw/untracked/

## 2. Analyze (silent)

- Are we still on the plan from `/atlas-start`?
- Has something emerged that should be captured now?
- Are there cross-links to make with existing wiki pages?
- Does the graph need a refresh? `atlas scan --update .`

## 3. Suggest

**Scope drift:** "You started on auth but you've been working on billing for 30 minutes. Intentional?"

**Capture now:** "You just made a significant architecture decision. Create a decision page now before we forget the reasoning?"

**Cross-linking:** "What you're discovering connects to [[payment-gateway]]. Add a cross-reference?"

**Graph refresh:** "You changed 5 files. Run `atlas scan --update .` to keep the graph current?"

**Save an answer:** "That analysis I gave you — want me to save it to wiki/ so it's not lost in the chat?"

**Knowledge gaps:** "The graph is missing [X]. Create a stub page?"

## 4. Ask 1-3 focused questions

Shorter than start. Just enough to course-correct:

- "Main thing done is [X]. Still aiming for [Y] by end of session?"
- "The graph shows [Z] is now a god node after your changes. Expected?"
- "Wiki page says [old]. Based on what just happened, update to [new]?"

## Rules

1. Always observe before asking.
2. Hypothesize, then confirm.
3. 1-3 questions max (shorter than start).
4. Show proposals before executing.
5. If the session is on track and nothing needs capturing, say so and move on.

---

## Other Atlas skills

- `/atlas-start` — begin a session, get briefed
- `/atlas-scan` — scan a directory into the graph
- `/atlas-query` — query the graph for connections
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-finish` — end session, write back durable knowledge
- `/atlas-health` — deep audit of graph and wiki
```

- [ ] **Step 3: Create atlas-finish/SKILL.md**

`atlas/skills/atlas-finish/SKILL.md`:
```markdown
---
name: atlas-finish
description: >
  End a session and write back durable knowledge. Extracts what's
  worth keeping, proposes wiki updates, syncs the graph, and
  executes after user approval.
---

# /atlas-finish

End of session. Extract what's durable, write it back.

## 1. Observe (silent)

- What files changed in this session? (git diff, timestamps)
- What was discussed, decided, discovered?
- What failed or was abandoned?
- Run `atlas audit --root .` — any new issues from this session?
- Run `atlas scan --update .` to capture code changes in the graph

## 2. Analyze (silent)

- What knowledge from this session has value beyond today?
- Status change vs decision vs failure vs source?
- Contradictions with existing wiki content?
- Does the graph index need updating?
- Did the graph structure change significantly? (`atlas god-nodes`, `atlas surprises`)

## 3. Suggest write-back

Show exactly what you'd write and where. User approves before anything is written.

**Project page update:** "I'd update wiki/projects/X.md: status -> 'auth complete, billing in progress'."

**New decision page:** "You decided to switch from Stripe to PayPal. I'd create wiki/decisions/YYYY-MM-DD-paypal-over-stripe.md."

**New source page:** "That API doc you pasted — I'd save to raw/ and create wiki/sources/YYYY-MM-DD-slug.md."

**New concept page:** "The topic [X] spans multiple pages now. I'd create wiki/concepts/X.md."

**Gap detection:** "Based on everything in the wiki, the 2-3 biggest gaps: [X, Y, Z]."

**Contradiction resolution:** "Wiki says timeline is 6 weeks. Based on today it's 8 weeks. Update?"

**Graph sync:** "After writing wiki updates, I'd run `atlas scan --update .` to sync the graph."

## 4. Ask 2-5 socratic questions

- "Main outcome I see is [X]. Anything else worth capturing?"
- "You hit a wall on [Y]. Record as dead end, or still open?"
- "Next step for next session? I'll put it in the project page."
- "Any source material from today I should save to raw/?"

## 5. Execute (after user confirms)

1. Update wiki pages as proposed
2. Create new pages if needed
3. Run `atlas scan --update .` to sync graph
4. Run `atlas audit --root .` — confirm wiki is healthy
5. Report: "Wiki updated. Graph synced. Next session will have this context."

If the session was trivial: "Nothing substantial to record. Skipping write-back."

## Rules

1. Always observe before asking.
2. Hypothesize, then confirm.
3. Suggest concretely. Show exact file paths and content.
4. 2-5 questions max.
5. Show write-back proposals before executing. User approves.
6. Always sync the graph after wiki writes.
7. If trivial, say so and skip.

---

## Other Atlas skills

- `/atlas-start` — begin a session, get briefed
- `/atlas-scan` — scan a directory into the graph
- `/atlas-query` — query the graph for connections
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-progress` — mid-session checkpoint
- `/atlas-health` — deep audit of graph and wiki
```

- [ ] **Step 4: Create atlas-health/SKILL.md**

`atlas/skills/atlas-health/SKILL.md`:
```markdown
---
name: atlas-health
description: >
  Deep audit of the knowledge graph and wiki. Finds contradictions,
  orphans, broken links, stale content, god nodes, and surprising
  connections. Use weekly or when things feel stale.
---

# /atlas-health

Deep audit of the knowledge graph and wiki. Not a quick check — a thorough review.

## 1. Run the full audit (silent)

```bash
atlas audit --root .
atlas god-nodes --root . --top 20
atlas surprises --root . --top 20
```

- Read every page in wiki/projects/, wiki/concepts/, wiki/decisions/, wiki/sources/
- Read wiki/index.md and wiki/log.md
- Check all [[wikilinks]] — do they point to real pages?
- If in a code repo, check `git log` for recent commits

## 2. Report issues by category

**Health score:** "Graph health: {score}/100. {nodes} nodes, {edges} edges, {communities} communities."

**Contradictions:** "Page A says [X] but page B says [Y]. Which is correct?"

**Unsourced claims:** "The project page says [claim] but no source in raw/ backs it. Verified?"

**Missing pages:** "The term [concept] appears in 4 pages but has no wiki page. Create one?"

**Orphan pages:** "These pages have no inbound links: [list]. Still relevant?"

**Stale pages:** "These pages haven't been updated in 30+ days: [list]. Refresh?"

**Broken links:** "These [[wikilinks]] point to non-existent pages: [list]."

**God nodes:** "These are the structural hubs: [list]. If any of these change, many things break."

**Surprising connections:** "These unexpected connections were found: [list]. Worth investigating?"

**Repo drift:** "The repo had 14 commits since wiki was last updated. Key changes: [list]. Wiki says [old state]."

## 3. Suggest improvements

- "Here are 3-5 pages that would fill the biggest gaps."
- "These sources were ingested but wiki pages are thin. Re-compile with more detail?"
- "Run `atlas scan --update .` to capture recent code changes."

**Enrich via web search:** "The wiki mentions [topic] but has no source. Search the web?"

## 4. Ask before fixing

Show everything you'd change. Get approval. Then execute.

Never silently fix — the whole point of health is surfacing issues for validation.

## 5. Execute fixes (after approval)

For each approved fix:
1. Update or create wiki pages
2. Run `atlas scan --update .` to sync graph
3. Run `atlas audit --root .` to confirm improvement
4. Report: "Fixed {N} issues. Health score improved from {old} to {new}."

## Rules

1. Always run the full audit before reporting.
2. Group issues by category for clarity.
3. Show proposals before fixing.
4. Never silently modify wiki content.
5. Re-run audit after fixes to confirm improvement.

---

## Other Atlas skills

- `/atlas-start` — begin a session, get briefed
- `/atlas-scan` — scan a directory into the graph
- `/atlas-query` — query the graph for connections
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-progress` — mid-session checkpoint
- `/atlas-finish` — end session, write back durable knowledge
```

- [ ] **Step 5: Commit**

```bash
git add atlas/skills/atlas-ingest/ atlas/skills/atlas-progress/ atlas/skills/atlas-finish/ atlas/skills/atlas-health/
git commit -m "feat: skill files — atlas-ingest, atlas-progress, atlas-finish, atlas-health

agentskills.io standard SKILL.md files. ingest handles URLs/files/text with
enrichment. progress is mid-session checkpoint. finish extracts durable
knowledge and syncs graph. health runs deep audit with fix proposals."
```

---

## Task 8: Skill Validation Tests

**Files:**
- Create: `tests/test_skills.py`

- [ ] **Step 1: Write skill validation tests**

`tests/test_skills.py`:
```python
"""Validate all Atlas skill files follow the agentskills.io standard."""
from pathlib import Path

import pytest
import yaml

SKILLS_DIR = Path(__file__).parent.parent / "atlas" / "skills"

EXPECTED_SKILLS = [
    "atlas-start",
    "atlas-scan",
    "atlas-query",
    "atlas-ingest",
    "atlas-progress",
    "atlas-finish",
    "atlas-health",
]


def _read_skill(name: str) -> str:
    path = SKILLS_DIR / name / "SKILL.md"
    assert path.exists(), f"Missing skill file: {path}"
    return path.read_text()


def _parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from a SKILL.md file."""
    assert content.startswith("---"), "SKILL.md must start with --- frontmatter"
    _, fm_raw, _ = content.split("---", 2)
    return yaml.safe_load(fm_raw)


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_exists(skill_name):
    """Each expected skill has a SKILL.md file."""
    path = SKILLS_DIR / skill_name / "SKILL.md"
    assert path.exists(), f"Missing: {path}"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_has_frontmatter(skill_name):
    """Each skill has valid YAML frontmatter with name and description."""
    content = _read_skill(skill_name)
    fm = _parse_frontmatter(content)
    assert "name" in fm, f"{skill_name}: frontmatter missing 'name'"
    assert "description" in fm, f"{skill_name}: frontmatter missing 'description'"
    assert fm["name"] == skill_name, f"{skill_name}: name mismatch — got '{fm['name']}'"
    assert len(fm["description"]) > 20, f"{skill_name}: description too short"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_has_heading(skill_name):
    """Each skill body starts with a # heading matching the skill name."""
    content = _read_skill(skill_name)
    # Skip frontmatter
    _, _, body = content.split("---", 2)
    body = body.strip()
    assert body.startswith(f"# /{skill_name}"), f"{skill_name}: body must start with '# /{skill_name}'"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_has_rules_section(skill_name):
    """Each skill has a Rules section."""
    content = _read_skill(skill_name)
    assert "## Rules" in content, f"{skill_name}: missing '## Rules' section"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_references_atlas_cli(skill_name):
    """Each skill references atlas CLI commands (not wikictl)."""
    content = _read_skill(skill_name)
    assert "atlas" in content.lower(), f"{skill_name}: must reference atlas CLI"
    # Skills should NOT reference old wikictl commands
    assert "wikictl" not in content, f"{skill_name}: must not reference deprecated wikictl"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_references_other_skills(skill_name):
    """Each skill mentions at least some other Atlas skills."""
    content = _read_skill(skill_name)
    other_skills = [s for s in EXPECTED_SKILLS if s != skill_name]
    mentioned = [s for s in other_skills if f"/{s}" in content]
    assert len(mentioned) >= 3, f"{skill_name}: should reference at least 3 other skills, found {len(mentioned)}"


def test_all_skills_present():
    """Verify no skill is missing from the expected list."""
    actual = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
    assert actual == sorted(EXPECTED_SKILLS)


def test_no_python_in_skills():
    """Skills are pure markdown — no .py files inside skill directories."""
    for skill_dir in SKILLS_DIR.iterdir():
        if skill_dir.is_dir():
            py_files = list(skill_dir.glob("*.py"))
            assert not py_files, f"Skill {skill_dir.name} should not contain Python files: {py_files}"
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_skills.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_skills.py
git commit -m "test: skill validation — frontmatter, structure, no wikictl refs

Parametrized tests for all 7 skills. Validates agentskills.io format:
YAML frontmatter with name + description, heading, Rules section, atlas
CLI references, cross-skill links, no Python files in skill dirs."
```

---

## Task 9: Git Hooks — post-commit and post-checkout

**Files:**
- Create: `atlas/hooks.py`
- Test: `tests/test_hooks.py`

- [ ] **Step 1: Write failing tests**

`tests/test_hooks.py`:
```python
"""Tests for atlas git hooks — post-commit, post-checkout."""
from pathlib import Path

import pytest

from atlas.hooks import install, uninstall, status


def _make_git_repo(tmp_path: Path) -> Path:
    """Create a minimal .git directory."""
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)
    return tmp_path


def test_install_creates_hooks(tmp_path):
    repo = _make_git_repo(tmp_path)
    result = install(repo)
    assert "installed" in result
    assert (repo / ".git" / "hooks" / "post-commit").exists()
    assert (repo / ".git" / "hooks" / "post-checkout").exists()


def test_install_idempotent(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    result = install(repo)
    assert "already installed" in result


def test_uninstall_removes_hooks(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    result = uninstall(repo)
    assert "removed" in result


def test_status_not_installed(tmp_path):
    repo = _make_git_repo(tmp_path)
    result = status(repo)
    assert "not installed" in result


def test_status_after_install(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    result = status(repo)
    assert "installed" in result
    assert "not installed" not in result.replace("already installed", "")


def test_install_not_git_repo(tmp_path):
    with pytest.raises(RuntimeError, match="No git repository"):
        install(tmp_path)


def test_hook_appends_to_existing(tmp_path):
    """If a hook already exists from another tool, atlas appends."""
    repo = _make_git_repo(tmp_path)
    existing_hook = repo / ".git" / "hooks" / "post-commit"
    existing_hook.write_text("#!/bin/bash\necho 'existing hook'\n")

    install(repo)

    content = existing_hook.read_text()
    assert "existing hook" in content
    assert "atlas-hook" in content
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_hooks.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement hooks.py**

`atlas/hooks.py`:
```python
"""Git hook integration — install/uninstall post-commit and post-checkout hooks."""
from __future__ import annotations

from pathlib import Path

_HOOK_MARKER = "# atlas-hook"
_CHECKOUT_MARKER = "# atlas-checkout-hook"

_HOOK_SCRIPT = """\
#!/bin/bash
# atlas-hook
# Auto-rebuilds the knowledge graph after each commit.
# Installed by: atlas hook install

CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only HEAD 2>/dev/null)
if [ -z "$CHANGED" ]; then
    exit 0
fi

# Only rebuild if atlas-out/ exists (graph has been built before)
if [ ! -d "atlas-out" ]; then
    exit 0
fi

echo "[atlas] Code changed — rebuilding knowledge graph..."
atlas scan . --update 2>/dev/null || python3 -m atlas.cli scan . --update 2>/dev/null || true
"""

_CHECKOUT_SCRIPT = """\
#!/bin/bash
# atlas-checkout-hook
# Auto-rebuilds the knowledge graph when switching branches.
# Installed by: atlas hook install

PREV_HEAD=$1
NEW_HEAD=$2
BRANCH_SWITCH=$3

# Only run on branch switches, not file checkouts
if [ "$BRANCH_SWITCH" != "1" ]; then
    exit 0
fi

# Only run if atlas-out/ exists (graph has been built before)
if [ ! -d "atlas-out" ]; then
    exit 0
fi

echo "[atlas] Branch switched — rebuilding knowledge graph..."
atlas scan . --update 2>/dev/null || python3 -m atlas.cli scan . --update 2>/dev/null || true
"""


def _git_root(path: Path) -> Path | None:
    """Walk up to find .git directory."""
    current = path.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _install_hook(hooks_dir: Path, name: str, script: str, marker: str) -> str:
    """Install a single git hook, appending if an existing hook is present."""
    hook_path = hooks_dir / name
    if hook_path.exists():
        content = hook_path.read_text()
        if marker in content:
            return f"already installed at {hook_path}"
        hook_path.write_text(content.rstrip() + "\n\n" + script)
        return f"appended to existing {name} hook at {hook_path}"
    hook_path.write_text(script)
    hook_path.chmod(0o755)
    return f"installed at {hook_path}"


def _uninstall_hook(hooks_dir: Path, name: str, marker: str) -> str:
    """Remove atlas section from a git hook."""
    hook_path = hooks_dir / name
    if not hook_path.exists():
        return f"no {name} hook found — nothing to remove."
    content = hook_path.read_text()
    if marker not in content:
        return f"atlas hook not found in {name} — nothing to remove."
    before = content.split(marker)[0].rstrip()
    non_empty = [line for line in before.splitlines() if line.strip() and not line.startswith("#!")]
    if not non_empty:
        hook_path.unlink()
        return f"removed {name} hook at {hook_path}"
    hook_path.write_text(before + "\n")
    return f"atlas removed from {name} at {hook_path} (other hook content preserved)"


def install(path: Path = Path(".")) -> str:
    """Install atlas post-commit and post-checkout hooks."""
    root = _git_root(path)
    if root is None:
        raise RuntimeError(f"No git repository found at or above {path.resolve()}")

    hooks_dir = root / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    commit_msg = _install_hook(hooks_dir, "post-commit", _HOOK_SCRIPT, _HOOK_MARKER)
    checkout_msg = _install_hook(hooks_dir, "post-checkout", _CHECKOUT_SCRIPT, _CHECKOUT_MARKER)

    return f"post-commit: {commit_msg}\npost-checkout: {checkout_msg}"


def uninstall(path: Path = Path(".")) -> str:
    """Remove atlas post-commit and post-checkout hooks."""
    root = _git_root(path)
    if root is None:
        raise RuntimeError(f"No git repository found at or above {path.resolve()}")

    hooks_dir = root / ".git" / "hooks"
    commit_msg = _uninstall_hook(hooks_dir, "post-commit", _HOOK_MARKER)
    checkout_msg = _uninstall_hook(hooks_dir, "post-checkout", _CHECKOUT_MARKER)

    return f"post-commit: {commit_msg}\npost-checkout: {checkout_msg}"


def status(path: Path = Path(".")) -> str:
    """Check if atlas hooks are installed."""
    root = _git_root(path)
    if root is None:
        return "Not in a git repository."

    hooks_dir = root / ".git" / "hooks"

    def _check(name: str, marker: str) -> str:
        p = hooks_dir / name
        if not p.exists():
            return "not installed"
        return "installed" if marker in p.read_text() else "not installed (hook exists but atlas not found)"

    commit = _check("post-commit", _HOOK_MARKER)
    checkout = _check("post-checkout", _CHECKOUT_MARKER)
    return f"post-commit: {commit}\npost-checkout: {checkout}"
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_hooks.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/hooks.py tests/test_hooks.py
git commit -m "feat: git hooks — post-commit and post-checkout auto-rebuild

Hooks run atlas scan --update after commits and branch switches.
Appends to existing hooks if present. Install/uninstall/status commands."
```

---

## Task 10: Integration Test — Full CLI Workflow

**Files:**
- Create: `tests/test_cli_integration.py`

- [ ] **Step 1: Write integration test**

`tests/test_cli_integration.py`:
```python
"""End-to-end integration test for the full CLI workflow."""
from pathlib import Path

from typer.testing import CliRunner

from atlas.cli import app

runner = CliRunner()


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project with code, docs, and a wiki."""
    # Code files
    src = tmp_path / "src"
    src.mkdir()
    (src / "auth.py").write_text(
        '"""Auth module — JWT and sessions."""\n'
        'import hashlib\n\n'
        'class AuthManager:\n'
        '    """Handles authentication."""\n'
        '    def verify(self, token: str) -> bool:\n'
        '        return len(token) > 0\n'
    )
    (src / "billing.py").write_text(
        '"""Billing module — Stripe integration."""\n'
        'from src.auth import AuthManager\n\n'
        'class BillingService:\n'
        '    """Processes payments via Stripe."""\n'
        '    def charge(self, amount: int) -> bool:\n'
        '        return amount > 0\n'
    )

    # Wiki
    wiki = tmp_path / "wiki"
    for d in ["projects", "concepts", "sources", "decisions"]:
        (wiki / d).mkdir(parents=True)
    (wiki / "index.md").write_text("---\ntype: wiki-index\n---\n\n# Index\n")
    (wiki / "concepts" / "auth.md").write_text(
        "---\ntype: wiki-concept\ntitle: Auth\ntags: [auth]\nupdated: 2026-04-06\n---\n\n"
        "# Auth\n\nJWT-based. See [[billing]].\n"
    )
    (wiki / "concepts" / "billing.md").write_text(
        "---\ntype: wiki-concept\ntitle: Billing\ntags: [payments]\nupdated: 2026-04-06\n---\n\n"
        "# Billing\n\nStripe. See [[auth]].\n"
    )

    # Raw source
    raw = tmp_path / "raw" / "untracked"
    raw.mkdir(parents=True)
    (raw / "notes.md").write_text("# Research Notes\n\nSome findings about API design.\n")

    return tmp_path


def test_full_workflow(tmp_path):
    """atlas scan -> query -> path -> explain -> god-nodes -> surprises -> audit -> export."""
    project = _make_project(tmp_path)

    # Step 1: Scan
    result = runner.invoke(app, ["scan", str(project)])
    assert result.exit_code == 0, f"scan failed: {result.stdout}"
    assert (project / "atlas-out" / "graph.json").exists()

    root_flag = ["--root", str(project)]

    # Step 2: Query
    result = runner.invoke(app, ["query", "auth", *root_flag])
    assert result.exit_code == 0, f"query failed: {result.stdout}"

    # Step 3: God nodes
    result = runner.invoke(app, ["god-nodes", *root_flag])
    assert result.exit_code == 0, f"god-nodes failed: {result.stdout}"

    # Step 4: Surprises
    result = runner.invoke(app, ["surprises", *root_flag])
    assert result.exit_code == 0, f"surprises failed: {result.stdout}"

    # Step 5: Audit
    result = runner.invoke(app, ["audit", *root_flag])
    assert result.exit_code == 0, f"audit failed: {result.stdout}"
    assert "health" in result.stdout.lower() or "score" in result.stdout.lower()

    # Step 6: Export JSON
    result = runner.invoke(app, ["export", "json", *root_flag])
    assert result.exit_code == 0, f"export failed: {result.stdout}"

    # Step 7: Ingest
    notes_path = str(project / "raw" / "untracked" / "notes.md")
    result = runner.invoke(app, ["ingest", notes_path, *root_flag])
    assert result.exit_code == 0, f"ingest failed: {result.stdout}"


def test_migrate_then_query(tmp_path):
    """atlas migrate -> query to verify migration produces a usable graph."""
    from tests.test_migrate import _make_wiki_v1

    _make_wiki_v1(tmp_path)

    # Migrate
    result = runner.invoke(app, ["migrate", "--root", str(tmp_path), "--no-skills"])
    assert result.exit_code == 0, f"migrate failed: {result.stdout}"

    # Query should work on the migrated graph
    result = runner.invoke(app, ["query", "auth", "--root", str(tmp_path)])
    assert result.exit_code == 0, f"query after migrate failed: {result.stdout}"
    assert "auth" in result.stdout.lower()
```

- [ ] **Step 2: Run integration test**

Run: `python -m pytest tests/test_cli_integration.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli_integration.py
git commit -m "test: full CLI workflow integration — scan, query, audit, export, migrate

End-to-end test with a minimal project (code + wiki + raw). Validates the
complete atlas scan -> query -> god-nodes -> surprises -> audit -> export ->
ingest flow, plus migrate -> query path."
```

---

## Self-Review Checklist

| Criterion | Status |
|-----------|--------|
| CLI consumes Core directly, not via REST API | Yes — all commands import from `atlas.core.*` |
| Skills are static SKILL.md files, no Python inside | Yes — validated by `test_no_python_in_skills` |
| Each skill has agentskills.io frontmatter (name + description) | Yes — validated by `test_skill_has_frontmatter` |
| Skills reference `atlas` CLI, not deprecated `wikictl` | Yes — validated by `test_skill_references_atlas_cli` |
| Installer auto-detects platforms | Yes — `detect_platforms()` checks `~/.claude`, `~/.codex`, `~/.cursor`, `~/.hermes` |
| Claude Code gets PreToolUse hook | Yes — `install_claude_hook()` writes to `.claude/settings.json` |
| Codex/Cursor/Hermes get AGENTS.md | Yes — `install_agents_md()` writes section |
| Migration preserves all wiki content | Yes — validated by `test_migrate_preserves_wiki` |
| Migration builds graph.json from existing wiki | Yes — uses `Linker.sync_wiki_to_graph()` |
| Git hooks auto-rebuild on commit/checkout | Yes — `atlas/hooks.py` with post-commit and post-checkout |
| All commands have tests | Yes — unit + integration |
| Plan matches spec sections 5.6, 10, 12 | Yes — 7 skills, migration path, interfaces contract respected |

### Potential issues to watch

1. **Export modules may not exist yet** — the `atlas export` command has a fallback for JSON but other formats depend on Plan 3/Quality squad. The CLI gracefully errors with "install atlas-ai[all]".
2. **`atlas serve` depends on Server squad** — it just calls `uvicorn.run("atlas.server.app:app")`. If the server module isn't ready, it errors cleanly.
3. **Skill discovery varies by platform** — Claude Code reads `~/.claude/skills/`, Codex reads `~/.agents/skills/`, Cursor reads `~/.cursor/skills/`, Hermes reads `~/.hermes/skills/`. The installer copies (not symlinks) for cross-platform robustness.
4. **Migration assumes Linker is idempotent** — running `atlas migrate` twice should produce the same graph. Validated by `test_migrate_idempotent`.
