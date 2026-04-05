# Example: Long Research Project

## Scenario

You're tracking a fast-moving domain (AI agents, fintech regulation, biotech trends) over weeks or months. Sources pile up. You need cumulative synthesis, not scattered bookmarks.

## Setup

```
raw/
├── articles/
│   ├── 2026-04-01-agent-frameworks-survey.md
│   ├── 2026-04-03-karpathy-llm-wiki.md
│   └── 2026-04-05-multi-agent-orchestration.md
wiki/
├── index.md
├── projects/
│   └── agentic-tools-research.md
├── sources/
│   ├── 2026-04-01-agent-frameworks-survey.md
│   └── 2026-04-03-karpathy-llm-wiki.md
└── decisions/
```

## Flow

### Week 1: First sources

1. Drop 3 articles into `raw/articles/`.
2. Tell the agent: "Ingest these sources for my agentic tools research."
3. Agent reads each article, creates source pages in `wiki/sources/`.
4. Agent creates `wiki/projects/agentic-tools-research.md` with:
   - Key frameworks identified
   - Comparison table
   - Open questions
5. `wiki/index.md` updated. `wiki/log.md` gets 3 entries.

### Week 2: More sources + queries

6. Drop 2 more articles.
7. Agent ingests — updates existing project page, adds new source pages.
8. You ask: "Which framework handles multi-agent best?"
9. Agent reads wiki, synthesizes answer with citations.
10. Answer is valuable → agent files it back as a section in the project page.

### Week 4: Lint

11. Run lint. Agent finds:
    - One source contradicts an earlier claim about token limits.
    - Two concepts mentioned repeatedly but have no dedicated page.
    - One source page has no inbound links.
12. Agent fixes: updates contradicted claim with `[superseded]`, creates missing pages, links orphan.

## Agents involved

Any agent that can read/write markdown and call `wikictl`. Works with Claude Code, Codex, Cursor, or Hermes.

## Result after 1 month

A wiki with ~15-20 pages covering the domain. Any new agent session starts by reading the project page and has full context in 30 seconds. No re-reading of original articles needed.
