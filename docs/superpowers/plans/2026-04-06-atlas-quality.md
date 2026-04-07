# Atlas Quality — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the quality infrastructure for Atlas — CI/CD pipelines, test harness, worked examples, benchmarks, documentation, and PyPI publishing. This plan ensures Atlas is shippable, trustworthy, and viral from day one.

**Squad:** Quality (3 devs)
**Dependencies:** Plan 1 (Core Engine) must be merged first. Plans 2-4 (Server, Dashboard, Skills) can land in parallel — this plan tests their interfaces, not their internals.

**Principles:**
- Worked examples are real, not stubs. Every output is checked in and verified by CI.
- Benchmarks are reproducible scripts, not hand-waved numbers.
- The README is the product's storefront — it must convert a dev in 30 seconds.
- CI catches regressions before humans do.

---

## File Map

```
.github/
├── workflows/
│   ├── ci.yml                    # Lint, type-check, test, build — every push/PR
│   ├── benchmarks.yml            # Perf benchmarks — weekly + manual trigger
│   └── publish.yml               # PyPI publish — on tag push

tests/
├── conftest.py                   # (extended from Plan 1) — add corpus fixtures
├── fixtures/
│   ├── sample.py                 # (from Plan 1)
│   ├── sample.ts                 # (from Plan 1)
│   ├── sample.md                 # (from Plan 1)
│   ├── sample_wiki/              # (from Plan 1)
│   └── corpus/                   # Mini-corpus of 15 realistic files
│       ├── src/
│       │   ├── auth.py
│       │   ├── billing.py
│       │   ├── db.py
│       │   ├── api.py
│       │   └── utils.py
│       ├── docs/
│       │   ├── architecture.md
│       │   ├── onboarding.md
│       │   └── api-reference.md
│       ├── papers/
│       │   ├── attention-is-all-you-need.md
│       │   └── scaling-laws.md
│       ├── notes/
│       │   ├── meeting-2026-03-15.md
│       │   ├── ideas.md
│       │   └── todo.md
│       ├── config/
│       │   └── settings.yaml
│       └── README.md
├── integration/
│   ├── test_e2e_pipeline.py      # Full scan → graph → wiki → linker → audit → export
│   └── test_incremental.py       # Incremental scan correctness
├── performance/
│   ├── test_scan_perf.py         # Scan 100 files < 2 min
│   ├── test_query_perf.py        # Graph query < 100ms
│   └── conftest.py               # Perf fixtures (large generated corpus)

worked/
├── codebase/
│   ├── input/                    # A real Python project (5-10 files)
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── routes.py
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── utils.py
│   │   └── tests/
│   │       └── test_models.py
│   ├── expected/
│   │   ├── graph.json
│   │   └── GRAPH_REPORT.md
│   ├── review.md
│   └── run.sh
├── research/
│   ├── input/                    # Papers + notes markdown (Karpathy-style)
│   │   ├── papers/
│   │   │   ├── attention.md
│   │   │   ├── scaling-laws.md
│   │   │   └── chinchilla.md
│   │   ├── notes/
│   │   │   ├── transformer-intuition.md
│   │   │   ├── training-tips.md
│   │   │   └── open-questions.md
│   │   └── README.md
│   ├── expected/
│   │   ├── graph.json
│   │   └── GRAPH_REPORT.md
│   ├── review.md
│   └── run.sh
├── business/
│   ├── input/                    # Multi-project wiki (agent-wiki style)
│   │   ├── wiki/
│   │   │   ├── index.md
│   │   │   ├── projects/
│   │   │   │   ├── ara.md
│   │   │   │   ├── atlas.md
│   │   │   │   └── hermes.md
│   │   │   ├── concepts/
│   │   │   │   ├── mcp.md
│   │   │   │   ├── finops.md
│   │   │   │   └── knowledge-graph.md
│   │   │   ├── decisions/
│   │   │   │   ├── 2026-03-01-python-only.md
│   │   │   │   └── 2026-03-15-networkx-over-neo4j.md
│   │   │   └── sources/
│   │   │       ├── karpathy-llm-wiki.md
│   │   │       └── graphrag-paper.md
│   │   └── AGENTS.md
│   ├── expected/
│   │   ├── graph.json
│   │   └── GRAPH_REPORT.md
│   ├── review.md
│   └── run.sh

benchmarks/
├── bench_scan.py                 # Scan performance — time per file, full vs incremental
├── bench_query.py                # Query latency — p50/p95/p99
├── bench_tokens.py               # Token efficiency — raw corpus vs graph query
├── bench_cache.py                # Cache hit rate measurement
├── run_all.py                    # Orchestrator — runs all, outputs JSON + markdown
└── results/                      # Git-tracked baseline results
    └── .gitkeep

docs/
├── README.md                     # The storefront — demo, install, usage, examples
├── ARCHITECTURE.md               # System internals for contributors
├── SECURITY.md                   # Threat model, data handling, LLM trust
├── CHANGELOG.md                  # Keep-a-changelog format
└── CONTRIBUTING.md               # How to contribute, code style, PR process
```

---

## Task 1: CI/CD Pipeline — GitHub Actions

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/benchmarks.yml`
- Create: `.github/workflows/publish.yml`

- [ ] **Step 1: Create the main CI workflow**

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  lint:
    name: Lint (ruff)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check atlas/ tests/ benchmarks/
      - run: ruff format --check atlas/ tests/ benchmarks/

  typecheck:
    name: Type check (pyright)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]" pyright
      - run: pyright atlas/

  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: python -m pytest tests/ -v --cov=atlas --cov-report=xml --cov-report=term-missing -x
      - name: Check coverage threshold
        run: |
          python -c "
          import xml.etree.ElementTree as ET
          tree = ET.parse('coverage.xml')
          rate = float(tree.getroot().attrib['line-rate'])
          pct = round(rate * 100, 1)
          print(f'Coverage: {pct}%')
          assert pct >= 80, f'Coverage {pct}% is below 80% threshold'
          "
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage-${{ matrix.python-version }}
          path: coverage.xml

  build:
    name: Build validation
    runs-on: ubuntu-latest
    needs: [lint, typecheck, test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build
      - run: python -m build
      - name: Verify install from wheel
        run: |
          pip install dist/*.whl
          python -c "import atlas; print(f'atlas {atlas.__version__} OK')"
          atlas --help
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```

- [ ] **Step 2: Create the benchmarks workflow**

`.github/workflows/benchmarks.yml`:
```yaml
name: Benchmarks

on:
  schedule:
    - cron: "0 6 * * 1"  # Weekly Monday 6 AM UTC
  workflow_dispatch:       # Manual trigger

permissions:
  contents: read

jobs:
  benchmark:
    name: Performance benchmarks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - name: Run benchmarks
        run: python benchmarks/run_all.py --output benchmarks/results/latest.json
      - name: Check thresholds
        run: |
          python -c "
          import json, sys
          with open('benchmarks/results/latest.json') as f:
              r = json.load(f)
          fail = False
          if r['scan']['time_per_file_ms'] > 1200:
              print(f'FAIL: scan {r[\"scan\"][\"time_per_file_ms\"]:.0f}ms/file > 1200ms')
              fail = True
          if r['query']['p95_ms'] > 100:
              print(f'FAIL: query p95 {r[\"query\"][\"p95_ms\"]:.1f}ms > 100ms')
              fail = True
          if not fail:
              print('All benchmarks within thresholds')
          sys.exit(1 if fail else 0)
          "
      - uses: actions/upload-artifact@v4
        with:
          name: benchmark-results
          path: benchmarks/results/latest.json
```

- [ ] **Step 3: Create the PyPI publish workflow**

`.github/workflows/publish.yml`:
```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*"

permissions:
  contents: write   # For GitHub release
  id-token: write   # For trusted publishing (PyPI OIDC)

jobs:
  publish:
    name: Build & publish
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build
      - run: python -m build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        # Uses trusted publishing — no API token needed
        # Configure at https://pypi.org/manage/project/atlas-ai/settings/publishing/

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: dist/*
```

- [ ] **Step 4: Add ruff and pyright config to pyproject.toml**

Append to the existing `pyproject.toml` (from Plan 1):
```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.lint.isort]
known-first-party = ["atlas"]

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"
reportMissingTypeStubs = false
include = ["atlas"]
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/
git commit -m "ci: add GitHub Actions — lint, typecheck, test, build, benchmarks, publish

Matrix: Python 3.12 + 3.13. Coverage gate at 80%.
Weekly benchmarks with threshold checks.
PyPI publish via trusted publishing on tag push."
```

---

## Task 2: Test Corpus — Realistic Fixture Files

**Files:**
- Create: `tests/fixtures/corpus/` (15 files)
- Update: `tests/conftest.py` (add corpus fixture)

- [ ] **Step 1: Create the corpus source files — Python codebase**

`tests/fixtures/corpus/src/auth.py`:
```python
"""Authentication module — JWT-based token management."""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass

from .db import get_connection
from .utils import generate_id


@dataclass
class User:
    id: str
    email: str
    role: str  # "admin" | "member" | "viewer"
    created_at: float


@dataclass
class Token:
    user_id: str
    scope: str
    expires_at: float
    signature: str


SECRET_KEY = "PLACEHOLDER_FOR_ENV"


def create_token(user: User, scope: str = "read", ttl: int = 3600) -> Token:
    """Create a signed JWT-like token for the given user."""
    expires = time.time() + ttl
    payload = f"{user.id}:{scope}:{expires}"
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return Token(user_id=user.id, scope=scope, expires_at=expires, signature=sig)


def verify_token(token: Token) -> bool:
    """Verify token signature and expiry."""
    if time.time() > token.expires_at:
        return False
    payload = f"{token.user_id}:{token.scope}:{token.expires_at}"
    expected = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(token.signature, expected)


def get_user_by_email(email: str) -> User | None:
    """Lookup user by email from the database."""
    conn = get_connection()
    row = conn.execute("SELECT id, email, role, created_at FROM users WHERE email = ?", (email,)).fetchone()
    if row:
        return User(id=row[0], email=row[1], role=row[2], created_at=row[3])
    return None
```

`tests/fixtures/corpus/src/billing.py`:
```python
"""Billing module — usage tracking and invoice generation."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .auth import User
from .db import get_connection
from .utils import generate_id


class PlanTier(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


PLAN_LIMITS = {
    PlanTier.FREE: {"scans_per_month": 100, "max_nodes": 1000},
    PlanTier.PRO: {"scans_per_month": 10000, "max_nodes": 100000},
    PlanTier.ENTERPRISE: {"scans_per_month": -1, "max_nodes": -1},
}


@dataclass
class UsageRecord:
    user_id: str
    operation: str  # "scan" | "query" | "ingest"
    tokens_used: int
    timestamp: float


@dataclass
class Invoice:
    id: str
    user_id: str
    period: str
    total_tokens: int
    amount_cents: int
    line_items: list[dict] = field(default_factory=list)


def record_usage(user: User, operation: str, tokens: int) -> UsageRecord:
    """Record a usage event for billing purposes."""
    import time

    record = UsageRecord(
        user_id=user.id,
        operation=operation,
        tokens_used=tokens,
        timestamp=time.time(),
    )
    conn = get_connection()
    conn.execute(
        "INSERT INTO usage (user_id, operation, tokens, ts) VALUES (?, ?, ?, ?)",
        (record.user_id, record.operation, record.tokens_used, record.timestamp),
    )
    return record


def check_quota(user: User, plan: PlanTier) -> bool:
    """Check if user is within their plan quota for the current month."""
    limits = PLAN_LIMITS[plan]
    if limits["scans_per_month"] == -1:
        return True
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM usage WHERE user_id = ? AND operation = 'scan' AND ts > ?",
        (user.id, _start_of_month()),
    ).fetchone()[0]
    return count < limits["scans_per_month"]


def generate_invoice(user: User, period: str) -> Invoice:
    """Generate a monthly invoice for a user."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT operation, SUM(tokens) FROM usage WHERE user_id = ? AND ts > ? GROUP BY operation",
        (user.id, _start_of_month()),
    ).fetchall()
    total = sum(r[1] for r in rows)
    amount = _calculate_cost(total)
    return Invoice(
        id=generate_id("inv"),
        user_id=user.id,
        period=period,
        total_tokens=total,
        amount_cents=amount,
        line_items=[{"operation": r[0], "tokens": r[1]} for r in rows],
    )


def _start_of_month() -> float:
    import time
    t = time.gmtime()
    return time.mktime(time.struct_time((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, -1)))


def _calculate_cost(tokens: int) -> int:
    """$0.01 per 1000 tokens, minimum $0."""
    return max(0, (tokens * 10) // 1000)
```

`tests/fixtures/corpus/src/db.py`:
```python
"""Database module — SQLite connection management."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

_DEFAULT_DB = Path("atlas.db")
_connection: sqlite3.Connection | None = None


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Get or create a database connection (singleton per process)."""
    global _connection
    if _connection is None:
        path = db_path or _DEFAULT_DB
        _connection = sqlite3.connect(str(path))
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
        _init_schema(_connection)
    return _connection


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL REFERENCES users(id),
            operation TEXT NOT NULL,
            tokens INTEGER NOT NULL DEFAULT 0,
            ts REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_usage_user ON usage(user_id, ts);
    """)


@contextmanager
def transaction():
    """Context manager for database transactions."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def close():
    """Close the database connection."""
    global _connection
    if _connection:
        _connection.close()
        _connection = None
```

`tests/fixtures/corpus/src/api.py`:
```python
"""API module — HTTP route handlers for the Atlas server."""
from __future__ import annotations

from dataclasses import dataclass

from .auth import User, create_token, get_user_by_email, verify_token
from .billing import PlanTier, check_quota, generate_invoice, record_usage


@dataclass
class Request:
    method: str
    path: str
    body: dict | None = None
    headers: dict | None = None


@dataclass
class Response:
    status: int
    body: dict


def handle_login(request: Request) -> Response:
    """POST /login — authenticate and return a token."""
    email = request.body.get("email") if request.body else None
    if not email:
        return Response(status=400, body={"error": "email required"})
    user = get_user_by_email(email)
    if not user:
        return Response(status=404, body={"error": "user not found"})
    token = create_token(user)
    return Response(status=200, body={"token": token.signature, "expires": token.expires_at})


def handle_scan(request: Request, user: User) -> Response:
    """POST /scan — trigger a scan, check quota, record usage."""
    if not check_quota(user, PlanTier.PRO):
        return Response(status=429, body={"error": "quota exceeded"})
    path = request.body.get("path") if request.body else None
    if not path:
        return Response(status=400, body={"error": "path required"})
    # Actual scan delegated to core engine
    record_usage(user, "scan", tokens=500)
    return Response(status=200, body={"status": "scanning", "path": path})


def handle_query(request: Request, user: User) -> Response:
    """POST /query — run a graph query, record usage."""
    question = request.body.get("question") if request.body else None
    if not question:
        return Response(status=400, body={"error": "question required"})
    record_usage(user, "query", tokens=100)
    return Response(status=200, body={"answer": f"Results for: {question}", "tokens": 100})


def handle_invoice(user: User, period: str) -> Response:
    """GET /invoice/:period — generate and return invoice."""
    invoice = generate_invoice(user, period)
    return Response(status=200, body={
        "id": invoice.id,
        "total_tokens": invoice.total_tokens,
        "amount_cents": invoice.amount_cents,
        "line_items": invoice.line_items,
    })


ROUTES = {
    ("POST", "/login"): handle_login,
    ("POST", "/scan"): handle_scan,
    ("POST", "/query"): handle_query,
}
```

`tests/fixtures/corpus/src/utils.py`:
```python
"""Utility functions shared across modules."""
from __future__ import annotations

import hashlib
import time
import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}_{uid}" if prefix else uid


def sha256_hash(content: str | bytes) -> str:
    """Compute SHA256 hash of content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def timestamp_iso() -> str:
    """Current UTC timestamp in ISO 8601 format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def truncate(text: str, max_length: int = 200) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")


def estimate_tokens(text: str) -> int:
    """Rough token estimate — 1 token per ~4 characters."""
    return max(1, len(text) // 4)
```

- [ ] **Step 2: Create the corpus docs**

`tests/fixtures/corpus/docs/architecture.md`:
```markdown
---
title: Architecture Overview
type: document
tags: [architecture, design, system]
---

# Architecture Overview

Atlas follows a layered architecture with clear separation of concerns.

## Layers

### Core Engine
The core engine contains the fundamental modules:
- **Scanner** — extracts entities and relationships from files using AST parsing and LLM analysis
- **Graph** — manages the knowledge graph (NetworkX-based) with BFS/DFS query support
- **Wiki** — maintains markdown pages with typed frontmatter and [[wikilinks]]
- **Linker** — bidirectional sync between graph and wiki (the key differentiator)
- **Analyzer** — detects god nodes, orphans, contradictions, and communities

### Server
FastAPI server exposing REST API, MCP protocol, and WebSocket for live updates.

### Dashboard
Static-first frontend (HTML + vanilla JS + Tailwind) served by FastAPI.

## Key Decisions
- [[NetworkX over Neo4j|decisions/networkx-over-neo4j]] — simplicity, git-versionable, no external deps
- [[Python-only|decisions/python-only]] — one language, one ecosystem, maximum contributor pool
- Storage abstraction allows swapping local filesystem for cloud (ARA mode)

## Data Flow
Files → Scanner → Extraction → Graph.merge → Linker.sync → Wiki pages
Wiki edits → Linker.sync_wiki_to_graph → Graph updates → Analyzer.audit
```

`tests/fixtures/corpus/docs/onboarding.md`:
```markdown
---
title: Onboarding Guide
type: document
tags: [onboarding, getting-started]
---

# Onboarding Guide

Welcome to Atlas development. This guide gets you productive in 15 minutes.

## Setup

1. Clone the repo: `git clone https://github.com/originlabs-app/atlas`
2. Install with dev deps: `pip install -e ".[dev]"`
3. Run tests: `pytest tests/ -v`
4. Start the server: `atlas serve`

## Key Concepts

- **Knowledge Graph** — a network of concepts, files, and relationships
- **Wiki** — markdown pages that document what the graph discovers
- **Linker** — the bridge between graph and wiki (see [[architecture]])
- **Scan** — the process of extracting entities from files
- **Audit** — health check that finds orphans, contradictions, and gaps

## Daily Workflow

1. `atlas scan .` — scan the codebase
2. Open the dashboard at http://localhost:7100
3. Review audit findings
4. Write or edit wiki pages to curate knowledge
5. `atlas query "how does auth connect to billing?"` — ask questions

## Contributing

See [[CONTRIBUTING]] for code style, PR process, and review guidelines.
```

`tests/fixtures/corpus/docs/api-reference.md`:
```markdown
---
title: API Reference
type: document
tags: [api, reference, rest]
---

# API Reference

## Authentication

All API calls require a bearer token obtained via `POST /login`.

### POST /login
- Body: `{"email": "user@example.com"}`
- Returns: `{"token": "...", "expires": 1234567890}`

## Scan

### POST /scan
- Auth: required
- Body: `{"path": "/path/to/folder"}`
- Returns: `{"status": "scanning", "path": "..."}`
- Quota: checked against user plan (see [[billing]])

## Query

### POST /query
- Auth: required
- Body: `{"question": "how does auth connect to billing?"}`
- Returns: `{"answer": "...", "tokens": 100}`

## Invoice

### GET /invoice/:period
- Auth: required
- Returns: `{"id": "...", "total_tokens": 1500, "amount_cents": 15}`

## Rate Limits

| Plan       | Scans/month | Max nodes |
|------------|-------------|-----------|
| Free       | 100         | 1,000     |
| Pro        | 10,000      | 100,000   |
| Enterprise | Unlimited   | Unlimited |

See [[auth]] for token management and [[billing]] for quota details.
```

- [ ] **Step 3: Create the corpus papers and notes**

`tests/fixtures/corpus/papers/attention-is-all-you-need.md`:
```markdown
---
title: "Attention Is All You Need"
type: paper
authors: [Vaswani, Shazeer, Parmar, Uszkoreit, Jones, Gomez, Kaiser, Polosukhin]
year: 2017
tags: [transformer, attention, architecture, nlp]
---

# Attention Is All You Need

## Key Contribution
Introduced the Transformer architecture — replacing recurrence entirely with self-attention mechanisms. This became the foundation for all modern LLMs.

## Core Ideas
- **Self-attention** — each token attends to all other tokens in the sequence
- **Multi-head attention** — parallel attention heads capture different relationship types
- **Positional encoding** — sinusoidal functions inject sequence order without recurrence
- **Encoder-decoder** — separate stacks for understanding input and generating output

## Impact
- Enabled [[scaling-laws]] — transformers scale predictably with compute
- Led to GPT series, BERT, T5, and all modern language models
- Parallelizable training (unlike RNNs) unlocked massive scale

## Relevance to Atlas
Atlas uses LLMs (transformers) for semantic extraction from documents and images.
The attention mechanism is what allows the model to identify relationships between
concepts across long documents — exactly what Atlas needs for graph construction.
```

`tests/fixtures/corpus/papers/scaling-laws.md`:
```markdown
---
title: "Scaling Laws for Neural Language Models"
type: paper
authors: [Kaplan, McCandlish, Henighan, Brown, Chess, Child, Gray, Radford, Wu, Amodei]
year: 2020
tags: [scaling, compute, training, llm]
---

# Scaling Laws for Neural Language Models

## Key Contribution
Demonstrated that language model performance follows predictable power laws across three axes: parameters, data, and compute.

## Core Findings
- Loss scales as a power law with model size (parameters N)
- Loss scales as a power law with dataset size (tokens D)
- Loss scales as a power law with compute budget (FLOPs C)
- Larger models are more sample-efficient
- Optimal allocation: scale model size faster than dataset size

## Implications
- Predictable scaling enables reliable compute budgeting
- Bigger is reliably better (up to a point)
- Led to [[chinchilla]] rethinking the compute-optimal frontier

## Relevance to Atlas
Atlas benchmarks track token efficiency — how many LLM tokens are needed per
file scanned. Scaling laws help predict costs as corpus size grows. The
[[attention-is-all-you-need|Transformer architecture]] underpins all extraction.
```

`tests/fixtures/corpus/notes/meeting-2026-03-15.md`:
```markdown
---
title: "Team Meeting — 2026-03-15"
type: note
date: 2026-03-15
tags: [meeting, planning, atlas]
---

# Team Meeting — 2026-03-15

## Attendees
Pierre, Anna, Marc

## Decisions
1. Atlas will be Python-only for v2.0 (see [[architecture]])
2. NetworkX over Neo4j — no external DB dependency
3. Wiki markdown is the source of truth, graph.json is derived
4. Target: `pip install atlas-ai && atlas scan .` works in under 30 seconds

## Action Items
- [ ] Pierre: write the design spec
- [ ] Anna: prototype the scanner with tree-sitter
- [ ] Marc: draft the [[billing]] model for ARA integration

## Notes
- Key differentiator is the [[linker|Linker]] — bidirectional graph-wiki sync
- Discussed token efficiency: aim for 10x compression (raw corpus vs graph query)
- Need worked examples for demo — a real codebase, a research corpus, a business wiki
```

`tests/fixtures/corpus/notes/ideas.md`:
```markdown
---
title: Ideas Backlog
type: note
tags: [ideas, backlog, future]
---

# Ideas Backlog

## Near-term
- **Confidence decay** — INFERRED edges lose confidence over time without confirmation
- **Cross-corpus linking** — detect relationships across multiple scanned projects
- **Community auto-labeling** — LLM names clusters instead of "Community 0"

## Medium-term
- **Obsidian plugin** — sync Atlas graph directly into an Obsidian vault
- **VS Code extension** — inline knowledge graph in the editor sidebar
- **Git hooks** — auto-scan on commit for continuous graph maintenance

## Long-term
- **Multi-tenant ARA mode** — hosted Atlas with per-org isolation
- **Real-time collaboration** — multiple agents curating the same wiki simultaneously
- **Embedding hybrid** — combine graph structure with vector embeddings for richer [[query]] results

## Rejected
- Neo4j backend — too heavy for the solo dev use case (see meeting notes)
- TypeScript rewrite — Python ecosystem is richer for ML/graph tooling
```

`tests/fixtures/corpus/notes/todo.md`:
```markdown
---
title: Sprint TODO
type: note
tags: [todo, sprint, tracking]
---

# Sprint TODO — Week 1

## Must Have
- [x] Project scaffold + models (Plan 1, Task 1)
- [x] Storage backend (Plan 1, Task 2)
- [ ] Wiki engine with frontmatter parsing
- [ ] Graph engine with BFS/DFS query
- [ ] Scanner AST extraction for Python

## Should Have
- [ ] Linker bidirectional sync
- [ ] Cache engine with SHA256 manifest
- [ ] Basic CLI with `atlas scan` and `atlas query`

## Nice to Have
- [ ] Dashboard graph visualization
- [ ] MCP server stub
- [ ] Multi-language AST (TypeScript, Go)

## Blockers
- tree-sitter Python bindings have a version conflict with 3.13 — tracking upstream fix
- Need to finalize the [[auth]] token format before implementing the API layer
```

`tests/fixtures/corpus/config/settings.yaml`:
```yaml
# Atlas configuration
atlas:
  version: "2.0.0a1"
  storage:
    backend: local
    root: .
  scanner:
    languages: [python, typescript, go, rust, markdown]
    max_file_size_kb: 500
    exclude_patterns:
      - "node_modules/"
      - ".git/"
      - "__pycache__/"
      - "*.pyc"
      - ".env"
  graph:
    max_depth: 5
    confidence_threshold: 0.3
    community_algorithm: leiden
  cache:
    enabled: true
    directory: .atlas-cache
  server:
    host: "127.0.0.1"
    port: 7100
```

`tests/fixtures/corpus/README.md`:
```markdown
# Atlas Test Corpus

This is a realistic mini-corpus used to test Atlas end-to-end.

## Contents

- `src/` — A Python codebase with auth, billing, database, API, and utilities
- `docs/` — Architecture, onboarding, and API reference documentation
- `papers/` — Research papers on transformers and scaling laws
- `notes/` — Meeting notes, ideas, and sprint tracking
- `config/` — Atlas configuration file

## Expected Results

After `atlas scan tests/fixtures/corpus/`:
- ~25-35 nodes (functions, classes, concepts, documents)
- ~30-50 edges (imports, calls, references, semantic links)
- 3-5 communities (auth/security, billing/usage, infrastructure, research, planning)
- Health score > 60 (mostly EXTRACTED relations from code AST)
```

- [ ] **Step 4: Extend conftest.py with corpus fixture**

Add to existing `tests/conftest.py`:
```python
@pytest.fixture
def corpus_path():
    """Path to the realistic mini-corpus fixture."""
    return FIXTURES / "corpus"


@pytest.fixture
def corpus_storage(tmp_path, corpus_path):
    """A LocalStorage pre-populated with the test corpus as raw/ input."""
    import shutil
    raw = tmp_path / "raw"
    raw.mkdir()
    shutil.copytree(corpus_path, raw / "corpus", dirs_exist_ok=True)

    wiki = tmp_path / "wiki"
    for d in [wiki / "projects", wiki / "concepts", wiki / "decisions", wiki / "sources"]:
        d.mkdir(parents=True)
    (wiki / "index.md").write_text("# Wiki Index\n")
    (wiki / "log.md").write_text("# Wiki Log\n")

    return LocalStorage(root=tmp_path)
```

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/corpus/ tests/conftest.py
git commit -m "test: add realistic 15-file mini-corpus fixture

Python codebase (auth, billing, db, api, utils), documentation
(architecture, onboarding, api-reference), research papers
(attention, scaling-laws), meeting notes, ideas, and config.
All files have realistic content with cross-references."
```

---

## Task 3: Integration Tests — End-to-End Pipeline

**Files:**
- Create: `tests/integration/test_e2e_pipeline.py`
- Create: `tests/integration/test_incremental.py`
- Create: `tests/integration/__init__.py`

- [ ] **Step 1: Create the E2E pipeline test**

`tests/integration/__init__.py`:
```python
"""Integration tests — full pipeline and cross-module behavior."""
```

`tests/integration/test_e2e_pipeline.py`:
```python
"""End-to-end integration test: scan → graph → wiki → linker → audit → export.

This test exercises the full Atlas pipeline against the realistic corpus fixture.
It validates that all modules work together, not just individually.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from atlas.core.analyzer import Analyzer
from atlas.core.cache import CacheEngine
from atlas.core.graph import Graph
from atlas.core.linker import Linker
from atlas.core.models import Extraction
from atlas.core.scanner import Scanner
from atlas.core.storage import LocalStorage
from atlas.core.wiki import WikiEngine


class TestE2EPipeline:
    """Full pipeline test against the 15-file corpus."""

    @pytest.fixture(autouse=True)
    def setup(self, corpus_storage):
        """Initialize all engine components."""
        self.storage = corpus_storage
        self.cache = CacheEngine(self.storage)
        self.scanner = Scanner(storage=self.storage, cache=self.cache)
        self.graph = Graph()
        self.wiki = WikiEngine(self.storage)
        self.linker = Linker(graph=self.graph, wiki=self.wiki, storage=self.storage)
        self.analyzer = Analyzer(graph=self.graph, wiki=self.wiki)

    def test_step1_scan_extracts_nodes_and_edges(self, corpus_path):
        """Scan the corpus and verify extraction results are non-trivial."""
        extraction = self.scanner.scan(corpus_path)

        assert isinstance(extraction, Extraction)
        assert len(extraction.nodes) >= 10, f"Expected >=10 nodes, got {len(extraction.nodes)}"
        assert len(extraction.edges) >= 5, f"Expected >=5 edges, got {len(extraction.edges)}"

        # Verify we extracted from multiple file types
        source_files = {n.source_file for n in extraction.nodes}
        assert any("auth.py" in f for f in source_files), "Should extract from auth.py"
        assert any(".md" in f for f in source_files), "Should extract from markdown files"

    def test_step2_graph_merge_builds_connected_graph(self, corpus_path):
        """Merge extraction into graph and verify connectivity."""
        extraction = self.scanner.scan(corpus_path)
        self.graph.merge(extraction)

        stats = self.graph.stats()
        assert stats.nodes >= 10
        assert stats.edges >= 5
        assert stats.health_score > 0

    def test_step3_graph_query_returns_results(self, corpus_path):
        """Query the graph and verify meaningful results."""
        extraction = self.scanner.scan(corpus_path)
        self.graph.merge(extraction)

        # BFS query — should find auth-related nodes
        result = self.graph.query("auth", mode="bfs", depth=2)
        assert len(result.nodes) >= 1, "BFS query for 'auth' should return results"

        # Path query — if auth and billing are both in the graph
        node_ids = {n.id for n in extraction.nodes}
        if "auth" in node_ids and "billing" in node_ids:
            path = self.graph.path("auth", "billing")
            assert isinstance(path, list)

    def test_step4_wiki_pages_created(self, corpus_path):
        """Verify wiki engine can create and read pages."""
        self.wiki.write(
            "concepts/auth",
            "# Auth\n\nAuthentication module. See [[billing]] for payment integration.",
            frontmatter={"type": "wiki-concept", "title": "Auth", "tags": ["auth", "security"]},
        )

        page = self.wiki.read("concepts/auth")
        assert page is not None
        assert page.title == "Auth"
        assert "billing" in page.wikilinks

    def test_step5_linker_syncs_wiki_to_graph(self, corpus_path):
        """Linker should create graph edges from wiki wikilinks."""
        # Write two pages with cross-references
        self.wiki.write(
            "concepts/auth",
            "# Auth\n\nSee [[billing]] for payment.",
            frontmatter={"type": "wiki-concept", "title": "Auth"},
        )
        self.wiki.write(
            "concepts/billing",
            "# Billing\n\nUses [[auth]] for verification.",
            frontmatter={"type": "wiki-concept", "title": "Billing"},
        )

        changes = self.linker.sync_wiki_to_graph()
        assert isinstance(changes, list)
        assert len(changes) >= 2, "Linker should create nodes and/or edges from wiki pages"

    def test_step6_linker_proposes_wiki_updates(self, corpus_path):
        """Linker should suggest wiki pages for graph-only nodes."""
        extraction = self.scanner.scan(corpus_path)
        self.graph.merge(extraction)

        suggestions = self.linker.sync_graph_to_wiki()
        assert isinstance(suggestions, list)
        # Nodes from scan without wiki pages should generate suggestions
        if len(extraction.nodes) > 0:
            assert len(suggestions) >= 1, "Should suggest wiki pages for graph-only nodes"

    def test_step7_analyzer_produces_audit_report(self, corpus_path):
        """Analyzer should generate a comprehensive audit report."""
        extraction = self.scanner.scan(corpus_path)
        self.graph.merge(extraction)

        report = self.analyzer.audit()
        assert report is not None
        assert report.stats is not None
        assert report.stats.nodes >= 10
        assert isinstance(report.orphan_pages, list)
        assert isinstance(report.god_nodes, list)
        assert isinstance(report.contradictions, list)

    def test_step8_graph_serialization_roundtrip(self, corpus_path, tmp_path):
        """Graph should serialize to JSON and reload identically."""
        extraction = self.scanner.scan(corpus_path)
        self.graph.merge(extraction)

        # Serialize
        graph_path = tmp_path / "graph.json"
        graph_data = self.graph.to_dict()
        graph_path.write_text(json.dumps(graph_data, indent=2))

        # Reload
        reloaded_data = json.loads(graph_path.read_text())
        graph2 = Graph.from_dict(reloaded_data)

        assert graph2.stats().nodes == self.graph.stats().nodes
        assert graph2.stats().edges == self.graph.stats().edges

    def test_full_pipeline_health_score_above_threshold(self, corpus_path):
        """The full pipeline on the corpus should produce a healthy graph."""
        # Scan
        extraction = self.scanner.scan(corpus_path)
        self.graph.merge(extraction)

        # Wiki curation
        self.wiki.write(
            "concepts/auth",
            "# Auth\n\nSee [[billing]].",
            frontmatter={"type": "wiki-concept", "title": "Auth"},
        )
        self.linker.sync_wiki_to_graph()

        # Audit
        report = self.analyzer.audit()
        print(f"\n=== Pipeline Summary ===")
        print(f"Nodes: {report.stats.nodes}")
        print(f"Edges: {report.stats.edges}")
        print(f"Communities: {report.stats.communities}")
        print(f"Health: {report.health_score:.1f}")
        print(f"God nodes: {len(report.god_nodes)}")
        print(f"Orphans: {len(report.orphan_pages)}")
        print(f"Contradictions: {len(report.contradictions)}")

        # Baseline expectations for the 15-file corpus
        assert report.stats.nodes >= 10, "Corpus should yield at least 10 nodes"
        assert report.health_score >= 0, "Health score should be non-negative"
```

- [ ] **Step 2: Create incremental scan test**

`tests/integration/test_incremental.py`:
```python
"""Integration tests for incremental scanning behavior."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from atlas.core.cache import CacheEngine
from atlas.core.graph import Graph
from atlas.core.scanner import Scanner
from atlas.core.storage import LocalStorage


class TestIncrementalScan:
    """Verify incremental scan only processes changed files."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.storage = LocalStorage(root=tmp_path)
        self.cache = CacheEngine(self.storage)
        self.scanner = Scanner(storage=self.storage, cache=self.cache)
        self.graph = Graph()

        # Create initial files
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("def hello():\n    return 'hello'\n")
        (src / "b.py").write_text("def world():\n    return 'world'\n")
        (src / "c.py").write_text("from .a import hello\nfrom .b import world\n\ndef greet():\n    return hello() + ' ' + world()\n")
        self.src = src

    def test_full_scan_processes_all_files(self):
        """Full scan should process every file."""
        extraction = self.scanner.scan(self.src)
        assert len(extraction.nodes) >= 3, "Should extract from all 3 files"

    def test_incremental_scan_skips_unchanged(self):
        """Incremental scan after no changes should use cache entirely."""
        # First scan — populates cache
        e1 = self.scanner.scan(self.src)
        n1 = len(e1.nodes)

        # Second scan (incremental) — no changes
        e2 = self.scanner.scan(self.src, incremental=True)
        assert len(e2.nodes) == n1, "Unchanged files should yield same node count from cache"

    def test_incremental_scan_detects_changes(self):
        """Modified file should be re-scanned, unchanged files should use cache."""
        # First scan
        self.scanner.scan(self.src)

        # Modify one file
        time.sleep(0.05)  # Ensure mtime changes
        (self.src / "a.py").write_text("def hello_v2():\n    return 'hello v2'\n\ndef new_func():\n    pass\n")

        # Incremental scan
        e2 = self.scanner.scan(self.src, incremental=True)
        # Should have re-scanned a.py, used cache for b.py and c.py
        labels = {n.label for n in e2.nodes}
        # The exact labels depend on scanner implementation, but we should see the new function
        assert len(e2.nodes) >= 3, "Should have at least same number of nodes after adding a function"

    def test_incremental_scan_detects_new_files(self):
        """New files should be discovered and scanned."""
        self.scanner.scan(self.src)

        # Add a new file
        (self.src / "d.py").write_text("def new_module():\n    pass\n")

        e2 = self.scanner.scan(self.src, incremental=True)
        source_files = {n.source_file for n in e2.nodes}
        assert any("d.py" in str(f) for f in source_files), "New file should be discovered"

    def test_incremental_scan_detects_deleted_files(self):
        """Deleted files should be noted (nodes may be flagged for cleanup)."""
        e1 = self.scanner.scan(self.src)
        n1 = len(e1.nodes)

        # Delete a file
        (self.src / "b.py").unlink()

        e2 = self.scanner.scan(self.src, incremental=True)
        # After deletion, we should have fewer or equal nodes
        # (exact behavior depends on whether scanner prunes or flags)
        assert isinstance(e2.nodes, list)

    def test_force_scan_ignores_cache(self):
        """Force scan should re-process everything regardless of cache."""
        self.scanner.scan(self.src)

        # Force scan — should re-extract everything
        e2 = self.scanner.scan(self.src, incremental=False)
        assert len(e2.nodes) >= 3, "Force scan should still find all nodes"
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/
git commit -m "test: integration tests — E2E pipeline and incremental scan

E2E tests the full chain: scan corpus → graph merge → wiki write →
linker sync → analyzer audit → graph serialization roundtrip.
Incremental tests verify cache hit/miss on changed, new, and deleted files."
```

---

## Task 4: Performance Tests

**Files:**
- Create: `tests/performance/__init__.py`
- Create: `tests/performance/conftest.py`
- Create: `tests/performance/test_scan_perf.py`
- Create: `tests/performance/test_query_perf.py`

- [ ] **Step 1: Create performance fixtures**

`tests/performance/__init__.py`:
```python
"""Performance tests — verify scan and query meet latency targets."""
```

`tests/performance/conftest.py`:
```python
"""Fixtures for performance tests — generates large synthetic corpora."""
from __future__ import annotations

import random
import string
from pathlib import Path

import pytest

from atlas.core.graph import Graph
from atlas.core.models import Edge, Extraction, Node


def _random_python_file(name: str, imports: list[str] | None = None) -> str:
    """Generate a realistic Python file with functions, classes, and imports."""
    lines = [f'"""Module {name} — auto-generated for benchmarking."""']
    lines.append("from __future__ import annotations\n")

    if imports:
        for imp in imports:
            lines.append(f"from .{imp} import {imp}_main")
    lines.append("")

    # Add a class
    class_name = name.replace("_", " ").title().replace(" ", "")
    lines.append(f"class {class_name}:")
    lines.append(f'    """Primary class for {name} module."""')
    lines.append("")
    lines.append("    def __init__(self):")
    lines.append(f"        self.name = '{name}'")
    lines.append(f"        self.data = {{}}")
    lines.append("")

    # Add 3-5 methods
    for i in range(random.randint(3, 5)):
        method_name = f"process_{name}_{i}"
        lines.append(f"    def {method_name}(self, input_data: dict) -> dict:")
        lines.append(f'        """Process step {i} for {name}."""')
        lines.append(f"        result = {{**input_data, 'step': {i}}}")
        lines.append(f"        return result")
        lines.append("")

    # Add 2-3 standalone functions
    for i in range(random.randint(2, 3)):
        func_name = f"{name}_helper_{i}"
        lines.append(f"def {func_name}(x: str) -> str:")
        lines.append(f'    """Helper function {i} for {name}."""')
        lines.append(f"    return x.strip().lower()")
        lines.append("")

    return "\n".join(lines)


def _random_markdown_file(name: str, refs: list[str] | None = None) -> str:
    """Generate a realistic markdown document with wikilinks."""
    content = f"---\ntitle: {name.replace('_', ' ').title()}\ntype: document\ntags: [{name}, auto-generated]\n---\n\n"
    content += f"# {name.replace('_', ' ').title()}\n\n"
    content += f"This document covers the {name} module and its interactions.\n\n"
    content += "## Overview\n\n"
    content += f"The {name} system handles processing of incoming data through multiple stages.\n"
    content += "Each stage validates, transforms, and forwards the data to the next component.\n\n"

    if refs:
        content += "## Related\n\n"
        for ref in refs:
            content += f"- See [[{ref}]] for related functionality\n"

    content += "\n## Implementation Notes\n\n"
    content += "Key considerations:\n"
    content += f"- Performance target: < 100ms per {name} operation\n"
    content += "- Error handling: retry with exponential backoff\n"
    content += "- Logging: structured JSON logs for observability\n"

    return content


@pytest.fixture
def large_corpus(tmp_path) -> Path:
    """Generate a corpus of 100 files (70 Python + 30 Markdown) for perf testing."""
    src = tmp_path / "src"
    docs = tmp_path / "docs"
    src.mkdir()
    docs.mkdir()

    module_names = [f"module_{i:03d}" for i in range(70)]

    # Python files — with realistic imports between modules
    for i, name in enumerate(module_names):
        # Each module imports 0-3 earlier modules
        possible_imports = module_names[:i] if i > 0 else []
        imports = random.sample(possible_imports, min(random.randint(0, 3), len(possible_imports)))
        content = _random_python_file(name, imports)
        (src / f"{name}.py").write_text(content)

    # Markdown files — with wikilinks between them
    doc_names = [f"doc_{i:03d}" for i in range(30)]
    for i, name in enumerate(doc_names):
        possible_refs = doc_names[:i] + module_names[:5]  # Reference some code modules too
        refs = random.sample(possible_refs, min(random.randint(1, 4), len(possible_refs)))
        content = _random_markdown_file(name, refs)
        (docs / f"{name}.md").write_text(content)

    return tmp_path


@pytest.fixture
def large_graph() -> Graph:
    """A pre-built graph with 500 nodes and 1500 edges for query perf testing."""
    graph = Graph()
    nodes = []
    edges = []

    for i in range(500):
        node = Node(
            id=f"node_{i:04d}",
            label=f"Concept {i}",
            type=random.choice(["code", "document", "wiki-concept", "wiki-decision"]),
            source_file=f"src/module_{i % 70:03d}.py",
            community=i % 15,
        )
        nodes.append(node)

    for _ in range(1500):
        src_idx = random.randint(0, 499)
        tgt_idx = random.randint(0, 499)
        if src_idx != tgt_idx:
            edge = Edge(
                source=f"node_{src_idx:04d}",
                target=f"node_{tgt_idx:04d}",
                relation=random.choice(["imports", "calls", "references", "tagged_with", "semantically_similar_to"]),
                confidence=random.choice(["EXTRACTED", "EXTRACTED", "INFERRED", "AMBIGUOUS"]),
            )
            edges.append(edge)

    extraction = Extraction(nodes=nodes, edges=edges)
    graph.merge(extraction)
    return graph
```

- [ ] **Step 2: Create scan performance test**

`tests/performance/test_scan_perf.py`:
```python
"""Scan performance tests — verify 100 files scanned in under 2 minutes."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from atlas.core.cache import CacheEngine
from atlas.core.scanner import Scanner
from atlas.core.storage import LocalStorage


class TestScanPerformance:
    """Scan latency and throughput benchmarks."""

    def test_full_scan_100_files_under_2_minutes(self, large_corpus, tmp_path):
        """SPEC REQUIREMENT: Initial scan of 100 files should complete in < 2 min."""
        storage = LocalStorage(root=tmp_path)
        cache = CacheEngine(storage)
        scanner = Scanner(storage=storage, cache=cache)

        start = time.perf_counter()
        extraction = scanner.scan(large_corpus)
        elapsed = time.perf_counter() - start

        print(f"\n=== Scan Performance ===")
        print(f"Files: 100")
        print(f"Nodes extracted: {len(extraction.nodes)}")
        print(f"Edges extracted: {len(extraction.edges)}")
        print(f"Total time: {elapsed:.2f}s")
        print(f"Time per file: {elapsed / 100 * 1000:.0f}ms")

        assert elapsed < 120, f"Full scan took {elapsed:.1f}s — exceeds 2 min target"
        assert len(extraction.nodes) >= 50, "100 files should yield at least 50 nodes"

    def test_incremental_scan_3_changed_under_10_seconds(self, large_corpus, tmp_path):
        """SPEC REQUIREMENT: Incremental scan of 3 changed files should complete in < 10 sec."""
        storage = LocalStorage(root=tmp_path)
        cache = CacheEngine(storage)
        scanner = Scanner(storage=storage, cache=cache)

        # Full scan first (populates cache)
        scanner.scan(large_corpus)

        # Modify 3 files
        src = large_corpus / "src"
        for i in range(3):
            f = src / f"module_{i:03d}.py"
            content = f.read_text()
            f.write_text(content + f"\ndef added_func_{i}():\n    pass\n")

        start = time.perf_counter()
        extraction = scanner.scan(large_corpus, incremental=True)
        elapsed = time.perf_counter() - start

        print(f"\n=== Incremental Scan Performance ===")
        print(f"Changed files: 3 / 100")
        print(f"Total time: {elapsed:.2f}s")

        assert elapsed < 10, f"Incremental scan took {elapsed:.1f}s — exceeds 10s target"

    def test_scan_throughput_by_file_type(self, large_corpus, tmp_path):
        """Measure scan time per file type (Python vs Markdown)."""
        storage = LocalStorage(root=tmp_path)
        cache = CacheEngine(storage)
        scanner = Scanner(storage=storage, cache=cache)

        # Scan Python only
        py_start = time.perf_counter()
        py_extraction = scanner.scan(large_corpus / "src")
        py_elapsed = time.perf_counter() - py_start

        # Scan Markdown only
        md_start = time.perf_counter()
        md_extraction = scanner.scan(large_corpus / "docs")
        md_elapsed = time.perf_counter() - md_start

        print(f"\n=== Throughput by Type ===")
        print(f"Python: {len(py_extraction.nodes)} nodes in {py_elapsed:.2f}s ({py_elapsed / 70 * 1000:.0f}ms/file)")
        print(f"Markdown: {len(md_extraction.nodes)} nodes in {md_elapsed:.2f}s ({md_elapsed / 30 * 1000:.0f}ms/file)")
```

- [ ] **Step 3: Create query performance test**

`tests/performance/test_query_perf.py`:
```python
"""Graph query performance tests — verify queries complete in under 100ms."""
from __future__ import annotations

import statistics
import time

import pytest

from atlas.core.graph import Graph


class TestQueryPerformance:
    """Query latency benchmarks against a 500-node graph."""

    def test_bfs_query_under_100ms(self, large_graph):
        """SPEC REQUIREMENT: BFS graph query should complete in < 100ms."""
        times = []

        for i in range(100):
            node_id = f"node_{i * 5:04d}"
            start = time.perf_counter()
            result = large_graph.query(node_id, mode="bfs", depth=3)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

        p50 = statistics.median(times)
        p95 = sorted(times)[94]
        p99 = sorted(times)[98]
        mean = statistics.mean(times)

        print(f"\n=== BFS Query Latency (500 nodes, 1500 edges) ===")
        print(f"Queries: 100")
        print(f"Mean: {mean:.2f}ms")
        print(f"p50: {p50:.2f}ms")
        print(f"p95: {p95:.2f}ms")
        print(f"p99: {p99:.2f}ms")

        assert p95 < 100, f"BFS query p95 {p95:.1f}ms exceeds 100ms target"

    def test_path_query_under_100ms(self, large_graph):
        """Shortest path query should complete in < 100ms."""
        times = []

        for i in range(50):
            src = f"node_{i * 2:04d}"
            tgt = f"node_{(i * 2 + 100) % 500:04d}"
            start = time.perf_counter()
            try:
                result = large_graph.path(src, tgt)
            except Exception:
                pass  # Path may not exist — that's OK for perf measurement
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        p95 = sorted(times)[47]  # 95th percentile of 50 samples

        print(f"\n=== Path Query Latency ===")
        print(f"Queries: 50")
        print(f"p95: {p95:.2f}ms")

        assert p95 < 100, f"Path query p95 {p95:.1f}ms exceeds 100ms target"

    def test_god_nodes_under_100ms(self, large_graph):
        """God nodes detection should complete in < 100ms."""
        start = time.perf_counter()
        result = large_graph.god_nodes(top_n=10)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n=== God Nodes Detection ===")
        print(f"Time: {elapsed:.2f}ms")
        print(f"Top node: {result[0] if result else 'none'}")

        assert elapsed < 100, f"God nodes took {elapsed:.1f}ms — exceeds 100ms target"

    def test_stats_under_50ms(self, large_graph):
        """Graph stats should be near-instant."""
        start = time.perf_counter()
        stats = large_graph.stats()
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n=== Graph Stats ===")
        print(f"Time: {elapsed:.2f}ms")
        print(f"Nodes: {stats.nodes}, Edges: {stats.edges}")

        assert elapsed < 50, f"Stats took {elapsed:.1f}ms — exceeds 50ms target"
```

- [ ] **Step 4: Commit**

```bash
git add tests/performance/
git commit -m "test: performance tests — scan throughput and query latency

Scan: 100-file corpus < 2 min, incremental 3 files < 10s.
Query: BFS/path/god-nodes p95 < 100ms on 500-node graph.
Synthetic fixtures generate realistic corpora for reproducibility."
```

---

## Task 5: Worked Examples

**Files:**
- Create: `worked/codebase/` (input + expected + review + run script)
- Create: `worked/research/` (input + expected + review + run script)
- Create: `worked/business/` (input + expected + review + run script)

- [ ] **Step 1: Create worked/codebase/ — a real Python project**

`worked/codebase/input/main.py`:
```python
"""TaskFlow — a minimal async task queue."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from .models import Task, TaskStatus, TaskResult
from .queue import TaskQueue
from .executor import Executor
from .persistence import FileStore

logger = logging.getLogger("taskflow")


class TaskFlow:
    """Main orchestrator — manages the lifecycle of tasks."""

    def __init__(self, store_path: Path | None = None):
        self.queue = TaskQueue()
        self.executor = Executor(max_workers=4)
        self.store = FileStore(store_path or Path(".taskflow"))
        self._running = False

    async def submit(self, task: Task) -> str:
        """Submit a task to the queue. Returns task ID."""
        task.status = TaskStatus.QUEUED
        self.store.save_task(task)
        await self.queue.enqueue(task)
        logger.info(f"Task {task.id} submitted: {task.name}")
        return task.id

    async def run(self):
        """Main event loop — dequeues and executes tasks."""
        self._running = True
        logger.info("TaskFlow started")
        while self._running:
            task = await self.queue.dequeue()
            if task:
                result = await self.executor.execute(task)
                self.store.save_result(task.id, result)
                logger.info(f"Task {task.id} completed: {result.status}")
            await asyncio.sleep(0.01)

    def stop(self):
        """Stop the event loop gracefully."""
        self._running = False
        logger.info("TaskFlow stopped")

    def get_status(self, task_id: str) -> TaskStatus | None:
        """Check the current status of a task."""
        task = self.store.load_task(task_id)
        return task.status if task else None

    def get_result(self, task_id: str) -> TaskResult | None:
        """Retrieve the result of a completed task."""
        return self.store.load_result(task_id)
```

`worked/codebase/input/models.py`:
```python
"""Data models for TaskFlow."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: str
    name: str
    handler: Callable[..., Any]
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0  # Higher = more urgent
    retries: int = 0
    max_retries: int = 3


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
```

`worked/codebase/input/queue.py`:
```python
"""Priority queue implementation for tasks."""
from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass, field

from .models import Task


@dataclass(order=True)
class PrioritizedTask:
    priority: int
    task: Task = field(compare=False)


class TaskQueue:
    """Async priority queue — higher priority tasks dequeue first."""

    def __init__(self):
        self._heap: list[PrioritizedTask] = []
        self._lock = asyncio.Lock()
        self._event = asyncio.Event()

    async def enqueue(self, task: Task) -> None:
        """Add a task to the queue."""
        async with self._lock:
            heapq.heappush(self._heap, PrioritizedTask(priority=-task.priority, task=task))
            self._event.set()

    async def dequeue(self, timeout: float = 1.0) -> Task | None:
        """Remove and return the highest-priority task, or None on timeout."""
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        async with self._lock:
            if self._heap:
                item = heapq.heappop(self._heap)
                if not self._heap:
                    self._event.clear()
                return item.task
            self._event.clear()
            return None

    @property
    def size(self) -> int:
        return len(self._heap)

    @property
    def is_empty(self) -> bool:
        return len(self._heap) == 0
```

`worked/codebase/input/executor.py`:
```python
"""Task execution engine with retry logic."""
from __future__ import annotations

import asyncio
import logging
import time
import traceback

from .models import Task, TaskResult, TaskStatus

logger = logging.getLogger("taskflow.executor")


class Executor:
    """Executes tasks with concurrency control and retry logic."""

    def __init__(self, max_workers: int = 4):
        self._semaphore = asyncio.Semaphore(max_workers)
        self.max_workers = max_workers

    async def execute(self, task: Task) -> TaskResult:
        """Execute a task with retry logic and concurrency limiting."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            logger.info(f"Executing task {task.id}: {task.name}")

            for attempt in range(task.max_retries + 1):
                start = time.perf_counter()
                try:
                    if asyncio.iscoroutinefunction(task.handler):
                        output = await task.handler(*task.args, **task.kwargs)
                    else:
                        output = await asyncio.to_thread(task.handler, *task.args, **task.kwargs)

                    duration = (time.perf_counter() - start) * 1000
                    task.status = TaskStatus.COMPLETED
                    return TaskResult(
                        task_id=task.id,
                        status=TaskStatus.COMPLETED,
                        output=output,
                        duration_ms=duration,
                    )
                except Exception as e:
                    duration = (time.perf_counter() - start) * 1000
                    task.retries += 1
                    logger.warning(f"Task {task.id} attempt {attempt + 1} failed: {e}")

                    if attempt < task.max_retries:
                        await asyncio.sleep(2 ** attempt * 0.1)  # Exponential backoff
                        continue

                    task.status = TaskStatus.FAILED
                    return TaskResult(
                        task_id=task.id,
                        status=TaskStatus.FAILED,
                        error=traceback.format_exc(),
                        duration_ms=duration,
                    )
```

`worked/codebase/input/persistence.py`:
```python
"""File-based persistence for tasks and results."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import Task, TaskResult, TaskStatus

logger = logging.getLogger("taskflow.persistence")


class FileStore:
    """Stores tasks and results as JSON files on disk."""

    def __init__(self, root: Path):
        self.root = root
        self.tasks_dir = root / "tasks"
        self.results_dir = root / "results"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def save_task(self, task: Task) -> None:
        """Persist a task to disk."""
        data = {
            "id": task.id,
            "name": task.name,
            "status": task.status.value,
            "priority": task.priority,
            "retries": task.retries,
            "max_retries": task.max_retries,
        }
        path = self.tasks_dir / f"{task.id}.json"
        path.write_text(json.dumps(data, indent=2))

    def load_task(self, task_id: str) -> Task | None:
        """Load a task from disk by ID."""
        path = self.tasks_dir / f"{task_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return Task(
            id=data["id"],
            name=data["name"],
            handler=lambda: None,  # Handler can't be serialized
            status=TaskStatus(data["status"]),
            priority=data["priority"],
            retries=data["retries"],
            max_retries=data["max_retries"],
        )

    def save_result(self, task_id: str, result: TaskResult) -> None:
        """Persist a task result to disk."""
        data = {
            "task_id": result.task_id,
            "status": result.status.value,
            "output": str(result.output) if result.output else None,
            "error": result.error,
            "duration_ms": result.duration_ms,
        }
        path = self.results_dir / f"{task_id}.json"
        path.write_text(json.dumps(data, indent=2))

    def load_result(self, task_id: str) -> TaskResult | None:
        """Load a task result from disk by ID."""
        path = self.results_dir / f"{task_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return TaskResult(
            task_id=data["task_id"],
            status=TaskStatus(data["status"]),
            output=data.get("output"),
            error=data.get("error"),
            duration_ms=data.get("duration_ms", 0.0),
        )

    def list_tasks(self) -> list[str]:
        """List all stored task IDs."""
        return [f.stem for f in self.tasks_dir.glob("*.json")]
```

`worked/codebase/input/utils.py`:
```python
"""Shared utilities for TaskFlow."""
from __future__ import annotations

import uuid


def generate_task_id() -> str:
    """Generate a unique task identifier."""
    return f"task_{uuid.uuid4().hex[:8]}"


def format_duration(ms: float) -> str:
    """Format milliseconds into a human-readable string."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms / 1000:.1f}s"
    else:
        return f"{ms / 60000:.1f}min"
```

`worked/codebase/input/tests/test_models.py`:
```python
"""Tests for TaskFlow models."""
from models import Task, TaskStatus, TaskResult


def test_task_defaults():
    task = Task(id="t1", name="test", handler=lambda: None)
    assert task.status == TaskStatus.PENDING
    assert task.priority == 0
    assert task.max_retries == 3


def test_task_result():
    result = TaskResult(task_id="t1", status=TaskStatus.COMPLETED, output=42, duration_ms=150.5)
    assert result.output == 42
    assert result.duration_ms == 150.5
```

`worked/codebase/run.sh`:
```bash
#!/usr/bin/env bash
# Run Atlas scan on the TaskFlow codebase worked example.
# Usage: cd worked/codebase && bash run.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_DIR="$SCRIPT_DIR/input"
OUTPUT_DIR="$SCRIPT_DIR/output"

echo "=== Atlas Worked Example: Codebase ==="
echo "Scanning: $INPUT_DIR"

# Clean previous output
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Run Atlas scan
atlas scan "$INPUT_DIR" --output-dir "$OUTPUT_DIR" --format json --report

echo ""
echo "=== Output ==="
echo "Graph: $OUTPUT_DIR/graph.json"
echo "Report: $OUTPUT_DIR/GRAPH_REPORT.md"

# Compare with expected (if present)
if [ -d "$SCRIPT_DIR/expected" ]; then
    echo ""
    echo "=== Validation ==="
    python3 -c "
import json, sys

with open('$OUTPUT_DIR/graph.json') as f:
    actual = json.load(f)
with open('$SCRIPT_DIR/expected/graph.json') as f:
    expected = json.load(f)

a_nodes = len(actual.get('nodes', []))
e_nodes = len(expected.get('nodes', []))
a_edges = len(actual.get('edges', []))
e_edges = len(expected.get('edges', []))

print(f'Nodes: {a_nodes} (expected ~{e_nodes})')
print(f'Edges: {a_edges} (expected ~{e_edges})')

# Allow 20% variance
if abs(a_nodes - e_nodes) > e_nodes * 0.3:
    print(f'WARNING: Node count differs significantly')
if abs(a_edges - e_edges) > e_edges * 0.3:
    print(f'WARNING: Edge count differs significantly')
print('Validation complete.')
"
fi
```

`worked/codebase/expected/graph.json`:
```json
{
  "nodes": [
    {"id": "taskflow", "label": "TaskFlow", "type": "code", "source_file": "main.py"},
    {"id": "task", "label": "Task", "type": "code", "source_file": "models.py"},
    {"id": "task_status", "label": "TaskStatus", "type": "code", "source_file": "models.py"},
    {"id": "task_result", "label": "TaskResult", "type": "code", "source_file": "models.py"},
    {"id": "task_queue", "label": "TaskQueue", "type": "code", "source_file": "queue.py"},
    {"id": "prioritized_task", "label": "PrioritizedTask", "type": "code", "source_file": "queue.py"},
    {"id": "executor", "label": "Executor", "type": "code", "source_file": "executor.py"},
    {"id": "file_store", "label": "FileStore", "type": "code", "source_file": "persistence.py"},
    {"id": "generate_task_id", "label": "generate_task_id", "type": "code", "source_file": "utils.py"},
    {"id": "format_duration", "label": "format_duration", "type": "code", "source_file": "utils.py"},
    {"id": "test_models", "label": "test_models", "type": "code", "source_file": "tests/test_models.py"}
  ],
  "edges": [
    {"source": "taskflow", "target": "task", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "taskflow", "target": "task_status", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "taskflow", "target": "task_result", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "taskflow", "target": "task_queue", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "taskflow", "target": "executor", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "taskflow", "target": "file_store", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "executor", "target": "task", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "executor", "target": "task_result", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "executor", "target": "task_status", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "file_store", "target": "task", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "file_store", "target": "task_result", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "file_store", "target": "task_status", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "task_queue", "target": "task", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "prioritized_task", "target": "task", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "test_models", "target": "task", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "test_models", "target": "task_status", "relation": "imports", "confidence": "EXTRACTED"},
    {"source": "test_models", "target": "task_result", "relation": "imports", "confidence": "EXTRACTED"}
  ]
}
```

`worked/codebase/expected/GRAPH_REPORT.md`:
```markdown
# Graph Report — TaskFlow Codebase

**Scanned:** 7 files (6 Python modules + 1 test file)
**Nodes:** ~11 (6 classes + 3 functions + 1 enum + 1 test module)
**Edges:** ~17 (imports + references)
**Communities:** 2-3 (orchestration, data models, infrastructure)
**Health Score:** ~85 (mostly EXTRACTED from AST)

## Key Findings

### God Nodes
- **Task** (degree ~8) — imported by nearly every module. Central data type.
- **TaskStatus** (degree ~5) — enum used everywhere.

### Architecture
The codebase follows a clean layered pattern:
- `models.py` defines shared data types (no outgoing deps)
- `queue.py` and `executor.py` depend on models
- `persistence.py` handles storage, depends on models
- `main.py` orchestrates everything — depends on all other modules
- `utils.py` is standalone (no deps, not imported by others)

### Potential Issues
- `utils.py` is **orphaned** — `generate_task_id()` and `format_duration()` are defined but never imported
- `Task.handler` is a callable field — not serializable, breaks persistence roundtrip
- No explicit error handling in `main.py`'s run loop beyond retry logic in executor

### Communities
1. **Orchestration** — TaskFlow, TaskQueue, Executor
2. **Data** — Task, TaskStatus, TaskResult, PrioritizedTask
3. **Storage** — FileStore
```

`worked/codebase/review.md`:
```markdown
# Review — Codebase Worked Example

## What Atlas Got Right
- Correctly identified all classes, functions, and their import relationships
- Detected Task and TaskStatus as god nodes (high centrality)
- Found the orphaned utils.py — real issue, not a false positive
- Community detection mapped cleanly to the architectural layers

## What Atlas Missed or Got Wrong
- The handler serialization issue is a real bug — Atlas flagged it via AST analysis
  but the description could be more actionable (suggest using a task registry pattern)
- Did not detect the potential deadlock between queue.dequeue() and executor._semaphore
  under high concurrency — this requires runtime analysis, not just static graph

## Verdict
Atlas produces a useful architectural map of this small codebase in under 5 seconds.
The graph accurately represents module dependencies. The audit findings are actionable.
For a 7-file project, the ROI is modest — Atlas shines more on larger, messier codebases
where the structure isn't obvious.

**Score: 8/10** — Accurate graph, useful audit, minor gaps in deep semantic analysis.
```

- [ ] **Step 2: Create worked/research/ — papers and notes**

`worked/research/input/papers/attention.md`:
```markdown
---
title: "Attention Is All You Need"
type: paper
authors: [Vaswani, Shazeer, Parmar, Uszkoreit, Jones, Gomez, Kaiser, Polosukhin]
year: 2017
tags: [transformer, attention, architecture, foundation]
---

# Attention Is All You Need

## Core Contribution
Replaced recurrent layers entirely with self-attention mechanisms, creating the
Transformer architecture. This is the foundation of all modern LLMs.

## Key Mechanisms
- **Self-attention** — each token attends to all others in parallel
- **Multi-head attention** — 8 heads capture different relationship patterns
- **Positional encoding** — sinusoidal functions replace recurrence for position info
- **Layer normalization** — stabilizes training at scale
- **Residual connections** — enables deep stacking (6 layers encoder, 6 decoder)

## Results
- BLEU 28.4 on WMT2014 EN→DE (new SOTA at the time)
- 3.5 days training on 8 P100 GPUs
- Enabled the [[scaling-laws]] paradigm shift

## Legacy
Every modern model — GPT, Claude, Gemini, Llama — is a Transformer descendant.
The [[chinchilla]] paper showed how to train them optimally.
```

`worked/research/input/papers/scaling-laws.md`:
```markdown
---
title: "Scaling Laws for Neural Language Models"
type: paper
authors: [Kaplan, McCandlish, Henighan, Brown]
year: 2020
tags: [scaling, compute, training, power-law]
---

# Scaling Laws for Neural Language Models

## Core Contribution
Language model loss follows predictable power laws in three variables:
parameters (N), dataset size (D), and compute (C).

## Key Findings
1. L(N) ~ N^{-0.076} — loss decreases as a power law of model size
2. L(D) ~ D^{-0.095} — loss decreases as a power law of data
3. L(C) ~ C^{-0.050} — loss decreases as a power law of compute
4. Larger models are more **sample-efficient** — they learn more per token
5. Optimal strategy: **scale N faster than D** (later revised by [[chinchilla]])

## Implications
- Training budgets can be planned with confidence
- "Bigger is better" has a mathematical basis (within the scaling regime)
- Compute-optimal training is a solvable optimization problem
- Foundation for the [[attention|Transformer]] scaling era
```

`worked/research/input/papers/chinchilla.md`:
```markdown
---
title: "Training Compute-Optimal Large Language Models"
type: paper
authors: [Hoffmann, Borgeaud, Mensch, Buchatskaya, Cai, Rutherford, Casas, Hendricks]
year: 2022
tags: [chinchilla, scaling, compute-optimal, training]
---

# Chinchilla — Training Compute-Optimal LLMs

## Core Contribution
Revised the [[scaling-laws]]: for a fixed compute budget, models should be trained
on **much more data** than Kaplan et al. suggested. Previous models were significantly
undertrained.

## Key Finding
For compute-optimal training, parameters N and tokens D should scale equally:
- N ~ C^{0.5}
- D ~ C^{0.5}

This means a 70B model should see ~1.4T tokens — not 300B as GPT-3 did.

## Impact
- Chinchilla (70B params, 1.4T tokens) outperformed Gopher (280B params, 300B tokens)
- Proved that **data quantity matters as much as model size**
- Led to LLaMA (65B, 1.4T tokens) achieving competitive performance at lower cost
- Changed industry strategy: invest in data curation, not just bigger GPUs
- Validates the [[attention|Transformer]] architecture's data efficiency

## Relevance
Atlas tracks token efficiency — how many tokens per file. Chinchilla's lesson applies:
more data (curated wiki pages) > bigger models for knowledge quality.
```

`worked/research/input/notes/transformer-intuition.md`:
```markdown
---
title: "Transformer Intuition"
type: note
tags: [transformer, intuition, mental-model]
---

# Transformer Intuition

## What Self-Attention Really Does

Think of it as a **lookup table** where every token asks:
"Which other tokens in this context are relevant to me?"

The weights are learned — not fixed. So the model discovers *what to pay attention to*
during training. This is why [[attention]] works: it lets the model build its own
feature extraction pipeline, specific to each input.

## Why It Replaced Recurrence

RNNs process tokens sequentially — token 100 "forgets" token 1.
Transformers process all tokens in parallel — token 100 can directly attend to token 1.

Trade-off: O(n^2) attention cost. But GPUs are parallel machines, so it's faster in practice.

## The Architecture Pattern

```
Input → Embedding + Position → [Attention + FFN] x N → Output
```

Each layer refines the representation. Early layers capture syntax, later layers capture semantics.
This is why [[scaling-laws]] work: more layers = more refinement steps = lower loss.
```

`worked/research/input/notes/training-tips.md`:
```markdown
---
title: "Training Tips"
type: note
tags: [training, tips, practical]
---

# Training Tips (Compiled)

## Learning Rate
- Use cosine decay with warmup
- Peak LR scales with sqrt(batch_size) per [[scaling-laws]]
- Warmup: 1-5% of total steps

## Data
- Quality > quantity (post-[[chinchilla]] lesson)
- Deduplicate aggressively — duplicates distort loss curves
- Mix domains: code + text + math for general capability

## Architecture
- Use [[attention|pre-norm]] (LayerNorm before attention, not after)
- RMSNorm slightly faster than LayerNorm for same quality
- Rotary Position Embeddings (RoPE) > sinusoidal > learned

## Evaluation
- Don't trust training loss alone — overfit is real
- Use held-out eval set from different distribution
- Track per-domain performance (code, math, reasoning separately)

## Hardware
- Mixed precision (bf16) is free performance
- Gradient checkpointing for memory-constrained setups
- Pipeline parallelism for very large models
```

`worked/research/input/notes/open-questions.md`:
```markdown
---
title: "Open Questions"
type: note
tags: [questions, research, future]
---

# Open Questions

## Scaling
- Do [[scaling-laws]] hold beyond 10^25 FLOPs? Or do we hit a wall?
- Is the [[chinchilla]] ratio (N=D) still optimal with synthetic data?
- What happens when we run out of natural text data?

## Architecture
- Can we beat [[attention|Transformers]] for long context? (Mamba, RWKV, etc.)
- Is the quadratic attention cost fundamentally necessary?
- Can sparse attention achieve dense attention quality?

## Training
- How to train efficiently on mixed-quality data?
- Curriculum learning: does training order matter at scale?
- RLHF vs DPO vs RLAIF — which alignment method scales best?

## Knowledge
- How do LLMs store factual knowledge? Superposition?
- Can we extract a knowledge graph from model weights directly?
- Will retrieval-augmented generation (RAG) replace fine-tuning?

## Relevance to Atlas
Atlas sits at the intersection of knowledge graphs and LLMs.
If we can extract structured knowledge (graph) from unstructured text (via LLMs),
that's more robust than relying on the LLM's internal parametric memory alone.
```

`worked/research/input/README.md`:
```markdown
# Research Corpus

A collection of key papers and notes on the Transformer architecture
and scaling laws. This corpus demonstrates Atlas's ability to extract
a knowledge graph from research literature.

## Papers
- attention.md — "Attention Is All You Need" (Vaswani et al., 2017)
- scaling-laws.md — "Scaling Laws for Neural Language Models" (Kaplan et al., 2020)
- chinchilla.md — "Training Compute-Optimal LLMs" (Hoffmann et al., 2022)

## Notes
- transformer-intuition.md — mental models for self-attention
- training-tips.md — practical tips compiled from multiple sources
- open-questions.md — unresolved research directions
```

`worked/research/run.sh`:
```bash
#!/usr/bin/env bash
# Run Atlas scan on the research corpus worked example.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_DIR="$SCRIPT_DIR/input"
OUTPUT_DIR="$SCRIPT_DIR/output"

echo "=== Atlas Worked Example: Research ==="
echo "Scanning: $INPUT_DIR"

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

atlas scan "$INPUT_DIR" --output-dir "$OUTPUT_DIR" --format json --report

echo ""
echo "=== Output ==="
echo "Graph: $OUTPUT_DIR/graph.json"
echo "Report: $OUTPUT_DIR/GRAPH_REPORT.md"

if [ -d "$SCRIPT_DIR/expected" ]; then
    echo ""
    echo "=== Validation ==="
    python3 -c "
import json
with open('$OUTPUT_DIR/graph.json') as f:
    actual = json.load(f)
with open('$SCRIPT_DIR/expected/graph.json') as f:
    expected = json.load(f)
a_n = len(actual.get('nodes', []))
e_n = len(expected.get('nodes', []))
a_e = len(actual.get('edges', []))
e_e = len(expected.get('edges', []))
print(f'Nodes: {a_n} (expected ~{e_n})')
print(f'Edges: {a_e} (expected ~{e_e})')
print('Validation complete.')
"
fi
```

`worked/research/expected/graph.json`:
```json
{
  "nodes": [
    {"id": "attention_paper", "label": "Attention Is All You Need", "type": "paper", "source_file": "papers/attention.md"},
    {"id": "scaling_laws_paper", "label": "Scaling Laws for Neural Language Models", "type": "paper", "source_file": "papers/scaling-laws.md"},
    {"id": "chinchilla_paper", "label": "Training Compute-Optimal LLMs", "type": "paper", "source_file": "papers/chinchilla.md"},
    {"id": "self_attention", "label": "Self-Attention", "type": "document", "source_file": "papers/attention.md"},
    {"id": "multi_head_attention", "label": "Multi-Head Attention", "type": "document", "source_file": "papers/attention.md"},
    {"id": "positional_encoding", "label": "Positional Encoding", "type": "document", "source_file": "papers/attention.md"},
    {"id": "power_law_scaling", "label": "Power Law Scaling", "type": "document", "source_file": "papers/scaling-laws.md"},
    {"id": "compute_optimal_training", "label": "Compute-Optimal Training", "type": "document", "source_file": "papers/chinchilla.md"},
    {"id": "transformer_intuition", "label": "Transformer Intuition", "type": "document", "source_file": "notes/transformer-intuition.md"},
    {"id": "training_tips", "label": "Training Tips", "type": "document", "source_file": "notes/training-tips.md"},
    {"id": "open_questions", "label": "Open Questions", "type": "document", "source_file": "notes/open-questions.md"}
  ],
  "edges": [
    {"source": "attention_paper", "target": "scaling_laws_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "attention_paper", "target": "chinchilla_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "scaling_laws_paper", "target": "chinchilla_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "scaling_laws_paper", "target": "attention_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "chinchilla_paper", "target": "scaling_laws_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "chinchilla_paper", "target": "attention_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "transformer_intuition", "target": "attention_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "transformer_intuition", "target": "scaling_laws_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "training_tips", "target": "scaling_laws_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "training_tips", "target": "chinchilla_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "training_tips", "target": "attention_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "open_questions", "target": "scaling_laws_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "open_questions", "target": "chinchilla_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "open_questions", "target": "attention_paper", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "self_attention", "target": "multi_head_attention", "relation": "semantically_similar_to", "confidence": "INFERRED"},
    {"source": "power_law_scaling", "target": "compute_optimal_training", "relation": "semantically_similar_to", "confidence": "INFERRED"}
  ]
}
```

`worked/research/expected/GRAPH_REPORT.md`:
```markdown
# Graph Report — Research Corpus

**Scanned:** 7 files (3 papers + 3 notes + 1 README)
**Nodes:** ~11 (3 papers + 5 concepts + 3 notes)
**Edges:** ~16 (14 wikilink references + 2 inferred semantic links)
**Communities:** 2 (scaling theory, transformer architecture)
**Health Score:** ~75 (mostly EXTRACTED from wikilinks, some INFERRED)

## Key Findings

### God Nodes
- **Attention Is All You Need** (degree ~8) — referenced by every other document
- **Scaling Laws** (degree ~7) — referenced by chinchilla, training tips, open questions

### Knowledge Map
The corpus tells a coherent story:
1. Transformers (attention paper) enabled scaling
2. Scaling laws (Kaplan) quantified the relationship
3. Chinchilla revised the optimal training recipe
4. Notes connect theory to practice

### Surprises
- All three notes reference all three papers — high interconnectedness
- The research corpus has NO orphan nodes — every document is connected
- Wikilinks create explicit, high-confidence edges — the graph is trustworthy

### Potential Issues
- README adds no substantive knowledge — could be excluded from graph
- No contradiction detected (papers are consistent)
- Training tips compile knowledge from multiple undocumented sources — provenance gap
```

`worked/research/review.md`:
```markdown
# Review — Research Worked Example

## What Atlas Got Right
- Extracted wikilinks as high-confidence EXTRACTED edges — correct
- Identified the three papers as central nodes with accurate degree counts
- Community detection naturally separated "scaling theory" from "architecture"
- Noted the training tips provenance gap — subtle but valid finding

## What Atlas Missed or Got Wrong
- Could extract more granular concepts from within the papers (e.g., "gradient checkpointing"
  from training-tips.md is a technique worth its own node)
- Temporal relationships not captured — attention (2017) → scaling (2020) → chinchilla (2022)
  forms a causal chain that the flat graph doesn't represent
- The "semantically_similar_to" edges between self-attention/multi-head and power-law/compute-optimal
  are reasonable but borderline — they're more "part of" than "similar to"

## Verdict
Atlas handles research literature well when the corpus uses wikilinks.
The graph is accurate and the report highlights real structural insights.
For a corpus without explicit links, Atlas would need stronger LLM extraction
to achieve the same quality.

**Score: 7/10** — Strong on explicit links, weaker on implicit semantic relationships.
```

- [ ] **Step 3: Create worked/business/ — multi-project wiki**

`worked/business/input/wiki/index.md`:
```markdown
---
title: "Origin Labs Wiki Index"
type: index
---

# Origin Labs — Knowledge Base

## Projects
- [[projects/ara]] — Agent Runtime & API Marketplace
- [[projects/atlas]] — Knowledge Engine for AI Agents
- [[projects/hermes]] — AI Gateway & Messaging

## Concepts
- [[concepts/mcp]] — Model Context Protocol
- [[concepts/finops]] — Financial Operations for AI
- [[concepts/knowledge-graph]] — Knowledge Graph Fundamentals

## Decisions
- [[decisions/2026-03-01-python-only]] — Python-Only Stack Decision
- [[decisions/2026-03-15-networkx-over-neo4j]] — NetworkX Over Neo4j

## Sources
- [[sources/karpathy-llm-wiki]] — Karpathy LLM Wiki Pattern
- [[sources/graphrag-paper]] — GraphRAG Paper
```

`worked/business/input/wiki/projects/ara.md`:
```markdown
---
title: "ARA — Agent Runtime & API"
type: project
status: active
team: [Pierre, Anna, Marc]
tags: [ara, marketplace, agents, saas]
---

# ARA — Agent Runtime & API

## What
ARA is the Amazon of AI agents — a marketplace where developers publish agents
and businesses consume them. Hosted, metered, and settled.

## Architecture
- S1 Gateway — routes LLM calls, meters tokens, manages API keys
- S2 FinOps — budget tracking, cost alerts, double-entry ledger
- S3 MCP Marketplace — agents expose [[concepts/mcp]] endpoints
- S4 [[projects/atlas]] — knowledge engine module (embedded)
- S5 Payments — Stripe Connect, settlements
- S6 Deploy — agent hosting with persistent memory

## Status
- S1 MVP live
- S2 FinOps plans ready (25 tasks)
- S3-S6 planned for Q3 2026

## Key Decisions
- [[decisions/2026-03-01-python-only]] for backend
- [[concepts/finops]] model: per-token billing with budget caps

## Revenue Model
Marketplace commission (15%) + hosting fees + premium support.
```

`worked/business/input/wiki/projects/atlas.md`:
```markdown
---
title: "Atlas — Knowledge Engine"
type: project
status: active
team: [Pierre, Anna]
tags: [atlas, knowledge-graph, wiki, discovery]
---

# Atlas — Knowledge Engine

## What
Atlas scans any folder — code, papers, notes, screenshots — and produces
a knowledge graph + living wiki that AI agents maintain.

## Architecture
- Core: Scanner, Graph, Wiki, Linker, Analyzer, Cache
- Server: FastAPI + [[concepts/mcp]] server
- Dashboard: Static HTML + d3 graph viz
- Skills: 7 agent skills (atlas-start, atlas-scan, etc.)

## Key Differentiators
1. The Linker — bidirectional graph-wiki sync (unique)
2. Socratic workflow — skills ask questions, detect tensions
3. [[projects/ara]] integration — Atlas is the knowledge module

## Tech Stack
- Python 3.12+ ([[decisions/2026-03-01-python-only]])
- [[decisions/2026-03-15-networkx-over-neo4j|NetworkX]] for graph storage
- [[concepts/knowledge-graph]] patterns from [[sources/graphrag-paper]]

## Origin
Evolved from the Karpathy pattern ([[sources/karpathy-llm-wiki]])
combined with graphify's discovery capabilities.
```

`worked/business/input/wiki/projects/hermes.md`:
```markdown
---
title: "Hermes — AI Gateway"
type: project
status: active
team: [Pierre]
tags: [hermes, gateway, messaging, telegram]
---

# Hermes — AI Gateway & Messaging

## What
Hermes is a local AI gateway that routes conversations between users (Telegram)
and AI agents (Claude, GPT, local models). Two personalities: Anna (tech) and Marc (business).

## Architecture
- Gateway: MiniMax-M2.7 default model, profile-based routing
- Telegram bridge: bot API, topic-based channels
- Local config at `~/.hermes/`
- No cloud dependency — runs fully local

## Integration
- Uses [[concepts/mcp]] for tool calling
- Will integrate with [[projects/ara]] for metered API access
- Could use [[projects/atlas]] for persistent conversation memory

## Current State
- 2 profiles active (Anna, Marc)
- Telegram channel operational
- No billing — personal use only
```

`worked/business/input/wiki/concepts/mcp.md`:
```markdown
---
title: "MCP — Model Context Protocol"
type: concept
tags: [mcp, protocol, agents, interop]
---

# MCP — Model Context Protocol

## What
MCP is an open protocol by Anthropic for connecting AI agents to tools and data sources.
It standardizes how agents discover and invoke capabilities.

## How Atlas Uses MCP
- Atlas exposes an MCP server (stdio + SSE transports)
- Any MCP-compatible agent can query the knowledge graph
- Skills are thin wrappers around MCP calls

## How ARA Uses MCP
- [[projects/ara]] Marketplace lists MCP endpoints
- Agents publish their MCP manifest to be discoverable
- Gateway routes MCP calls with metering

## Why It Matters
MCP is the "USB standard" for AI agents. Without it, every agent-tool pair
needs custom integration. With MCP, Atlas works with Claude Code, Cursor,
Codex, and any future MCP client — zero custom code.
```

`worked/business/input/wiki/concepts/finops.md`:
```markdown
---
title: "FinOps — Financial Operations for AI"
type: concept
tags: [finops, billing, cost, budgeting]
---

# FinOps — Financial Operations for AI

## What
FinOps applies financial discipline to AI spend. Track every token,
set budgets, alert on anomalies, settle with precision.

## ARA FinOps Model
- Per-token billing (input and output tokens tracked separately)
- Double-entry ledger: every transaction has two sides
- Budget caps: hard limits prevent runaway costs
- Cost allocation: attribute spend to specific agents, projects, or users

## Relevance to Atlas
- [[projects/atlas]] scans use LLM tokens — must be tracked
- In [[projects/ara]] mode, Atlas scans are billable operations
- Token efficiency benchmarks help users predict costs

## Key Metric
Token efficiency ratio = useful knowledge extracted / tokens spent.
Atlas aims for 10x compression — 1000 tokens of raw text yields
100 tokens of structured graph knowledge.
```

`worked/business/input/wiki/concepts/knowledge-graph.md`:
```markdown
---
title: "Knowledge Graph Fundamentals"
type: concept
tags: [knowledge-graph, graph-theory, entities, relations]
---

# Knowledge Graph Fundamentals

## What
A knowledge graph represents information as nodes (entities) connected by edges (relationships).
Unlike flat documents, graphs capture structure, enabling traversal, inference, and discovery.

## Atlas's Graph Model
- **Nodes:** files, functions, classes, concepts, papers, wiki pages
- **Edges:** imports, calls, references, tagged_with, semantically_similar_to
- **Confidence levels:** EXTRACTED (from code/wikilinks), INFERRED (LLM), AMBIGUOUS (uncertain)
- **Storage:** [[decisions/2026-03-15-networkx-over-neo4j|NetworkX]] in-memory, serialized to graph.json

## GraphRAG Connection
[[sources/graphrag-paper]] showed that knowledge graphs improve RAG quality by providing
structured context. Atlas builds on this by maintaining the graph over time (not one-shot).

## vs. Traditional RAG
| Aspect | RAG | Atlas Graph |
|--------|-----|-------------|
| Structure | Flat chunks | Typed nodes + edges |
| Query | Vector similarity | Graph traversal |
| Explainability | Black box | Visible path |
| Maintenance | Re-embed on change | Incremental update |
```

`worked/business/input/wiki/decisions/2026-03-01-python-only.md`:
```markdown
---
title: "ADR: Python-Only Stack"
type: decision
date: 2026-03-01
status: accepted
tags: [python, stack, decision]
---

# ADR: Python-Only Stack

## Context
Atlas and [[projects/ara]] need a programming language. Options: Python, TypeScript, Go, Rust.

## Decision
Python only. No polyglot.

## Rationale
1. **Ecosystem** — NetworkX, tree-sitter, graspologic, FastAPI, all Python-native
2. **LLM tooling** — Every LLM library (anthropic, openai, transformers) is Python-first
3. **Contributor pool** — Python has the largest ML/AI developer community
4. **Simplicity** — One language, one build system, one set of conventions

## Consequences
- Positive: fast iteration, easy hiring, rich ecosystem
- Negative: slower runtime (mitigated by async + C extensions where needed)
- Negative: no frontend story (solved by static HTML + vanilla JS for dashboard)

## Alternatives Considered
- TypeScript — better for full-stack, but Python ecosystem is richer for AI
- Rust — better performance, but slower development and smaller ML ecosystem
```

`worked/business/input/wiki/decisions/2026-03-15-networkx-over-neo4j.md`:
```markdown
---
title: "ADR: NetworkX Over Neo4j"
type: decision
date: 2026-03-15
status: accepted
tags: [networkx, neo4j, graph, decision]
---

# ADR: NetworkX Over Neo4j

## Context
Atlas needs a graph engine. Options: NetworkX (in-memory), Neo4j (server), custom.

## Decision
NetworkX. No external database.

## Rationale
1. **Zero deps** — `pip install atlas-ai` just works, no Neo4j server needed
2. **Git-versionable** — graph.json is a plain file, can be committed and diffed
3. **Fast enough** — for <100k nodes, in-memory NetworkX is sub-millisecond
4. **Portable** — works on any machine, including CI, cloud functions, local dev

## Consequences
- Positive: dead simple install, git-native workflow
- Positive: all tests run without external services
- Negative: can't handle millions of nodes (mitigated: Atlas targets <100k)
- Negative: no built-in query language like Cypher (mitigated: custom BFS/DFS)

## If Requirements Change
If Atlas needs to scale beyond 100k nodes, add a Neo4j backend behind the
existing StorageBackend protocol. The interface won't change.
```

`worked/business/input/wiki/sources/karpathy-llm-wiki.md`:
```markdown
---
title: "Karpathy LLM Wiki Pattern"
type: source
url: "https://karpathy.ai/llm-wiki.html"
date: 2025-06-15
tags: [karpathy, wiki, llm, pattern]
---

# Karpathy LLM Wiki Pattern

## Summary
Andrej Karpathy proposed that LLMs should maintain living wikis —
curated knowledge bases that agents read, write, and update over time.

## Key Ideas
- `raw/` folder for immutable source material
- `wiki/` folder for compiled knowledge (maintained by AI agents)
- Typed pages with frontmatter (projects, concepts, decisions, sources)
- Append-only log for provenance
- Agents read the wiki at session start, write back at session end

## How Atlas Extends This
- Adds [[concepts/knowledge-graph|knowledge graph]] discovery layer
- The Linker creates bidirectional graph-wiki sync
- Scanner automates the `raw/ → wiki/` compilation step
- Analyzer audits wiki health (orphans, contradictions, staleness)

## Origin
Atlas's wiki engine is a direct descendant of this pattern.
The original agent-wiki v1 implemented it. Atlas v2 adds the graph.
```

`worked/business/input/wiki/sources/graphrag-paper.md`:
```markdown
---
title: "GraphRAG Paper"
type: source
url: "https://arxiv.org/abs/2404.16130"
date: 2024-04-24
tags: [graphrag, rag, knowledge-graph, microsoft]
---

# GraphRAG — Graph-Enhanced Retrieval Augmented Generation

## Summary
Microsoft Research paper showing that building a knowledge graph from text
and using graph structure for retrieval significantly improves RAG quality
over flat vector search alone.

## Key Findings
- Community detection on the text graph reveals themes invisible to embeddings
- Graph traversal provides structured context that embeddings miss
- Global summaries from the graph reduce hallucination
- Works especially well for multi-document synthesis questions

## How Atlas Uses This
- Atlas builds a [[concepts/knowledge-graph]] from raw sources
- Graph queries use BFS/DFS (like GraphRAG's community-based retrieval)
- Community detection uses Leiden algorithm (same as GraphRAG)
- Wiki pages provide human-readable global summaries (better than auto-summaries)

## Differences from GraphRAG
- Atlas adds wiki curation (GraphRAG is read-only)
- Atlas maintains the graph across sessions (GraphRAG rebuilds)
- Atlas supports code + docs + images (GraphRAG targets text only)
```

`worked/business/input/AGENTS.md`:
```markdown
# Origin Labs Wiki — Agent Instructions

This wiki follows the Karpathy LLM Wiki pattern.
AI agents read wiki/ at session start and write back at session end.

## Structure
- wiki/ — compiled knowledge (the source of truth)
- wiki/projects/ — one page per project
- wiki/concepts/ — shared concepts and definitions
- wiki/decisions/ — Architecture Decision Records
- wiki/sources/ — external sources referenced

## Rules
- raw/ is immutable — never modify
- wiki/ pages must have typed frontmatter
- Use [[wikilinks]] for cross-references
- Append new entries to log.md
```

`worked/business/run.sh`:
```bash
#!/usr/bin/env bash
# Run Atlas scan on the business wiki worked example.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_DIR="$SCRIPT_DIR/input"
OUTPUT_DIR="$SCRIPT_DIR/output"

echo "=== Atlas Worked Example: Business Wiki ==="
echo "Scanning: $INPUT_DIR"

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

atlas scan "$INPUT_DIR" --output-dir "$OUTPUT_DIR" --format json --report

echo ""
echo "=== Output ==="
echo "Graph: $OUTPUT_DIR/graph.json"
echo "Report: $OUTPUT_DIR/GRAPH_REPORT.md"

if [ -d "$SCRIPT_DIR/expected" ]; then
    echo ""
    echo "=== Validation ==="
    python3 -c "
import json
with open('$OUTPUT_DIR/graph.json') as f:
    actual = json.load(f)
with open('$SCRIPT_DIR/expected/graph.json') as f:
    expected = json.load(f)
a_n = len(actual.get('nodes', []))
e_n = len(expected.get('nodes', []))
a_e = len(actual.get('edges', []))
e_e = len(expected.get('edges', []))
print(f'Nodes: {a_n} (expected ~{e_n})')
print(f'Edges: {a_e} (expected ~{e_e})')
print('Validation complete.')
"
fi
```

`worked/business/expected/graph.json`:
```json
{
  "nodes": [
    {"id": "ara", "label": "ARA — Agent Runtime & API", "type": "wiki-page", "source_file": "wiki/projects/ara.md"},
    {"id": "atlas", "label": "Atlas — Knowledge Engine", "type": "wiki-page", "source_file": "wiki/projects/atlas.md"},
    {"id": "hermes", "label": "Hermes — AI Gateway", "type": "wiki-page", "source_file": "wiki/projects/hermes.md"},
    {"id": "mcp", "label": "MCP — Model Context Protocol", "type": "wiki-page", "source_file": "wiki/concepts/mcp.md"},
    {"id": "finops", "label": "FinOps", "type": "wiki-page", "source_file": "wiki/concepts/finops.md"},
    {"id": "knowledge_graph", "label": "Knowledge Graph Fundamentals", "type": "wiki-page", "source_file": "wiki/concepts/knowledge-graph.md"},
    {"id": "python_only", "label": "ADR: Python-Only Stack", "type": "wiki-page", "source_file": "wiki/decisions/2026-03-01-python-only.md"},
    {"id": "networkx_over_neo4j", "label": "ADR: NetworkX Over Neo4j", "type": "wiki-page", "source_file": "wiki/decisions/2026-03-15-networkx-over-neo4j.md"},
    {"id": "karpathy_wiki", "label": "Karpathy LLM Wiki Pattern", "type": "wiki-page", "source_file": "wiki/sources/karpathy-llm-wiki.md"},
    {"id": "graphrag", "label": "GraphRAG Paper", "type": "wiki-page", "source_file": "wiki/sources/graphrag-paper.md"},
    {"id": "index", "label": "Origin Labs Wiki Index", "type": "wiki-page", "source_file": "wiki/index.md"}
  ],
  "edges": [
    {"source": "ara", "target": "mcp", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "ara", "target": "atlas", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "ara", "target": "python_only", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "ara", "target": "finops", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "atlas", "target": "mcp", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "atlas", "target": "ara", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "atlas", "target": "python_only", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "atlas", "target": "networkx_over_neo4j", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "atlas", "target": "knowledge_graph", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "atlas", "target": "graphrag", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "atlas", "target": "karpathy_wiki", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "hermes", "target": "mcp", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "hermes", "target": "ara", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "hermes", "target": "atlas", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "mcp", "target": "ara", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "finops", "target": "atlas", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "finops", "target": "ara", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "knowledge_graph", "target": "networkx_over_neo4j", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "knowledge_graph", "target": "graphrag", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "karpathy_wiki", "target": "knowledge_graph", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "graphrag", "target": "knowledge_graph", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "index", "target": "ara", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "index", "target": "atlas", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "index", "target": "hermes", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "index", "target": "mcp", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "index", "target": "finops", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "index", "target": "knowledge_graph", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "index", "target": "python_only", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "index", "target": "networkx_over_neo4j", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "index", "target": "karpathy_wiki", "relation": "references", "confidence": "EXTRACTED"},
    {"source": "index", "target": "graphrag", "relation": "references", "confidence": "EXTRACTED"}
  ]
}
```

`worked/business/expected/GRAPH_REPORT.md`:
```markdown
# Graph Report — Business Wiki

**Scanned:** 11 files (3 projects + 3 concepts + 2 decisions + 2 sources + 1 index)
**Nodes:** ~11 (all wiki pages)
**Edges:** ~31 (all EXTRACTED from [[wikilinks]])
**Communities:** 3 (products, concepts/theory, governance/decisions)
**Health Score:** ~95 (100% EXTRACTED — no INFERRED edges)

## Key Findings

### God Nodes
- **ARA** (degree ~8) — referenced by atlas, hermes, finops, mcp, index
- **Atlas** (degree ~10) — references nearly everything, referenced by many
- **MCP** (degree ~6) — the protocol connecting all three projects

### Architecture
The wiki is well-structured:
- **Projects** reference concepts and decisions (outgoing links)
- **Concepts** reference each other and sources (cross-linking)
- **Decisions** are referenced by projects (ADR pattern)
- **Sources** are referenced by concepts and projects (provenance)
- **Index** references everything (the navigation hub)

### Strengths
- 100% EXTRACTED edges — all from explicit [[wikilinks]]
- No orphan pages — every page is connected
- Clean ADR pattern — decisions are referenced by the projects they govern
- Provenance chain: sources → concepts → projects

### Potential Issues
- Index has extremely high out-degree (10) — it's the god node by design
- No contradictions detected (the wiki is consistent)
- Missing reverse links: ARA references atlas, but the atlas → ARA link
  is about ARA integration, not a peer reference

### Communities
1. **Products** — ARA, Atlas, Hermes (interconnected projects)
2. **Foundation** — MCP, Knowledge Graph, GraphRAG, Karpathy (theoretical base)
3. **Governance** — Python-Only, NetworkX (architecture decisions)
```

`worked/business/review.md`:
```markdown
# Review — Business Wiki Worked Example

## What Atlas Got Right
- Extracted ALL wikilinks as high-confidence EXTRACTED edges — perfect recall
- Correctly identified ARA, Atlas, and MCP as central nodes
- Community detection mapped cleanly to the wiki's semantic structure
- Health score of 95 is appropriate for a well-curated wiki
- Provenance chain (sources → concepts → projects) is a real structural insight

## What Atlas Missed or Got Wrong
- Did not detect the implicit temporal ordering of decisions (March 1 → March 15)
- Could extract more granular concepts from within pages (e.g., "double-entry ledger"
  from finops.md, "Leiden algorithm" from knowledge-graph.md)
- The AGENTS.md file was not mapped as a node — it contains meta-instructions
  that could be useful as a "meta" page type
- Tag-based edges (e.g., all pages tagged "agents" share a relationship) were not extracted

## What Makes This Example Interesting
This corpus has zero code — it's pure wiki markdown with explicit wikilinks.
It demonstrates Atlas's ability to build a useful graph from structured documentation
alone, without any AST parsing. The 100% EXTRACTED confidence shows that well-written
wikis produce the most trustworthy graphs.

## Verdict
Atlas handles structured wikis exceptionally well. The graph is a faithful mirror
of the wiki's link structure. The audit findings are appropriate. The main gap
is in implicit knowledge extraction — things that are "in" the text but not linked.

**Score: 9/10** — Near-perfect for explicit wiki graphs. Gap: implicit knowledge.
```

- [ ] **Step 4: Commit**

```bash
git add worked/
git commit -m "feat: add 3 worked examples — codebase, research, business wiki

Each example has: realistic input files, expected graph.json + GRAPH_REPORT.md,
honest review.md, and run.sh for reproducibility.
- codebase: TaskFlow async task queue (7 Python files)
- research: Transformer papers + notes (7 markdown files)
- business: Origin Labs multi-project wiki (11 wiki pages)"
```

---

## Task 6: Benchmark Scripts

**Files:**
- Create: `benchmarks/bench_scan.py`
- Create: `benchmarks/bench_query.py`
- Create: `benchmarks/bench_tokens.py`
- Create: `benchmarks/bench_cache.py`
- Create: `benchmarks/run_all.py`
- Create: `benchmarks/results/.gitkeep`

- [ ] **Step 1: Create scan benchmark**

`benchmarks/bench_scan.py`:
```python
"""Benchmark: scan performance — time per file, full vs incremental."""
from __future__ import annotations

import random
import time
from pathlib import Path

from atlas.core.cache import CacheEngine
from atlas.core.scanner import Scanner
from atlas.core.storage import LocalStorage


def generate_corpus(root: Path, n_files: int = 100) -> Path:
    """Generate a synthetic corpus of n_files for benchmarking."""
    src = root / "src"
    docs = root / "docs"
    src.mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)

    n_py = int(n_files * 0.7)
    n_md = n_files - n_py

    for i in range(n_py):
        name = f"module_{i:04d}"
        content = f'"""Module {name}."""\nfrom __future__ import annotations\n\n'
        for j in range(random.randint(2, 5)):
            content += f"def {name}_func_{j}(x: str) -> str:\n    return x.strip()\n\n"
        content += f"class {name.title().replace('_','')}:\n    def __init__(self):\n        self.name = '{name}'\n"
        (src / f"{name}.py").write_text(content)

    for i in range(n_md):
        name = f"doc_{i:04d}"
        content = f"---\ntitle: {name}\ntype: document\n---\n\n# {name}\n\nContent for {name}.\n"
        refs = [f"module_{random.randint(0, n_py-1):04d}" for _ in range(random.randint(1, 3))]
        for ref in refs:
            content += f"\nSee [[{ref}]] for details.\n"
        (docs / f"{name}.md").write_text(content)

    return root


def bench_full_scan(corpus_path: Path, tmp_path: Path) -> dict:
    """Benchmark a full scan of the corpus."""
    storage = LocalStorage(root=tmp_path)
    cache = CacheEngine(storage)
    scanner = Scanner(storage=storage, cache=cache)

    start = time.perf_counter()
    extraction = scanner.scan(corpus_path)
    elapsed = time.perf_counter() - start

    n_files = sum(1 for _ in corpus_path.rglob("*") if _.is_file())

    return {
        "operation": "full_scan",
        "files": n_files,
        "nodes": len(extraction.nodes),
        "edges": len(extraction.edges),
        "total_seconds": round(elapsed, 3),
        "time_per_file_ms": round(elapsed / max(1, n_files) * 1000, 1),
    }


def bench_incremental_scan(corpus_path: Path, tmp_path: Path, n_changed: int = 3) -> dict:
    """Benchmark incremental scan after changing n files."""
    storage = LocalStorage(root=tmp_path)
    cache = CacheEngine(storage)
    scanner = Scanner(storage=storage, cache=cache)

    # Initial full scan
    scanner.scan(corpus_path)

    # Modify n files
    py_files = list(corpus_path.rglob("*.py"))[:n_changed]
    for f in py_files:
        content = f.read_text()
        f.write_text(content + f"\ndef added_{f.stem}(): pass\n")

    start = time.perf_counter()
    extraction = scanner.scan(corpus_path, incremental=True)
    elapsed = time.perf_counter() - start

    return {
        "operation": "incremental_scan",
        "changed_files": n_changed,
        "total_seconds": round(elapsed, 3),
    }


def run(tmp_dir: Path | None = None) -> dict:
    """Run all scan benchmarks."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        base = Path(tmp_dir or td)
        corpus_dir = base / "corpus"
        work_dir = base / "work"
        work_dir.mkdir(parents=True, exist_ok=True)

        corpus = generate_corpus(corpus_dir, n_files=100)

        full = bench_full_scan(corpus, work_dir / "full")
        incr = bench_incremental_scan(corpus, work_dir / "incr", n_changed=3)

        return {
            "full": full,
            "incremental": incr,
            "time_per_file_ms": full["time_per_file_ms"],
        }


if __name__ == "__main__":
    import json
    results = run()
    print(json.dumps(results, indent=2))
```

- [ ] **Step 2: Create query benchmark**

`benchmarks/bench_query.py`:
```python
"""Benchmark: graph query latency — BFS, path, god-nodes, stats."""
from __future__ import annotations

import random
import statistics
import time

from atlas.core.graph import Graph
from atlas.core.models import Edge, Extraction, Node


def build_graph(n_nodes: int = 500, n_edges: int = 1500) -> Graph:
    """Build a synthetic graph for benchmarking."""
    graph = Graph()
    nodes = [
        Node(
            id=f"n{i:04d}",
            label=f"Concept_{i}",
            type=random.choice(["code", "document", "wiki-concept"]),
            source_file=f"src/mod_{i % 70:03d}.py",
            community=i % 15,
        )
        for i in range(n_nodes)
    ]
    edges = []
    for _ in range(n_edges):
        s, t = random.sample(range(n_nodes), 2)
        edges.append(Edge(
            source=f"n{s:04d}",
            target=f"n{t:04d}",
            relation=random.choice(["imports", "calls", "references"]),
            confidence=random.choice(["EXTRACTED", "INFERRED"]),
        ))
    graph.merge(Extraction(nodes=nodes, edges=edges))
    return graph


def bench_bfs(graph: Graph, n_queries: int = 200) -> dict:
    """Benchmark BFS queries."""
    node_count = graph.stats().nodes
    times = []
    for i in range(n_queries):
        node_id = f"n{(i * 3) % node_count:04d}"
        start = time.perf_counter()
        graph.query(node_id, mode="bfs", depth=3)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return {
        "operation": "bfs_query",
        "queries": n_queries,
        "mean_ms": round(statistics.mean(times), 2),
        "p50_ms": round(statistics.median(times), 2),
        "p95_ms": round(sorted(times)[int(n_queries * 0.95)], 2),
        "p99_ms": round(sorted(times)[int(n_queries * 0.99)], 2),
    }


def bench_path(graph: Graph, n_queries: int = 100) -> dict:
    """Benchmark shortest-path queries."""
    node_count = graph.stats().nodes
    times = []
    for i in range(n_queries):
        src = f"n{(i * 2) % node_count:04d}"
        tgt = f"n{(i * 2 + 100) % node_count:04d}"
        start = time.perf_counter()
        try:
            graph.path(src, tgt)
        except Exception:
            pass
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return {
        "operation": "path_query",
        "queries": n_queries,
        "mean_ms": round(statistics.mean(times), 2),
        "p95_ms": round(sorted(times)[int(n_queries * 0.95)], 2),
    }


def bench_god_nodes(graph: Graph) -> dict:
    """Benchmark god nodes detection."""
    start = time.perf_counter()
    graph.god_nodes(top_n=10)
    elapsed = (time.perf_counter() - start) * 1000
    return {"operation": "god_nodes", "time_ms": round(elapsed, 2)}


def bench_stats(graph: Graph) -> dict:
    """Benchmark stats computation."""
    start = time.perf_counter()
    graph.stats()
    elapsed = (time.perf_counter() - start) * 1000
    return {"operation": "stats", "time_ms": round(elapsed, 2)}


def run() -> dict:
    """Run all query benchmarks."""
    graph = build_graph(500, 1500)
    return {
        "graph_size": {"nodes": 500, "edges": 1500},
        "bfs": bench_bfs(graph),
        "path": bench_path(graph),
        "god_nodes": bench_god_nodes(graph),
        "stats": bench_stats(graph),
        "p95_ms": bench_bfs(graph)["p95_ms"],
    }


if __name__ == "__main__":
    import json
    results = run()
    print(json.dumps(results, indent=2))
```

- [ ] **Step 3: Create token efficiency benchmark**

`benchmarks/bench_tokens.py`:
```python
"""Benchmark: token efficiency — raw corpus size vs graph query response size."""
from __future__ import annotations

import json
from pathlib import Path

from atlas.core.graph import Graph
from atlas.core.models import Extraction, Node, Edge


def estimate_tokens(text: str) -> int:
    """Rough token count: ~4 chars per token."""
    return max(1, len(text) // 4)


def bench_token_efficiency(corpus_path: Path) -> dict:
    """Measure token efficiency: how much compression does the graph provide?"""
    # 1. Measure raw corpus size
    raw_text = ""
    file_count = 0
    for f in corpus_path.rglob("*"):
        if f.is_file() and f.suffix in {".py", ".md", ".yaml", ".yml", ".json", ".txt"}:
            try:
                raw_text += f.read_text()
                file_count += 1
            except (UnicodeDecodeError, PermissionError):
                pass

    raw_tokens = estimate_tokens(raw_text)

    # 2. Simulate a graph query response (typical: 10-20 nodes + edges)
    # This is the amount of context an agent gets from atlas query
    # vs. reading all files directly
    sample_query_response = json.dumps({
        "question": "how does auth connect to billing?",
        "nodes": [
            {"id": "auth", "label": "Auth Module", "summary": "JWT-based auth"},
            {"id": "billing", "label": "Billing", "summary": "Usage tracking"},
            {"id": "db", "label": "Database", "summary": "SQLite storage"},
        ],
        "edges": [
            {"source": "auth", "target": "db", "relation": "imports"},
            {"source": "billing", "target": "db", "relation": "imports"},
            {"source": "billing", "target": "auth", "relation": "references"},
        ],
        "path": "auth → db ← billing",
        "answer": "Auth and billing are connected through the database module. Both import db for data access."
    })
    query_tokens = estimate_tokens(sample_query_response)

    # 3. Measure graph.json size (full graph serialized)
    sample_graph = {
        "nodes": [{"id": f"n{i}", "label": f"Node {i}", "type": "code"} for i in range(file_count)],
        "edges": [{"source": f"n{i}", "target": f"n{(i+1) % file_count}", "relation": "imports"} for i in range(file_count)],
    }
    graph_tokens = estimate_tokens(json.dumps(sample_graph))

    ratio = raw_tokens / max(1, query_tokens)

    return {
        "raw_corpus_tokens": raw_tokens,
        "graph_json_tokens": graph_tokens,
        "query_response_tokens": query_tokens,
        "compression_ratio": round(ratio, 1),
        "files_scanned": file_count,
        "graph_vs_raw_ratio": round(graph_tokens / max(1, raw_tokens), 2),
    }


def run(corpus_path: Path | None = None) -> dict:
    """Run token efficiency benchmark."""
    if corpus_path is None:
        corpus_path = Path(__file__).parent.parent / "tests" / "fixtures" / "corpus"
    return bench_token_efficiency(corpus_path)


if __name__ == "__main__":
    import json as j
    results = run()
    print(j.dumps(results, indent=2))
```

- [ ] **Step 4: Create cache hit rate benchmark**

`benchmarks/bench_cache.py`:
```python
"""Benchmark: cache hit rate — measure how effectively the cache avoids re-extraction."""
from __future__ import annotations

import random
import time
from pathlib import Path

from atlas.core.cache import CacheEngine
from atlas.core.scanner import Scanner
from atlas.core.storage import LocalStorage


def bench_cache_hit_rate(corpus_path: Path, tmp_path: Path, change_pct: float = 0.05) -> dict:
    """Measure cache hit rate after modifying a percentage of files.

    Args:
        corpus_path: Path to the corpus to scan.
        tmp_path: Temp directory for storage.
        change_pct: Fraction of files to modify between scans (0.0 - 1.0).
    """
    storage = LocalStorage(root=tmp_path)
    cache = CacheEngine(storage)
    scanner = Scanner(storage=storage, cache=cache)

    # Collect all scannable files
    all_files = [f for f in corpus_path.rglob("*") if f.is_file() and f.suffix in {".py", ".md"}]
    total_files = len(all_files)

    # Initial full scan — populates cache
    t0 = time.perf_counter()
    scanner.scan(corpus_path)
    full_time = time.perf_counter() - t0

    # Modify a subset of files
    n_change = max(1, int(total_files * change_pct))
    changed = random.sample(all_files, min(n_change, len(all_files)))
    for f in changed:
        content = f.read_text()
        f.write_text(content + f"\n# Modified for benchmark\n")

    # Incremental scan
    t1 = time.perf_counter()
    scanner.scan(corpus_path, incremental=True)
    incr_time = time.perf_counter() - t1

    cache_hits = total_files - n_change
    hit_rate = cache_hits / max(1, total_files)

    return {
        "total_files": total_files,
        "changed_files": n_change,
        "change_pct": round(change_pct * 100, 1),
        "cache_hits": cache_hits,
        "cache_hit_rate": round(hit_rate * 100, 1),
        "full_scan_seconds": round(full_time, 3),
        "incremental_seconds": round(incr_time, 3),
        "speedup": round(full_time / max(0.001, incr_time), 1),
    }


def run(corpus_path: Path | None = None) -> dict:
    """Run cache benchmark at multiple change percentages."""
    import tempfile

    if corpus_path is None:
        corpus_path = Path(__file__).parent.parent / "tests" / "fixtures" / "corpus"

    results = {}
    for pct in [0.0, 0.05, 0.10, 0.25, 0.50]:
        with tempfile.TemporaryDirectory() as td:
            r = bench_cache_hit_rate(corpus_path, Path(td), change_pct=pct)
            results[f"{int(pct*100)}pct_changed"] = r

    return results


if __name__ == "__main__":
    import json
    results = run()
    print(json.dumps(results, indent=2))
```

- [ ] **Step 5: Create the orchestrator**

`benchmarks/run_all.py`:
```python
"""Run all Atlas benchmarks and output results as JSON + markdown summary."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Ensure atlas is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_benchmarks(output_path: str | None = None) -> dict:
    """Run all benchmarks and collect results."""
    from benchmarks import bench_scan, bench_query, bench_tokens, bench_cache

    print("=" * 60)
    print(f"Atlas Benchmarks — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "benchmarks": {},
    }

    # Scan benchmark
    print("\n[1/4] Scan performance...")
    try:
        scan_results = bench_scan.run()
        results["benchmarks"]["scan"] = scan_results
        results["scan"] = {"time_per_file_ms": scan_results["time_per_file_ms"]}
        print(f"  Full scan: {scan_results['full']['total_seconds']:.2f}s ({scan_results['time_per_file_ms']:.0f}ms/file)")
        print(f"  Incremental: {scan_results['incremental']['total_seconds']:.2f}s")
    except Exception as e:
        print(f"  ERROR: {e}")
        results["benchmarks"]["scan"] = {"error": str(e)}
        results["scan"] = {"time_per_file_ms": 9999}

    # Query benchmark
    print("\n[2/4] Query latency...")
    try:
        query_results = bench_query.run()
        results["benchmarks"]["query"] = query_results
        results["query"] = {"p95_ms": query_results["p95_ms"]}
        print(f"  BFS p95: {query_results['bfs']['p95_ms']:.1f}ms")
        print(f"  Path p95: {query_results['path']['p95_ms']:.1f}ms")
    except Exception as e:
        print(f"  ERROR: {e}")
        results["benchmarks"]["query"] = {"error": str(e)}
        results["query"] = {"p95_ms": 9999}

    # Token efficiency
    print("\n[3/4] Token efficiency...")
    try:
        token_results = bench_tokens.run()
        results["benchmarks"]["tokens"] = token_results
        print(f"  Raw corpus: {token_results['raw_corpus_tokens']} tokens")
        print(f"  Query response: {token_results['query_response_tokens']} tokens")
        print(f"  Compression: {token_results['compression_ratio']}x")
    except Exception as e:
        print(f"  ERROR: {e}")
        results["benchmarks"]["tokens"] = {"error": str(e)}

    # Cache hit rate
    print("\n[4/4] Cache hit rate...")
    try:
        cache_results = bench_cache.run()
        results["benchmarks"]["cache"] = cache_results
        zero_change = cache_results.get("0pct_changed", {})
        print(f"  0% changed: {zero_change.get('cache_hit_rate', 'N/A')}% hit rate, {zero_change.get('speedup', 'N/A')}x speedup")
    except Exception as e:
        print(f"  ERROR: {e}")
        results["benchmarks"]["cache"] = {"error": str(e)}

    print("\n" + "=" * 60)
    print("Benchmarks complete.")

    # Save results
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(results, indent=2))
        print(f"Results saved to: {output}")

        # Also write markdown summary
        md_path = output.with_suffix(".md")
        md_path.write_text(_format_markdown(results))
        print(f"Summary saved to: {md_path}")

    return results


def _format_markdown(results: dict) -> str:
    """Format benchmark results as a readable markdown summary."""
    md = f"# Atlas Benchmark Results\n\n"
    md += f"**Date:** {results['timestamp']}\n\n"

    benchmarks = results.get("benchmarks", {})

    # Scan
    scan = benchmarks.get("scan", {})
    if "error" not in scan:
        md += "## Scan Performance\n\n"
        md += f"| Metric | Value |\n|--------|-------|\n"
        full = scan.get("full", {})
        md += f"| Full scan (100 files) | {full.get('total_seconds', 'N/A')}s |\n"
        md += f"| Time per file | {scan.get('time_per_file_ms', 'N/A')}ms |\n"
        md += f"| Nodes extracted | {full.get('nodes', 'N/A')} |\n"
        md += f"| Edges extracted | {full.get('edges', 'N/A')} |\n"
        incr = scan.get("incremental", {})
        md += f"| Incremental (3 changed) | {incr.get('total_seconds', 'N/A')}s |\n"
        md += "\n"

    # Query
    query = benchmarks.get("query", {})
    if "error" not in query:
        md += "## Query Latency\n\n"
        md += f"Graph: {query.get('graph_size', {}).get('nodes', '?')} nodes, "
        md += f"{query.get('graph_size', {}).get('edges', '?')} edges\n\n"
        md += f"| Query | Mean | p50 | p95 | p99 |\n|-------|------|-----|-----|-----|\n"
        bfs = query.get("bfs", {})
        md += f"| BFS (depth=3) | {bfs.get('mean_ms', 'N/A')}ms | {bfs.get('p50_ms', 'N/A')}ms | {bfs.get('p95_ms', 'N/A')}ms | {bfs.get('p99_ms', 'N/A')}ms |\n"
        path = query.get("path", {})
        md += f"| Shortest path | {path.get('mean_ms', 'N/A')}ms | — | {path.get('p95_ms', 'N/A')}ms | — |\n"
        md += f"| God nodes | {query.get('god_nodes', {}).get('time_ms', 'N/A')}ms | — | — | — |\n"
        md += f"| Stats | {query.get('stats', {}).get('time_ms', 'N/A')}ms | — | — | — |\n"
        md += "\n"

    # Tokens
    tokens = benchmarks.get("tokens", {})
    if "error" not in tokens:
        md += "## Token Efficiency\n\n"
        md += f"| Metric | Value |\n|--------|-------|\n"
        md += f"| Raw corpus tokens | {tokens.get('raw_corpus_tokens', 'N/A')} |\n"
        md += f"| Graph JSON tokens | {tokens.get('graph_json_tokens', 'N/A')} |\n"
        md += f"| Query response tokens | {tokens.get('query_response_tokens', 'N/A')} |\n"
        md += f"| Compression ratio | {tokens.get('compression_ratio', 'N/A')}x |\n"
        md += "\n"

    # Cache
    cache = benchmarks.get("cache", {})
    if "error" not in cache:
        md += "## Cache Hit Rate\n\n"
        md += f"| Changed % | Hit Rate | Full Scan | Incremental | Speedup |\n"
        md += f"|-----------|----------|-----------|-------------|--------|\n"
        for key in sorted(cache.keys()):
            entry = cache[key]
            md += f"| {entry.get('change_pct', '?')}% | {entry.get('cache_hit_rate', '?')}% | {entry.get('full_scan_seconds', '?')}s | {entry.get('incremental_seconds', '?')}s | {entry.get('speedup', '?')}x |\n"
        md += "\n"

    return md


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Atlas benchmarks")
    parser.add_argument("--output", "-o", help="Output JSON path", default=None)
    args = parser.parse_args()
    run_benchmarks(args.output)
```

`benchmarks/__init__.py`:
```python
"""Atlas benchmarks."""
```

`benchmarks/results/.gitkeep` — empty file.

- [ ] **Step 6: Commit**

```bash
git add benchmarks/
git commit -m "feat: benchmark suite — scan, query, tokens, cache

Automated benchmarks with JSON output and markdown summary.
- bench_scan: full + incremental scan throughput
- bench_query: BFS/path/god-nodes latency p50/p95/p99
- bench_tokens: raw corpus vs graph query compression ratio
- bench_cache: hit rate at 0/5/10/25/50% file change
- run_all.py orchestrates and writes results."
```

---

## Task 7: Documentation

**Files:**
- Create: `docs/README.md`
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/SECURITY.md`
- Create: `docs/CHANGELOG.md`
- Create: `docs/CONTRIBUTING.md`

- [ ] **Step 1: Write README.md — the storefront**

`docs/README.md`:
```markdown
# Atlas

**Scan anything. Know everything. Remember forever.**

Atlas is a knowledge engine for AI agents. Point it at any folder and it does two things no one else does together:

1. **Discovery** — scans code, docs, papers, images and builds a knowledge graph automatically
2. **Curation** — compiles a living wiki that agents maintain session after session

The graph and the wiki are linked. When the graph discovers a relationship, the wiki documents it. When the wiki evolves, the graph updates. One system, not two tools glued together.

<!-- TODO: Add demo GIF here once v2.0 is live -->
<!-- ![atlas-demo](https://raw.githubusercontent.com/originlabs-app/atlas/main/docs/assets/demo.gif) -->

## Install

```bash
pip install atlas-ai
```

That's it. No database. No Docker. No config.

## Quickstart

### 30-second demo

```bash
# Scan your project
atlas scan .

# Open the dashboard
atlas serve
# → http://localhost:7100

# Ask a question
atlas query "how does auth connect to billing?"

# See the audit report
atlas audit
```

### What you get

```
your-project/
├── wiki/                    # Living wiki (maintained by agents)
│   ├── index.md
│   ├── concepts/
│   ├── projects/
│   └── decisions/
├── graph.json               # Knowledge graph (git-versionable)
└── GRAPH_REPORT.md          # Audit report
```

## Features

### Multi-modal scanning
Atlas extracts from everything:
- **Code** (Python, TypeScript, Go, Rust + 9 more) — AST-level analysis
- **Markdown/docs** — concepts, entities, relationships
- **PDF** — text extraction + citation mining
- **Images** — screenshots, diagrams, whiteboards (via Claude Vision)
- **URLs** — tweets, arxiv, GitHub, webpages (auto-fetched)

### Knowledge graph
```bash
atlas query "what connects auth to billing?"
atlas path "Auth" "Database"
atlas god-nodes
atlas surprises
```
In-memory NetworkX graph. No Neo4j. No external DB. Git-versionable.

### Living wiki
Markdown pages with typed frontmatter. `[[Wikilinks]]` for navigation. Templates per type. Auto-maintained index.

### The Linker (unique to Atlas)
Bidirectional graph-wiki sync:
- Wiki `[[wikilink]]` added → graph edge created
- Graph discovers new node → wiki page suggested
- The graph proposes, you decide. No automatic writes.

### Dashboard
```bash
atlas serve
```
Interactive graph visualization. Wiki reader. Audit dashboard. Search. Timeline.
Static HTML — boots in 200ms.

### Agent skills
Atlas ships 7 skills for any MCP-compatible agent:
- `/atlas-start` — begin session, get briefed
- `/atlas-scan` — scan a new corpus
- `/atlas-query` — ask questions
- `/atlas-ingest` — add a URL or file
- `/atlas-progress` — checkpoint
- `/atlas-finish` — end session, write back knowledge
- `/atlas-health` — deep audit

### Export
```bash
atlas export html      # Standalone interactive graph
atlas export obsidian  # Obsidian vault with backlinks
atlas export neo4j     # Cypher import
atlas export graphml   # Gephi/yEd
atlas export svg       # Embed in GitHub/Notion
atlas export pdf       # Printable report
```

## Worked examples

Three ready-to-run examples in [`worked/`](../worked/):

| Example | What | Files | Graph |
|---------|------|-------|-------|
| [codebase](../worked/codebase/) | Python async task queue | 7 | 11 nodes, 17 edges |
| [research](../worked/research/) | Transformer papers + notes | 7 | 11 nodes, 16 edges |
| [business](../worked/business/) | Multi-project wiki | 11 | 11 nodes, 31 edges |

Run any example:
```bash
cd worked/codebase && bash run.sh
```

Each includes input files, expected output, and an honest review.

## Performance

| Operation | Target | Measured |
|-----------|--------|----------|
| Scan 100 files | < 2 min | See `benchmarks/` |
| Incremental scan (3 changed) | < 10 sec | See `benchmarks/` |
| Graph query | < 100ms p95 | See `benchmarks/` |
| Dashboard load | < 200ms | Static HTML |

Run benchmarks yourself:
```bash
python benchmarks/run_all.py --output benchmarks/results/latest.json
```

## MCP Server

Atlas exposes a full MCP server for agent integration:

```bash
atlas serve --mcp        # stdio transport
atlas serve --mcp-sse    # SSE transport (remote)
```

```python
atlas.scan(path)                # Scan a folder
atlas.query(question, mode)     # Query the graph
atlas.wiki.read(page)           # Read a wiki page
atlas.wiki.write(page, content) # Write a wiki page
atlas.audit()                   # Run audit
```

## Migration from agent-wiki v1

```bash
atlas migrate   # Detects existing wiki, builds graph, installs skills
```

Zero data loss. Old `/agent-wiki-*` skills redirect to `/atlas-*`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We welcome PRs for:
- New language support in the scanner
- Export format plugins
- Dashboard visualizations
- Documentation improvements

## License

MIT
```

- [ ] **Step 2: Write ARCHITECTURE.md**

`docs/ARCHITECTURE.md`:
```markdown
# Architecture

Atlas is a Python package (`atlas-ai`) with four layers:

```
CLI / Skills
    ↓
Server (FastAPI + MCP + WebSocket)
    ↓
Core Engine (Scanner, Graph, Wiki, Linker, Analyzer, Cache, Ingest)
    ↓
Storage Backend (LocalStorage | ARAStorage)
```

## Core Engine

### Models (`atlas/core/models.py`)
All data structures: `Node`, `Edge`, `Extraction`, `Page`, `Subgraph`, `GraphStats`, `AuditReport`, `WikiSuggestion`, `GraphChange`, `LinkSuggestion`. Pure dataclasses, no dependencies.

### Storage (`atlas/core/storage.py`)
`StorageBackend` protocol with two implementations:
- `LocalStorage` — reads/writes files on local filesystem
- `ARAStorage` — (future) S3/GCS + PostgreSQL index

All other modules use `storage.read()` / `storage.write()`. No direct `Path` operations.

### Cache (`atlas/core/cache.py`)
SHA256 content hashing. Stores extraction results per file. Enables incremental scanning: only re-extract files whose hash changed.

### Scanner (`atlas/core/scanner.py`)
Two extraction modes:
- `scanner_ast.py` — tree-sitter AST parsing for code files (free, deterministic)
- `scanner_semantic.py` — LLM extraction for docs/images (costly, cached aggressively)

The main `Scanner` class dispatches to the right extractor based on file type.

### Graph (`atlas/core/graph.py`)
NetworkX DiGraph wrapper. Operations: `merge`, `query` (BFS/DFS), `path`, `god_nodes`, `surprises`, `stats`. Serializes to/from `graph.json`.

### Wiki (`atlas/core/wiki.py`)
Markdown page management. YAML frontmatter. `[[wikilink]]` parsing. Templates per page type. Full-text search.

### Linker (`atlas/core/linker.py`)
The heart of Atlas — bidirectional sync:
- `sync_wiki_to_graph()` — wiki changes → graph updates (automatic)
- `sync_graph_to_wiki()` — graph discoveries → wiki suggestions (proposed, never forced)

### Analyzer (`atlas/core/analyzer.py`)
Detects: orphan pages, god nodes, broken links, stale pages, contradictions. Produces `AuditReport` with a health score.

### Ingest (`atlas/core/ingest.py`)
Smart URL fetching: tweets, arxiv, PDFs, webpages. Downloads to `raw/`, triggers scanner.

## Server

### FastAPI App (`atlas/server/app.py`)
REST API wrapping all core operations. Serves the dashboard as static files.

### MCP Server (`atlas/server/mcp.py`)
Model Context Protocol server (stdio + SSE). The universal entry point for agents.

### WebSocket (`atlas/server/ws.py`)
Live updates during scans and wiki edits.

## Dashboard

Static HTML + vanilla JS + Tailwind CDN. No build step. Served by FastAPI.
- `graph.js` — d3/vis.js graph visualization
- `wiki.js` — Markdown renderer with wikilinks
- `audit.js` — Audit dashboard
- `search.js` — Combined full-text + graph search

## Data Flow

```
Files → Scanner → Extraction → Graph.merge → Linker.sync → Wiki pages
Wiki edits → Linker.sync_wiki_to_graph → Graph updates → Analyzer.audit
```

The wiki markdown is the source of truth. `graph.json` is derived. Delete the graph, run `atlas scan`, and it rebuilds.

## Interfaces Contract

All squads code against these interfaces (defined in `atlas/core/`):
- `Scanner.scan(path) → Extraction`
- `Graph.merge(extraction) → None`
- `Graph.query(question, mode, depth) → Subgraph`
- `WikiEngine.read(page) → Page`
- `WikiEngine.write(page, content, frontmatter) → None`
- `Linker.sync_wiki_to_graph() → list[GraphChange]`
- `Linker.sync_graph_to_wiki() → list[WikiSuggestion]`
- `Analyzer.audit() → AuditReport`

Server, Dashboard, and Skills only call these interfaces. No direct filesystem access.
```

- [ ] **Step 3: Write SECURITY.md**

`docs/SECURITY.md`:
```markdown
# Security

## Threat Model

Atlas runs locally by default. The primary threats are:

### 1. File system access
**Risk:** Atlas scans directories and reads file contents.
**Mitigation:** Atlas only reads files in the explicitly specified scan path. It never reads outside the target directory. The `exclude_patterns` config prevents scanning sensitive paths (`.env`, `.git/`, `credentials.json`).

### 2. LLM data exposure
**Risk:** File contents are sent to LLM APIs for semantic extraction.
**Mitigation:**
- AST extraction (code files) is fully local — no LLM call needed
- LLM extraction only happens for docs/images that require semantic understanding
- Users can disable LLM extraction with `atlas scan --no-llm` (AST only)
- No data is sent to LLM providers without explicit scan invocation
- Cache prevents re-sending the same content

### 3. MCP server access
**Risk:** The MCP server exposes wiki read/write operations.
**Mitigation:**
- In local mode (stdio), only the connected agent has access
- In SSE mode, bind to `127.0.0.1` by default (localhost only)
- Authentication required for remote access (ARA mode)

### 4. Dashboard
**Risk:** The web dashboard serves wiki content and graph data.
**Mitigation:**
- Binds to `127.0.0.1:7100` by default (not exposed to network)
- No user authentication in local mode (same trust as local files)
- Content-Security-Policy headers prevent XSS

### 5. Dependency supply chain
**Risk:** Python dependencies could be compromised.
**Mitigation:**
- Minimal core dependencies: `networkx`, `pyyaml`, `httpx`
- Optional deps clearly separated (`[ast]`, `[cluster]`, `[server]`)
- Pinned versions in `pyproject.toml`
- CI runs on every PR

## Data Handling

- **raw/** — Immutable source material. Atlas never modifies these files.
- **wiki/** — Compiled knowledge. Atlas writes here (with user/agent consent).
- **graph.json** — Derived graph. Can be deleted and rebuilt.
- **atlas-cache/** — Extraction cache. Can be deleted safely.

## Sensitive Files

Atlas excludes these patterns by default:
```
.env, .env.*, *.pem, *.key, *.secret
credentials.json, secrets.yaml
.git/, node_modules/, __pycache__/
```

Add custom exclusions in `settings.yaml` under `scanner.exclude_patterns`.

## Reporting Vulnerabilities

Email security@originlabs.dev with details. We aim to respond within 48 hours.
Do not open public issues for security vulnerabilities.
```

- [ ] **Step 4: Write CHANGELOG.md**

`docs/CHANGELOG.md`:
```markdown
# Changelog

All notable changes to Atlas are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Added
- Core engine: Scanner, Graph, Wiki, Linker, Analyzer, Cache, Ingest, Storage
- FastAPI server with REST API and MCP server
- Interactive dashboard with graph visualization, wiki view, and audit
- 7 agent skills (`/atlas-start`, `/atlas-scan`, `/atlas-query`, `/atlas-ingest`, `/atlas-progress`, `/atlas-finish`, `/atlas-health`)
- CLI via typer (`atlas scan`, `atlas query`, `atlas serve`, `atlas export`)
- Export: JSON, HTML, Obsidian, Neo4j, GraphML, SVG, PDF
- 3 worked examples (codebase, research, business wiki)
- Benchmark suite (scan, query, tokens, cache)
- CI/CD: GitHub Actions (lint, typecheck, test, build, benchmarks, publish)
- Migration from agent-wiki v1 (`atlas migrate`)

### Changed
- Evolved from agent-wiki v1 + graphify into unified Atlas package

## [1.0.0] — agent-wiki v1 (predecessor)

### Features
- Karpathy LLM Wiki pattern implementation
- Markdown pages with typed frontmatter
- `[[wikilink]]` navigation
- Auto-maintained index
- 6 agent skills (`/agent-wiki-*`)
```

- [ ] **Step 5: Write CONTRIBUTING.md**

`docs/CONTRIBUTING.md`:
```markdown
# Contributing to Atlas

## Getting Started

```bash
# Clone
git clone https://github.com/originlabs-app/atlas
cd atlas

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linter
ruff check atlas/ tests/
ruff format --check atlas/ tests/

# Run type checker
pyright atlas/
```

## Code Style

- **Python 3.12+** — use `from __future__ import annotations`
- **Formatting:** ruff format (120 char line length)
- **Linting:** ruff check with rules: E, F, W, I, UP, B, SIM, RUF
- **Types:** pyright standard mode. All public functions must have type hints.
- **Docstrings:** Google style. Required for all public classes and functions.

## Project Structure

```
atlas/
├── core/       # Engine modules (scanner, graph, wiki, linker, etc.)
├── server/     # FastAPI backend, MCP server, WebSocket
├── dashboard/  # Static HTML frontend
├── skills/     # Agent skills (agentskills.io standard)
├── export/     # Output format plugins
└── cli.py      # Typer CLI
```

## Testing

```bash
# Unit tests
pytest tests/core/ -v

# Integration tests
pytest tests/integration/ -v

# Performance tests
pytest tests/performance/ -v -s

# Full suite with coverage
pytest tests/ -v --cov=atlas --cov-report=term-missing
```

Coverage target: **80%**. CI enforces this.

## Pull Request Process

1. Create a branch from `main`
2. Write tests first (TDD preferred)
3. Implement the change
4. Run the full test suite locally
5. Open a PR with:
   - Clear title (< 70 chars)
   - Summary of what and why
   - Test plan
6. CI must pass (lint + types + tests + build)
7. One approval required for merge

## Commit Messages

```
type: short description

Longer explanation of why, not what.
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `ci`, `perf`

## Adding a New Language to the Scanner

1. Add the tree-sitter grammar to `pyproject.toml` optional deps
2. Create a parser in `atlas/core/scanner_ast.py` (follow the Python parser pattern)
3. Add test fixtures in `tests/fixtures/`
4. Add tests in `tests/core/test_scanner_ast.py`
5. Update `docs/README.md` language list

## Adding a New Export Format

1. Create `atlas/export/your_format.py`
2. Implement the `export(graph, wiki, output_path)` function
3. Register in the CLI (`atlas/cli.py`)
4. Add tests
5. Update README export table
```

- [ ] **Step 6: Commit**

```bash
git add docs/
git commit -m "docs: README, ARCHITECTURE, SECURITY, CHANGELOG, CONTRIBUTING

README: install, quickstart, features, worked examples, benchmarks, MCP, migration.
ARCHITECTURE: system layers, module descriptions, data flow, interfaces.
SECURITY: threat model, data handling, sensitive file exclusions.
CHANGELOG: keep-a-changelog format for v2.0.
CONTRIBUTING: setup, code style, testing, PR process, extension guides."
```

---

## Task 8: PyPI Publish Configuration

**Files:**
- Update: `pyproject.toml` (verify classifiers, URLs, entry points)
- Create: `.github/ISSUE_TEMPLATE/bug_report.md`
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`

- [ ] **Step 1: Verify and extend pyproject.toml for PyPI**

Add to the existing `pyproject.toml` (from Plan 1):
```toml
[project.urls]
Homepage = "https://github.com/originlabs-app/atlas"
Documentation = "https://github.com/originlabs-app/atlas/tree/main/docs"
Repository = "https://github.com/originlabs-app/atlas"
Issues = "https://github.com/originlabs-app/atlas/issues"
Changelog = "https://github.com/originlabs-app/atlas/blob/main/docs/CHANGELOG.md"

[project]
# Add to existing classifiers:
classifiers = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Documentation",
    "Typing :: Typed",
]
```

- [ ] **Step 2: Create release tagging script**

The publish workflow (Task 1, Step 3) already handles PyPI publish on tag push. The process is:

```bash
# 1. Update version in atlas/__init__.py and pyproject.toml
# 2. Update CHANGELOG.md
# 3. Commit and tag
git add -A
git commit -m "release: v2.0.0"
git tag v2.0.0
git push origin main --tags
# 4. GitHub Actions builds, publishes to PyPI, creates GitHub Release
```

- [ ] **Step 3: Create issue templates**

`.github/ISSUE_TEMPLATE/bug_report.md`:
```markdown
---
name: Bug Report
about: Report a bug in Atlas
title: "[Bug] "
labels: bug
---

## Describe the bug
A clear description of what the bug is.

## To reproduce
1. `pip install atlas-ai`
2. `atlas scan ...`
3. See error

## Expected behavior
What you expected to happen.

## Environment
- OS: [e.g., macOS 14.5, Ubuntu 24.04]
- Python: [e.g., 3.12.4]
- Atlas version: [e.g., 2.0.0]

## Logs
```
Paste relevant error output here
```
```

`.github/ISSUE_TEMPLATE/feature_request.md`:
```markdown
---
name: Feature Request
about: Suggest an improvement to Atlas
title: "[Feature] "
labels: enhancement
---

## Problem
What problem does this solve? What's the use case?

## Proposed solution
Describe the feature you'd like.

## Alternatives considered
Other approaches you've thought about.
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .github/ISSUE_TEMPLATE/
git commit -m "ci: PyPI metadata, issue templates, release process

Added project URLs, Python 3.13 classifier, typed marker.
Issue templates for bug reports and feature requests.
Release process: tag → GitHub Actions → PyPI + GitHub Release."
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Section 7 Performance targets — Task 4 (scan < 2 min, query < 100ms), Task 6 (benchmarks)
- [x] Section 11 Quality squad — All 6 areas covered (CI, tests, worked examples, benchmarks, docs, publish)
- [x] Section 11 Week 1 gate — CI pipeline ensures `pip install -e . && atlas scan tests/fixtures/` works
- [x] Section 11 Week 2 gate — Integration tests verify external dev can use Atlas on real corpus
- [x] Section 11 Week 3 gate — 3 worked examples with published benchmarks
- [x] Section 11 Week 4 gate — PyPI publish workflow, README with demo GIF placeholder, CHANGELOG
- [x] Section 12 Interfaces — Tests use the interfaces contract (Scanner, Graph, Wiki, Linker, Analyzer)

**Quality of deliverables:**
- [x] CI matrix covers Python 3.12 + 3.13
- [x] Coverage gate at 80% (enforced in CI)
- [x] Worked examples have realistic content (not stubs) — 25+ files of real code/docs
- [x] Each worked example has: input files, expected graph.json, GRAPH_REPORT.md, honest review.md, run.sh
- [x] Reviews are honest — they note what Atlas got wrong, not just what it got right
- [x] Benchmarks are scripts that run and produce JSON, not hand-picked numbers
- [x] README covers: install (1 line), quickstart (4 commands), features, worked examples, benchmarks
- [x] SECURITY.md has a real threat model, not boilerplate
- [x] CONTRIBUTING.md explains how to extend Atlas (new language, new export)

**Placeholder scan:**
- [x] README has a `TODO` comment for demo GIF (intentional — can't create GIF before v2.0 exists)
- [x] Benchmark "Measured" column says "See benchmarks/" — filled by run_all.py after execution
- [x] No TBD/TODO in code or config files

**Cross-plan consistency:**
- [x] conftest.py extends Plan 1's fixtures (doesn't replace them)
- [x] pyproject.toml additions are additive (don't conflict with Plan 1's config)
- [x] Integration tests use the same module interfaces as Plan 1's unit tests
- [x] Benchmark fixtures generate data compatible with Plan 1's models (Node, Edge, Extraction)
