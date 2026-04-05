---
type: wiki-decision
decision: "Separate scraping and scoring into two independent bots"
date: 2026-04-02
status: active
decided-by: Pierre + Emile
project: bsacopilot
---

# Two-Bot Architecture for AO Monitoring

## Context

BSACopilot needs automated public tender monitoring. Initial approach was a single monolithic bot. After first scraping tests, performance and maintainability concerns led to a redesign.

## Decision

Split into two independent bots:
1. **Scraping bot** — fetches AO from BOAMP + Nukema, injects into "Identified" column
2. **Scoring bot** — scores identified AO against client profiles (50/50 business-fit + geography)

## Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| Two separate bots (chosen) | Independent scaling, easier debugging, can run on different schedules | More infrastructure, coordination overhead |
| Single monolithic bot | Simpler deployment, single codebase | Hard to debug, can't scale scraping independently from scoring |

## Consequences

- Scraping bot can run more frequently without re-scoring everything
- Scoring can be improved independently (model, criteria) without touching scraping
- Need a shared data layer (Supabase) between the two bots

## Sources

- [[wiki/sources/2026-04-02-visio-emile-roadmap]]
