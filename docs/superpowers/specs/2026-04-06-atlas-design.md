# Atlas — Knowledge Engine Design Spec

**Date:** 2026-04-06
**Status:** Draft
**Author:** Pierre Beunardeau / Origin Labs
**Repo:** originlabs-app/atlas (evolves from originlabs-app/agent-wiki)

---

## 1. Vision

Atlas is a knowledge engine for AI agents. Point it at any folder — code, papers, notes, screenshots — and it does two things no one else does together:

1. **Discovery** — scans everything, extracts a graph of relationships automatically, gives you an interactive map in 30 seconds
2. **Curation** — compiles a living wiki that agents maintain session after session, compounding knowledge over time

The graph and the wiki are linked: when the graph discovers a relationship, the wiki documents it. When the wiki evolves, the graph updates. One system, not two tools glued together.

**Tagline:** *Scan anything. Know everything. Remember forever.*

**Origin:** Atlas is the evolution of agent-wiki (Karpathy LLM Wiki pattern), enriched with graphify's discovery capabilities, designed as a future ARA module.

---

## 2. Users

**Primary: Dev solo / indie hacker** — "I have 200 files (code, papers, notes). I want to understand what I have and keep it up to date." The viral hook. One command, instant value.

**Secondary: Technical team** — "We have 5 repos, 3 years of decisions, docs everywhere. We want a team second brain that agents maintain." The retention play. Multi-project, shared knowledge.

**Tertiary: ARA platform user** — Atlas becomes a hosted module within ARA, with multi-tenant storage, billing, and collaboration.

---

## 3. Surfaces

Three surfaces, one codebase:

| Surface | What | Entry point |
|---------|------|-------------|
| **CLI** | `pip install atlas-ai && atlas scan .` | The viral hook (day 1) |
| **Dashboard** | Local FastAPI server, graph viz, wiki view, audit | The daily driver (day 2+) |
| **MCP server** | Any agent (Claude Code, Codex, Cursor, Hermes) connects and queries/curates | The infrastructure (always) |

---

## 4. Architecture

```
atlas/                             # Python package
├── core/                          # The engine
│   ├── scanner.py                 # Discovery — AST + LLM extraction
│   ├── graph.py                   # Graph engine — NetworkX, build, merge, query
│   ├── wiki.py                    # Wiki engine — markdown pages, templates, frontmatter
│   ├── linker.py                  # The fusion — graph <-> wiki bidirectional sync
│   ├── analyzer.py                # God nodes, surprises, gaps, contradictions
│   ├── cache.py                   # SHA256 incremental
│   ├── ingest.py                  # Smart URL fetch (tweet, arxiv, PDF, webpage)
│   └── storage.py                 # Storage abstraction (local filesystem / ARA cloud)
│
├── server/                        # FastAPI backend
│   ├── app.py                     # REST API routes
│   ├── mcp.py                     # MCP server (stdio + SSE)
│   └── ws.py                      # WebSocket for live updates
│
├── dashboard/                     # Frontend (static-first, no build step)
│   ├── index.html                 # SPA shell
│   ├── graph.js                   # Graph visualization (vis.js or d3)
│   ├── wiki.js                    # Markdown wiki renderer
│   ├── audit.js                   # Audit dashboard
│   └── search.js                  # Full-text + graph traversal search
│
├── skills/                        # Agent skills (agentskills.io standard)
│   ├── atlas-start/
│   ├── atlas-scan/
│   ├── atlas-query/
│   ├── atlas-ingest/
│   ├── atlas-progress/
│   ├── atlas-finish/
│   └── atlas-health/
│
├── export/                        # Output formats
│   ├── html.py                    # Interactive graph
│   ├── obsidian.py                # Obsidian vault
│   ├── neo4j.py                   # Cypher export
│   ├── graphml.py                 # Gephi/yEd
│   ├── svg.py                     # Static embed
│   └── pdf.py                     # Printable report
│
└── cli.py                         # Main CLI (typer)
```

**Key principle:** The wiki markdown is the source of truth. `graph.json` is derived from the wiki + raw sources. Delete `graph.json`, run `atlas scan`, and it rebuilds in 30 seconds. The wiki survives without the graph. The graph doesn't survive without the wiki.

---

## 5. Features

### 5.1 — Discovery Engine (`atlas scan`)

**Multi-modal extraction:**
- Code (13 languages) → AST via tree-sitter, call graph, imports, rationale comments
- Markdown/docs → concepts, entities, relationships via LLM
- PDF → text extraction + citation mining
- Images → Claude Vision (screenshots, diagrams, whiteboards, any language)
- URLs → smart fetch (tweet, arxiv, GitHub, webpage) with auto frontmatter

**Beyond graphify:**
- Native incremental extraction — real diff, not just cache. "3 files changed, update only those 3 nodes."
- Cross-corpus relations — if you have 3 projects in Atlas, scan finds links between them.
- Confidence decay — INFERRED relations age. After 30 days without human confirmation, they drop from medium to low.

### 5.2 — Graph Engine (`atlas query`)

**Storage:** `graph.json` — serialized NetworkX. No external DB, no Neo4j required. Git-versionable.

**Operations:**
- `atlas query "what connects auth to billing?"` — BFS/DFS traversal, token-aware
- `atlas path "ConceptA" "ConceptB"` — shortest path with relations
- `atlas explain "ConceptX"` — plain-English summary of a node + neighbors
- `atlas god-nodes` — top N most-connected concepts
- `atlas surprises` — unexpected connections (cross-file, cross-type, cross-community)

**Clustering:** Leiden community detection. Communities become wiki "domains" — not "Community 0" but "Auth & Security" (LLM-labeled).

### 5.3 — Wiki Engine (agent-wiki heritage)

**Everything agent-wiki v1 does:**
- Markdown pages with typed frontmatter (projects, concepts, decisions, sources)
- Normalized templates per type
- `[[wikilinks]]` for navigation
- Auto-maintained index
- Append-only log

**New in Atlas:**
- Auto-linking — when writing a page, Atlas detects mentioned concepts and suggests missing `[[wikilinks]]`
- Contradiction detection — "Page ARA says 'FastAPI'. Page GED says 'Express'. Contradiction?"
- Staleness tracking — pages not updated in 30 days → flagged in audit
- Provenance — every claim traces its source (`raw/` file, URL, or agent session)

### 5.4 — The Linker (the fusion, the new thing)

The heart of Atlas — what exists nowhere else.

**Wiki → Graph (always automatic, synchronous):**

| Wiki event | Graph action |
|---|---|
| Page created | Node added (type = frontmatter `type:`) |
| Page deleted | Node removed + orphan edges cleaned |
| `[[wikilink]]` added | Edge created (relation=`references`, confidence=EXTRACTED) |
| `[[wikilink]]` removed | Edge removed |
| `tags: [x, y]` modified | `tagged_with` edges updated |
| `description:` modified | Node `summary` attribute updated |

**Graph → Wiki (always proposed, never forced):**

| Graph event | Wiki suggestion |
|---|---|
| New node without wiki page | "Create a page for {label}?" |
| INFERRED edge between two existing pages | "Add `[[wikilink]]` from {A} to {B}?" (with reason) |
| Node becomes god node (top 5 by degree) | Flagged in AUDIT_REPORT |
| Community without concept page | "These 8 nodes form a theme. Create a concept page?" |
| AMBIGUOUS edge | "Clarify the relationship between {A} and {B}?" |

**Golden rule:** The graph proposes, the agent or human disposes. No automatic wiki writes without validation.

### 5.5 — Server & Dashboard (`atlas serve`)

**FastAPI backend:**
- REST API for all operations (scan, query, wiki CRUD, audit)
- MCP server (stdio for local, SSE for remote)
- WebSocket for live updates

**Dashboard:**
- **Graph view** — interactive visualization (d3/vis.js). Click node → see wiki page. Filter by community, type, confidence.
- **Wiki view** — rendered markdown. Breadcrumbs, backlinks, table of contents. Inline editable.
- **Audit view** — orphans, contradictions, staleness, god nodes, surprises. Global health score.
- **Search** — full-text + graph traversal combined.
- **Timeline** — operation log. Who changed what, when, why.

Static-first: HTML + vanilla JS + Tailwind CDN. Single `index.html` served by FastAPI. Boots in 200ms.

### 5.6 — Agent Skills (`/atlas-*`)

7 skills, agentskills.io standard, cross-platform:

| Skill | When | What it does |
|---|---|---|
| `/atlas-start` | Session start | Reads wiki + graph, briefs agent, detects tensions, proposes plan |
| `/atlas-scan` | New corpus | Points at folder → extraction → graph + wiki in one pass |
| `/atlas-ingest` | New source | URL, file, or text → raw/ + wiki page + graph update |
| `/atlas-query` | Question | Traverses graph, synthesizes, files answer into wiki if valuable |
| `/atlas-progress` | Mid-session | Checkpoint, scope drift, write-back suggestions |
| `/atlas-finish` | Session end | Extracts durable knowledge, proposes write-backs, syncs graph |
| `/atlas-health` | Weekly | Deep audit — contradictions, orphans, staleness, gaps, web enrichment |

### 5.7 — Export

| Format | Command | Use case |
|---|---|---|
| JSON | `atlas export json` | API, GraphRAG, backup |
| HTML | `atlas export html` | Standalone interactive graph |
| Obsidian | `atlas export obsidian` | Vault with backlinks |
| Neo4j | `atlas export neo4j` | Cypher import |
| GraphML | `atlas export graphml` | Gephi, yEd |
| SVG | `atlas export svg` | Embed GitHub, Notion |
| PDF | `atlas export pdf` | Printable full report |
| MCP | `atlas serve --mcp` | Agents connect |

---

## 6. MCP Server

The MCP server is the universal entry point. Skills call MCP. Dashboard calls MCP. REST API wraps MCP. One codebase, three surfaces.

```
atlas.scan(path)                    → runs scan, returns summary
atlas.query(question, mode)         → BFS/DFS traversal, returns subgraph
atlas.path(from, to)                → shortest path
atlas.explain(concept)              → plain-English node summary
atlas.god_nodes(top_n)              → most connected concepts
atlas.stats()                       → nodes, edges, communities, health score
atlas.ingest(url_or_path)           → ingests a source
atlas.wiki.read(page)               → reads a wiki page
atlas.wiki.write(page, content)     → writes a wiki page
atlas.wiki.search(terms)            → full-text search
atlas.audit()                       → returns AUDIT_REPORT
atlas.suggest_links()               → missing wikilink suggestions
```

---

## 7. Data Flow

### The complete lifecycle

```
USER DROPS FILES          AGENT WORKS              USER/AGENT QUERIES
      |                        |                         |
      v                        v                         v
   raw/                     wiki/                    atlas query
      |                        |                         |
      v                        v                         v
  SCANNER ----nodes----> GRAPH ENGINE <---edges---- ANALYZER
                              |                         |
                         <----+                         |
                        LINKER ----suggestions--->  AUDIT_REPORT
                              |
                              v
                           wiki/
                        (pages updated)
```

The flow is a loop, not a pipeline. Each session enriches the cycle.

### Three fundamental operations

**SCAN** — automatic discovery:
`raw/file → Scanner.extract → Graph.merge → Linker.sync_graph_to_wiki → suggestions`

**CURATE** — agent enrichment:
`/atlas-ingest URL → Ingest.fetch → raw/ → Scanner.extract → Graph.merge → Linker → Agent writes wiki → Linker.sync_wiki_to_graph`

**QUERY** — intelligent interrogation:
`question → Graph.query(BFS/DFS) → Analyzer.synthesize → answer (optionally filed back to wiki)`

### Cache and performance

```
atlas-cache/
├── manifest.json              # {filepath: {hash, mtime, last_extracted}}
├── extractions/{sha256}.json  # full extraction per file
└── semantic/{sha256}.json     # LLM extraction (docs, images)
```

- Code → AST (free, always re-extracted if mtime changes)
- Docs/images → LLM (expensive, cached by SHA256 content hash)
- `atlas scan --update` → re-extracts only delta
- `atlas scan --force` → ignores cache

**Performance targets:**
- Initial scan 100 files → < 2 min
- Incremental scan 3 changed files → < 10 sec
- Graph query → < 100ms (in-memory)
- Dashboard load → < 200ms (static HTML)

---

## 8. Storage Abstraction

```python
class StorageBackend(Protocol):
    def read(self, path: str) -> str: ...
    def write(self, path: str, content: str) -> None: ...
    def list(self, prefix: str) -> list[str]: ...
    def delete(self, path: str) -> None: ...

class LocalStorage(StorageBackend):     # standalone
    """Local filesystem — wiki/ and raw/"""

class ARAStorage(StorageBackend):       # ARA mode
    """S3/GCS + PostgreSQL index"""
```

Core engine (Scanner, Graph, Wiki, Linker) never touches the filesystem directly. It calls `storage.read()` and `storage.write()`. In local mode it's filesystem, in ARA mode it's cloud. Same code, same tests.

---

## 9. ARA Integration

Atlas standalone is the ARA module in standalone mode. When ARA goes live, Atlas becomes a microservice instead of a local server. Same API, same MCP, same dashboard — only the hosting changes.

| Aspect | Standalone | ARA |
|---|---|---|
| Storage | Local filesystem | S3/GCS + PostgreSQL |
| Auth | None (local) | ARA auth (API key, org, RBAC) |
| Multi-tenant | One wiki per machine | One wiki per org, schema isolation |
| MCP | stdio local | SSE remote, authenticated |
| Billing | Free | LLM tokens billed via ARA ledger (double-entry) |
| Dashboard | `localhost:7100` | `app.ara.dev/atlas` (embedded) |
| Collaboration | Git (push/pull) | Real-time (WebSocket) |

**ARA surfaces Atlas activates:**

| ARA Surface | What Atlas brings |
|---|---|
| S1 — Gateway | LLM scans route through ARA gateway → automatic metering |
| S2 — FinOps | Budget per knowledge base |
| S3 — MCP Marketplace | Atlas exposes MCP. Other agents can buy access to a knowledge base. |
| S4 — Atlas | The surface itself |
| S5 — Payments | Enterprises pay for hosted Atlas. Settlement via ledger. |
| S6 — Deploy | Agent running 24/7 with Atlas as persistent memory |

**The flywheel:** Dev installs Atlas (free) → accumulates knowledge → wants to share/scale → joins ARA → agents consume tokens via ARA Gateway → ARA bills → more agents → more knowledge bases → more Atlas.

---

## 10. Migration from agent-wiki v1

```bash
pip install atlas-ai
atlas migrate              # detects ~/agent-wiki or ./wiki
```

`atlas migrate`:
1. Detects existing wiki (structure `wiki/`, `raw/`, `AGENTS.md`)
2. Scans to build initial `graph.json`
3. Installs Atlas skills (symlinks `~/.agents/skills/atlas-*`)
4. Updates README with new commands
5. Keeps all content intact — zero loss

Old `/agent-wiki-*` skills redirect to `/atlas-*` with deprecation notice.

---

## 11. Team Organization

20 developers, 4 weeks, 5 squads:

| Squad | Devs | Responsibility |
|---|---|---|
| **Core** | 5 | Scanner, Graph, Wiki, Linker, Cache, Analyzer |
| **Server** | 4 | FastAPI, MCP server, WebSocket, REST API |
| **Dashboard** | 4 | Graph viz, Wiki view, Audit view, Search |
| **Skills** | 4 | 7 skills, CLI, multi-platform, install |
| **Quality** | 3 | Tests, CI/CD, benchmarks, worked examples, docs |

### Week 1 — Foundations

All squads deliver their v1. Gate: `pip install -e . && atlas scan tests/fixtures/ && atlas serve` shows the graph in the dashboard.

### Week 2 — Complete features

Scanner multi-modal, full API, full dashboard, all 7 skills, 80%+ test coverage. Gate: external dev installs and uses Atlas on a real repo.

### Week 3 — Polish and differentiators

Confidence decay, contradiction detection, cross-corpus linking, community auto-labeling, dark mode, responsive, socratic workflow, git hooks, watch mode, 3 worked examples. Gate: worked examples with published benchmarks.

### Week 4 — Launch

Bug fixes, all export formats, ARA-ready flags, onboarding flow, PyPI publish, GitHub release v2.0, README with demo GIF, tweet thread.

---

## 12. Interfaces Contract

Squads work in parallel. Interfaces are defined Day 1 of Week 1:

```python
class Scanner:
    def scan(path: Path, mode: str = "default") -> Extraction: ...
    def scan_incremental(path: Path, manifest: Manifest) -> Extraction: ...

class Graph:
    def merge(extraction: Extraction) -> None: ...
    def query(question: str, mode: str = "bfs", depth: int = 3) -> Subgraph: ...
    def path(source: str, target: str) -> list[Edge]: ...
    def god_nodes(top_n: int = 10) -> list[Node]: ...
    def surprises(top_n: int = 10) -> list[Edge]: ...
    def stats() -> GraphStats: ...

class WikiEngine:
    def read(page: str) -> Page: ...
    def write(page: str, content: str, frontmatter: dict) -> None: ...
    def search(terms: str) -> list[Page]: ...
    def list_pages(type: str = None) -> list[str]: ...

class Linker:
    def sync_wiki_to_graph() -> list[GraphChange]: ...
    def sync_graph_to_wiki() -> list[WikiSuggestion]: ...

class Analyzer:
    def audit() -> AuditReport: ...
    def suggest_links() -> list[LinkSuggestion]: ...
```

Server, Dashboard, and Skills only call these interfaces. No direct filesystem access.

---

## 13. What Differentiates Atlas

| Tool | What it does | What it doesn't |
|---|---|---|
| graphify | One-shot discovery, interactive graph | No curation, no memory, no server |
| agent-wiki v1 | Agent curation, living wiki | No graph, no discovery, no dashboard |
| NotebookLM | Q&A with citations | No graph, no persistence, no agents |
| Obsidian + plugins | Personal wiki, graph view | Manual, no agents, no extraction |
| RAG | Retrieval on embeddings | No structure, no relations, black box |
| **Atlas** | Discovery + curation + service | — |

**The moat:**
1. The Linker — bidirectional graph-wiki sync exists nowhere else
2. Socratic workflow — skills ask questions, detect tensions, propose write-backs
3. ARA integration — Atlas standalone is the Trojan horse for ARA adoption
