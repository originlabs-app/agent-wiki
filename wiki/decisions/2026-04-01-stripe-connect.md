---
type: wiki-decision
decision: "Switch to Stripe Connect for payouts"
date: 2026-04-01
status: active
decided-by: ""
project: acme-api
---

# Stripe Connect for Payouts

## Context

Needed a payout solution for the Acme API marketplace.

## Decision

Switched to Stripe Connect for handling payouts to sellers.

## Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| Stripe Connect (chosen) | Mature marketplace support, handles compliance | Platform fees |
| Manual bank transfers | Full control | Complex compliance, slow |

## Consequences

- Payouts handled via Stripe Connect API
- Marketplace compliance delegated to Stripe

## Sources

- [[wiki/sources/2026-04-01-client-meeting-roadmap]]
- [[wiki/projects/acme-api]]
