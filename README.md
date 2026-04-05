# Agent Wiki

A Karpathy-style knowledge base for multi-agent workflows.

You open an agent, it reads the wiki, it works, it writes the result back, and knowledge compounds.

## What this is

A shared contract that any LLM agent can follow — Claude, Codex, Cursor, Hermes, or anything that reads markdown.

- `raw/` stores immutable source material.
- `wiki/` stores compiled knowledge, written and maintained by agents.
- `AGENTS.md` defines the protocol.
- `wikictl` and MCP are the operational interface.
- Agents are clients of this contract.

This is not RAG. Not a chat memory. Not a manual wiki. Not tied to a single agent.

It's a format for making knowledge persist across sessions and across agents.

## Before installing

You can read this repo without installing anything. The idea is simple:

1. Sources go into `raw/` (articles, transcripts, briefs, docs).
2. Agents compile the useful parts into `wiki/` (summaries, decisions, cross-references).
3. The wiki gets richer with every source you add and every question you ask.
4. Any agent starting a new session reads the wiki first — full context in 30 seconds.

The principle:

- Chat is for working.
- Wiki is for remembering.
- Tools are for synchronizing.

## After installing

1. Open the repo in Claude, Codex, Cursor, or Hermes.
2. The agent reads `AGENTS.md` (or `CLAUDE.md`).
3. It reads `wiki/index.md`.
4. It opens the relevant project page.
5. If it needs detail, it reads the sources in `raw/`.
6. It works.
7. End of session: it writes back to the wiki via `wikictl` or MCP.
8. `wiki/log.md` keeps the trace. `wiki/index.md` stays current.

## How it works

### 1. You give a source

Drop an article, transcript, brief, or document into `raw/`.

### 2. The agent compiles

It reads the source, extracts the key facts, and updates the wiki — project pages, source summaries, cross-references.

### 3. You ask a question

The agent reads the wiki, finds the right pages, and synthesizes an answer with citations.

### 4. Useful answers get filed back

If the answer produces durable knowledge, it goes back into the wiki as a page or a section.

### 5. The system improves with every session

The wiki becomes richer, more structured, easier to query. That's the compounding effect.

## Agent setup

### Claude Code

- Reads `CLAUDE.md` → follows the shared contract.
- Uses hooks in `.claude/settings.json` for session lifecycle.
- Calls `wikictl` or MCP for writes.

### Codex

- Reads `AGENTS.md` → same contract.
- Calls `wikictl` or MCP for writes.

### Cursor

- Reads `AGENTS.md` or `.cursor/rules/agent-wiki.mdc`.
- Same contract, same commands.

### Hermes

- Uses `adapters/hermes/SKILL.md`.
- Same protocol, calls `wikictl` or MCP.

## What this is not

- Not a vector database or RAG pipeline.
- Not a chat history or session memory.
- Not a wiki you maintain by hand.
- Not locked to any specific agent or provider.

## Install

```bash
./install.sh
```

Optional — link agent configs to your local tools:

```bash
./install.sh --bootstrap
```

Or with make:

```bash
make init
make bootstrap
make status
make heal
```

## Commands

```bash
./cli/wikictl ingest "<project>" <source...>   # register sources with a project
./cli/wikictl query <terms...>                  # search wiki and raw
./cli/wikictl heal                              # rebuild index from project pages
./cli/wikictl sync <agent> <op> <desc>          # end-of-session write-back
./cli/wikictl lint                              # check structure health
./cli/wikictl log <agent> <op> <desc>           # append to log
./cli/wikictl status                            # health summary
```

## MCP

If your agent speaks MCP:

```bash
npm install
npm run mcp
```

The MCP server exposes the same operations as the CLI.

## Layout

```
agent-wiki/
├── AGENTS.md                    # the contract (read this first)
├── CLAUDE.md                    # Claude Code entry point → AGENTS.md
├── contract/manifest.yaml       # protocol at a glance
├── cli/wikictl                  # bash CLI (zero dependencies)
├── mcp/server.mjs               # MCP transport (Node.js)
├── raw/                         # immutable source material
├── wiki/
│   ├── index.md                 # entry point — read first
│   ├── log.md                   # append-only operation log
│   ├── projects/                # one page per project
│   ├── sources/                 # one page per ingested source
│   └── decisions/               # architecture/business decisions
├── adapters/
│   ├── claude/CLAUDE.md
│   ├── codex/AGENTS.md
│   ├── cursor/
│   └── hermes/SKILL.md
├── docs/
│   ├── usage.md
│   ├── tool-configs.md
│   └── examples/                # 4 real use-case walkthroughs
├── scripts/
│   ├── bootstrap-local.sh
│   └── verify.sh
└── install.sh
```

## Use cases

See `docs/examples/` for detailed walkthroughs:

- **[Research project](docs/examples/research-project.md)** — cumulative synthesis over weeks/months.
- **[Software project](docs/examples/software-project.md)** — multi-agent handoff, architecture decisions survive across sessions.
- **[Business operations](docs/examples/business-operations.md)** — client management, meeting notes compiled into living project pages.
- **[Analysis dossier](docs/examples/analysis-dossier.md)** — benchmarking, due diligence, decisions with full source trail.

## Credits

Inspired by [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (April 2026).

## License

MIT
