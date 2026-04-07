---
name: atlas-start
description: >
  Begin an Atlas session. Reads the knowledge graph and wiki, detects
  tensions, briefs the agent, asks socratic questions, and proposes a
  session plan. Use at the start of every work session.
---

# /atlas-start

Begin a session. Observe, analyze, suggest, ask.

## 1. Observe (silent)

- Run `atlas audit --root .` to get graph + wiki health
- Read `wiki/index.md` — what topics exist?
- Scan `wiki/projects/`, `wiki/concepts/`, `wiki/decisions/`, `wiki/sources/`
- Read `wiki/log.md` — what happened recently?
- Check `raw/untracked/` — any new sources waiting?
- Run `atlas god-nodes --root .` — what are the key concepts?
- Check recent git activity if in a code repo

## 2. Analyze (silent)

Look for tensions between what the wiki says and what's actually happening:

- Wiki says priority is X, but repo activity suggests Y
- A decision was recorded, but code goes a different direction
- Next steps in wiki are stale or already done
- New sources in raw/untracked/ not yet ingested
- No wiki page exists for this repo/project
- Atlas audit found contradictions, orphans, or broken links
- Recent work not reflected in the wiki
- God nodes that lack dedicated wiki pages

## 3. Suggest

Based on what you found, make concrete suggestions:

**Ingestion:** "There are 3 files in raw/untracked/. Want me to ingest them? I'd run `atlas ingest` for each."

**Graph gaps:** "The graph has 5 nodes without wiki pages. Want me to create stubs?"

**Staleness:** "The wiki hasn't been updated in 2 weeks. The repo has 14 new commits. Want me to run `atlas scan --update .` and refresh?"

**Contradictions:** "The wiki says you chose Stripe, but the graph shows PayPal imports. Which is current?"

**Missing context:** "I don't see a wiki page for this project. Want me to create one from what the graph shows?"

## 4. Ask 2-5 socratic questions

Based on tensions observed. Always hypothesize before asking:

- Bad: "What project is this?"
- Good: "Based on the graph, this is the auth module — the wiki says next step is API integration. Is that what we're doing today?"

- Bad: "What do you want to do?"
- Good: "The audit shows 3 stale pages and 2 broken links. The most recent commit touched billing. Are we continuing billing, or should we fix the wiki first?"

## 5. Connect intent to the graph

When the user says what they want to work on, query the graph:

- "You want to work on auth. Let me check: `atlas query auth`. The graph shows auth connects to db, cache, and billing. The wiki has a decision page about JWT vs sessions. Here's what it says: [summary]."
- "That topic isn't in the graph yet. Want me to scan for it or create a wiki page?"

## 6. Propose a short session plan

2-4 concrete steps based on the answers.

## 7. Multi-step deep queries

When answering complex questions:
1. `atlas query "<concept>"` — get the graph neighborhood
2. Read the wiki page for that concept
3. If it cites sources, read those source pages
4. If sources reference raw files, read the original
5. Synthesize across all levels. Cite with [[page-name]].

---

## Atlas CLI commands used

- `atlas audit --root .` — health score, orphans, contradictions, staleness
- `atlas god-nodes --root .` — most connected concepts
- `atlas query "<concept>" --root .` — graph traversal from a concept
- `atlas surprises --root .` — unexpected cross-boundary connections
- `atlas scan --update . ` — incremental re-scan

## Rules

1. Always observe before asking. Never ask what you can infer.
2. Hypothesize, then confirm. "I think X. Correct?" not "What is X?"
3. Suggest concretely. "I'd run [command] to [result]" not "should I update something?"
4. 2-5 questions max. Never more.
5. Show write-back proposals before executing. User approves.
6. If atlas-out/graph.json doesn't exist, suggest running `atlas scan .` first.
7. If the session is trivial, say so and skip.

---

## Other Atlas skills

- `/atlas-scan` — scan a directory into the knowledge graph
- `/atlas-query` — query the graph for connections
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-progress` — mid-session checkpoint
- `/atlas-finish` — end session, write back durable knowledge
- `/atlas-health` — deep audit of graph and wiki
