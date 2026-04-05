---
type: wiki-concept
concept: REST API Design
status: active
updated: 2026-04-05
updated_by: claude
confidence: medium
---

# REST API Design

## Summary

Patterns and conventions for building REST APIs. Covers endpoint design, authentication, error handling, and versioning.

## Key ideas

- Resource-based URLs (/users, /users/{id})
- HTTP methods map to CRUD (GET=read, POST=create, PUT=update, DELETE=delete)
- JWT or API key authentication for stateless auth
- Consistent error response format with status codes
- Version via URL prefix (/v1/) or headers

## Related projects

- [[wiki/projects/acme-api]] — uses FastAPI with JWT + API key auth

## Related decisions

- [[wiki/decisions/2026-03-15-fastapi-over-express]] — framework choice for REST API

## Related sources

- [[wiki/sources/2026-03-10-api-requirements-v2]] — requirements that shaped the API design
