# Atlas — Product Vision

> Knowledge engine for AI agents. Scan anything, know everything, remember forever.

## The Problem

AI agents are amnesiac. Every session starts from zero. They don't know your codebase deeply, can't answer "why was this decision made?", and burn context windows rereading the same files. Context window stuffing is a band-aid, not a solution.

## What Atlas Does

Atlas gives agents a **persistent, structured memory** that compounds over time.

1. **Point it at a repo** — it scans AST + semantics, builds a knowledge graph, generates wiki pages
2. **Feed it docs, PRs, decisions** — it ingests, links, cross-references
3. **Ask it anything** — your agent queries Atlas instead of rereading the entire codebase
4. **It compounds** — every ingestion enriches the graph, making the next query richer

## How It's Different

| | RAG (basic) | Atlas |
|---|---|---|
| Structure | Flat chunks | Typed knowledge graph with relationships |
| Querying | Cosine similarity | Graph traversal + semantic search |
| Connections | None | Bidirectional: code ↔ decisions ↔ docs ↔ concepts |
| Understanding | Text matching | Structure + intent + relationships |
| Growth | Static index | Compounds with every ingestion |

## The Stack at Origin Labs

- **ARA** = execution account for agents (infrastructure, billing, routing)
- **Atlas** = knowledge/memory engine for agents (the brain)
- **Agent-wiki** = the open-source core (Karpathy wiki pattern)

## Target Users

Phase 1: **Us** (Origin Labs). Dogfood hard. Atlas powers our own agents — Anna, Marc, project-specific agents. We feel the pain first.

Phase 2: **Teams building autonomous AI agents** who need their agents to actually understand large, evolving codebases and project context.

Phase 3: **Open-source community**. agent-wiki is the base. Atlas is the enriched version with graph engine, AST scanner, MCP server.

## Business Model

- Open-source core (agent-wiki) — builds trust, adoption, community
- Atlas = enriched version: graph engine, AST scanner, semantic analysis, MCP server
- Plug-and-play for any agent framework (Claude, GPT, open-source)
- Sell to teams building autonomous agents who need them to not be dumb

## The Dream Flow

```
Developer points Atlas at a repo
        ↓
Atlas scans codebase (AST + semantic extraction)
        ↓
Knowledge graph built: modules, functions, types, decisions, patterns
        ↓
Wiki pages auto-generated with cross-references
        ↓
Developer asks agent: "Why did we use PostgreSQL instead of SQLite?"
        ↓
Agent queries Atlas → finds decision doc + relevant code + context
        ↓
Developer feeds a new RFC into Atlas
        ↓
Graph updates, links form, knowledge compounds
        ↓
Next agent session starts → it already knows everything
```

## What "Done" Looks Like

### MVP (v0.1)
- [ ] Scan a Python/JS repo → knowledge graph → wiki pages
- [ ] Query the graph (natural language → structured answer)
- [ ] Ingest URLs, PDFs, markdown → enrich graph
- [ ] MCP server so any agent can query Atlas
- [ ] Health check: detect orphans, contradictions, stale pages

### v0.2 — Dogfood
- [ ] Anna + Marc use Atlas as primary knowledge source for Origin Labs projects
- [ ] Git hooks: auto-scan on commit
- [ ] Dashboard: graph stats, coverage, health

### v0.3 — Open Source
- [ ] Clean API surface, documented, tested
- [ ] agent-wiki = OSS core, Atlas = enriched
- [ ] Community can extend scanners, storage backends

## Guiding Principles

1. **Knowledge compounds** — every ingestion makes the next query better
2. **Structure over search** — a graph beats a bag of chunks
3. **Dogfood first** — we build it because we need it
4. **Open core** — agent-wiki is OSS, Atlas is the product
5. **Radical simplicity** — no feature that hasn't been tested E2E
6. **Agents are the users** — optimize for agent consumption, not human browsing

## Success Metrics

- Agent query accuracy (can it answer "why?" questions about the codebase?)
- Graph coverage (% of codebase nodes linked to decisions/docs)
- Ingestion velocity (time from new source → graph enrichment)
- Dogfood intensity (how often do Anna/Marc query Atlas vs raw files)
- Test count (quality proxy — must grow every sprint)
