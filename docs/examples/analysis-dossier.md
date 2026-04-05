# Example: Analysis Dossier (Due Diligence / Benchmarking)

## Scenario

You need to evaluate options — tools, vendors, strategies, markets. You read 10-20 sources, compare them, and make a decision. Without a wiki, your analysis lives in one long chat thread that nobody can reuse.

## Setup

```
raw/
├── tools/
│   ├── sage-wiki-readme.md
│   ├── llm-wiki-compiler-readme.md
│   ├── karpathy-gist.md
│   └── hn-discussion.md
wiki/
├── index.md
├── projects/
│   └── wiki-tools-benchmark.md
├── sources/
│   ├── 2026-04-04-sage-wiki.md
│   ├── 2026-04-04-llm-wiki-compiler.md
│   ├── 2026-04-04-karpathy-gist.md
│   └── 2026-04-05-hn-discussion.md
└── decisions/
    └── 2026-04-05-chose-agent-wiki-over-sage.md
```

## Flow

### Phase 1: Gather sources

1. Drop 4 tool READMEs / articles into `raw/tools/`.
2. Agent ingests each one → 4 source pages in `wiki/sources/`.
3. Agent creates `wiki/projects/wiki-tools-benchmark.md` with:
   - Comparison table (features, maturity, multi-agent support, install complexity).
   - Strengths/weaknesses per tool.
   - Open questions.

### Phase 2: Deep dive

4. You ask: "Which tool supports multi-agent best?"
5. Agent reads source pages → synthesizes answer → files comparison back into project page.
6. You ask: "What are the risks of sage-wiki?"
7. Agent answers with citations → adds risk section to project page.

### Phase 3: Decision

8. You decide. Agent creates `wiki/decisions/2026-04-05-chose-agent-wiki-over-sage.md`.
9. Decision page links to all source pages that informed it.
10. Project page updated: status → "decided", decision linked.

### Phase 4: Reuse

11. Three months later, someone asks "why did we build our own?"
12. Agent reads decision page → full rationale with sources.
13. No archaeology needed. The wiki has the complete trail.

## Agents involved

- Research agent does the initial ingestion and comparison.
- Any agent can later query the analysis.
- The decision page is the permanent record.

## Key insight

Analysis is expensive. Without the wiki, you redo it every time someone asks "why did we choose X?" With the wiki, the analysis compounds — it's done once, queryable forever.
