# Agent Wiki

A shared knowledge base that any LLM agent can read and maintain.

You open an agent, it reads the wiki, it works, it writes the result back, and knowledge compounds over time.

Inspired by [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

---

## Install

### As a skill (recommended)

Works with Claude Code, Codex, Cursor, Gemini CLI, and any agent supporting the [Agent Skills](https://agentskills.io/) standard:

```bash
npx skills add originlabs-app/agent-wiki
```

The skill teaches your agent how to use `wikictl` and the wiki protocol. Your existing configs are not modified.

### As a standalone repo

```bash
git clone https://github.com/originlabs-app/agent-wiki.git
cd agent-wiki
./install.sh
```

Open the folder in your agent. It reads `SKILL.md` automatically.

### Inside an existing repo or vault

Give `INSTALL.md` to your LLM agent:

```
Read INSTALL.md and set up agent-wiki on my machine.
```

The agent will add the wiki layer to your existing project without overwriting anything.

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
agent-wiki/
├── SKILL.md                 # the skill — agents read this to learn the protocol
├── AGENTS.md                # full contract (read order, access control, rules)
├── CLAUDE.md                # Claude Code entry point → SKILL.md
├── cli/wikictl              # CLI tool (bash, zero dependencies)
├── wiki/
│   ├── index.md             # entry point — read this first
│   ├── log.md               # append-only operation log
│   ├── projects/            # one page per project
│   ├── sources/             # one page per ingested source
│   └── decisions/           # architecture and business decisions
├── raw/                     # immutable source material
├── mcp/server.mjs           # MCP transport (optional, needs Node.js)
├── contract/manifest.yaml   # protocol at a glance
├── INSTALL.md               # LLM-friendly install instructions
└── docs/
    ├── usage.md
    ├── tool-configs.md
    ├── vault-organization.md
    └── examples/            # 4 real use-case walkthroughs
```

## Commands

```bash
wikictl status                              # health check
wikictl ingest "My Project" raw/source.md   # register a source
wikictl query "search terms"                # search wiki + raw
wikictl heal                                # rebuild index
wikictl sync claude done "finished auth"    # end-of-session write-back
wikictl lint                                # structure check
```

Instance mode (for external vaults):
```bash
wikictl --instance my-vault status
wikictl --config ~/.agent-wiki/instances/my-vault.conf query "test"
```

---

## Supported agents

The `SKILL.md` follows the [Agent Skills](https://agentskills.io/) open standard. It works with:

- Claude Code
- OpenAI Codex
- Cursor
- Gemini CLI
- GitHub Copilot
- Hermes
- Any agent that reads SKILL.md

All agents follow the same protocol. One skill, not four adapters.

---

## Use cases

See [`docs/examples/`](docs/examples/) for detailed walkthroughs:

- **[Research project](docs/examples/research-project.md)** — cumulative synthesis over weeks.
- **[Software project](docs/examples/software-project.md)** — multi-agent handoff, decisions survive across sessions.
- **[Business operations](docs/examples/business-operations.md)** — meetings compiled into living project pages.
- **[Analysis dossier](docs/examples/analysis-dossier.md)** — benchmarking with full source trail.

---

## Advanced

### MCP server

If your agent speaks MCP:

```bash
npm install
npm run mcp
```

Exposes the same operations as the CLI over the MCP tool transport.

### Instance mode

Attach agent-wiki to an existing vault or folder without moving files:

```bash
mkdir -p ~/.agent-wiki/instances
cat > ~/.agent-wiki/instances/my-vault.conf << EOF
WIKI_ROOT=/path/to/your/wiki
RAW_ROOT=/path/to/your/raw
EOF

wikictl --instance my-vault status
```

### Obsidian

Open the `agent-wiki` folder (or your attached vault) as an Obsidian vault. Obsidian is just a reading surface — agents do the writing. You get backlinks, graph view, and visual navigation for free.

Not required. Not a dependency.

---

## What this is not

- Not a vector database or RAG pipeline.
- Not a chat history or session memory.
- Not a wiki you maintain by hand.
- Not tied to any single agent or provider.

---

## Credits

Inspired by [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (April 2026).

## License

MIT
