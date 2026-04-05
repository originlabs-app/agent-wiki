# Agent Wiki Contract

A Karpathy-style knowledge base for multi-agent workflows.

## Data model

- `raw/` — immutable source drop zone. Never edit.
- `wiki/` — compiled knowledge layer. Agents write here.
- `wiki/log.md` — append-only operation log.

## Read order

1. `wiki/index.md`
2. `wiki/projects/<project>.md`
3. `raw/` only when more detail is needed

## Operations (wikictl)

Three core operations from Karpathy's model:

| Command | What it does |
|---------|-------------|
| `wikictl ingest <project> <source>` | Register + compile a source into wiki |
| `wikictl query <terms>` | Search across wiki/ and raw/ |
| `wikictl lint` | Check structure and alignment |

Supporting commands:

| Command | What it does |
|---------|-------------|
| `wikictl status` | Health summary |
| `wikictl heal` | Rebuild wiki/index.md |
| `wikictl sync <agent> <op> <desc>` | End-of-session write-back + log |
| `wikictl log <agent> <op> <desc>` | Append to log |

## Write-back rule

Every session that produces durable knowledge must write it back to the wiki
before ending — update project pages, create decision/source pages as needed,
and run `wikictl sync`.

## Rules

1. `raw/` is immutable — never edit source files.
2. Prefer wikictl for writes; direct edit is fallback only.
3. Every meaningful operation gets one log entry.
