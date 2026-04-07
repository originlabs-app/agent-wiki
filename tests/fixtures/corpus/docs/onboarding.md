# Onboarding — Atlas Core

Welcome to the Atlas development team. This guide gets you from zero to contributing in under 30 minutes.

## Setup

```bash
# Clone and install
git clone https://github.com/originlabs-app/atlas.git
cd atlas
uv sync --all-extras  # installs all optional deps

# Run tests
uv run pytest -v

# Install git hooks for auto-graph-rebuild
atlas hook install
```

## Project Structure

```
atlas/
├── core/          # Core engine — models, scanner, graph, wiki, linker, analyzer
├── server/        # FastAPI REST + WebSocket server
├── dashboard/     # Static SPA served at /
├── skills/        # Agent skill files (agentskills.io format)
├── cli.py         # Typer CLI — the user-facing interface
├── install.py     # Multi-platform installer (Claude, Codex, Cursor, Hermes)
└── migrate.py     # agent-wiki v1 → Atlas v2 migration
```

## Key Concepts

- **Node**: A concept in the knowledge graph (code entity, document, wiki page)
- **Edge**: A relationship between nodes (imports, calls, references)
- **Extraction**: The output of scanning a file — nodes + edges
- **Subgraph**: A subset of the graph returned by a query
- **Community**: A cluster of related nodes (via Leiden algorithm)

## Daily Workflow

1. Pick an issue from GitHub
2. Write a failing test first (TDD)
3. Implement and pass the test
4. Run full test suite: `uv run pytest`
5. Lint: `uv run ruff check --fix .`
6. Commit with conventional message
7. Open PR
