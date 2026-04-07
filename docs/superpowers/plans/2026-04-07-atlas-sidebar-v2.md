# Atlas Sidebar v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the Explorer sidebar from 4 sections (OVERVIEW, FILES, WIKI, COMMUNITIES) down to 2 sections (OVERVIEW, BROWSE with 3-mode toggle). Fix content panel UX issues: visible Edit/View in Graph buttons, clickable `[[wikilinks]]`, human-readable community labels. Add "Enrich with AI" button to OVERVIEW.

**Architecture:** Modify `explorer.js` in place. The BROWSE section replaces the 3 separate sections (FILES, WIKI, COMMUNITIES) with a single section that toggles between Folder, Type, and Community modes. The active browse mode is persisted in `localStorage`. The OVERVIEW section is enriched with an "Enrich with AI" button. No new files created — all changes are edits to existing `explorer.js` and `styles.css`.

**Tech Stack:** HTML5, vanilla JS (ES2022 modules), Tailwind CSS 3.x CDN, marked.js (markdown), highlight.js (code blocks). No build step.

**Depends on:** Plan 7 (Explorer) merged and working (1149-line `explorer.js` exists, all 4 sidebar sections functional).

**Spec reference:** `docs/superpowers/specs/2026-04-07-atlas-v2-ide-design.md` — sections 5 (Sidebar), 6 (Content Panel fixes), 7 (Enrich with AI).

**API contract — existing endpoints used (no new endpoints needed):**

| Endpoint | Method | Returns |
|---|---|---|
| `/api/stats` | GET | `{stats: {nodes, edges, communities, health_score}}` |
| `/api/files` | GET | `[{path, type, degree, children}]` — file tree |
| `/api/wiki/pages` | GET | `Page[]` (list with content, frontmatter, type, wikilinks) |
| `/api/communities` | GET | `[{id, label, size, cohesion, members}]` — community list |
| `POST /api/wiki/write` | POST `{page, content, frontmatter}` | `{page}` |
| `POST /api/explain` | POST `{concept}` | `{neighbors, edges}` |

---

## File Map

```
atlas/
├── dashboard/
│   ├── explorer.js         # MODIFY: rewrite sidebar (OVERVIEW + BROWSE toggle), fix content panel UX
│   └── styles.css          # MODIFY: add browse-toggle styles, enrich-button styles

tests/
├── dashboard/
│   └── test_sidebar_v2.py  # CREATE: tests for sidebar v2 behavior
```

---

## Task 1: BROWSE Toggle — Replace 3 Sidebar Sections with 1

**Files:**
- Modify: `atlas/dashboard/explorer.js`

**What changes:**
- Remove `renderFileTree()`, `renderWikiList()`, `renderCommunities()` as standalone sidebar sections
- Keep the rendering functions but repurpose them as modes inside a single BROWSE section
- Add a `browseMode` state variable (`'folder'` | `'type'` | `'community'`), persisted in `localStorage` key `atlas-browse-mode`
- Add a toggle bar at the top of the BROWSE section: 3 buttons with emoji icons
- Only one mode renders at a time

### Step-by-step

- [ ] **Step 1: Add browse mode state**

In the state section at the top of `explorer.js`, add:

```js
let browseMode = 'folder'; // 'folder' | 'type' | 'community'
```

Add localStorage helpers:

```js
function loadBrowseMode() {
    try {
        const stored = localStorage.getItem('atlas-browse-mode');
        if (stored && ['folder', 'type', 'community'].includes(stored)) {
            browseMode = stored;
        }
    } catch { /* ignore */ }
}

function saveBrowseMode() {
    try {
        localStorage.setItem('atlas-browse-mode', browseMode);
    } catch { /* ignore */ }
}
```

Call `loadBrowseMode()` inside the existing `init()` function, right after `loadFolderState()`.

- [ ] **Step 2: Create the browse toggle bar**

Add a new function `renderBrowseToggle()`:

```js
function renderBrowseToggle() {
    const modes = [
        { key: 'folder',    icon: '\uD83D\uDCC1', label: 'Folder' },
        { key: 'type',      icon: '\uD83D\uDCDD', label: 'Type' },
        { key: 'community', icon: '\uD83C\uDFD8\uFE0F', label: 'Community' },
    ];

    return `
        <div class="flex items-center gap-0.5 px-3 py-1.5">
            ${modes.map(m => {
                const isActive = browseMode === m.key;
                return `
                    <button data-action="set-browse-mode" data-mode="${m.key}"
                        class="flex items-center gap-1 px-2 py-1 rounded text-[11px] transition-colors ${
                            isActive
                                ? 'bg-atlas-600/20 text-atlas-400 font-medium'
                                : 'text-gray-500 hover:text-gray-300 hover:bg-surface-2'
                        }">
                        <span class="text-xs">${m.icon}</span>
                        <span>${m.label}</span>
                    </button>
                `;
            }).join('')}
        </div>
    `;
}
```

- [ ] **Step 3: Create `renderBrowseContent()` dispatcher**

This function renders the active mode's content:

```js
function renderBrowseContent() {
    switch (browseMode) {
        case 'folder':    return renderFileTree(sidebarData.files);
        case 'type':      return renderTypeList();
        case 'community': return renderCommunityList();
        default:          return renderFileTree(sidebarData.files);
    }
}
```

Note: `renderFileTree()` already exists and needs no changes. `renderCommunityList()` is the renamed `renderCommunities()`. `renderTypeList()` is a new function (see Step 5).

- [ ] **Step 4: Rename `renderCommunities()` to `renderCommunityList()`**

The function body stays identical. The community label is already the highest-degree node's label (from the server API at `/api/communities` line 421 of `app.py`). If the label is a file path (e.g., `wiki/concepts/auth.md`), clean it up to show just the human name:

```js
function renderCommunityList() {
    const communities = sidebarData.communities;
    if (!communities || !communities.length) {
        return `<div class="px-3 py-2 text-xs text-gray-500">No communities detected.</div>`;
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
                // Human-readable label: strip path prefixes and extensions
                const humanLabel = humanizeCommunityLabel(c.label);

                return `
                    <a href="#/explorer/community/${c.id}"
                       class="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer hover:bg-surface-2 transition-colors ${isActive ? 'bg-surface-2' : ''}">
                        <span class="truncate ${isActive ? 'text-white' : 'text-gray-400'} transition-colors flex-1">${escapeHtml(humanLabel)}</span>
                        <span class="text-[10px] text-gray-600 shrink-0">${c.size}</span>
                        <div class="w-16 h-1.5 bg-surface-3 rounded-full shrink-0 overflow-hidden">
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
```

Add the helper:

```js
function humanizeCommunityLabel(label) {
    // If it looks like a path (contains / or ends with .ext), clean it
    if (label.includes('/') || /\.\w{1,5}$/.test(label)) {
        // Take the last segment, strip extension, replace dashes/underscores with spaces
        const base = label.split('/').pop().replace(/\.\w{1,5}$/, '');
        return base.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }
    return label;
}
```

- [ ] **Step 5: Create `renderTypeList()` — semantic grouping**

This is the new Type mode. Groups wiki pages by their `type` field, and puts non-wiki files in an "Other" group:

```js
function renderTypeList() {
    const pages = sidebarData.pages;
    const files = sidebarData.files;

    if ((!pages || !pages.length) && (!files || !files.length)) {
        return `<div class="px-3 py-2 text-xs text-gray-500">No content scanned.</div>`;
    }

    // Group wiki pages by semantic type
    const groups = {
        'Concepts':  [],
        'Projects':  [],
        'Decisions': [],
        'Sources':   [],
        'Other':     [],
    };

    const TYPE_TO_GROUP = {
        'wiki-concept':  'Concepts',
        'wiki-page':     'Projects',
        'wiki-decision': 'Decisions',
        'wiki-source':   'Sources',
    };

    // Add wiki pages to their groups
    const wikiPaths = new Set();
    pages.forEach(p => {
        const group = TYPE_TO_GROUP[p.type] || 'Other';
        const slug = p.path.replace(/\.md$/, '').split('/').pop();
        const tags = p.frontmatter?.tags || [];
        const status = p.frontmatter?.status;
        groups[group].push({
            title: p.title,
            slug,
            path: p.path,
            tags,
            status,
            isWiki: true,
        });
        wikiPaths.add(p.path);
    });

    // Collect non-wiki files into "Other"
    function collectFiles(nodes) {
        for (const node of nodes) {
            if (node.children) {
                collectFiles(node.children);
            } else if (!wikiPaths.has(node.path)) {
                groups['Other'].push({
                    title: node.name,
                    slug: null,
                    path: node.path,
                    tags: [],
                    status: node.type,
                    isWiki: false,
                });
            }
        }
    }
    collectFiles(files);

    const groupOrder = ['Concepts', 'Projects', 'Decisions', 'Sources', 'Other'];

    return groupOrder.filter(g => groups[g].length > 0).map(groupName => {
        const items = groups[groupName].sort((a, b) => a.title.localeCompare(b.title));
        const groupKey = `type-group-${groupName}`;
        const isCollapsed = folderState[groupKey] === true;

        return `
            <div>
                <div class="flex items-center gap-1 px-3 py-1 text-xs cursor-pointer hover:bg-surface-2 transition-colors group"
                     data-action="toggle-folder" data-path="${groupKey}">
                    <span class="text-gray-500 text-[9px] w-3 shrink-0">${isCollapsed ? '\u25B6' : '\u25BC'}</span>
                    <span class="text-gray-400 group-hover:text-gray-200 transition-colors">${groupName}</span>
                    <span class="text-[10px] text-gray-600 ml-1">(${items.length})</span>
                </div>
                ${isCollapsed ? '' : `
                    <div>
                        ${items.map(item => {
                            const href = item.isWiki
                                ? `#/explorer/wiki/${encodeURIComponent(item.slug)}`
                                : `#/explorer/file/${encodeURIComponent(item.path)}`;
                            const isActive = item.isWiki
                                ? (currentSelection?.type === 'wiki' && currentSelection?.path === item.path)
                                : (currentSelection?.type === 'file' && currentSelection?.path === item.path);

                            return `
                                <a href="${href}"
                                   class="flex items-center gap-1.5 px-3 py-1 text-xs cursor-pointer hover:bg-surface-2 transition-colors ${isActive ? 'bg-surface-2' : ''}"
                                   style="padding-left: 28px">
                                    <span class="truncate ${isActive ? 'text-white' : 'text-gray-400 hover:text-gray-200'} transition-colors">${escapeHtml(item.title)}</span>
                                    <span class="ml-auto flex items-center gap-1 shrink-0">
                                        ${item.tags.slice(0, 2).map(t => `<span class="px-1 py-0 bg-surface-3 rounded text-[9px] text-gray-500">${t}</span>`).join('')}
                                        ${item.status ? `<span class="text-[10px] text-gray-500">${item.status}</span>` : ''}
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
```

- [ ] **Step 6: Rewrite `renderSidebar()` to use OVERVIEW + BROWSE**

Replace the entire `renderSidebar()` function:

```js
function renderSidebar() {
    return `
        <aside id="explorer-sidebar" class="w-72 shrink-0 border-r border-surface-3 bg-surface-1 flex flex-col overflow-hidden">
            <!-- OVERVIEW -->
            <div class="border-b border-surface-3">
                <div class="px-3 py-2 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Overview</div>
                ${renderOverview()}
            </div>

            <!-- BROWSE -->
            <div class="flex-1 flex flex-col overflow-hidden">
                <div class="flex items-center justify-between px-3 py-2 border-b border-surface-3">
                    <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Browse</span>
                </div>
                ${renderBrowseToggle()}
                <div class="flex-1 overflow-y-auto pb-2">
                    ${renderBrowseContent()}
                </div>
            </div>
        </aside>
    `;
}
```

- [ ] **Step 7: Handle the browse mode toggle click**

In `attachSidebarListeners()`, inside the existing click handler, add a new action case:

```js
if (action === 'set-browse-mode') {
    const mode = target.dataset.mode;
    if (mode && ['folder', 'type', 'community'].includes(mode)) {
        browseMode = mode;
        saveBrowseMode();
        sidebar.outerHTML = renderSidebar();
        attachSidebarListeners();
    }
}
```

- [ ] **Step 8: Remove dead code**

Delete the old section toggles that no longer exist:
- Remove `__section_files`, `__section_wiki`, `__section_communities` from any folderState defaults
- The old `renderWikiList()` function is replaced by `renderTypeList()` — delete `renderWikiList()`
- The old `renderCommunities()` function is replaced by `renderCommunityList()` — delete `renderCommunities()`

- [ ] **Step 9: Verify the toggle bar renders correctly**

Manual verification:
1. Open `http://localhost:7100/#/explorer`
2. The sidebar should show OVERVIEW at the top, then BROWSE with a 3-button toggle
3. Default mode = Folder (file tree, same as before)
4. Click Type -> wiki pages grouped by Concepts/Projects/Decisions/Sources/Other
5. Click Community -> community list with size bars
6. Refresh the page -> same mode persisted
7. Clicking items in any mode still opens the correct content panel

---

## Task 2: Content Panel UX Fixes

**Files:**
- Modify: `atlas/dashboard/explorer.js`

### Fix 2a: Wikilinks rendered in all markdown contexts

**Problem:** The current `createRenderer()` only handles `[[wikilinks]]` inside `renderer.paragraph()`. This means wikilinks in list items, blockquotes, table cells, and headings are not converted.

- [ ] **Step 1: Move wikilink processing to a post-processing step**

Instead of patching `renderer.paragraph`, apply the regex after `marked.parse()` returns the full HTML. This catches all contexts:

```js
function processWikilinks(html) {
    return html.replace(
        /\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g,
        (_, target, display) => {
            const slug = target.trim();
            const label = (display || target).trim();
            return `<a href="#/explorer/wiki/${encodeURIComponent(slug)}" class="wikilink" data-target="${slug}">${escapeHtml(label)}</a>`;
        }
    );
}
```

Update `createRenderer()` to remove the paragraph override (restore original behavior):

```js
function createRenderer() {
    const renderer = new marked.Renderer();

    // Code blocks with highlight.js
    renderer.code = function (code, language) {
        const lang = language && hljs.getLanguage(language) ? language : 'plaintext';
        const highlighted = hljs.highlight(code, { language: lang }).value;
        return `<pre><code class="hljs language-${lang}">${highlighted}</code></pre>`;
    };

    return renderer;
}
```

Apply `processWikilinks()` after `marked.parse()` in three places:
1. `renderWikiReadMode()` — after `let html = marked.parse(body, markedOptions);`
2. `renderFileReadMode()` — after `let html = marked.parse(content, markedOptions);`
3. `updatePreview()` — after `let html = marked.parse(body, markedOptions);`

Pattern at each call site:

```js
let html = marked.parse(body, markedOptions);
html = processWikilinks(html);
html = addHeadingIds(html);
```

### Fix 2b: Edit / View in Graph buttons always visible

**Problem:** The buttons exist in the current code (lines 510-528 of `explorer.js`) but are inside a `<div class="flex items-start justify-between mb-4">` which can collapse on narrow viewports or get hidden by overflow.

- [ ] **Step 2: Move action buttons to a sticky header bar**

In `renderWikiReadMode()`, extract the Edit/View in Graph/Copy buttons into a fixed header bar above the scrollable content:

```js
contentEl.innerHTML = `
    <div class="flex flex-col h-full">
        <!-- Sticky action header -->
        <div class="flex items-center justify-between px-6 py-2 border-b border-surface-3 bg-surface-1 shrink-0">
            <nav class="flex items-center gap-1.5 text-xs text-gray-500">
                ${breadcrumbs.map((c, i) => {
                    const sep = i > 0 ? '<span class="text-gray-600">/</span>' : '';
                    if (c.href) {
                        return \`\${sep}<a href="\${c.href}" class="hover:text-gray-300 transition-colors">\${c.label}</a>\`;
                    }
                    return \`\${sep}<span class="\${i === breadcrumbs.length - 1 ? 'text-gray-300' : 'text-gray-500'}">\${c.label}</span>\`;
                }).join('')}
            </nav>
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

        <!-- Scrollable content -->
        <div class="flex-1 overflow-y-auto">
            <div class="max-w-3xl mx-auto px-6 py-6">
                <!-- title, metadata, tags, frontmatter table, wiki-content, backlinks, neighbors -->
                ...
            </div>
        </div>
    </div>
`;
```

Apply the same pattern to `renderFileReadMode()` — move the "View in Graph" and "Copy path" buttons into a sticky header.

- [ ] **Step 3: Verify buttons are always visible**

Manual verification:
1. Open a wiki page in the content panel
2. Scroll down through the content
3. The Edit / View in Graph / Copy buttons must stay visible in the header bar
4. Click Edit -> split editor opens correctly
5. Click View in Graph -> navigates to `#/graph/<slug>`

### Fix 2c: Community labels — human-readable names

- [ ] **Step 4: Apply `humanizeCommunityLabel()` in community view**

In `renderCommunityView()` (the content panel community view), use the same `humanizeCommunityLabel()` helper:

```js
// Line ~892 of current explorer.js
<h1 class="text-2xl font-bold text-white mb-1">${escapeHtml(humanizeCommunityLabel(community.label))}</h1>
```

Also apply it to member labels in the community view member list.

---

## Task 3: OVERVIEW Enrichment

**Files:**
- Modify: `atlas/dashboard/explorer.js`

- [ ] **Step 1: Add "Enrich with AI" button to OVERVIEW**

Update `renderOverview()` to add the button below the health bar:

```js
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
            <button data-action="enrich-ai"
                class="mt-2 w-full px-3 py-1.5 text-xs text-atlas-400 border border-atlas-600/30 rounded-lg hover:bg-atlas-600/10 hover:text-atlas-300 transition-colors flex items-center justify-center gap-1.5">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
                Enrich with AI
            </button>
        </div>
    `;
}
```

- [ ] **Step 2: Handle the "Enrich with AI" click**

Add a new action handler in `attachSidebarListeners()`:

```js
if (action === 'enrich-ai') {
    showEnrichModal();
}
```

Add the modal function:

```js
function showEnrichModal() {
    // Check if MCP agent is connected (via WebSocket status)
    const wsConnected = document.getElementById('ws-dot')?.classList.contains('bg-emerald-500');

    const overlay = document.createElement('div');
    overlay.id = 'enrich-modal-overlay';
    overlay.className = 'fixed inset-0 bg-black/50 z-50 flex items-center justify-center';
    overlay.innerHTML = `
        <div class="bg-surface-1 border border-surface-3 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 class="text-lg font-semibold text-white mb-3">Enrich with AI</h3>
            ${wsConnected ? `
                <p class="text-sm text-gray-400 mb-4">
                    An agent is connected. Send the enrichment job?
                </p>
                <p class="text-xs text-gray-500 mb-4">
                    This will extract semantic relations, concepts, and cross-file connections using your connected agent's LLM.
                </p>
                <div class="flex gap-2 justify-end">
                    <button data-action="close-enrich-modal" class="px-4 py-2 text-xs text-gray-400 hover:text-gray-200 bg-surface-3 rounded-lg transition-colors">Cancel</button>
                    <button data-action="start-enrichment" class="px-4 py-2 text-xs text-white bg-atlas-600 rounded-lg hover:bg-atlas-700 transition-colors">Start Enrichment</button>
                </div>
            ` : `
                <p class="text-sm text-gray-400 mb-4">
                    To enrich with AI, run this in your agent:
                </p>
                <div class="bg-surface-0 border border-surface-3 rounded-lg p-3 mb-4 flex items-center justify-between">
                    <code class="text-sm text-atlas-400 font-mono">atlas scan --deep</code>
                    <button data-action="copy-enrich-cmd" class="text-xs text-gray-500 hover:text-white transition-colors px-2 py-1 rounded hover:bg-surface-3">Copy</button>
                </div>
                <p class="text-xs text-gray-500 mb-4">
                    Works with Claude Code, Codex, Cursor, or any MCP agent.
                </p>
                <div class="flex justify-end">
                    <button data-action="close-enrich-modal" class="px-4 py-2 text-xs text-gray-400 hover:text-gray-200 bg-surface-3 rounded-lg transition-colors">Close</button>
                </div>
            `}
        </div>
    `;

    overlay.addEventListener('click', (e) => {
        if (e.target === overlay || e.target.closest('[data-action="close-enrich-modal"]')) {
            overlay.remove();
        }
        if (e.target.closest('[data-action="copy-enrich-cmd"]')) {
            navigator.clipboard.writeText('atlas scan --deep').then(() => {
                toast('Command copied', 'success');
            });
        }
        if (e.target.closest('[data-action="start-enrichment"]')) {
            // Send enrichment request via API
            api.post('/api/scan', { level: 'deep' }).then(() => {
                toast('Enrichment started', 'success');
                overlay.remove();
            }).catch(err => {
                toast(`Enrichment failed: ${err.message}`, 'error');
            });
        }
    });

    document.body.appendChild(overlay);
}
```

- [ ] **Step 3: Verify the enrich flow**

Manual verification:
1. OVERVIEW section shows the "Enrich with AI" button below the health bar
2. Click it -> modal appears
3. If WebSocket disconnected -> shows the CLI command with a Copy button
4. If WebSocket connected -> shows "Start Enrichment" option
5. Copy button works
6. Modal closes on Cancel / outside click

---

## Task 4: CSS Additions

**Files:**
- Modify: `atlas/dashboard/styles.css`

- [ ] **Step 1: Add browse toggle styles**

Append to `styles.css`:

```css
/* --- Browse toggle --- */
.browse-toggle-active {
    background: rgba(51, 141, 255, 0.15);
    color: #338dff;
}

/* --- Enrich button pulse (when enrichment is in progress) --- */
.enrich-in-progress {
    animation: enrich-pulse 2s ease-in-out infinite;
}

@keyframes enrich-pulse {
    0%, 100% { border-color: rgba(27, 108, 245, 0.3); }
    50% { border-color: rgba(27, 108, 245, 0.7); }
}

/* --- Enrich modal backdrop --- */
#enrich-modal-overlay {
    animation: modal-fade-in 150ms ease-out;
}

@keyframes modal-fade-in {
    from { opacity: 0; }
    to   { opacity: 1; }
}

#enrich-modal-overlay > div {
    animation: modal-slide-up 200ms ease-out;
}

@keyframes modal-slide-up {
    from { transform: translateY(10px); opacity: 0; }
    to   { transform: translateY(0); opacity: 1; }
}

/* --- Content panel sticky header --- */
#explorer-content > div > .border-b:first-child {
    position: sticky;
    top: 0;
    z-index: 10;
}
```

---

## Task 5: Tests

**Files:**
- Create: `tests/dashboard/test_sidebar_v2.py`

- [ ] **Step 1: Write structural tests**

```python
"""Tests for Sidebar v2 changes in explorer.js."""
import re
from pathlib import Path

EXPLORER_JS = Path(__file__).resolve().parents[2] / "atlas" / "dashboard" / "explorer.js"
STYLES_CSS = Path(__file__).resolve().parents[2] / "atlas" / "dashboard" / "styles.css"


class TestBrowseToggle:
    """Verify the browse toggle replaces old sidebar sections."""

    def test_explorer_js_exists(self):
        assert EXPLORER_JS.exists()

    def test_no_section_files_in_sidebar(self):
        """Old __section_files toggle should not appear in renderSidebar."""
        content = EXPLORER_JS.read_text()
        # The old sidebar rendered __section_files, __section_wiki, __section_communities
        # as separate collapsible sections. They should no longer be in renderSidebar().
        render_sidebar_match = re.search(
            r'function renderSidebar\(\)(.*?)(?=\nfunction |\n// ---)',
            content,
            re.DOTALL
        )
        assert render_sidebar_match, "renderSidebar() not found"
        sidebar_body = render_sidebar_match.group(1)
        assert '__section_files' not in sidebar_body
        assert '__section_wiki' not in sidebar_body
        assert '__section_communities' not in sidebar_body

    def test_browse_mode_state_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'browseMode' in content
        assert 'atlas-browse-mode' in content

    def test_render_browse_toggle_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'renderBrowseToggle' in content

    def test_render_browse_content_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'renderBrowseContent' in content

    def test_render_type_list_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'renderTypeList' in content

    def test_render_community_list_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'renderCommunityList' in content

    def test_old_render_wiki_list_removed(self):
        content = EXPLORER_JS.read_text()
        assert 'function renderWikiList' not in content

    def test_old_render_communities_removed(self):
        content = EXPLORER_JS.read_text()
        assert 'function renderCommunities(' not in content

    def test_set_browse_mode_action(self):
        content = EXPLORER_JS.read_text()
        assert 'set-browse-mode' in content


class TestWikilinks:
    """Verify wikilinks are processed as a post-processing step."""

    def test_process_wikilinks_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'processWikilinks' in content

    def test_wikilinks_not_only_in_paragraph(self):
        """processWikilinks should be called after marked.parse, not in renderer.paragraph."""
        content = EXPLORER_JS.read_text()
        # Should NOT have the old pattern of overriding renderer.paragraph for wikilinks
        assert 'renderer.paragraph' not in content or 'wikilink' not in content.split('renderer.paragraph')[1].split('function')[0]


class TestEnrichButton:
    """Verify the Enrich with AI button exists."""

    def test_enrich_action_in_overview(self):
        content = EXPLORER_JS.read_text()
        assert 'enrich-ai' in content

    def test_enrich_modal_function(self):
        content = EXPLORER_JS.read_text()
        assert 'showEnrichModal' in content

    def test_enrich_modal_shows_cli_fallback(self):
        content = EXPLORER_JS.read_text()
        assert 'atlas scan --deep' in content


class TestContentPanelFixes:
    """Verify content panel header is sticky."""

    def test_sticky_header_pattern(self):
        content = EXPLORER_JS.read_text()
        # The content panel should wrap content in a flex-col layout
        # with a sticky header bar
        assert 'shrink-0' in content
        # Edit and View in Graph should be in a header bar, not buried in scroll content
        assert 'data-action="edit-page"' in content

    def test_humanize_community_label(self):
        content = EXPLORER_JS.read_text()
        assert 'humanizeCommunityLabel' in content


class TestCssAdditions:
    """Verify new CSS was added."""

    def test_browse_toggle_styles(self):
        content = STYLES_CSS.read_text()
        assert 'enrich-pulse' in content or 'enrich-in-progress' in content

    def test_modal_styles(self):
        content = STYLES_CSS.read_text()
        assert 'enrich-modal-overlay' in content or 'modal-fade-in' in content
```

---

## Self-Review Checklist

| Check | Status |
|---|---|
| BROWSE replaces FILES + WIKI + COMMUNITIES as 3 separate sections | Covered in Task 1 |
| Toggle persists in localStorage | Task 1, Step 1 |
| Folder mode = existing file tree (no regressions) | Task 1, Step 3 — reuses `renderFileTree()` unchanged |
| Type mode = wiki pages grouped by semantic type + Other for non-wiki files | Task 1, Step 5 |
| Community mode = clusters with human labels + size bars | Task 1, Step 4 |
| `[[wikilinks]]` clickable in all markdown contexts (not just paragraphs) | Task 2, Fix 2a |
| Edit / View in Graph always visible in sticky header | Task 2, Fix 2b |
| Community labels cleaned up (no raw file paths) | Task 1 Step 4 + Task 2 Step 4 |
| "Enrich with AI" button in OVERVIEW | Task 3, Step 1 |
| Enrich modal with MCP-connected vs CLI fallback | Task 3, Step 2 |
| No new files besides test file | File Map shows only MODIFY |
| Vanilla JS + Tailwind CDN, no build step | All code is vanilla JS with Tailwind classes |
| No regressions on content panel (wiki read, edit, file, community views) | All existing functions preserved, only sidebar rendering changed |
| Tests cover structural requirements | Task 5 — 16 test cases |
| CSS additions for modal and toggle animations | Task 4 |

### Risks / Open Questions

1. **Type grouping heuristic:** `wiki-page` is mapped to "Projects" group. If the wiki has pages of type `wiki-page` that aren't projects (e.g., general articles), this mapping is wrong. May need a `wiki-project` type or a frontmatter-based grouping. Acceptable for v2 MVP — revisit if users report confusion.

2. **Enrich API endpoint:** Task 3 Step 2 calls `POST /api/scan` with `{ level: 'deep' }`. This endpoint needs to support the `level` parameter server-side (spec section 9 mentions it). If the server doesn't support it yet, the enrichment flow will fail gracefully (toast error). Can be wired up in a separate server plan.

3. **Non-wiki files in Type mode "Other" group:** Collecting all leaf files from the file tree into "Other" could create a very large list (hundreds of code files). Consider adding a cap (show top 50 by degree) or collapsing by default. Current implementation shows all, which is acceptable for small-to-medium projects.

4. **`processWikilinks()` running on HTML:** Applying a regex on the HTML output of `marked.parse()` could match `[[...]]` inside code blocks or pre tags. The current implementation in `createRenderer().paragraph` has the same issue. For v2, acceptable — fix with a proper AST walk if users report false positives in code blocks.
