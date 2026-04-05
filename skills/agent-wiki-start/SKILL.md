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

## 5. Propose a session plan

2-4 concrete steps based on the answers.

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
