---
name: atlas-progress
description: >
  Mid-session checkpoint. Checks progress, detects scope drift,
  captures emerging knowledge, and does a quick graph + wiki health
  check without ending the session.
---

# /atlas-progress

Mid-session checkpoint. Quick but thorough.

## 1. Observe (silent)

- What has changed since session start? (git diff, file timestamps)
- Run `atlas audit --root .` — any new issues?
- Run `atlas god-nodes --root .` — has the structure shifted?
- Check if new files appeared in raw/untracked/

## 2. Analyze (silent)

- Are we still on the plan from `/atlas-start`?
- Has something emerged that should be captured now?
- Are there cross-links to make with existing wiki pages?
- Does the graph need a refresh? `atlas scan --update .`

## 3. Suggest

**Scope drift:** "You started on auth but you've been working on billing for 30 minutes. Intentional?"

**Capture now:** "You just made a significant architecture decision. Create a decision page now before we forget the reasoning?"

**Cross-linking:** "What you're discovering connects to [[payment-gateway]]. Add a cross-reference?"

**Graph refresh:** "You changed 5 files. Run `atlas scan --update .` to keep the graph current?"

**Save an answer:** "That analysis I gave you — want me to save it to wiki/ so it's not lost in the chat?"

**Knowledge gaps:** "The graph is missing [X]. Create a stub page?"

## 4. Ask 1-3 focused questions

Shorter than start. Just enough to course-correct:

- "Main thing done is [X]. Still aiming for [Y] by end of session?"
- "The graph shows [Z] is now a god node after your changes. Expected?"
- "Wiki page says [old]. Based on what just happened, update to [new]?"

## Rules

1. Always observe before asking.
2. Hypothesize, then confirm.
3. 1-3 questions max (shorter than start).
4. Show proposals before executing.
5. If the session is on track and nothing needs capturing, say so and move on.

---

## Other Atlas skills

- `/atlas-start` — begin a session, get briefed
- `/atlas-scan` — scan a directory into the graph
- `/atlas-query` — query the graph for connections
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-finish` — end session, write back durable knowledge
- `/atlas-health` — deep audit of graph and wiki
