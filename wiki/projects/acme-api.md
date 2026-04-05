---
type: wiki-page
project: Acme API
status: active
updated: 2026-04-05
updated_by: claude
repo: ""
---

# Acme API — Overview

## Summary

REST API for Acme Corp's inventory management system. FastAPI + PostgreSQL. Handles product catalog, stock levels, and order fulfillment.

## Current status

- Core CRUD endpoints: done
- Auth (JWT + API keys): done
- Webhook notifications: in progress
- Dashboard: not started

## Tech stack

- Backend: FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL 16
- Cache: Redis
- Deploy: Railway

## Decisions

| Date | Decision | Source |
|------|----------|--------|
| 2026-03-15 | Chose FastAPI over Express | [[wiki/decisions/2026-03-15-fastapi-over-express]] |
| 2026-04-01 | Switched to Stripe Connect for payouts | [[wiki/decisions/2026-04-01-stripe-connect]] |

## What failed

- First auth approach with session cookies: conflicted with mobile client requirements [confirmed]
- Attempted Redis pub/sub for webhooks: too complex for the scale, switched to simple HTTP callbacks [confirmed]

## Next steps

- [ ] Finish webhook notification system
- [ ] Add rate limiting middleware
- [ ] Start dashboard frontend

## Sources

- [[wiki/sources/2026-03-10-api-requirements-v2]]
- [[wiki/sources/2026-04-01-client-meeting-roadmap]]
