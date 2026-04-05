---
name: agent-wiki-health
description: >
  Deep audit of the wiki. Use monthly or when things feel stale.
  Scans every page, finds contradictions, orphans, dead links,
  unsourced claims, stale content, and suggests improvements.
---

# /agent-wiki-health

Deep audit of the wiki. Not a quick check — a thorough review. Run monthly or when things feel stale.

## 1. Scan the entire wiki (silent)

- Read every page in wiki/projects/, wiki/sources/, wiki/decisions/
- Read wiki/index.md and wiki/log.md
- Run `wikictl lint`
- Check all [[links]] — do they point to real pages?
- Check all source citations — do the raw files exist?

## 2. Report issues by category

**Contradictions:** "Page A says [X] but page B says [Y]. Which is correct?"

**Unsourced claims:** "The project page says [claim] but I can't find a source for it in raw/. Is this verified?"

**Missing pages:** "The term [concept] is mentioned in 4 pages but has no dedicated page. Should I create one?"

**Orphan pages:** "These pages have no inbound links: [list]. Are they still relevant or should they be archived?"

**Stale pages:** "These pages haven't been updated in over 30 days: [list]. Want me to refresh them?"

**Dead links:** "These links point to pages that don't exist: [list]. Should I create them or remove the links?"

**Error propagation:** "I found a claim in [page] that seems to have been copied from [other page] without verification. The original source says something different. Want me to correct both?"

## 3. Suggest improvements

- "Here are 3-5 pages that would fill the biggest gaps in the wiki."
- "These sources in raw/ingested/ were ingested but the wiki pages are thin. Want me to re-compile with more detail?"
- "The index is missing [N] pages. Want me to run heal?"

## 4. Ask before fixing

Show everything you'd change. Get approval. Then execute.

Never silently fix — the whole point of health is surfacing issues for the human to validate.

---

## How to detect agent-wiki

```bash
[ -x ./tools/wikictl ] || command -v wikictl >/dev/null 2>&1
```

If not available, continue normally. Do not fail.

## wikictl operations

The skill uses these wikictl commands behind the scenes:

- `wikictl status` — what's configured, how many pages
- `wikictl ingest "<project>" <source>` — register + move source to raw/ingested/
- `wikictl query "<terms>"` — search wiki and raw
- `wikictl lint` — detect orphans, dead links, stale pages
- `wikictl heal` — rebuild index from project pages
- `wikictl sync <agent> <op> "<desc>"` — log + lint + status

## Rules

1. Always observe before asking. Never ask what you can infer.
2. Hypothesize, then confirm. "I think X. Correct?" not "What is X?"
3. Suggest concretely. "I'd write [this] to [here]" not "should I update something?"
4. 2-5 questions per command. Never more.
5. Show write-back proposals before executing. User approves.
6. If the session is trivial, say so and skip.
7. If wikictl is not available, continue normally.

---

## Other commands

- `/agent-wiki-start` — begin a session, read wiki, get briefed
- `/agent-wiki-ingest` — process a source (URL, text, or file) into the wiki
- `/agent-wiki-progress` — mid-session checkpoint, scope drift detection
- `/agent-wiki-finish` — end session, write back durable knowledge
