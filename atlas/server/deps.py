"""Shared dependencies — engine singletons and event bus for the server layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from atlas.core.analyzer import Analyzer
from atlas.core.cache import CacheEngine
from atlas.core.graph import GraphEngine
from atlas.core.ingest import IngestEngine
from atlas.core.linker import Linker
from atlas.core.scanner import Scanner
from atlas.core.storage import LocalStorage
from atlas.core.wiki import WikiEngine


@dataclass
class EngineSet:
    """All Core engine instances needed by the server."""

    root: Path
    storage: LocalStorage
    graph: GraphEngine
    wiki: WikiEngine
    linker: Linker
    analyzer: Analyzer
    scanner: Scanner
    cache: CacheEngine
    ingest: IngestEngine

    @property
    def graph_path(self) -> Path:
        return self.root / "wiki" / "graph.json"

    def save_graph(self) -> None:
        """Persist the in-memory graph to disk."""
        self.graph.save(self.graph_path)

    def load_graph(self) -> None:
        """Load graph from disk if it exists."""
        if self.graph_path.exists():
            self.graph._g = GraphEngine.load(self.graph_path)._g


def create_engine_set(root: Path | str) -> EngineSet:
    """Factory: create all Core engine instances from a root directory."""
    root = Path(root)
    storage = LocalStorage(root=root)
    cache = CacheEngine(storage)
    graph = GraphEngine()
    wiki = WikiEngine(storage)
    linker = Linker(wiki=wiki, graph=graph)
    analyzer = Analyzer(graph=graph, wiki=wiki)
    scanner = Scanner(storage=storage, cache=cache)
    ingest = IngestEngine(storage)

    return EngineSet(
        root=root,
        storage=storage,
        graph=graph,
        wiki=wiki,
        linker=linker,
        analyzer=analyzer,
        scanner=scanner,
        cache=cache,
        ingest=ingest,
    )


class EventBus:
    """Simple synchronous pub/sub for intra-process events.

    Events:
        - wiki.changed   — a wiki page was created/updated/deleted
        - graph.updated  — the graph was modified (scan, linker sync)
        - scan.completed — a scan operation finished
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable[[dict[str, Any]], None]) -> None:
        self._handlers.setdefault(event, []).append(handler)

    def unsubscribe(self, event: str, handler: Callable) -> None:
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h is not handler]

    def emit(self, event: str, data: dict[str, Any] | None = None) -> None:
        for handler in self._handlers.get(event, []):
            handler(data or {})
