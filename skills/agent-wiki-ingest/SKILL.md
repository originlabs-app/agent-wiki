---
name: agent-wiki-ingest
description: >
  Process a source into the wiki. Use when the user gives you a URL,
  pasted text, or file path to ingest. Saves to raw/, compiles into
  wiki pages, cross-links, and flags contradictions.
---

# /agent-wiki-ingest

The user gives you a source — a URL, pasted text, or a file path. You handle the full pipeline.

## 1. Detect the input type

- **URL** — fetch the content (use web extract, agent-browser, curl, or whatever tool is available)
- **Pasted text** — the user pasted content directly in the chat
- **File path** — a file already on disk (may or may not be in raw/)

## 2. Save to raw/untracked/

Save the source as a markdown file in raw/untracked/ with a dated name:
`raw/untracked/YYYY-MM-DD-short-slug.md`

If the source is already in raw/, skip this step.

## 3. Read, analyze, and discuss

- Read the full source content
- Read the relevant existing wiki pages
- Summarize the key takeaways (3-5 bullet points)

Then ask 2-5 socratic questions based on what the source says vs what the wiki knows:

**Project:** "This looks related to [project]. Correct?" (don't ask "which project?" if you can guess)

**Contradictions:** "The source says [X] but the wiki says [Y]. Which is current?"

**Decisions:** "The source describes 3 approaches. We only documented approach 1. Should I add the alternatives to the decisions page?"

**Missing context:** "The source mentions [person/tool/concept] that doesn't exist in the wiki yet. Should I create a page?"

**Emphasis:** "This source covers [A, B, C]. What matters most to you? Or should I compile everything?"

**Staleness:** "The wiki page for this project hasn't been updated since [date]. This source has fresher info. Want me to refresh the whole page?"

Always hypothesize before asking. Confront the source with the wiki. The goal is compilation, not just summarization.

## 4. Compile into the wiki

- Create or update the relevant project page in wiki/projects/
- Create a source summary page in wiki/sources/YYYY-MM-DD-slug.md
- Create or update a concept page in wiki/concepts/ when a topic spans multiple sources (e.g., RAG, vector search)
- Update wiki/index.md with the new source and any project changes
- Add cross-links to existing wiki pages where relevant
- Flag contradictions with existing wiki content

A single source can touch 5-15 wiki pages. That's normal.

## 5. Move and log

- Run `wikictl ingest "<project>" raw/untracked/<source>` (moves to raw/ingested/)
- Append to wiki/log.md
- Confirm: "Ingested. Project page [X] updated. Source page created. [N] wiki pages touched."

## 6. Suggest next actions

- "There are 2 more files in raw/untracked/. Want me to ingest them too?"
- "This source mentions [topic] which doesn't have a wiki page yet. Create one?"
- "This contradicts what the wiki says about [X]. Want me to update it?"

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
- `/agent-wiki-progress` — mid-session checkpoint, scope drift detection
- `/agent-wiki-finish` — end session, write back durable knowledge
- `/agent-wiki-health` — deep audit of wiki (contradictions, orphans, staleness)
