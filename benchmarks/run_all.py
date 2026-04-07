"""Benchmark suite — scan, query, graph merge, wiki sync."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

from atlas.core.graph import GraphEngine
from atlas.core.models import Node, Edge, Extraction
from atlas.core.scanner import Scanner
from atlas.core.storage import LocalStorage
from atlas.core.wiki import WikiEngine
from atlas.core.linker import Linker


def _make_test_corpus(tmp: Path, n_files: int = 20) -> int:
    """Create a realistic test corpus. Returns file count."""
    src = tmp / "src"
    src.mkdir()
    for i in range(n_files):
        content = f"# Module {i}\ndef func_{i}():\n    return {i}\n"
        (src / f"module_{i:03d}.py").write_text(content)
    return n_files


def bench_scan(n_files: int = 20) -> dict:
    """Benchmark: scan N files, measure time."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        file_count = _make_test_corpus(tmp, n_files)

        storage = LocalStorage(root=tmp)
        scanner = Scanner(storage=storage)

        start = time.perf_counter()
        extraction = scanner.scan(tmp)
        elapsed = time.perf_counter() - start

        return {
            "files_scanned": file_count,
            "time_total_ms": elapsed * 1000,
            "time_per_file_ms": (elapsed * 1000) / max(file_count, 1),
            "nodes_extracted": len(extraction.nodes),
            "edges_extracted": len(extraction.edges),
        }


def bench_graph_merge(n_nodes: int = 100) -> dict:
    """Benchmark: merge N nodes into a graph."""
    graph = GraphEngine()
    nodes = [Node(id=f"n_{i}", label=f"Node {i}", type="code", source_file=f"file_{i}.py")
             for i in range(n_nodes)]
    edges = [Edge(source=f"n_{i}", target=f"n_{(i+1) % n_nodes}", relation="calls")
             for i in range(n_nodes)]
    extraction = Extraction(nodes=nodes, edges=edges)

    start = time.perf_counter()
    graph.merge(extraction)
    elapsed = time.perf_counter() - start

    return {
        "nodes_merged": n_nodes,
        "edges_merged": n_nodes,
        "time_ms": elapsed * 1000,
        "time_per_1k_nodes_ms": (elapsed * 1000 / max(n_nodes, 1)) * 1000,
    }


def bench_query(n_nodes: int = 500, depth: int = 5) -> dict:
    """Benchmark: BFS query on a graph."""
    graph = GraphEngine()
    for i in range(n_nodes):
        graph.set_node(f"n_{i}", label=f"Node {i}", type="code", source_file=f"file_{i}.py")
        for j in range(3):
            target = f"n_{(i + j + 1) % n_nodes}"
            graph.set_edge(f"n_{i}", target, relation="calls", confidence="EXTRACTED")

    p95_times = []
    for _ in range(10):
        start = time.perf_counter()
        result = graph.query("n_0", mode="bfs", depth=depth)
        elapsed = time.perf_counter() - start
        p95_times.append(elapsed * 1000)

    p95_times.sort()
    p95 = p95_times[int(len(p95_times) * 0.95)] if p95_times else 0

    return {
        "graph_nodes": n_nodes,
        "graph_edges": n_nodes * 3,
        "p95_ms": p95,
        "avg_ms": sum(p95_times) / max(len(p95_times), 1),
        "min_ms": min(p95_times) if p95_times else 0,
        "max_ms": max(p95_times) if p95_times else 0,
    }


def bench_wiki_sync(n_pages: int = 20) -> dict:
    """Benchmark: wiki <-> graph sync."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        wiki_dir = tmp / "wiki"
        for d in ["projects", "concepts", "sources", "decisions"]:
            (wiki_dir / d).mkdir(parents=True)
        (wiki_dir / "index.md").write_text("# Index\n")
        (wiki_dir / "log.md").write_text("# Log\n")
        for i in range(n_pages):
            (wiki_dir / "concepts" / f"concept_{i}.md").write_text(
                f"---\ntype: wiki-concept\ntitle: Concept {i}\n---\n\n# Concept {i}\n\nSee [[concept_{(i+1) % n_pages}]].\n"
            )

        storage = LocalStorage(root=tmp)
        wiki = WikiEngine(storage)

        graph = GraphEngine()
        for i in range(n_pages):
            graph.set_node(f"concept_{i}", label=f"Concept {i}", type="wiki-concept", source_file=f"wiki/concepts/concept_{i}.md")

        linker = Linker(wiki=wiki, graph=graph)

        start = time.perf_counter()
        changes = linker.sync_wiki_to_graph()
        suggestions = linker.sync_graph_to_wiki()
        elapsed = time.perf_counter() - start

        return {
            "pages_synced": n_pages,
            "graph_changes": len(changes),
            "suggestions": len(suggestions),
            "time_ms": elapsed * 1000,
            "time_per_page_ms": (elapsed * 1000) / max(n_pages, 1),
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run Atlas benchmarks")
    parser.add_argument("--output", default=None, help="Write results to JSON file")
    args = parser.parse_args()

    print("Running benchmarks...")

    results = {
        "scan": bench_scan(),
        "graph_merge": bench_graph_merge(),
        "query": bench_query(),
        "wiki_sync": bench_wiki_sync(),
    }

    # Print summary
    print(f"\n=== Results ===")
    print(f"Scan:        {results['scan']['time_per_file_ms']:.1f}ms/file ({results['scan']['files_scanned']} files)")
    print(f"Graph merge: {results['graph_merge']['time_ms']:.1f}ms ({results['graph_merge']['nodes_merged']} nodes)")
    print(f"Query p95:   {results['query']['p95_ms']:.1f}ms ({results['query']['graph_nodes']} nodes)")
    print(f"Wiki sync:   {results['wiki_sync']['time_per_page_ms']:.1f}ms/page ({results['wiki_sync']['pages_synced']} pages)")

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults written to {args.output}")

    return results


if __name__ == "__main__":
    main()
