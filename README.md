# Agent Wiki

A Karpathy-style knowledge base that any LLM agent can read and maintain.

You drop sources, the AI compiles a wiki, and knowledge compounds over time.

## Prerequisites

Requires: `bash`, `git`. Optional: `rg` ([ripgrep](https://github.com/BurntSushi/ripgrep)) for faster search.

## Quick start

```bash
git clone https://github.com/originlabs-app/agent-wiki.git
cd agent-wiki
```

Open in your agent (Claude Code, Codex, Cursor, Hermes) and say:

```
Read INSTALL.md and set up agent-wiki.
```

Then say:

```
/agent-wiki-start
```

That's it. The agent reads the wiki, briefs you, and you're working.

---

## How to use

### The daily workflow

```
/agent-wiki-start       ← begin your session
       ↓
    work normally
       ↓
/agent-wiki-progress    ← optional mid-session checkpoint
       ↓
    keep working
       ↓
/agent-wiki-finish      ← end your session, write back to wiki
```

### When you have a source to add

```
/agent-wiki-ingest      ← paste a URL, text, or file path
```

The agent saves it to `raw/`, reads it, asks you socratic questions about what it means, compiles it into the wiki, and cross-links with existing pages.

### Monthly health check

```
/agent-wiki-health      ← deep audit of the wiki
```

Finds contradictions, orphan pages, stale content, dead links, unsourced claims, and suggests new pages to fill gaps.

---

## All commands

### Skill commands (you say these to your agent)

| Command | When | What it does |
|---------|------|-------------|
| `/agent-wiki-start` | Beginning of session | Reads wiki, detects tensions, briefs you, asks socratic questions, proposes a plan |
| `/agent-wiki-ingest` | When you have a source | Saves to raw/, compiles into wiki, cross-links, flags contradictions |
| `/agent-wiki-progress` | Mid-session | Quick checkpoint — scope drift detection, save suggestions, health check |
| `/agent-wiki-finish` | End of session | Proposes write-back, asks what changed, updates wiki, logs |
| `/agent-wiki-health` | Monthly | Deep audit — contradictions, orphans, staleness, gaps, error propagation |

### CLI commands (the engine behind the skill)

| Command | What it does |
|---------|-------------|
| `./tools/wikictl status` | Health summary — pages count, stale detection |
| `./tools/wikictl ingest "<project>" <source>` | Register source, update project page, move to ingested/ |
| `./tools/wikictl query "<terms>"` | Search across wiki/ and raw/ |
| `./tools/wikictl lint` | Check structure — missing files, broken links |
| `./tools/wikictl heal` | Rebuild wiki/index.md from project pages |
| `./tools/wikictl sync <agent> <op> "<desc>"` | End-of-session write-back + lint + status |
| `./tools/wikictl log <agent> <op> "<desc>"` | Append entry to wiki/log.md |

You don't usually call wikictl directly — the skill commands call it for you.

---

## Two modes

### Mode 1: In-Wiki

Open your agent in this repo. Work directly in `raw/`, `wiki/`, `outputs/`. The repo is your wiki.

### Mode 2: Second-Brain

Open your agent in another repo (client code, project, etc.). Agent-wiki lives alongside as shared memory. Your code stays in the code repo. Durable knowledge goes into agent-wiki.

Both modes use the same 5 commands.

---

## Folder structure

```
agent-wiki/
├── raw/
│   ├── untracked/     ← drop sources here
│   └── ingested/      ← processed sources land here
├── wiki/
│   ├── index.md       ← table of contents (read first)
│   ├── log.md         ← operation history
│   ├── projects/      ← one page per project
│   ├── sources/       ← one page per ingested source
│   └── decisions/     ← architecture / business decisions
│   └── concepts/      ← thematic pages (topics spanning multiple sources)
├── outputs/           ← generated answers, reports, research
├── tools/
│   ├── wikictl        ← CLI engine (bash)
│   └── mcp/           ← optional MCP transport (Node.js)
├── skills/            ← one directory per command (agents read these)
│   ├── agent-wiki-start/SKILL.md
│   ├── agent-wiki-ingest/SKILL.md
│   ├── agent-wiki-progress/SKILL.md
│   ├── agent-wiki-finish/SKILL.md
│   └── agent-wiki-health/SKILL.md
├── SKILL.md           ← combined reference (all 5 commands)
├── AGENTS.md          ← schema and rules
├── CLAUDE.md          ← Claude Code entry point
├── INSTALL.md         ← agent-driven setup
└── README.md          ← you are here
```

## Key files

| File | Who reads it | Purpose |
|------|-------------|---------|
| `skills/agent-wiki-*/SKILL.md` | Your agent | One skill per command — start, ingest, progress, finish, health |
| `AGENTS.md` | Your agent | Schema — folder structure, rules, operations |
| `INSTALL.md` | Your agent | First-time setup — detects tools, asks questions, installs skill |
| `CLAUDE.md` | Claude Code | Entry point that points to skills/ and AGENTS.md |
| `wiki/index.md` | Everyone | Table of contents for the compiled wiki |

---

## MCP (optional)

If your agent speaks MCP:

```bash
cd tools && npm install && npm run mcp
```

---

## Notes

- Obsidian is optional. Open the repo as a vault for graph view and backlinks.
- No database. No embeddings. Pure markdown.
- The agent writes the wiki. You read it and ask questions.

## Credits

Inspired by [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## License

MIT
