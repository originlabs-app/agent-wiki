# Atlas Explorer — Design Spec

**Date:** 2026-04-07
**Status:** Draft
**Author:** Pierre Beunardeau / Origin Labs
**Context:** Replaces the current "Wiki" view in the Atlas dashboard

---

## 1. Vision

The Explorer is an IDE for knowledge. Like VS Code is for code, Atlas Explorer is for any folder of files — code, docs, papers, images, wikis. You scan any directory, and Explorer gives you a navigable, structured view of everything in it.

It works with zero structure (random folder of 200 files) and gets better with structure (curated wiki pages, frontmatter, tags). The wiki is not a prerequisite — it's what agents build after the scan.

**Replaces:** The current "Wiki" tab in the dashboard nav.

**Inspired by:** VS Code (file tree + editor), Obsidian (backlinks + graph), Karpathy's vision of LLM workspaces.

---

## 2. Layout

Three-panel layout:

```
┌──────────────┬──────────────────────────────────────────────────┐
│   SIDEBAR    │              CONTENT PANEL                       │
│   (280px)    │              (flex-1)                             │
│              │                                                   │
│  [Overview]  │  Read mode:                                       │
│  [Files]     │  ┌──────────────────────────────────────────┐    │
│  [Wiki]      │  │  Rendered markdown / syntax-highlighted   │    │
│  [Communities]│  │  code / image preview                    │    │
│              │  │                                           │    │
│              │  │  + Backlinks section                      │    │
│              │  │  + Graph neighbors section                │    │
│              │  └──────────────────────────────────────────┘    │
│              │                                                   │
│              │  Edit mode (split):                               │
│              │  ┌───────────────┬──────────────────────────┐    │
│              │  │  Raw markdown │  Live rendered preview    │    │
│              │  │  (editable)   │  (auto-updates on type)  │    │
│              │  │               │                           │    │
│              │  └───────────────┴──────────────────────────┘    │
│              │  [Save] [Cancel]                                  │
└──────────────┴──────────────────────────────────────────────────┘
```

---

## 3. Sidebar — 4 Sections

### 3.1 Overview (always visible at top)

Quick stats banner:

```
945 nodes · 1051 edges · 56 communities
Health: 70 ██████████░░ 
```

Clicking the health score navigates to Audit view.

### 3.2 Files (collapsible tree)

File tree of everything that was scanned, exactly like VS Code sidebar.

```
📁 Files
├── 📁 src/
│   ├── 📄 auth.py          (12 connections)
│   ├── 📄 db.py             (8 connections)
│   └── 📄 api.py            (15 connections)
├── 📁 docs/
│   └── 📄 architecture.md   (6 connections)
├── 📁 raw/
│   ├── 📄 paper.pdf          (4 connections)
│   └── 📄 screenshot.png     (2 connections)
└── 📄 README.md              (3 connections)
```

- Files show connection count (degree in graph) as a subtle badge
- Color-coded by type (same colors as graph view: code=cyan, doc=purple, etc.)
- Click → opens in content panel
- Right-click or hover → "View in Graph" button
- Folders are collapsible, state persisted in localStorage
- If no files were scanned (wiki-only mode), this section shows "No files scanned. Run `atlas scan .` to populate."

### 3.3 Wiki (collapsible, grouped by type)

Curated wiki pages organized by type:

```
📝 Wiki (60 pages)
├── 📂 Concepts (26)
│   ├── Agent Aggregator Platform
│   ├── Agent Skills Convention       [skills] [standard]
│   ├── Atlas Knowledge Engine        [atlas] [ara]
│   ├── Discovery-Curation Fusion     [atlas] [innovation]
│   └── ...
├── 📂 Projects (10)
│   ├── ARA                           active
│   ├── agent-wiki                    active
│   ├── BSACopilot                    active
│   └── ...
├── 📂 Decisions (5)
│   ├── FastAPI over Express          2026-04-03
│   └── ...
└── 📂 Sources (11)
    ├── ARA PRD + GTM                 2026-04-03
    └── ...
```

- Pages show tags (as small badges) for concepts
- Pages show status (active/blocked/completed) for projects
- Pages show date for sources and decisions
- Click → opens in content panel
- Type groups show count, are collapsible
- If no wiki exists, shows "No wiki pages yet. Agents will create them during sessions."

### 3.4 Communities (collapsible)

Auto-detected topic clusters:

```
🏘️ Communities (56)
├── Auth & Security (12 nodes)        ████░
├── Billing & Payments (8 nodes)      ███░░
├── API Layer (15 nodes)              █████
├── Documentation (20 nodes)          ██████░
└── ... (show top 15, "Show all" button)
```

- Bar shows relative size
- Click → filters the graph view to this community + lists members in content panel
- Community names are auto-labeled by LLM (not "Community 0")
- If Leiden is not installed or 0 communities: "Install graspologic for community detection."

---

## 4. Content Panel

### 4.1 Read Mode (default)

When a file or wiki page is selected:

**Header:**
```
┌─────────────────────────────────────────────────────┐
│  # Authentication Module                             │
│  wiki/concepts/auth.md · wiki-concept · high         │
│  [tags: auth, security]                              │
│                                                      │
│  [Edit] [View in Graph] [View Source] [Copy Path]    │
└─────────────────────────────────────────────────────┘
```

**Body:**
- Markdown rendered via marked.js (already in the dashboard)
- Code blocks with syntax highlighting (highlight.js, already loaded)
- `[[wikilinks]]` rendered as clickable links → navigate within Explorer
- Images rendered inline

**Footer sections:**

```
── Backlinks (3) ──────────────────────────────
← billing.md ("See [[auth]] for authorization checks")
← acme.md (listed in Sources section)
← api-spec.md (referenced in Key Takeaways)

── Graph Neighbors (8) ────────────────────────
→ imports: db, jwt
→ calls: billing, session
→ tagged_with: auth, security
→ references: api-spec (EXTRACTED), billing (EXTRACTED)

── Metadata ───────────────────────────────────
Type: wiki-concept
Confidence: high
Updated: 2026-04-06
Updated by: agent
Community: Auth & Security (#3)
```

### 4.2 Edit Mode (split view)

Click "Edit" → content panel splits in two:

```
┌───────────────────┬───────────────────┐
│  Raw Markdown     │  Live Preview     │
│  (textarea/       │  (rendered,       │
│   CodeMirror)     │   auto-updates)   │
│                   │                   │
│  ---              │  # Auth Module    │
│  type: wiki-...   │                   │
│  title: "Auth"    │  JWT-based auth   │
│  ---              │  with session     │
│                   │  fallback.        │
│  # Auth Module    │                   │
│                   │  ## Key ideas     │
│  JWT-based auth   │  - JWT HS256      │
│  with session     │                   │
│  fallback.        │                   │
│                   │                   │
│  ## Key ideas     │                   │
│  - JWT HS256      │                   │
│                   │                   │
└───────────────────┴───────────────────┘
[Save] [Cancel]                  Editing auth.md
```

- Left: raw markdown with monospace font. Textarea for v1, CodeMirror for v1.1.
- Right: live preview re-rendered on every keystroke (debounced 200ms)
- Save → POST /api/wiki/write → triggers Linker sync → graph updates → WebSocket notifies
- Cancel → revert to read mode, no changes
- Frontmatter is editable (shown as raw YAML in the editor)

### 4.3 No Selection State

When nothing is selected (first load):

```
┌──────────────────────────────────────────────┐
│                                               │
│        📂 Select a file or page               │
│           from the sidebar                    │
│                                               │
│        Or scan a new directory:               │
│        atlas scan ~/my-folder                 │
│                                               │
└──────────────────────────────────────────────┘
```

### 4.4 Community View

When a community is selected from the sidebar:

```
┌──────────────────────────────────────────────┐
│  🏘️ Auth & Security                          │
│  12 nodes · 18 internal edges · cohesion 0.47│
│                                               │
│  [View in Graph]                              │
│                                               │
│  Key Members:                                 │
│  ● auth.py (15 connections) — god node        │
│  ● session.py (8 connections)                 │
│  ● jwt.py (6 connections)                     │
│  ● login.py (4 connections)                   │
│  ...                                          │
│                                               │
│  Cross-Community Links:                       │
│  → Billing & Payments (5 shared edges)        │
│  → API Layer (3 shared edges)                 │
│                                               │
│  Wiki Coverage:                               │
│  ✅ auth has a wiki page                       │
│  ❌ session — no wiki page (suggest creation?) │
│  ❌ jwt — no wiki page                         │
│                                               │
└──────────────────────────────────────────────┘
```

---

## 5. Interactions

### 5.1 Navigation

- Sidebar click → load in content panel (no full page reload, SPA)
- `[[wikilink]]` click in rendered content → navigate to that page in Explorer
- "View in Graph" → switch to Graph tab with that node focused/highlighted
- Browser back/forward works (hash-based routing: `#/explorer/wiki/concepts/auth`)
- Ctrl+K → quick search (already exists)

### 5.2 File Tree State

- Collapsed/expanded folders persisted in localStorage
- Last selected file persisted → reopened on page load
- File tree auto-updates via WebSocket when files change

### 5.3 Edit Flow

1. Click "Edit" → split view appears
2. Edit raw markdown on the left
3. Preview updates live on the right (debounced 200ms)
4. Click "Save" → `POST /api/wiki/write` with full content
5. Server writes file → Linker syncs wiki→graph → WebSocket broadcasts `wiki.changed`
6. Explorer receives WebSocket event → refreshes sidebar (page might have new tags, links)
7. Return to read mode

### 5.4 Context Menu (v1.1)

Right-click on any file/page in sidebar:
- View in Graph
- Copy path
- Open in terminal (VS Code link)
- Delete (with confirmation)

---

## 6. API Requirements

Existing endpoints used:
- `GET /api/wiki/pages` — list all wiki pages (sidebar Wiki section)
- `GET /api/wiki/search?q=` — search (Ctrl+K)
- `POST /api/wiki/read` — read a page (content panel)
- `POST /api/wiki/write` — save edits
- `GET /api/graph` — all nodes/edges (sidebar Files, Communities)
- `GET /api/audit` — health score (sidebar Overview)
- `GET /api/stats` — node/edge counts (sidebar Overview)

New endpoints needed:
- `GET /api/files` — list scanned files as a tree structure `[{path, type, degree, children}]`
- `GET /api/communities` — list communities with labels, sizes, cohesion `[{id, label, size, cohesion, members}]`
- `GET /api/file/read?path=src/auth.py` — read raw file content (for non-wiki files)

---

## 7. Tech Constraints

- Same stack as existing dashboard: vanilla JS, no build step, Tailwind CDN
- marked.js for markdown rendering (already loaded)
- highlight.js for code highlighting (already loaded)
- Textarea for edit mode (CodeMirror is a v1.1 upgrade)
- File tree: custom HTML/CSS, no external tree library (keep it lightweight)
- Responsive: sidebar collapses to icons on mobile (<768px)

---

## 8. Migration from current Wiki view

- Rename "Wiki" tab to "Explorer" in nav
- Current wiki.js → refactored into explorer.js (new file)
- All existing wiki rendering logic is preserved (just moved into the content panel)
- URL changes: `#/wiki` → `#/explorer`, `#/wiki/page` → `#/explorer/wiki/concepts/page`
- Old URLs redirect for backward compat

---

## 9. Performance

- Sidebar loads from cached API responses (graph + pages already fetched by Graph view)
- File tree is virtualized if >500 files (only render visible items)
- Content panel lazy-loads (no pre-fetching of all page contents)
- Edit preview debounced at 200ms
- Target: sidebar renders in <100ms, content panel in <200ms
