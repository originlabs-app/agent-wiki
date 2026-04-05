# Knowledge Base Schema

## What This Is

A persistent knowledge base maintained by LLM agents. Knowledge compounds over time — each session makes the next one richer.

<!-- Customize: describe what YOUR wiki is about -->
<!-- Example: "A knowledge base about AI agent tooling, our client projects, and technical architecture decisions." -->

## How It's Organized

- `raw/` — immutable source material. Drop articles, notes, transcripts, screenshots here. Never modify after adding.
- `wiki/` — the compiled knowledge base. AI writes and maintains this. You read it.
  - `wiki/projects/` — one page per project
  - `wiki/sources/` — one page per ingested source
  - `wiki/decisions/` — architecture and business decisions
  - `wiki/concepts/` — thematic pages aggregating knowledge across sources
  - `wiki/index.md` — catalog of everything, read this first
  - `wiki/log.md` — append-only operation log
- `outputs/` — generated answers, reports, and research.
- `tools/` — the engine (wikictl CLI, MCP server).

## Rules

1. Never edit files in `raw/`. They're the source of truth.
2. Every wiki article starts with a one-paragraph summary.
3. Link related topics using `[[page-name]]` format.
4. Keep `wiki/index.md` current — it lists every page with a one-line description.
5. When new sources are added, update the relevant wiki pages.
6. Append meaningful operations to `wiki/log.md`.
7. Prefer updating the wiki over leaving knowledge in chat history.
8. Good outputs may be filed back into relevant wiki pages.
9. Every wiki page should have a confidence indicator in its frontmatter: `confidence: high | medium | low`
   - **high** = verified by human or multiple corroborating sources
   - **medium** = single source, agent analysis
   - **low** = hypothesis, unverified, or stale (>30 days without refresh)
10. Use dual-link format on every cross-reference: `[[page-name|Display Name]](../path/to/page.md)`. This ensures links work in Obsidian (wikilinks), GitHub (markdown links), and plain text editors.

## Read order

1. `wiki/index.md`
2. `wiki/log.md` — what happened recently
3. Relevant pages in `wiki/projects/`, `wiki/sources/`, `wiki/decisions/`, `wiki/concepts/`
4. `raw/` only when more detail is needed

## Operations

- **ingest** — integrate new sources from `raw/` into the wiki. One source can touch 5-15 pages.
- **query** — answer questions against the wiki with citations.
- **compile** — batch-ingest all pending sources in `raw/untracked/` into the wiki.
- **lint** — detect contradictions, gaps, dead links, orphan pages, and stale content.

## Workflow

Use the agent-wiki skills (each is a separate slash command):
- `/agent-wiki-start` — begin a session (reads wiki, asks socratic questions, proposes a plan)
- `/agent-wiki-ingest` — process a source (URL, text, or file → compiled into wiki)
- `/agent-wiki-progress` — mid-session checkpoint
- `/agent-wiki-finish` — end of session (writes back durable knowledge)
- `/agent-wiki-health` — deep audit of the wiki (contradictions, orphans, stale pages)
