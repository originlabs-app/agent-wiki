---
name: agent-wiki
description: >
  Karpathy-style shared knowledge base for multi-agent workflows. Use when starting
  a work session (read wiki context), after completing meaningful work (write back
  decisions, status changes, lessons learned), or when asked to ingest, query, lint,
  or sync the wiki. Works with wikictl CLI and optional MCP server.
---

# Agent Wiki

A persistent, compounding knowledge base shared across agents and sessions.

## Detect

Check if agent-wiki is available:

```bash
command -v wikictl >/dev/null 2>&1 && echo "available" ||   ([ -x ./cli/wikictl ] && echo "available" || echo "not configured")
```

If not available, continue normally. Do not fail. Do not ask the user to install anything.

## Before starting work

1. Run `wikictl status` to see what's configured.
2. Read the wiki index it points to.
3. Find the project page matching your current work.
4. Read it — you now have context: status, decisions, failures, next steps.

If using an instance: `wikictl --instance <name> status`

## During work

Work normally. The wiki is reference material, not a constraint.

## After completing meaningful work

5. Update the relevant project page with what changed:
   - Status changes
   - Decisions made (with rationale)
   - What was tried and failed
   - Next steps
6. If a significant decision was made, create a decision page:
   - `wiki/decisions/YYYY-MM-DD-short-slug.md`
7. Sync: `wikictl sync <agent-name> <operation> "<description>"`

## Ingest a source

When the user drops a source (article, transcript, brief, document):

```bash
wikictl ingest "<project-name>" <source-file>
```

Then read the source and compile the useful facts into the project page. Don't just leave the stub — extract and synthesize.

## Query the wiki

```bash
wikictl query "<search terms>"
```

Read the results, synthesize an answer with citations to wiki pages.

## Health checks

```bash
wikictl lint    # check structure
wikictl heal    # rebuild index from project pages
```

## Commands reference

| Command | What it does |
|---------|-------------|
| `wikictl status` | Health summary — what's configured, how many pages |
| `wikictl ingest "<project>" <source>` | Register a source with a project |
| `wikictl query "<terms>"` | Search wiki and raw sources |
| `wikictl heal` | Rebuild wiki/index.md from project pages |
| `wikictl lint` | Check contract files and structure |
| `wikictl sync <agent> <op> "<desc>"` | End-of-session write-back + lint |
| `wikictl log <agent> <op> "<desc>"` | Append to wiki/log.md |

## Instance mode

For external vaults or folders:

```bash
wikictl --instance origin-labs status
wikictl --config ~/.agent-wiki/instances/my-vault.conf status
```

Instance config is a simple file:
```
WIKI_ROOT=/path/to/wiki
RAW_ROOT=/path/to/raw
```

## Page types

| Type | Location | Template |
|------|----------|----------|
| Project | `wiki/projects/{slug}.md` | `wiki/projects/_template.md` |
| Source | `wiki/sources/{date}-{slug}.md` | `wiki/sources/_template.md` |
| Decision | `wiki/decisions/{date}-{slug}.md` | `wiki/decisions/_template.md` |

## Confidence markers

Use in wiki pages to signal reliability:
- `[confirmed]` — verified by human or multiple sources
- `[hypothesis]` — agent analysis, not yet verified
- `[stale]` — older than 14 days without refresh

## Rules

1. `raw/` is immutable. Never edit source files.
2. `wiki/` is the compiled layer. Keep it current.
3. Write back after every meaningful session.
4. Cite sources when adding facts.
5. When contradicting existing content, mark old claims as `[superseded]`.
6. If wikictl is not available, continue normally.

## Full contract

See `AGENTS.md` in the agent-wiki repo for the complete protocol.
