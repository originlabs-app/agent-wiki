---
type: wiki-page
project: BSACopilot
status: active
updated: 2026-04-05
updated_by: anna
repo: "~/dev/clients/BSA_COPILOT_PRODUCTION"
---

# BSACopilot — Overview

## Summary

SaaS platform for public tender monitoring. Origin Labs builds the software + AI bots (scraping, scoring) for BSACopilot (client: Emile Pinson).

## Current status

- **Platform**: production (Supabase staging + prod)
- **Tender monitoring bot**: operational via Hermes skill (scrapes BOAMP + Nukema, scores with Claude, 2x/week)
- **Monitoring frontend**: ready, prod pipeline not connected yet
- **Scoring**: 50/50 business-fit + geography, categories TRAVAUX+SERVICES

## Tech stack

- Frontend: Next.js (Vercel)
- Backend: Supabase
- Scraping: Hermes agent skill (Marc)
- Scoring: Claude via Claude Code Max Pro

## Decisions

| Date | Decision | Source |
|------|----------|--------|
| 2026-04-02 | 2-bot architecture (scraping + scoring separated) | [[wiki/sources/2026-04-02-visio-emile-roadmap]] |
| 2026-04-02 | "Identified" column + GoNoGo delegated to Achille | same |
| 2026-03-30 | Paul's manual process encoded as Claude Code skill | [[wiki/sources/2026-03-30-visio-paul-nukema]] |

## What failed

- Nukema scraping v1/v2: unstable, replaced by v3 [confirmed]
- Current gap: scraping→prod pipeline not connected [hypothesis]

## Next steps

- [ ] Deploy multi-source scraping bot → inject into "Identified" column
- [ ] Handle 12-13 platform feature requests/bugs
- [ ] Connect monitoring pipeline to production
- [ ] Transfer GoNoGo notification specs to Achille

## Sources

- [[wiki/sources/2026-04-02-visio-emile-roadmap]]
- [[wiki/sources/2026-03-30-visio-paul-nukema]]
