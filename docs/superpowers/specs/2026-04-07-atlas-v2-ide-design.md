# Atlas v2 — IDE for Knowledge

**Date:** 2026-04-07
**Status:** Draft
**Author:** Pierre Beunardeau / Origin Labs
**Context:** Next evolution of Atlas dashboard — from wiki viewer to knowledge IDE

---

## 1. Vision

Atlas becomes an IDE for knowledge. Like VS Code is for code, Atlas is for any folder of files. You open a folder, you see your files, your graph, your connections. No setup, no config, no LLM required for the base experience.

The product is useful in 10 seconds: Open Folder → see the graph → navigate. Everything else is a bonus.

---

## 2. Key Decisions

### 2.1 Scan Levels

| Level | What | Cost | When |
|---|---|---|---|
| **L0 — File listing** | File tree, types, sizes | Free, 1 second | On folder open |
| **L1 — Structure** | AST code (classes, functions, imports) + regex markdown (headings, links) | Free, 5-30 seconds | First open + auto-rescan |
| **L2 — Relations** | Cross-file semantic connections, concept extraction | LLM required | Opt-in "Enrich with AI" |
| **L3 — Deep** | PDF extraction, images (Vision), rationale mining | LLM + Vision | Opt-in "Enrich with AI" |

**L0+L1 = the product. L2/L3 = the bonus.**

The dashboard must be instantly useful without configuration, API keys, or agents. L0+L1 are pure Python (AST + regex), free, and fast.

### 2.2 No API Keys in Atlas

Atlas never stores or uses LLM API keys directly. For L2/L3 enrichment:
- If an agent is connected via MCP (WebSocket) → send the job to the agent
- If no agent connected → show: "Run `atlas scan --deep` in your agent"

The LLM is the user's agent, not Atlas.

### 2.3 Auto-rescan on Reopen

When reopening a project:
1. Load `graph.json` from cache (instant)
2. Compare file mtimes with manifest (100ms)
3. If files changed → auto-rescan L0+L1 silently (free, 2-5 seconds)
4. Graph updates transparently, no banner, no question

---

## 3. Welcome Screen — "Recent Projects"

Displayed when no project is loaded (first launch or click on Atlas logo).

```
┌──────────────────────────────────────────────┐
│  ◆ Atlas                                     │
│                                              │
│  Recent Projects                             │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ 📁 ~/dev/my-app              3h ago  │    │
│  │   142 nodes · 12 communities         │    │
│  ├──────────────────────────────────────┤    │
│  │ 📁 ~/agent-wiki              1d ago  │    │
│  │   945 nodes · 56 communities         │    │
│  ├──────────────────────────────────────┤    │
│  │ 📁 ~/dev/experiments/graphify        │    │
│  │   386 nodes · 0 communities          │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  [Open Folder...]                            │
│                                              │
└──────────────────────────────────────────────┘
```

**Data source:** `~/.atlas/projects.json` — stores path, last opened, node/edge/community counts.

**Behavior:**
- Click a project → load it (auto-rescan if needed)
- "Open Folder" → text input for path (no native file picker in browser — type or paste the path)
- New folder → L0+L1 scan runs with progress bar → opens Explorer when done
- Atlas logo in navbar always returns to this screen

---

## 4. Project Switcher — Navbar Dropdown

When inside a project, the project name appears in the navbar as a dropdown:

```
┌───────────────────────────────────────────────────────┐
│  ◆ Atlas   📁 agent-wiki ▾   Graph  Explorer  Audit   │
│            ┌─────────────────────┐                    │
│            │ 📁 agent-wiki    ●   │                    │
│            │ 📁 my-app            │                    │
│            │ 📁 graphify          │                    │
│            │ ───────────────────  │                    │
│            │ Open Folder...       │                    │
│            │ Recent Projects      │                    │
│            └─────────────────────┘                    │
└───────────────────────────────────────────────────────┘
```

**Behavior:**
- Click project name → dropdown opens
- Click another project → switch (auto-rescan L0+L1 if needed)
- "Open Folder..." → same as welcome screen
- "Recent Projects" → back to welcome screen
- Green dot (●) = currently active project

---

## 5. Sidebar — Simplified to 3 Sections

### 5.1 OVERVIEW (always visible)

```
OVERVIEW
  945 nodes · 1051 edges · 56 communities
  Health: 100 ██████████
  [Enrich with AI]
```

- Stats update in real-time (WebSocket)
- Health score links to Audit view
- "Enrich with AI" button for L2/L3 (see section 2.2)

### 5.2 BROWSE (toggle between 3 modes)

One section with 3 tabs/toggle:

```
BROWSE  [📁 Folder] [📝 Type] [🏘️ Community]
```

**📁 Folder mode** — file tree like VS Code:
```
├── 📁 src/
│   ├── auth.py          (12)
│   ├── db.py             (8)
│   └── api.py           (15)
├── 📁 docs/
│   └── architecture.md   (6)
├── 📁 wiki/
│   ├── 📁 concepts/     (23)
│   ├── 📁 projects/     (10)
│   ├── 📁 decisions/     (5)
│   └── 📁 sources/      (13)
└── README.md              (3)
```

- Numbers in parentheses = graph degree (connections)
- Color-coded by type (same as graph view)
- Click → opens in content panel
- Collapsible, state persisted in localStorage

**📝 Type mode** — pages grouped semantically:
```
Concepts (23)
  Agent Aggregator Platform        [ara]
  Agent Skills Convention          [skills] [standard]
  Atlas Knowledge Engine           [atlas]
  ...

Projects (10)
  ARA                              active
  agent-wiki                       active
  ...

Decisions (5)
  FastAPI over Express             2026-04-03
  ...

Sources (13)
  ARA PRD + GTM                    2026-04-03
  ...

Other (files without wiki type)
  auth.py                          code
  api.py                           code
  ...
```

**🏘️ Community mode** — auto-detected clusters:
```
ARA Core (72 nodes)                ████████████
Gateway & Routing (60 nodes)       ██████████
Gamification (35 nodes)            ██████
Agent Tooling (28 nodes)           █████
...
[Show all 56 communities]
```

- Labels are human-readable (LLM-generated if available, otherwise highest-degree node label)
- Click → community detail in content panel (members, cross-links, wiki coverage)

### Why not 4 sections like before

The old sidebar had FILES + WIKI + COMMUNITIES as separate sections. This showed the same content twice (wiki files appeared in both FILES and WIKI). The toggle approach shows one view at a time — no duplication, no confusion.

---

## 6. Content Panel — Unchanged

Keep the existing content panel design from the Explorer spec:

- **Read mode** (default) — rendered markdown, metadata, backlinks, graph neighbors
- **Edit mode** (split) — raw markdown left, live preview right, Save/Cancel
- **Community view** — members, cross-links, wiki coverage
- **File view** — syntax-highlighted code for non-markdown files
- **No-selection state** — "Select a file or page from the sidebar"

### Fixes required:
- **Edit/View in Graph buttons** must be visible (currently hidden or missing)
- **`[[wikilinks]]`** must render as clickable links in markdown (currently shown as raw text)
- **Double H1** in old pages must be cleaned up (pre-existing data issue from old file-back)

---

## 7. "Enrich with AI" Flow

The button appears in two places:
1. OVERVIEW section in sidebar
2. After L0+L1 scan completes (banner: "Basic scan done. Enrich with AI for deeper analysis?")

**When clicked:**

```
Is an agent connected via MCP?
├── Yes → send enrichment job to agent
│         → progress shown in dashboard (WebSocket)
│         → graph updates in real-time as agent extracts
│         → toast: "Enrichment complete — 47 new relations found"
│
└── No → modal:
         "To enrich with AI, run this in your agent:"
         ┌─────────────────────────────────────┐
         │ atlas scan --deep ~/dev/my-project  │  [Copy]
         └─────────────────────────────────────┘
         "Works with Claude Code, Codex, Cursor, or any MCP agent."
```

---

## 8. Data Storage

### Project Registry

`~/.atlas/projects.json`:
```json
[
  {
    "path": "/Users/pierre/agent-wiki",
    "name": "agent-wiki",
    "last_opened": "2026-04-07T15:00:00Z",
    "nodes": 945,
    "edges": 1051,
    "communities": 56,
    "health": 100
  },
  {
    "path": "/Users/pierre/dev/experiments/graphify/graphify",
    "name": "graphify",
    "last_opened": "2026-04-07T14:00:00Z",
    "nodes": 386,
    "edges": 549,
    "communities": 56,
    "health": 77
  }
]
```

### Per-project Data

Each project stores its Atlas data in `<project>/atlas-out/`:
```
atlas-out/
├── graph.json          # the knowledge graph
├── manifest.json       # file hashes for incremental scan
└── cache/              # extraction cache (SHA256-keyed)
```

---

## 9. Server Changes

### New Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/projects` | GET | List all registered projects |
| `POST /api/projects/open` | POST | Open a folder (registers + L0+L1 scan) |
| `POST /api/projects/switch` | POST | Switch active project |
| `DELETE /api/projects/{path}` | DELETE | Remove from recent (doesn't delete files) |
| `GET /api/scan/status` | GET | Current scan progress (for progress bar) |

### Modified Endpoints

- `POST /api/scan` — add `level` parameter (default "structure", option "deep")
- All existing endpoints become project-scoped (read from the active project's graph)

### Server State

The server holds one active project at a time. Switching projects:
1. Save current graph
2. Load new project's graph.json (or scan if first time)
3. Update in-memory engines (graph, wiki, linker, analyzer)
4. Broadcast `project.switched` via WebSocket

---

## 10. CLI Changes

### New Commands

```bash
atlas .                          # scan + serve + open browser (the magic command)
atlas open ~/dev/my-project      # register + scan + serve
atlas projects                   # list registered projects
atlas projects remove <path>     # unregister a project
```

### `atlas .` Behavior

```
atlas .
  → Is atlas-out/graph.json present?
  ├── Yes → load graph, start server, open browser
  └── No → L0+L1 scan, save graph, start server, open browser
  → Auto-opens http://localhost:7100 in default browser
```

One command. That's it.

---

## 11. Performance Targets

| Action | Target |
|---|---|
| Open recent project (cached) | < 500ms |
| L0 file listing (1000 files) | < 1 second |
| L1 structure scan (100 files) | < 10 seconds |
| L1 incremental (3 files changed) | < 2 seconds |
| Project switch | < 1 second |
| Sidebar render | < 100ms |
| Content panel render | < 200ms |

---

## 12. Agent Integration — Skills & MCP

### 12.1 How Agents Use Atlas

Agents interact with Atlas in two modes:

**Mode 1 — Navigation (read).** The agent queries the graph to navigate code and knowledge instead of searching blind. Before any `grep` or `glob`, the agent checks the graph first.

**Mode 2 — Enrichment (write).** When the agent discovers a relationship during its work (e.g., "auth depends on billing"), it creates the edge in the graph and proposes a wiki page. The knowledge base grows passively as agents work.

Both modes use the same channel: **MCP** if the Atlas server is running, **CLI** (`atlas query`, `atlas scan --deep`) if not.

### 12.2 Skills Design — 2 Skills, Not 7

Inspired by Hermes's native LLM Wiki skill (476 lines, 1 skill that does everything). We consolidate from 7 skills to 2:

**Skill 1: `/atlas`** (~400 lines) — the main skill. One entry point for everything.

```
/atlas                        → orientation + brief (like /atlas-start)
/atlas scan .                 → scan a folder
/atlas scan . --deep          → LLM-enriched scan (triggers /atlas-deep)
/atlas query "auth"           → graph traversal
/atlas ingest <url>           → ingest a source
/atlas audit                  → health check
/atlas finish                 → end-of-session write-back
```

**Skill 2: `/atlas-deep`** (~150 lines) — LLM enrichment. Separate because it costs tokens.

```
/atlas-deep                   → enrich current project graph with LLM
/atlas-deep <path>            → enrich a specific folder
```

**Why 2 instead of 7:** The user types `/atlas` and has everything. No need to remember `/atlas-start` vs `/atlas-finish` vs `/atlas-ingest`. The skill detects context (session start? end? query?) and adapts. Like Hermes LLM Wiki — one skill, multiple operations.

**Patterns borrowed from Hermes LLM Wiki:**

| Pattern | What it does | Where in `/atlas` |
|---|---|---|
| **Configurable project path** | Agent knows where the project is without hardcoding | Reads from config or `$CWD` |
| **Mandatory orientation** | Every session: read AGENTS.md → index.md → last 30 log entries | First thing when `/atlas` is invoked without arguments |
| **Page Thresholds** | Create page when entity in 2+ sources OR central to one. No pages for passing mentions. | Ingest and finish operations |
| **Update Policy** | On contradiction: note both positions with dates, mark frontmatter, flag for review | Ingest and finish operations |
| **Cross-reference enforcement** | Every page links to 2+ other pages via `[[wikilinks]]` | All write operations |
| **Scaling rules** | Index > 50 per section → split. Log > 500 → rotate. Page > 200 lines → split. | Audit operation |
| **Compile batch** | Ingest all `raw/untracked/` in one pass (one search, not N) | Scan operation |

### 12.3 MCP vs CLI — Automatic Detection

The skill works in two modes transparently:

```
/atlas invoked
    │
    ├── Atlas server running? (curl localhost:7100/api/health)
    │   └── Yes → MCP mode
    │       All operations via MCP tools (atlas.query, atlas.scan, etc.)
    │       Dashboard updates in real-time via WebSocket
    │
    └── No → CLI mode
        All operations via CLI (atlas query, atlas scan, atlas audit)
        Works offline, no dashboard needed
```

The agent checks once at session start. The user never chooses or configures.

### 12.4 Installation — `atlas install`

One command installs skills for every agent on the machine:

```bash
atlas install
```

Detection and installation per platform:

```
atlas install
    │
    ├── Copy skills to ~/.agents/skills/atlas/ and ~/.agents/skills/atlas-deep/
    │   (source of truth — agentskills.io convention)
    │
    ├── Claude Code (~/.claude/ exists?)
    │   ├── Symlink ~/.agents/skills/atlas → ~/.claude/skills/atlas
    │   ├── Symlink ~/.agents/skills/atlas-deep → ~/.claude/skills/atlas-deep
    │   └── Install PreToolUse hook in .claude/settings.json:
    │       "If atlas-out/graph.json exists, use atlas query before Glob/Grep"
    │
    ├── Codex (~/.codex/ or ~/.agents/ exists?)
    │   └── Already in ~/.agents/skills/ → Codex sees it natively
    │
    ├── Cursor (~/.cursor/ exists?)
    │   ├── Symlink ~/.agents/skills/atlas → ~/.cursor/skills/atlas
    │   └── Symlink ~/.agents/skills/atlas-deep → ~/.cursor/skills/atlas-deep
    │
    ├── Hermes (~/.hermes/ exists?)
    │   ├── Symlink ~/.agents/skills/atlas → ~/.hermes/skills/atlas
    │   ├── Symlink ~/.agents/skills/atlas-deep → ~/.hermes/skills/atlas-deep
    │   └── Symlink into each profile (~/.hermes/profiles/*/skills/)
    │
    ├── Windsurf (~/.codeium/ exists?)
    │   └── Scans ~/.agents/skills/ natively — no symlinks needed
    │
    └── GitHub Copilot (~/.copilot/ exists?)
        └── Scans ~/.agents/skills/ natively — no symlinks needed
```

**Uninstall:** `atlas uninstall` removes all symlinks and hooks.

**Report:**
```
$ atlas install
Atlas skills installed:
  ✅ Claude Code — 2 skills + PreToolUse hook
  ✅ Codex — native (~/.agents/skills/)
  ✅ Hermes — 2 skills + 1 profile (anna)
  ⬚ Cursor — not detected
  ⬚ Windsurf — not detected

Type /atlas in any agent to get started.
```

**What Atlas adds that LLM Wiki doesn't have:**

| Feature | What it does | How |
|---|---|---|
| **Graph-first navigation** | Agent checks graph before grepping. `atlas query auth` → traverses graph → finds relevant files in 100ms instead of reading 200 files | `/atlas-start` tells agent: "Graph exists. Use `atlas query` before `grep`." |
| **Active enrichment** | Agent discovers a relation → creates edge in graph + proposes wiki page | `/atlas-finish` collects discoveries, writes edges via MCP |
| **MCP channel** | Agent talks to Atlas server in real-time, not just reading files | All skills can use MCP tools if server is running, fallback to CLI |
| **Graph-aware audit** | God nodes, surprising connections, orphan detection via graph topology | `/atlas-health` runs analyzer on graph, not just wikilinks |

### 12.5 Skill Behaviors

**`/atlas` (no arguments) — Session Orientation**

```
1. Locate project: config path > $CWD > ask user
2. Detect mode: MCP (server running) or CLI
3. MANDATORY ORIENTATION:
   a. Read AGENTS.md (conventions, schemas)
   b. Read wiki/index.md (what exists)
   c. Read last 30 lines of wiki/log.md (recent activity)
   d. Read graph stats (nodes, edges, communities, health)
4. Check for changes since last session
5. Brief the user + propose next actions
```

**`/atlas scan <path>` — Discovery**

```
1. L0+L1 scan (free, AST + regex)
2. Build/update graph + Linker sync
3. Report: "Found X nodes, Y edges, Z communities"
```

**`/atlas query "..."` — Graph Navigation**

```
1. Match nodes → BFS/DFS traversal
2. Return subgraph as context
3. If answer is valuable → file back to wiki
```

**`/atlas ingest <url>` — Source Integration**

```
1. Fetch + save to raw/ with auto frontmatter
2. L0+L1 scan of the new source
3. Apply Page Thresholds + Cross-reference enforcement
4. Update graph + index + log
```

**`/atlas audit` — Health Check**

```
1. God nodes, surprises, gaps, contradictions
2. Page Thresholds, cross-refs, scaling rules, staleness
3. Report with severity + suggested actions
```

**`/atlas finish` — Session End**

```
1. Collect discoveries → create graph edges
2. Apply Update Policy for contradictions
3. Write-back to wiki + sync graph
4. Update log with session summary
```

**`/atlas-deep` — LLM Enrichment**

```
1. Read current graph
2. Extract semantic relations cross-file via LLM
3. Extract concepts from PDFs/images via Vision
4. Add INFERRED edges to graph
5. Propose wiki pages for new concepts
```

### 12.6 The "Always-On" Hook (from graphify)

For Claude Code, install a PreToolUse hook that fires before every Glob and Grep:

```json
{
  "matcher": "Glob|Grep",
  "hooks": [{
    "type": "command",
    "command": "[ -f atlas-out/graph.json ] && echo 'Atlas: Knowledge graph exists. Use atlas query before searching raw files.'"
  }]
}
```

This nudges the agent to check the graph before grepping blindly. Installed via `atlas install --platform claude-code`.

For Codex/Cursor/Hermes, the equivalent is a line in AGENTS.md:

```
Before searching files, check if atlas-out/graph.json exists. If it does, use `atlas query` first — it's faster and finds connections that grep misses.
```

---

## 13. What This Does NOT Include

- No API key management in Atlas
- No built-in LLM calls (L2/L3 is always via agent)
- No real-time collaboration (that's ARA)
- No cloud storage (that's ARA)
- No code execution or debugging (it's an IDE for knowledge, not for running code)
