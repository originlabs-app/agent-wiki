---
name: agent-wiki-health
description: >
  Deep audit of the wiki and repo-vs-wiki gap assessment. Use weekly or when things feel stale.
  Scans every page, finds contradictions, orphans, dead links,
  unsourced claims, stale content, repo drift, and suggests improvements.
---

# /agent-wiki-health

Deep audit of the wiki. Not a quick check — a thorough review. Run weekly or when things feel stale.

## 1. Scan the entire wiki (silent)

- Read every page in wiki/projects/, wiki/sources/, wiki/decisions/, wiki/concepts/
- Read wiki/index.md and wiki/log.md
- Run `wikictl lint`
- Check all [[links]] — do they point to real pages?
- Check all source citations — do the raw files exist?
- If in a code repo (Mode 2 / second-brain), also scan the repo:
  - Check `git log` for recent commits
  - Check what files changed recently
  - Compare repo state with wiki project page

## 2. Report issues by category

**Contradictions:** "Page A says [X] but page B says [Y]. Which is correct?"

**Unsourced claims:** "The project page says [claim] but I can't find a source for it in raw/. Is this verified?"

**Missing pages:** "The term [concept] is mentioned in 4 pages but has no dedicated page. Should I create one?"

**Orphan pages:** "These pages have no inbound links: [list]. Are they still relevant or should they be archived?"

**Stale pages:** "These pages haven't been updated in over 30 days: [list]. Want me to refresh them?"

**Dead links:** "These links point to pages that don't exist: [list]. Should I create them or remove the links?"

**Low confidence pages:** "These pages are rated low or haven't been refreshed in 30+ days: [list]. Want me to find corroborating sources to upgrade them?"

**Repo vs wiki drift:** "The repo has had 14 commits since the wiki was last updated. Key changes: [list]. The wiki still says [old state]. Want me to refresh the project page?"

**New repo files not in wiki:** "These files appeared in the repo but aren't reflected in the wiki: [list]. Should I ingest them?"

**Error propagation:** "I found a claim in [page] that seems to have been copied from [other page] without verification. The original source says something different. Want me to correct both?"

## 3. Suggest improvements

- "Here are 3-5 pages that would fill the biggest gaps in the wiki."
- "These sources in raw/ingested/ were ingested but the wiki pages are thin. Want me to re-compile with more detail?"
- "The index is missing [N] pages. Want me to run heal?"

**Fill gaps via web search:** "The wiki mentions [topic] but has no dedicated page and no source for it. Want me to search the web, find a good source, save it to raw/, and compile it into the wiki?"

**Suggest new sources:** "Based on the gaps I found, here are 3 searches that would strengthen the wiki: [search 1], [search 2], [search 3]. Want me to run them?"

This aligns with Karpathy's 'fills gaps via web search' in the Lint + Heal support layer.

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
- `wikictl file-back <project> "<title>" [--type source|decision|concept]` — create wiki page + update index + log

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
