# Agent Wiki

This repo is a Karpathy-style knowledge base. The AI writes and maintains the wiki. The human reads and asks questions.

- `raw/` — source material (immutable)
- `wiki/` — compiled knowledge (you maintain this)
- `outputs/` — generated answers and reports
- `tools/wikictl` — the CLI engine

Read `AGENTS.md` for the full schema and rules.
Use `SKILL.md` for the session workflow (`/agent-wiki start`, `ingest`, `progress`, `finish`).
