# Atlas — Knowledge Engine for AI Agents

[![CI](https://github.com/originlabs-app/atlas/actions/workflows/ci.yml/badge.svg)](https://github.com/originlabs-app/atlas/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/atlas-ai.svg)](https://pypi.org/project/atlas-ai/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Scan anything. Know everything. Remember forever.**

Atlas transforms your codebase, documents, and research into a persistent knowledge graph. AI agents query it for context instead of re-reading thousands of files every session.

## What It Does

```bash
# Point it at any repo
atlas scan ./my-project

# Ask questions
atlas query "how does auth connect to billing?"
atlas path "UserModel" "PaymentGateway"
atlas explain "RateLimiter"

# See what's weird
atlas god-nodes        # Most connected concepts
atlas surprises        # Unexpected cross-boundary connections
atlas audit            # Health score, contradictions, stale pages
```

## Quick Start

```bash
pip install atlas-ai

# Scan your project
atlas scan ./your-repo

# That's it. The knowledge graph is at ./your-repo/atlas-out/graph.json.
```

## Core Features

| Feature | What it does |
|---------|-------------|
| **Scan** | Extract a knowledge graph from code, docs, and images |
| **Query** | Traverse the graph from any concept (BFS/DFS) |
| **Path** | Find connections between two concepts |
| **Explain** | Get a concept's type, summary, and neighbors |
| **God Nodes** | Find the most connected ideas in your codebase |
| **Surprises** | Discover unexpected cross-boundary relationships |
| **Audit** | Health score, orphans, contradictions, staleness |
| **Ingest** | Add URLs, files, or pasted text to the knowledge base |
| **Migrate** | Zero-loss migration from agent-wiki v1 |
| **Serve** | REST API + WebSocket + Dashboard with `atlas serve` |

## How It Works

```
Code/Docs/Images → Scanner (AST + Semantic) → Extraction
       ↓
   GraphEngine (NetworkX) ←→ Linker ←→ Wiki (Markdown)
       ↓
   Analyzer (communities, god nodes, surprises, contradictions)
```

1. **Scan** extracts structure via tree-sitter (code) and semantic analysis (docs)
2. **Graph** builds and merges NetworkX graphs with confidence scoring
3. **Wiki** syncs bidirectionally — wiki pages update the graph, graph suggests wiki improvements
4. **Query** traverses the graph (BFS/DFS, pathfinding, community detection)
5. **Audit** scores health, finds orphans, contradictions, and stale content

## Why Atlas?

| Problem | Before Atlas | After Atlas |
|---------|-------------|-------------|
| "How does auth connect to billing?" | Read 50 files, grep everywhere | `atlas path auth billing` |
| Onboarding a new dev | 2 weeks of reading | `atlas scan .` → `atlas god-nodes` |
| "What changed?" | Diff every file | `atlas scan --update .` → diff the graph |
| Knowledge in chat | Lost when session ends | Persisted in wiki/ directory, compounds |
| Contradictions | Nobody notices for months | `atlas audit` flags them |

## Installation

```bash
# Minimal (scan, query, wiki, audit)
pip install atlas-ai

# With AST parsing (tree-sitter)
pip install "atlas-ai[ast]"

# With server and dashboard
pip install "atlas-ai[server]"

# Everything
pip install "atlas-ai[all]"
```

## For AI Agents

Atlas installs as skills for Claude Code, Codex CLI, Cursor, and Hermes:

```python
from atlas.install import install
report = install()
print(report["platforms"])  # ["claude", "codex", "hermes"]
```

## Developer Setup

```bash
git clone https://github.com/originlabs-app/atlas.git
cd atlas
uv sync --all-extras

# Run tests
uv run pytest -v

# Lint + format
uv run ruff check atlas/ tests/
uv run ruff format atlas/ tests/

# Type check
uv run pyright atlas/
```

## Architecture

```
atlas/
├── core/          # Engine — models, storage, scanner, graph, wiki, linker, analyzer, ingest
├── server/        # FastAPI REST + WebSocket + Dashboard
├── skills/        # Agent skill files (agentskills.io format)
├── cli.py         # Typer CLI
├── install.py     # Multi-platform installer
└── migrate.py     # agent-wiki v1 → Atlas v2 migration

tests/             # 265+ tests
├── core/          # Unit tests per module
├── server/        # API contract + integration tests
├── fixtures/corpus/  # 15 realistic files for testing
└── test_cli_integration.py  # E2E workflow tests

benchmarks/        # Reproducible performance benchmarks
.github/workflows/ # CI (lint, test, typecheck, build, benchmarks, publish)
```

## Command Reference

| Command | Description |
|---------|-------------|
| `atlas scan <path>` | Scan a directory, extract knowledge graph |
| `atlas scan <path> --update` | Incremental scan (only changed files) |
| `atlas query <concept>` | Graph traversal from a concept |
| `atlas path <A> <B>` | Shortest path between two concepts |
| `atlas explain <concept>` | Single concept details + neighbors |
| `atlas god-nodes` | Most connected nodes |
| `atlas surprises` | Most surprising cross-community edges |
| `atlas audit` | Full health audit |
| `atlas stats` | Graph statistics |
| `atlas ingest <url|file>` | Add a source to the knowledge base |
| `atlas export json` | Export graph to JSON |
| `atlas migrate` | Migrate from agent-wiki v1 |
| `atlas serve` | Start REST API + WebSocket + Dashboard |
| `atlas hook install` | Install git hooks for auto-rebuild |

## Performance

Benchmarks run weekly on CI. Current thresholds:

| Operation | Threshold | Target |
|-----------|-----------|--------|
| Scan | < 1200ms/file | < 800ms/file |
| Graph merge | < 100ms/1K nodes | < 50ms/1K nodes |
| Query (p95) | < 100ms | < 50ms |
| Wiki sync | < 50ms/page | < 20ms/page |

Run benchmarks locally: `python benchmarks/run_all.py`

## License

MIT — see [LICENSE](LICENSE) for details.

## Contributing

1. Fork and create a branch from `main`
2. Write failing tests first (TDD)
3. Implement, pass tests, lint, typecheck
4. Open a PR with a clear description

All PRs require: CI green, reviewer approval, no coverage regression below 80%.
