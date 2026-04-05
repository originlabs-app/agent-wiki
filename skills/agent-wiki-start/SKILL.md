---
name: agent-wiki-start
description: >
  Begin an agent-wiki session. Reads the wiki, detects tensions between
  wiki content and actual state, briefs you, asks socratic questions,
  and proposes a session plan. Use at the start of every work session.
---

# /agent-wiki-start

Begin a session. Observe, analyze, suggest, ask.

## 1. Observe (silent)

- Detect: am I inside agent-wiki (Mode 1) or in another repo (Mode 2)?
- Run `wikictl status`
- Read `wiki/index.md`
- Scan `wiki/projects/`, `wiki/sources/`, `wiki/decisions/`, `wiki/concepts/`
- Find the project or concept page matching current work
- Read `wiki/log.md` — what happened recently?
- Check `raw/untracked/` — any new sources waiting?
- Check recent git activity if in a code repo

## 2. Analyze (silent)

Look for tensions between what the wiki says and what's actually happening:

- Wiki says priority is X, but repo activity suggests Y
- A decision was recorded, but code goes a different direction
- Next steps in wiki are stale or already done
- New sources in raw/untracked/ not yet ingested
- No wiki page exists for this repo/project
- Pages that link to nothing (orphans)
- Recent work not reflected in the wiki

## 3. Suggest

Based on what you found, make concrete suggestions:

**Ingestion:** "There are 3 files in raw/untracked/. Want me to ingest them? I'd update the project page and create source summaries."

**Linking:** "The project page mentions 'auth migration' but there's no decision page for it. Should I create one?"

**Staleness:** "The wiki hasn't been updated in 2 weeks. The repo has 14 new commits. Want me to refresh the project page?"

**Contradictions:** "The wiki says you chose Stripe, but I see PayPal imports in the code. Which is current?"

**Missing context:** "I don't see a wiki page for this project. Want me to create one from what I can see in the repo?"

## 4. Ask 2-5 socratic questions

Based on tensions observed. Always hypothesize before asking:

- Bad: "What project is this?"
- Good: "I think we're on pygmalion based on the repo name. The wiki says next step is API integration. Is that what we're doing today?"

- Bad: "What do you want to do?"
- Good: "The wiki lists 3 next steps. The most recent commit touched the auth module. Are we continuing auth work, or switching to something else?"

### 5. Connect the user's intent to the wiki

When the user says what they want to work on, cross-reference it with the wiki:

- "You want to work on auth. The wiki has a decision page about JWT vs sessions from last week, and the project page mentions auth is 80% done. Here's what it says: [summary]."
- "You're asking about pricing. The wiki has a source page from the client meeting where pricing was discussed. Want me to pull it up?"
- "That topic isn't in the wiki yet. Want me to create a concept page as we work on it?"

The goal: everything the user says gets matched against what the wiki knows. The wiki is the memory — use it.

### 6. Propose a short session plan

2-4 concrete steps based on the answers.

## 6. Multi-step deep queries

When answering complex questions against the wiki, use multi-step retrieval:
1. Read wiki/index.md — understand what topics exist
2. Read relevant concept pages — get the synthesis
3. If concept pages cite sources, read those source pages for deeper detail
4. If source pages reference raw files, read the original raw material
5. Synthesize across all levels. Cite with [[page-name]].

This is the L0→L1→L2→L3 progressive disclosure pattern.

---

## How to detect agent-wiki

```bash
[ -x ./tools/wikictl ] || command -v wikictl >/dev/null 2>&1
```

If not available, continue normally. Do not fail.

## wikictl operations

The skill uses these wikictl commands behind the scenes:

- `wikictl status` — what's configured, how many pages
- `wikictl ingest "<project>" <source>` — register + move source to raw/ingested/
- `wikictl query "<terms>"` — search wiki and raw
- `wikictl lint` — detect orphans, dead links, stale pages
- `wikictl heal` — rebuild index from project pages
- `wikictl sync <agent> <op> "<desc>"` — log + lint + status
- `wikictl file-back <project> "<title>" [--type source|decision|concept]` — create wiki page + update index + log

## Wiki as memory — always search it

Whenever the user asks a question, mentions a topic, or needs context — check the wiki FIRST before answering from scratch. The wiki is the shared memory. Use it.

- User asks "what did we decide about auth?" → search wiki/decisions/ before answering
- User mentions "the client meeting last week" → check wiki/sources/ for the transcript
- User says "I think we tried this before" → check project page's "What failed" section
- User asks about a concept → check wiki/concepts/

Run `wikictl query "<terms>"` to search. Then read the relevant pages. Cite them in your answer: "According to [[wiki/decisions/2026-03-15-fastapi-over-express]], we chose FastAPI because..."

If the wiki doesn't have it, say so: "The wiki doesn't have anything on this yet. Want me to create a page?"

## Rules

1. Always observe before asking. Never ask what you can infer.
2. Hypothesize, then confirm. "I think X. Correct?" not "What is X?"
3. Suggest concretely. "I'd write [this] to [here]" not "should I update something?"
4. 2-5 questions per command. Never more.
5. Show write-back proposals before executing. User approves.
6. If the session is trivial, say so and skip.
7. If wikictl is not available, continue normally.

---

## Other commands

- `/agent-wiki-ingest` — process a source (URL, text, or file) into the wiki
- `/agent-wiki-progress` — mid-session checkpoint, scope drift detection
- `/agent-wiki-finish` — end session, write back durable knowledge
- `/agent-wiki-health` — deep audit of wiki (contradictions, orphans, staleness)
