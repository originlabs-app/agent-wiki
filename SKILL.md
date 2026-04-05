---
name: agent-wiki
description: >
  Shared knowledge base for LLM Wiki projects. Three commands:
  /agent-wiki start (begin session), /agent-wiki progress (mid-session),
  /agent-wiki finish (end session). Each command observes, analyzes,
  suggests, and asks socratic questions. Uses wikictl CLI for wiki operations.
---

# Agent Wiki

Three commands. Each one: observe, analyze, suggest, ask.

## /agent-wiki start

### 1. Observe (silent)

- Detect: am I inside agent-wiki (Mode 1) or in another repo (Mode 2)?
- Run `wikictl status`
- Read `wiki/index.md`
- Find the project page matching current work
- Read `wiki/log.md` — what happened recently?
- Check `raw/untracked/` — any new sources waiting?
- Check recent git activity if in a code repo

### 2. Analyze (silent)

Look for tensions between what the wiki says and what's actually happening:

- Wiki says priority is X, but repo activity suggests Y
- A decision was recorded, but code goes a different direction
- Next steps in wiki are stale or already done
- New sources in raw/untracked/ not yet ingested
- No wiki page exists for this repo/project
- Pages that link to nothing (orphans)
- Recent work not reflected in the wiki

### 3. Suggest

Based on what you found, make concrete suggestions:

**Ingestion:** "There are 3 files in raw/untracked/. Want me to ingest them? I'd update the project page and create source summaries."

**Linking:** "The project page mentions 'auth migration' but there's no decision page for it. Should I create one?"

**Staleness:** "The wiki hasn't been updated in 2 weeks. The repo has 14 new commits. Want me to refresh the project page?"

**Contradictions:** "The wiki says you chose Stripe, but I see PayPal imports in the code. Which is current?"

**Missing context:** "I don't see a wiki page for this project. Want me to create one from what I can see in the repo?"

### 4. Ask 2-5 socratic questions

Based on tensions observed. Always hypothesize before asking:

- Bad: "What project is this?"
- Good: "I think we're on pygmalion based on the repo name. The wiki says next step is API integration. Is that what we're doing today?"

- Bad: "What do you want to do?"
- Good: "The wiki lists 3 next steps. The most recent commit touched the auth module. Are we continuing auth work, or switching to something else?"

### 5. Propose a session plan

2-4 concrete steps based on the answers.

---

## /agent-wiki progress

Mid-session checkpoint. Quick but thorough.

### 1. Observe (silent)

- What has changed since start? (files modified, commits, conversations)
- Re-read the project page (may have changed if multi-agent)
- Run `wikictl query` on the current topic to check for relevant context
- Check if new files appeared in raw/untracked/

### 2. Analyze (silent)

- Are we still on the plan from start?
- Has something emerged that should be captured now, not at finish?
- Are there cross-links to make with existing wiki pages?
- Any contradictions with what the wiki says?

### 3. Suggest

**Scope drift:** "You started on auth migration but you've been working on billing for 30 minutes. Is this intentional, or should we refocus?"

**Capture now:** "You just made a significant architecture decision. Want me to create a decision page now before we forget the reasoning?"

**Cross-linking:** "What you're discovering connects to the 'payment-gateway' project page. Want me to add a cross-reference?"

**Ingestion:** "You pasted a long article in the chat. Want me to save it to raw/ and ingest it?"

**Health check:** "Quick lint shows 2 orphan pages and 1 dead link in the wiki. Want me to fix them?"

### 4. Ask 1-3 focused questions

Shorter than start. Just enough to course-correct:

- "We're halfway through. The main thing done is [X]. Still aiming for [Y] by end of session?"
- "I noticed [Z] isn't working as expected. Should I add it to 'what failed' in the wiki now?"
- "The project page says [old thing]. Based on what just happened, should I update it to [new thing]?"

---

## /agent-wiki finish

End of session. Extract what's durable, write it back.

### 1. Observe (silent)

- What files changed in this session? (git diff, timestamps)
- What was discussed, decided, discovered?
- What failed or was abandoned?
- Run `wikictl lint` — any new issues?
- Check if answers from this session should be saved

### 2. Analyze (silent)

- What knowledge from this session has value beyond today?
- What's a status change vs a decision vs a failure vs a source?
- Are there contradictions with existing wiki content?
- Does the index need updating?

### 3. Suggest write-back

Show exactly what you'd write and where. The user approves before anything is written.

**Project page update:** "I'd update wiki/projects/pygmalion.md: status → 'auth complete, billing in progress'. Add billing API choice to decisions table. Add Redis pub/sub to 'what failed'."

**New decision page:** "You decided to switch from Stripe to PayPal. I'd create wiki/decisions/2026-04-05-paypal-over-stripe.md with the reasoning."

**New source page:** "That API doc you pasted — I'd save it to raw/ and create wiki/sources/2026-04-05-paypal-api-docs.md."

**Answer filing:** "The analysis you asked me to do about pricing — that's worth keeping. I'd save it to outputs/ and reference it from the project page."

**Contradiction resolution:** "The wiki says timeline is 6 weeks. Based on today's meeting it's now 8 weeks. I'd update the project page and mark the old claim as [superseded]."

**Cross-linking:** "The decision about PayPal should link to the billing project page and the payment-gateway source page."

### 4. Ask 2-5 socratic questions

- "The main outcome I see is [X]. Is there anything else worth capturing?"
- "You hit a wall on [Y]. Should I record it as a dead end, or is it still open?"
- "What's the next step for the next session? I'll put it in the project page."
- "Any source material from today I should save to raw/?"

### 5. Execute (after user confirms)

- Update project page
- Create decision/source pages if needed
- Save outputs if needed
- Run `wikictl sync <agent> <op> "<description>"`
- Run `wikictl lint` — confirm wiki is healthy
- Report: "Wiki updated. Next session will have this context."

If the session was trivial (typo fix, quick question): "Nothing substantial to record. Skipping write-back."

---

## How to detect agent-wiki

```bash
command -v wikictl >/dev/null 2>&1 || [ -x ./tools/wikictl ] || [ -x ~/dev/internal/agent-wiki/tools/wikictl ]
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
- `wikictl list` — browse raw sources and wiki pages

## Rules

1. Always observe before asking. Never ask what you can infer.
2. Hypothesize, then confirm. "I think X. Correct?" not "What is X?"
3. Suggest concretely. "I'd write [this] to [here]" not "should I update something?"
4. 2-5 questions per command. Never more.
5. Show write-back proposals before executing. User approves.
6. If the session is trivial, say so and skip.
7. If wikictl is not available, continue normally.
