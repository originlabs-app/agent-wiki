---
name: agent-wiki
description: Read and write to a shared Karpathy-style wiki. Use wikictl for ingest, query, heal, sync. Reads wiki at session start, writes back at session end.
tags: [wiki, knowledge-base, memory, multi-agent]
---

# Agent Wiki — Hermes Adapter

Read `AGENTS.md` for the full contract.

## When to activate

- Start of any session where project context would help.
- End of any session where knowledge was produced.
- When the user says "ingest", "query wiki", "lint wiki", "sync".

## Wiki Protocol

If `wikictl` is available (check `./cli/wikictl` or the repo path):

### Before starting work

1. Run `wikictl status` (or `wikictl --instance <name> status` if configured).
2. If a wiki is configured, read the index.
3. Find and read the project page matching the current work.
4. You now have context — decisions, failures, current status, next steps.

### After completing meaningful work

5. Update the relevant project page with what changed.
6. If a significant decision was made, create a decision page.
7. Run `wikictl sync hermes <op> "<description>"`.

### Ingest (user drops a source)

8. Run `wikictl ingest "<project>" <source-path>`.
9. Read the source file.
10. Compile the useful facts into the project page (don't just leave the stub).
11. Create a source page in `wiki/sources/` if the source is substantial.

### Query

12. Run `wikictl query "<terms>"` to search wiki and raw.
13. Read the relevant results.
14. Synthesize an answer with citations to wiki pages.

### If wikictl is not available

Continue normally. Do not fail. Do not ask the user to install anything.

## Keep it simple

This skill tells you to use wikictl. The contract is in `AGENTS.md`. The config is resolved by wikictl (local wiki/ or `--instance` or `--config`).
