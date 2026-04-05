# Agent Wiki

A shared knowledge base that any LLM agent can read and maintain.

You open an agent, it reads the wiki, it works, it writes the result back, and knowledge compounds over time.

Inspired by [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

---

## Quickstart

Pick the mode that fits your setup:

### Mode 1: Standalone (no Obsidian, no existing repo)

```bash
git clone https://github.com/originlabs-app/agent-wiki.git
cd agent-wiki
./install.sh
```

Open the folder in Claude Code, Codex, or Cursor. The agent reads `AGENTS.md` and starts working with the wiki.

### Mode 2: With Obsidian

Same as Mode 1, then open the `agent-wiki` folder as an Obsidian vault.

Obsidian is just a reading surface — you browse the wiki, follow backlinks, use graph view. Agents still do the writing.

You don't need Obsidian. It's nice to have.

### Mode 3: Inside an existing repo or vault

```bash
cd ~/your-existing-project
curl -sL https://raw.githubusercontent.com/originlabs-app/agent-wiki/main/install.sh | bash -s -- --here
```

Or manually:

```bash
git clone https://github.com/originlabs-app/agent-wiki.git /tmp/agent-wiki
cp -r /tmp/agent-wiki/{AGENTS.md,cli,wiki,raw} ~/your-existing-project/
```

This adds the wiki layer to your existing project. Your code and files stay untouched.

---

## How it works

### 1. You give a source

Drop an article, transcript, brief, or document into `raw/`.

### 2. The agent compiles

It reads the source, extracts key facts, and updates the wiki — project pages, source summaries, cross-references.

### 3. You ask a question

The agent reads the wiki, finds the right pages, and answers with citations.

### 4. Useful answers get filed back

Durable knowledge goes back into the wiki as a page or section.

### 5. The wiki gets richer every session

That's the compounding effect. Each session makes the next one faster.

---

## What's inside

```
raw/                    # drop sources here (immutable, agents never edit)
wiki/
├── index.md            # read this first — catalog of everything
├── log.md              # append-only operation log
├── projects/           # one page per project (compiled summaries)
├── sources/            # one page per ingested source
└── decisions/          # architecture and business decisions
AGENTS.md               # the contract — every agent reads this
cli/wikictl             # local CLI for ingest, query, heal, sync
```

## Commands

```bash
./cli/wikictl ingest "My Project" raw/article.md   # register a source
./cli/wikictl query "search terms"                  # search wiki + raw
./cli/wikictl heal                                  # rebuild index
./cli/wikictl sync claude done "finished auth"      # end-of-session write-back
./cli/wikictl status                                # health check
./cli/wikictl lint                                  # structure check
```

---

## Supported agents

| Agent | Entry point | How it writes |
|-------|-------------|---------------|
| Claude Code | `CLAUDE.md` → `AGENTS.md` | `wikictl` or MCP |
| Codex | `AGENTS.md` | `wikictl` or MCP |
| Cursor | `AGENTS.md` or `.cursor/rules/` | `wikictl` or MCP |
| Hermes | `adapters/hermes/SKILL.md` | `wikictl` or MCP |

All agents follow the same contract. Adapters are thin — one file each.

---

## Use cases

See [`docs/examples/`](docs/examples/) for detailed walkthroughs:

- **[Research project](docs/examples/research-project.md)** — cumulative synthesis over weeks.
- **[Software project](docs/examples/software-project.md)** — multi-agent handoff, architecture decisions survive across sessions.
- **[Business operations](docs/examples/business-operations.md)** — meeting notes compiled into living project pages.
- **[Analysis dossier](docs/examples/analysis-dossier.md)** — benchmarking and due diligence with full source trail.

---

## Advanced

### MCP server

If your agent speaks MCP:

```bash
npm install
npm run mcp
```

The MCP server exposes the same operations as the CLI over the tool transport.

### Hooks (Claude Code)

`.claude/settings.json` includes hooks for automatic write-back at end of session. See [`docs/tool-configs.md`](docs/tool-configs.md).

### Adapters

Each agent gets a thin adapter file in `adapters/`. These just point to `AGENTS.md`. See [`docs/tool-configs.md`](docs/tool-configs.md) for the full config map.

### Bootstrap local configs

To link adapters into your local tool config directories:

```bash
./scripts/bootstrap-local.sh
```

This symlinks the adapter files into `~/.claude/`, `~/.codex/`, `~/.cursor/`, and `~/.hermes/`.

---

## What this is not

- Not a vector database or RAG pipeline.
- Not a chat history or session memory.
- Not a wiki you maintain by hand.
- Not tied to any single agent or provider.

---

## License

MIT
