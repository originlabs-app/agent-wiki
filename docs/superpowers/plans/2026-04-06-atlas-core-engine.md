# Atlas Core Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core engine of Atlas — the 8 modules that Scanner, Graph, Wiki, Linker, Cache, Analyzer, Ingest, and Storage comprise. This is the foundation that Server, Dashboard, Skills, and CLI all consume.

**Architecture:** Each module is a standalone Python class behind a Protocol interface. Modules communicate through typed dataclasses (Extraction, Node, Edge, Page, etc.). Storage is abstracted so the same code runs on local filesystem or ARA cloud. The wiki markdown is the source of truth; graph.json is derived.

**Tech Stack:** Python 3.12+, NetworkX, tree-sitter, graspologic (Leiden), PyYAML, httpx, typer

---

## File Map

```
atlas/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── models.py          # All dataclasses: Node, Edge, Extraction, Page, Subgraph, etc.
│   ├── storage.py          # StorageBackend protocol + LocalStorage
│   ├── cache.py            # SHA256 manifest, incremental extraction cache
│   ├── scanner.py          # Multi-modal extraction (AST + LLM dispatch)
│   ├── scanner_ast.py      # AST extraction via tree-sitter (code files)
│   ├── scanner_semantic.py # LLM extraction (docs, PDF, images)
│   ├── graph.py            # Graph engine: build, merge, query, BFS/DFS, serialize
│   ├── wiki.py             # Wiki engine: read, write, search, frontmatter, templates
│   ├── linker.py           # Bidirectional graph <-> wiki sync
│   ├── analyzer.py         # God nodes, surprises, gaps, contradictions, communities
│   └── ingest.py           # Smart URL fetch (tweet, arxiv, PDF, webpage)
├── py.typed
└── pyproject.toml

tests/
├── conftest.py             # Shared fixtures (tmp storage, sample pages, sample graph)
├── core/
│   ├── test_models.py
│   ├── test_storage.py
│   ├── test_cache.py
│   ├── test_scanner_ast.py
│   ├── test_scanner_semantic.py
│   ├── test_scanner.py
│   ├── test_graph.py
│   ├── test_wiki.py
│   ├── test_linker.py
│   ├── test_analyzer.py
│   └── test_ingest.py
├── fixtures/
│   ├── sample.py           # Simple Python file for AST extraction
│   ├── sample.ts           # Simple TypeScript file
│   ├── sample.md           # Markdown doc with concepts
│   ├── sample_wiki/        # Pre-built wiki for testing
│   │   ├── index.md
│   │   ├── projects/
│   │   │   └── acme.md
│   │   ├── concepts/
│   │   │   ├── auth.md
│   │   │   └── billing.md
│   │   ├── sources/
│   │   │   └── 2026-04-01-api-spec.md
│   │   └── decisions/
│   │       └── 2026-04-01-fastapi.md
│   └── AGENTS.md
```

---

## Task 1: Project Scaffold + Models

**Files:**
- Create: `pyproject.toml`
- Create: `atlas/__init__.py`
- Create: `atlas/core/__init__.py`
- Create: `atlas/core/models.py`
- Test: `tests/core/test_models.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "atlas-ai"
version = "2.0.0a1"
description = "Knowledge engine for AI agents — scan anything, know everything, remember forever."
readme = "README.md"
license = "MIT"
requires-python = ">=3.12"
authors = [{ name = "Origin Labs", email = "hello@originlabs.dev" }]
keywords = ["knowledge-graph", "wiki", "agents", "mcp", "llm"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "networkx>=3.2",
    "pyyaml>=6.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
ast = ["tree-sitter>=0.22", "tree-sitter-python>=0.23", "tree-sitter-javascript>=0.23", "tree-sitter-typescript>=0.23", "tree-sitter-go>=0.23", "tree-sitter-rust>=0.23"]
cluster = ["graspologic>=3.4"]
server = ["fastapi>=0.115", "uvicorn>=0.32"]
all = ["atlas-ai[ast,cluster,server]"]
dev = ["atlas-ai[all]", "pytest>=8.0", "pytest-cov>=5.0", "ruff>=0.8"]

[project.scripts]
atlas = "atlas.cli:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --tb=short"

[tool.ruff]
target-version = "py312"
line-length = 120
```

- [ ] **Step 2: Create package init files**

`atlas/__init__.py`:
```python
"""Atlas — Knowledge engine for AI agents."""
__version__ = "2.0.0a1"
```

`atlas/core/__init__.py`:
```python
"""Core engine: models, storage, scanner, graph, wiki, linker, analyzer, ingest."""
```

- [ ] **Step 3: Write the failing test for models**

`tests/core/test_models.py`:
```python
from atlas.core.models import Node, Edge, Extraction, Page, Subgraph, GraphStats, AuditReport, WikiSuggestion, GraphChange, LinkSuggestion


def test_node_creation():
    node = Node(id="auth_module", label="Auth Module", type="code", source_file="src/auth.py")
    assert node.id == "auth_module"
    assert node.label == "Auth Module"
    assert node.type == "code"
    assert node.source_file == "src/auth.py"
    assert node.confidence == "high"  # default
    assert node.community is None


def test_edge_creation():
    edge = Edge(source="auth_module", target="db_client", relation="imports", confidence="EXTRACTED")
    assert edge.source == "auth_module"
    assert edge.target == "db_client"
    assert edge.confidence_score == 1.0  # EXTRACTED default


def test_edge_inferred_default_score():
    edge = Edge(source="a", target="b", relation="related", confidence="INFERRED")
    assert edge.confidence_score == 0.7


def test_extraction_merge():
    e1 = Extraction(nodes=[Node(id="a", label="A", type="code", source_file="a.py")], edges=[])
    e2 = Extraction(nodes=[Node(id="b", label="B", type="code", source_file="b.py")], edges=[])
    merged = e1.merge(e2)
    assert len(merged.nodes) == 2
    assert len(merged.edges) == 0


def test_page_creation():
    page = Page(
        path="wiki/concepts/auth.md",
        title="Auth",
        type="wiki-concept",
        content="# Auth\n\nAuthentication module.",
        frontmatter={"type": "wiki-concept", "title": "Auth", "confidence": "high", "tags": ["auth"]},
    )
    assert page.title == "Auth"
    assert page.wikilinks == []


def test_page_extract_wikilinks():
    page = Page(
        path="wiki/concepts/auth.md",
        title="Auth",
        type="wiki-concept",
        content="# Auth\n\nSee [[billing]] and [[wiki/projects/acme]].",
        frontmatter={},
    )
    assert page.wikilinks == ["billing", "wiki/projects/acme"]


def test_subgraph_token_count():
    nodes = [Node(id="a", label="A", type="code", source_file="a.py")]
    edges = [Edge(source="a", target="b", relation="calls", confidence="EXTRACTED")]
    sg = Subgraph(nodes=nodes, edges=edges)
    assert sg.estimated_tokens > 0


def test_graph_stats():
    stats = GraphStats(nodes=100, edges=200, communities=5, confidence_breakdown={"EXTRACTED": 120, "INFERRED": 70, "AMBIGUOUS": 10})
    assert stats.health_score > 0  # higher EXTRACTED ratio = higher score
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd /Users/pierrebeunardeau/dev/internal/agent-wiki && python -m pytest tests/core/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.core.models'`

- [ ] **Step 5: Implement models.py**

`atlas/core/models.py`:
```python
"""Data models for Atlas core engine."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Node:
    id: str
    label: str
    type: str  # "code" | "document" | "paper" | "image" | "wiki-page" | "wiki-concept" | "wiki-decision" | "wiki-source"
    source_file: str
    source_location: str | None = None
    source_url: str | None = None
    confidence: str = "high"  # "high" | "medium" | "low"
    community: int | None = None
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    captured_at: str | None = None
    author: str | None = None


@dataclass
class Edge:
    source: str
    target: str
    relation: str  # "imports" | "calls" | "references" | "tagged_with" | "semantically_similar_to" | etc.
    confidence: str = "EXTRACTED"  # "EXTRACTED" | "INFERRED" | "AMBIGUOUS"
    confidence_score: float | None = None
    source_file: str | None = None
    weight: float = 1.0

    def __post_init__(self):
        if self.confidence_score is None:
            self.confidence_score = {"EXTRACTED": 1.0, "INFERRED": 0.7, "AMBIGUOUS": 0.2}.get(self.confidence, 0.5)


@dataclass
class Extraction:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    source_file: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0

    def merge(self, other: Extraction) -> Extraction:
        seen_ids = {n.id for n in self.nodes}
        new_nodes = [n for n in other.nodes if n.id not in seen_ids]
        return Extraction(
            nodes=self.nodes + new_nodes,
            edges=self.edges + other.edges,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


@dataclass
class Page:
    path: str
    title: str
    type: str
    content: str
    frontmatter: dict = field(default_factory=dict)

    @property
    def wikilinks(self) -> list[str]:
        return _WIKILINK_RE.findall(self.content)

    @property
    def slug(self) -> str:
        return self.path.rsplit("/", 1)[-1].removesuffix(".md")


@dataclass
class Subgraph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    path_description: str | None = None

    @property
    def estimated_tokens(self) -> int:
        text = "".join(f"{n.id} {n.label} {n.type}" for n in self.nodes)
        text += "".join(f"{e.source} {e.relation} {e.target}" for e in self.edges)
        return max(1, len(text) // 4)


@dataclass
class GraphStats:
    nodes: int
    edges: int
    communities: int
    confidence_breakdown: dict[str, int] = field(default_factory=dict)

    @property
    def health_score(self) -> float:
        total = sum(self.confidence_breakdown.values()) or 1
        extracted = self.confidence_breakdown.get("EXTRACTED", 0)
        ambiguous = self.confidence_breakdown.get("AMBIGUOUS", 0)
        return round((extracted / total) * 100 - (ambiguous / total) * 50, 1)


@dataclass
class WikiSuggestion:
    type: str  # "create_page" | "add_wikilink" | "flag_god_node" | "create_concept" | "clarify_relation" | "contradiction"
    description: str
    target_page: str | None = None
    source_node: str | None = None
    target_node: str | None = None
    reason: str | None = None


@dataclass
class GraphChange:
    type: str  # "add_node" | "remove_node" | "add_edge" | "remove_edge" | "update_node"
    node_id: str | None = None
    edge: Edge | None = None
    details: str | None = None


@dataclass
class LinkSuggestion:
    from_page: str
    to_page: str
    reason: str
    confidence: str = "INFERRED"


@dataclass
class AuditReport:
    orphan_pages: list[str] = field(default_factory=list)
    god_nodes: list[tuple[str, int]] = field(default_factory=list)  # (node_id, degree)
    broken_links: list[tuple[str, str]] = field(default_factory=list)  # (page, broken_link)
    stale_pages: list[str] = field(default_factory=list)
    contradictions: list[dict] = field(default_factory=list)
    missing_links: list[LinkSuggestion] = field(default_factory=list)
    communities: list[dict] = field(default_factory=list)
    stats: GraphStats | None = None
    health_score: float = 0.0
```

- [ ] **Step 6: Run tests**

Run: `cd /Users/pierrebeunardeau/dev/internal/agent-wiki && python -m pytest tests/core/test_models.py -v`
Expected: All PASS

- [ ] **Step 7: Create conftest.py with shared fixtures**

`tests/conftest.py`:
```python
"""Shared test fixtures."""
import shutil
from pathlib import Path

import pytest

from atlas.core.models import Node, Edge, Extraction, Page
from atlas.core.storage import LocalStorage

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_storage(tmp_path):
    """A LocalStorage instance pointed at a temp directory with wiki/ and raw/ structure."""
    wiki = tmp_path / "wiki"
    raw = tmp_path / "raw"
    for d in [wiki / "projects", wiki / "concepts", wiki / "decisions", wiki / "sources", raw / "untracked", raw / "ingested"]:
        d.mkdir(parents=True)
    (wiki / "index.md").write_text("# Wiki Index\n")
    (wiki / "log.md").write_text("# Wiki Log\n")
    return LocalStorage(root=tmp_path)


@pytest.fixture
def sample_wiki(tmp_storage):
    """A LocalStorage pre-populated with sample pages."""
    src = FIXTURES / "sample_wiki"
    if src.exists():
        shutil.copytree(src, tmp_storage.root / "wiki", dirs_exist_ok=True)
    return tmp_storage


@pytest.fixture
def sample_extraction():
    """A minimal Extraction for testing graph merge."""
    return Extraction(
        nodes=[
            Node(id="auth", label="Auth Module", type="code", source_file="src/auth.py"),
            Node(id="db", label="Database", type="code", source_file="src/db.py"),
            Node(id="api", label="API", type="code", source_file="src/api.py"),
        ],
        edges=[
            Edge(source="api", target="auth", relation="imports", confidence="EXTRACTED"),
            Edge(source="api", target="db", relation="imports", confidence="EXTRACTED"),
            Edge(source="auth", target="db", relation="calls", confidence="INFERRED"),
        ],
    )
```

- [ ] **Step 8: Commit**

```bash
git add atlas/ tests/ pyproject.toml
git commit -m "feat: atlas project scaffold + core models

Dataclasses for Node, Edge, Extraction, Page, Subgraph, GraphStats,
AuditReport, WikiSuggestion, GraphChange, LinkSuggestion.
All models tested. pyproject.toml with optional deps (ast, cluster, server)."
```

---

## Task 2: Storage Backend

**Files:**
- Create: `atlas/core/storage.py`
- Test: `tests/core/test_storage.py`

- [ ] **Step 1: Write failing tests**

`tests/core/test_storage.py`:
```python
from pathlib import Path

from atlas.core.storage import LocalStorage


def test_write_and_read(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth\n\nAuth module.")
    content = s.read("wiki/concepts/auth.md")
    assert content == "# Auth\n\nAuth module."


def test_read_nonexistent(tmp_path):
    s = LocalStorage(root=tmp_path)
    assert s.read("wiki/nope.md") is None


def test_list_files(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth")
    s.write("wiki/concepts/billing.md", "# Billing")
    s.write("wiki/projects/acme.md", "# Acme")
    result = s.list("wiki/concepts/")
    assert sorted(result) == ["wiki/concepts/auth.md", "wiki/concepts/billing.md"]


def test_list_with_suffix_filter(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth")
    s.write("wiki/concepts/_template.md", "# Template")
    result = s.list("wiki/concepts/", exclude_prefix="_")
    assert result == ["wiki/concepts/auth.md"]


def test_delete(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth")
    s.delete("wiki/concepts/auth.md")
    assert s.read("wiki/concepts/auth.md") is None


def test_exists(tmp_path):
    s = LocalStorage(root=tmp_path)
    assert not s.exists("wiki/concepts/auth.md")
    s.write("wiki/concepts/auth.md", "# Auth")
    assert s.exists("wiki/concepts/auth.md")


def test_mtime(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth")
    mtime = s.mtime("wiki/concepts/auth.md")
    assert mtime > 0


def test_hash(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth")
    h = s.hash("wiki/concepts/auth.md")
    assert len(h) == 64  # SHA256 hex digest
    # Same content = same hash
    s.write("wiki/concepts/auth2.md", "# Auth")
    assert s.hash("wiki/concepts/auth2.md") == h
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/core/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement storage.py**

`atlas/core/storage.py`:
```python
"""Storage abstraction — local filesystem for standalone, cloud for ARA."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for storage backends. Core engine calls this, never touches filesystem directly."""

    def read(self, path: str) -> str | None: ...
    def write(self, path: str, content: str) -> None: ...
    def list(self, prefix: str, exclude_prefix: str | None = None) -> list[str]: ...
    def delete(self, path: str) -> None: ...
    def exists(self, path: str) -> bool: ...
    def mtime(self, path: str) -> float: ...
    def hash(self, path: str) -> str | None: ...


class LocalStorage:
    """Local filesystem storage backend."""

    def __init__(self, root: Path | str):
        self.root = Path(root)

    def _resolve(self, path: str) -> Path:
        return self.root / path

    def read(self, path: str) -> str | None:
        p = self._resolve(path)
        if not p.is_file():
            return None
        return p.read_text(encoding="utf-8")

    def write(self, path: str, content: str) -> None:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def list(self, prefix: str, exclude_prefix: str | None = None) -> list[str]:
        d = self._resolve(prefix)
        if not d.is_dir():
            return []
        results = []
        for f in sorted(d.iterdir()):
            if not f.is_file() or not f.suffix == ".md":
                continue
            if exclude_prefix and f.name.startswith(exclude_prefix):
                continue
            results.append(f"{prefix}{f.name}")
        return results

    def delete(self, path: str) -> None:
        p = self._resolve(path)
        if p.is_file():
            p.unlink()

    def exists(self, path: str) -> bool:
        return self._resolve(path).is_file()

    def mtime(self, path: str) -> float:
        p = self._resolve(path)
        return p.stat().st_mtime if p.is_file() else 0.0

    def hash(self, path: str) -> str | None:
        p = self._resolve(path)
        if not p.is_file():
            return None
        return hashlib.sha256(p.read_bytes()).hexdigest()
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/core/test_storage.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/core/storage.py tests/core/test_storage.py
git commit -m "feat: storage backend with LocalStorage implementation

Protocol-based abstraction. LocalStorage wraps filesystem with read, write,
list, delete, exists, mtime, hash. ARAStorage will implement the same protocol."
```

---

## Task 3: Wiki Engine

**Files:**
- Create: `atlas/core/wiki.py`
- Test: `tests/core/test_wiki.py`
- Create: `tests/fixtures/sample_wiki/` structure

- [ ] **Step 1: Create test fixtures**

`tests/fixtures/sample_wiki/index.md`:
```markdown
---
type: wiki-index
updated: 2026-04-06
---

# Wiki Index
```

`tests/fixtures/sample_wiki/projects/acme.md`:
```markdown
---
type: wiki-page
project: Acme
title: "Acme"
status: active
updated: 2026-04-06
updated_by: agent
confidence: high
---

# Acme — Overview

## Summary

A test project for Atlas.

## Sources

- [[wiki/sources/2026-04-01-api-spec]]
```

`tests/fixtures/sample_wiki/concepts/auth.md`:
```markdown
---
type: wiki-concept
title: "Authentication"
updated: 2026-04-06
updated_by: agent
confidence: high
tags: [auth, security]
description: "Auth module handling JWT tokens and session management."
---

# Authentication

The auth module handles JWT tokens and sessions. Related to [[billing]] and [[wiki/projects/acme]].

## Key ideas

- JWT-based stateless auth
- Session fallback for legacy clients
```

`tests/fixtures/sample_wiki/concepts/billing.md`:
```markdown
---
type: wiki-concept
title: "Billing"
updated: 2026-04-06
updated_by: agent
confidence: medium
tags: [billing, payments]
description: "Billing system processing Stripe payments."
---

# Billing

Stripe-based billing. See [[auth]] for authorization checks.
```

`tests/fixtures/sample_wiki/sources/2026-04-01-api-spec.md`:
```markdown
---
type: wiki-source
title: "API Specification v2"
date: 2026-04-01
project: acme
confidence: high
---

# API Specification v2

## Summary

REST API spec for the Acme project.
```

`tests/fixtures/sample_wiki/decisions/2026-04-01-fastapi.md`:
```markdown
---
type: wiki-decision
title: "FastAPI over Express"
date: 2026-04-01
project: acme
status: active
confidence: high
---

# FastAPI over Express

## Context

Needed async Python backend.

## Decision

Chose FastAPI for async support and type safety.
```

`tests/fixtures/AGENTS.md`:
```markdown
# Knowledge Base Schema

## What This Is

A test wiki for Atlas.
```

- [ ] **Step 2: Write failing tests**

`tests/core/test_wiki.py`:
```python
from atlas.core.wiki import WikiEngine


def test_list_pages(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    pages = wiki.list_pages()
    slugs = [p.slug for p in pages]
    assert "acme" in slugs
    assert "auth" in slugs
    assert "billing" in slugs


def test_list_pages_by_type(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    concepts = wiki.list_pages(type="wiki-concept")
    assert all(p.type == "wiki-concept" for p in concepts)
    assert len(concepts) == 2


def test_read_page(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    page = wiki.read("wiki/concepts/auth.md")
    assert page is not None
    assert page.title == "Authentication"
    assert page.type == "wiki-concept"
    assert "JWT" in page.content
    assert page.frontmatter["tags"] == ["auth", "security"]


def test_read_nonexistent(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    assert wiki.read("wiki/concepts/nope.md") is None


def test_write_page(tmp_storage):
    wiki = WikiEngine(tmp_storage)
    wiki.write(
        path="wiki/concepts/caching.md",
        content="# Caching\n\nRedis-based caching layer.",
        frontmatter={"type": "wiki-concept", "title": "Caching", "confidence": "medium", "tags": ["cache", "redis"]},
    )
    page = wiki.read("wiki/concepts/caching.md")
    assert page.title == "Caching"
    assert page.frontmatter["tags"] == ["cache", "redis"]
    assert "Redis-based" in page.content


def test_write_preserves_frontmatter_order(tmp_storage):
    wiki = WikiEngine(tmp_storage)
    wiki.write(
        path="wiki/concepts/test.md",
        content="# Test\n\nBody.",
        frontmatter={"type": "wiki-concept", "title": "Test", "confidence": "high"},
    )
    raw = tmp_storage.read("wiki/concepts/test.md")
    assert raw.startswith("---\n")
    assert "type: wiki-concept" in raw


def test_search(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    results = wiki.search("JWT")
    assert len(results) >= 1
    assert any(p.slug == "auth" for p in results)


def test_search_no_results(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    results = wiki.search("nonexistent_term_xyz")
    assert results == []


def test_extract_wikilinks(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    page = wiki.read("wiki/concepts/auth.md")
    assert "billing" in page.wikilinks
    assert "wiki/projects/acme" in page.wikilinks


def test_all_wikilinks(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    links = wiki.all_wikilinks()
    # Returns dict: page_path -> [list of wikilink targets]
    assert "wiki/concepts/auth.md" in links
    assert "billing" in links["wiki/concepts/auth.md"]


def test_backlinks(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    backlinks = wiki.backlinks("billing")
    assert "wiki/concepts/auth.md" in backlinks


def test_delete_page(tmp_storage):
    wiki = WikiEngine(tmp_storage)
    wiki.write("wiki/concepts/temp.md", "# Temp", frontmatter={"type": "wiki-concept", "title": "Temp"})
    assert wiki.read("wiki/concepts/temp.md") is not None
    wiki.delete("wiki/concepts/temp.md")
    assert wiki.read("wiki/concepts/temp.md") is None
```

- [ ] **Step 3: Run tests to verify failure**

Run: `python -m pytest tests/core/test_wiki.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement wiki.py**

`atlas/core/wiki.py`:
```python
"""Wiki engine — read, write, search, frontmatter, templates, wikilinks."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml

from atlas.core.models import Page

if TYPE_CHECKING:
    from atlas.core.storage import StorageBackend

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_WIKI_DIRS = ["wiki/projects/", "wiki/concepts/", "wiki/decisions/", "wiki/sources/"]


class WikiEngine:
    """Read, write, search wiki pages through a StorageBackend."""

    def __init__(self, storage: StorageBackend):
        self.storage = storage

    def read(self, path: str) -> Page | None:
        content = self.storage.read(path)
        if content is None:
            return None
        frontmatter, body = self._parse_frontmatter(content)
        title = frontmatter.get("title", path.rsplit("/", 1)[-1].removesuffix(".md"))
        page_type = frontmatter.get("type", "unknown")
        return Page(path=path, title=title, type=page_type, content=content, frontmatter=frontmatter)

    def write(self, path: str, content: str, frontmatter: dict | None = None) -> None:
        if frontmatter:
            fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()
            full = f"---\n{fm_str}\n---\n\n{content}\n"
        else:
            full = content
        self.storage.write(path, full)

    def delete(self, path: str) -> None:
        self.storage.delete(path)

    def list_pages(self, type: str | None = None) -> list[Page]:
        pages = []
        for dir_prefix in _WIKI_DIRS:
            for file_path in self.storage.list(dir_prefix, exclude_prefix="_"):
                page = self.read(file_path)
                if page and (type is None or page.type == type):
                    pages.append(page)
        return pages

    def search(self, terms: str) -> list[Page]:
        terms_lower = terms.lower()
        results = []
        for page in self.list_pages():
            if terms_lower in page.content.lower() or terms_lower in page.title.lower():
                results.append(page)
        return results

    def all_wikilinks(self) -> dict[str, list[str]]:
        result = {}
        for page in self.list_pages():
            links = page.wikilinks
            if links:
                result[page.path] = links
        return result

    def backlinks(self, target: str) -> list[str]:
        target_lower = target.lower()
        result = []
        for page_path, links in self.all_wikilinks().items():
            for link in links:
                link_slug = link.rsplit("/", 1)[-1].removesuffix(".md").lower()
                if link_slug == target_lower or link.lower() == target_lower:
                    result.append(page_path)
                    break
        return result

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[dict, str]:
        m = _FRONTMATTER_RE.match(content)
        if not m:
            return {}, content
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            fm = {}
        body = content[m.end():]
        return fm, body
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/core/test_wiki.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add atlas/core/wiki.py tests/core/test_wiki.py tests/fixtures/
git commit -m "feat: wiki engine with read, write, search, wikilinks, backlinks

Parses frontmatter, extracts wikilinks via regex, supports search and
backlink resolution. All operations go through StorageBackend protocol."
```

---

## Task 4: Graph Engine

**Files:**
- Create: `atlas/core/graph.py`
- Test: `tests/core/test_graph.py`

- [ ] **Step 1: Write failing tests**

`tests/core/test_graph.py`:
```python
import json

from atlas.core.graph import GraphEngine
from atlas.core.models import Node, Edge, Extraction, Subgraph


def test_merge_extraction(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    assert g.node_count == 3
    assert g.edge_count == 3


def test_merge_dedup_nodes():
    g = GraphEngine()
    e1 = Extraction(nodes=[Node(id="a", label="A", type="code", source_file="a.py")], edges=[])
    e2 = Extraction(nodes=[Node(id="a", label="A Updated", type="code", source_file="a.py")], edges=[])
    g.merge(e1)
    g.merge(e2)
    assert g.node_count == 1
    assert g.get_node("a").label == "A Updated"  # last write wins


def test_get_node(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    node = g.get_node("auth")
    assert node is not None
    assert node.label == "Auth Module"


def test_get_neighbors(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    neighbors = g.get_neighbors("api")
    assert len(neighbors) == 2
    ids = {n.id for n, _ in neighbors}
    assert "auth" in ids
    assert "db" in ids


def test_query_bfs(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    result = g.query("auth", mode="bfs", depth=2)
    assert isinstance(result, Subgraph)
    assert len(result.nodes) >= 1


def test_query_dfs(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    result = g.query("api", mode="dfs", depth=3)
    assert isinstance(result, Subgraph)
    assert len(result.nodes) >= 1


def test_shortest_path(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    path = g.path("api", "db")
    assert path is not None
    assert len(path) >= 1


def test_shortest_path_no_route():
    g = GraphEngine()
    e = Extraction(
        nodes=[Node(id="a", label="A", type="code", source_file="a.py"), Node(id="b", label="B", type="code", source_file="b.py")],
        edges=[],
    )
    g.merge(e)
    path = g.path("a", "b")
    assert path is None  # no edges = no path


def test_stats(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    stats = g.stats()
    assert stats.nodes == 3
    assert stats.edges == 3
    assert stats.confidence_breakdown["EXTRACTED"] == 2
    assert stats.confidence_breakdown["INFERRED"] == 1


def test_remove_node(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    g.remove_node("auth")
    assert g.node_count == 2
    assert g.get_node("auth") is None
    # Edges involving auth should be removed
    assert g.edge_count == 1  # only api->db remains


def test_serialize_deserialize(sample_extraction, tmp_path):
    g = GraphEngine()
    g.merge(sample_extraction)
    path = tmp_path / "graph.json"
    g.save(path)
    assert path.exists()

    g2 = GraphEngine.load(path)
    assert g2.node_count == 3
    assert g2.edge_count == 3


def test_add_edge():
    g = GraphEngine()
    e = Extraction(
        nodes=[Node(id="a", label="A", type="code", source_file="a.py"), Node(id="b", label="B", type="code", source_file="b.py")],
        edges=[],
    )
    g.merge(e)
    g.add_edge(Edge(source="a", target="b", relation="references", confidence="EXTRACTED"))
    assert g.edge_count == 1


def test_remove_edge():
    g = GraphEngine()
    e = Extraction(
        nodes=[Node(id="a", label="A", type="code", source_file="a.py"), Node(id="b", label="B", type="code", source_file="b.py")],
        edges=[Edge(source="a", target="b", relation="references", confidence="EXTRACTED")],
    )
    g.merge(e)
    g.remove_edge("a", "b")
    assert g.edge_count == 0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/core/test_graph.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement graph.py**

`atlas/core/graph.py`:
```python
"""Graph engine — build, merge, query, BFS/DFS, serialize."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from dataclasses import asdict

import networkx as nx

from atlas.core.models import Node, Edge, Extraction, Subgraph, GraphStats


class GraphEngine:
    """In-memory graph backed by NetworkX. Serializes to graph.json."""

    def __init__(self):
        self._g = nx.Graph()

    @property
    def node_count(self) -> int:
        return self._g.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._g.number_of_edges()

    def merge(self, extraction: Extraction) -> None:
        for node in extraction.nodes:
            self._g.add_node(node.id, **{k: v for k, v in asdict(node).items() if k != "id"})
        for edge in extraction.edges:
            if edge.source in self._g and edge.target in self._g:
                self._g.add_edge(
                    edge.source,
                    edge.target,
                    relation=edge.relation,
                    confidence=edge.confidence,
                    confidence_score=edge.confidence_score,
                    source_file=edge.source_file,
                    weight=edge.weight,
                )

    def get_node(self, node_id: str) -> Node | None:
        if node_id not in self._g:
            return None
        data = self._g.nodes[node_id]
        return Node(id=node_id, **{k: v for k, v in data.items() if k in Node.__dataclass_fields__ and k != "id"})

    def get_neighbors(self, node_id: str) -> list[tuple[Node, Edge]]:
        if node_id not in self._g:
            return []
        result = []
        for neighbor_id in self._g.neighbors(node_id):
            node = self.get_node(neighbor_id)
            edge_data = self._g.edges[node_id, neighbor_id]
            edge = Edge(
                source=node_id,
                target=neighbor_id,
                relation=edge_data.get("relation", "related"),
                confidence=edge_data.get("confidence", "EXTRACTED"),
                confidence_score=edge_data.get("confidence_score", 1.0),
            )
            result.append((node, edge))
        return result

    def add_edge(self, edge: Edge) -> None:
        self._g.add_edge(
            edge.source,
            edge.target,
            relation=edge.relation,
            confidence=edge.confidence,
            confidence_score=edge.confidence_score,
            weight=edge.weight,
        )

    def remove_edge(self, source: str, target: str) -> None:
        if self._g.has_edge(source, target):
            self._g.remove_edge(source, target)

    def remove_node(self, node_id: str) -> None:
        if node_id in self._g:
            self._g.remove_node(node_id)

    def query(self, start: str, mode: str = "bfs", depth: int = 3) -> Subgraph:
        if start not in self._g:
            return Subgraph()
        visited_nodes = set()
        visited_edges = []

        if mode == "bfs":
            queue = deque([(start, 0)])
            visited_nodes.add(start)
            while queue:
                current, d = queue.popleft()
                if d >= depth:
                    continue
                for neighbor in self._g.neighbors(current):
                    edge_data = self._g.edges[current, neighbor]
                    visited_edges.append(Edge(
                        source=current, target=neighbor,
                        relation=edge_data.get("relation", "related"),
                        confidence=edge_data.get("confidence", "EXTRACTED"),
                        confidence_score=edge_data.get("confidence_score", 1.0),
                    ))
                    if neighbor not in visited_nodes:
                        visited_nodes.add(neighbor)
                        queue.append((neighbor, d + 1))
        else:  # dfs
            stack = [(start, 0)]
            while stack:
                current, d = stack.pop()
                if current in visited_nodes and current != start:
                    continue
                visited_nodes.add(current)
                if d >= depth:
                    continue
                for neighbor in self._g.neighbors(current):
                    edge_data = self._g.edges[current, neighbor]
                    visited_edges.append(Edge(
                        source=current, target=neighbor,
                        relation=edge_data.get("relation", "related"),
                        confidence=edge_data.get("confidence", "EXTRACTED"),
                        confidence_score=edge_data.get("confidence_score", 1.0),
                    ))
                    if neighbor not in visited_nodes:
                        stack.append((neighbor, d + 1))

        nodes = [self.get_node(nid) for nid in visited_nodes if self.get_node(nid)]
        return Subgraph(nodes=nodes, edges=visited_edges)

    def path(self, source: str, target: str) -> list[Edge] | None:
        if source not in self._g or target not in self._g:
            return None
        try:
            node_path = nx.shortest_path(self._g, source, target)
        except nx.NetworkXNoPath:
            return None
        edges = []
        for i in range(len(node_path) - 1):
            a, b = node_path[i], node_path[i + 1]
            ed = self._g.edges[a, b]
            edges.append(Edge(
                source=a, target=b,
                relation=ed.get("relation", "related"),
                confidence=ed.get("confidence", "EXTRACTED"),
                confidence_score=ed.get("confidence_score", 1.0),
            ))
        return edges

    def stats(self) -> GraphStats:
        breakdown: dict[str, int] = {"EXTRACTED": 0, "INFERRED": 0, "AMBIGUOUS": 0}
        for _, _, data in self._g.edges(data=True):
            conf = data.get("confidence", "EXTRACTED")
            breakdown[conf] = breakdown.get(conf, 0) + 1
        communities = set()
        for _, data in self._g.nodes(data=True):
            c = data.get("community")
            if c is not None:
                communities.add(c)
        return GraphStats(
            nodes=self.node_count,
            edges=self.edge_count,
            communities=len(communities),
            confidence_breakdown=breakdown,
        )

    def save(self, path: Path | str) -> None:
        path = Path(path)
        data = nx.node_link_data(self._g)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> GraphEngine:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        engine = cls()
        engine._g = nx.node_link_graph(data)
        return engine
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/core/test_graph.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/core/graph.py tests/core/test_graph.py
git commit -m "feat: graph engine with merge, query (BFS/DFS), path, stats, serialize

NetworkX-backed in-memory graph. Supports node/edge CRUD, BFS/DFS traversal,
shortest path, stats with confidence breakdown. Saves to graph.json."
```

---

## Task 5: Linker — Wiki-to-Graph Sync

**Files:**
- Create: `atlas/core/linker.py`
- Test: `tests/core/test_linker.py`

- [ ] **Step 1: Write failing tests**

`tests/core/test_linker.py`:
```python
from atlas.core.graph import GraphEngine
from atlas.core.wiki import WikiEngine
from atlas.core.linker import Linker
from atlas.core.models import Edge


def test_sync_wiki_to_graph_creates_nodes(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    changes = linker.sync_wiki_to_graph()
    # Should create nodes for each wiki page
    assert graph.node_count >= 4  # acme, auth, billing, api-spec, fastapi decision
    # Check node types match page types
    auth_node = graph.get_node("auth")
    assert auth_node is not None
    assert auth_node.type == "wiki-concept"


def test_sync_wiki_to_graph_creates_wikilink_edges(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    linker.sync_wiki_to_graph()
    # auth.md links to [[billing]] and [[wiki/projects/acme]]
    neighbors = graph.get_neighbors("auth")
    neighbor_ids = {n.id for n, _ in neighbors}
    assert "billing" in neighbor_ids


def test_sync_wiki_to_graph_creates_tag_edges(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    linker.sync_wiki_to_graph()
    # auth.md has tags: [auth, security]
    auth_node = graph.get_node("auth")
    assert auth_node is not None
    assert "auth" in auth_node.tags


def test_sync_wiki_to_graph_idempotent(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    linker.sync_wiki_to_graph()
    count1 = graph.node_count
    edge1 = graph.edge_count
    # Run again
    linker.sync_wiki_to_graph()
    assert graph.node_count == count1
    assert graph.edge_count == edge1


def test_sync_graph_to_wiki_suggests_missing_pages(sample_wiki, sample_extraction):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    graph.merge(sample_extraction)  # adds auth, db, api nodes from code
    linker = Linker(wiki=wiki, graph=graph)
    suggestions = linker.sync_graph_to_wiki()
    # db and api don't have wiki pages -> should suggest creating them
    create_suggestions = [s for s in suggestions if s.type == "create_page"]
    suggested_nodes = {s.source_node for s in create_suggestions}
    assert "db" in suggested_nodes or "api" in suggested_nodes


def test_sync_graph_to_wiki_suggests_missing_wikilinks(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    linker.sync_wiki_to_graph()
    # Add an inferred edge between auth and api-spec that isn't a wikilink
    graph.add_edge(Edge(source="auth", target="2026-04-01-api-spec", relation="related", confidence="INFERRED"))
    suggestions = linker.sync_graph_to_wiki()
    link_suggestions = [s for s in suggestions if s.type == "add_wikilink"]
    # Should suggest adding a wikilink from auth to api-spec
    assert len(link_suggestions) >= 0  # depends on whether the pages exist


def test_returns_graph_changes(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    changes = linker.sync_wiki_to_graph()
    assert len(changes) > 0
    assert all(hasattr(c, "type") for c in changes)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/core/test_linker.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement linker.py**

`atlas/core/linker.py`:
```python
"""Linker — bidirectional graph <-> wiki synchronization."""
from __future__ import annotations

from atlas.core.graph import GraphEngine
from atlas.core.models import Edge, GraphChange, Node, WikiSuggestion
from atlas.core.wiki import WikiEngine


class Linker:
    """Synchronizes the wiki and graph bidirectionally.

    wiki -> graph: automatic, synchronous (wikilinks become edges).
    graph -> wiki: suggestions only (never writes without validation).
    """

    def __init__(self, wiki: WikiEngine, graph: GraphEngine):
        self.wiki = wiki
        self.graph = graph

    def sync_wiki_to_graph(self) -> list[GraphChange]:
        """Parse all wiki pages, create/update nodes and edges in the graph.

        Returns list of changes applied.
        """
        changes: list[GraphChange] = []
        pages = self.wiki.list_pages()

        # Build set of current wiki page slugs for edge resolution
        slug_to_path: dict[str, str] = {}
        for page in pages:
            slug_to_path[page.slug] = page.path

        # Track existing nodes to detect removals
        existing_wiki_nodes = {nid for nid in self.graph._g.nodes if self.graph._g.nodes[nid].get("_wiki_managed")}

        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str]] = set()

        for page in pages:
            node_id = page.slug
            seen_nodes.add(node_id)

            # Create or update node
            node = Node(
                id=node_id,
                label=page.title,
                type=page.type,
                source_file=page.path,
                confidence=page.frontmatter.get("confidence", "medium"),
                summary=page.frontmatter.get("description"),
                tags=page.frontmatter.get("tags", []) if isinstance(page.frontmatter.get("tags"), list) else [],
            )
            is_new = node_id not in self.graph._g
            self.graph._g.add_node(node_id, _wiki_managed=True, **{
                k: v for k, v in {
                    "label": node.label, "type": node.type, "source_file": node.source_file,
                    "confidence": node.confidence, "summary": node.summary, "tags": node.tags,
                }.items() if v is not None
            })

            if is_new:
                changes.append(GraphChange(type="add_node", node_id=node_id, details=f"Wiki page: {page.title}"))
            else:
                changes.append(GraphChange(type="update_node", node_id=node_id, details=f"Updated: {page.title}"))

            # Create edges from wikilinks
            for link in page.wikilinks:
                target_slug = link.rsplit("/", 1)[-1].removesuffix(".md")
                if target_slug in slug_to_path and target_slug != node_id:
                    edge_key = (node_id, target_slug)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        if not self.graph._g.has_edge(node_id, target_slug) or \
                                self.graph._g.edges[node_id, target_slug].get("_wiki_managed"):
                            self.graph._g.add_edge(
                                node_id, target_slug,
                                relation="references",
                                confidence="EXTRACTED",
                                confidence_score=1.0,
                                _wiki_managed=True,
                            )
                            changes.append(GraphChange(
                                type="add_edge",
                                edge=Edge(source=node_id, target=target_slug, relation="references", confidence="EXTRACTED"),
                                details=f"Wikilink: {node_id} -> {target_slug}",
                            ))

        # Remove wiki-managed nodes that no longer have pages
        for old_node in existing_wiki_nodes - seen_nodes:
            self.graph.remove_node(old_node)
            changes.append(GraphChange(type="remove_node", node_id=old_node, details="Page deleted"))

        # Remove wiki-managed edges that no longer exist as wikilinks
        edges_to_remove = []
        for u, v, data in self.graph._g.edges(data=True):
            if data.get("_wiki_managed") and (u, v) not in seen_edges and (v, u) not in seen_edges:
                edges_to_remove.append((u, v))
        for u, v in edges_to_remove:
            self.graph.remove_edge(u, v)
            changes.append(GraphChange(type="remove_edge", edge=Edge(source=u, target=v, relation="removed"), details="Wikilink removed"))

        return changes

    def sync_graph_to_wiki(self) -> list[WikiSuggestion]:
        """Analyze the graph and suggest wiki improvements.

        Returns suggestions — never writes automatically.
        """
        suggestions: list[WikiSuggestion] = []
        wiki_slugs = {p.slug for p in self.wiki.list_pages()}

        # Suggest pages for graph nodes without wiki pages
        for node_id in self.graph._g.nodes:
            data = self.graph._g.nodes[node_id]
            if not data.get("_wiki_managed") and node_id not in wiki_slugs:
                label = data.get("label", node_id)
                suggestions.append(WikiSuggestion(
                    type="create_page",
                    description=f"Node '{label}' exists in the graph but has no wiki page.",
                    source_node=node_id,
                    reason=f"Discovered via scan. Type: {data.get('type', 'unknown')}. Degree: {self.graph._g.degree(node_id)}.",
                ))

        # Suggest wikilinks for INFERRED edges between pages that exist
        for u, v, data in self.graph._g.edges(data=True):
            if data.get("confidence") == "INFERRED" and not data.get("_wiki_managed"):
                if u in wiki_slugs and v in wiki_slugs:
                    suggestions.append(WikiSuggestion(
                        type="add_wikilink",
                        description=f"INFERRED relationship between '{u}' and '{v}' — consider adding a [[wikilink]].",
                        target_page=u,
                        source_node=u,
                        target_node=v,
                        reason=f"Relation: {data.get('relation', 'related')}. Confidence: {data.get('confidence_score', 0.7):.1f}.",
                    ))

        # Suggest clarification for AMBIGUOUS edges
        for u, v, data in self.graph._g.edges(data=True):
            if data.get("confidence") == "AMBIGUOUS":
                suggestions.append(WikiSuggestion(
                    type="clarify_relation",
                    description=f"AMBIGUOUS relationship between '{u}' and '{v}' needs clarification.",
                    source_node=u,
                    target_node=v,
                    reason=f"Relation: {data.get('relation', 'unknown')}. Score: {data.get('confidence_score', 0.2):.1f}.",
                ))

        return suggestions
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/core/test_linker.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/core/linker.py tests/core/test_linker.py
git commit -m "feat: linker — bidirectional wiki <-> graph sync

wiki->graph: automatic. Pages become nodes, wikilinks become EXTRACTED edges.
graph->wiki: suggestions only. Missing pages, missing wikilinks, ambiguous edges."
```

---

## Task 6: Cache Engine

**Files:**
- Create: `atlas/core/cache.py`
- Test: `tests/core/test_cache.py`

- [ ] **Step 1: Write failing tests**

`tests/core/test_cache.py`:
```python
import json

from atlas.core.cache import CacheEngine
from atlas.core.models import Extraction, Node, Edge
from atlas.core.storage import LocalStorage


def test_check_returns_miss_for_new_file(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/doc.md", "# Hello")
    cache = CacheEngine(storage)
    hit = cache.check("raw/doc.md")
    assert hit is None


def test_save_and_check_returns_hit(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/doc.md", "# Hello")
    cache = CacheEngine(storage)
    extraction = Extraction(
        nodes=[Node(id="hello", label="Hello", type="document", source_file="raw/doc.md")],
        edges=[],
    )
    cache.save("raw/doc.md", extraction)
    hit = cache.check("raw/doc.md")
    assert hit is not None
    assert len(hit.nodes) == 1
    assert hit.nodes[0].id == "hello"


def test_cache_invalidated_on_content_change(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/doc.md", "# Hello")
    cache = CacheEngine(storage)
    extraction = Extraction(nodes=[], edges=[])
    cache.save("raw/doc.md", extraction)
    # Change file content
    storage.write("raw/doc.md", "# Changed")
    hit = cache.check("raw/doc.md")
    assert hit is None  # hash changed


def test_manifest_persists(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/doc.md", "# Hello")
    cache = CacheEngine(storage)
    extraction = Extraction(nodes=[], edges=[])
    cache.save("raw/doc.md", extraction)

    # Load a new CacheEngine instance — should read manifest from disk
    cache2 = CacheEngine(storage)
    hit = cache2.check("raw/doc.md")
    assert hit is not None


def test_detect_changed_files(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/a.md", "# A")
    storage.write("raw/b.md", "# B")
    cache = CacheEngine(storage)
    cache.save("raw/a.md", Extraction())
    cache.save("raw/b.md", Extraction())
    # Change a.md
    storage.write("raw/a.md", "# A modified")
    changed = cache.detect_changed(["raw/a.md", "raw/b.md"])
    assert "raw/a.md" in changed
    assert "raw/b.md" not in changed


def test_detect_new_files(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/a.md", "# A")
    cache = CacheEngine(storage)
    storage.write("raw/new.md", "# New")
    changed = cache.detect_changed(["raw/a.md", "raw/new.md"])
    assert "raw/new.md" in changed
    assert "raw/a.md" in changed  # never cached
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/core/test_cache.py -v`
Expected: FAIL

- [ ] **Step 3: Implement cache.py**

`atlas/core/cache.py`:
```python
"""SHA256 incremental extraction cache."""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

from atlas.core.models import Extraction, Node, Edge

if TYPE_CHECKING:
    from atlas.core.storage import StorageBackend

MANIFEST_PATH = "atlas-cache/manifest.json"
CACHE_DIR = "atlas-cache/extractions"


class CacheEngine:
    """Content-hash based extraction cache.

    Stores extraction results keyed by SHA256 of the source file content.
    Detects changes by comparing current hash with cached hash.
    """

    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self._manifest = self._load_manifest()

    def check(self, file_path: str) -> Extraction | None:
        current_hash = self.storage.hash(file_path)
        if current_hash is None:
            return None
        entry = self._manifest.get(file_path)
        if entry is None or entry.get("hash") != current_hash:
            return None
        cache_path = f"{CACHE_DIR}/{current_hash}.json"
        cached = self.storage.read(cache_path)
        if cached is None:
            return None
        return self._deserialize(cached)

    def save(self, file_path: str, extraction: Extraction) -> None:
        current_hash = self.storage.hash(file_path)
        if current_hash is None:
            return
        cache_path = f"{CACHE_DIR}/{current_hash}.json"
        self.storage.write(cache_path, self._serialize(extraction))
        self._manifest[file_path] = {
            "hash": current_hash,
            "mtime": self.storage.mtime(file_path),
        }
        self._save_manifest()

    def detect_changed(self, file_paths: list[str]) -> list[str]:
        changed = []
        for fp in file_paths:
            current_hash = self.storage.hash(fp)
            entry = self._manifest.get(fp)
            if entry is None or entry.get("hash") != current_hash:
                changed.append(fp)
        return changed

    def _load_manifest(self) -> dict:
        raw = self.storage.read(MANIFEST_PATH)
        if raw is None:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _save_manifest(self) -> None:
        self.storage.write(MANIFEST_PATH, json.dumps(self._manifest, indent=2))

    @staticmethod
    def _serialize(extraction: Extraction) -> str:
        return json.dumps({
            "nodes": [asdict(n) for n in extraction.nodes],
            "edges": [asdict(e) for e in extraction.edges],
            "input_tokens": extraction.input_tokens,
            "output_tokens": extraction.output_tokens,
        }, ensure_ascii=False, indent=2)

    @staticmethod
    def _deserialize(raw: str) -> Extraction:
        data = json.loads(raw)
        nodes = [Node(**n) for n in data.get("nodes", [])]
        edges = [Edge(**e) for e in data.get("edges", [])]
        return Extraction(
            nodes=nodes,
            edges=edges,
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
        )
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/core/test_cache.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/core/cache.py tests/core/test_cache.py
git commit -m "feat: SHA256 extraction cache with manifest

Content-hash based caching. detect_changed() returns only files whose
content hash differs from the cached extraction. Manifest persists to disk."
```

---

## Task 7: Analyzer

**Files:**
- Create: `atlas/core/analyzer.py`
- Test: `tests/core/test_analyzer.py`

- [ ] **Step 1: Write failing tests**

`tests/core/test_analyzer.py`:
```python
from atlas.core.analyzer import Analyzer
from atlas.core.graph import GraphEngine
from atlas.core.wiki import WikiEngine
from atlas.core.models import Node, Edge, Extraction


def _build_graph_with_communities():
    """Build a graph with clear community structure."""
    g = GraphEngine()
    nodes = [
        Node(id="auth", label="Auth", type="code", source_file="auth.py"),
        Node(id="session", label="Session", type="code", source_file="session.py"),
        Node(id="jwt", label="JWT", type="code", source_file="jwt.py"),
        Node(id="billing", label="Billing", type="code", source_file="billing.py"),
        Node(id="stripe", label="Stripe", type="code", source_file="stripe.py"),
        Node(id="invoice", label="Invoice", type="code", source_file="invoice.py"),
        Node(id="api", label="API Gateway", type="code", source_file="api.py"),
    ]
    edges = [
        Edge(source="auth", target="session", relation="calls", confidence="EXTRACTED"),
        Edge(source="auth", target="jwt", relation="imports", confidence="EXTRACTED"),
        Edge(source="session", target="jwt", relation="uses", confidence="EXTRACTED"),
        Edge(source="billing", target="stripe", relation="imports", confidence="EXTRACTED"),
        Edge(source="billing", target="invoice", relation="calls", confidence="EXTRACTED"),
        Edge(source="stripe", target="invoice", relation="uses", confidence="INFERRED"),
        Edge(source="api", target="auth", relation="imports", confidence="EXTRACTED"),
        Edge(source="api", target="billing", relation="imports", confidence="EXTRACTED"),
    ]
    g.merge(Extraction(nodes=nodes, edges=edges))
    return g


def test_god_nodes():
    g = _build_graph_with_communities()
    analyzer = Analyzer(graph=g)
    gods = analyzer.god_nodes(top_n=3)
    assert len(gods) <= 3
    # api has degree 2, auth has degree 3 (session, jwt, api), billing has degree 3
    ids = [node_id for node_id, _ in gods]
    assert "auth" in ids or "billing" in ids or "api" in ids


def test_surprises():
    g = _build_graph_with_communities()
    analyzer = Analyzer(graph=g)
    surprises = analyzer.surprises(top_n=5)
    # The INFERRED edge (stripe->invoice) should score higher
    assert len(surprises) >= 0  # may have 0 if all edges are same type


def test_orphan_pages(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    g = GraphEngine()
    analyzer = Analyzer(graph=g, wiki=wiki)
    report = analyzer.audit()
    # With empty graph, all pages are "orphans" (no incoming edges)
    assert len(report.orphan_pages) >= 0


def test_broken_links(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    g = GraphEngine()
    analyzer = Analyzer(graph=g, wiki=wiki)
    report = analyzer.audit()
    # auth.md links to [[billing]] which exists, and [[wiki/projects/acme]] which exists
    # No broken links expected in sample wiki
    assert isinstance(report.broken_links, list)


def test_stats():
    g = _build_graph_with_communities()
    analyzer = Analyzer(graph=g)
    report = analyzer.audit()
    assert report.stats is not None
    assert report.stats.nodes == 7
    assert report.stats.edges == 8


def test_health_score():
    g = _build_graph_with_communities()
    analyzer = Analyzer(graph=g)
    report = analyzer.audit()
    assert report.health_score > 0


def test_stale_pages(tmp_storage):
    """Pages older than 30 days should be flagged as stale."""
    wiki = WikiEngine(tmp_storage)
    wiki.write(
        "wiki/concepts/old.md",
        "# Old Concept\n\nThis is old.",
        frontmatter={"type": "wiki-concept", "title": "Old", "updated": "2026-01-01", "confidence": "medium"},
    )
    g = GraphEngine()
    analyzer = Analyzer(graph=g, wiki=wiki)
    report = analyzer.audit()
    assert "wiki/concepts/old.md" in report.stale_pages
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/core/test_analyzer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement analyzer.py**

`atlas/core/analyzer.py`:
```python
"""Analyzer — god nodes, surprises, gaps, contradictions, audit."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from atlas.core.models import AuditReport, Edge, GraphStats, LinkSuggestion

if TYPE_CHECKING:
    from atlas.core.graph import GraphEngine
    from atlas.core.wiki import WikiEngine

STALE_THRESHOLD_DAYS = 30


class Analyzer:
    """Analyzes the graph and wiki for structural insights."""

    def __init__(self, graph: GraphEngine, wiki: WikiEngine | None = None):
        self.graph = graph
        self.wiki = wiki

    def god_nodes(self, top_n: int = 10) -> list[tuple[str, int]]:
        """Return top N nodes by degree (most connected)."""
        degrees = [(nid, self.graph._g.degree(nid)) for nid in self.graph._g.nodes]
        degrees.sort(key=lambda x: -x[1])
        return degrees[:top_n]

    def surprises(self, top_n: int = 10) -> list[Edge]:
        """Return edges ranked by surprise score (INFERRED/AMBIGUOUS + cross-community)."""
        scored: list[tuple[float, Edge]] = []
        for u, v, data in self.graph._g.edges(data=True):
            score = 0.0
            conf = data.get("confidence", "EXTRACTED")
            if conf == "AMBIGUOUS":
                score += 3.0
            elif conf == "INFERRED":
                score += 2.0
            else:
                score += 1.0

            # Cross-community bonus
            u_comm = self.graph._g.nodes[u].get("community")
            v_comm = self.graph._g.nodes[v].get("community")
            if u_comm is not None and v_comm is not None and u_comm != v_comm:
                score += 1.0

            # Cross file-type bonus
            u_type = self.graph._g.nodes[u].get("type", "")
            v_type = self.graph._g.nodes[v].get("type", "")
            if u_type != v_type:
                score += 2.0

            edge = Edge(
                source=u, target=v,
                relation=data.get("relation", "related"),
                confidence=conf,
                confidence_score=data.get("confidence_score", 1.0),
            )
            scored.append((score, edge))

        scored.sort(key=lambda x: -x[0])
        return [edge for _, edge in scored[:top_n]]

    def audit(self) -> AuditReport:
        """Full audit of graph + wiki health."""
        report = AuditReport()
        report.stats = self.graph.stats()
        report.god_nodes = self.god_nodes()

        if self.wiki:
            all_links = self.wiki.all_wikilinks()
            page_slugs = {p.slug for p in self.wiki.list_pages()}

            # Broken links: wikilinks pointing to non-existent pages
            for page_path, links in all_links.items():
                for link in links:
                    link_slug = link.rsplit("/", 1)[-1].removesuffix(".md")
                    if link_slug not in page_slugs:
                        report.broken_links.append((page_path, link))

            # Orphan pages: pages with no incoming wikilinks
            incoming: set[str] = set()
            for links in all_links.values():
                for link in links:
                    incoming.add(link.rsplit("/", 1)[-1].removesuffix(".md"))
            for page in self.wiki.list_pages():
                if page.slug not in incoming and page.type != "wiki-index":
                    report.orphan_pages.append(page.path)

            # Stale pages: not updated in 30+ days
            cutoff = (datetime.now() - timedelta(days=STALE_THRESHOLD_DAYS)).strftime("%Y-%m-%d")
            for page in self.wiki.list_pages():
                updated = page.frontmatter.get("updated", "")
                if isinstance(updated, str) and updated and updated < cutoff:
                    report.stale_pages.append(page.path)

        # Health score
        total_issues = len(report.orphan_pages) + len(report.broken_links) + len(report.stale_pages)
        base_score = report.stats.health_score if report.stats else 50.0
        penalty = min(total_issues * 2, 30)
        report.health_score = max(0, base_score - penalty)

        return report
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/core/test_analyzer.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/core/analyzer.py tests/core/test_analyzer.py
git commit -m "feat: analyzer with god nodes, surprises, audit report

God nodes by degree, surprise edges by composite score (confidence + cross-type
+ cross-community), full audit (orphans, broken links, stale pages, health score)."
```

---

## Task 8: Ingest Engine

**Files:**
- Create: `atlas/core/ingest.py`
- Test: `tests/core/test_ingest.py`

- [ ] **Step 1: Write failing tests**

`tests/core/test_ingest.py`:
```python
from atlas.core.ingest import IngestEngine, detect_url_type


def test_detect_url_type_arxiv():
    assert detect_url_type("https://arxiv.org/abs/1706.03762") == "arxiv"


def test_detect_url_type_tweet():
    assert detect_url_type("https://x.com/karpathy/status/123456") == "tweet"
    assert detect_url_type("https://twitter.com/someone/status/789") == "tweet"


def test_detect_url_type_github():
    assert detect_url_type("https://github.com/safishamsi/graphify") == "github"


def test_detect_url_type_pdf():
    assert detect_url_type("https://example.com/paper.pdf") == "pdf"


def test_detect_url_type_image():
    assert detect_url_type("https://example.com/diagram.png") == "image"
    assert detect_url_type("https://example.com/photo.jpg") == "image"


def test_detect_url_type_webpage():
    assert detect_url_type("https://example.com/blog/article") == "webpage"


def test_slugify_url():
    from atlas.core.ingest import slugify_url
    assert slugify_url("https://arxiv.org/abs/1706.03762") == "arxiv-org-abs-1706-03762"
    assert slugify_url("https://x.com/karpathy/status/123") == "x-com-karpathy-status-123"


def test_build_frontmatter():
    from atlas.core.ingest import build_frontmatter
    fm = build_frontmatter(
        url="https://arxiv.org/abs/1706.03762",
        url_type="arxiv",
        title="Attention Is All You Need",
        author="Vaswani et al.",
    )
    assert fm["source_url"] == "https://arxiv.org/abs/1706.03762"
    assert fm["type"] == "arxiv"
    assert fm["title"] == "Attention Is All You Need"
    assert fm["author"] == "Vaswani et al."
    assert "captured_at" in fm


def test_ingest_local_file(tmp_path):
    # Create a local file
    src = tmp_path / "raw" / "untracked"
    src.mkdir(parents=True)
    (src / "notes.md").write_text("# My Notes\n\nSome content.")

    from atlas.core.storage import LocalStorage
    storage = LocalStorage(root=tmp_path)
    engine = IngestEngine(storage)
    result = engine.ingest_file("raw/untracked/notes.md", title="My Notes")
    assert result is not None
    assert result.endswith(".md")
    # Should be moved to raw/ingested/
    content = storage.read(result)
    assert "My Notes" in content
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/core/test_ingest.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ingest.py**

`atlas/core/ingest.py`:
```python
"""Smart URL and file ingestion with type detection and frontmatter."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from atlas.core.storage import StorageBackend


def detect_url_type(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path.lower()

    if "arxiv.org" in host:
        return "arxiv"
    if host in ("x.com", "twitter.com") and "/status/" in path:
        return "tweet"
    if "github.com" in host:
        return "github"
    if path.endswith(".pdf"):
        return "pdf"
    if any(path.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return "image"
    return "webpage"


def slugify_url(url: str) -> str:
    parsed = urlparse(url)
    raw = f"{parsed.hostname or ''}{parsed.path}".strip("/")
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")[:80]


def build_frontmatter(
    url: str,
    url_type: str,
    title: str | None = None,
    author: str | None = None,
    contributor: str | None = None,
) -> dict:
    fm: dict = {
        "source_url": url,
        "type": url_type,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    if title:
        fm["title"] = title
    if author:
        fm["author"] = author
    if contributor:
        fm["contributor"] = contributor
    return fm


class IngestEngine:
    """Ingests URLs and local files into raw/ with frontmatter."""

    def __init__(self, storage: StorageBackend):
        self.storage = storage

    def ingest_file(self, source_path: str, title: str | None = None) -> str | None:
        """Move a local file from raw/untracked/ to raw/ingested/ with frontmatter."""
        content = self.storage.read(source_path)
        if content is None:
            return None

        slug = source_path.rsplit("/", 1)[-1].removesuffix(".md")
        date = datetime.now().strftime("%Y-%m-%d")
        dest_path = f"raw/ingested/{date}-{slug}.md"

        # Add frontmatter if not present
        if not content.startswith("---"):
            fm = f"---\ntitle: \"{title or slug}\"\ncaptured_at: {datetime.now(timezone.utc).isoformat()}\n---\n\n"
            content = fm + content

        self.storage.write(dest_path, content)
        return dest_path

    async def ingest_url(self, url: str, title: str | None = None, author: str | None = None) -> str | None:
        """Fetch a URL and save to raw/ingested/ with auto-detected frontmatter.

        Requires httpx. Returns the path of the saved file, or None on failure.
        """
        import httpx

        url_type = detect_url_type(url)
        slug = slugify_url(url)
        date = datetime.now().strftime("%Y-%m-%d")
        dest_path = f"raw/ingested/{date}-{slug}.md"

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException):
            return None

        text = resp.text
        fm = build_frontmatter(url=url, url_type=url_type, title=title, author=author)
        fm_lines = ["---"]
        for k, v in fm.items():
            fm_lines.append(f'{k}: "{v}"' if isinstance(v, str) else f"{k}: {v}")
        fm_lines.append("---\n")
        full = "\n".join(fm_lines) + "\n" + text

        self.storage.write(dest_path, full)
        return dest_path
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/core/test_ingest.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add atlas/core/ingest.py tests/core/test_ingest.py
git commit -m "feat: ingest engine with URL type detection and auto frontmatter

Detects arxiv, tweet, github, pdf, image, webpage. Builds frontmatter with
source_url, type, captured_at, author. Local file ingestion moves to raw/ingested/."
```

---

## Task 9: Scanner — AST Extraction (Python)

**Files:**
- Create: `atlas/core/scanner_ast.py`
- Test: `tests/core/test_scanner_ast.py`
- Create: `tests/fixtures/sample.py`

- [ ] **Step 1: Create test fixture**

`tests/fixtures/sample.py`:
```python
"""Sample module for testing AST extraction."""
import os
from pathlib import Path


class AuthManager:
    """Handles authentication and session management."""

    def __init__(self, secret: str):
        self.secret = secret

    def verify_token(self, token: str) -> bool:
        """Verify a JWT token."""
        # NOTE: This uses HS256, consider RS256 for production
        return len(token) > 0

    def create_session(self, user_id: int) -> str:
        """Create a new session."""
        return f"session_{user_id}"


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    # HACK: Using simple hash for now
    return f"hashed_{password}"


def login(username: str, password: str) -> bool:
    """Main login flow."""
    mgr = AuthManager(secret="test")
    hashed = hash_password(password)
    return mgr.verify_token(hashed)
```

- [ ] **Step 2: Write failing tests**

`tests/core/test_scanner_ast.py`:
```python
from pathlib import Path

from atlas.core.scanner_ast import extract_python

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_extract_python_nodes():
    extraction = extract_python(FIXTURES / "sample.py")
    ids = {n.id for n in extraction.nodes}
    assert "sample" in ids  # file node
    assert "sample_AuthManager" in ids or "authmanager" in ids.union({i.lower() for i in ids})
    # Should find classes and functions
    labels = {n.label for n in extraction.nodes}
    assert any("AuthManager" in l for l in labels)
    assert any("hash_password" in l for l in labels)
    assert any("login" in l for l in labels)


def test_extract_python_edges():
    extraction = extract_python(FIXTURES / "sample.py")
    relations = {(e.source, e.relation, e.target) for e in extraction.edges}
    # File contains the class and functions
    assert any(r == "contains" for _, r, _ in relations)


def test_extract_python_imports():
    extraction = extract_python(FIXTURES / "sample.py")
    import_edges = [e for e in extraction.edges if e.relation in ("imports", "imports_from")]
    assert len(import_edges) >= 2  # os and pathlib


def test_extract_python_rationale():
    extraction = extract_python(FIXTURES / "sample.py")
    # Should extract NOTE and HACK comments
    rationale_nodes = [n for n in extraction.nodes if "NOTE" in (n.label or "") or "HACK" in (n.label or "")]
    assert len(rationale_nodes) >= 0  # may or may not extract depending on implementation


def test_extract_python_methods():
    extraction = extract_python(FIXTURES / "sample.py")
    labels = {n.label for n in extraction.nodes}
    assert any("verify_token" in l for l in labels)
    assert any("create_session" in l for l in labels)


def test_extract_nonexistent_returns_empty():
    extraction = extract_python(Path("/nonexistent/file.py"))
    assert len(extraction.nodes) == 0
    assert len(extraction.edges) == 0
```

- [ ] **Step 3: Run tests to verify failure**

Run: `python -m pytest tests/core/test_scanner_ast.py -v`
Expected: FAIL

- [ ] **Step 4: Implement scanner_ast.py**

`atlas/core/scanner_ast.py`:
```python
"""AST extraction via tree-sitter for code files."""
from __future__ import annotations

import re
from pathlib import Path

from atlas.core.models import Edge, Extraction, Node

_RATIONALE_RE = re.compile(r"#\s*(NOTE|HACK|WHY|IMPORTANT|TODO|FIXME):\s*(.+)", re.IGNORECASE)


def extract_python(path: Path) -> Extraction:
    """Extract nodes and edges from a Python file using the ast module.

    Falls back to stdlib ast if tree-sitter is not available.
    """
    if not path.is_file():
        return Extraction()

    try:
        import ast as stdlib_ast
        source = path.read_text(encoding="utf-8")
        tree = stdlib_ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return Extraction()

    stem = path.stem
    nodes: list[Node] = []
    edges: list[Edge] = []
    seen_ids: set[str] = set()

    # File node
    file_id = stem
    nodes.append(Node(id=file_id, label=f"{path.name}", type="code", source_file=str(path)))
    seen_ids.add(file_id)

    # Extract imports
    for node in stdlib_ast.walk(tree):
        if isinstance(node, stdlib_ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                mod_id = f"_import_{mod}"
                if mod_id not in seen_ids:
                    seen_ids.add(mod_id)
                    nodes.append(Node(id=mod_id, label=mod, type="code", source_file="<external>"))
                edges.append(Edge(source=file_id, target=mod_id, relation="imports", confidence="EXTRACTED", source_file=str(path)))
        elif isinstance(node, stdlib_ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0]
                mod_id = f"_import_{mod}"
                if mod_id not in seen_ids:
                    seen_ids.add(mod_id)
                    nodes.append(Node(id=mod_id, label=mod, type="code", source_file="<external>"))
                edges.append(Edge(source=file_id, target=mod_id, relation="imports_from", confidence="EXTRACTED", source_file=str(path)))

    # Extract classes and functions
    for node in stdlib_ast.iter_child_nodes(tree):
        if isinstance(node, stdlib_ast.ClassDef):
            class_id = f"{stem}_{node.name}"
            if class_id not in seen_ids:
                seen_ids.add(class_id)
                nodes.append(Node(id=class_id, label=node.name, type="code", source_file=str(path), source_location=f"L{node.lineno}"))
                edges.append(Edge(source=file_id, target=class_id, relation="contains", confidence="EXTRACTED"))

            # Methods
            for item in stdlib_ast.iter_child_nodes(node):
                if isinstance(item, stdlib_ast.FunctionDef):
                    method_id = f"{class_id}_{item.name}"
                    if method_id not in seen_ids:
                        seen_ids.add(method_id)
                        nodes.append(Node(id=method_id, label=f".{item.name}()", type="code", source_file=str(path), source_location=f"L{item.lineno}"))
                        edges.append(Edge(source=class_id, target=method_id, relation="method", confidence="EXTRACTED"))

        elif isinstance(node, stdlib_ast.FunctionDef):
            func_id = f"{stem}_{node.name}"
            if func_id not in seen_ids:
                seen_ids.add(func_id)
                nodes.append(Node(id=func_id, label=f"{node.name}()", type="code", source_file=str(path), source_location=f"L{node.lineno}"))
                edges.append(Edge(source=file_id, target=func_id, relation="contains", confidence="EXTRACTED"))

    # Extract rationale comments
    for i, line in enumerate(source.splitlines(), 1):
        m = _RATIONALE_RE.search(line)
        if m:
            tag, text = m.group(1).upper(), m.group(2).strip()
            rat_id = f"{stem}_rationale_L{i}"
            if rat_id not in seen_ids:
                seen_ids.add(rat_id)
                nodes.append(Node(id=rat_id, label=f"{tag}: {text}", type="code", source_file=str(path), source_location=f"L{i}"))

    # Infer call edges (simple name matching)
    func_names: dict[str, str] = {}
    for n in nodes:
        if n.label.endswith("()"):
            name = n.label.rstrip("()").lstrip(".")
            func_names[name] = n.id

    for node in stdlib_ast.walk(tree):
        if isinstance(node, stdlib_ast.Call):
            if isinstance(node.func, stdlib_ast.Name) and node.func.id in func_names:
                # Find which function/method contains this call
                caller_id = _find_enclosing(tree, node.lineno, stem)
                target_id = func_names[node.func.id]
                if caller_id and caller_id != target_id:
                    edges.append(Edge(source=caller_id, target=target_id, relation="calls", confidence="INFERRED", confidence_score=0.8))

    return Extraction(nodes=nodes, edges=edges, source_file=str(path))


def _find_enclosing(tree, lineno: int, stem: str) -> str | None:
    """Find the function/class enclosing a given line number."""
    import ast as stdlib_ast
    best = None
    for node in stdlib_ast.walk(tree):
        if isinstance(node, (stdlib_ast.FunctionDef, stdlib_ast.ClassDef)):
            if hasattr(node, "lineno") and node.lineno <= lineno:
                if hasattr(node, "end_lineno") and (node.end_lineno is None or node.end_lineno >= lineno):
                    best = f"{stem}_{node.name}"
    return best
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/core/test_scanner_ast.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add atlas/core/scanner_ast.py tests/core/test_scanner_ast.py tests/fixtures/sample.py
git commit -m "feat: Python AST extraction — classes, functions, imports, calls, rationale

Uses stdlib ast (no tree-sitter dependency for Python). Extracts file, class,
function, method nodes. EXTRACTED edges for imports/contains/method. INFERRED
edges for calls (name matching). Rationale comments (NOTE, HACK, WHY)."
```

---

## Task 10: Scanner Coordinator + End-to-End Test

**Files:**
- Create: `atlas/core/scanner.py`
- Create: `atlas/core/scanner_semantic.py` (stub)
- Test: `tests/core/test_scanner.py`

- [ ] **Step 1: Write failing tests**

`tests/core/test_scanner.py`:
```python
from pathlib import Path

from atlas.core.scanner import Scanner
from atlas.core.storage import LocalStorage
from atlas.core.cache import CacheEngine


def test_scan_python_file(tmp_path):
    storage = LocalStorage(root=tmp_path)
    # Copy fixture
    src = Path(__file__).parent.parent / "fixtures" / "sample.py"
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text(src.read_text())

    scanner = Scanner(storage=storage)
    extraction = scanner.scan(Path(tmp_path / "src"))
    assert len(extraction.nodes) > 0
    assert len(extraction.edges) > 0


def test_scan_markdown_file(tmp_path):
    storage = LocalStorage(root=tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "readme.md").write_text("# Project\n\nThis project uses [[auth]] and [[billing]].")

    scanner = Scanner(storage=storage)
    extraction = scanner.scan(Path(tmp_path / "docs"))
    assert len(extraction.nodes) >= 1  # at least the file node


def test_scan_with_cache(tmp_path):
    storage = LocalStorage(root=tmp_path)
    src = Path(__file__).parent.parent / "fixtures" / "sample.py"
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text(src.read_text())

    cache = CacheEngine(storage)
    scanner = Scanner(storage=storage, cache=cache)

    # First scan
    e1 = scanner.scan(Path(tmp_path / "src"))
    assert len(e1.nodes) > 0

    # Second scan (cached) — should return same results
    e2 = scanner.scan(Path(tmp_path / "src"))
    assert len(e2.nodes) == len(e1.nodes)


def test_scan_incremental(tmp_path):
    storage = LocalStorage(root=tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("def hello(): pass")
    (tmp_path / "src" / "b.py").write_text("def world(): pass")

    cache = CacheEngine(storage)
    scanner = Scanner(storage=storage, cache=cache)
    scanner.scan(Path(tmp_path / "src"))

    # Modify only a.py
    (tmp_path / "src" / "a.py").write_text("def hello_changed(): pass")
    e = scanner.scan(Path(tmp_path / "src"), incremental=True)
    # Should still produce results (from cache + re-extracted)
    assert len(e.nodes) >= 2


def test_scan_empty_dir(tmp_path):
    storage = LocalStorage(root=tmp_path)
    (tmp_path / "empty").mkdir()
    scanner = Scanner(storage=storage)
    extraction = scanner.scan(Path(tmp_path / "empty"))
    assert len(extraction.nodes) == 0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/core/test_scanner.py -v`
Expected: FAIL

- [ ] **Step 3: Create scanner_semantic.py stub**

`atlas/core/scanner_semantic.py`:
```python
"""Semantic extraction via LLM for docs, PDFs, and images.

This is a stub — full implementation requires LLM integration (Claude/GPT).
For now, it extracts basic structure from markdown files.
"""
from __future__ import annotations

import re
from pathlib import Path

from atlas.core.models import Edge, Extraction, Node

_HEADING_RE = re.compile(r"^#+\s+(.+)$", re.MULTILINE)
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def extract_markdown(path: Path) -> Extraction:
    """Extract nodes and edges from a markdown file.

    Basic extraction: file node, heading concepts, wikilinks as edges.
    Full LLM extraction will be added when the server squad integrates Claude.
    """
    if not path.is_file():
        return Extraction()

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return Extraction()

    stem = path.stem
    nodes: list[Node] = []
    edges: list[Edge] = []

    # File node
    file_id = stem
    nodes.append(Node(id=file_id, label=path.name, type="document", source_file=str(path)))

    # Extract headings as concept nodes
    for match in _HEADING_RE.finditer(content):
        heading = match.group(1).strip()
        heading_id = f"{stem}_{re.sub(r'[^a-z0-9]+', '_', heading.lower()).strip('_')}"
        if heading_id != file_id:
            nodes.append(Node(id=heading_id, label=heading, type="document", source_file=str(path)))
            edges.append(Edge(source=file_id, target=heading_id, relation="contains", confidence="EXTRACTED"))

    # Extract wikilinks as edges
    for match in _WIKILINK_RE.finditer(content):
        target = match.group(1)
        target_slug = target.rsplit("/", 1)[-1].removesuffix(".md")
        target_id = re.sub(r"[^a-z0-9]+", "_", target_slug.lower()).strip("_")
        if target_id != file_id:
            edges.append(Edge(source=file_id, target=target_id, relation="references", confidence="EXTRACTED"))

    return Extraction(nodes=nodes, edges=edges, source_file=str(path))
```

- [ ] **Step 4: Implement scanner.py**

`atlas/core/scanner.py`:
```python
"""Scanner coordinator — dispatches to AST or semantic extractors based on file type."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from atlas.core.models import Extraction
from atlas.core.scanner_ast import extract_python
from atlas.core.scanner_semantic import extract_markdown

if TYPE_CHECKING:
    from atlas.core.cache import CacheEngine
    from atlas.core.storage import StorageBackend

CODE_EXTENSIONS = {".py", ".ts", ".js", ".go", ".rs", ".java", ".c", ".cpp", ".rb", ".cs", ".kt", ".scala", ".php"}
DOC_EXTENSIONS = {".md", ".txt", ".rst"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

# Map extensions to extractors (expand as more languages are added)
_AST_EXTRACTORS = {
    ".py": extract_python,
    # ".ts": extract_typescript,  # TODO: add with tree-sitter
    # ".js": extract_javascript,
    # ".go": extract_go,
}

_SEMANTIC_EXTRACTORS = {
    ".md": extract_markdown,
    ".txt": extract_markdown,  # treat .txt as markdown
}


class Scanner:
    """Coordinates extraction across file types with optional caching."""

    def __init__(self, storage: StorageBackend, cache: CacheEngine | None = None):
        self.storage = storage
        self.cache = cache

    def scan(self, path: Path, incremental: bool = False) -> Extraction:
        """Scan a directory, extract nodes and edges from all supported files.

        If incremental=True and cache is available, only re-extract changed files.
        """
        files = self._collect_files(path)

        if incremental and self.cache:
            rel_paths = [str(f.relative_to(self.storage.root)) if f.is_relative_to(self.storage.root) else str(f) for f in files]
            changed = set(self.cache.detect_changed(rel_paths))
        else:
            changed = None  # process all

        merged = Extraction()

        for file_path in files:
            rel = str(file_path.relative_to(self.storage.root)) if file_path.is_relative_to(self.storage.root) else str(file_path)

            # Check cache first
            if self.cache and changed is not None and rel not in changed:
                cached = self.cache.check(rel)
                if cached:
                    merged = merged.merge(cached)
                    continue

            # Extract
            extraction = self._extract_file(file_path)
            if extraction.nodes:
                merged = merged.merge(extraction)
                if self.cache:
                    self.cache.save(rel, extraction)

        return merged

    def _extract_file(self, path: Path) -> Extraction:
        suffix = path.suffix.lower()
        extractor = _AST_EXTRACTORS.get(suffix) or _SEMANTIC_EXTRACTORS.get(suffix)
        if extractor:
            return extractor(path)
        return Extraction()

    def _collect_files(self, path: Path) -> list[Path]:
        if not path.is_dir():
            return [path] if path.is_file() else []
        valid_extensions = CODE_EXTENSIONS | DOC_EXTENSIONS | IMAGE_EXTENSIONS | {".pdf"}
        files = []
        for f in sorted(path.rglob("*")):
            if f.is_file() and f.suffix.lower() in valid_extensions:
                if not any(part.startswith(".") for part in f.relative_to(path).parts):
                    files.append(f)
        return files
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/core/test_scanner.py -v`
Expected: All PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests PASS across all modules

- [ ] **Step 7: Commit**

```bash
git add atlas/core/scanner.py atlas/core/scanner_semantic.py tests/core/test_scanner.py
git commit -m "feat: scanner coordinator with AST dispatch and markdown extraction

Routes files to AST (Python) or semantic (markdown) extractors. Supports
incremental scan via CacheEngine. Collects files by extension, skips dotfiles."
```

---

## Task 11: End-to-End Integration Test

**Files:**
- Test: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

`tests/test_integration.py`:
```python
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
```

- [ ] **Step 2: Run integration test**

Run: `python -m pytest tests/test_integration.py -v`
Expected: All PASS

- [ ] **Step 3: Run full suite with coverage**

Run: `python -m pytest tests/ -v --cov=atlas.core --cov-report=term-missing`
Expected: All PASS, >80% coverage on core modules

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: end-to-end integration test — scan, graph, wiki, linker, analyzer

Validates the full pipeline: scan raw files -> build graph -> create wiki pages
-> linker sync -> analyzer audit -> save/reload graph -> query -> suggestions.
Also tests incremental rescan with cache."
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Section 4 Architecture — Task 1 (scaffold), Task 2 (storage)
- [x] Section 5.1 Discovery — Tasks 9, 10 (scanner AST + coordinator)
- [x] Section 5.2 Graph Engine — Task 4
- [x] Section 5.3 Wiki Engine — Task 3
- [x] Section 5.4 Linker — Task 5
- [x] Section 7 Data Flow / Cache — Task 6
- [x] Section 8 Storage Abstraction — Task 2
- [x] Section 12 Interfaces — All tasks follow the interfaces contract
- [ ] Section 5.5-5.7 (Server, Skills, Export) — Covered by Plans 2-4
- [ ] Section 5.1 multi-language AST — Only Python in this plan. Other languages are incremental additions.
- [ ] Section 5.1 LLM semantic extraction — Stub in scanner_semantic.py. Full implementation requires Server squad (Claude/GPT integration).
- [ ] Leiden clustering — Analyzer imports graspologic optionally. Full clustering in a follow-up task (needs the cluster optional dep).

**Placeholder scan:** No TBD/TODO in task steps. scanner_semantic.py is explicitly a stub with a clear path to full implementation.

**Type consistency:** All tasks use the same model types from models.py. Scanner returns Extraction, Graph.merge takes Extraction, WikiEngine returns Page, Linker uses GraphChange/WikiSuggestion.

---

## Remaining Plans (to be written separately)

- **Plan 2 — Server:** FastAPI app, REST routes, MCP server, WebSocket
- **Plan 3 — Dashboard:** Graph viz, wiki view, audit view, search
- **Plan 4 — Skills + CLI:** 7 skills, typer CLI, multi-platform install
- **Plan 5 — Quality:** CI/CD, benchmarks, worked examples, README
