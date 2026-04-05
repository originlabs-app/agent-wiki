# Agent Wiki

This repo is a Karpathy-style knowledge base. The AI writes the wiki. You read it.

- raw/ — source material (immutable)
- wiki/ — compiled knowledge (you maintain this)
- outputs/ — generated answers and reports
- tools/wikictl — the CLI engine

Full schema: AGENTS.md
Session workflow: use /agent-wiki-start, /agent-wiki-ingest, /agent-wiki-progress, /agent-wiki-finish, /agent-wiki-health

Each command is a separate skill in skills/.
