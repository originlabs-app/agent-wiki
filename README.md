# Agent Wiki

Karpathy-style knowledge base starter pack for multiple agents.

## Core idea

- `raw/` stores immutable source material.
- `wiki/` stores the compiled knowledge base written by agents.
- `AGENTS.md` is the canonical contract.
- `wikictl` is the single local command for init, log, lint, and status.
- `.claude/settings.json` provides the project-level Claude hooks.

## Supported agents

- Claude
- Codex
- Cursor
- Hermès

Each agent gets a thin adapter only. The workflow stays the same everywhere.

## Quick start

```bash
./install.sh
./scripts/bootstrap-local.sh
./cli/wikictl status
./cli/wikictl heal
```

If you want the local tool links in one step:

```bash
./install.sh --bootstrap
```

Or with `make`:

```bash
make init
make bootstrap
make status
make heal
```

Open the repo in your agent of choice and let it read `AGENTS.md` first.

For the exact config map by tool, read [docs/tool-configs.md](docs/tool-configs.md).
No global config overwrite is required for the project to work inside this repo.

If you want MCP, install the Node dependency and run the transport:

```bash
npm install
npm run mcp
```

## Layout

```text
agent-wiki/
├── AGENTS.md
├── CLAUDE.md
├── .claude/settings.json
├── README.md
├── install.sh
├── scripts/bootstrap-local.sh
├── cli/wikictl
├── package.json
├── contract/manifest.yaml
├── raw/
├── wiki/
├── mcp/
├── adapters/
├── skills/
├── docs/
└── .cursor/
```

## Rules

1. Read `wiki/index.md` first.
2. Treat `raw/` as immutable.
3. Compile knowledge into `wiki/`.
4. Append every meaningful operation to `wiki/log.md`.
5. Keep adapter files thin. Put the real contract in `AGENTS.md`.

## Common commands

- `./cli/wikictl ingest "<project>" <source...>` registers source files with a project page.
- `./cli/wikictl query <terms...>` searches the wiki and raw sources.
- `./cli/wikictl heal` rebuilds `wiki/index.md` from project pages.
- `./cli/wikictl sync <agent> <op> <description...>` logs an operation and checks the repo.
