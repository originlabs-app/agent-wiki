# Tool Config Map

This repo is intentionally simple: the same contract is reused across tools,
with thin adapters where needed.

## Claude

- Root contract: `CLAUDE.md`
- Project hooks: `.claude/settings.json`
- End-of-session write-back: `./cli/wikictl sync`
- Health check: `./cli/wikictl heal`
- Source registration: `./cli/wikictl ingest`
- Search: `./cli/wikictl query`

Claude Code reads the project `CLAUDE.md` and project settings file when you
open the repo.

## Codex

- Root contract: `AGENTS.md`
- Repo workflow helper: `./cli/wikictl`
- End-of-session write-back: `./cli/wikictl sync`
- Health check: `./cli/wikictl heal`
- Source registration: `./cli/wikictl ingest`
- Search: `./cli/wikictl query`

Codex uses `AGENTS.md` as the project instruction surface in this pack.

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
