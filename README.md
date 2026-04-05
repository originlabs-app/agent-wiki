# Agent Wiki

A simple Karpathy-style starter for building a persistent wiki with an LLM.

## Prerequisites

Requires: bash, git. Optional: rg (ripgrep) for faster search.

This repo is the starting vault.
Clone it, open it in your agent, and let the agent set everything up.

- `raw/` is where you drop source material
- `wiki/` is where the LLM compiles knowledge
- `outputs/` is where generated reports and research live

`INSTALL.md` is for setup.
`SKILL.md` is for day-to-day use.
`tools/wikictl` is the local engine. `tools/mcp/` is optional.

## Two concrete examples

### Example 1: Working inside the wiki (In-Wiki mode)

You open Claude, Codex, or Hermès in this repo.

You say:

```text
Read INSTALL.md and set up agent-wiki for this repo.
Read SKILL.md and use agent-wiki for this session.
```

Then your flow is:

```text
/agent-wiki start
...ingest sources, ask questions, update the wiki...
/agent-wiki finish
```

### Example 2: Coding in another repo, using agent-wiki as memory (Second-Brain mode)

You open the agent in another repo, for example a client codebase.

The code work happens there.
The durable memory lives in `agent-wiki`.

Your flow is:

```text
/agent-wiki start
...work in the code repo...
/agent-wiki finish
```

In this mode, the wiki is not the main workspace.
It is the second brain that keeps context, decisions, failures, and next steps across sessions.

## Getting started

Open this repo in your agent and say:

```text
Read INSTALL.md and set up agent-wiki for this repo.
Read SKILL.md and use agent-wiki for this session.
```

Daily flow: `/agent-wiki start` → work → `/agent-wiki progress` → work → `/agent-wiki finish`.

## Under the hood

```bash
./tools/wikictl status
./tools/wikictl ingest "Project" raw/untracked/source.md
./tools/wikictl query "search terms"
./tools/wikictl lint
./tools/wikictl heal
./tools/wikictl sync claude done "updated project memory"
```

## Folder model

```text
raw/
  untracked/   new source material waiting to be ingested
  ingested/    source material already processed

wiki/
  index.md     the table of contents
  log.md       append-only operation log
  projects/    project pages
  sources/     source pages
  decisions/   decision pages

outputs/
  README.md
```

## Notes

- Obsidian is optional.
- You do not need a database.
- `raw/`, `wiki/`, and `outputs/` are the only folders that matter.
- The default setup flow is agent-first.

## License

MIT
