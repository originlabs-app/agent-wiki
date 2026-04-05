---
name: agent-wiki
description: >
  Shared knowledge base for multi-agent workflows. Three commands:
  /agent-wiki start (brief before work), /agent-wiki check (status mid-session),
  /agent-wiki finish (debrief after work). Uses wikictl CLI for ingest, query,
  heal, sync. Activate when starting a session, checking progress, or wrapping up.
---

# Agent Wiki

A persistent, compounding knowledge base shared across agents and sessions.

## Commands

### /agent-wiki start

Socratic brief at the beginning of a session. Don't ask generic questions — observe, hypothesize, then ask.

**Step 1: Observe (silent — don't ask the user)**

- Detect current directory, repo name, git branch, recently modified files.
- Run `wikictl status` (try `--instance` if configured, fall back to local).
- Read `wiki/index.md`.
- Find the project page matching the current repo/directory.
- Read the project page: status, decisions, failures, next steps.
- Check `wiki/log.md` for recent operations.
- Check if `raw/` has unprocessed sources.

**Step 2: Analyze (silent)**

- Compare repo state with wiki state. Look for tensions:
  - Wiki says priority is X, but repo activity suggests Y.
  - A decision was recorded, but code goes a different direction.
  - Next steps in wiki are stale or already done.
  - New sources in raw/ not yet reflected in wiki.
  - No wiki page exists for this repo.

**Step 3: Brief the user**

Present what you found:
- "Here's what the wiki says about this project: [summary]"
- "Last session: [who did what, when]"
- "Current priority according to wiki: [X]"

**Step 4: Ask 2-5 socratic questions**

Based on tensions observed. Examples:

- "The wiki says the next step is auth migration, but I see recent commits on billing. Are we pivoting or is this a side task?"
- "There's a source in raw/ from yesterday that isn't reflected in the project page. Should I ingest it first?"
- "The wiki hasn't been updated in 3 weeks. Want me to refresh it from the current repo state before we start?"
- "I don't see a wiki page for this repo. Should I create one, or link this to an existing project?"
- "The wiki lists 3 next steps. Which one are we tackling this session?"

**Rules:**
- 2 questions minimum, 5 maximum.
- No redundant questions.
- If you can infer the answer from context, propose a hypothesis instead of asking blindly.
- Bad: "What project?" — Good: "I think we're on pygmalion. Confirm?"

**Step 5: Propose a short session plan**

Based on answers, propose 2-4 concrete steps for this session.

---

### /agent-wiki check

Mid-session status check. Quick — don't interrupt the flow.

**What to do:**

1. Re-read the project page (may have changed if multi-agent).
2. Compare with work done since start.
3. Show: "Here's what we've done, here's what remains."
4. Detect scope drift: "You were working on X, now you're on Y — intentional?"
5. Suggest logical next step.
6. Check for new tensions (new sources, stale info, contradictions).

**Keep it short.** This is a 30-second checkpoint, not a full brief.

---

### /agent-wiki finish

Debrief at the end of a session. Extract what's durable, write it back.

**Step 1: Observe (silent)**

- What files were modified in this session (git diff or file timestamps).
- What was discussed / decided.
- What failed or was abandoned.

**Step 2: Ask 2-5 targeted questions**

- "The main change I see is [X]. Is that the key outcome, or is there more?"
- "You made a decision about [Y]. Should I record it as a formal decision page?"
- "I noticed [Z] didn't work. Should I add it to 'what failed' in the project page?"
- "What's the logical next step for the next session?"
- "Anything else worth remembering that isn't in the code?"

**Rules:**
- Same as start: 2-5 questions, no redundancy, hypothesize before asking.
- If the session was trivial (typo fix, small config change), say "Nothing substantial to record" and skip.

**Step 3: Propose write-back**

Show exactly what you'll write and where:
- "I'll update wiki/projects/pygmalion.md: status → [new status], add decision about [X], add [Y] to what failed."
- "I'll create wiki/decisions/2026-04-05-switched-to-stripe.md."
- "I'll append to wiki/log.md."

Ask: "OK to write these updates?"

**Step 4: Execute**

- Update project page.
- Create decision/source pages if needed.
- Run `wikictl sync <agent> <op> "<description>"`.
- Confirm: "Wiki updated. Next session will have this context."

---

## Detect

Check if agent-wiki is available:

```bash
command -v wikictl >/dev/null 2>&1 && echo "available" || \
  ([ -x ./cli/wikictl ] && echo "available" || \
  ([ -x ~/dev/internal/agent-wiki/cli/wikictl ] && echo "available at ~/dev/internal/agent-wiki/cli/wikictl" || \
  echo "not configured"))
```

If not available, continue normally. Do not fail. Do not ask the user to install anything.

## Instance resolution

```bash
# Try instance mode first
wikictl --instance origin-labs status 2>/dev/null || \
  wikictl status 2>/dev/null || \
  echo "no wiki configured"
```

If multiple instances exist, ask: "I see instances [X, Y]. Which one for this session?"
If one instance exists, use it by default.
If no instance exists, use local wiki/ in the repo.

## wikictl reference

| Command | What it does |
|---------|-------------|
| `wikictl status` | Health summary |
| `wikictl ingest "<project>" <source>` | Register + compile a source |
| `wikictl query "<terms>"` | Search wiki and raw |
| `wikictl heal` | Rebuild index |
| `wikictl sync <agent> <op> "<desc>"` | End-of-session write-back |
| `wikictl lint` | Structure check |
| `wikictl log <agent> <op> "<desc>"` | Append to log |

## Page types

| Type | Location | When to create |
|------|----------|----------------|
| Project | `wiki/projects/{slug}.md` | One per project |
| Source | `wiki/sources/{date}-{slug}.md` | When ingesting a substantial source |
| Decision | `wiki/decisions/{date}-{slug}.md` | When a significant decision is made |

## Confidence markers

- `[confirmed]` — verified by human or multiple sources
- `[hypothesis]` — agent analysis, not yet verified
- `[stale]` — older than 14 days without refresh

## Rules

1. `raw/` is immutable. Never edit source files.
2. `wiki/` is the compiled layer. Keep it current.
3. Write back after every meaningful session.
4. Cite sources when adding facts.
5. When contradicting existing content, mark old claims as `[superseded]`.
6. If wikictl is not available, continue normally.
7. Don't ask questions you can answer from context. Hypothesize, then confirm.
