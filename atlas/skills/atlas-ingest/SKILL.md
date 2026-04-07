---
name: atlas-ingest
description: >
  Ingest a source into the Atlas knowledge base. Handles URLs, local files,
  and pasted text. Saves to raw/, creates wiki pages, updates the graph,
  and flags contradictions. Can enrich with web research.
---

# /atlas-ingest

The user gives you a source — a URL, pasted text, or file path. You handle the full pipeline: fetch → save to raw/ → build wiki pages → update graph → flag contradictions.

## Usage

```bash
# Ingest a URL (auto-detects type: tweet, arxiv, github, pdf, webpage, image)
atlas ingest https://arxiv.org/abs/2401.00001 --title "My Paper" --author "Author"

# Ingest a local file (must be in raw/untracked/ or provide path)
atlas ingest /path/to/file.md --title "My Document"

# Ingest from a specific project root
atlas ingest https://example.com --title "Article" --root /path/to/project
```

## Step-by-step instructions

### 1. Detect the input type

The user gives you one of these:

- **URL** — detect type with `atlas ingest <url>`. Auto-detects: arxiv, tweet/x.com, github, pdf, image, generic webpage.
- **Pasted text** — the user pasted content directly. Save VERBATIM to `raw/untracked/YYYY-MM-DD-slug.md`. Word for word, no summarization. Then run `atlas ingest raw/untracked/YYYY-MM-DD-slug.md`.
- **File path** — if it's not already in `raw/ingested/`, copy to `raw/untracked/` first, then ingest.
- **Obsidian Web Clipper** — check `raw/untracked/` for recently added markdown files with images.
- **Images** — save alongside markdown in `raw/`. Reference them in the wiki source page.

### 2. Save to raw/

For URLs, the `ingest` command fetches and saves to `raw/ingested/YYYY-MM-DD-slug.md` automatically.

For pasted text, you must save it first:

```bash
# Create the untracked directory if it doesn't exist
mkdir -p <project>/raw/untracked/

# Save the pasted content verbatim
# <content> = whatever the user pasted, no edits
cat > <project>/raw/untracked/YYYY-MM-DD-slug.md << 'EOF'
<exact user content>
EOF

# Then ingest it
atlas ingest <project>/raw/untracked/YYYY-MM-DD-slug.md --title "Source Title"
```

Frontmatter requirements per source type:
- URLs get auto-generated: `source_url`, `type`, `captured_at`, optional `title`/`author`
- Local files that lack YAML frontmatter get: `title`, `captured_at`
- Pasted text must be verbatim — not a single word lost

### 3. Read and analyze the source

- Read the full content of the ingested file
- Check what the graph says about this topic: `atlas query "<topic>" --root <project>`
- Read relevant existing wiki pages

Summarize 3-5 key takeaways. Then ask 2-5 socratic questions based on what the source says vs what the wiki knows:

**Project:** "This looks related to [project]. Correct?" (don't ask "which project?" if you can guess)

**Contradictions:** "The source says [X] but the wiki says [Y]. Which is current?"

**Decisions:** "The source describes 3 approaches. We only documented approach 1. Should I add the alternatives?"

**Missing context:** "The source mentions [person/tool/concept] that doesn't exist in the wiki yet. Should I create a page?"

**Emphasis:** "This source covers [A, B, C]. What matters most? Or should I compile everything?"

**Staleness:** "The wiki page for this hasn't been updated since [date]. This source has fresher info. Refresh it?"

Always hypothesize before asking. Confront the source with the wiki. The goal is compilation, not just summarization.

### 4. Create wiki pages

A single source can touch 5-15 wiki pages. That's normal.

**Project page:** Create or update `wiki/projects/<slug>.md` with relevant sections from the source.

**Source page:** Create `wiki/sources/YYYY-MM-DD-slug.md` with:
```yaml
---
type: wiki-source
title: "Source Title"
date: YYYY-MM-DD
project: project-name
source-type: article
raw-path: raw/ingested/YYYY-MM-DD-slug.md
ingested-by: agent
confidence: medium
---
```

**Concept pages:** Create or update `wiki/concepts/<slug>.md` when a topic spans multiple sources. No date prefix — concepts are timeless.

**Decision pages:** Create `wiki/decisions/YYYY-MM-DD-slug.md` for any decisions extracted.

**Index update:** Update `wiki/index.md` with new pages and one-line descriptions.

**Cross-links:** Add `[[wikilinks]]` to existing pages where relevant.

**Confidence scoring:** high = corroborated by multiple sources, medium = single source, low = hypothesis or stale.

### 5. Sync the graph

After creating wiki pages:

```bash
atlas scan --update <project>
```

This syncs wiki → graph and graph → wiki via the Linker. The graph now reflects the new knowledge structure.

### 6. Log and confirm

```bash
atlas stats --root <project>
```

Tell the user: "Ingested [source]. Project page [X] updated. Source page created. [N] wiki pages touched. Graph now has [M] nodes, [K] edges."

### 7. Suggest enrichment (optional)

After ingesting, check if the source mentions topics the wiki doesn't cover yet:

"This source mentions [X, Y, Z] that aren't in the wiki yet. Want me to:
- **Quick** — 1 web search per topic, ingest the best result
- **Deep** — 3-5 parallel searches, ingest all good results
- **Skip** — keep what we have"

If the user wants enrichment: search, save to `raw/untracked/`, ingest each one. Create concept pages for new topics.

## Enrichment strategies by URL type

- **Arxiv** — Extract paper title, abstract, key contributions. Check if related concepts exist in wiki. Suggest papers on the same topic.
- **Tweet/X** — Save the tweet text + context. Usually a single insight. Quick ingest, minimal wiki impact.
- **GitHub** — Save the repo/page content. Extract architecture patterns if visible. Link to projects that use similar tech.
- **PDF** — Extract full text. This is the biggest source — can touch many wiki pages. Consider deep enrichment.
- **Webpage** — Extract key sections. Check if it contradicts or confirms existing wiki content.

## Rules

1. Always observe before asking. Never ask what you can infer.
2. Hypothesize, then confirm. "I think X. Correct?" not "What is X?"
3. Suggest concretely. "I'd write [this] to [here]" not "should I update something?"
4. 2-5 questions per command. Never more.
5. Show write-back proposals before executing. User approves.
6. If atlas CLI is not available, continue normally (save to raw/ and wiki/ manually).
7. Paste text VERBATIM to raw/ — no summarization, no editing.
8. One source can touch many wiki pages. That's by design — don't try to force it into one page.
9. Always scan after wiki writes to keep graph in sync.

---

## Other Atlas skills

- `/atlas-start` — begin a session, read the graph, get briefed
- `/atlas-scan` — scan a directory into the graph
- `/atlas-query` — query the graph for connections
- `/atlas-progress` — mid-session checkpoint
- `/atlas-finish` — end session, write back durable knowledge
- `/atlas-health` — deep audit of graph and wiki
