# Example: Business Operations & Client Management

## Scenario

You run a small agency. Clients, proposals, meeting notes, strategy docs — scattered across chat, email, and docs. Decisions get lost. Context doesn't survive between conversations. An agent helping you with client X doesn't know about the meeting you had last week.

## Setup

```
raw/
├── meetings/
│   ├── 2026-03-30-client-alpha-kickoff.md
│   └── 2026-04-02-client-alpha-roadmap.md
├── proposals/
│   └── 2026-03-28-client-alpha-proposal.md
wiki/
├── index.md
├── projects/
│   └── client-alpha.md
├── sources/
│   ├── 2026-03-28-proposal-client-alpha.md
│   ├── 2026-03-30-meeting-kickoff.md
│   └── 2026-04-02-meeting-roadmap.md
└── decisions/
    └── 2026-04-02-revised-timeline.md
```

## Flow

### Day 1: Client onboarding

1. Drop the proposal PDF/markdown into `raw/proposals/`.
2. Agent ingests → creates source page + project page.
3. Project page has: client context, scope, budget, timeline, contacts.

### Day 5: Kickoff meeting

4. Drop meeting transcript into `raw/meetings/`.
5. Agent ingests → creates source page, updates project page with decisions from meeting.
6. Key decisions get their own decision pages.

### Day 10: Follow-up meeting

7. Drop follow-up transcript.
8. Agent ingests → detects contradiction: timeline changed from 6 weeks to 8 weeks.
9. Agent updates project page, marks old timeline as `[superseded]`, creates decision page for the change.

### Day 30: You ask "what's the current status with Client Alpha?"

10. Agent reads `wiki/projects/client-alpha.md`.
11. Has full history: original scope, decisions, changes, current status.
12. Answers with citations to source pages.
13. You didn't re-explain anything. The wiki had it all.

## Agents involved

- Business agent ingests meeting notes and proposals.
- Tech agent reads the project page before coding sessions.
- Both benefit from the same compiled knowledge.

## Key insight

Meeting notes are useless after 2 weeks if nobody synthesizes them. The wiki does the synthesis automatically. Every meeting makes the project page richer.
