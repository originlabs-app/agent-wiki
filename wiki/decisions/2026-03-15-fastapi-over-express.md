---
type: wiki-decision
decision: "Use FastAPI instead of Express.js for the API layer"
date: 2026-03-15
status: active
decided-by: tech-lead
project: acme-api
---

# FastAPI over Express.js

## Context

Starting a new API project. Team has experience with both Python and Node.js. Need to choose the primary framework.

## Decision

Use FastAPI (Python) for the API layer.

## Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| FastAPI (chosen) | Auto-generated OpenAPI docs, type safety with Pydantic, async native, excellent for data-heavy APIs | Smaller ecosystem than Express, fewer middleware options |
| Express.js | Massive ecosystem, team familiarity, easy to hire for | No built-in validation, TypeScript adds complexity, callback patterns |

## Consequences

- All backend code is Python
- Use SQLAlchemy + Alembic for ORM/migrations (natural fit)
- API docs come free via FastAPI's OpenAPI generation
- Team needs to be comfortable with Python async patterns

## Sources

- [[wiki/sources/2026-03-10-api-requirements-v2]]
