# Atlas Explorer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current "Wiki" tab with a full Explorer view — an IDE for knowledge. Sidebar with 4 sections (Overview, Files, Wiki, Communities), content panel with read/edit/community modes, 3 new API routes, hash-based routing, wikilink navigation. The Explorer is the primary way users interact with scanned files and wiki pages.

**Architecture:** Single `explorer.js` module replaces `wiki.js`. Same static-first pattern: vanilla JS, no build step, Tailwind CDN. The sidebar is a permanent left panel (280px), the content panel fills the rest. All state lives in module-scoped variables. Hash routing `#/explorer/*` with backward-compat redirects from `#/wiki/*`. Three new server endpoints provide file trees, communities, and raw file reads.

**Tech Stack:** HTML5, vanilla JS (ES2022 modules), Tailwind CSS 3.x CDN, marked.js (markdown), highlight.js (code blocks). Textarea for edit mode (v1). No external tree library.

**Depends on:** Plan 1 (Core models), Plan 2 (Server REST API), Plan 3 (Dashboard shell + app.js router). All 5 plans must be merged (265 tests passing).

**API contract — existing endpoints used:**

| Endpoint | Method | Returns |
|---|---|---|
| `/api/wiki/pages` | GET | `Page[]` (list with content + frontmatter) |
| `/api/wiki/search?q=` | GET | `Page[]` |
| `POST /api/wiki/read` | POST `{page}` | `{page: Page}` |
| `POST /api/wiki/write` | POST `{page, content, frontmatter}` | `{page}` |
| `/api/graph` | GET | `{nodes: [...], edges: [...]}` |
| `/api/audit` | GET | `AuditReport` with health_score |
| `/api/stats` | GET | `{stats: {nodes, edges, communities, health_score}}` |

**API contract — new endpoints (this plan creates them):**

| Endpoint | Method | Returns |
|---|---|---|
| `/api/files` | GET | `[{path, type, degree, children}]` — tree of scanned files |
| `/api/communities` | GET | `[{id, label, size, cohesion, members}]` — community list |
| `/api/file/read?path=` | GET | `{path, content, type}` — raw file content |

---

## File Map

```
atlas/
├── server/
│   ├── app.py              # MODIFY: add 3 new routes (/api/files, /api/communities, /api/file/read)
│   └── schemas.py          # MODIFY: add FileTreeNode, CommunitySchema, FileReadResponse
├── dashboard/
│   ├── index.html          # MODIFY: rename Wiki tab to Explorer, update href
│   ├── app.js              # MODIFY: register explorer, redirect #/wiki/* to #/explorer/*
│   ├── explorer.js         # CREATE: full Explorer view (replaces wiki.js)
│   ├── wiki.js             # KEEP: not deleted yet (Plan 3 code, remove in cleanup)
│   └── styles.css          # MODIFY: add explorer-specific styles

tests/
├── server/
│   └── test_explorer_api.py      # CREATE: tests for 3 new API routes
├── dashboard/
│   ├── test_explorer_exists.py   # CREATE: explorer.js exists + required exports
│   └── test_dashboard_served.py  # MODIFY: add explorer.js to required files list
```

---

## Task 1: Server — 3 New API Routes

**Files:**
- Modify: `atlas/server/schemas.py`
- Modify: `atlas/server/app.py`
- Create: `tests/server/test_explorer_api.py`

- [ ] **Step 1: Write the tests**

`tests/server/test_explorer_api.py`:
```python
"""Tests for the 3 Explorer API routes: /api/files, /api/communities, /api/file/read."""
import pytest
from pathlib import Path

from atlas.core.models import Node, Edge, Extraction
from atlas.server.app import create_app
from atlas.server.deps import create_engine_set, EventBus


@pytest.fixture
def engines(tmp_path):
    """Create engine set with a populated graph."""
    root = tmp_path
    # Create some files to scan
    (root / "src").mkdir()
    (root / "src" / "auth.py").write_text("# auth module\nimport jwt\n")
    (root / "src" / "db.py").write_text("# database module\n")
    (root / "docs").mkdir()
    (root / "docs" / "readme.md").write_text("# Project Readme\n")
    # Create wiki pages
    (root / "wiki" / "concepts").mkdir(parents=True)
    (root / "wiki" / "concepts" / "auth.md").write_text(
        "---\ntitle: Auth\ntype: wiki-concept\n---\n\nAuthentication module.\n"
    )

    es = create_engine_set(root)

    # Populate graph with nodes that have source_file pointing to real files
    extraction = Extraction(
        nodes=[
            Node(id="src/auth.py", label="auth.py", type="code", source_file="src/auth.py", community=0),
            Node(id="src/db.py", label="db.py", type="code", source_file="src/db.py", community=0),
            Node(id="docs/readme.md", label="readme.md", type="document", source_file="docs/readme.md", community=1),
            Node(id="wiki/concepts/auth", label="Auth", type="wiki-concept", source_file="wiki/concepts/auth.md", community=0),
        ],
        edges=[
            Edge(source="src/auth.py", target="src/db.py", relation="imports", confidence="EXTRACTED"),
            Edge(source="src/auth.py", target="wiki/concepts/auth", relation="references", confidence="EXTRACTED"),
            Edge(source="docs/readme.md", target="src/auth.py", relation="references", confidence="INFERRED"),
        ],
    )
    es.graph.merge(extraction)
    return es


@pytest.fixture
def client(engines):
    """TestClient for the API."""
    from fastapi.testclient import TestClient
    app = create_app(engines=engines, event_bus=EventBus())
    return TestClient(app)


class TestFilesEndpoint:
    def test_returns_tree_structure(self, client):
        resp = client.get("/api/files")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Should have top-level entries (src/, docs/, wiki/)
        paths = [item["path"] for item in data]
        assert any("src" in p for p in paths)

    def test_nodes_have_required_fields(self, client):
        resp = client.get("/api/files")
        data = resp.json()
        # Flatten to find a file node
        def find_files(nodes):
            files = []
            for n in nodes:
                if n.get("children"):
                    files.extend(find_files(n["children"]))
                else:
                    files.append(n)
            return files
        files = find_files(data)
        assert len(files) > 0
        f = files[0]
        assert "path" in f
        assert "type" in f
        assert "degree" in f

    def test_directory_nodes_have_children(self, client):
        resp = client.get("/api/files")
        data = resp.json()
        dirs = [item for item in data if item.get("children") is not None]
        assert len(dirs) > 0
        for d in dirs:
            assert isinstance(d["children"], list)


class TestCommunitiesEndpoint:
    def test_returns_community_list(self, client):
        resp = client.get("/api/communities")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_community_has_required_fields(self, client):
        resp = client.get("/api/communities")
        data = resp.json()
        if len(data) > 0:
            c = data[0]
            assert "id" in c
            assert "label" in c
            assert "size" in c
            assert "cohesion" in c
            assert "members" in c

    def test_community_members_are_node_ids(self, client, engines):
        resp = client.get("/api/communities")
        data = resp.json()
        all_node_ids = set(engines.graph.iter_node_ids())
        for c in data:
            for member in c["members"]:
                assert member in all_node_ids


class TestFileReadEndpoint:
    def test_read_existing_file(self, client):
        resp = client.get("/api/file/read", params={"path": "src/auth.py"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["path"] == "src/auth.py"
        assert "auth module" in data["content"]

    def test_read_nonexistent_file_returns_404(self, client):
        resp = client.get("/api/file/read", params={"path": "src/nonexistent.py"})
        assert resp.status_code == 404

    def test_path_traversal_blocked(self, client):
        resp = client.get("/api/file/read", params={"path": "../../etc/passwd"})
        assert resp.status_code in (400, 403, 404, 422)

    def test_read_markdown_file(self, client):
        resp = client.get("/api/file/read", params={"path": "docs/readme.md"})
        assert resp.status_code == 200
        data = resp.json()
        assert "Readme" in data["content"]
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/server/test_explorer_api.py -v`
Expected: FAIL — routes don't exist yet.

- [ ] **Step 3: Add response schemas**

In `atlas/server/schemas.py`, add at the end before `ErrorResponse`:

```python
class FileTreeNode(BaseModel):
    """A node in the file tree (file or directory)."""
    path: str
    name: str
    type: str  # "directory" | node type (code, document, etc.)
    degree: int = 0
    children: list["FileTreeNode"] | None = None  # None for files, list for dirs


class CommunitySchema(BaseModel):
    """A detected community cluster."""
    id: int
    label: str
    size: int
    cohesion: float = 0.0
    members: list[str] = Field(default_factory=list)


class FileReadResponse(BaseModel):
    """Raw file content response."""
    path: str
    content: str
    type: str  # guessed file type
```

- [ ] **Step 4: Add the 3 routes to app.py**

In `atlas/server/app.py`, add these imports at the top schemas import block:

```python
from atlas.server.schemas import (
    # ... existing imports ...
    FileTreeNode,
    CommunitySchema,
    FileReadResponse,
)
```

Then add 3 new route blocks inside `create_app()`, after the `# --- Audit ---` section and before `# --- Suggest Links ---`:

```python
    # --- Explorer: Files ---

    @app.get("/api/files", response_model=list[FileTreeNode])
    def get_files():
        """Return the scanned file tree with degree counts.

        Builds a hierarchical tree from all graph nodes that have a source_file.
        Each file node includes its degree (connection count) from the graph.
        """
        # Collect all unique source files from graph nodes
        file_set: dict[str, dict] = {}  # path -> {type, degree}
        for nid in engines.graph.iter_node_ids():
            data = engines.graph.get_node_data(nid)
            sf = data.get("source_file", "")
            if not sf:
                continue
            node_type = data.get("type", "unknown")
            degree = engines.graph.degree(nid)
            # Keep highest degree if multiple nodes map to same file
            if sf not in file_set or degree > file_set[sf]["degree"]:
                file_set[sf] = {"type": node_type, "degree": degree}

        # Build tree structure
        tree: dict = {}  # nested dict: {name: {__children__: {...}, __meta__: ...}}
        for path, meta in sorted(file_set.items()):
            parts = path.split("/")
            current = tree
            for i, part in enumerate(parts):
                if part not in current:
                    current[part] = {"__children__": {}, "__meta__": None}
                if i == len(parts) - 1:
                    # Leaf file
                    current[part]["__meta__"] = {
                        "path": path,
                        "type": meta["type"],
                        "degree": meta["degree"],
                    }
                current = current[part]["__children__"]

        def to_tree_nodes(subtree: dict, prefix: str = "") -> list[dict]:
            nodes = []
            for name, entry in sorted(subtree.items()):
                full_path = f"{prefix}{name}" if not prefix else f"{prefix}/{name}"
                meta = entry["__meta__"]
                children_dict = entry["__children__"]

                if children_dict:
                    # Directory
                    children = to_tree_nodes(children_dict, full_path)
                    # Sum degrees of all children for the directory
                    total_degree = sum(c.get("degree", 0) for c in children)
                    nodes.append({
                        "path": full_path,
                        "name": name,
                        "type": "directory",
                        "degree": total_degree,
                        "children": children,
                    })
                elif meta:
                    # File
                    nodes.append({
                        "path": meta["path"],
                        "name": name,
                        "type": meta["type"],
                        "degree": meta["degree"],
                        "children": None,
                    })
            return nodes

        return to_tree_nodes(tree)

    # --- Explorer: Communities ---

    @app.get("/api/communities", response_model=list[CommunitySchema])
    def get_communities():
        """Return detected communities with labels, sizes, cohesion scores.

        Groups nodes by their `community` attribute, computes internal edge
        density (cohesion), and labels each community by its highest-degree
        member node's label.
        """
        # Group nodes by community
        communities: dict[int, list[str]] = {}
        for nid in engines.graph.iter_node_ids():
            data = engines.graph.get_node_data(nid)
            comm = data.get("community")
            if comm is not None:
                communities.setdefault(comm, []).append(nid)

        result = []
        for comm_id, members in sorted(communities.items()):
            member_set = set(members)
            # Count internal edges
            internal_edges = 0
            for u, v in engines.graph.iter_edges(data=False):
                if u in member_set and v in member_set:
                    internal_edges += 1

            # Cohesion = internal edges / max possible edges
            n = len(members)
            max_edges = n * (n - 1) if n > 1 else 1
            cohesion = round(internal_edges / max_edges, 2) if max_edges > 0 else 0.0

            # Label = highest-degree member's label
            best_member = max(members, key=lambda m: engines.graph.degree(m))
            best_data = engines.graph.get_node_data(best_member)
            label = best_data.get("label", best_member)

            result.append(CommunitySchema(
                id=comm_id,
                label=label,
                size=n,
                cohesion=cohesion,
                members=members,
            ))

        # Sort by size descending
        result.sort(key=lambda c: -c.size)
        return result

    # --- Explorer: File Read ---

    @app.get("/api/file/read", response_model=FileReadResponse)
    def read_file(path: str):
        """Read raw content of a scanned file (non-wiki files).

        Uses the storage backend, so path traversal is blocked.
        """
        try:
            content = engines.storage.read(path)
        except ValueError:
            # Path traversal blocked
            raise AtlasValidationError(f"Invalid path: {path}")

        if content is None:
            raise AtlasNotFoundError(f"File not found: {path}")

        # Guess type from extension
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        type_map = {
            "py": "code", "js": "code", "ts": "code", "rs": "code",
            "go": "code", "java": "code", "rb": "code", "c": "code",
            "cpp": "code", "h": "code", "sh": "code", "yaml": "code",
            "yml": "code", "toml": "code", "json": "code",
            "md": "document", "txt": "document", "rst": "document",
            "pdf": "paper", "png": "image", "jpg": "image",
            "jpeg": "image", "gif": "image", "svg": "image",
        }
        file_type = type_map.get(ext, "unknown")

        return FileReadResponse(path=path, content=content, type=file_type)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/server/test_explorer_api.py -v`
Expected: All tests pass.

- [ ] **Step 6: Run full test suite to confirm no regressions**

Run: `python -m pytest --tb=short -q`
Expected: 265+ tests pass, 0 fail.

---

## Task 2: Dashboard — Explorer Sidebar

**Files:**
- Create: `atlas/dashboard/explorer.js` (sidebar portion only)
- Create: `tests/dashboard/test_explorer_exists.py`

This task builds the left sidebar panel with 4 sections: Overview, Files (tree), Wiki (grouped), Communities. Content panel is a placeholder — Task 3 fills it in.

- [ ] **Step 1: Write the test**

`tests/dashboard/test_explorer_exists.py`:
```python
"""Verify explorer.js exists and has the required module exports."""
from pathlib import Path


def test_explorer_js_exists():
    explorer = Path(__file__).parent.parent.parent / "atlas" / "dashboard" / "explorer.js"
    assert explorer.exists(), "explorer.js must exist in atlas/dashboard/"
    content = explorer.read_text()
    assert "export async function init" in content
    assert "export function destroy" in content


def test_explorer_has_sidebar_sections():
    explorer = Path(__file__).parent.parent.parent / "atlas" / "dashboard" / "explorer.js"
    content = explorer.read_text()
    # Sidebar must reference all 4 sections
    assert "Overview" in content or "overview" in content
    assert "Files" in content or "file-tree" in content
    assert "Wiki" in content or "wiki-list" in content
    assert "Communities" in content or "communities" in content


def test_explorer_imports_app():
    explorer = Path(__file__).parent.parent.parent / "atlas" / "dashboard" / "explorer.js"
    content = explorer.read_text()
    assert "from '/dashboard/app.js'" in content or "from \"/dashboard/app.js\"" in content
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/dashboard/test_explorer_exists.py -v`
Expected: FAIL — explorer.js doesn't exist yet.

- [ ] **Step 3: Create explorer.js — Sidebar**

`atlas/dashboard/explorer.js`:
```javascript
/**
 * Atlas Dashboard — Explorer View
 * IDE for knowledge: sidebar (overview, files, wiki, communities) + content panel.
 * Replaces wiki.js.
 */

import { api, on, emit, toast } from '/dashboard/app.js';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let currentSelection = null;  // { type: 'wiki'|'file'|'community', path|id }
let isEditing = false;
let sidebarData = { stats: null, files: [], pages: [], communities: [] };
let folderState = {};  // path -> collapsed boolean (persisted in localStorage)
let wsUnsubs = [];
let editDebounceTimer = null;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const NODE_COLORS = {
    code:            '#22d3ee',
    document:        '#a78bfa',
    paper:           '#f472b6',
    image:           '#fb923c',
    'wiki-page':     '#338dff',
    'wiki-concept':  '#34d399',
    'wiki-decision': '#fbbf24',
    'wiki-source':   '#94a3b8',
    directory:       '#6b7280',
    unknown:         '#6b7280',
};

const TYPE_LABELS = {
    'wiki-concept': 'Concepts',
    'wiki-page': 'Pages',
    'wiki-decision': 'Decisions',
    'wiki-source': 'Sources',
    'other': 'Other',
};

const TYPE_ORDER = ['wiki-concept', 'wiki-page', 'wiki-decision', 'wiki-source', 'other'];

// ---------------------------------------------------------------------------
// LocalStorage helpers
// ---------------------------------------------------------------------------

function loadFolderState() {
    try {
        const stored = localStorage.getItem('atlas-explorer-folders');
        if (stored) folderState = JSON.parse(stored);
    } catch { /* ignore */ }
}

function saveFolderState() {
    try {
        localStorage.setItem('atlas-explorer-folders', JSON.stringify(folderState));
    } catch { /* ignore */ }
}

function loadLastSelection() {
    try {
        const stored = localStorage.getItem('atlas-explorer-selection');
        if (stored) return JSON.parse(stored);
    } catch { /* ignore */ }
    return null;
}

function saveLastSelection(sel) {
    try {
        localStorage.setItem('atlas-explorer-selection', JSON.stringify(sel));
    } catch { /* ignore */ }
}

// ---------------------------------------------------------------------------
// Markdown Renderer Setup
// ---------------------------------------------------------------------------

function createRenderer() {
    const renderer = new marked.Renderer();

    // Wikilinks: [[target]] or [[target|display]]
    const originalParagraph = renderer.paragraph.bind(renderer);
    renderer.paragraph = function (text) {
        const withLinks = text.replace(
            /\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g,
            (_, target, display) => {
                const slug = target.trim();
                const label = (display || target).trim();
                return `<a href="#/explorer/wiki/${encodeURIComponent(slug)}" class="wikilink" data-target="${slug}">${label}</a>`;
            }
        );
        return originalParagraph(withLinks);
    };

    // Code blocks with highlight.js
    renderer.code = function (code, language) {
        const lang = language && hljs.getLanguage(language) ? language : 'plaintext';
        const highlighted = hljs.highlight(code, { language: lang }).value;
        return `<pre><code class="hljs language-${lang}">${highlighted}</code></pre>`;
    };

    return renderer;
}

const markedOptions = {
    renderer: createRenderer(),
    breaks: true,
    gfm: true,
};

// ---------------------------------------------------------------------------
// HTML Helpers
// ---------------------------------------------------------------------------

function escapeHtml(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function addHeadingIds(html) {
    return html.replace(
        /<h([1-3])([^>]*)>(.*?)<\/h\1>/gi,
        (_, level, attrs, text) => {
            const plainText = text.replace(/<[^>]+>/g, '');
            const id = plainText.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
            return `<h${level}${attrs} id="${id}">${text}</h${level}>`;
        }
    );
}

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadSidebarData() {
    const [statsRes, filesRes, pagesRes, commRes] = await Promise.allSettled([
        api.get('/api/stats'),
        api.get('/api/files'),
        api.get('/api/wiki/pages'),
        api.get('/api/communities'),
    ]);

    sidebarData.stats = statsRes.status === 'fulfilled' ? statsRes.value : null;
    sidebarData.files = filesRes.status === 'fulfilled' ? filesRes.value : [];
    sidebarData.pages = pagesRes.status === 'fulfilled' ? pagesRes.value : [];
    sidebarData.communities = commRes.status === 'fulfilled' ? commRes.value : [];
}

// ---------------------------------------------------------------------------
// Sidebar: Overview Section
// ---------------------------------------------------------------------------

function renderOverview() {
    const stats = sidebarData.stats?.stats;
    if (!stats) {
        return `
            <div class="px-3 py-2 text-xs text-gray-500">
                No data yet. Run <code class="text-atlas-400">atlas scan</code>.
            </div>
        `;
    }

    const healthPct = Math.max(0, Math.min(100, Math.round(stats.health_score)));
    const healthColor = healthPct >= 70 ? '#34d399' : healthPct >= 40 ? '#fbbf24' : '#f87171';
    const filledBlocks = Math.round(healthPct / 10);
    const bar = '\u2588'.repeat(filledBlocks) + '\u2591'.repeat(10 - filledBlocks);

    return `
        <div class="px-3 py-2">
            <div class="text-xs text-gray-400">
                <span class="text-gray-200 font-medium">${stats.nodes}</span> nodes
                <span class="mx-1 text-gray-600">&middot;</span>
                <span class="text-gray-200 font-medium">${stats.edges}</span> edges
                <span class="mx-1 text-gray-600">&middot;</span>
                <span class="text-gray-200 font-medium">${stats.communities}</span> communities
            </div>
            <a href="#/audit" class="flex items-center gap-2 mt-1.5 text-xs group">
                <span class="text-gray-500 group-hover:text-gray-300 transition-colors">Health:</span>
                <span class="font-mono text-[10px] tracking-wider" style="color: ${healthColor}">${healthPct} ${bar}</span>
            </a>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Sidebar: File Tree Section
// ---------------------------------------------------------------------------

function renderFileTree(nodes, depth = 0) {
    if (!nodes || !nodes.length) {
        if (depth === 0) {
            return `
                <div class="px-3 py-2 text-xs text-gray-500">
                    No files scanned. Run <code class="text-atlas-400">atlas scan .</code> to populate.
                </div>
            `;
        }
        return '';
    }

    return nodes.map(node => {
        const isDir = node.children !== null && node.children !== undefined;
        const isCollapsed = folderState[node.path] !== false; // collapsed by default
        const indent = depth * 16;
        const color = NODE_COLORS[node.type] || NODE_COLORS.unknown;
        const isActive = currentSelection?.type === 'file' && currentSelection?.path === node.path;

        if (isDir) {
            const arrow = isCollapsed ? '\u25B6' : '\u25BC';
            return `
                <div>
                    <div class="flex items-center gap-1 px-3 py-1 text-xs cursor-pointer hover:bg-surface-2 transition-colors group"
                         style="padding-left: ${12 + indent}px"
                         data-action="toggle-folder" data-path="${escapeHtml(node.path)}">
                        <span class="text-gray-500 text-[9px] w-3 shrink-0">${arrow}</span>
                        <span class="text-gray-400 group-hover:text-gray-200 transition-colors truncate">${escapeHtml(node.name)}/</span>
                        ${node.degree > 0 ? `<span class="ml-auto text-[10px] text-gray-600 shrink-0">${node.degree}</span>` : ''}
                    </div>
                    ${isCollapsed ? '' : `<div>${renderFileTree(node.children, depth + 1)}</div>`}
                </div>
            `;
        }

        // File leaf
        return `
            <a href="#/explorer/file/${encodeURIComponent(node.path)}"
               class="flex items-center gap-1.5 px-3 py-1 text-xs cursor-pointer hover:bg-surface-2 transition-colors group ${isActive ? 'bg-surface-2 text-white' : ''}"
               style="padding-left: ${12 + indent + 16}px">
                <span class="w-2 h-2 rounded-full shrink-0" style="background: ${color}"></span>
                <span class="truncate ${isActive ? 'text-white' : 'text-gray-400 group-hover:text-gray-200'} transition-colors">${escapeHtml(node.name)}</span>
                ${node.degree > 0 ? `<span class="ml-auto text-[10px] text-gray-600 shrink-0">(${node.degree})</span>` : ''}
            </a>
        `;
    }).join('');
}

// ---------------------------------------------------------------------------
// Sidebar: Wiki Section
// ---------------------------------------------------------------------------

function renderWikiList() {
    const pages = sidebarData.pages;
    if (!pages || !pages.length) {
        return `
            <div class="px-3 py-2 text-xs text-gray-500">
                No wiki pages yet. Agents will create them during sessions.
            </div>
        `;
    }

    // Group by type
    const grouped = {};
    pages.forEach(p => {
        const type = p.type || 'other';
        const key = TYPE_ORDER.includes(type) ? type : 'other';
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push(p);
    });

    return TYPE_ORDER.filter(t => grouped[t]?.length).map(type => {
        const items = grouped[type].sort((a, b) => a.title.localeCompare(b.title));
        const groupKey = `wiki-group-${type}`;
        const isCollapsed = folderState[groupKey] === true;

        return `
            <div>
                <div class="flex items-center gap-1 px-3 py-1 text-xs cursor-pointer hover:bg-surface-2 transition-colors group"
                     data-action="toggle-folder" data-path="${groupKey}">
                    <span class="text-gray-500 text-[9px] w-3 shrink-0">${isCollapsed ? '\u25B6' : '\u25BC'}</span>
                    <span class="text-gray-400 group-hover:text-gray-200 transition-colors">${TYPE_LABELS[type] || type}</span>
                    <span class="text-[10px] text-gray-600 ml-1">(${items.length})</span>
                </div>
                ${isCollapsed ? '' : `
                    <div>
                        ${items.map(page => {
                            const slug = page.path.replace(/\.md$/, '').split('/').pop();
                            const isActive = currentSelection?.type === 'wiki' && currentSelection?.path === page.path;
                            const tags = page.frontmatter?.tags || [];
                            const status = page.frontmatter?.status;
                            const date = page.frontmatter?.updated || page.frontmatter?.date;

                            return `
                                <a href="#/explorer/wiki/${encodeURIComponent(slug)}"
                                   class="flex items-center gap-1.5 px-3 py-1 text-xs cursor-pointer hover:bg-surface-2 transition-colors ${isActive ? 'bg-surface-2' : ''}"
                                   style="padding-left: 28px">
                                    <span class="truncate ${isActive ? 'text-white' : 'text-gray-400 hover:text-gray-200'} transition-colors">${escapeHtml(page.title)}</span>
                                    <span class="ml-auto flex items-center gap-1 shrink-0">
                                        ${tags.slice(0, 2).map(t => `<span class="px-1 py-0 bg-surface-3 rounded text-[9px] text-gray-500">${t}</span>`).join('')}
                                        ${status ? `<span class="text-[10px] text-gray-500">${status}</span>` : ''}
                                        ${date && !status ? `<span class="text-[10px] text-gray-600">${typeof date === 'string' ? date.slice(0, 10) : date}</span>` : ''}
                                    </span>
                                </a>
                            `;
                        }).join('')}
                    </div>
                `}
            </div>
        `;
    }).join('');
}

// ---------------------------------------------------------------------------
// Sidebar: Communities Section
// ---------------------------------------------------------------------------

function renderCommunities() {
    const communities = sidebarData.communities;
    if (!communities || !communities.length) {
        return `
            <div class="px-3 py-2 text-xs text-gray-500">
                Install <code class="text-atlas-400">graspologic</code> for community detection.
            </div>
        `;
    }

    const maxSize = Math.max(...communities.map(c => c.size));
    const displayCount = 15;
    const visible = communities.slice(0, displayCount);
    const hasMore = communities.length > displayCount;

    return `
        <div>
            ${visible.map(c => {
                const barWidth = Math.round((c.size / maxSize) * 100);
                const isActive = currentSelection?.type === 'community' && currentSelection?.id === c.id;

                return `
                    <a href="#/explorer/community/${c.id}"
                       class="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer hover:bg-surface-2 transition-colors ${isActive ? 'bg-surface-2' : ''}">
                        <span class="truncate ${isActive ? 'text-white' : 'text-gray-400'} transition-colors flex-1">${escapeHtml(c.label)}</span>
                        <span class="text-[10px] text-gray-600 shrink-0">${c.size}</span>
                        <div class="w-12 h-1.5 bg-surface-3 rounded-full shrink-0 overflow-hidden">
                            <div class="h-full bg-atlas-600 rounded-full" style="width: ${barWidth}%"></div>
                        </div>
                    </a>
                `;
            }).join('')}
            ${hasMore ? `
                <button class="px-3 py-1 text-[10px] text-atlas-400 hover:text-atlas-300 transition-colors"
                        data-action="show-all-communities">
                    Show all ${communities.length} communities
                </button>
            ` : ''}
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Full Sidebar Render
// ---------------------------------------------------------------------------

function renderSidebar() {
    return `
        <aside id="explorer-sidebar" class="w-72 shrink-0 border-r border-surface-3 bg-surface-1 flex flex-col overflow-hidden">
            <!-- Overview -->
            <div class="border-b border-surface-3">
                <div class="px-3 py-2 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Overview</div>
                ${renderOverview()}
            </div>

            <!-- Scrollable sections -->
            <div class="flex-1 overflow-y-auto">
                <!-- Files -->
                <div class="border-b border-surface-3">
                    <div class="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-surface-2 transition-colors"
                         data-action="toggle-folder" data-path="__section_files">
                        <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Files</span>
                        <span class="text-[9px] text-gray-600">${folderState.__section_files === true ? '\u25B6' : '\u25BC'}</span>
                    </div>
                    ${folderState.__section_files === true ? '' : `<div class="pb-2">${renderFileTree(sidebarData.files)}</div>`}
                </div>

                <!-- Wiki -->
                <div class="border-b border-surface-3">
                    <div class="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-surface-2 transition-colors"
                         data-action="toggle-folder" data-path="__section_wiki">
                        <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                            Wiki
                            <span class="text-gray-600 font-normal">(${sidebarData.pages.length})</span>
                        </span>
                        <span class="text-[9px] text-gray-600">${folderState.__section_wiki === true ? '\u25B6' : '\u25BC'}</span>
                    </div>
                    ${folderState.__section_wiki === true ? '' : `<div class="pb-2">${renderWikiList()}</div>`}
                </div>

                <!-- Communities -->
                <div>
                    <div class="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-surface-2 transition-colors"
                         data-action="toggle-folder" data-path="__section_communities">
                        <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                            Communities
                            <span class="text-gray-600 font-normal">(${sidebarData.communities.length})</span>
                        </span>
                        <span class="text-[9px] text-gray-600">${folderState.__section_communities === true ? '\u25B6' : '\u25BC'}</span>
                    </div>
                    ${folderState.__section_communities === true ? '' : `<div class="pb-2">${renderCommunities()}</div>`}
                </div>
            </div>
        </aside>
    `;
}

// ---------------------------------------------------------------------------
// Content Panel: No Selection
// ---------------------------------------------------------------------------

function renderNoSelection() {
    return `
        <div class="flex items-center justify-center h-full">
            <div class="text-center max-w-sm">
                <svg class="w-12 h-12 text-gray-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                </svg>
                <p class="text-gray-400 font-medium mb-1">Select a file or page</p>
                <p class="text-gray-600 text-sm mb-3">from the sidebar</p>
                <p class="text-gray-600 text-xs">
                    Or scan a new directory:<br>
                    <code class="text-atlas-400 bg-surface-2 px-2 py-0.5 rounded text-xs">atlas scan ~/my-folder</code>
                </p>
            </div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Content Panel: Wiki Page — Read Mode
// ---------------------------------------------------------------------------

async function loadAndRenderWikiPage(slug, contentEl) {
    contentEl.innerHTML = `
        <div class="flex items-center justify-center h-full">
            <svg class="w-8 h-8 text-atlas-500 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" opacity="0.2"/>
                <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
        </div>
    `;

    try {
        // Find page path from slug
        const page = sidebarData.pages.find(p => {
            const pageSlug = p.path.replace(/\.md$/, '').split('/').pop();
            return pageSlug === slug;
        });

        if (!page) {
            contentEl.innerHTML = renderPageNotFound(slug);
            return;
        }

        currentSelection = { type: 'wiki', path: page.path };
        saveLastSelection(currentSelection);
        renderWikiReadMode(page, contentEl);
    } catch (err) {
        contentEl.innerHTML = `<div class="p-6 text-red-400">Failed to load page: ${escapeHtml(err.message)}</div>`;
    }
}

function renderPageNotFound(slug) {
    return `
        <div class="max-w-3xl mx-auto px-6 py-6">
            <div class="text-center py-16">
                <p class="text-5xl font-bold text-gray-700 mb-3">Page Not Found</p>
                <p class="text-gray-500 mb-4">No wiki page for "<span class="text-gray-300">${escapeHtml(slug)}</span>"</p>
                <a href="#/explorer" class="text-atlas-400 hover:text-atlas-300 text-sm">Back to Explorer</a>
            </div>
        </div>
    `;
}

async function renderWikiReadMode(page, contentEl) {
    const slug = page.path.replace(/\.md$/, '').split('/').pop();

    // Parse frontmatter to get body only
    let body = page.content;
    const fmMatch = body.match(/^---\n[\s\S]*?\n---\n/);
    if (fmMatch) {
        body = body.slice(fmMatch[0].length);
    }

    let html = marked.parse(body, markedOptions);
    html = addHeadingIds(html);

    // Frontmatter display
    const fm = page.frontmatter || {};
    const skipKeys = new Set(['title', 'type']);
    const fmEntries = Object.entries(fm).filter(([k]) => !skipKeys.has(k));

    // Breadcrumbs
    const parts = page.path.replace(/\.md$/, '').split('/').filter(Boolean);
    const breadcrumbs = [{ label: 'Explorer', href: '#/explorer' }];
    parts.forEach((part, i) => {
        breadcrumbs.push({
            label: part.charAt(0).toUpperCase() + part.slice(1),
            href: i === parts.length - 1 ? null : null,
        });
    });

    // Tags from frontmatter
    const tags = fm.tags || [];

    contentEl.innerHTML = `
        <div class="max-w-3xl mx-auto px-6 py-6">
            <!-- Breadcrumbs -->
            <nav class="flex items-center gap-1.5 text-xs text-gray-500 mb-4">
                ${breadcrumbs.map((c, i) => {
                    const sep = i > 0 ? '<span class="text-gray-600">/</span>' : '';
                    if (c.href) {
                        return `${sep}<a href="${c.href}" class="hover:text-gray-300 transition-colors">${c.label}</a>`;
                    }
                    return `${sep}<span class="${i === breadcrumbs.length - 1 ? 'text-gray-300' : 'text-gray-500'}">${c.label}</span>`;
                }).join('')}
            </nav>

            <!-- Header -->
            <div class="flex items-start justify-between mb-4">
                <div>
                    <h1 class="text-2xl font-bold text-white mb-1">${escapeHtml(page.title)}</h1>
                    <div class="flex items-center gap-2 text-xs">
                        <span class="text-gray-500 font-mono">${escapeHtml(page.path)}</span>
                        ${page.type ? `<span class="px-2 py-0.5 rounded bg-surface-3 text-gray-400">${page.type}</span>` : ''}
                        ${fm.confidence ? `<span class="px-2 py-0.5 rounded badge-${fm.confidence === 'high' ? 'extracted' : fm.confidence === 'medium' ? 'inferred' : 'ambiguous'}">${fm.confidence}</span>` : ''}
                    </div>
                    ${tags.length ? `
                        <div class="flex gap-1 mt-1.5">
                            ${tags.map(t => `<span class="px-1.5 py-0.5 bg-surface-3 rounded text-[10px] text-gray-400">${t}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
                <div class="flex gap-2 shrink-0">
                    <button data-action="edit-page" class="px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-surface-2 border border-surface-4 rounded-lg hover:bg-surface-3 transition-colors flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                            <path d="M18.5 2.5a2.12 2.12 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                        Edit
                    </button>
                    <a href="#/graph/${encodeURIComponent(slug)}" class="px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-surface-2 border border-surface-4 rounded-lg hover:bg-surface-3 transition-colors flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><line x1="8.5" y1="7.5" x2="15.5" y2="16.5"/>
                        </svg>
                        View in Graph
                    </a>
                    <button data-action="copy-path" data-path="${escapeHtml(page.path)}" class="px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-surface-2 border border-surface-4 rounded-lg hover:bg-surface-3 transition-colors" title="Copy path">
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                        </svg>
                    </button>
                </div>
            </div>

            <!-- Frontmatter metadata -->
            ${fmEntries.length ? `
                <div class="bg-surface-2 rounded-lg px-4 py-3 mb-4 text-xs">
                    <div class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                        ${fmEntries.map(([key, value]) => {
                            const display = Array.isArray(value)
                                ? value.map(v => `<span class="px-1.5 py-0.5 bg-surface-3 rounded text-gray-400">${v}</span>`).join(' ')
                                : `<span class="text-gray-300">${value}</span>`;
                            return `<span class="text-gray-500">${key}:</span><span>${display}</span>`;
                        }).join('')}
                    </div>
                </div>
            ` : ''}

            <!-- Rendered content -->
            <div class="wiki-content">${html}</div>

            <!-- Backlinks -->
            <div id="explorer-backlinks" class="mt-8 pt-4 border-t border-surface-3"></div>

            <!-- Graph Neighbors -->
            <div id="explorer-neighbors" class="mt-4 pt-4 border-t border-surface-3"></div>

            <!-- Metadata footer -->
            <div id="explorer-metadata" class="mt-4 pt-4 border-t border-surface-3 text-xs text-gray-500">
                <p class="font-medium uppercase tracking-wider mb-2">Metadata</p>
                <div class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                    <span>Type:</span><span class="text-gray-300">${page.type}</span>
                    ${fm.confidence ? `<span>Confidence:</span><span class="text-gray-300">${fm.confidence}</span>` : ''}
                    ${fm.updated ? `<span>Updated:</span><span class="text-gray-300">${fm.updated}</span>` : ''}
                    ${fm.updated_by ? `<span>Updated by:</span><span class="text-gray-300">${fm.updated_by}</span>` : ''}
                </div>
            </div>
        </div>
    `;

    // Async: load backlinks
    loadBacklinks(slug).then(backlinks => {
        const el = document.getElementById('explorer-backlinks');
        if (el && backlinks.length) {
            el.innerHTML = `
                <p class="text-xs text-gray-500 font-medium uppercase tracking-wider mb-2">Backlinks (${backlinks.length})</p>
                <div class="flex flex-wrap gap-1.5">
                    ${backlinks.map(link => {
                        const linkSlug = link.replace(/\.md$/, '').split('/').pop();
                        return `<a href="#/explorer/wiki/${encodeURIComponent(linkSlug)}" class="px-2 py-1 bg-surface-2 rounded text-xs text-atlas-400 hover:bg-surface-3 transition-colors">${linkSlug}</a>`;
                    }).join('')}
                </div>
            `;
        }
    });

    // Async: load graph neighbors
    loadNeighbors(slug).then(neighbors => {
        const el = document.getElementById('explorer-neighbors');
        if (el && neighbors.length) {
            // Group by relation
            const grouped = {};
            neighbors.forEach(({ node, edge }) => {
                const rel = edge.relation || 'related';
                if (!grouped[rel]) grouped[rel] = [];
                grouped[rel].push(node);
            });

            el.innerHTML = `
                <p class="text-xs text-gray-500 font-medium uppercase tracking-wider mb-2">Graph Neighbors (${neighbors.length})</p>
                <div class="space-y-1">
                    ${Object.entries(grouped).map(([rel, nodes]) => `
                        <div class="text-xs">
                            <span class="text-gray-500">\u2192 ${rel}:</span>
                            ${nodes.map(n => `<a href="#/explorer/wiki/${encodeURIComponent(n.id)}" class="text-atlas-400 hover:text-atlas-300 ml-1">${n.label}</a>`).join(',')}
                        </div>
                    `).join('')}
                </div>
            `;
        }
    });
}

async function loadBacklinks(slug) {
    try {
        // Use wiki engine backlinks via all_wikilinks approach on client
        // Check all pages for wikilinks pointing to this slug
        const backlinks = [];
        for (const page of sidebarData.pages) {
            const wikilinks = page.wikilinks || [];
            for (const link of wikilinks) {
                const linkSlug = link.replace(/\.md$/, '').split('/').pop().toLowerCase();
                if (linkSlug === slug.toLowerCase()) {
                    backlinks.push(page.path);
                    break;
                }
            }
        }
        return backlinks;
    } catch {
        return [];
    }
}

async function loadNeighbors(slug) {
    try {
        const data = await api.post('/api/explain', { concept: slug });
        if (!data.neighbors) return [];
        return data.neighbors.map((node, i) => ({
            node,
            edge: data.edges[i] || { relation: 'related' },
        }));
    } catch {
        return [];
    }
}

// ---------------------------------------------------------------------------
// Content Panel: Wiki Page — Edit Mode (Split View)
// ---------------------------------------------------------------------------

function renderWikiEditMode(page, contentEl) {
    isEditing = true;
    const rawContent = page.content;

    contentEl.innerHTML = `
        <div class="flex flex-col h-full">
            <!-- Edit toolbar -->
            <div class="flex items-center justify-between px-4 py-2 border-b border-surface-3 bg-surface-1 shrink-0">
                <span class="text-xs text-amber-400 font-medium">Editing ${escapeHtml(page.path)}</span>
                <div class="flex gap-2">
                    <button data-action="cancel-edit" class="px-3 py-1 text-xs text-gray-400 hover:text-gray-200 bg-surface-3 rounded transition-colors">Cancel</button>
                    <button data-action="save-edit" class="px-3 py-1 text-xs text-white bg-atlas-600 rounded hover:bg-atlas-700 transition-colors">Save</button>
                </div>
            </div>

            <!-- Split view -->
            <div class="flex flex-1 overflow-hidden">
                <!-- Editor (left) -->
                <div class="flex-1 border-r border-surface-3 flex flex-col">
                    <div class="px-3 py-1 text-[10px] text-gray-500 uppercase tracking-wider bg-surface-2 border-b border-surface-3">Raw Markdown</div>
                    <textarea id="explorer-editor"
                        class="flex-1 w-full bg-surface-0 p-4 text-sm text-gray-300 font-mono leading-relaxed resize-none focus:outline-none"
                    >${escapeHtml(rawContent)}</textarea>
                </div>

                <!-- Preview (right) -->
                <div class="flex-1 flex flex-col">
                    <div class="px-3 py-1 text-[10px] text-gray-500 uppercase tracking-wider bg-surface-2 border-b border-surface-3">Live Preview</div>
                    <div id="explorer-preview" class="flex-1 overflow-y-auto p-4 wiki-content"></div>
                </div>
            </div>
        </div>
    `;

    const textarea = document.getElementById('explorer-editor');
    const preview = document.getElementById('explorer-preview');

    // Initial preview
    updatePreview(textarea.value, preview);

    // Live preview on keystroke (debounced 200ms)
    textarea.addEventListener('input', () => {
        clearTimeout(editDebounceTimer);
        editDebounceTimer = setTimeout(() => {
            updatePreview(textarea.value, preview);
        }, 200);
    });

    textarea.focus();
}

function updatePreview(rawContent, previewEl) {
    // Strip frontmatter for preview
    let body = rawContent;
    const fmMatch = body.match(/^---\n[\s\S]*?\n---\n/);
    if (fmMatch) {
        body = body.slice(fmMatch[0].length);
    }

    let html = marked.parse(body, markedOptions);
    html = addHeadingIds(html);
    previewEl.innerHTML = html;
}

async function saveEdit(page, contentEl) {
    const textarea = document.getElementById('explorer-editor');
    if (!textarea) return;

    const newContent = textarea.value;

    try {
        await api.post('/api/wiki/write', {
            page: page.path,
            content: newContent,
            frontmatter: page.frontmatter || {},
        });

        // Update local page data
        page.content = newContent;
        isEditing = false;
        toast('Page saved', 'success');

        // Re-render read mode
        renderWikiReadMode(page, contentEl);

        // Refresh sidebar (tags/links may have changed)
        await loadSidebarData();
        const sidebar = document.getElementById('explorer-sidebar');
        if (sidebar) {
            sidebar.outerHTML = renderSidebar();
            attachSidebarListeners();
        }
    } catch (err) {
        toast(`Save failed: ${err.message}`, 'error');
    }
}

// ---------------------------------------------------------------------------
// Content Panel: File Read Mode
// ---------------------------------------------------------------------------

async function loadAndRenderFile(path, contentEl) {
    contentEl.innerHTML = `
        <div class="flex items-center justify-center h-full">
            <svg class="w-8 h-8 text-atlas-500 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" opacity="0.2"/>
                <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
        </div>
    `;

    try {
        const data = await api.get(`/api/file/read?path=${encodeURIComponent(path)}`);
        currentSelection = { type: 'file', path };
        saveLastSelection(currentSelection);
        renderFileReadMode(data, contentEl);
    } catch (err) {
        contentEl.innerHTML = `
            <div class="max-w-3xl mx-auto px-6 py-6">
                <div class="text-center py-16">
                    <p class="text-5xl font-bold text-gray-700 mb-3">File Not Found</p>
                    <p class="text-gray-500 mb-4">"${escapeHtml(path)}"</p>
                    <a href="#/explorer" class="text-atlas-400 hover:text-atlas-300 text-sm">Back to Explorer</a>
                </div>
            </div>
        `;
    }
}

function renderFileReadMode(fileData, contentEl) {
    const { path, content, type } = fileData;
    const name = path.split('/').pop();
    const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : '';
    const isMarkdown = ext === 'md' || ext === 'markdown';
    const isCode = type === 'code' || ['py', 'js', 'ts', 'rs', 'go', 'java', 'rb', 'c', 'cpp', 'h', 'sh', 'yaml', 'yml', 'toml', 'json'].includes(ext);

    let renderedContent;
    if (isMarkdown) {
        let html = marked.parse(content, markedOptions);
        html = addHeadingIds(html);
        renderedContent = `<div class="wiki-content">${html}</div>`;
    } else if (isCode) {
        const lang = ext && hljs.getLanguage(ext) ? ext : 'plaintext';
        const highlighted = hljs.highlight(content, { language: lang }).value;
        renderedContent = `<pre class="bg-surface-1 border border-surface-3 rounded-lg p-4 overflow-x-auto"><code class="hljs language-${lang} text-sm">${highlighted}</code></pre>`;
    } else {
        renderedContent = `<pre class="bg-surface-1 border border-surface-3 rounded-lg p-4 overflow-x-auto text-sm text-gray-300 whitespace-pre-wrap">${escapeHtml(content)}</pre>`;
    }

    // Find node data for degree info
    const nodeSlug = path;
    const graphNode = findGraphNode(path);

    contentEl.innerHTML = `
        <div class="max-w-3xl mx-auto px-6 py-6">
            <!-- Breadcrumbs -->
            <nav class="flex items-center gap-1.5 text-xs text-gray-500 mb-4">
                <a href="#/explorer" class="hover:text-gray-300 transition-colors">Explorer</a>
                ${path.split('/').map((part, i, arr) => `
                    <span class="text-gray-600">/</span>
                    <span class="${i === arr.length - 1 ? 'text-gray-300' : 'text-gray-500'}">${part}</span>
                `).join('')}
            </nav>

            <!-- Header -->
            <div class="flex items-start justify-between mb-4">
                <div>
                    <h1 class="text-2xl font-bold text-white mb-1">${escapeHtml(name)}</h1>
                    <div class="flex items-center gap-2 text-xs">
                        <span class="text-gray-500 font-mono">${escapeHtml(path)}</span>
                        <span class="px-2 py-0.5 rounded bg-surface-3 text-gray-400">${type}</span>
                        ${graphNode ? `<span class="text-gray-500">${graphNode.degree} connections</span>` : ''}
                    </div>
                </div>
                <div class="flex gap-2 shrink-0">
                    <a href="#/graph/${encodeURIComponent(path)}" class="px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-surface-2 border border-surface-4 rounded-lg hover:bg-surface-3 transition-colors flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><line x1="8.5" y1="7.5" x2="15.5" y2="16.5"/>
                        </svg>
                        View in Graph
                    </a>
                    <button data-action="copy-path" data-path="${escapeHtml(path)}" class="px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-surface-2 border border-surface-4 rounded-lg hover:bg-surface-3 transition-colors" title="Copy path">
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                        </svg>
                    </button>
                </div>
            </div>

            <!-- File content -->
            ${renderedContent}
        </div>
    `;
}

function findGraphNode(path) {
    // Find a matching node in the graph data from files tree
    function search(nodes) {
        for (const n of nodes) {
            if (n.path === path && n.children === null) return n;
            if (n.children) {
                const found = search(n.children);
                if (found) return found;
            }
        }
        return null;
    }
    return search(sidebarData.files);
}

// ---------------------------------------------------------------------------
// Content Panel: Community View
// ---------------------------------------------------------------------------

function renderCommunityView(communityId, contentEl) {
    const community = sidebarData.communities.find(c => c.id === communityId);
    if (!community) {
        contentEl.innerHTML = `
            <div class="max-w-3xl mx-auto px-6 py-6 text-center py-16">
                <p class="text-gray-500">Community #${communityId} not found.</p>
                <a href="#/explorer" class="text-atlas-400 hover:text-atlas-300 text-sm">Back to Explorer</a>
            </div>
        `;
        return;
    }

    currentSelection = { type: 'community', id: communityId };
    saveLastSelection(currentSelection);

    // Find member details from graph/file data
    const memberDetails = community.members.map(memberId => {
        const fileNode = findGraphNode(memberId);
        return {
            id: memberId,
            degree: fileNode?.degree || 0,
            type: fileNode?.type || 'unknown',
        };
    }).sort((a, b) => b.degree - a.degree);

    // Cross-community links: find edges that connect this community to others
    const memberSet = new Set(community.members);
    const crossLinks = {};
    sidebarData.communities.forEach(other => {
        if (other.id === communityId) return;
        const otherSet = new Set(other.members);
        // Count shared edges (simplified: count members that appear in edges to other community)
        let sharedCount = 0;
        // This is approximate since we don't have full edge data in sidebar
        // A more precise count would need an API call
        crossLinks[other.label] = { id: other.id, count: 0 };
    });

    // Wiki coverage: check which members have wiki pages
    const wikiSlugs = new Set(sidebarData.pages.map(p => p.path.replace(/\.md$/, '').split('/').pop().toLowerCase()));
    const coverage = memberDetails.map(m => ({
        ...m,
        hasWiki: wikiSlugs.has(m.id.split('/').pop().replace(/\.[^.]+$/, '').toLowerCase()),
    }));

    contentEl.innerHTML = `
        <div class="max-w-3xl mx-auto px-6 py-6">
            <!-- Header -->
            <div class="flex items-start justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-bold text-white mb-1">${escapeHtml(community.label)}</h1>
                    <div class="flex items-center gap-2 text-xs text-gray-500">
                        <span>${community.size} nodes</span>
                        <span class="text-gray-600">&middot;</span>
                        <span>cohesion ${community.cohesion}</span>
                    </div>
                </div>
                <a href="#/graph" class="px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-surface-2 border border-surface-4 rounded-lg hover:bg-surface-3 transition-colors flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><line x1="8.5" y1="7.5" x2="15.5" y2="16.5"/>
                    </svg>
                    View in Graph
                </a>
            </div>

            <!-- Key Members -->
            <div class="mb-6">
                <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Key Members</h2>
                <div class="space-y-1">
                    ${coverage.map(m => {
                        const color = NODE_COLORS[m.type] || NODE_COLORS.unknown;
                        const isGodNode = m.degree >= 10;
                        return `
                            <a href="#/explorer/file/${encodeURIComponent(m.id)}" class="flex items-center gap-2 px-3 py-2 bg-surface-1 border border-surface-3 rounded-lg hover:bg-surface-2 transition-colors group">
                                <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background: ${color}"></span>
                                <span class="text-sm text-gray-300 group-hover:text-white transition-colors truncate">${escapeHtml(m.id)}</span>
                                <span class="text-xs text-gray-500 shrink-0">(${m.degree} connections)</span>
                                ${isGodNode ? '<span class="text-[10px] text-amber-400 shrink-0">god node</span>' : ''}
                            </a>
                        `;
                    }).join('')}
                </div>
            </div>

            <!-- Wiki Coverage -->
            <div>
                <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Wiki Coverage</h2>
                <div class="space-y-1">
                    ${coverage.map(m => {
                        const icon = m.hasWiki ? '\u2705' : '\u274C';
                        const text = m.hasWiki ? 'has a wiki page' : 'no wiki page';
                        return `
                            <div class="flex items-center gap-2 text-xs text-gray-400">
                                <span>${icon}</span>
                                <span>${escapeHtml(m.id)}</span>
                                <span class="text-gray-600">&mdash; ${text}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Event Delegation
// ---------------------------------------------------------------------------

let currentPageData = null;  // for edit mode save reference

function attachSidebarListeners() {
    const sidebar = document.getElementById('explorer-sidebar');
    if (!sidebar) return;

    sidebar.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;

        const action = target.dataset.action;

        if (action === 'toggle-folder') {
            const path = target.dataset.path;
            // For file tree: toggle between collapsed/expanded
            // Default state is collapsed (true), first click expands (false)
            if (path.startsWith('__section_') || path.startsWith('wiki-group-')) {
                folderState[path] = !folderState[path];
            } else {
                folderState[path] = folderState[path] === false ? true : false;
            }
            saveFolderState();
            // Re-render sidebar
            sidebar.outerHTML = renderSidebar();
            attachSidebarListeners();
        }

        if (action === 'show-all-communities') {
            // Remove the displayCount limit — toggle a flag
            sidebar.outerHTML = renderSidebar();
            attachSidebarListeners();
        }
    });
}

function attachContentListeners(contentEl) {
    contentEl.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;

        const action = target.dataset.action;

        if (action === 'edit-page') {
            if (currentPageData) {
                renderWikiEditMode(currentPageData, contentEl);
            }
        }

        if (action === 'cancel-edit') {
            isEditing = false;
            clearTimeout(editDebounceTimer);
            if (currentPageData) {
                renderWikiReadMode(currentPageData, contentEl);
            }
        }

        if (action === 'save-edit') {
            if (currentPageData) {
                saveEdit(currentPageData, contentEl);
            }
        }

        if (action === 'copy-path') {
            const path = target.dataset.path;
            navigator.clipboard.writeText(path).then(() => {
                toast('Path copied', 'success');
            }).catch(() => {
                toast('Failed to copy', 'error');
            });
        }
    });
}

// ---------------------------------------------------------------------------
// Main Layout
// ---------------------------------------------------------------------------

function renderLayout(contentHtml) {
    return `
        <div class="flex h-full">
            ${renderSidebar()}
            <div id="explorer-content" class="flex-1 overflow-y-auto bg-surface-0">
                ${contentHtml}
            </div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Router — Parse hash and render the right content
// ---------------------------------------------------------------------------

async function routeContent(params, contentEl) {
    const type = params[0]; // 'wiki', 'file', 'community', or undefined
    const rest = params.slice(1).join('/');

    if (!type) {
        // Restore last selection or show empty state
        const last = loadLastSelection();
        if (last) {
            if (last.type === 'wiki') {
                const slug = last.path.replace(/\.md$/, '').split('/').pop();
                currentPageData = sidebarData.pages.find(p => p.path === last.path) || null;
                await loadAndRenderWikiPage(slug, contentEl);
            } else if (last.type === 'file') {
                await loadAndRenderFile(last.path, contentEl);
            } else if (last.type === 'community') {
                renderCommunityView(last.id, contentEl);
            } else {
                contentEl.innerHTML = renderNoSelection();
            }
        } else {
            contentEl.innerHTML = renderNoSelection();
        }
        return;
    }

    if (type === 'wiki') {
        const slug = decodeURIComponent(rest);
        currentPageData = sidebarData.pages.find(p => {
            const pageSlug = p.path.replace(/\.md$/, '').split('/').pop();
            return pageSlug === slug;
        }) || null;
        await loadAndRenderWikiPage(slug, contentEl);
    } else if (type === 'file') {
        const path = decodeURIComponent(rest);
        await loadAndRenderFile(path, contentEl);
    } else if (type === 'community') {
        const id = parseInt(rest, 10);
        renderCommunityView(id, contentEl);
    } else {
        contentEl.innerHTML = renderNoSelection();
    }
}

// ---------------------------------------------------------------------------
// Init / Destroy (module interface)
// ---------------------------------------------------------------------------

export async function init(container, params) {
    // Load persisted state
    loadFolderState();

    // Load all sidebar data in parallel
    await loadSidebarData();

    // Render layout with placeholder content
    container.innerHTML = renderLayout(renderNoSelection());

    // Attach listeners
    attachSidebarListeners();
    const contentEl = document.getElementById('explorer-content');
    if (contentEl) {
        attachContentListeners(contentEl);
    }

    // Route to the right content based on URL params
    if (contentEl) {
        await routeContent(params || [], contentEl);
    }

    // Highlight active sidebar item
    refreshSidebarActive();

    // WebSocket: live updates
    wsUnsubs.push(on('ws:wiki_update', async () => {
        await loadSidebarData();
        const sidebar = document.getElementById('explorer-sidebar');
        if (sidebar) {
            sidebar.outerHTML = renderSidebar();
            attachSidebarListeners();
        }
    }));

    wsUnsubs.push(on('ws:graph_update', async () => {
        await loadSidebarData();
        const sidebar = document.getElementById('explorer-sidebar');
        if (sidebar) {
            sidebar.outerHTML = renderSidebar();
            attachSidebarListeners();
        }
    }));
}

export function destroy() {
    currentSelection = null;
    currentPageData = null;
    isEditing = false;
    clearTimeout(editDebounceTimer);
    wsUnsubs.forEach(unsub => unsub());
    wsUnsubs = [];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function refreshSidebarActive() {
    // Update active state in sidebar after navigation
    const sidebar = document.getElementById('explorer-sidebar');
    if (!sidebar) return;

    sidebar.querySelectorAll('a[href]').forEach(a => {
        const href = a.getAttribute('href');
        const current = window.location.hash;
        if (href === current) {
            a.classList.add('bg-surface-2');
        }
    });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/dashboard/test_explorer_exists.py -v`
Expected: All pass.

---

## Task 3: App Shell — Rename Wiki to Explorer + Routing

**Files:**
- Modify: `atlas/dashboard/index.html`
- Modify: `atlas/dashboard/app.js`

- [ ] **Step 1: Update index.html — Rename Wiki tab to Explorer**

In `atlas/dashboard/index.html`, replace the Wiki nav tab:

Find:
```html
                <a href="#/wiki" class="nav-tab" data-view="wiki">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path d="M4 4h16v16H4z"/><path d="M8 8h8M8 12h6M8 16h4"/>
                    </svg>
                    Wiki
                </a>
```

Replace with:
```html
                <a href="#/explorer" class="nav-tab" data-view="explorer">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                    </svg>
                    Explorer
                </a>
```

- [ ] **Step 2: Update app.js — Register Explorer + Redirect**

In `atlas/dashboard/app.js`, replace the boot function's import and registration block:

Find:
```javascript
    const [graphMod, wikiMod, auditMod, searchMod, timelineMod] = await Promise.all([
        import('/dashboard/graph.js'),
        import('/dashboard/wiki.js'),
        import('/dashboard/audit.js'),
        import('/dashboard/search.js'),
        import('/dashboard/timeline.js'),
    ]);

    registerView('graph', graphMod);
    registerView('wiki', wikiMod);
    registerView('audit', auditMod);
    registerView('search', searchMod);
    registerView('timeline', timelineMod);
```

Replace with:
```javascript
    const [graphMod, explorerMod, auditMod, searchMod, timelineMod] = await Promise.all([
        import('/dashboard/graph.js'),
        import('/dashboard/explorer.js'),
        import('/dashboard/audit.js'),
        import('/dashboard/search.js'),
        import('/dashboard/timeline.js'),
    ]);

    registerView('graph', graphMod);
    registerView('explorer', explorerMod);
    registerView('audit', auditMod);
    registerView('search', searchMod);
    registerView('timeline', timelineMod);
```

- [ ] **Step 3: Add backward-compat redirect in the router**

In `atlas/dashboard/app.js`, at the top of the `route()` function, add a redirect for old `#/wiki` URLs.

Find:
```javascript
async function route() {
    const hash = window.location.hash.slice(1) || '/';
    const segments = hash.split('/').filter(Boolean);
    const viewName = segments[0] || 'graph';
    const params = segments.slice(1);
```

Replace with:
```javascript
async function route() {
    const hash = window.location.hash.slice(1) || '/';
    const segments = hash.split('/').filter(Boolean);
    let viewName = segments[0] || 'graph';
    let params = segments.slice(1);

    // Backward compat: #/wiki/* -> #/explorer/wiki/*
    if (viewName === 'wiki') {
        const newHash = params.length
            ? `#/explorer/wiki/${params.join('/')}`
            : '#/explorer';
        window.location.hash = newHash;
        return; // hashchange will re-trigger route()
    }
```

- [ ] **Step 4: Update the test for required static files**

In `tests/dashboard/test_dashboard_served.py`, add `explorer.js` to the required files list if it exists. If the test already checks for wiki.js, keep it (wiki.js is not deleted yet) and add explorer.js:

Find the `required` list in `test_static_files_exist`:
```python
    required = ["index.html", "app.js", "graph.js", "wiki.js", "audit.js", "search.js", "timeline.js", "styles.css"]
```

Replace with:
```python
    required = ["index.html", "app.js", "graph.js", "wiki.js", "explorer.js", "audit.js", "search.js", "timeline.js", "styles.css"]
```

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest --tb=short -q`
Expected: All tests pass (265+ existing + new explorer tests).

---

## Task 4: Explorer Styles

**Files:**
- Modify: `atlas/dashboard/styles.css`

- [ ] **Step 1: Add explorer-specific styles to styles.css**

Append the following after the existing `.wikilink.broken` block and before the `/* --- Confidence badges --- */` section:

```css
/* --- Explorer layout --- */
#explorer-sidebar {
    transition: width 200ms ease;
}

@media (max-width: 768px) {
    #explorer-sidebar {
        width: 48px !important;
        overflow: hidden;
    }
    #explorer-sidebar .text-xs,
    #explorer-sidebar .text-\[10px\],
    #explorer-sidebar .text-\[9px\],
    #explorer-sidebar a span.truncate,
    #explorer-sidebar span.text-gray-400 {
        display: none;
    }
}

/* --- File tree indentation lines --- */
.explorer-tree-line {
    border-left: 1px solid rgba(255, 255, 255, 0.06);
    margin-left: 18px;
}

/* --- Explorer editor --- */
#explorer-editor {
    tab-size: 4;
    -moz-tab-size: 4;
}

#explorer-editor:focus {
    box-shadow: inset 0 0 0 1px rgba(51, 141, 255, 0.3);
}

/* --- Explorer split view resize handle --- */
.explorer-split-handle {
    width: 4px;
    cursor: col-resize;
    background: transparent;
    transition: background 150ms;
}
.explorer-split-handle:hover {
    background: rgba(51, 141, 255, 0.3);
}

/* --- Community cohesion bar --- */
.cohesion-bar {
    height: 6px;
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.06);
    overflow: hidden;
}
.cohesion-bar-fill {
    height: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, #1b6cf5, #34d399);
    transition: width 300ms ease;
}
```

- [ ] **Step 2: Verify styles don't break existing views**

Run: `python -m pytest tests/dashboard/ -v`
Expected: All dashboard tests pass.

---

## Task 5: Integration Testing

This task validates the full flow end-to-end: API routes return correct data, Explorer renders without errors, navigation works.

**Files:**
- Create: `tests/integration/test_explorer_integration.py`

- [ ] **Step 1: Write integration tests**

`tests/integration/test_explorer_integration.py`:
```python
"""Integration tests — Explorer API routes work with real engine data."""
import pytest
from pathlib import Path

from atlas.core.models import Node, Edge, Extraction
from atlas.server.app import create_app
from atlas.server.deps import create_engine_set, EventBus


@pytest.fixture
def populated_engines(tmp_path):
    """Create an engine set with realistic data: files, wiki pages, communities."""
    root = tmp_path

    # Create source files
    (root / "src").mkdir()
    (root / "src" / "auth.py").write_text("import jwt\nimport db\n\ndef login(user):\n    pass\n")
    (root / "src" / "db.py").write_text("import sqlalchemy\n\ndef connect():\n    pass\n")
    (root / "src" / "api.py").write_text("from auth import login\nfrom db import connect\n")
    (root / "docs").mkdir()
    (root / "docs" / "architecture.md").write_text("# Architecture\n\nModular design with auth, db, api layers.\n")

    # Create wiki pages
    (root / "wiki" / "concepts").mkdir(parents=True)
    (root / "wiki" / "concepts" / "auth.md").write_text(
        "---\ntitle: Authentication\ntype: wiki-concept\ntags:\n  - auth\n  - security\n---\n\n"
        "JWT-based auth with session fallback. See [[billing]] for payment auth.\n"
    )
    (root / "wiki" / "concepts" / "billing.md").write_text(
        "---\ntitle: Billing\ntype: wiki-concept\ntags:\n  - billing\n---\n\n"
        "Stripe integration. Uses [[auth]] for authorization.\n"
    )
    (root / "wiki" / "projects").mkdir(parents=True)
    (root / "wiki" / "projects" / "atlas.md").write_text(
        "---\ntitle: Atlas\ntype: wiki-page\nstatus: active\n---\n\nKnowledge engine.\n"
    )

    es = create_engine_set(root)

    # Build graph
    extraction = Extraction(
        nodes=[
            Node(id="src/auth.py", label="auth.py", type="code", source_file="src/auth.py", community=0),
            Node(id="src/db.py", label="db.py", type="code", source_file="src/db.py", community=0),
            Node(id="src/api.py", label="api.py", type="code", source_file="src/api.py", community=0),
            Node(id="docs/architecture.md", label="architecture.md", type="document", source_file="docs/architecture.md", community=1),
            Node(id="wiki/concepts/auth", label="Authentication", type="wiki-concept", source_file="wiki/concepts/auth.md", community=0),
            Node(id="wiki/concepts/billing", label="Billing", type="wiki-concept", source_file="wiki/concepts/billing.md", community=2),
            Node(id="wiki/projects/atlas", label="Atlas", type="wiki-page", source_file="wiki/projects/atlas.md", community=1),
        ],
        edges=[
            Edge(source="src/auth.py", target="src/db.py", relation="imports", confidence="EXTRACTED"),
            Edge(source="src/api.py", target="src/auth.py", relation="imports", confidence="EXTRACTED"),
            Edge(source="src/api.py", target="src/db.py", relation="imports", confidence="EXTRACTED"),
            Edge(source="wiki/concepts/auth", target="wiki/concepts/billing", relation="references", confidence="EXTRACTED"),
            Edge(source="wiki/concepts/billing", target="wiki/concepts/auth", relation="references", confidence="EXTRACTED"),
            Edge(source="docs/architecture.md", target="src/auth.py", relation="references", confidence="INFERRED"),
        ],
    )
    es.graph.merge(extraction)
    return es


@pytest.fixture
def client(populated_engines):
    from fastapi.testclient import TestClient
    app = create_app(engines=populated_engines, event_bus=EventBus())
    return TestClient(app)


class TestFilesTreeIntegration:
    def test_tree_has_src_and_docs(self, client):
        resp = client.get("/api/files")
        assert resp.status_code == 200
        top_paths = [n["name"] for n in resp.json()]
        assert "src" in top_paths
        assert "docs" in top_paths

    def test_src_has_three_files(self, client):
        resp = client.get("/api/files")
        src = next(n for n in resp.json() if n["name"] == "src")
        assert len(src["children"]) == 3
        names = {c["name"] for c in src["children"]}
        assert names == {"auth.py", "db.py", "api.py"}

    def test_file_degrees_are_positive(self, client):
        resp = client.get("/api/files")
        src = next(n for n in resp.json() if n["name"] == "src")
        for child in src["children"]:
            assert child["degree"] > 0, f"{child['name']} should have connections"


class TestCommunitiesIntegration:
    def test_multiple_communities(self, client):
        resp = client.get("/api/communities")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_community_sizes_sum_to_total_nodes(self, client, populated_engines):
        resp = client.get("/api/communities")
        total = sum(c["size"] for c in resp.json())
        # Not all nodes may have communities, so total <= graph node count
        assert total <= populated_engines.graph.node_count

    def test_cohesion_is_between_0_and_1(self, client):
        resp = client.get("/api/communities")
        for c in resp.json():
            assert 0.0 <= c["cohesion"] <= 1.0, f"Community {c['id']} cohesion out of range"


class TestFileReadIntegration:
    def test_read_python_file(self, client):
        resp = client.get("/api/file/read", params={"path": "src/auth.py"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "code"
        assert "import jwt" in data["content"]

    def test_read_markdown_file(self, client):
        resp = client.get("/api/file/read", params={"path": "docs/architecture.md"})
        assert resp.status_code == 200
        assert data := resp.json()
        assert data["type"] == "document"
        assert "Architecture" in data["content"]

    def test_read_wiki_page_as_file(self, client):
        resp = client.get("/api/file/read", params={"path": "wiki/concepts/auth.md"})
        assert resp.status_code == 200
        data = resp.json()
        assert "JWT" in data["content"] or "auth" in data["content"].lower()


class TestExplorerStaticFiles:
    def test_explorer_js_served(self, client):
        resp = client.get("/dashboard/explorer.js")
        # File must be created before this test passes
        assert resp.status_code == 200
```

- [ ] **Step 2: Run integration tests**

Run: `python -m pytest tests/integration/test_explorer_integration.py -v`
Expected: All pass.

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest --tb=short -q`
Expected: All tests pass, no regressions.

---

## Task 6: Self-Review Checklist

Before marking this plan as done, verify each item:

- [ ] **API Routes:** All 3 endpoints return correct data
  - `GET /api/files` returns nested tree with path, type, degree, children
  - `GET /api/communities` returns list with id, label, size, cohesion, members
  - `GET /api/file/read?path=` returns raw content with path traversal protection
- [ ] **Sidebar:** 4 sections render (Overview, Files, Wiki, Communities)
  - Overview shows node/edge/community counts and health bar
  - File tree is collapsible, shows degree badges, color-coded by type
  - Wiki list is grouped by type, shows tags/status/date
  - Communities show size bars, sorted by size descending
- [ ] **Content Panel:**
  - Wiki read mode: rendered markdown, breadcrumbs, backlinks, graph neighbors, metadata
  - Wiki edit mode: split view, textarea left, live preview right, debounced 200ms
  - File read mode: syntax highlighting for code, rendered markdown for .md
  - Community view: member list, wiki coverage, cohesion stats
  - No-selection state: helpful empty state with scan command hint
- [ ] **Navigation:**
  - Hash routing: `#/explorer`, `#/explorer/wiki/slug`, `#/explorer/file/path`, `#/explorer/community/id`
  - Wikilink clicks navigate within Explorer
  - "View in Graph" links switch to Graph tab
  - Browser back/forward works (hash-based)
  - Old `#/wiki/*` redirects to `#/explorer/*`
- [ ] **Persistence:**
  - Folder collapsed/expanded state in localStorage
  - Last selected file/page restored on load
- [ ] **No Build Step:** All vanilla JS, Tailwind CDN, no node_modules
- [ ] **No Regressions:** Full test suite passes (265+ tests)
- [ ] **Performance:** Sidebar loads from cached API responses, content lazy-loaded
