# Usage

## Local install

```bash
./install.sh
./scripts/bootstrap-local.sh
```

If you want a quick health refresh:

```bash
./cli/wikictl heal
```

## Session flow

1. Open the repo in the agent you want.
2. Read the tool-specific adapter or the root `AGENTS.md`.
3. Work against `wiki/` and `raw/`.
4. End the session with `./cli/wikictl sync`.

## Core commands

- `./cli/wikictl ingest "<project>" <source...>`
- `./cli/wikictl query <terms...>`
- `./cli/wikictl heal`
- `./cli/wikictl lint`

## MCP

If you want the MCP transport, install dependencies and run:

```bash
npm install
npm run mcp
```

The MCP server exposes the same operations as the CLI, but over the tool
transport.
