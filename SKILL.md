---
name: agent-wiki
description: >
  Shared knowledge base workflow for LLM Wiki projects.
  Use /agent-wiki start at the beginning of a session and
  /agent-wiki finish at the end. Use wikictl or MCP for ingest,
  query, lint, heal, and sync.
---

# Agent Wiki

Use this skill when working in a project that follows the LLM Wiki pattern.

## Modes

### Mode 1: In-Wiki

Use this when the current repo is `agent-wiki` itself.

- Read and write the local `wiki/`, `raw/`, and `outputs/`.
- Use local `wikictl` or local MCP tools when available.

### Mode 2: Second-Brain

Use this when the current repo is some other working repo, but `agent-wiki`
is configured as shared memory.

- Work happens in the current repo.
- Durable memory lives in the configured `agent-wiki` instance.
- Read context from the wiki before work.
- Write back durable knowledge after work.

## /agent-wiki start

Run at the beginning of a meaningful session.

### What to do

1. Observe silently:
   - inspect the current repo or working directory
   - determine whether you are in Mode 1 or Mode 2
   - read `wiki/index.md` from the relevant wiki
   - find the most relevant project page
   - check `wiki/log.md` for recent work
   - check whether new sources exist in `raw/untracked/`

2. Analyze silently:
   - compare repo state and wiki state
   - detect tensions, gaps, contradictions, stale next steps, or missing context

3. Brief the user:
   - summarize what the wiki says about the current project
   - state the most likely current objective

4. Ask 2 to 5 Socratic questions:
   - base them on tensions or ambiguities you observed
   - hypothesize before asking
   - avoid generic questions you could answer from context

5. Propose a short session plan:
   - 2 to 4 concrete steps

## /agent-wiki finish

Run at the end of a meaningful session.

### What to do

1. Observe silently:
   - inspect what changed in the repo, files, or outputs
   - determine whether write-back belongs in the local wiki or the second-brain wiki
   - identify decisions, learnings, failures, and next steps

2. Ask 2 to 5 targeted questions:
   - focus only on what should become durable knowledge

3. Propose write-back:
   - say exactly what should be updated and where
   - examples:
     - `wiki/projects/...`
     - `wiki/decisions/...`
     - `wiki/sources/...`


4. Ask for confirmation.

5. Execute:
   - update the wiki
   - run `wikictl sync <agent> <op> "<description>"` or the MCP equivalent

## Operations

Use `wikictl` or MCP for these operations when available:

- `ingest`
- `query`
- `lint`
- `heal`
- `sync`

## Rules

1. Never edit `raw/`.
2. Keep the wiki current.
3. Prefer filing useful outputs back into the wiki.
4. Do not leave durable knowledge only in chat.
5. If the project is not configured for agent-wiki, continue normally without failing.
