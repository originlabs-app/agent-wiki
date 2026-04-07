---
name: atlas-finish
description: >
  End a session and write back durable knowledge. Extracts what's
  worth keeping, proposes wiki updates, syncs the graph, and
  executes after user approval.
---

# /atlas-finish

End of session. Extract what's durable, write it back.

## 1. Observe (silent)

- What files changed in this session? (git diff, timestamps)
- What was discussed, decided, discovered?
- What failed or was abandoned?
- Run `atlas audit --root .` — any new issues from this session?
- Run `atlas scan --update .` to capture code changes in the graph

## 2. Analyze (silent)

- What knowledge from this session has value beyond today?
- Status change vs decision vs failure vs source?
- Contradictions with existing wiki content?
- Does the graph index need updating?
- Did the graph structure change significantly? (`atlas god-nodes`, `atlas surprises`)

## 3. Suggest write-back

Show exactly what you'd write and where. User approves before anything is written.

**Project page update:** "I'd update wiki/projects/X.md: status -> 'auth complete, billing in progress'."

**New decision page:** "You decided to switch from Stripe to PayPal. I'd create wiki/decisions/YYYY-MM-DD-paypal-over-stripe.md."

**New source page:** "That API doc you pasted — I'd save to raw/ and create wiki/sources/YYYY-MM-DD-slug.md."

**New concept page:** "The topic [X] spans multiple pages now. I'd create wiki/concepts/X.md."

**Gap detection:** "Based on everything in the wiki, the 2-3 biggest gaps: [X, Y, Z]."

**Contradiction resolution:** "Wiki says timeline is 6 weeks. Based on today it's 8 weeks. Update?"

**Graph sync:** "After writing wiki updates, I'd run `atlas scan --update .` to sync the graph."

## 4. Ask 2-5 socratic questions

- "Main outcome I see is [X]. Anything else worth capturing?"
- "You hit a wall on [Y]. Record as dead end, or still open?"
- "Next step for next session? I'll put it in the project page."
- "Any source material from today I should save to raw/?"

## 5. Execute (after user confirms)

1. Update wiki pages as proposed
2. Create new pages if needed
3. Run `atlas scan --update .` to sync graph
4. Run `atlas audit --root .` — confirm wiki is healthy
5. Report: "Wiki updated. Graph synced. Next session will have this context."

If the session was trivial: "Nothing substantial to record. Skipping write-back."

## Rules

1. Always observe before asking.
2. Hypothesize, then confirm.
3. Suggest concretely. Show exact file paths and content.
4. 2-5 questions max.
5. Show write-back proposals before executing. User approves.
6. Always sync the graph after wiki writes.
7. If trivial, say so and skip.

---

## Other Atlas skills

- `/atlas-start` — begin a session, get briefed
- `/atlas-scan` — scan a directory into the graph
- `/atlas-query` — query the graph for connections
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-progress` — mid-session checkpoint
- `/atlas-health` — deep audit of graph and wiki
