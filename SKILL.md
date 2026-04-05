---
name: agent-wiki
description: >
  Shared knowledge base across agents and sessions. Two commands:
  /agent-wiki start (brief before work), /agent-wiki finish (debrief after work).
  Uses wikictl CLI for wiki operations.
---

# Agent Wiki

A persistent, compounding knowledge base shared across agents and sessions.

## Commands

### /agent-wiki start

Run at the beginning of every session.

1. **Observe** (silent — don't ask the user yet)
   - Run `wikictl status`.
   - Read `wiki/index.md` and the project page for the current repo.
   - Check `wiki/log.md` for recent activity.
   - Check `raw/` for unprocessed sources.

2. **Analyze** (silent)
   - Compare repo state with wiki state. Look for tensions:
     stale next-steps, contradictions between wiki and code, missing pages.

3. **Brief the user**
   - Summarize what the wiki says about this project, last session, current priority.

4. **Ask 2–5 Socratic questions**
   - Based on tensions you found. Hypothesize before asking.
   - Bad: "What project?" — Good: "Looks like we're on X. Confirm?"

5. **Propose a session plan** — 2–4 concrete steps.

---

### /agent-wiki finish

Run at the end of every session.

1. **Observe** (silent)
   - What changed this session (git diff, files modified, decisions made, failures).

2. **Ask 2–5 targeted questions**
   - "The main outcome was X — anything else?"
   - "Should I record the decision about Y?"
   - "What's the next step for the next session?"

3. **Propose write-back** — show exactly what you'll write and where.
   Ask: "OK to write these updates?"

4. **Execute**
   - Update project page, create decision/source pages if needed.
   - Run `wikictl sync <agent> <op> "<description>"`.
   - Confirm: "Wiki updated."

---

## Detect

```bash
command -v wikictl >/dev/null 2>&1 || [ -x ./cli/wikictl ] || [ -x ~/dev/internal/agent-wiki/cli/wikictl ]
```

If not available, continue normally. Don't fail. Don't ask to install.

## Rules

1. `raw/` is immutable. Never edit source files.
2. `wiki/` is the compiled layer. Keep it current.
3. Write back after every meaningful session.
4. Don't ask questions you can answer from context.
