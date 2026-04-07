---
name: atlas-scan
description: >
  Scan a directory to build or update the knowledge graph. Extracts
  nodes and edges from code, docs, and images. Use when pointing Atlas
  at a new corpus or refreshing after changes.
---

# /atlas-scan

Point Atlas at a folder. It extracts a knowledge graph automatically from code, docs, and any files in the target.

## Usage

```bash
# Full scan — everything from scratch
atlas scan /path/to/repo

# Incremental scan — only changed files (faster)
atlas scan /path/to/repo --update

# Force full re-scan, ignoring cache
atlas scan /path/to/repo --force

# Scan a single file
atlas scan /path/to/file.py
```

## What it does

The scan has 3 stages:

1. **Extract** — Scanner reads each file and produces an Extraction (Node + Edge dataclasses). AST extraction via tree-sitter for code files, semantic extraction for docs/images. Cache skips unchanged files.
2. **Build/Merge** — Merge the Extraction into the GraphEngine (NetworkX-backed). If `--update`, loads existing `atlas-out/graph.json`. Otherwise starts fresh.
3. **Wiki Sync** — If a `wiki/` directory exists, the Linker:
   - Sync wiki → graph: update nodes/edges that match wiki page titles/wikilinks
   - Sync graph → wiki: suggest new pages or links for disconnected graph nodes

## Step-by-step instructions

When the user invokes this skill:

### 1. Understand the target

Ask the user what directory to scan if not specified. Check:
- Does it exist? Is it a code repo, docs folder, mixed?
- Does it already have an `atlas-out/graph.json`? If yes, suggest `--update`.
- Does it have a `wiki/` directory? If yes, wiki sync will be attempted.

### 2. Run the scan

```bash
atlas scan /path/to/target [--update] [--force]
```

Watch the output for:
- "Extracted N nodes, M edges" — sanity check. Empty = wrong path or no supported files.
- "Wiki sync: X changes, Y suggestions" — only appears if wiki/ exists.
- "Graph: N nodes, M edges, C communities" — the final state.
- "Health score: X" — 0-100. Higher is better.

### 3. Interpret results

After the scan runs, summarize:

**Graph stats:** "The graph now has N nodes across C communities."
**Health score:** Explain the score. Below 40 = lots of inferred/ambiguous edges. Above 70 = strong extraction signal.
**Wiki sync:** If changes were made, list them. If suggestions were generated, offer to apply them.

### 4. Post-scan suggestions

- **God nodes:** "Want me to check the most connected concepts? `atlas god-nodes`"
- **Surprises:** "Want to see unexpected connections? `atlas surprises`"
- **Next steps:** If nothing is in the graph yet → suggest `/atlas-ingest` to add sources. If graph exists → suggest `/atlas-query` to explore.

## How scanning works (internal)

- **Code files** → tree-sitter AST parsing extracts imports, function calls, class hierarchies. Each function/class becomes a Node. Dependencies become Edges.
- **Markdown/docs** → Wikilinks become edges. Headings and concepts become nodes.
- **Images/PDFs** → Saved alongside their content. Semantic extraction creates nodes with summaries.
- **Cache** → SHA256 hash manifest at `atlas-out/cache.json`. Changed files are re-extracted, unchanged ones reuse cached Extractions.

### Scanner pipeline

```bash
Scanner.scan(target)
  → extracts Extraction (nodes + edges)
  → CacheEngine.check() — skip if hash matches
  → scanner_ast.py for code (tree-sitter)
  → scanner_semantic.py for docs (LLM dispatch)
  → GraphEngine.merge(extraction)
  → Linker.sync_wiki_to_graph() (if wiki/ exists)
  → Linker.sync_graph_to_wiki() (if wiki/ exists)
```

## Rules

1. Always run a full scan first (`--force`) if no graph.json exists. Then use `--update` for subsequent scans.
2. If atlas CLI is not available, continue normally.
3. The graph output is always at `<target>/atlas-out/graph.json`.
4. Wiki sync is optional — if wiki/ doesn't exist, only graph gets updated.
5. Don't force a full scan on a large repo unless the user asks — incremental is faster and preserves manual annotations.
6. After scan, always show the user the graph stats and health score.
7. If scan produces 0 nodes, check: is the path correct? Are there any code/doc files?

---

## Other Atlas skills

- `/atlas-start` — begin a session, read the graph, get briefed
- `/atlas-query` — query the graph for connections
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-progress` — mid-session checkpoint
- `/atlas-finish` — end session, write back durable knowledge
- `/atlas-health` — deep audit of graph and wiki
