---
type: wiki-index
updated: 2026-04-06
maintained-by: [agent-wiki]
---

# Wiki Index

Read this file first.

## Purpose

This is the compiled knowledge layer. Sources live in `raw/`, project-specific
summaries live in `wiki/projects/`, and the log records every meaningful
operation.

## How to use

- Start with the relevant project page.
- Expand to raw sources only when needed.
- Keep project summaries short and current.
- Write back after each meaningful session.

## Projects

| Project | Status | Updated | Wiki | Summary |
|--------|--------|---------|------|---------|
| Acme API | active | 2026-04-05 | [[wiki/projects/acme-api]] | REST API for Acme Corp's inventory management system. FastAPI + PostgreSQL. Handles product catalog, stock levels, and order fulfillment. |

## Sources

| Source | Date | Wiki | Summary |
|--------|------|------|---------|
| API Requirements v2 | 2026-03-10 | [[wiki/sources/2026-03-10-api-requirements-v2]] | See page |
| Client meeting — Q2 roadmap review | 2026-04-01 | [[wiki/sources/2026-04-01-client-meeting-roadmap]] | See page |

## Decisions

| Decision | Date | Wiki | Summary |
|----------|------|------|---------|
| Use FastAPI instead of Express.js for the API layer | 2026-03-15 | [[wiki/decisions/2026-03-15-fastapi-over-express]] | See page |
| Switch to Stripe Connect for payouts | 2026-04-01 | [[wiki/decisions/2026-04-01-stripe-connect]] | See page |

## Concepts

| Concept | Updated | Wiki | Summary |
|---------|---------|------|---------|
| REST API Design | 2026-04-05 | [[wiki/concepts/rest-api-design]] | Patterns and conventions for building REST APIs. Covers endpoint design, authentication, error handling, and versioning. |

## References

- [[wiki/log]]
- [[wiki/projects/_template]]
- [[wiki/sources/_template]]
- [[wiki/decisions/_template]]
