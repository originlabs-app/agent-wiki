---
name: agent-wiki
description: >
  Shared knowledge base for LLM Wiki projects. Five commands:
  /agent-wiki start (begin session), /agent-wiki ingest (process a source),
  /agent-wiki progress (mid-session checkpoint),
  /agent-wiki finish (end session), /agent-wiki health (deep audit).
  Each command observes, analyzes, suggests, and asks socratic questions.
  Uses wikictl CLI for wiki operations.
---

# Agent Wiki

Five commands. Each one: observe, analyze, suggest, ask.

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

## /agent-wiki ingest

The user gives you a source — a URL, pasted text, or a file path. You handle the full pipeline.

### 1. Detect the input type

- **URL** — fetch the content (use web extract, agent-browser, curl, or whatever tool is available)
- **Pasted text** — the user pasted content directly in the chat
- **File path** — a file already on disk (may or may not be in raw/)

### 2. Save to raw/untracked/

Save the source as a markdown file in raw/untracked/ with a dated name:
`raw/untracked/YYYY-MM-DD-short-slug.md`

If the source is already in raw/, skip this step.

### 3. Read, analyze, and discuss

- Read the full source content
- Read the relevant existing wiki pages
- Summarize the key takeaways (3-5 bullet points)

Then ask 2-5 socratic questions based on what the source says vs what the wiki knows:

**Project:** "This looks related to [project]. Correct?" (don't ask "which project?" if you can guess)

**Contradictions:** "The source says [X] but the wiki says [Y]. Which is current?"

**Decisions:** "The source describes 3 approaches. We only documented approach 1. Should I add the alternatives to the decisions page?"

**Missing context:** "The source mentions [person/tool/concept] that doesn't exist in the wiki yet. Should I create a page?"

**Emphasis:** "This source covers [A, B, C]. What matters most to you? Or should I compile everything?"

**Staleness:** "The wiki page for this project hasn't been updated since [date]. This source has fresher info. Want me to refresh the whole page?"

Always hypothesize before asking. Confront the source with the wiki. The goal is compilation, not just summarization.

### 4. Compile into the wiki

- Create or update the relevant project page in wiki/projects/
- Create a source summary page in wiki/sources/YYYY-MM-DD-slug.md
- Update wiki/index.md with the new source and any project changes
- Add cross-links to existing wiki pages where relevant
- Flag contradictions with existing wiki content

A single source can touch 5-15 wiki pages. That's normal.

### 5. Move and log

- Run `wikictl ingest "<project>" raw/untracked/<source>` (moves to raw/ingested/)
- Append to wiki/log.md
- Confirm: "Ingested. Project page [X] updated. Source page created. [N] wiki pages touched."

### 6. Suggest next actions

- "There are 2 more files in raw/untracked/. Want me to ingest them too?"
- "This source mentions [topic] which doesn't have a wiki page yet. Create one?"
- "This contradicts what the wiki says about [X]. Want me to update it?"

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

**Save an answer:** "That analysis I just gave you on [topic] — want me to save it to outputs/ so it's not lost in the chat?"

**Knowledge gaps:** "Based on what we've been discussing, the wiki is missing [X]. Want me to flag it or create a stub page?"

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

**Gap detection:** "Based on everything in the wiki, here are the 2-3 biggest gaps I see in the knowledge base: [X, Y, Z]. Want me to suggest sources to fill them?"

**Cross-source comparison:** "During this session we touched info from source A and source B. They disagree on [topic]. Want me to flag this contradiction in the project page?"

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

## /agent-wiki health

Deep audit of the wiki. Not a quick check — a thorough review. Run monthly or when things feel stale.

### 1. Scan the entire wiki (silent)

- Read every page in wiki/projects/, wiki/sources/, wiki/decisions/
- Read wiki/index.md and wiki/log.md
- Run `wikictl lint`
- Check all [[links]] — do they point to real pages?
- Check all source citations — do the raw files exist?

### 2. Report issues by category

**Contradictions:** "Page A says [X] but page B says [Y]. Which is correct?"

**Unsourced claims:** "The project page says [claim] but I can't find a source for it in raw/. Is this verified?"

**Missing pages:** "The term [concept] is mentioned in 4 pages but has no dedicated page. Should I create one?"

**Orphan pages:** "These pages have no inbound links: [list]. Are they still relevant or should they be archived?"

**Stale pages:** "These pages haven't been updated in over 30 days: [list]. Want me to refresh them?"

**Dead links:** "These links point to pages that don't exist: [list]. Should I create them or remove the links?"

**Error propagation:** "I found a claim in [page] that seems to have been copied from [other page] without verification. The original source says something different. Want me to correct both?"

### 3. Suggest improvements

- "Here are 3-5 pages that would fill the biggest gaps in the wiki."
- "These sources in raw/ingested/ were ingested but the wiki pages are thin. Want me to re-compile with more detail?"
- "The index is missing [N] pages. Want me to run heal?"

### 4. Ask before fixing

Show everything you'd change. Get approval. Then execute.

Never silently fix — the whole point of health is surfacing issues for the human to validate.

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
