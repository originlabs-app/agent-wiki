---
name: agent-wiki-finish
description: >
  End a session and write back durable knowledge. Use at the end of
  every work session. Extracts what's worth keeping, proposes wiki
  updates, and executes after user approval.
---

# /agent-wiki-finish

End of session. Extract what's durable, write it back.

## 1. Observe (silent)

- What files changed in this session? (git diff, timestamps)
- What was discussed, decided, discovered?
- What failed or was abandoned?
- Run `wikictl lint` — any new issues?
- Check if answers from this session should be saved

## 2. Analyze (silent)

- What knowledge from this session has value beyond today?
- What's a status change vs a decision vs a failure vs a source?
- Are there contradictions with existing wiki content?
- Does the index need updating?

## 3. Suggest write-back

Show exactly what you'd write and where. The user approves before anything is written.

**Project page update:** "I'd update wiki/projects/pygmalion.md: status → 'auth complete, billing in progress'. Add billing API choice to decisions table. Add Redis pub/sub to 'what failed'."

**New decision page:** "You decided to switch from Stripe to PayPal. I'd create wiki/decisions/2026-04-05-paypal-over-stripe.md with the reasoning."

**New source page:** "That API doc you pasted — I'd save it to raw/ and create wiki/sources/2026-04-05-paypal-api-docs.md."

**New concept page:** "The topic of [X] keeps coming up across multiple sources. I'd create wiki/concepts/X.md to aggregate what we know."

**Answer filing:** "The analysis you asked me to do about pricing — that's worth keeping. I'd save it to outputs/ and reference it from the project page."

**Gap detection:** "Based on everything in the wiki, here are the 2-3 biggest gaps I see in the knowledge base: [X, Y, Z]. Want me to suggest sources to fill them?"

**Cross-source comparison:** "During this session we touched info from source A and source B. They disagree on [topic]. Want me to flag this contradiction in the project page?"

**Contradiction resolution:** "The wiki says timeline is 6 weeks. Based on today's meeting it's now 8 weeks. I'd update the project page and mark the old claim as [superseded]."

**Cross-linking:** "The decision about PayPal should link to the billing project page and the payment-gateway source page."

## 4. Ask 2-5 socratic questions

- "The main outcome I see is [X]. Is there anything else worth capturing?"
- "You hit a wall on [Y]. Should I record it as a dead end, or is it still open?"
- "What's the next step for the next session? I'll put it in the project page."
- "Any source material from today I should save to raw/?"

## 5. Execute (after user confirms)

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

- `/agent-wiki-start` — begin a session, read wiki, get briefed
- `/agent-wiki-ingest` — process a source (URL, text, or file) into the wiki
- `/agent-wiki-progress` — mid-session checkpoint, scope drift detection
- `/agent-wiki-health` — deep audit of wiki (contradictions, orphans, staleness)
