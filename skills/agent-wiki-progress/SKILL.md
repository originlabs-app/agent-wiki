---
name: agent-wiki-progress
description: >
  Mid-session checkpoint. Use when you want to check progress, detect
  scope drift, capture emerging knowledge, or do a quick wiki health
  check without ending the session.
---

# /agent-wiki-progress

Mid-session checkpoint. Quick but thorough.

## 1. Observe (silent)

- What has changed since start? (files modified, commits, conversations)
- Re-read the project page (may have changed if multi-agent)
- Run `wikictl query` on the current topic to check for relevant context
- Check if new files appeared in raw/untracked/

## 2. Analyze (silent)

- Are we still on the plan from start?
- Has something emerged that should be captured now, not at finish?
- Are there cross-links to make with existing wiki pages?
- Any contradictions with what the wiki says?

## 3. Suggest

**Scope drift:** "You started on auth migration but you've been working on billing for 30 minutes. Is this intentional, or should we refocus?"

**Capture now:** "You just made a significant architecture decision. Want me to create a decision page now before we forget the reasoning?"

**Cross-linking:** "What you're discovering connects to the 'payment-gateway' project page. Want me to add a cross-reference?"

**Ingestion:** "You pasted a long article in the chat. Want me to save it to raw/ and ingest it?"

**Health check:** "Quick lint shows 2 orphan pages and 1 dead link in the wiki. Want me to fix them?"

**Save an answer:** "That analysis I just gave you on [topic] — want me to save it to outputs/ so it's not lost in the chat? I can also file it into the wiki with `wikictl file-back <project> \"<title>\"` so it's indexed and logged automatically."

**Knowledge gaps:** "Based on what we've been discussing, the wiki is missing [X]. Want me to flag it or create a stub page?"

**Concept page:** "The topic [X] spans multiple sources now. Want me to create a concept page in wiki/concepts/ to tie them together?"

**Deep dive:** "You asked a complex question earlier. Want me to do a multi-step deep dive — read the concepts, then the sources, then the raw material?"

**Render outputs:** "Want me to render what we've found so far as a slide deck, chart, or report in outputs/?"

## 4. Ask 1-3 focused questions

Shorter than start. Just enough to course-correct:

- "We're halfway through. The main thing done is [X]. Still aiming for [Y] by end of session?"
- "I noticed [Z] isn't working as expected. Should I add it to 'what failed' in the wiki now?"
- "The project page says [old thing]. Based on what just happened, should I update it to [new thing]?"

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

- `/agent-wiki-start` — begin a session, read wiki, get briefed
- `/agent-wiki-ingest` — process a source (URL, text, or file) into the wiki
- `/agent-wiki-finish` — end session, write back durable knowledge
- `/agent-wiki-health` — deep audit of wiki (contradictions, orphans, staleness)
