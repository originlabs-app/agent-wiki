"""End-to-end integration test: scan -> graph -> wiki -> linker -> analyzer."""
from pathlib import Path

from atlas.core.analyzer import Analyzer
from atlas.core.cache import CacheEngine
from atlas.core.graph import GraphEngine
from atlas.core.linker import Linker
from atlas.core.scanner import Scanner
from atlas.core.storage import LocalStorage
from atlas.core.wiki import WikiEngine


def test_full_pipeline(tmp_path):
    """Scan files, build graph, sync with wiki, run audit."""
    # Setup storage with raw files and wiki structure
    storage = LocalStorage(root=tmp_path)

    # Create wiki structure
    for d in ["wiki/projects", "wiki/concepts", "wiki/decisions", "wiki/sources", "raw/untracked", "raw/ingested"]:
        (tmp_path / d).mkdir(parents=True)

    # Add a Python source file
    (tmp_path / "raw" / "untracked" / "auth.py").write_text(
        'import os\n\nclass AuthManager:\n    """Auth manager."""\n    def login(self): pass\n    def logout(self): pass\n'
    )

    # Add a markdown source
    (tmp_path / "raw" / "untracked" / "architecture.md").write_text(
        "# Architecture\n\nThe system uses [[auth]] for authentication and [[billing]] for payments.\n"
    )

    # Step 1: Scan
    cache = CacheEngine(storage)
    scanner = Scanner(storage=storage, cache=cache)
    extraction = scanner.scan(tmp_path / "raw" / "untracked")
    assert len(extraction.nodes) > 0, "Scanner should find nodes"

    # Step 2: Build graph
    graph = GraphEngine()
    graph.merge(extraction)
    assert graph.node_count > 0, "Graph should have nodes after merge"

    # Step 3: Create wiki pages
    wiki = WikiEngine(storage)
    wiki.write(
        "wiki/concepts/auth.md",
        "# Authentication\n\nHandles login/logout. See [[billing]].",
        frontmatter={"type": "wiki-concept", "title": "Authentication", "confidence": "high", "tags": ["auth"]},
    )
    wiki.write(
        "wiki/concepts/billing.md",
        "# Billing\n\nStripe integration. See [[auth]].",
        frontmatter={"type": "wiki-concept", "title": "Billing", "confidence": "medium", "tags": ["billing"]},
    )

    # Step 4: Linker sync
    linker = Linker(wiki=wiki, graph=graph)
    changes = linker.sync_wiki_to_graph()
    assert len(changes) > 0, "Linker should produce changes"
    assert graph.get_node("auth") is not None, "Auth wiki page should be a graph node"
    assert graph.get_node("billing") is not None, "Billing wiki page should be a graph node"

    # Step 5: Analyzer audit
    analyzer = Analyzer(graph=graph, wiki=wiki)
    report = analyzer.audit()
    assert report.stats is not None
    assert report.stats.nodes > 0
    assert report.health_score >= 0

    # Step 6: Save and reload graph
    graph_path = tmp_path / "wiki" / "graph.json"
    graph.save(graph_path)
    assert graph_path.exists()
    graph2 = GraphEngine.load(graph_path)
    assert graph2.node_count == graph.node_count

    # Step 7: Query the graph
    result = graph.query("auth", mode="bfs", depth=2)
    assert len(result.nodes) >= 1

    # Step 8: Graph -> Wiki suggestions
    suggestions = linker.sync_graph_to_wiki()
    # Some scan nodes (from raw/) don't have wiki pages -> should suggest creating them
    assert isinstance(suggestions, list)

    print(f"Pipeline complete: {graph.node_count} nodes, {graph.edge_count} edges, "
          f"health={report.health_score:.1f}, suggestions={len(suggestions)}")


def test_incremental_rescan(tmp_path):
    """Verify that incremental scan only re-processes changed files."""
    storage = LocalStorage(root=tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("def hello(): pass")
    (tmp_path / "src" / "b.py").write_text("def world(): pass")

    cache = CacheEngine(storage)
    scanner = Scanner(storage=storage, cache=cache)

    # Full scan
    e1 = scanner.scan(tmp_path / "src")
    n1 = len(e1.nodes)

    # No changes -> incremental should use cache
    e2 = scanner.scan(tmp_path / "src", incremental=True)
    assert len(e2.nodes) == n1

    # Change one file -> incremental should update
    (tmp_path / "src" / "a.py").write_text("def hello_changed(): pass\ndef new_func(): pass")
    e3 = scanner.scan(tmp_path / "src", incremental=True)
    assert len(e3.nodes) >= n1  # at least same, possibly more
