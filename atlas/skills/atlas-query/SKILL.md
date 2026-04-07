---
name: atlas-query
description: >
  Query the Atlas knowledge graph. Traverses nodes, finds paths,
  explains concepts, identifies god nodes and surprises. Use when
  the user asks a question about the codebase or knowledge base.
---

# /atlas-query

Ask the knowledge graph a question. It traverses nodes/edges and synthesizes answers with citations.

## Usage

```bash
# Query from a concept — BFS traversal, depth 3 (default)
atlas query "auth" --root /path/to/target

# Deeper traversal (deeper = more context, more tokens)
atlas query "auth" --depth 5 --root /path/to/target

# DFS instead of BFS (follows deep chains, not wide nets)
atlas query "auth" --mode dfs --depth 3 --root /path/to/target

# Shortest path between two concepts
atlas path "auth" "billing" --root /path/to/target

# Explain a single concept + neighbors
atlas explain "auth" --root /path/to/target

# Top most-connected nodes
atlas god-nodes --top 10 --root /path/to/target

# Most surprising cross-boundary connections
atlas surprises --top 10 --root /path/to/target

# Quick graph stats
atlas stats --root /path/to/target
```

## Step-by-step instructions

When the user asks a question or wants to explore the knowledge graph:

### 1. Check the graph exists

```bash
ls -la <target>/atlas-out/graph.json 2>/dev/null
```

If no graph exists: "No graph yet. Want me to scan the directory first? `atlas scan <path>`"

### 2. Understand the query

- **Specific question about a concept** → `atlas explain "<concept>"`
- **"What connects X and Y?"** → `atlas path "X" "Y"`
- **Broad exploration** → `atlas query "<concept>"` then read wiki pages
- **"What's the big picture?"** → `atlas god-nodes` + `atlas stats`
- **"What's surprising here?"** → `atlas surprises`

### 3. Run the query and interpret

Each command returns structured output:

**Query** → list of nodes in the subgraph, connection count, token estimate.
- If the query returns many nodes → suggest narrowing by topic or lowering depth.
- If it returns 0 nodes → suggest trying a different term or scanning first.

**Path** → shortest chain of edges between two nodes.
- If no path → "No connection found. They might be in different communities."
- Read the wiki for each hop if the user wants more detail.

**Explain** → node details, summary (if available), and all neighbors.
- Always read the corresponding wiki page if one exists.
- If the node has wikilinks in the wiki, follow those too.

**God nodes** → the most connected concepts in the graph.
- These are your "hub" topics. Usually: auth, database, API, config.
- Check if they have matching wiki pages. If not, suggest creating one.

**Surprises** → unexpected connections across unrelated domains.
- These are your most interesting findings. "Why does the auth module depend on the email template system?"

### 4. Multi-step deep queries (for complex questions)

For questions that require synthesis across the graph:

1. `atlas query "<concept>"` — get the graph neighborhood
2. Read the wiki page for that concept (if exists)
3. If the wiki page cites sources, read the source pages in `wiki/sources/`
4. If sources reference raw files, read the original in `raw/ingested/`
5. `atlas path "<A>" "<B>"` — check if specific connections exist
6. Synthesize across all levels. Always cite with [[page-name]] format.

This follows the Karpathy L0→L1→L2→L3 pattern: start broad, go deeper only when it matters.

### 5. Synthesize the answer

When presenting results to the user:

**Graph-first:** "In the graph, auth connects to 12 nodes. Top connections: db (imports), cache (calls), billing (semantically related)."

**Wiki-second:** "The wiki has a decision page about JWT vs sessions from April 2, 2026. It says [summary]."

**Source-third:** "The source article that informed this decision was from Stripe's docs. Key takeaway: [summary]."

Always cite sources. Never present graph data as fact — it's extracted and may have extraction errors.

## How queries work (internal)

- **BFS** — Breadth-first from a start node. Gets the "neighborhood" of a concept. Default mode. Good for "tell me about X and what it connects to."
- **DFS** — Depth-first. Follows long chains. Good for tracing dependency chains: "What does auth need, and what do those need?"
- **Path** — NetworkX shortest_path() between two node IDs. Returns edges, not just node lists.
- **Token estimate** — Each query result includes `estimated_tokens`. This helps the LLM decide if the subgraph fits in context.

### Node types in the graph

| Type | Source | Example |
|------|--------|---------|
| code | AST extraction | `auth_module`, `db_client`, `UserModel` |
| document | Semantic extraction | `API spec`, `deploy guide` |
| wiki-page | Wiki sync | `wiki/projects/acme` |
| wiki-concept | Wiki sync | `wiki/concepts/auth` |
| wiki-decision | Wiki sync | `wiki/decisions/jwt-over-sessions` |
| wiki-source | Wiki sync | `wiki/sources/2026-04-01-stripe-api` |

### Edge confidence

- **EXTRACTED** (1.0) — Directly found in source code or wiki. High confidence.
- **INFERRED** (0.7) — Deduced from context. Medium confidence.
- **AMBIGUOUS** (0.2) — Low confidence, needs verification.

## Rules

1. Always start with the graph. If the graph exists, query it before searching raw files.
2. If atlas CLI is not available, continue normally (fall back to grep/rg on wiki/).
3. BFS is the default. Use DFS only for dependency tracing.
4. Always show the token count if it's large (>2000 tokens). Helps with context budgeting.
5. Graph data is extracted, not verified. Don't present it as authoritative truth.
6. When explaining a concept, always check: does a wiki page exist for this node? Read it if yes.
7. Cite everything: `[[page-name]]` for wiki pages, file paths for raw files.

---

## Other Atlas skills

- `/atlas-start` — begin a session, read the graph, get briefed
- `/atlas-scan` — scan a directory into the graph
- `/atlas-ingest` — ingest a URL, file, or pasted text
- `/atlas-progress` — mid-session checkpoint
- `/atlas-finish` — end session, write back durable knowledge
- `/atlas-health` — deep audit of graph and wiki
