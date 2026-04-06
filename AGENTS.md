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

## Page types and frontmatter

Each page type has a required frontmatter schema. Use the templates in each directory (`_template.md`) as reference. `wikictl file-back` generates this automatically — if you write pages directly, follow the same schema.

### Projects (`wiki/projects/`)

One page per project. Filename: `{slug}.md`.

```yaml
---
type: wiki-page
project: ProjectName        # display name
status: active              # active | paused | completed | blocked
updated: YYYY-MM-DD
updated_by: agent
repo: ""                    # optional git repo URL
confidence: medium          # high | medium | low
---
```

### Sources (`wiki/sources/`)

One page per ingested source. Filename: `YYYY-MM-DD-{slug}.md` (date-prefixed).

```yaml
---
type: wiki-source
title: "Source Title"
date: YYYY-MM-DD            # date of the source
project: project-name       # which project this relates to
source-type: article        # article | transcript | brief | meeting | report
raw-path: ""                # path to raw/ file
ingested-by: agent
confidence: medium
---
```

### Decisions (`wiki/decisions/`)

One page per decision. Filename: `YYYY-MM-DD-{slug}.md` (date-prefixed).

```yaml
---
type: wiki-decision
title: "Decision Title"
date: YYYY-MM-DD            # when the decision was made
project: project-name
status: active              # active | superseded | reversed
decided-by: ""
confidence: medium
---
```

### Concepts (`wiki/concepts/`)

Thematic pages that aggregate knowledge across sources. Filename: `{slug}.md` (no date — concepts are timeless).

```yaml
---
type: wiki-concept
title: "Concept Name"
updated: YYYY-MM-DD
updated_by: agent
confidence: medium
tags: [tag1, tag2]          # for discovery and cross-referencing
description: "One-sentence summary for the index."
---
```

Concepts do NOT have `date:` or `project:` — they span projects and evolve over time.

### Confidence levels

- **high** = verified by human or multiple corroborating sources
- **medium** = single source, agent analysis
- **low** = hypothesis, unverified, or stale (>30 days without refresh)

## Rules

1. Never edit files in `raw/`. They're the source of truth.
2. Every wiki article starts with a one-paragraph summary after the H1.
3. Link related topics using `[[page-name]]` format.
4. Keep `wiki/index.md` current — it lists every page with a one-line description.
5. When new sources are added, update the relevant wiki pages.
6. Append meaningful operations to `wiki/log.md`.
7. Prefer updating the wiki over leaving knowledge in chat history.
8. Good outputs may be filed back into relevant wiki pages.
9. Every wiki page must have a `confidence` field in its frontmatter.
10. Use [[wikilinks]] for cross-references. They work in Obsidian and are readable in plain text.
11. Always use `title:` in frontmatter (not `concept:` or `decision:` as standalone keys).

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
