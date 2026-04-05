# Example: Living Software Repository

## Scenario

Multiple agents work on the same codebase across sessions. Architecture decisions, failed approaches, and current state need to survive between sessions. Today's Codex session shouldn't redo what yesterday's Claude Code session already figured out.

## Setup

```
raw/
├── specs/
│   └── api-requirements-v2.md
wiki/
├── index.md
├── projects/
│   └── payment-gateway.md
├── sources/
│   └── 2026-04-01-api-requirements-v2.md
└── decisions/
    ├── 2026-03-15-chose-fastapi-over-express.md
    └── 2026-04-01-switched-to-stripe-connect.md
```

## Flow

### Session 1: Claude Code — initial architecture

1. Claude Code reads `wiki/index.md` → `wiki/projects/payment-gateway.md`.
2. Page is empty (new project). Claude Code reads `raw/specs/api-requirements-v2.md`.
3. Claude Code designs the architecture, writes code.
4. End of session:
   - Updates `wiki/projects/payment-gateway.md` (stack, status, decisions).
   - Creates `wiki/decisions/2026-03-15-chose-fastapi-over-express.md`.
   - Runs `wikictl sync claude session-1 "Initial architecture + FastAPI decision"`.

### Session 2: Codex — payment integration

5. Codex reads `wiki/projects/payment-gateway.md` → knows the stack is FastAPI, knows the architecture.
6. Codex implements Stripe Connect integration.
7. Hits a problem: Stripe Connect doesn't support the planned flow.
8. End of session:
   - Updates project page: adds failure to "What failed" section.
   - Creates `wiki/decisions/2026-04-01-switched-to-stripe-connect.md`.
   - Runs `wikictl sync codex session-2 "Stripe integration + flow pivot"`.

### Session 3: Claude Code — picks up where Codex left off

9. Claude Code reads the project page → sees the Stripe failure and the pivot decision.
10. Doesn't retry the old approach. Starts from the new decision.
11. This is the compounding effect: knowledge from session 2 saved session 3 from a dead end.

## Agents involved

- Claude Code and Codex alternate on the same repo.
- Both read the same wiki. Both write back.
- The wiki is the handoff mechanism.

## Key insight

Without the wiki, session 3 would re-discover the Stripe limitation. With it, the agent reads one page and knows what was tried, what failed, and what to do instead.
