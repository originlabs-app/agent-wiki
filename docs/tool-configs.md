# Tool Config Map

This repo is intentionally simple: the same contract is reused across tools,
with thin adapters where needed.

`agent-wiki` supports two storage modes:

- Starter mode: `wikictl` uses the local `wiki/` and `raw/` in this repo.
- Attach mode: `wikictl --instance <name>` or `wikictl --config <path>` points at an external vault.

## Claude

- Root contract: `CLAUDE.md`
- Project hooks: `.claude/settings.json`
- End-of-session write-back: `./cli/wikictl sync`
- Health check: `./cli/wikictl heal`
- Source registration: `./cli/wikictl ingest`
- Search: `./cli/wikictl query`

Claude Code reads the project `CLAUDE.md` and project settings file when you
open the repo. For an attached vault, call `wikictl --instance <name> ...` in
hooks or prompts.

## Codex

- Root contract: `AGENTS.md`
- Repo workflow helper: `./cli/wikictl`
- End-of-session write-back: `./cli/wikictl sync`
- Health check: `./cli/wikictl heal`
- Source registration: `./cli/wikictl ingest`
- Search: `./cli/wikictl query`

Codex uses `AGENTS.md` as the project instruction surface in this pack.
For an attached vault, use `wikictl --instance <name> ...` or `--config`.

## Cursor

- Root contract fallback: `AGENTS.md`
- Project rules: `.cursor/rules/agent-wiki.mdc`
- End-of-session write-back: `./cli/wikictl sync`
- Health check: `./cli/wikictl heal`
- Source registration: `./cli/wikictl ingest`
- Search: `./cli/wikictl query`

Cursor understands project rules in `.cursor/rules` and also supports
`AGENTS.md` as a simpler alternative.

## Hermès

- Adapter: `adapters/hermes/SKILL.md`
- End-of-session write-back: `./cli/wikictl sync`
- Health check: `./cli/wikictl heal`
- Source registration: `./cli/wikictl ingest`
- Search: `./cli/wikictl query`

Hermès uses the shared contract plus the skill wrapper.

## MCP

The MCP server follows the same mode split:

- `npm run mcp`
- `npm run mcp -- --instance origin-labs`
- `npm run mcp -- --config ~/.agent-wiki/instances/origin-labs.conf`
