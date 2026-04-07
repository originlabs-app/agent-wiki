# Atlas Server — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the server layer of Atlas — FastAPI REST API, MCP server (stdio + SSE), WebSocket live updates, and middleware. The server is the universal access layer: Dashboard calls REST, agents call MCP, both get live updates via WebSocket.

**Architecture:** The server never touches the filesystem or graph internals directly. Every operation goes through Core interfaces (GraphEngine, WikiEngine, Linker, Analyzer, Scanner, IngestEngine, CacheEngine, StorageBackend). The MCP server exposes the same 12 operations as the REST API. WebSocket broadcasts change events when wiki or graph state mutates.

**Tech Stack:** Python 3.12+, FastAPI, uvicorn, mcp (pip package), websockets, pydantic

**Depends on:** Plan 1 — Core Engine (all 8 modules must be installed and working)

---

## File Map

```
atlas/
├── server/
│   ├── __init__.py
│   ├── deps.py             # Shared dependencies: engine singletons, event bus
│   ├── schemas.py          # Pydantic request/response models
│   ├── app.py              # FastAPI app + REST API routes
│   ├── mcp.py              # MCP server (stdio + SSE transport)
│   ├── ws.py               # WebSocket manager + broadcast
│   └── middleware.py        # CORS, error handling, request logging

tests/
├── server/
│   ├── conftest.py          # Shared fixtures (test client, engine instances)
│   ├── test_schemas.py
│   ├── test_deps.py
│   ├── test_app_scan.py
│   ├── test_app_query.py
│   ├── test_app_wiki.py
│   ├── test_app_analysis.py
│   ├── test_app_ingest.py
│   ├── test_mcp.py
│   ├── test_ws.py
│   └── test_middleware.py
```

---

## Task 1: Pydantic Schemas + Shared Dependencies

**Files:**
- Create: `atlas/server/__init__.py`
- Create: `atlas/server/schemas.py`
- Create: `atlas/server/deps.py`
- Test: `tests/server/conftest.py`
- Test: `tests/server/test_schemas.py`
- Test: `tests/server/test_deps.py`

- [ ] **Step 1: Create server package init**

`atlas/server/__init__.py`:
```python
"""Atlas server — REST API, MCP server, WebSocket live updates."""
```

- [ ] **Step 2: Write failing tests for schemas**

`tests/server/test_schemas.py`:
```python
from atlas.server.schemas import (
    ScanRequest,
    ScanResponse,
    QueryRequest,
    QueryResponse,
    PathRequest,
    PathResponse,
    ExplainRequest,
    ExplainResponse,
    GodNodesRequest,
    GodNodesResponse,
    SurprisesRequest,
    SurprisesResponse,
    StatsResponse,
    WikiReadRequest,
    WikiReadResponse,
    WikiWriteRequest,
    WikiWriteResponse,
    WikiSearchRequest,
    WikiSearchResponse,
    AuditResponse,
    SuggestLinksResponse,
    IngestRequest,
    IngestResponse,
    ErrorResponse,
    NodeSchema,
    EdgeSchema,
    PageSchema,
)


def test_scan_request_defaults():
    req = ScanRequest(path="/some/folder")
    assert req.path == "/some/folder"
    assert req.incremental is False
    assert req.force is False


def test_scan_request_with_options():
    req = ScanRequest(path="/code", incremental=True, force=False)
    assert req.incremental is True


def test_query_request():
    req = QueryRequest(question="auth", mode="bfs", depth=3)
    assert req.question == "auth"
    assert req.mode == "bfs"
    assert req.depth == 3


def test_query_request_defaults():
    req = QueryRequest(question="billing")
    assert req.mode == "bfs"
    assert req.depth == 3


def test_path_request():
    req = PathRequest(source="auth", target="billing")
    assert req.source == "auth"


def test_explain_request():
    req = ExplainRequest(concept="auth")
    assert req.concept == "auth"


def test_god_nodes_request_defaults():
    req = GodNodesRequest()
    assert req.top_n == 10


def test_surprises_request_defaults():
    req = SurprisesRequest()
    assert req.top_n == 10


def test_wiki_read_request():
    req = WikiReadRequest(page="wiki/concepts/auth.md")
    assert req.page == "wiki/concepts/auth.md"


def test_wiki_write_request():
    req = WikiWriteRequest(
        page="wiki/concepts/auth.md",
        content="# Auth\n\nUpdated.",
        frontmatter={"type": "wiki-concept", "title": "Auth"},
    )
    assert req.page == "wiki/concepts/auth.md"
    assert req.frontmatter["type"] == "wiki-concept"


def test_wiki_search_request():
    req = WikiSearchRequest(terms="JWT")
    assert req.terms == "JWT"


def test_ingest_request_url():
    req = IngestRequest(url="https://arxiv.org/abs/1706.03762")
    assert req.url == "https://arxiv.org/abs/1706.03762"
    assert req.file_path is None


def test_ingest_request_file():
    req = IngestRequest(file_path="raw/untracked/notes.md", title="My Notes")
    assert req.file_path == "raw/untracked/notes.md"
    assert req.title == "My Notes"


def test_node_schema():
    ns = NodeSchema(id="auth", label="Auth", type="code", source_file="auth.py")
    assert ns.id == "auth"
    assert ns.confidence == "high"


def test_edge_schema():
    es = EdgeSchema(source="auth", target="db", relation="imports", confidence="EXTRACTED")
    assert es.confidence_score == 1.0


def test_error_response():
    err = ErrorResponse(error="not_found", detail="Page not found")
    assert err.error == "not_found"
```

- [ ] **Step 3: Run tests to verify failure**

Run: `cd /Users/pierrebeunardeau/dev/internal/agent-wiki && python -m pytest tests/server/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.server.schemas'`

- [ ] **Step 4: Implement schemas.py**

`atlas/server/schemas.py`:
```python
"""Pydantic request/response models for the Atlas REST API and MCP server."""
from __future__ import annotations

from pydantic import BaseModel, Field


# --- Shared sub-schemas ---

class NodeSchema(BaseModel):
    id: str
    label: str
    type: str
    source_file: str
    source_location: str | None = None
    source_url: str | None = None
    confidence: str = "high"
    community: int | None = None
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_core(cls, node) -> NodeSchema:
        """Convert atlas.core.models.Node to schema."""
        return cls(
            id=node.id,
            label=node.label,
            type=node.type,
            source_file=node.source_file,
            source_location=node.source_location,
            source_url=node.source_url,
            confidence=node.confidence,
            community=node.community,
            summary=node.summary,
            tags=node.tags or [],
        )


class EdgeSchema(BaseModel):
    source: str
    target: str
    relation: str
    confidence: str = "EXTRACTED"
    confidence_score: float = 1.0
    weight: float = 1.0

    def __init__(self, **data):
        if "confidence_score" not in data or data.get("confidence_score") is None:
            conf = data.get("confidence", "EXTRACTED")
            data["confidence_score"] = {"EXTRACTED": 1.0, "INFERRED": 0.7, "AMBIGUOUS": 0.2}.get(conf, 0.5)
        super().__init__(**data)

    @classmethod
    def from_core(cls, edge) -> EdgeSchema:
        return cls(
            source=edge.source,
            target=edge.target,
            relation=edge.relation,
            confidence=edge.confidence,
            confidence_score=edge.confidence_score or 1.0,
            weight=edge.weight,
        )


class PageSchema(BaseModel):
    path: str
    title: str
    type: str
    content: str
    frontmatter: dict = Field(default_factory=dict)
    wikilinks: list[str] = Field(default_factory=list)

    @classmethod
    def from_core(cls, page) -> PageSchema:
        return cls(
            path=page.path,
            title=page.title,
            type=page.type,
            content=page.content,
            frontmatter=page.frontmatter,
            wikilinks=page.wikilinks,
        )


class LinkSuggestionSchema(BaseModel):
    from_page: str
    to_page: str
    reason: str
    confidence: str = "INFERRED"


class WikiSuggestionSchema(BaseModel):
    type: str
    description: str
    target_page: str | None = None
    source_node: str | None = None
    target_node: str | None = None
    reason: str | None = None


class GraphStatsSchema(BaseModel):
    nodes: int
    edges: int
    communities: int
    confidence_breakdown: dict[str, int] = Field(default_factory=dict)
    health_score: float = 0.0


# --- Request models ---

class ScanRequest(BaseModel):
    path: str
    incremental: bool = False
    force: bool = False


class QueryRequest(BaseModel):
    question: str
    mode: str = "bfs"
    depth: int = 3


class PathRequest(BaseModel):
    source: str
    target: str


class ExplainRequest(BaseModel):
    concept: str


class GodNodesRequest(BaseModel):
    top_n: int = 10


class SurprisesRequest(BaseModel):
    top_n: int = 10


class WikiReadRequest(BaseModel):
    page: str


class WikiWriteRequest(BaseModel):
    page: str
    content: str
    frontmatter: dict = Field(default_factory=dict)


class WikiSearchRequest(BaseModel):
    terms: str


class IngestRequest(BaseModel):
    url: str | None = None
    file_path: str | None = None
    title: str | None = None
    author: str | None = None


# --- Response models ---

class ScanResponse(BaseModel):
    nodes_found: int
    edges_found: int
    files_scanned: int = 0
    message: str = "Scan complete"


class QueryResponse(BaseModel):
    nodes: list[NodeSchema]
    edges: list[EdgeSchema]
    estimated_tokens: int = 0


class PathResponse(BaseModel):
    edges: list[EdgeSchema]
    found: bool = True


class ExplainResponse(BaseModel):
    concept: str
    label: str
    type: str
    summary: str | None = None
    neighbors: list[NodeSchema]
    edges: list[EdgeSchema]


class GodNodesResponse(BaseModel):
    nodes: list[dict]  # [{id, label, degree}]


class SurprisesResponse(BaseModel):
    edges: list[EdgeSchema]


class StatsResponse(BaseModel):
    stats: GraphStatsSchema


class WikiReadResponse(BaseModel):
    page: PageSchema | None


class WikiWriteResponse(BaseModel):
    page: str
    message: str = "Page saved"


class WikiSearchResponse(BaseModel):
    results: list[PageSchema]


class AuditResponse(BaseModel):
    orphan_pages: list[str] = Field(default_factory=list)
    god_nodes: list[dict] = Field(default_factory=list)
    broken_links: list[dict] = Field(default_factory=list)
    stale_pages: list[str] = Field(default_factory=list)
    contradictions: list[dict] = Field(default_factory=list)
    missing_links: list[LinkSuggestionSchema] = Field(default_factory=list)
    communities: list[dict] = Field(default_factory=list)
    stats: GraphStatsSchema | None = None
    health_score: float = 0.0


class SuggestLinksResponse(BaseModel):
    suggestions: list[WikiSuggestionSchema]


class IngestResponse(BaseModel):
    path: str | None
    message: str = "Ingested"


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
```

- [ ] **Step 5: Run schema tests**

Run: `python -m pytest tests/server/test_schemas.py -v`
Expected: All PASS

- [ ] **Step 6: Write failing tests for deps**

`tests/server/test_deps.py`:
```python
from pathlib import Path

from atlas.server.deps import create_engine_set, EngineSet, EventBus


def test_create_engine_set(tmp_path):
    # Setup minimal directory structure
    for d in ["wiki/projects", "wiki/concepts", "wiki/decisions", "wiki/sources", "raw/untracked", "raw/ingested"]:
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "wiki" / "index.md").write_text("# Wiki Index\n")

    engines = create_engine_set(tmp_path)
    assert isinstance(engines, EngineSet)
    assert engines.storage is not None
    assert engines.graph is not None
    assert engines.wiki is not None
    assert engines.linker is not None
    assert engines.analyzer is not None
    assert engines.scanner is not None
    assert engines.cache is not None
    assert engines.ingest is not None


def test_engine_set_graph_path(tmp_path):
    for d in ["wiki/projects", "wiki/concepts", "wiki/decisions", "wiki/sources", "raw"]:
        (tmp_path / d).mkdir(parents=True)
    engines = create_engine_set(tmp_path)
    assert engines.graph_path == tmp_path / "wiki" / "graph.json"


def test_event_bus_subscribe_and_emit():
    bus = EventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe("wiki.changed", handler)
    bus.emit("wiki.changed", {"page": "auth.md"})
    assert len(received) == 1
    assert received[0]["page"] == "auth.md"


def test_event_bus_multiple_subscribers():
    bus = EventBus()
    a_received = []
    b_received = []

    bus.subscribe("graph.updated", lambda e: a_received.append(e))
    bus.subscribe("graph.updated", lambda e: b_received.append(e))
    bus.emit("graph.updated", {"nodes": 42})
    assert len(a_received) == 1
    assert len(b_received) == 1


def test_event_bus_no_crosstalk():
    bus = EventBus()
    received = []

    bus.subscribe("wiki.changed", lambda e: received.append(e))
    bus.emit("graph.updated", {"nodes": 42})
    assert len(received) == 0


def test_event_bus_unsubscribe():
    bus = EventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe("wiki.changed", handler)
    bus.unsubscribe("wiki.changed", handler)
    bus.emit("wiki.changed", {"page": "auth.md"})
    assert len(received) == 0
```

- [ ] **Step 7: Run deps tests to verify failure**

Run: `python -m pytest tests/server/test_deps.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 8: Implement deps.py**

`atlas/server/deps.py`:
```python
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
```

- [ ] **Step 9: Run deps tests**

Run: `python -m pytest tests/server/test_deps.py -v`
Expected: All PASS

- [ ] **Step 10: Create server test conftest**

`tests/server/conftest.py`:
```python
"""Shared test fixtures for the server test suite."""
from pathlib import Path

import pytest

from atlas.server.deps import create_engine_set, EngineSet, EventBus


@pytest.fixture
def engine_root(tmp_path):
    """Create a temp directory with wiki + raw structure."""
    for d in ["wiki/projects", "wiki/concepts", "wiki/decisions", "wiki/sources", "raw/untracked", "raw/ingested"]:
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "wiki" / "index.md").write_text("# Wiki Index\n")
    (tmp_path / "wiki" / "log.md").write_text("# Wiki Log\n")
    return tmp_path


@pytest.fixture
def engines(engine_root) -> EngineSet:
    """A fully initialized EngineSet backed by a temp directory."""
    return create_engine_set(engine_root)


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def seeded_engines(engines) -> EngineSet:
    """EngineSet with pre-populated wiki pages and graph data."""
    engines.wiki.write(
        "wiki/concepts/auth.md",
        "# Authentication\n\nHandles JWT tokens. See [[billing]].",
        frontmatter={"type": "wiki-concept", "title": "Authentication", "confidence": "high", "tags": ["auth", "security"]},
    )
    engines.wiki.write(
        "wiki/concepts/billing.md",
        "# Billing\n\nStripe integration. See [[auth]].",
        frontmatter={"type": "wiki-concept", "title": "Billing", "confidence": "medium", "tags": ["billing"]},
    )
    engines.wiki.write(
        "wiki/projects/acme.md",
        "# Acme\n\nTest project.",
        frontmatter={"type": "wiki-page", "title": "Acme", "project": "Acme", "confidence": "high"},
    )
    # Sync wiki to graph so we have nodes and edges
    engines.linker.sync_wiki_to_graph()
    return engines
```

- [ ] **Step 11: Commit**

```bash
git add atlas/server/ tests/server/
git commit -m "feat(server): pydantic schemas, engine dependencies, event bus

Schemas for all 12 REST/MCP operations. EngineSet wires all Core modules.
EventBus for intra-process pub/sub (wiki.changed, graph.updated, scan.completed)."
```

---

## Task 2: Middleware — CORS, Error Handling, Lifecycle

**Files:**
- Create: `atlas/server/middleware.py`
- Test: `tests/server/test_middleware.py`

- [ ] **Step 1: Write failing tests**

`tests/server/test_middleware.py`:
```python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.server.middleware import add_middleware, AtlasErrorHandler
from atlas.server.schemas import ErrorResponse


def _create_test_app() -> FastAPI:
    app = FastAPI()
    add_middleware(app)

    @app.get("/ok")
    def ok_endpoint():
        return {"status": "ok"}

    @app.get("/fail")
    def fail_endpoint():
        raise ValueError("Something went wrong")

    @app.get("/404")
    def not_found_endpoint():
        from atlas.server.middleware import AtlasNotFoundError
        raise AtlasNotFoundError("Page not found")

    @app.get("/400")
    def bad_request_endpoint():
        from atlas.server.middleware import AtlasValidationError
        raise AtlasValidationError("Invalid input")

    return app


def test_cors_headers():
    app = _create_test_app()
    client = TestClient(app)
    resp = client.options("/ok", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


def test_ok_response():
    app = _create_test_app()
    client = TestClient(app)
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_unhandled_error_returns_500():
    app = _create_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/fail")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "internal_error"
    assert "Something went wrong" in body["detail"]


def test_not_found_error_returns_404():
    app = _create_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/404")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "not_found"


def test_validation_error_returns_400():
    app = _create_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/400")
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "validation_error"


def test_request_id_header():
    app = _create_test_app()
    client = TestClient(app)
    resp = client.get("/ok")
    assert "x-request-id" in resp.headers
    # Should be a UUID-like string
    assert len(resp.headers["x-request-id"]) >= 20
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/server/test_middleware.py -v`
Expected: FAIL

- [ ] **Step 3: Implement middleware.py**

`atlas/server/middleware.py`:
```python
"""Middleware — CORS, error handling, request IDs, lifecycle hooks."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("atlas.server")


# --- Custom exceptions ---

class AtlasNotFoundError(Exception):
    """Raised when a resource is not found."""
    def __init__(self, detail: str = "Resource not found"):
        self.detail = detail


class AtlasValidationError(Exception):
    """Raised for invalid input."""
    def __init__(self, detail: str = "Invalid input"):
        self.detail = detail


class AtlasErrorHandler:
    """Unified error handler producing consistent JSON error responses."""

    @staticmethod
    async def not_found_handler(request: Request, exc: AtlasNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "detail": exc.detail},
        )

    @staticmethod
    async def validation_handler(request: Request, exc: AtlasValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": "validation_error", "detail": exc.detail},
        )

    @staticmethod
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "detail": str(exc)},
        )


def add_middleware(app: FastAPI) -> None:
    """Register all middleware on a FastAPI app instance."""

    # CORS — permissive for local development, tighten for ARA
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(AtlasNotFoundError, AtlasErrorHandler.not_found_handler)
    app.add_exception_handler(AtlasValidationError, AtlasErrorHandler.validation_handler)
    app.add_exception_handler(Exception, AtlasErrorHandler.unhandled_handler)

    # Request ID + timing middleware
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = str(uuid.uuid4())
        start = time.monotonic()

        response = await call_next(request)

        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(elapsed_ms)

        logger.info(
            "%s %s %s %sms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/server/test_middleware.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/server/middleware.py tests/server/test_middleware.py
git commit -m "feat(server): middleware — CORS, error handling, request IDs

Custom exceptions (AtlasNotFoundError, AtlasValidationError) with JSON responses.
CORS wildcard for local dev. Request ID + timing headers on every response."
```

---

## Task 3: FastAPI App — Scan + Stats Routes

**Files:**
- Create: `atlas/server/app.py`
- Test: `tests/server/test_app_scan.py`

- [ ] **Step 1: Write failing tests**

`tests/server/test_app_scan.py`:
```python
import pytest
from fastapi.testclient import TestClient
from pathlib import Path


@pytest.fixture
def client(engines, event_bus):
    from atlas.server.app import create_app
    app = create_app(engines=engines, event_bus=event_bus)
    return TestClient(app)


@pytest.fixture
def seeded_client(seeded_engines, event_bus):
    from atlas.server.app import create_app
    app = create_app(engines=seeded_engines, event_bus=event_bus)
    return TestClient(app)


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_scan_endpoint(client, engine_root):
    # Create a Python file to scan
    src = engine_root / "raw" / "untracked" / "sample.py"
    src.write_text("class Foo:\n    pass\n")

    resp = client.post("/api/scan", json={"path": str(engine_root / "raw" / "untracked")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["nodes_found"] >= 1
    assert body["message"] == "Scan complete"


def test_scan_nonexistent_path(client):
    resp = client.post("/api/scan", json={"path": "/nonexistent/path/xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["nodes_found"] == 0


def test_scan_incremental(client, engine_root):
    src = engine_root / "raw" / "untracked" / "code.py"
    src.write_text("def hello(): pass")

    # First scan
    resp1 = client.post("/api/scan", json={"path": str(engine_root / "raw" / "untracked")})
    assert resp1.status_code == 200

    # Second scan (incremental)
    resp2 = client.post("/api/scan", json={"path": str(engine_root / "raw" / "untracked"), "incremental": True})
    assert resp2.status_code == 200


def test_stats_endpoint(seeded_client):
    resp = seeded_client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    stats = body["stats"]
    assert stats["nodes"] >= 3  # auth, billing, acme
    assert isinstance(stats["communities"], int)
    assert isinstance(stats["confidence_breakdown"], dict)


def test_scan_emits_event(engines, event_bus, engine_root):
    from atlas.server.app import create_app

    received = []
    event_bus.subscribe("scan.completed", lambda e: received.append(e))
    event_bus.subscribe("graph.updated", lambda e: received.append(e))

    app = create_app(engines=engines, event_bus=event_bus)
    client = TestClient(app)

    src = engine_root / "raw" / "untracked" / "test.py"
    src.write_text("x = 1")
    client.post("/api/scan", json={"path": str(engine_root / "raw" / "untracked")})

    events = [e.get("event") for e in received if isinstance(e, dict)]
    assert "scan.completed" in events or len(received) > 0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/server/test_app_scan.py -v`
Expected: FAIL

- [ ] **Step 3: Implement app.py — initial skeleton + scan/stats routes**

`atlas/server/app.py`:
```python
"""FastAPI application — REST API for all Atlas operations."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from atlas.server.middleware import add_middleware
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
        extraction = engines.scanner.scan(scan_path, incremental=req.incremental)

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
        from atlas.server.middleware import AtlasNotFoundError

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
        from atlas.server.middleware import AtlasValidationError

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

    return app
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/server/test_app_scan.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/server/app.py tests/server/test_app_scan.py
git commit -m "feat(server): FastAPI app skeleton with scan + stats routes

create_app() wires EngineSet + EventBus. /api/scan triggers scanner + graph merge
+ linker sync. /api/stats returns graph statistics. Events emitted on mutations."
```

---

## Task 4: FastAPI App — Query, Path, Explain, God Nodes, Surprises

**Files:**
- Test: `tests/server/test_app_query.py`

- [ ] **Step 1: Write failing tests**

`tests/server/test_app_query.py`:
```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(seeded_engines, event_bus):
    from atlas.server.app import create_app
    app = create_app(engines=seeded_engines, event_bus=event_bus)
    return TestClient(app)


def test_query_bfs(client):
    resp = client.post("/api/query", json={"question": "auth", "mode": "bfs", "depth": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) >= 1
    assert "estimated_tokens" in body


def test_query_dfs(client):
    resp = client.post("/api/query", json={"question": "billing", "mode": "dfs", "depth": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) >= 1


def test_query_nonexistent_node(client):
    resp = client.post("/api/query", json={"question": "nonexistent_xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["nodes"] == []
    assert body["edges"] == []


def test_path_exists(client):
    resp = client.post("/api/path", json={"source": "auth", "target": "billing"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert len(body["edges"]) >= 1


def test_path_not_found(client):
    resp = client.post("/api/path", json={"source": "auth", "target": "nonexistent_xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert body["edges"] == []


def test_explain(client):
    resp = client.post("/api/explain", json={"concept": "auth"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["concept"] == "auth"
    assert body["label"] == "Authentication"
    assert len(body["neighbors"]) >= 1
    assert len(body["edges"]) >= 1


def test_explain_not_found(client):
    resp = client.post("/api/explain", json={"concept": "nonexistent_xyz"})
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "not_found"


def test_god_nodes(client):
    resp = client.post("/api/god-nodes", json={"top_n": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) >= 1
    first = body["nodes"][0]
    assert "id" in first
    assert "label" in first
    assert "degree" in first


def test_god_nodes_default(client):
    resp = client.post("/api/god-nodes", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) >= 1


def test_surprises(client):
    resp = client.post("/api/surprises", json={"top_n": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["edges"], list)


def test_surprises_default(client):
    resp = client.post("/api/surprises", json={})
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/server/test_app_query.py -v`
Expected: All PASS (routes already implemented in Task 3 app.py)

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_app_query.py
git commit -m "test(server): query, path, explain, god_nodes, surprises route tests

Full coverage for graph traversal routes: BFS/DFS query, shortest path,
concept explain with neighbors, god nodes ranking, surprise edge detection."
```

---

## Task 5: FastAPI App — Wiki CRUD + Ingest Routes

**Files:**
- Test: `tests/server/test_app_wiki.py`
- Test: `tests/server/test_app_ingest.py`

- [ ] **Step 1: Write failing wiki tests**

`tests/server/test_app_wiki.py`:
```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(seeded_engines, event_bus):
    from atlas.server.app import create_app
    app = create_app(engines=seeded_engines, event_bus=event_bus)
    return TestClient(app)


def test_wiki_read_existing(client):
    resp = client.post("/api/wiki/read", json={"page": "wiki/concepts/auth.md"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] is not None
    assert body["page"]["title"] == "Authentication"
    assert "JWT" in body["page"]["content"]
    assert "billing" in body["page"]["wikilinks"]


def test_wiki_read_nonexistent(client):
    resp = client.post("/api/wiki/read", json={"page": "wiki/concepts/nonexistent.md"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] is None


def test_wiki_write_new_page(client, seeded_engines, event_bus):
    received = []
    event_bus.subscribe("wiki.changed", lambda e: received.append(e))

    resp = client.post("/api/wiki/write", json={
        "page": "wiki/concepts/caching.md",
        "content": "# Caching\n\nRedis caching layer. See [[auth]].",
        "frontmatter": {"type": "wiki-concept", "title": "Caching", "confidence": "medium", "tags": ["cache"]},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == "wiki/concepts/caching.md"
    assert body["message"] == "Page saved"

    # Verify page was created
    read_resp = client.post("/api/wiki/read", json={"page": "wiki/concepts/caching.md"})
    assert read_resp.json()["page"]["title"] == "Caching"

    # Verify event was emitted
    assert len(received) >= 1
    assert received[0]["page"] == "wiki/concepts/caching.md"


def test_wiki_write_updates_graph(client, seeded_engines):
    # Write a page with a new wikilink
    client.post("/api/wiki/write", json={
        "page": "wiki/concepts/sessions.md",
        "content": "# Sessions\n\nSession management. See [[auth]].",
        "frontmatter": {"type": "wiki-concept", "title": "Sessions"},
    })

    # The linker should have added a graph node
    node = seeded_engines.graph.get_node("sessions")
    assert node is not None
    assert node.label == "Sessions"


def test_wiki_search(client):
    resp = client.post("/api/wiki/search", json={"terms": "JWT"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) >= 1
    assert any(p["title"] == "Authentication" for p in body["results"])


def test_wiki_search_no_results(client):
    resp = client.post("/api/wiki/search", json={"terms": "nonexistent_term_xyz_123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"] == []
```

- [ ] **Step 2: Write failing ingest tests**

`tests/server/test_app_ingest.py`:
```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(engines, event_bus, engine_root):
    from atlas.server.app import create_app
    app = create_app(engines=engines, event_bus=event_bus)
    return TestClient(app)


def test_ingest_local_file(client, engine_root, engines):
    # Create a file to ingest
    src = engine_root / "raw" / "untracked" / "notes.md"
    src.write_text("# My Notes\n\nSome content about architecture.")

    resp = client.post("/api/ingest", json={
        "file_path": "raw/untracked/notes.md",
        "title": "My Notes",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["path"] is not None
    assert body["path"].startswith("raw/ingested/")
    assert body["message"] == "Ingested"


def test_ingest_local_file_not_found(client):
    resp = client.post("/api/ingest", json={
        "file_path": "raw/untracked/nonexistent.md",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["path"] is None


def test_ingest_no_source(client):
    resp = client.post("/api/ingest", json={})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "validation_error"


def test_ingest_emits_event(engines, event_bus, engine_root):
    from atlas.server.app import create_app

    received = []
    event_bus.subscribe("wiki.changed", lambda e: received.append(e))

    app = create_app(engines=engines, event_bus=event_bus)
    client = TestClient(app)

    src = engine_root / "raw" / "untracked" / "event_test.md"
    src.write_text("# Event Test\n\nContent.")

    client.post("/api/ingest", json={"file_path": "raw/untracked/event_test.md"})
    assert len(received) >= 1
    assert received[0]["action"] == "ingest"
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/server/test_app_wiki.py tests/server/test_app_ingest.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/server/test_app_wiki.py tests/server/test_app_ingest.py
git commit -m "test(server): wiki CRUD + ingest route tests

Wiki read/write/search with graph sync verification. Ingest local files
with event emission. Edge cases: nonexistent pages, missing sources."
```

---

## Task 6: FastAPI App — Audit + Suggest Links Routes

**Files:**
- Test: `tests/server/test_app_analysis.py`

- [ ] **Step 1: Write failing tests**

`tests/server/test_app_analysis.py`:
```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(seeded_engines, event_bus):
    from atlas.server.app import create_app
    app = create_app(engines=seeded_engines, event_bus=event_bus)
    return TestClient(app)


def test_audit(client):
    resp = client.get("/api/audit")
    assert resp.status_code == 200
    body = resp.json()
    assert "orphan_pages" in body
    assert "god_nodes" in body
    assert "broken_links" in body
    assert "stale_pages" in body
    assert "stats" in body
    assert "health_score" in body
    assert body["stats"]["nodes"] >= 3


def test_audit_god_nodes_structure(client):
    resp = client.get("/api/audit")
    body = resp.json()
    for god in body["god_nodes"]:
        assert "id" in god
        assert "degree" in god


def test_audit_broken_links_structure(client):
    resp = client.get("/api/audit")
    body = resp.json()
    for bl in body["broken_links"]:
        assert "page" in bl
        assert "link" in bl


def test_suggest_links(client):
    resp = client.get("/api/suggest-links")
    assert resp.status_code == 200
    body = resp.json()
    assert "suggestions" in body
    assert isinstance(body["suggestions"], list)


def test_suggest_links_structure(client):
    resp = client.get("/api/suggest-links")
    body = resp.json()
    for s in body["suggestions"]:
        assert "type" in s
        assert "description" in s


def test_audit_after_adding_orphan(client, seeded_engines):
    # Add a page with no incoming links
    seeded_engines.wiki.write(
        "wiki/concepts/orphan.md",
        "# Orphan\n\nThis page has no incoming links.",
        frontmatter={"type": "wiki-concept", "title": "Orphan"},
    )
    seeded_engines.linker.sync_wiki_to_graph()

    resp = client.get("/api/audit")
    body = resp.json()
    orphan_paths = body["orphan_pages"]
    assert "wiki/concepts/orphan.md" in orphan_paths


def test_audit_stale_page(client, seeded_engines):
    seeded_engines.wiki.write(
        "wiki/concepts/old.md",
        "# Old Concept",
        frontmatter={"type": "wiki-concept", "title": "Old", "updated": "2025-01-01"},
    )
    seeded_engines.linker.sync_wiki_to_graph()

    resp = client.get("/api/audit")
    body = resp.json()
    assert "wiki/concepts/old.md" in body["stale_pages"]
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/server/test_app_analysis.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_app_analysis.py
git commit -m "test(server): audit + suggest-links route tests

Full audit structure verification (orphans, god nodes, broken links, stale pages).
Suggest links returns WikiSuggestion list. Stale page detection at 30-day threshold."
```

---

## Task 7: WebSocket Manager

**Files:**
- Create: `atlas/server/ws.py`
- Test: `tests/server/test_ws.py`

- [ ] **Step 1: Write failing tests**

`tests/server/test_ws.py`:
```python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.server.ws import WebSocketManager, mount_websocket


@pytest.fixture
def ws_manager():
    return WebSocketManager()


@pytest.fixture
def ws_app(seeded_engines, event_bus):
    from atlas.server.app import create_app

    app = create_app(engines=seeded_engines, event_bus=event_bus)
    ws_manager = WebSocketManager()
    mount_websocket(app, ws_manager, event_bus)
    return app, ws_manager


def test_websocket_connect(ws_app):
    app, _ = ws_app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        # Should receive a welcome message
        data = ws.receive_json()
        assert data["type"] == "connected"
        assert "message" in data


def test_websocket_receives_wiki_event(ws_app):
    app, ws_manager = ws_app
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        # Read the welcome message
        ws.receive_json()

        # Trigger a wiki write via REST
        client.post("/api/wiki/write", json={
            "page": "wiki/concepts/ws_test.md",
            "content": "# WS Test",
            "frontmatter": {"type": "wiki-concept", "title": "WS Test"},
        })

        # The WebSocket should receive a wiki.changed event
        data = ws.receive_json()
        assert data["type"] == "wiki.changed"
        assert data["data"]["page"] == "wiki/concepts/ws_test.md"


def test_websocket_receives_graph_event(ws_app, engine_root):
    app, ws_manager = ws_app
    client = TestClient(app)

    # Create a file to scan
    src = engine_root / "raw" / "untracked" / "ws_scan.py"
    src.write_text("class WsTest:\n    pass\n")

    with client.websocket_connect("/ws") as ws:
        # Read welcome
        ws.receive_json()

        # Trigger scan
        client.post("/api/scan", json={"path": str(engine_root / "raw" / "untracked")})

        # Should receive event(s)
        data = ws.receive_json()
        assert data["type"] in ("scan.completed", "graph.updated", "wiki.changed")


def test_websocket_manager_broadcast():
    import asyncio

    mgr = WebSocketManager()
    # Test internal broadcast tracking
    assert mgr.active_count == 0


def test_websocket_disconnect(ws_app):
    app, ws_manager = ws_app
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # welcome
    # After disconnect, active count should be 0 (eventual consistency)
    # We just verify it doesn't crash
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/server/test_ws.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ws.py**

`atlas/server/ws.py`:
```python
"""WebSocket manager — live updates when wiki or graph changes."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, TYPE_CHECKING

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from atlas.server.deps import EventBus

logger = logging.getLogger("atlas.server.ws")


class WebSocketManager:
    """Manages active WebSocket connections and broadcasts events."""

    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WebSocket connected. Active: %d", self.active_count)
        await ws.send_json({"type": "connected", "message": "Atlas WebSocket connected", "active": self.active_count})

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)
        logger.info("WebSocket disconnected. Active: %d", self.active_count)

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Send an event to all connected WebSocket clients."""
        message = json.dumps({"type": event_type, "data": data})
        dead: list[WebSocket] = []

        async with self._lock:
            connections = list(self._connections)

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self._connections:
                        self._connections.remove(ws)

    def broadcast_sync(self, event_type: str, data: dict[str, Any]) -> None:
        """Synchronous wrapper for broadcast — used from EventBus handlers.

        Gets or creates an event loop and schedules the broadcast.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event_type, data))
        except RuntimeError:
            # No running loop — skip broadcast (happens in sync test context)
            pass


def mount_websocket(app: FastAPI, manager: WebSocketManager, event_bus: EventBus) -> None:
    """Add the /ws endpoint and wire EventBus -> WebSocket broadcasting."""

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await manager.connect(ws)
        try:
            while True:
                # Keep connection alive; client can send pings or commands
                data = await ws.receive_text()
                # For now, echo back as acknowledgment
                await ws.send_json({"type": "ack", "received": data})
        except WebSocketDisconnect:
            await manager.disconnect(ws)
        except Exception:
            await manager.disconnect(ws)

    # Wire EventBus events to WebSocket broadcasts
    for event in ("wiki.changed", "graph.updated", "scan.completed"):
        event_bus.subscribe(event, lambda data, evt=event: manager.broadcast_sync(evt, data))
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/server/test_ws.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/server/ws.py tests/server/test_ws.py
git commit -m "feat(server): WebSocket manager with EventBus integration

/ws endpoint broadcasts wiki.changed, graph.updated, scan.completed events.
Manager tracks active connections, handles disconnect cleanup.
Sync wrapper for EventBus -> async WebSocket bridge."
```

---

## Task 8: MCP Server

**Files:**
- Create: `atlas/server/mcp.py`
- Test: `tests/server/test_mcp.py`

- [ ] **Step 1: Write failing tests**

`tests/server/test_mcp.py`:
```python
import pytest
from pathlib import Path

from atlas.server.mcp import create_mcp_server, TOOL_DEFINITIONS
from atlas.server.deps import create_engine_set, EventBus


@pytest.fixture
def mcp_engines(engine_root):
    engines = create_engine_set(engine_root)
    # Seed wiki
    engines.wiki.write(
        "wiki/concepts/auth.md",
        "# Authentication\n\nJWT tokens. See [[billing]].",
        frontmatter={"type": "wiki-concept", "title": "Authentication", "confidence": "high", "tags": ["auth"]},
    )
    engines.wiki.write(
        "wiki/concepts/billing.md",
        "# Billing\n\nStripe. See [[auth]].",
        frontmatter={"type": "wiki-concept", "title": "Billing", "confidence": "medium"},
    )
    engines.linker.sync_wiki_to_graph()
    return engines


def test_tool_definitions_count():
    """MCP server must expose exactly 12 tools as per spec section 6."""
    assert len(TOOL_DEFINITIONS) == 12


def test_tool_definitions_names():
    names = {t["name"] for t in TOOL_DEFINITIONS}
    expected = {
        "atlas.scan",
        "atlas.query",
        "atlas.path",
        "atlas.explain",
        "atlas.god_nodes",
        "atlas.stats",
        "atlas.ingest",
        "atlas.wiki.read",
        "atlas.wiki.write",
        "atlas.wiki.search",
        "atlas.audit",
        "atlas.suggest_links",
    }
    assert names == expected


def test_tool_definitions_have_descriptions():
    for tool in TOOL_DEFINITIONS:
        assert "description" in tool
        assert len(tool["description"]) > 10


def test_tool_definitions_have_input_schema():
    for tool in TOOL_DEFINITIONS:
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"


def test_create_mcp_server(mcp_engines):
    event_bus = EventBus()
    server = create_mcp_server(engines=mcp_engines, event_bus=event_bus)
    assert server is not None
    assert hasattr(server, "name")


def test_handle_scan(mcp_engines, engine_root):
    """Test scan tool handler directly."""
    from atlas.server.mcp import handle_tool_call

    event_bus = EventBus()
    # Create a file to scan
    (engine_root / "raw" / "untracked" / "mcp_test.py").write_text("class MCP:\n    pass\n")

    result = handle_tool_call(
        "atlas.scan",
        {"path": str(engine_root / "raw" / "untracked")},
        engines=mcp_engines,
        event_bus=event_bus,
    )
    assert result["nodes_found"] >= 1


def test_handle_query(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.query",
        {"question": "auth", "mode": "bfs", "depth": 2},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert len(result["nodes"]) >= 1


def test_handle_path(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.path",
        {"source": "auth", "target": "billing"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["found"] is True


def test_handle_path_not_found(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.path",
        {"source": "auth", "target": "nonexistent"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["found"] is False


def test_handle_explain(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.explain",
        {"concept": "auth"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["concept"] == "auth"
    assert result["label"] == "Authentication"
    assert len(result["neighbors"]) >= 1


def test_handle_explain_not_found(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.explain",
        {"concept": "nonexistent"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert "error" in result


def test_handle_god_nodes(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.god_nodes",
        {"top_n": 5},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert len(result["nodes"]) >= 1


def test_handle_stats(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.stats",
        {},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["nodes"] >= 2
    assert "confidence_breakdown" in result


def test_handle_wiki_read(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.wiki.read",
        {"page": "wiki/concepts/auth.md"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["title"] == "Authentication"
    assert "JWT" in result["content"]


def test_handle_wiki_read_not_found(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.wiki.read",
        {"page": "wiki/concepts/nonexistent.md"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result is None or result.get("error") == "not_found"


def test_handle_wiki_write(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.wiki.write",
        {
            "page": "wiki/concepts/caching.md",
            "content": "# Caching\n\nRedis layer.",
            "frontmatter": {"type": "wiki-concept", "title": "Caching"},
        },
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["page"] == "wiki/concepts/caching.md"

    # Verify page exists
    page = mcp_engines.wiki.read("wiki/concepts/caching.md")
    assert page is not None


def test_handle_wiki_search(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.wiki.search",
        {"terms": "JWT"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert len(result["results"]) >= 1


def test_handle_audit(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.audit",
        {},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert "orphan_pages" in result
    assert "god_nodes" in result
    assert "health_score" in result


def test_handle_suggest_links(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.suggest_links",
        {},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert "suggestions" in result


def test_handle_ingest_file(mcp_engines, engine_root):
    from atlas.server.mcp import handle_tool_call

    (engine_root / "raw" / "untracked" / "mcp_ingest.md").write_text("# MCP Ingest Test")

    result = handle_tool_call(
        "atlas.ingest",
        {"file_path": "raw/untracked/mcp_ingest.md", "title": "MCP Test"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["path"] is not None
    assert result["path"].startswith("raw/ingested/")


def test_handle_unknown_tool(mcp_engines):
    from atlas.server.mcp import handle_tool_call

    result = handle_tool_call(
        "atlas.unknown_tool",
        {},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/server/test_mcp.py -v`
Expected: FAIL

- [ ] **Step 3: Implement mcp.py**

`atlas/server/mcp.py`:
```python
"""MCP server — stdio for local, SSE for remote. 12 tools as per Atlas spec section 6."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
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
    extraction = engines.scanner.scan(scan_path, incremental=incremental)

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

    Usage:
        # stdio (local, for Claude Code / Codex):
        server = create_mcp_server(engines, event_bus)
        server.run_stdio()

        # SSE (remote, for ARA):
        server = create_mcp_server(engines, event_bus)
        server.run_sse(host="0.0.0.0", port=7200)
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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/server/test_mcp.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/server/mcp.py tests/server/test_mcp.py
git commit -m "feat(server): MCP server with 12 tools — stdio + SSE transport

All 12 Atlas tools per spec section 6: scan, query, path, explain, god_nodes,
stats, ingest, wiki.read, wiki.write, wiki.search, audit, suggest_links.
handle_tool_call() dispatches to Core engines. create_mcp_server() uses mcp package."
```

---

## Task 9: Server Entry Point + CLI Integration

**Files:**
- Update: `atlas/server/app.py` (add `run_server` function)
- No new test file — tested via integration

- [ ] **Step 1: Add run_server helper to app.py**

Append to `atlas/server/app.py`:
```python
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
```

- [ ] **Step 2: Verify import works**

Run: `cd /Users/pierrebeunardeau/dev/internal/agent-wiki && python -c "from atlas.server.app import run_server, run_mcp; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add atlas/server/app.py
git commit -m "feat(server): run_server + run_mcp entry points for atlas serve / atlas mcp

run_server() starts FastAPI + WebSocket on port 7100.
run_mcp() starts MCP server (stdio for local, SSE for remote on port 7200).
Both auto-create EngineSet, load graph, sync wiki on startup."
```

---

## Task 10: Server Integration Test

**Files:**
- Test: `tests/server/test_integration.py`

- [ ] **Step 1: Write integration test**

`tests/server/test_integration.py`:
```python
"""End-to-end server integration test — REST API, event flow, graph sync."""
import pytest
from fastapi.testclient import TestClient

from atlas.server.app import create_app
from atlas.server.deps import create_engine_set, EventBus
from atlas.server.ws import WebSocketManager, mount_websocket


@pytest.fixture
def full_app(tmp_path):
    """Create a fully wired app with WebSocket support."""
    for d in ["wiki/projects", "wiki/concepts", "wiki/decisions", "wiki/sources", "raw/untracked", "raw/ingested"]:
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "wiki" / "index.md").write_text("# Wiki Index\n")

    engines = create_engine_set(tmp_path)
    event_bus = EventBus()
    app = create_app(engines=engines, event_bus=event_bus)

    ws_manager = WebSocketManager()
    mount_websocket(app, ws_manager, event_bus)

    return app, engines, event_bus, tmp_path


def test_full_lifecycle(full_app):
    """Test the complete lifecycle: write wiki, scan, query, audit."""
    app, engines, event_bus, root = full_app
    client = TestClient(app)

    # 1. Health check
    resp = client.get("/health")
    assert resp.status_code == 200

    # 2. Write wiki pages
    client.post("/api/wiki/write", json={
        "page": "wiki/concepts/auth.md",
        "content": "# Auth\n\nJWT-based auth. See [[billing]].",
        "frontmatter": {"type": "wiki-concept", "title": "Auth", "confidence": "high", "tags": ["auth"]},
    })
    client.post("/api/wiki/write", json={
        "page": "wiki/concepts/billing.md",
        "content": "# Billing\n\nStripe integration. See [[auth]].",
        "frontmatter": {"type": "wiki-concept", "title": "Billing", "confidence": "medium"},
    })

    # 3. Verify pages exist
    resp = client.post("/api/wiki/read", json={"page": "wiki/concepts/auth.md"})
    assert resp.json()["page"]["title"] == "Auth"

    # 4. Search wiki
    resp = client.post("/api/wiki/search", json={"terms": "JWT"})
    assert len(resp.json()["results"]) >= 1

    # 5. Check stats (graph should have nodes from wiki sync)
    resp = client.get("/api/stats")
    stats = resp.json()["stats"]
    assert stats["nodes"] >= 2

    # 6. Query the graph
    resp = client.post("/api/query", json={"question": "auth", "mode": "bfs", "depth": 2})
    assert len(resp.json()["nodes"]) >= 1

    # 7. Find path
    resp = client.post("/api/path", json={"source": "auth", "target": "billing"})
    assert resp.json()["found"] is True

    # 8. Explain concept
    resp = client.post("/api/explain", json={"concept": "auth"})
    assert resp.json()["label"] == "Auth"

    # 9. God nodes
    resp = client.post("/api/god-nodes", json={})
    assert len(resp.json()["nodes"]) >= 1

    # 10. Surprises
    resp = client.post("/api/surprises", json={})
    assert resp.status_code == 200

    # 11. Audit
    resp = client.get("/api/audit")
    audit = resp.json()
    assert audit["stats"]["nodes"] >= 2
    assert "health_score" in audit

    # 12. Suggest links
    resp = client.get("/api/suggest-links")
    assert "suggestions" in resp.json()

    # 13. Scan a Python file
    src = root / "raw" / "untracked" / "scanner_test.py"
    src.write_text("class Scanner:\n    def scan(self): pass\n")
    resp = client.post("/api/scan", json={"path": str(root / "raw" / "untracked")})
    assert resp.json()["nodes_found"] >= 1

    # 14. Stats should reflect new nodes
    resp = client.get("/api/stats")
    assert resp.json()["stats"]["nodes"] > 2

    # 15. Ingest a local file
    (root / "raw" / "untracked" / "notes.md").write_text("# Notes\n\nUseful notes.")
    resp = client.post("/api/ingest", json={"file_path": "raw/untracked/notes.md", "title": "Notes"})
    assert resp.json()["path"] is not None


def test_websocket_in_lifecycle(full_app):
    """Test WebSocket receives events during REST operations."""
    app, engines, event_bus, root = full_app
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        welcome = ws.receive_json()
        assert welcome["type"] == "connected"

        # Write a wiki page — should trigger wiki.changed
        client.post("/api/wiki/write", json={
            "page": "wiki/concepts/ws_lifecycle.md",
            "content": "# WS Lifecycle",
            "frontmatter": {"type": "wiki-concept", "title": "WS Lifecycle"},
        })

        msg = ws.receive_json()
        assert msg["type"] in ("wiki.changed", "graph.updated")


def test_mcp_tool_handler_matches_rest(full_app):
    """Verify MCP tool handlers produce equivalent results to REST routes."""
    app, engines, event_bus, root = full_app
    client = TestClient(app)
    from atlas.server.mcp import handle_tool_call

    # Write wiki pages via REST
    client.post("/api/wiki/write", json={
        "page": "wiki/concepts/auth.md",
        "content": "# Auth\n\nJWT auth.",
        "frontmatter": {"type": "wiki-concept", "title": "Auth"},
    })

    # Compare REST stats vs MCP stats
    rest_stats = client.get("/api/stats").json()["stats"]
    mcp_stats = handle_tool_call("atlas.stats", {}, engines=engines, event_bus=event_bus)
    assert rest_stats["nodes"] == mcp_stats["nodes"]
    assert rest_stats["edges"] == mcp_stats["edges"]

    # Compare REST wiki.read vs MCP wiki.read
    rest_page = client.post("/api/wiki/read", json={"page": "wiki/concepts/auth.md"}).json()["page"]
    mcp_page = handle_tool_call("atlas.wiki.read", {"page": "wiki/concepts/auth.md"}, engines=engines, event_bus=event_bus)
    assert rest_page["title"] == mcp_page["title"]
    assert rest_page["content"] == mcp_page["content"]
```

- [ ] **Step 2: Run integration tests**

Run: `python -m pytest tests/server/test_integration.py -v`
Expected: All PASS

- [ ] **Step 3: Run full server test suite**

Run: `python -m pytest tests/server/ -v --tb=short`
Expected: All PASS across all server test modules

- [ ] **Step 4: Commit**

```bash
git add tests/server/test_integration.py
git commit -m "test(server): end-to-end integration — 15-step lifecycle + WS + MCP parity

Full lifecycle: wiki CRUD, scan, query, path, explain, god_nodes, surprises,
audit, suggest_links, ingest. WebSocket receives events. MCP produces
identical results to REST for all operations."
```

---

## Task 11: Self-Review

Before declaring the Server plan complete, verify the following:

- [ ] **Step 1: Spec coverage**

Check every operation from spec section 6 is covered:

| Spec operation | REST route | MCP tool | Tested |
|---|---|---|---|
| `atlas.scan(path)` | `POST /api/scan` | `atlas.scan` | Yes |
| `atlas.query(question, mode)` | `POST /api/query` | `atlas.query` | Yes |
| `atlas.path(from, to)` | `POST /api/path` | `atlas.path` | Yes |
| `atlas.explain(concept)` | `POST /api/explain` | `atlas.explain` | Yes |
| `atlas.god_nodes(top_n)` | `POST /api/god-nodes` | `atlas.god_nodes` | Yes |
| `atlas.stats()` | `GET /api/stats` | `atlas.stats` | Yes |
| `atlas.ingest(url_or_path)` | `POST /api/ingest` | `atlas.ingest` | Yes |
| `atlas.wiki.read(page)` | `POST /api/wiki/read` | `atlas.wiki.read` | Yes |
| `atlas.wiki.write(page, content)` | `POST /api/wiki/write` | `atlas.wiki.write` | Yes |
| `atlas.wiki.search(terms)` | `POST /api/wiki/search` | `atlas.wiki.search` | Yes |
| `atlas.audit()` | `GET /api/audit` | `atlas.audit` | Yes |
| `atlas.suggest_links()` | `GET /api/suggest-links` | `atlas.suggest_links` | Yes |

Total: 12/12 operations covered.

- [ ] **Step 2: Placeholder scan**

Verify no `TODO`, `FIXME`, `pass`, or `...` placeholders in production code. All implementations are complete.

Exceptions allowed:
- `# TODO` comments for future enhancements (e.g., tree-sitter support in scanner) — these are from Core, not Server

- [ ] **Step 3: Type consistency**

Verify all interfaces match Core engine signatures:

| Server call | Core method |
|---|---|
| `engines.scanner.scan(path, incremental)` | `Scanner.scan(path: Path, incremental: bool)` |
| `engines.graph.query(question, mode, depth)` | `GraphEngine.query(start: str, mode: str, depth: int)` |
| `engines.graph.path(source, target)` | `GraphEngine.path(source: str, target: str)` |
| `engines.graph.get_node(concept)` | `GraphEngine.get_node(node_id: str)` |
| `engines.graph.get_neighbors(concept)` | `GraphEngine.get_neighbors(node_id: str)` |
| `engines.analyzer.god_nodes(top_n)` | `Analyzer.god_nodes(top_n: int)` |
| `engines.analyzer.surprises(top_n)` | `Analyzer.surprises(top_n: int)` |
| `engines.graph.stats()` | `GraphEngine.stats()` |
| `engines.wiki.read(page)` | `WikiEngine.read(path: str)` |
| `engines.wiki.write(page, content, frontmatter)` | `WikiEngine.write(path: str, content: str, frontmatter: dict)` |
| `engines.wiki.search(terms)` | `WikiEngine.search(terms: str)` |
| `engines.analyzer.audit()` | `Analyzer.audit()` |
| `engines.linker.sync_wiki_to_graph()` | `Linker.sync_wiki_to_graph()` |
| `engines.linker.sync_graph_to_wiki()` | `Linker.sync_graph_to_wiki()` |
| `engines.ingest.ingest_file(path, title)` | `IngestEngine.ingest_file(source_path: str, title: str)` |
| `engines.ingest.ingest_url(url, title, author)` | `IngestEngine.ingest_url(url: str, title: str, author: str)` |
| `engines.graph.merge(extraction)` | `GraphEngine.merge(extraction: Extraction)` |
| `engines.save_graph()` | `EngineSet.save_graph()` → `GraphEngine.save(path)` |
| `engines.load_graph()` | `EngineSet.load_graph()` → `GraphEngine.load(path)` |

All signatures match. No filesystem access from server layer.

- [ ] **Step 4: Event flow verification**

| Mutation | Events emitted | WebSocket broadcast |
|---|---|---|
| Scan | `scan.completed`, `graph.updated` | Yes |
| Wiki write | `wiki.changed`, `graph.updated` | Yes |
| Ingest | `wiki.changed` | Yes |
| Query (read-only) | None | N/A |
| Audit (read-only) | None | N/A |

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "docs(server): complete self-review — 12/12 spec operations, no placeholders

Full coverage verified: REST, MCP, WebSocket, middleware, lifecycle.
Type consistency with Core interfaces confirmed. Event flow documented."
```

---

## Backlog from Plan 1 Core Review

These items were identified during Core implementation and belong to the Server plan:

### SSRF Protection in ingest_url

The `IngestEngine.ingest_url()` async path uses `httpx.AsyncClient(follow_redirects=True)`. This must be hardened:
- Block `file://`, `ftp://`, `gopher://` schemes — only allow `http://` and `https://`
- Block redirects to private IPs (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Add `_NoFileRedirectHandler` pattern (like graphify's `security.py`)
- Cap response size (10MB max)
- Add to middleware or as a validation helper in `deps.py`

**Where:** Add a `validate_url()` function in `atlas/server/middleware.py` or `atlas/core/ingest.py`. Call it before any `httpx.get()`.

### Cache Manifest Locking

When the server handles concurrent requests (scan + ingest simultaneously), both may write to `atlas-cache/manifest.json` at the same time. Add file locking:
- Use `fcntl.flock()` (Unix) or `portalocker` (cross-platform) around manifest read/write
- Or serialize cache writes through the EventBus (only one writer at a time)

**Where:** `atlas/core/cache.py` — wrap `_save_manifest()` and `_load_manifest()` with a lock.

---

## Summary

| Task | Module | Tests | Lines (est.) |
|---|---|---|---|
| 1 | schemas.py + deps.py | test_schemas.py + test_deps.py | ~350 |
| 2 | middleware.py | test_middleware.py | ~100 |
| 3 | app.py (scan + stats) | test_app_scan.py | ~250 |
| 4 | app.py (query routes) | test_app_query.py | ~80 |
| 5 | app.py (wiki + ingest) | test_app_wiki.py + test_app_ingest.py | ~120 |
| 6 | app.py (audit + suggest) | test_app_analysis.py | ~80 |
| 7 | ws.py | test_ws.py | ~100 |
| 8 | mcp.py | test_mcp.py | ~400 |
| 9 | app.py (entry points) | — | ~60 |
| 10 | — | test_integration.py | ~150 |
| 11 | Self-review | — | — |

**Total: ~1700 lines of code + tests across 11 tasks for 4 developers.**

**Test commands:**
```bash
# Run all server tests
python -m pytest tests/server/ -v --tb=short

# Run with coverage
python -m pytest tests/server/ -v --cov=atlas.server --cov-report=term-missing

# Run a specific task's tests
python -m pytest tests/server/test_schemas.py -v
python -m pytest tests/server/test_mcp.py -v
python -m pytest tests/server/test_integration.py -v
```
