# Agent Wiki

A simple Karpathy-style starter for building a persistent wiki with an LLM.

This repo is the starting vault.
Clone it, open it in your agent, and let the agent set everything up.

- `raw/` is where you drop source material
- `wiki/` is where the LLM compiles knowledge
- `outputs/` is where generated reports and research live

`INSTALL.md` is for setup.
`SKILL.md` is for day-to-day use.
`tools/wikictl` is the local engine. `tools/mcp/` is optional.

## Two ways to use it

### Mode 1: In-Wiki

The agent is opened inside this repo.

In this mode:

- this repo is the vault
- the agent works directly in `raw/`, `wiki/`, and `outputs/`
- this is the simplest way to start

### Mode 2: Second-Brain

The agent is opened in another repo, but `agent-wiki` is used as shared memory.

In this mode:

- code lives in the other repo
- memory lives here
- the agent reads this wiki before work
- the agent writes durable knowledge back here after work

So `agent-wiki` can be both:

- the main workspace
- or the second brain behind another workspace

## Two concrete examples

### Example 1: Working inside the wiki

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

### Example 2: Coding in another repo, using agent-wiki as memory

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

## Agent-First Setup

Open this repo in your agent and say:

```text
Read INSTALL.md and set up agent-wiki for this repo.
```

Then say:

```text
Read SKILL.md and use agent-wiki for this session.
```

This repo is the wiki. Start here.

## How to use it

Daily flow:

```text
/agent-wiki start
...work normally...
/agent-wiki progress
...keep working...
/agent-wiki finish
```

What that means:

- `/agent-wiki start` reads the wiki, checks recent context, and asks a few good questions.
- `/agent-wiki progress` mid-session checkpoint — checks drift, captures emerging decisions.
- `/agent-wiki finish` proposes what should be written back, then updates the wiki.
- In Mode 1, it works in the local wiki.
- In Mode 2, it uses this repo as memory while work happens elsewhere.

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
