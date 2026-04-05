# Agent Wiki Contract

This repository is a Karpathy-style knowledge base for multi-agent workflows.

## Read order

1. `wiki/index.md`
2. `wiki/projects/<project>.md`
3. `raw/` only when more detail is needed
4. `adapters/<tool>/...` only for tool-specific bootstrap

## Data model

- `raw/` — immutable source drop zone. Never edit.
- `wiki/` — compiled knowledge layer. Agents write here via wikictl/MCP.
- `wiki/log.md` — append-only operation log.
- `contract/manifest.yaml` — protocol at a glance.

## Access control

| Path | Read | Write | Via |
|------|------|-------|-----|
| `raw/*` | all agents | human only (drop sources) | filesystem |
| `wiki/index.md` | all agents | wikictl heal | `wikictl heal` |
| `wiki/projects/*.md` | all agents | any agent | `wikictl ingest` or direct edit |
| `wiki/sources/*.md` | all agents | any agent | direct edit after ingest |
| `wiki/decisions/*.md` | all agents | any agent | direct edit |
| `wiki/log.md` | all agents | any agent | `wikictl log` or `wikictl sync` |
| `AGENTS.md` | all agents | human only | — |
| `contract/manifest.yaml` | all agents | human only | — |
| `adapters/*` | tool-specific | human only | — |

**Rule: agents SHOULD use wikictl/MCP for writes. Direct markdown edit is allowed as fallback but must still update index and log.**

## Page types

Three canonical types. Use the templates in `wiki/`.

### project

A compiled summary of an active project. One page per project.

- Template: `wiki/projects/_template.md`
- Naming: `wiki/projects/{slug}.md`
- Frontmatter type: `wiki-page`
- Updated after every significant work session.

### source

A summary of an ingested source (article, transcript, brief, meeting notes).

- Template: `wiki/sources/_template.md`
- Naming: `wiki/sources/{date}-{slug}.md`
- Frontmatter type: `wiki-source`
- Created during ingest. Never modified after (append corrections as notes).

### decision

An architecture decision record (ADR) or business decision.

- Template: `wiki/decisions/_template.md`
- Naming: `wiki/decisions/{date}-{slug}.md`
- Frontmatter type: `wiki-decision`
- Created when a significant decision is made. Updated if reversed.

## Workflow

### Start of session

1. Read `wiki/index.md`.
2. Read the relevant `wiki/projects/*.md` page.
3. Drill into `raw/` or `wiki/sources/` only if you need detail.

### During work

4. Work normally.

### End of session (MANDATORY)

5. Update `wiki/projects/*.md` with what changed (status, decisions, failures, next steps).
6. If you made a significant decision, create `wiki/decisions/{date}-{slug}.md`.
7. Run `wikictl sync <agent> <op> <description>` or manually:
   - Update `wiki/index.md` if project status changed.
   - Append to `wiki/log.md`.

### Write-back rules

**When to file back into the wiki:**
- A decision was made → `wiki/decisions/`
- A source was analyzed → `wiki/sources/`
- Project status changed → update `wiki/projects/`
- A useful Q&A answer was produced → append to relevant project or create source page

**What NOT to file back:**
- Trivial chat (small clarifications, typo fixes)
- Intermediate work that will change (draft code, WIP)
- Duplicate of what's already in the wiki

**Contradiction handling:**
- If new info contradicts existing wiki content, UPDATE the wiki page with the new info.
- Add a `## Superseded` note to the old claim with date and reason.
- Never silently overwrite — always leave a trace.

**Confidence markers:**
- `[confirmed]` — verified by human or multiple sources
- `[hypothesis]` — agent's analysis, not yet verified
- `[stale]` — older than 14 days without refresh, may be outdated

## Commands

| Command | What it does |
|---------|-------------|
| `wikictl init` | Create directory structure |
| `wikictl status` | Health summary |
| `wikictl lint` | Check contract files exist and align |
| `wikictl heal` | Rebuild wiki/index.md from project pages |
| `wikictl ingest <project> <source...>` | Register sources against a project page |
| `wikictl query <terms...>` | Search across wiki/ and raw/ |
| `wikictl sync <agent> <op> <description>` | End-of-session write-back + lint |
| `wikictl log <agent> <op> <description>` | Append log entry |

## Rules

1. `raw/` is immutable. Never edit source files.
2. Keep project pages short, current, and link-rich.
3. Prefer wikictl/MCP for writes. Direct edit is fallback only.
4. One log entry per meaningful operation.
5. Adapters are thin. All logic lives here.
6. Update `wiki/index.md` when project status changes.
7. Every session that produces knowledge must write back.
8. Mark confidence: `[confirmed]`, `[hypothesis]`, `[stale]`.
9. When contradicting existing content, leave a trace.
10. Use canonical page types (project, source, decision).
