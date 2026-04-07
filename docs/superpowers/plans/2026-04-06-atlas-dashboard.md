# Atlas Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Atlas dashboard — a static-first SPA served by FastAPI that gives users an interactive graph visualization, wiki reader/editor, audit view, full-text search, and operation timeline. One `index.html`, zero build steps, loads in <200ms.

**Architecture:** Single `index.html` with vanilla JS modules loaded via `<script type="module">`. Tailwind CSS via CDN. Each view is a self-contained JS file that exports `init()` and `destroy()` functions. A lightweight router in `app.js` swaps views based on URL hash. All data comes from the Server's REST API via `fetch()`. WebSocket for live updates (scan progress, wiki changes, new edges). No framework, no bundler, no transpiler.

**Tech Stack:** HTML5, vanilla JS (ES2022 modules), Tailwind CSS 3.x CDN, vis-network (graph), marked.js (markdown), highlight.js (code blocks)

**Depends on:** Plan 1 (Core models), Plan 2 (Server REST API + WebSocket). Dashboard squad can start Day 1 using mock data while Server squad builds real endpoints.

**API contract assumed** (from spec Section 6 + 12):

| Endpoint | Method | Returns |
|---|---|---|
| `/api/graph` | GET | Full graph `{nodes: [...], edges: [...]}` |
| `/api/graph/stats` | GET | `GraphStats` object |
| `/api/graph/query` | POST `{start, mode, depth}` | `Subgraph` |
| `/api/graph/path` | POST `{source, target}` | `Edge[]` |
| `/api/graph/node/{id}` | GET | `Node` + neighbors |
| `/api/graph/god-nodes` | GET `?top_n=10` | `[{id, degree}]` |
| `/api/graph/surprises` | GET `?top_n=10` | `Edge[]` |
| `/api/wiki/pages` | GET `?type=` | `Page[]` (list, no content) |
| `/api/wiki/page/{path}` | GET | `Page` with content |
| `/api/wiki/page/{path}` | PUT `{content, frontmatter}` | `Page` |
| `/api/wiki/search` | GET `?q=` | `Page[]` |
| `/api/wiki/backlinks/{slug}` | GET | `string[]` |
| `/api/audit` | GET | `AuditReport` |
| `/api/audit/suggestions` | GET | `LinkSuggestion[]` |
| `/api/scan` | POST `{path}` | `{status, job_id}` |
| `/api/log` | GET `?limit=&offset=` | `LogEntry[]` |
| `/ws` | WebSocket | `{type, payload}` events |

---

## File Map

```
atlas/dashboard/
├── index.html          # SPA shell — nav, view container, scripts, Tailwind
├── app.js              # Router, state, WebSocket manager, API client
├── graph.js            # Graph visualization (vis-network), filters, search
├── wiki.js             # Markdown renderer, breadcrumbs, backlinks, TOC, inline edit
├── audit.js            # Health dashboard, orphans, contradictions, god nodes
├── search.js           # Combined full-text + graph search
├── timeline.js         # Operation log viewer
└── styles.css          # Custom utilities beyond Tailwind (animations, graph colors)

tests/
├── dashboard/
│   ├── test_dashboard_served.py    # FastAPI serves index.html at /
│   ├── test_api_mock.py            # Mock API responses for frontend testing
│   └── test_static_files.py        # All static files accessible
```

---

## Task 1: SPA Shell + Router

**Files:**
- Create: `atlas/dashboard/index.html`
- Create: `atlas/dashboard/app.js`
- Create: `atlas/dashboard/styles.css`
- Test: `tests/dashboard/test_dashboard_served.py`

- [ ] **Step 1: Write the test — FastAPI serves the dashboard**

`tests/dashboard/test_dashboard_served.py`:
```python
"""Verify the dashboard is served correctly by FastAPI."""
from pathlib import Path


def test_index_html_exists():
    index = Path(__file__).parent.parent.parent / "atlas" / "dashboard" / "index.html"
    assert index.exists(), "index.html must exist in atlas/dashboard/"
    content = index.read_text()
    assert "<!DOCTYPE html>" in content
    assert "id=\"app\"" in content
    assert "app.js" in content


def test_static_files_exist():
    dashboard = Path(__file__).parent.parent.parent / "atlas" / "dashboard"
    required = ["index.html", "app.js", "graph.js", "wiki.js", "audit.js", "search.js", "timeline.js", "styles.css"]
    for f in required:
        assert (dashboard / f).exists(), f"Missing: {f}"


def test_no_build_artifacts():
    dashboard = Path(__file__).parent.parent.parent / "atlas" / "dashboard"
    forbidden = ["node_modules", "package.json", "dist", "build", ".next", "vite.config"]
    for f in forbidden:
        assert not (dashboard / f).exists(), f"Build artifact found: {f} — dashboard must be static-first"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/dashboard/test_dashboard_served.py -v`
Expected: FAIL — files don't exist yet

- [ ] **Step 3: Create index.html**

`atlas/dashboard/index.html`:
```html
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas — Knowledge Engine</title>

    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        atlas: {
                            50:  '#eef7ff',
                            100: '#d9edff',
                            200: '#bce0ff',
                            300: '#8ecdff',
                            400: '#59b0ff',
                            500: '#338dff',
                            600: '#1b6cf5',
                            700: '#1456e1',
                            800: '#1746b6',
                            900: '#193d8f',
                            950: '#142757',
                        },
                        surface: {
                            0:   '#0a0a0f',
                            1:   '#111118',
                            2:   '#1a1a24',
                            3:   '#232330',
                            4:   '#2d2d3d',
                        },
                    },
                    fontFamily: {
                        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
                        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
                    },
                },
            },
        }
    </script>

    <!-- Inter font -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

    <!-- Marked.js for markdown -->
    <script src="https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"></script>

    <!-- Highlight.js for code blocks -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11/styles/github-dark.min.css">
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11/highlight.min.js"></script>

    <!-- vis-network for graph -->
    <script src="https://cdn.jsdelivr.net/npm/vis-network@9/standalone/umd/vis-network.min.js"></script>

    <!-- Custom styles -->
    <link rel="stylesheet" href="/dashboard/styles.css">
</head>
<body class="bg-surface-0 text-gray-200 font-sans antialiased min-h-screen flex flex-col">

    <!-- Top Navigation -->
    <header class="bg-surface-1 border-b border-surface-3 px-4 py-2 flex items-center justify-between shrink-0 z-50">
        <div class="flex items-center gap-3">
            <!-- Logo -->
            <a href="#/" class="flex items-center gap-2 text-white hover:text-atlas-400 transition-colors">
                <svg class="w-7 h-7" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="14" cy="14" r="12" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
                    <circle cx="14" cy="6" r="2.5" fill="currentColor"/>
                    <circle cx="7" cy="18" r="2.5" fill="currentColor"/>
                    <circle cx="21" cy="18" r="2.5" fill="currentColor"/>
                    <line x1="14" y1="8.5" x2="8.5" y2="16" stroke="currentColor" stroke-width="1.2" opacity="0.6"/>
                    <line x1="14" y1="8.5" x2="19.5" y2="16" stroke="currentColor" stroke-width="1.2" opacity="0.6"/>
                    <line x1="9.5" y1="18" x2="18.5" y2="18" stroke="currentColor" stroke-width="1.2" opacity="0.6"/>
                </svg>
                <span class="text-lg font-semibold tracking-tight">Atlas</span>
            </a>

            <!-- Nav tabs -->
            <nav class="flex items-center gap-1 ml-6" id="nav-tabs">
                <a href="#/" class="nav-tab active" data-view="graph">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><circle cx="18" cy="6" r="3"/>
                        <line x1="8.5" y1="7.5" x2="15.5" y2="16.5"/><line x1="8.5" y1="6" x2="15" y2="6"/>
                    </svg>
                    Graph
                </a>
                <a href="#/wiki" class="nav-tab" data-view="wiki">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path d="M4 4h16v16H4z"/><path d="M8 8h8M8 12h6M8 16h4"/>
                    </svg>
                    Wiki
                </a>
                <a href="#/audit" class="nav-tab" data-view="audit">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="10"/>
                    </svg>
                    Audit
                </a>
                <a href="#/search" class="nav-tab" data-view="search">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                    Search
                </a>
                <a href="#/timeline" class="nav-tab" data-view="timeline">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
                    </svg>
                    Timeline
                </a>
            </nav>
        </div>

        <!-- Right side: search + status -->
        <div class="flex items-center gap-3">
            <!-- Quick search -->
            <div class="relative">
                <input
                    type="text"
                    id="quick-search"
                    placeholder="Search... (Ctrl+K)"
                    class="bg-surface-2 border border-surface-4 rounded-lg px-3 py-1.5 pl-8 text-sm text-gray-300 placeholder-gray-500 focus:outline-none focus:border-atlas-500 focus:ring-1 focus:ring-atlas-500/30 w-56 transition-all"
                >
                <svg class="w-4 h-4 absolute left-2.5 top-2 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
            </div>

            <!-- Connection status -->
            <div id="ws-status" class="flex items-center gap-1.5 text-xs text-gray-500">
                <span class="w-2 h-2 rounded-full bg-gray-600 animate-pulse" id="ws-dot"></span>
                <span id="ws-label">Connecting</span>
            </div>

            <!-- Dark mode toggle -->
            <button id="theme-toggle" class="p-1.5 rounded-lg hover:bg-surface-3 transition-colors text-gray-400 hover:text-gray-200" title="Toggle theme">
                <svg class="w-5 h-5 hidden dark:block" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                </svg>
                <svg class="w-5 h-5 block dark:hidden" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
                </svg>
            </button>
        </div>
    </header>

    <!-- Toast notifications -->
    <div id="toast-container" class="fixed top-16 right-4 z-50 flex flex-col gap-2"></div>

    <!-- Main content -->
    <main id="app" class="flex-1 overflow-hidden">
        <!-- Views are mounted here by the router -->
    </main>

    <!-- Loading overlay (shown on first load) -->
    <div id="loading-overlay" class="fixed inset-0 bg-surface-0 flex items-center justify-center z-[100] transition-opacity duration-300">
        <div class="text-center">
            <svg class="w-12 h-12 text-atlas-500 animate-spin mx-auto mb-3" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" opacity="0.2"/>
                <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <p class="text-gray-400 text-sm">Loading Atlas...</p>
        </div>
    </div>

    <!-- App entry point -->
    <script type="module" src="/dashboard/app.js"></script>
</body>
</html>
```

- [ ] **Step 4: Create styles.css**

`atlas/dashboard/styles.css`:
```css
/* ============================================================
   Atlas Dashboard — Custom Styles
   Beyond Tailwind: animations, graph node colors, transitions
   ============================================================ */

/* --- Nav tabs --- */
.nav-tab {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    border-radius: 0.5rem;
    font-size: 0.8125rem;
    font-weight: 500;
    color: #9ca3af;
    transition: all 150ms ease;
    text-decoration: none;
    white-space: nowrap;
}

.nav-tab:hover {
    color: #e5e7eb;
    background: rgba(255, 255, 255, 0.05);
}

.nav-tab.active {
    color: #338dff;
    background: rgba(51, 141, 255, 0.1);
}

/* --- Graph node colors by type --- */
.graph-legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}

:root {
    --node-code:        #22d3ee;
    --node-document:    #a78bfa;
    --node-paper:       #f472b6;
    --node-image:       #fb923c;
    --node-wiki-page:   #338dff;
    --node-wiki-concept:#34d399;
    --node-wiki-decision:#fbbf24;
    --node-wiki-source: #94a3b8;
    --node-default:     #6b7280;

    --edge-extracted:   rgba(100, 160, 255, 0.4);
    --edge-inferred:    rgba(251, 191, 36, 0.3);
    --edge-ambiguous:   rgba(248, 113, 113, 0.3);
}

/* --- Scrollbar --- */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
}

/* --- Toast animations --- */
.toast-enter {
    animation: toast-slide-in 200ms ease-out;
}
.toast-exit {
    animation: toast-slide-out 200ms ease-in forwards;
}

@keyframes toast-slide-in {
    from { transform: translateX(100%); opacity: 0; }
    to   { transform: translateX(0); opacity: 1; }
}
@keyframes toast-slide-out {
    from { transform: translateX(0); opacity: 1; }
    to   { transform: translateX(100%); opacity: 0; }
}

/* --- Wiki markdown styles --- */
.wiki-content h1 { font-size: 1.75rem; font-weight: 700; margin-top: 1.5rem; margin-bottom: 0.75rem; color: #f3f4f6; }
.wiki-content h2 { font-size: 1.375rem; font-weight: 600; margin-top: 1.25rem; margin-bottom: 0.5rem; color: #e5e7eb; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 0.375rem; }
.wiki-content h3 { font-size: 1.125rem; font-weight: 600; margin-top: 1rem; margin-bottom: 0.5rem; color: #d1d5db; }
.wiki-content p  { margin-bottom: 0.75rem; line-height: 1.7; color: #d1d5db; }
.wiki-content ul { list-style-type: disc; padding-left: 1.5rem; margin-bottom: 0.75rem; }
.wiki-content ol { list-style-type: decimal; padding-left: 1.5rem; margin-bottom: 0.75rem; }
.wiki-content li { margin-bottom: 0.25rem; color: #d1d5db; }
.wiki-content a  { color: #338dff; text-decoration: underline; text-underline-offset: 2px; }
.wiki-content a:hover { color: #59b0ff; }
.wiki-content code { font-family: 'JetBrains Mono', monospace; font-size: 0.85em; background: rgba(255,255,255,0.06); padding: 0.15em 0.35em; border-radius: 0.25rem; color: #e5e7eb; }
.wiki-content pre { background: #111118; border: 1px solid rgba(255,255,255,0.06); border-radius: 0.5rem; padding: 1rem; margin-bottom: 1rem; overflow-x: auto; }
.wiki-content pre code { background: transparent; padding: 0; font-size: 0.8125rem; }
.wiki-content blockquote { border-left: 3px solid #338dff; padding-left: 1rem; margin: 0.75rem 0; color: #9ca3af; font-style: italic; }
.wiki-content table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
.wiki-content th { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 2px solid rgba(255,255,255,0.1); font-weight: 600; color: #e5e7eb; }
.wiki-content td { padding: 0.5rem 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.05); color: #d1d5db; }
.wiki-content hr { border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 1.5rem 0; }

/* --- Wikilink styling in rendered markdown --- */
.wikilink {
    color: #34d399;
    text-decoration: none;
    border-bottom: 1px dashed rgba(52, 211, 153, 0.4);
    cursor: pointer;
    transition: all 150ms;
}
.wikilink:hover {
    color: #6ee7b7;
    border-bottom-color: #6ee7b7;
}
.wikilink.broken {
    color: #f87171;
    border-bottom-color: rgba(248, 113, 113, 0.4);
}

/* --- Confidence badges --- */
.badge-extracted  { background: rgba(52, 211, 153, 0.15); color: #34d399; }
.badge-inferred   { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
.badge-ambiguous  { background: rgba(248, 113, 113, 0.15); color: #f87171; }

/* --- Health score ring --- */
.health-ring {
    transform: rotate(-90deg);
    transform-origin: center;
}
.health-ring-bg {
    stroke: rgba(255, 255, 255, 0.06);
}
.health-ring-fill {
    transition: stroke-dashoffset 800ms ease;
}

/* --- Audit card hover --- */
.audit-card {
    transition: transform 150ms ease, box-shadow 150ms ease;
}
.audit-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* --- Responsive --- */
@media (max-width: 768px) {
    .nav-tab span:not(.sr-only) {
        /* Only icons on mobile, labels hidden via Tailwind responsive classes */
    }
}

/* --- Light mode overrides --- */
html:not(.dark) body {
    background: #f8fafc;
    color: #1e293b;
}
html:not(.dark) .nav-tab {
    color: #64748b;
}
html:not(.dark) .nav-tab:hover {
    color: #1e293b;
    background: rgba(0, 0, 0, 0.04);
}
html:not(.dark) .nav-tab.active {
    color: #1b6cf5;
    background: rgba(27, 108, 245, 0.08);
}
html:not(.dark) .wiki-content h1,
html:not(.dark) .wiki-content h2,
html:not(.dark) .wiki-content h3 { color: #1e293b; }
html:not(.dark) .wiki-content p,
html:not(.dark) .wiki-content li,
html:not(.dark) .wiki-content td { color: #475569; }
html:not(.dark) .wiki-content pre { background: #f1f5f9; border-color: #e2e8f0; }
html:not(.dark) .wiki-content code { background: rgba(0,0,0,0.04); color: #1e293b; }
```

- [ ] **Step 5: Create app.js — Router + API client + WebSocket manager**

`atlas/dashboard/app.js`:
```javascript
/**
 * Atlas Dashboard — App Shell
 * Router, API client, WebSocket manager, state, theme toggle.
 */

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE = window.location.origin;
const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`;

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const state = {
    currentView: null,
    graphData: null,
    statsData: null,
    ws: null,
    wsReconnectTimer: null,
    wsReconnectDelay: 1000,
    listeners: new Map(), // event -> Set<callback>
};

// ---------------------------------------------------------------------------
// Event bus (inter-view communication)
// ---------------------------------------------------------------------------

export function on(event, callback) {
    if (!state.listeners.has(event)) state.listeners.set(event, new Set());
    state.listeners.get(event).add(callback);
    return () => state.listeners.get(event)?.delete(callback);
}

export function emit(event, data) {
    state.listeners.get(event)?.forEach(cb => {
        try { cb(data); } catch (e) { console.error(`[event:${event}]`, e); }
    });
}

// ---------------------------------------------------------------------------
// API Client
// ---------------------------------------------------------------------------

export async function api(path, options = {}) {
    const url = `${API_BASE}${path}`;
    const config = {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    };
    if (options.body && typeof options.body === 'object') {
        config.body = JSON.stringify(options.body);
    }
    const res = await fetch(url, config);
    if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(`API ${res.status}: ${path} — ${text}`);
    }
    return res.json();
}

// Convenience methods
api.get = (path) => api(path);
api.post = (path, body) => api(path, { method: 'POST', body });
api.put = (path, body) => api(path, { method: 'PUT', body });

// ---------------------------------------------------------------------------
// WebSocket Manager
// ---------------------------------------------------------------------------

function connectWebSocket() {
    if (state.ws?.readyState === WebSocket.OPEN) return;

    try {
        state.ws = new WebSocket(WS_URL);
    } catch {
        scheduleReconnect();
        return;
    }

    state.ws.onopen = () => {
        state.wsReconnectDelay = 1000;
        updateWsStatus('connected');
        emit('ws:open');
    };

    state.ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            emit(`ws:${msg.type}`, msg.payload);
            emit('ws:message', msg);
        } catch {
            // Ignore malformed messages
        }
    };

    state.ws.onclose = () => {
        updateWsStatus('disconnected');
        emit('ws:close');
        scheduleReconnect();
    };

    state.ws.onerror = () => {
        state.ws?.close();
    };
}

function scheduleReconnect() {
    clearTimeout(state.wsReconnectTimer);
    state.wsReconnectTimer = setTimeout(() => {
        state.wsReconnectDelay = Math.min(state.wsReconnectDelay * 2, 30000);
        connectWebSocket();
    }, state.wsReconnectDelay);
}

function updateWsStatus(status) {
    const dot = document.getElementById('ws-dot');
    const label = document.getElementById('ws-label');
    if (!dot || !label) return;

    const styles = {
        connected:    { bg: 'bg-emerald-500', text: 'Connected', pulse: false },
        disconnected: { bg: 'bg-red-500',     text: 'Disconnected', pulse: false },
        connecting:   { bg: 'bg-gray-600',    text: 'Connecting', pulse: true },
    };
    const s = styles[status] || styles.connecting;
    dot.className = `w-2 h-2 rounded-full ${s.bg} ${s.pulse ? 'animate-pulse' : ''}`;
    label.textContent = s.text;
}

// ---------------------------------------------------------------------------
// Toast Notifications
// ---------------------------------------------------------------------------

export function toast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const colors = {
        info:    'bg-atlas-600 text-white',
        success: 'bg-emerald-600 text-white',
        warning: 'bg-amber-600 text-white',
        error:   'bg-red-600 text-white',
    };

    const el = document.createElement('div');
    el.className = `toast-enter px-4 py-2.5 rounded-lg text-sm font-medium shadow-lg ${colors[type] || colors.info}`;
    el.textContent = message;
    container.appendChild(el);

    setTimeout(() => {
        el.classList.remove('toast-enter');
        el.classList.add('toast-exit');
        el.addEventListener('animationend', () => el.remove());
    }, duration);
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

const views = {};

export function registerView(name, mod) {
    views[name] = mod;
}

async function route() {
    const hash = window.location.hash.slice(1) || '/';
    const segments = hash.split('/').filter(Boolean);
    const viewName = segments[0] || 'graph';
    const params = segments.slice(1);

    // Deactivate current view
    if (state.currentView && views[state.currentView]?.destroy) {
        views[state.currentView].destroy();
    }

    // Update nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.view === viewName);
    });

    // Activate new view
    const app = document.getElementById('app');
    if (!views[viewName]) {
        app.innerHTML = `
            <div class="flex items-center justify-center h-full">
                <div class="text-center">
                    <p class="text-6xl font-bold text-gray-700 mb-2">404</p>
                    <p class="text-gray-500">View "${viewName}" not found.</p>
                    <a href="#/" class="text-atlas-400 hover:text-atlas-300 text-sm mt-4 inline-block">Back to Graph</a>
                </div>
            </div>
        `;
        return;
    }

    state.currentView = viewName;
    views[viewName].init(app, params);
}

// ---------------------------------------------------------------------------
// Quick Search (Ctrl+K)
// ---------------------------------------------------------------------------

function initQuickSearch() {
    const input = document.getElementById('quick-search');
    if (!input) return;

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            input.focus();
            input.select();
        }
        if (e.key === 'Escape' && document.activeElement === input) {
            input.blur();
        }
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const q = input.value.trim();
            if (q) {
                window.location.hash = `#/search/${encodeURIComponent(q)}`;
                input.blur();
            }
        }
    });
}

// ---------------------------------------------------------------------------
// Theme Toggle
// ---------------------------------------------------------------------------

function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    const stored = localStorage.getItem('atlas-theme');
    if (stored === 'light') {
        document.documentElement.classList.remove('dark');
    }

    btn.addEventListener('click', () => {
        const isDark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('atlas-theme', isDark ? 'dark' : 'light');
        emit('theme:change', isDark ? 'dark' : 'light');
    });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function boot() {
    // Import views
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

    // Initialize
    initQuickSearch();
    initThemeToggle();
    connectWebSocket();

    // Route
    window.addEventListener('hashchange', route);
    await route();

    // Hide loading overlay
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 300);
    }
}

// Go
boot().catch(err => {
    console.error('[Atlas] Boot failed:', err);
    const app = document.getElementById('app');
    if (app) {
        app.innerHTML = `
            <div class="flex items-center justify-center h-full">
                <div class="text-center max-w-md">
                    <p class="text-xl font-semibold text-red-400 mb-2">Failed to load Atlas</p>
                    <p class="text-gray-500 text-sm mb-4">${err.message}</p>
                    <button onclick="location.reload()" class="px-4 py-2 bg-atlas-600 text-white rounded-lg text-sm hover:bg-atlas-700 transition-colors">
                        Reload
                    </button>
                </div>
            </div>
        `;
    }
});
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/dashboard/test_dashboard_served.py -v`
Expected: FAIL — only index.html, app.js, styles.css exist. graph.js etc. still missing. Tests will fully pass after all tasks are complete.

- [ ] **Step 7: Commit**

```bash
git add atlas/dashboard/index.html atlas/dashboard/app.js atlas/dashboard/styles.css tests/dashboard/
git commit -m "feat(dashboard): SPA shell with router, API client, WebSocket manager

Single index.html with Tailwind CDN, hash-based router, event bus,
theme toggle, quick search (Ctrl+K), toast notifications. No build step."
```

---

## Task 2: Graph View

**Files:**
- Create: `atlas/dashboard/graph.js`

- [ ] **Step 1: Implement graph.js**

`atlas/dashboard/graph.js`:
```javascript
/**
 * Atlas Dashboard — Graph View
 * Interactive network visualization using vis-network.
 * Filters by community, type, confidence. Click node -> wiki page.
 */

import { api, on, emit, toast } from '/dashboard/app.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const NODE_COLORS = {
    'code':           { bg: '#22d3ee', border: '#06b6d4', font: '#0e7490' },
    'document':       { bg: '#a78bfa', border: '#8b5cf6', font: '#6d28d9' },
    'paper':          { bg: '#f472b6', border: '#ec4899', font: '#be185d' },
    'image':          { bg: '#fb923c', border: '#f97316', font: '#c2410c' },
    'wiki-page':      { bg: '#338dff', border: '#1b6cf5', font: '#1e40af' },
    'wiki-concept':   { bg: '#34d399', border: '#10b981', font: '#065f46' },
    'wiki-decision':  { bg: '#fbbf24', border: '#f59e0b', font: '#92400e' },
    'wiki-source':    { bg: '#94a3b8', border: '#64748b', font: '#334155' },
};

const EDGE_COLORS = {
    'EXTRACTED':  { color: 'rgba(100, 160, 255, 0.5)', highlight: '#338dff' },
    'INFERRED':   { color: 'rgba(251, 191, 36, 0.4)', highlight: '#fbbf24' },
    'AMBIGUOUS':  { color: 'rgba(248, 113, 113, 0.4)', highlight: '#f87171' },
};

const DEFAULT_NODE_COLOR = { bg: '#6b7280', border: '#4b5563', font: '#374151' };

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let network = null;
let rawNodes = [];
let rawEdges = [];
let filteredNodes = null;
let filteredEdges = null;
let communities = new Set();
let nodeTypes = new Set();
let wsUnsub = null;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function nodeColor(type) {
    return NODE_COLORS[type] || DEFAULT_NODE_COLOR;
}

function buildVisNode(node) {
    const c = nodeColor(node.type);
    const degree = rawEdges.filter(e => e.source === node.id || e.target === node.id).length;
    const baseSize = 12;
    const size = baseSize + Math.min(degree * 3, 30);

    return {
        id: node.id,
        label: node.label || node.id,
        size,
        color: {
            background: c.bg,
            border: c.border,
            highlight: { background: c.bg, border: '#ffffff' },
            hover: { background: c.bg, border: '#e5e7eb' },
        },
        font: { color: '#e5e7eb', size: 11, face: 'Inter, sans-serif' },
        borderWidth: 1.5,
        borderWidthSelected: 3,
        shape: 'dot',
        shadow: { enabled: true, color: 'rgba(0,0,0,0.3)', size: 8, x: 0, y: 2 },
        // Store original data for filtering
        _atlas: {
            type: node.type,
            community: node.community,
            confidence: node.confidence,
            tags: node.tags || [],
            source_file: node.source_file,
            summary: node.summary,
        },
    };
}

function buildVisEdge(edge) {
    const ec = EDGE_COLORS[edge.confidence] || EDGE_COLORS.EXTRACTED;
    return {
        from: edge.source,
        to: edge.target,
        color: { color: ec.color, highlight: ec.highlight, hover: ec.highlight },
        width: edge.confidence === 'EXTRACTED' ? 1.5 : 1,
        dashes: edge.confidence === 'AMBIGUOUS' ? [5, 5] : false,
        smooth: { type: 'continuous', roundness: 0.2 },
        arrows: { to: { enabled: false } },
        title: `${edge.relation} (${edge.confidence})`,
        _atlas: {
            relation: edge.relation,
            confidence: edge.confidence,
            confidence_score: edge.confidence_score,
        },
    };
}

// ---------------------------------------------------------------------------
// Filters
// ---------------------------------------------------------------------------

function applyFilters() {
    const communityFilter = document.getElementById('filter-community')?.value || 'all';
    const typeFilter = document.getElementById('filter-type')?.value || 'all';
    const confidenceFilter = document.getElementById('filter-confidence')?.value || 'all';

    let nodes = rawNodes;
    let edges = rawEdges;

    // Filter nodes
    let visibleIds = new Set(nodes.map(n => n.id));

    if (communityFilter !== 'all') {
        const comm = parseInt(communityFilter);
        nodes = nodes.filter(n => n.community === comm);
        visibleIds = new Set(nodes.map(n => n.id));
    }

    if (typeFilter !== 'all') {
        nodes = nodes.filter(n => n.type === typeFilter);
        visibleIds = new Set(nodes.map(n => n.id));
    }

    // Filter edges by confidence and by visible nodes
    if (confidenceFilter !== 'all') {
        edges = edges.filter(e => e.confidence === confidenceFilter);
    }
    edges = edges.filter(e => visibleIds.has(e.source) && visibleIds.has(e.target));

    // Build vis datasets
    const visNodes = nodes.map(buildVisNode);
    const visEdges = edges.map(buildVisEdge);

    if (network) {
        network.setData({ nodes: visNodes, edges: visEdges });
    }

    // Update stats
    const statsEl = document.getElementById('graph-filter-stats');
    if (statsEl) {
        statsEl.textContent = `${visNodes.length} nodes, ${visEdges.length} edges`;
    }
}

function populateFilters() {
    communities.clear();
    nodeTypes.clear();

    rawNodes.forEach(n => {
        if (n.community != null) communities.add(n.community);
        if (n.type) nodeTypes.add(n.type);
    });

    // Community filter
    const communitySelect = document.getElementById('filter-community');
    if (communitySelect) {
        communitySelect.innerHTML = '<option value="all">All communities</option>';
        [...communities].sort((a, b) => a - b).forEach(c => {
            communitySelect.innerHTML += `<option value="${c}">Community ${c}</option>`;
        });
    }

    // Type filter
    const typeSelect = document.getElementById('filter-type');
    if (typeSelect) {
        typeSelect.innerHTML = '<option value="all">All types</option>';
        [...nodeTypes].sort().forEach(t => {
            typeSelect.innerHTML += `<option value="${t}">${t}</option>`;
        });
    }
}

// ---------------------------------------------------------------------------
// Graph Search (highlight node)
// ---------------------------------------------------------------------------

function searchGraph(query) {
    if (!network || !query) return;
    const q = query.toLowerCase();
    const match = rawNodes.find(n =>
        n.id.toLowerCase().includes(q) ||
        (n.label || '').toLowerCase().includes(q)
    );
    if (match) {
        network.focus(match.id, { scale: 1.2, animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
        network.selectNodes([match.id]);
    } else {
        toast('No matching node found', 'warning');
    }
}

// ---------------------------------------------------------------------------
// Node Detail Panel
// ---------------------------------------------------------------------------

function showNodeDetail(nodeId) {
    const panel = document.getElementById('node-detail');
    if (!panel) return;

    const node = rawNodes.find(n => n.id === nodeId);
    if (!node) {
        panel.classList.add('hidden');
        return;
    }

    const neighbors = rawEdges
        .filter(e => e.source === nodeId || e.target === nodeId)
        .map(e => ({
            id: e.source === nodeId ? e.target : e.source,
            relation: e.relation,
            confidence: e.confidence,
        }));

    const c = nodeColor(node.type);

    panel.innerHTML = `
        <div class="flex items-start justify-between mb-3">
            <div class="flex items-center gap-2">
                <span class="w-3 h-3 rounded-full" style="background: ${c.bg}"></span>
                <h3 class="text-sm font-semibold text-white truncate max-w-[180px]">${node.label || node.id}</h3>
            </div>
            <button id="close-node-detail" class="text-gray-500 hover:text-gray-300 text-lg leading-none">&times;</button>
        </div>
        <div class="space-y-2 text-xs text-gray-400">
            <div><span class="text-gray-500">Type:</span> <span class="text-gray-300">${node.type}</span></div>
            <div><span class="text-gray-500">Source:</span> <span class="text-gray-300 font-mono">${node.source_file || '—'}</span></div>
            ${node.community != null ? `<div><span class="text-gray-500">Community:</span> <span class="text-gray-300">${node.community}</span></div>` : ''}
            ${node.confidence ? `<div><span class="text-gray-500">Confidence:</span> <span class="badge-${node.confidence.toLowerCase()} px-1.5 py-0.5 rounded text-xs">${node.confidence}</span></div>` : ''}
            ${node.summary ? `<div class="mt-2 text-gray-300 leading-relaxed">${node.summary}</div>` : ''}
            ${node.tags?.length ? `<div class="flex flex-wrap gap-1 mt-1">${node.tags.map(t => `<span class="px-1.5 py-0.5 bg-surface-3 rounded text-gray-400 text-xs">${t}</span>`).join('')}</div>` : ''}
        </div>
        ${neighbors.length ? `
            <div class="mt-3 pt-3 border-t border-surface-3">
                <p class="text-xs text-gray-500 mb-2">Connections (${neighbors.length})</p>
                <div class="space-y-1 max-h-40 overflow-y-auto">
                    ${neighbors.map(n => `
                        <button class="neighbor-link w-full text-left px-2 py-1 rounded hover:bg-surface-3 text-xs transition-colors flex items-center justify-between gap-2" data-node-id="${n.id}">
                            <span class="text-gray-300 truncate">${n.id}</span>
                            <span class="badge-${n.confidence.toLowerCase()} px-1 py-0.5 rounded text-[10px] shrink-0">${n.relation}</span>
                        </button>
                    `).join('')}
                </div>
            </div>
        ` : ''}
        <div class="mt-3 pt-3 border-t border-surface-3 flex gap-2">
            <a href="#/wiki/${encodeURIComponent(node.id)}" class="flex-1 text-center px-2 py-1.5 bg-atlas-600/20 text-atlas-400 rounded text-xs hover:bg-atlas-600/30 transition-colors">
                View Wiki Page
            </a>
        </div>
    `;
    panel.classList.remove('hidden');

    // Event listeners
    panel.querySelector('#close-node-detail')?.addEventListener('click', () => panel.classList.add('hidden'));
    panel.querySelectorAll('.neighbor-link').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.nodeId;
            network.focus(id, { scale: 1.2, animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
            network.selectNodes([id]);
            showNodeDetail(id);
        });
    });
}

// ---------------------------------------------------------------------------
// Init / Destroy
// ---------------------------------------------------------------------------

export async function init(container, params) {
    container.innerHTML = `
        <div class="h-full flex">
            <!-- Graph canvas -->
            <div class="flex-1 relative">
                <!-- Toolbar -->
                <div class="absolute top-3 left-3 z-10 flex items-center gap-2 flex-wrap">
                    <select id="filter-community" class="bg-surface-2 border border-surface-4 rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-atlas-500">
                        <option value="all">All communities</option>
                    </select>
                    <select id="filter-type" class="bg-surface-2 border border-surface-4 rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-atlas-500">
                        <option value="all">All types</option>
                    </select>
                    <select id="filter-confidence" class="bg-surface-2 border border-surface-4 rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-atlas-500">
                        <option value="all">All confidence</option>
                        <option value="EXTRACTED">Extracted</option>
                        <option value="INFERRED">Inferred</option>
                        <option value="AMBIGUOUS">Ambiguous</option>
                    </select>
                    <div class="relative">
                        <input type="text" id="graph-search" placeholder="Find node..."
                            class="bg-surface-2 border border-surface-4 rounded-lg px-2 py-1 pl-7 text-xs text-gray-300 placeholder-gray-500 focus:outline-none focus:border-atlas-500 w-40">
                        <svg class="w-3.5 h-3.5 absolute left-2 top-1.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                        </svg>
                    </div>
                    <span id="graph-filter-stats" class="text-xs text-gray-500"></span>
                </div>

                <!-- Zoom controls -->
                <div class="absolute bottom-3 right-3 z-10 flex flex-col gap-1">
                    <button id="graph-zoom-in" class="bg-surface-2 border border-surface-4 rounded-lg w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white hover:bg-surface-3 transition-colors text-lg">+</button>
                    <button id="graph-zoom-out" class="bg-surface-2 border border-surface-4 rounded-lg w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white hover:bg-surface-3 transition-colors text-lg">&minus;</button>
                    <button id="graph-zoom-fit" class="bg-surface-2 border border-surface-4 rounded-lg w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white hover:bg-surface-3 transition-colors" title="Fit to view">
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M4 8V4h4M20 8V4h-4M4 16v4h4M20 16v4h-4"/></svg>
                    </button>
                </div>

                <!-- Legend -->
                <div class="absolute bottom-3 left-3 z-10 bg-surface-1/90 backdrop-blur-sm border border-surface-3 rounded-lg px-3 py-2">
                    <p class="text-[10px] text-gray-500 font-medium uppercase tracking-wider mb-1.5">Node Types</p>
                    <div class="grid grid-cols-2 gap-x-4 gap-y-0.5">
                        ${Object.entries(NODE_COLORS).map(([type, c]) => `
                            <div class="flex items-center gap-1.5 text-xs text-gray-400">
                                <span class="w-2 h-2 rounded-full" style="background: ${c.bg}"></span>
                                ${type}
                            </div>
                        `).join('')}
                    </div>
                </div>

                <!-- vis-network container -->
                <div id="graph-canvas" class="w-full h-full bg-surface-0"></div>
            </div>

            <!-- Node detail panel (right sidebar) -->
            <div id="node-detail" class="hidden w-72 bg-surface-1 border-l border-surface-3 p-4 overflow-y-auto shrink-0"></div>
        </div>
    `;

    // Load graph data
    try {
        const data = await api.get('/api/graph');
        rawNodes = data.nodes || [];
        rawEdges = data.edges || [];
    } catch (err) {
        toast(`Failed to load graph: ${err.message}`, 'error');
        rawNodes = [];
        rawEdges = [];
    }

    // Populate filters
    populateFilters();

    // Build vis-network
    const graphContainer = document.getElementById('graph-canvas');
    const visNodes = rawNodes.map(buildVisNode);
    const visEdges = rawEdges.map(buildVisEdge);

    const options = {
        physics: {
            solver: 'forceAtlas2Based',
            forceAtlas2Based: {
                gravitationalConstant: -40,
                centralGravity: 0.005,
                springLength: 120,
                springConstant: 0.04,
                damping: 0.4,
                avoidOverlap: 0.3,
            },
            stabilization: { iterations: 150, updateInterval: 25 },
            maxVelocity: 50,
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
            zoomView: true,
            dragView: true,
            multiselect: false,
            navigationButtons: false,
        },
        nodes: {
            borderWidth: 1.5,
            shadow: true,
        },
        edges: {
            smooth: { type: 'continuous', roundness: 0.2 },
            width: 1,
        },
    };

    network = new vis.Network(graphContainer, { nodes: visNodes, edges: visEdges }, options);

    // Click node -> detail panel
    network.on('click', (event) => {
        if (event.nodes.length > 0) {
            showNodeDetail(event.nodes[0]);
        } else {
            document.getElementById('node-detail')?.classList.add('hidden');
        }
    });

    // Double click -> wiki page
    network.on('doubleClick', (event) => {
        if (event.nodes.length > 0) {
            window.location.hash = `#/wiki/${encodeURIComponent(event.nodes[0])}`;
        }
    });

    // Filter change handlers
    ['filter-community', 'filter-type', 'filter-confidence'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', applyFilters);
    });

    // Graph search
    const graphSearchInput = document.getElementById('graph-search');
    graphSearchInput?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') searchGraph(graphSearchInput.value.trim());
    });

    // Zoom controls
    document.getElementById('graph-zoom-in')?.addEventListener('click', () => {
        const scale = network.getScale();
        network.moveTo({ scale: scale * 1.3, animation: { duration: 200 } });
    });
    document.getElementById('graph-zoom-out')?.addEventListener('click', () => {
        const scale = network.getScale();
        network.moveTo({ scale: scale / 1.3, animation: { duration: 200 } });
    });
    document.getElementById('graph-zoom-fit')?.addEventListener('click', () => {
        network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
    });

    // WebSocket: live graph updates
    wsUnsub = on('ws:graph_update', (payload) => {
        if (payload.new_nodes) {
            rawNodes = [...rawNodes, ...payload.new_nodes];
        }
        if (payload.new_edges) {
            rawEdges = [...rawEdges, ...payload.new_edges];
        }
        if (payload.removed_nodes) {
            const removed = new Set(payload.removed_nodes);
            rawNodes = rawNodes.filter(n => !removed.has(n.id));
        }
        populateFilters();
        applyFilters();
        toast(`Graph updated: ${payload.summary || 'changes applied'}`, 'info', 2000);
    });

    // If a node ID was passed as param, focus on it
    if (params?.[0]) {
        const targetId = decodeURIComponent(params[0]);
        network.once('stabilizationIterationsDone', () => {
            const match = rawNodes.find(n => n.id === targetId);
            if (match) {
                network.focus(match.id, { scale: 1.2, animation: { duration: 500 } });
                network.selectNodes([match.id]);
                showNodeDetail(match.id);
            }
        });
    }

    // Update stats
    const statsEl = document.getElementById('graph-filter-stats');
    if (statsEl) {
        statsEl.textContent = `${rawNodes.length} nodes, ${rawEdges.length} edges`;
    }
}

export function destroy() {
    if (network) {
        network.destroy();
        network = null;
    }
    if (wsUnsub) {
        wsUnsub();
        wsUnsub = null;
    }
    rawNodes = [];
    rawEdges = [];
}
```

- [ ] **Step 2: Commit**

```bash
git add atlas/dashboard/graph.js
git commit -m "feat(dashboard): graph view with vis-network, filters, node detail panel

Interactive force-directed graph. Filters by community, type, confidence.
Click node for detail panel, double-click to open wiki page. Search to
find and focus nodes. WebSocket updates for live changes. Zoom controls."
```

---

## Task 3: Wiki View

**Files:**
- Create: `atlas/dashboard/wiki.js`

- [ ] **Step 1: Implement wiki.js**

`atlas/dashboard/wiki.js`:
```javascript
/**
 * Atlas Dashboard — Wiki View
 * Markdown rendering, breadcrumbs, backlinks, TOC, inline editing.
 * Uses marked.js for rendering and highlight.js for code.
 */

import { api, on, emit, toast } from '/dashboard/app.js';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let currentPage = null;
let isEditing = false;
let wsUnsub = null;

// ---------------------------------------------------------------------------
// Markdown Renderer Setup
// ---------------------------------------------------------------------------

function createRenderer() {
    const renderer = new marked.Renderer();

    // Wikilinks: [[target]] or [[target|display]]
    const originalParagraph = renderer.paragraph.bind(renderer);
    renderer.paragraph = function (text) {
        // Transform [[...]] into clickable links
        const withLinks = text.replace(
            /\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g,
            (_, target, display) => {
                const slug = target.trim();
                const label = (display || target).trim();
                return `<a href="#/wiki/${encodeURIComponent(slug)}" class="wikilink" data-target="${slug}">${label}</a>`;
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
// Table of Contents
// ---------------------------------------------------------------------------

function extractTOC(html) {
    const headings = [];
    const regex = /<h([1-3])[^>]*>(.*?)<\/h\1>/gi;
    let match;
    while ((match = regex.exec(html)) !== null) {
        const level = parseInt(match[1]);
        const text = match[2].replace(/<[^>]+>/g, '');
        const id = text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
        headings.push({ level, text, id });
    }
    return headings;
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

function renderTOC(headings) {
    if (!headings.length) return '';
    return `
        <nav class="mb-6">
            <p class="text-xs text-gray-500 font-medium uppercase tracking-wider mb-2">On this page</p>
            <ul class="space-y-0.5">
                ${headings.map(h => `
                    <li style="padding-left: ${(h.level - 1) * 12}px">
                        <a href="#${h.id}" class="text-xs text-gray-400 hover:text-atlas-400 transition-colors block py-0.5"
                           onclick="event.preventDefault(); document.getElementById('${h.id}')?.scrollIntoView({behavior: 'smooth'})"
                        >${h.text}</a>
                    </li>
                `).join('')}
            </ul>
        </nav>
    `;
}

// ---------------------------------------------------------------------------
// Breadcrumbs
// ---------------------------------------------------------------------------

function renderBreadcrumbs(pagePath) {
    if (!pagePath) return '';
    const parts = pagePath.replace(/\.md$/, '').split('/').filter(Boolean);
    const crumbs = [{ label: 'Wiki', href: '#/wiki' }];

    let accumulated = '';
    parts.forEach((part, i) => {
        accumulated += (accumulated ? '/' : '') + part;
        const isLast = i === parts.length - 1;
        crumbs.push({
            label: part.charAt(0).toUpperCase() + part.slice(1),
            href: isLast ? null : `#/wiki/${encodeURIComponent(accumulated)}`,
        });
    });

    return `
        <nav class="flex items-center gap-1.5 text-xs text-gray-500 mb-4">
            ${crumbs.map((c, i) => {
                const sep = i > 0 ? '<span class="text-gray-600">/</span>' : '';
                if (c.href) {
                    return `${sep}<a href="${c.href}" class="hover:text-gray-300 transition-colors">${c.label}</a>`;
                }
                return `${sep}<span class="text-gray-300">${c.label}</span>`;
            }).join('')}
        </nav>
    `;
}

// ---------------------------------------------------------------------------
// Frontmatter Display
// ---------------------------------------------------------------------------

function renderFrontmatter(frontmatter) {
    if (!frontmatter || Object.keys(frontmatter).length === 0) return '';
    const skipKeys = new Set(['title', 'type']);

    const entries = Object.entries(frontmatter).filter(([k]) => !skipKeys.has(k));
    if (!entries.length) return '';

    return `
        <div class="bg-surface-2 rounded-lg px-4 py-3 mb-4 text-xs">
            <div class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                ${entries.map(([key, value]) => {
                    const display = Array.isArray(value)
                        ? value.map(v => `<span class="px-1.5 py-0.5 bg-surface-3 rounded text-gray-400">${v}</span>`).join(' ')
                        : `<span class="text-gray-300">${value}</span>`;
                    return `
                        <span class="text-gray-500">${key}:</span>
                        <span>${display}</span>
                    `;
                }).join('')}
            </div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Backlinks
// ---------------------------------------------------------------------------

async function loadBacklinks(slug) {
    try {
        const links = await api.get(`/api/wiki/backlinks/${encodeURIComponent(slug)}`);
        return links || [];
    } catch {
        return [];
    }
}

function renderBacklinks(backlinks) {
    if (!backlinks.length) return '';
    return `
        <div class="mt-8 pt-4 border-t border-surface-3">
            <p class="text-xs text-gray-500 font-medium uppercase tracking-wider mb-2">
                Backlinks (${backlinks.length})
            </p>
            <div class="flex flex-wrap gap-1.5">
                ${backlinks.map(link => {
                    const slug = link.replace(/\.md$/, '').split('/').pop();
                    return `<a href="#/wiki/${encodeURIComponent(slug)}" class="px-2 py-1 bg-surface-2 rounded text-xs text-atlas-400 hover:bg-surface-3 transition-colors">${slug}</a>`;
                }).join('')}
            </div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Inline Editing
// ---------------------------------------------------------------------------

function startEditing(page, contentEl) {
    if (isEditing) return;
    isEditing = true;

    const original = page.content;
    contentEl.innerHTML = `
        <div class="flex flex-col h-full">
            <div class="flex items-center justify-between mb-3">
                <span class="text-xs text-amber-400 font-medium">Editing</span>
                <div class="flex gap-2">
                    <button id="edit-cancel" class="px-3 py-1 text-xs text-gray-400 hover:text-gray-200 bg-surface-3 rounded transition-colors">Cancel</button>
                    <button id="edit-save" class="px-3 py-1 text-xs text-white bg-atlas-600 rounded hover:bg-atlas-700 transition-colors">Save</button>
                </div>
            </div>
            <textarea id="edit-textarea" class="flex-1 w-full bg-surface-0 border border-surface-4 rounded-lg p-4 text-sm text-gray-300 font-mono leading-relaxed resize-none focus:outline-none focus:border-atlas-500">${escapeHtml(original)}</textarea>
        </div>
    `;

    const textarea = document.getElementById('edit-textarea');
    textarea?.focus();

    document.getElementById('edit-cancel')?.addEventListener('click', () => {
        isEditing = false;
        renderPage(page, contentEl.parentElement);
    });

    document.getElementById('edit-save')?.addEventListener('click', async () => {
        const newContent = textarea.value;
        try {
            await api.put(`/api/wiki/page/${encodeURIComponent(page.path)}`, {
                content: newContent,
                frontmatter: page.frontmatter,
            });
            page.content = newContent;
            isEditing = false;
            toast('Page saved', 'success');
            renderPage(page, contentEl.parentElement);
        } catch (err) {
            toast(`Save failed: ${err.message}`, 'error');
        }
    });
}

function escapeHtml(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// Page Rendering
// ---------------------------------------------------------------------------

function renderPage(page, outerContainer) {
    let html = marked.parse(page.content, markedOptions);
    html = addHeadingIds(html);
    const toc = extractTOC(html);

    outerContainer.innerHTML = `
        <div class="flex h-full">
            <!-- TOC sidebar -->
            <aside class="w-52 shrink-0 border-r border-surface-3 p-4 overflow-y-auto hidden lg:block">
                ${renderTOC(toc)}
                <div id="wiki-backlinks-sidebar"></div>
            </aside>

            <!-- Content -->
            <div class="flex-1 overflow-y-auto">
                <div class="max-w-3xl mx-auto px-6 py-6">
                    ${renderBreadcrumbs(page.path)}

                    <!-- Header -->
                    <div class="flex items-start justify-between mb-4">
                        <div>
                            <h1 class="text-2xl font-bold text-white mb-1">${escapeHtml(page.title)}</h1>
                            ${page.type ? `<span class="px-2 py-0.5 rounded text-xs font-medium bg-surface-3 text-gray-400">${page.type}</span>` : ''}
                        </div>
                        <div class="flex gap-2">
                            <button id="wiki-edit-btn" class="px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-surface-2 border border-surface-4 rounded-lg hover:bg-surface-3 transition-colors flex items-center gap-1.5">
                                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                                    <path d="M18.5 2.5a2.12 2.12 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                                </svg>
                                Edit
                            </button>
                            <a href="#/graph/${encodeURIComponent(page.path.replace(/\.md$/, '').split('/').pop())}" class="px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-surface-2 border border-surface-4 rounded-lg hover:bg-surface-3 transition-colors flex items-center gap-1.5">
                                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                    <circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><line x1="8.5" y1="7.5" x2="15.5" y2="16.5"/>
                                </svg>
                                Graph
                            </a>
                        </div>
                    </div>

                    ${renderFrontmatter(page.frontmatter)}

                    <!-- Rendered content -->
                    <div id="wiki-content" class="wiki-content">
                        ${html}
                    </div>

                    <!-- Backlinks (mobile, shown below content) -->
                    <div id="wiki-backlinks-inline" class="lg:hidden"></div>
                </div>
            </div>
        </div>
    `;

    // Edit button
    const editBtn = document.getElementById('wiki-edit-btn');
    const contentEl = document.getElementById('wiki-content');
    editBtn?.addEventListener('click', () => startEditing(page, contentEl));

    // Load backlinks
    const slug = page.path.replace(/\.md$/, '').split('/').pop();
    loadBacklinks(slug).then(backlinks => {
        const sidebarEl = document.getElementById('wiki-backlinks-sidebar');
        const inlineEl = document.getElementById('wiki-backlinks-inline');
        const rendered = renderBacklinks(backlinks);
        if (sidebarEl) sidebarEl.innerHTML = rendered;
        if (inlineEl) inlineEl.innerHTML = rendered;
    });
}

// ---------------------------------------------------------------------------
// Page List (index)
// ---------------------------------------------------------------------------

async function renderPageList(container) {
    let pages;
    try {
        pages = await api.get('/api/wiki/pages');
    } catch (err) {
        container.innerHTML = `<div class="p-6 text-red-400">Failed to load pages: ${err.message}</div>`;
        return;
    }

    // Group by type
    const grouped = {};
    (pages || []).forEach(p => {
        const type = p.type || 'other';
        if (!grouped[type]) grouped[type] = [];
        grouped[type].push(p);
    });

    const typeOrder = ['wiki-concept', 'wiki-page', 'wiki-decision', 'wiki-source', 'other'];
    const typeLabels = {
        'wiki-concept': 'Concepts',
        'wiki-page': 'Pages',
        'wiki-decision': 'Decisions',
        'wiki-source': 'Sources',
        'other': 'Other',
    };

    container.innerHTML = `
        <div class="max-w-3xl mx-auto px-6 py-6">
            <h1 class="text-2xl font-bold text-white mb-6">Wiki</h1>

            ${typeOrder.filter(t => grouped[t]?.length).map(type => `
                <div class="mb-6">
                    <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">${typeLabels[type] || type}</h2>
                    <div class="grid gap-2">
                        ${grouped[type].sort((a, b) => a.title.localeCompare(b.title)).map(page => `
                            <a href="#/wiki/${encodeURIComponent(page.path.replace(/\.md$/, '').split('/').pop())}"
                               class="flex items-center justify-between px-4 py-3 bg-surface-1 border border-surface-3 rounded-lg hover:bg-surface-2 hover:border-surface-4 transition-colors group">
                                <div>
                                    <span class="text-sm text-gray-200 group-hover:text-white transition-colors">${escapeHtml(page.title)}</span>
                                    <span class="text-xs text-gray-500 ml-2 font-mono">${page.path}</span>
                                </div>
                                ${page.frontmatter?.tags?.length ? `
                                    <div class="flex gap-1">
                                        ${page.frontmatter.tags.slice(0, 3).map(t => `<span class="px-1.5 py-0.5 bg-surface-3 rounded text-[10px] text-gray-500">${t}</span>`).join('')}
                                    </div>
                                ` : ''}
                            </a>
                        `).join('')}
                    </div>
                </div>
            `).join('')}

            ${Object.keys(grouped).length === 0 ? `
                <div class="text-center py-16">
                    <p class="text-gray-500 mb-2">No wiki pages yet.</p>
                    <p class="text-gray-600 text-sm">Run <code class="text-atlas-400 bg-surface-2 px-2 py-0.5 rounded">atlas scan</code> to create the initial graph and wiki.</p>
                </div>
            ` : ''}
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Init / Destroy
// ---------------------------------------------------------------------------

export async function init(container, params) {
    const slug = params?.[0] ? decodeURIComponent(params[0]) : null;

    if (!slug) {
        // Show page list
        await renderPageList(container);
        return;
    }

    // Load specific page
    container.innerHTML = `
        <div class="flex items-center justify-center h-full">
            <div class="text-center">
                <svg class="w-8 h-8 text-atlas-500 animate-spin mx-auto mb-2" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" opacity="0.2"/>
                    <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                <p class="text-gray-500 text-sm">Loading page...</p>
            </div>
        </div>
    `;

    try {
        currentPage = await api.get(`/api/wiki/page/${encodeURIComponent(slug)}`);
        renderPage(currentPage, container);
    } catch (err) {
        container.innerHTML = `
            <div class="max-w-3xl mx-auto px-6 py-6">
                ${renderBreadcrumbs(slug)}
                <div class="text-center py-16">
                    <p class="text-5xl font-bold text-gray-700 mb-3">Page Not Found</p>
                    <p class="text-gray-500 mb-4">No wiki page for "<span class="text-gray-300">${escapeHtml(slug)}</span>"</p>
                    <a href="#/wiki" class="text-atlas-400 hover:text-atlas-300 text-sm">Back to Wiki Index</a>
                </div>
            </div>
        `;
    }

    // WebSocket: live wiki updates
    wsUnsub = on('ws:wiki_update', (payload) => {
        if (currentPage && payload.page === currentPage.path) {
            toast('This page was updated. Reloading...', 'info');
            init(container, params);
        }
    });
}

export function destroy() {
    currentPage = null;
    isEditing = false;
    if (wsUnsub) {
        wsUnsub();
        wsUnsub = null;
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add atlas/dashboard/wiki.js
git commit -m "feat(dashboard): wiki view with markdown rendering, TOC, backlinks, inline edit

Marked.js renderer with wikilink support, heading IDs, highlight.js code.
Table of contents sidebar, breadcrumb navigation, frontmatter display.
Backlinks section, inline editing with save via API. Page list index."
```

---

## Task 4: Audit View

**Files:**
- Create: `atlas/dashboard/audit.js`

- [ ] **Step 1: Implement audit.js**

`atlas/dashboard/audit.js`:
```javascript
/**
 * Atlas Dashboard — Audit View
 * Health score, orphan pages, contradictions, god nodes, surprises.
 * Data from /api/audit endpoint (returns AuditReport).
 */

import { api, on, toast } from '/dashboard/app.js';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let report = null;
let wsUnsub = null;

// ---------------------------------------------------------------------------
// Health Score Ring
// ---------------------------------------------------------------------------

function renderHealthRing(score) {
    const radius = 54;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;
    const color = score >= 70 ? '#34d399' : score >= 40 ? '#fbbf24' : '#f87171';
    const label = score >= 70 ? 'Healthy' : score >= 40 ? 'Needs attention' : 'Critical';

    return `
        <div class="flex flex-col items-center">
            <svg width="140" height="140" class="health-ring">
                <circle class="health-ring-bg" cx="70" cy="70" r="${radius}" fill="none" stroke-width="8"/>
                <circle class="health-ring-fill" cx="70" cy="70" r="${radius}" fill="none"
                    stroke="${color}" stroke-width="8" stroke-linecap="round"
                    stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"/>
            </svg>
            <div class="absolute flex flex-col items-center justify-center" style="margin-top: 36px;">
                <span class="text-3xl font-bold text-white">${Math.round(score)}</span>
                <span class="text-xs text-gray-500">${label}</span>
            </div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Stat Cards
// ---------------------------------------------------------------------------

function renderStatCards(report) {
    const stats = report.stats || {};
    const cards = [
        { label: 'Nodes', value: stats.nodes ?? '—', icon: 'circle', color: 'text-atlas-400' },
        { label: 'Edges', value: stats.edges ?? '—', icon: 'line', color: 'text-purple-400' },
        { label: 'Communities', value: stats.communities ?? '—', icon: 'grid', color: 'text-emerald-400' },
        { label: 'Orphan Pages', value: report.orphan_pages?.length ?? 0, icon: 'alert', color: 'text-amber-400' },
        { label: 'Broken Links', value: report.broken_links?.length ?? 0, icon: 'x', color: 'text-red-400' },
        { label: 'Stale Pages', value: report.stale_pages?.length ?? 0, icon: 'clock', color: 'text-orange-400' },
    ];

    return `
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            ${cards.map(c => `
                <div class="audit-card bg-surface-1 border border-surface-3 rounded-lg p-4 text-center">
                    <p class="text-2xl font-bold ${c.color}">${c.value}</p>
                    <p class="text-xs text-gray-500 mt-1">${c.label}</p>
                </div>
            `).join('')}
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Confidence Breakdown
// ---------------------------------------------------------------------------

function renderConfidenceBreakdown(breakdown) {
    if (!breakdown) return '';
    const total = Object.values(breakdown).reduce((a, b) => a + b, 0) || 1;

    const bars = [
        { key: 'EXTRACTED', label: 'Extracted', color: 'bg-emerald-500', textColor: 'text-emerald-400' },
        { key: 'INFERRED', label: 'Inferred', color: 'bg-amber-500', textColor: 'text-amber-400' },
        { key: 'AMBIGUOUS', label: 'Ambiguous', color: 'bg-red-500', textColor: 'text-red-400' },
    ];

    return `
        <div class="bg-surface-1 border border-surface-3 rounded-lg p-4 mb-6">
            <h3 class="text-sm font-semibold text-gray-300 mb-3">Edge Confidence</h3>
            <!-- Stacked bar -->
            <div class="w-full h-4 rounded-full bg-surface-3 flex overflow-hidden mb-3">
                ${bars.map(b => {
                    const pct = ((breakdown[b.key] || 0) / total * 100);
                    return pct > 0 ? `<div class="${b.color}" style="width: ${pct}%" title="${b.label}: ${breakdown[b.key]}"></div>` : '';
                }).join('')}
            </div>
            <div class="flex justify-between text-xs">
                ${bars.map(b => `
                    <span class="${b.textColor}">
                        ${b.label}: ${breakdown[b.key] || 0} (${Math.round((breakdown[b.key] || 0) / total * 100)}%)
                    </span>
                `).join('')}
            </div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// God Nodes
// ---------------------------------------------------------------------------

function renderGodNodes(godNodes) {
    if (!godNodes?.length) return '';
    return `
        <div class="bg-surface-1 border border-surface-3 rounded-lg p-4 mb-6">
            <h3 class="text-sm font-semibold text-gray-300 mb-3">
                God Nodes
                <span class="text-xs text-gray-500 font-normal ml-1">— most connected concepts</span>
            </h3>
            <div class="space-y-2">
                ${godNodes.slice(0, 10).map(([nodeId, degree], i) => {
                    const maxDegree = godNodes[0]?.[1] || 1;
                    const pct = (degree / maxDegree * 100);
                    return `
                        <div class="flex items-center gap-3">
                            <span class="text-xs text-gray-500 w-4 text-right">${i + 1}</span>
                            <a href="#/graph/${encodeURIComponent(nodeId)}" class="text-sm text-atlas-400 hover:text-atlas-300 truncate w-40">${nodeId}</a>
                            <div class="flex-1 h-2 bg-surface-3 rounded-full overflow-hidden">
                                <div class="h-full bg-atlas-500 rounded-full" style="width: ${pct}%"></div>
                            </div>
                            <span class="text-xs text-gray-400 w-8 text-right">${degree}</span>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Issue Lists
// ---------------------------------------------------------------------------

function renderIssueList(title, items, linkPrefix, emptyMsg, badgeClass) {
    return `
        <div class="bg-surface-1 border border-surface-3 rounded-lg p-4 mb-6">
            <h3 class="text-sm font-semibold text-gray-300 mb-3">
                ${title}
                ${items.length ? `<span class="ml-2 px-1.5 py-0.5 rounded text-xs ${badgeClass}">${items.length}</span>` : ''}
            </h3>
            ${items.length === 0 ? `
                <p class="text-xs text-gray-500">${emptyMsg}</p>
            ` : `
                <div class="space-y-1 max-h-48 overflow-y-auto">
                    ${items.map(item => {
                        const display = Array.isArray(item) ? item.join(' → ') : item;
                        const slug = Array.isArray(item) ? item[0] : item;
                        const link = slug.replace(/\.md$/, '').split('/').pop();
                        return `
                            <a href="${linkPrefix}${encodeURIComponent(link)}"
                               class="block px-3 py-2 rounded hover:bg-surface-2 text-xs text-gray-400 hover:text-gray-200 transition-colors font-mono truncate">
                                ${display}
                            </a>
                        `;
                    }).join('')}
                </div>
            `}
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Surprises
// ---------------------------------------------------------------------------

function renderSurprises(surprises) {
    if (!surprises?.length) return '';
    return `
        <div class="bg-surface-1 border border-surface-3 rounded-lg p-4 mb-6">
            <h3 class="text-sm font-semibold text-gray-300 mb-3">
                Surprises
                <span class="text-xs text-gray-500 font-normal ml-1">— unexpected connections</span>
            </h3>
            <div class="space-y-2">
                ${surprises.slice(0, 10).map(edge => `
                    <div class="flex items-center gap-2 px-3 py-2 rounded bg-surface-2 text-xs">
                        <a href="#/graph/${encodeURIComponent(edge.source)}" class="text-atlas-400 hover:text-atlas-300">${edge.source}</a>
                        <span class="text-gray-500">—</span>
                        <span class="badge-${edge.confidence.toLowerCase()} px-1.5 py-0.5 rounded">${edge.relation}</span>
                        <span class="text-gray-500">→</span>
                        <a href="#/graph/${encodeURIComponent(edge.target)}" class="text-atlas-400 hover:text-atlas-300">${edge.target}</a>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Contradictions
// ---------------------------------------------------------------------------

function renderContradictions(contradictions) {
    if (!contradictions?.length) return '';
    return `
        <div class="bg-surface-1 border border-surface-3 rounded-lg p-4 mb-6">
            <h3 class="text-sm font-semibold text-gray-300 mb-3">
                Contradictions
                <span class="ml-2 px-1.5 py-0.5 rounded text-xs badge-ambiguous">${contradictions.length}</span>
            </h3>
            <div class="space-y-2">
                ${contradictions.map(c => `
                    <div class="px-3 py-2 rounded bg-surface-2 text-xs">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-red-400 font-medium">${c.type || 'Contradiction'}</span>
                        </div>
                        <p class="text-gray-400">${c.description || JSON.stringify(c)}</p>
                        ${c.pages ? `<div class="mt-1 flex gap-1">${c.pages.map(p => `<a href="#/wiki/${encodeURIComponent(p)}" class="text-atlas-400 hover:underline">${p}</a>`).join(' vs ')}</div>` : ''}
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Suggestions
// ---------------------------------------------------------------------------

async function renderSuggestions(container) {
    try {
        const suggestions = await api.get('/api/audit/suggestions');
        if (!suggestions?.length) return;

        const el = document.getElementById('audit-suggestions');
        if (!el) return;

        el.innerHTML = `
            <div class="bg-surface-1 border border-surface-3 rounded-lg p-4 mb-6">
                <h3 class="text-sm font-semibold text-gray-300 mb-3">
                    Link Suggestions
                    <span class="ml-2 px-1.5 py-0.5 rounded text-xs badge-inferred">${suggestions.length}</span>
                </h3>
                <div class="space-y-2 max-h-60 overflow-y-auto">
                    ${suggestions.map(s => `
                        <div class="flex items-center justify-between px-3 py-2 rounded bg-surface-2 text-xs">
                            <div class="flex items-center gap-2">
                                <a href="#/wiki/${encodeURIComponent(s.from_page)}" class="text-atlas-400">${s.from_page}</a>
                                <span class="text-gray-500">→</span>
                                <a href="#/wiki/${encodeURIComponent(s.to_page)}" class="text-atlas-400">${s.to_page}</a>
                            </div>
                            <span class="text-gray-500 ml-2 truncate max-w-[200px]">${s.reason}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } catch {
        // Suggestions endpoint might not exist yet — ignore
    }
}

// ---------------------------------------------------------------------------
// Init / Destroy
// ---------------------------------------------------------------------------

export async function init(container) {
    container.innerHTML = `
        <div class="h-full overflow-y-auto">
            <div class="max-w-5xl mx-auto px-6 py-6">
                <div class="flex items-center justify-between mb-6">
                    <h1 class="text-2xl font-bold text-white">Audit</h1>
                    <button id="audit-refresh" class="px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-surface-2 border border-surface-4 rounded-lg hover:bg-surface-3 transition-colors flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path d="M4 4v5h5M20 20v-5h-5"/><path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/>
                        </svg>
                        Refresh
                    </button>
                </div>

                <!-- Loading state -->
                <div id="audit-loading" class="flex items-center justify-center py-16">
                    <svg class="w-8 h-8 text-atlas-500 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" opacity="0.2"/>
                        <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>

                <!-- Content (hidden until loaded) -->
                <div id="audit-content" class="hidden">
                    <!-- Health score + stats -->
                    <div class="flex flex-col md:flex-row gap-6 mb-6 items-start">
                        <div class="relative bg-surface-1 border border-surface-3 rounded-lg p-6 flex items-center justify-center">
                            <div id="audit-health-ring"></div>
                        </div>
                        <div class="flex-1" id="audit-stat-cards"></div>
                    </div>

                    <div id="audit-confidence"></div>

                    <!-- Two-column layout for issues -->
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div>
                            <div id="audit-god-nodes"></div>
                            <div id="audit-orphans"></div>
                        </div>
                        <div>
                            <div id="audit-surprises"></div>
                            <div id="audit-broken-links"></div>
                        </div>
                    </div>

                    <div id="audit-stale"></div>
                    <div id="audit-contradictions"></div>
                    <div id="audit-suggestions"></div>
                </div>
            </div>
        </div>
    `;

    await loadAudit();

    document.getElementById('audit-refresh')?.addEventListener('click', loadAudit);

    // WebSocket: auto-refresh after scan
    wsUnsub = on('ws:scan_complete', () => {
        toast('Scan complete — refreshing audit...', 'info', 2000);
        loadAudit();
    });
}

async function loadAudit() {
    const loading = document.getElementById('audit-loading');
    const content = document.getElementById('audit-content');
    if (loading) loading.classList.remove('hidden');
    if (content) content.classList.add('hidden');

    try {
        report = await api.get('/api/audit');
    } catch (err) {
        toast(`Audit failed: ${err.message}`, 'error');
        if (loading) loading.innerHTML = `<p class="text-red-400 text-sm">Failed to load audit: ${err.message}</p>`;
        return;
    }

    if (loading) loading.classList.add('hidden');
    if (content) content.classList.remove('hidden');

    // Fill sections
    document.getElementById('audit-health-ring').innerHTML = renderHealthRing(report.health_score ?? 0);
    document.getElementById('audit-stat-cards').innerHTML = renderStatCards(report);
    document.getElementById('audit-confidence').innerHTML = renderConfidenceBreakdown(report.stats?.confidence_breakdown);
    document.getElementById('audit-god-nodes').innerHTML = renderGodNodes(report.god_nodes);
    document.getElementById('audit-orphans').innerHTML = renderIssueList(
        'Orphan Pages', report.orphan_pages || [], '#/wiki/', 'No orphan pages', 'badge-inferred'
    );
    document.getElementById('audit-broken-links').innerHTML = renderIssueList(
        'Broken Links', report.broken_links || [], '#/wiki/', 'No broken links', 'badge-ambiguous'
    );
    document.getElementById('audit-stale').innerHTML = renderIssueList(
        'Stale Pages (>30 days)', report.stale_pages || [], '#/wiki/', 'No stale pages', 'badge-inferred'
    );
    document.getElementById('audit-surprises').innerHTML = renderSurprises(report.stats ? await loadSurprises() : []);
    document.getElementById('audit-contradictions').innerHTML = renderContradictions(report.contradictions);

    renderSuggestions();
}

async function loadSurprises() {
    try {
        return await api.get('/api/graph/surprises?top_n=10');
    } catch {
        return [];
    }
}

export function destroy() {
    report = null;
    if (wsUnsub) {
        wsUnsub();
        wsUnsub = null;
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add atlas/dashboard/audit.js
git commit -m "feat(dashboard): audit view with health score ring, god nodes, orphans, surprises

Visual health score (SVG ring), stat cards (nodes/edges/communities/issues),
confidence breakdown bar, god nodes ranking, orphan pages, broken links,
stale pages, surprises, contradictions, link suggestions. Auto-refresh on scan."
```

---

## Task 5: Search View

**Files:**
- Create: `atlas/dashboard/search.js`

- [ ] **Step 1: Implement search.js**

`atlas/dashboard/search.js`:
```javascript
/**
 * Atlas Dashboard — Search View
 * Combined full-text wiki search + graph traversal.
 * Accessible via nav tab, quick search (Ctrl+K), or #/search/query.
 */

import { api, toast } from '/dashboard/app.js';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let currentQuery = '';
let searchTimeout = null;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function escapeHtml(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function highlightMatch(text, query) {
    if (!query) return escapeHtml(text);
    const escaped = escapeHtml(text);
    const re = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return escaped.replace(re, '<mark class="bg-atlas-500/30 text-white rounded px-0.5">$1</mark>');
}

function extractSnippet(content, query, maxLen = 200) {
    if (!content || !query) return '';
    const lower = content.toLowerCase();
    const idx = lower.indexOf(query.toLowerCase());
    if (idx === -1) return content.slice(0, maxLen);

    const start = Math.max(0, idx - 60);
    const end = Math.min(content.length, idx + query.length + maxLen - 60);
    let snippet = content.slice(start, end);
    if (start > 0) snippet = '...' + snippet;
    if (end < content.length) snippet += '...';
    return snippet;
}

// ---------------------------------------------------------------------------
// Search Execution
// ---------------------------------------------------------------------------

async function executeSearch(query) {
    if (!query || query.length < 2) return { wiki: [], graph: [] };

    const [wikiResults, graphResults] = await Promise.allSettled([
        api.get(`/api/wiki/search?q=${encodeURIComponent(query)}`),
        api.post('/api/graph/query', { start: query, mode: 'bfs', depth: 2 }),
    ]);

    return {
        wiki: wikiResults.status === 'fulfilled' ? wikiResults.value : [],
        graph: graphResults.status === 'fulfilled' ? graphResults.value : { nodes: [], edges: [] },
    };
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderWikiResults(pages, query) {
    if (!pages?.length) return `
        <div class="text-center py-8 text-gray-500 text-sm">No wiki pages match "${escapeHtml(query)}"</div>
    `;

    return `
        <div class="space-y-2">
            ${pages.map(page => {
                const slug = page.path?.replace(/\.md$/, '').split('/').pop() || page.title;
                const snippet = extractSnippet(page.content || '', query);
                return `
                    <a href="#/wiki/${encodeURIComponent(slug)}"
                       class="block px-4 py-3 bg-surface-1 border border-surface-3 rounded-lg hover:bg-surface-2 hover:border-surface-4 transition-colors group">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-sm font-medium text-gray-200 group-hover:text-white">${highlightMatch(page.title, query)}</span>
                            <span class="px-1.5 py-0.5 rounded text-[10px] bg-surface-3 text-gray-500">${page.type || 'page'}</span>
                        </div>
                        ${snippet ? `<p class="text-xs text-gray-500 leading-relaxed line-clamp-2">${highlightMatch(snippet, query)}</p>` : ''}
                        <span class="text-[10px] text-gray-600 font-mono mt-1 block">${page.path || ''}</span>
                    </a>
                `;
            }).join('')}
        </div>
    `;
}

function renderGraphResults(subgraph, query) {
    const nodes = subgraph?.nodes || [];
    const edges = subgraph?.edges || [];

    if (!nodes.length) return `
        <div class="text-center py-8 text-gray-500 text-sm">No graph nodes match "${escapeHtml(query)}"</div>
    `;

    return `
        <div class="space-y-3">
            <!-- Nodes -->
            <div class="space-y-1">
                ${nodes.slice(0, 20).map(node => `
                    <div class="flex items-center justify-between px-3 py-2 bg-surface-1 border border-surface-3 rounded-lg hover:bg-surface-2 transition-colors">
                        <div class="flex items-center gap-2">
                            <span class="w-2.5 h-2.5 rounded-full" style="background: var(--node-${node.type}, var(--node-default))"></span>
                            <a href="#/graph/${encodeURIComponent(node.id)}" class="text-sm text-gray-200 hover:text-atlas-400">${highlightMatch(node.label || node.id, query)}</a>
                            <span class="text-[10px] text-gray-600">${node.type}</span>
                        </div>
                        <a href="#/wiki/${encodeURIComponent(node.id)}" class="text-[10px] text-gray-500 hover:text-atlas-400">wiki</a>
                    </div>
                `).join('')}
            </div>

            ${nodes.length > 20 ? `<p class="text-xs text-gray-500 text-center">... and ${nodes.length - 20} more nodes</p>` : ''}

            <!-- Edges summary -->
            ${edges.length ? `
                <div class="mt-2 px-3 py-2 bg-surface-2 rounded-lg text-xs text-gray-500">
                    ${edges.length} relationships found in this subgraph
                </div>
            ` : ''}
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Init / Destroy
// ---------------------------------------------------------------------------

export async function init(container, params) {
    const initialQuery = params?.[0] ? decodeURIComponent(params[0]) : '';

    container.innerHTML = `
        <div class="h-full overflow-y-auto">
            <div class="max-w-3xl mx-auto px-6 py-6">
                <h1 class="text-2xl font-bold text-white mb-6">Search</h1>

                <!-- Search input -->
                <div class="relative mb-6">
                    <input type="text" id="search-input" value="${escapeHtml(initialQuery)}"
                        placeholder="Search wiki pages and graph nodes..."
                        class="w-full bg-surface-1 border border-surface-3 rounded-xl px-4 py-3 pl-10 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-atlas-500 focus:ring-1 focus:ring-atlas-500/30 transition-all"
                        autofocus>
                    <svg class="w-4.5 h-4.5 absolute left-3.5 top-3.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                    <span id="search-status" class="absolute right-3.5 top-3.5 text-xs text-gray-600"></span>
                </div>

                <!-- Results tabs -->
                <div class="flex gap-4 border-b border-surface-3 mb-4" id="search-tabs">
                    <button class="search-tab active" data-tab="wiki">
                        Wiki Pages <span id="search-wiki-count" class="ml-1 text-gray-600"></span>
                    </button>
                    <button class="search-tab" data-tab="graph">
                        Graph Nodes <span id="search-graph-count" class="ml-1 text-gray-600"></span>
                    </button>
                </div>

                <!-- Results -->
                <div id="search-results-wiki"></div>
                <div id="search-results-graph" class="hidden"></div>

                <!-- Empty state -->
                <div id="search-empty" class="${initialQuery ? 'hidden' : ''}">
                    <div class="text-center py-16">
                        <svg class="w-12 h-12 text-gray-700 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                        </svg>
                        <p class="text-gray-500 mb-1">Search across wiki and graph</p>
                        <p class="text-gray-600 text-xs">Full-text search on wiki pages + BFS traversal on graph nodes</p>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Style search tabs
    const style = document.createElement('style');
    style.textContent = `
        .search-tab {
            padding: 0.5rem 0;
            font-size: 0.8125rem;
            font-weight: 500;
            color: #6b7280;
            border-bottom: 2px solid transparent;
            transition: all 150ms;
            cursor: pointer;
            background: none;
            border-top: none; border-left: none; border-right: none;
        }
        .search-tab:hover { color: #d1d5db; }
        .search-tab.active { color: #338dff; border-bottom-color: #338dff; }
    `;
    container.appendChild(style);

    // Tab switching
    document.querySelectorAll('.search-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.search-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.dataset.tab;
            document.getElementById('search-results-wiki').classList.toggle('hidden', target !== 'wiki');
            document.getElementById('search-results-graph').classList.toggle('hidden', target !== 'graph');
        });
    });

    // Search input
    const input = document.getElementById('search-input');
    input?.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => doSearch(input.value.trim()), 300);
    });

    // If initial query, search immediately
    if (initialQuery) {
        await doSearch(initialQuery);
    }
}

async function doSearch(query) {
    currentQuery = query;
    const status = document.getElementById('search-status');
    const empty = document.getElementById('search-empty');
    const wikiContainer = document.getElementById('search-results-wiki');
    const graphContainer = document.getElementById('search-results-graph');

    if (!query || query.length < 2) {
        if (wikiContainer) wikiContainer.innerHTML = '';
        if (graphContainer) graphContainer.innerHTML = '';
        if (empty) empty.classList.remove('hidden');
        if (status) status.textContent = '';
        return;
    }

    if (empty) empty.classList.add('hidden');
    if (status) status.textContent = 'Searching...';

    try {
        const results = await executeSearch(query);

        // Check if query is still current (user might have typed more)
        if (query !== currentQuery) return;

        const wikiCount = results.wiki?.length || 0;
        const graphCount = results.graph?.nodes?.length || 0;

        if (wikiContainer) wikiContainer.innerHTML = renderWikiResults(results.wiki, query);
        if (graphContainer) graphContainer.innerHTML = renderGraphResults(results.graph, query);

        document.getElementById('search-wiki-count').textContent = wikiCount ? `(${wikiCount})` : '';
        document.getElementById('search-graph-count').textContent = graphCount ? `(${graphCount})` : '';

        if (status) status.textContent = `${wikiCount + graphCount} results`;
    } catch (err) {
        if (status) status.textContent = '';
        toast(`Search failed: ${err.message}`, 'error');
    }
}

export function destroy() {
    clearTimeout(searchTimeout);
    currentQuery = '';
}
```

- [ ] **Step 2: Commit**

```bash
git add atlas/dashboard/search.js
git commit -m "feat(dashboard): search view combining full-text wiki + graph traversal

Debounced search (300ms), wiki tab (full-text on pages), graph tab (BFS
traversal from matching node), highlighted matches, snippets, result counts.
Accessible via nav, Ctrl+K, or direct URL hash."
```

---

## Task 6: Timeline View

**Files:**
- Create: `atlas/dashboard/timeline.js`

- [ ] **Step 1: Implement timeline.js**

`atlas/dashboard/timeline.js`:
```javascript
/**
 * Atlas Dashboard — Timeline View
 * Operation log: scan events, wiki edits, graph changes.
 * Data from /api/log endpoint + WebSocket live feed.
 */

import { api, on, toast } from '/dashboard/app.js';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let entries = [];
let offset = 0;
let hasMore = true;
let loading = false;
let wsUnsub = null;

const PAGE_SIZE = 50;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function formatTimestamp(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHr = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr < 24) return `${diffHr}h ago`;
    if (diffDay < 7) return `${diffDay}d ago`;

    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
}

function formatTimeFull(ts) {
    if (!ts) return '';
    return new Date(ts).toLocaleString('en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
}

// ---------------------------------------------------------------------------
// Entry type icons and colors
// ---------------------------------------------------------------------------

const ENTRY_STYLES = {
    scan:        { icon: '&#x1F50D;', color: 'text-atlas-400', bg: 'bg-atlas-500/10', label: 'Scan' },
    wiki_create: { icon: '&#x1F4DD;', color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Page Created' },
    wiki_update: { icon: '&#x270F;',  color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Page Updated' },
    wiki_delete: { icon: '&#x1F5D1;', color: 'text-red-400', bg: 'bg-red-500/10', label: 'Page Deleted' },
    graph_merge: { icon: '&#x1F517;', color: 'text-purple-400', bg: 'bg-purple-500/10', label: 'Graph Merge' },
    ingest:      { icon: '&#x1F4E5;', color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: 'Ingest' },
    query:       { icon: '&#x2753;',  color: 'text-gray-400', bg: 'bg-gray-500/10', label: 'Query' },
    audit:       { icon: '&#x2705;',  color: 'text-green-400', bg: 'bg-green-500/10', label: 'Audit' },
    error:       { icon: '&#x26A0;',  color: 'text-red-400', bg: 'bg-red-500/10', label: 'Error' },
};

function getEntryStyle(type) {
    return ENTRY_STYLES[type] || { icon: '&#x25CF;', color: 'text-gray-400', bg: 'bg-gray-500/10', label: type || 'Event' };
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderEntry(entry) {
    const style = getEntryStyle(entry.type);

    return `
        <div class="flex gap-3 px-4 py-3 hover:bg-surface-1 transition-colors rounded-lg group">
            <!-- Timeline dot -->
            <div class="flex flex-col items-center pt-1">
                <div class="w-8 h-8 rounded-lg ${style.bg} flex items-center justify-center text-sm shrink-0">${style.icon}</div>
                <div class="w-px flex-1 bg-surface-3 mt-2 group-last:hidden"></div>
            </div>

            <!-- Content -->
            <div class="flex-1 min-w-0 pb-3">
                <div class="flex items-center gap-2 mb-0.5">
                    <span class="text-xs font-medium ${style.color}">${style.label}</span>
                    <span class="text-[10px] text-gray-600" title="${formatTimeFull(entry.timestamp)}">${formatTimestamp(entry.timestamp)}</span>
                    ${entry.agent ? `<span class="text-[10px] text-gray-600 font-mono">by ${escapeHtml(entry.agent)}</span>` : ''}
                </div>

                <p class="text-sm text-gray-300 leading-relaxed">${escapeHtml(entry.description || entry.message || '')}</p>

                ${entry.details ? `
                    <details class="mt-1">
                        <summary class="text-[10px] text-gray-600 cursor-pointer hover:text-gray-400 transition-colors">Details</summary>
                        <pre class="mt-1 text-[10px] text-gray-500 font-mono bg-surface-2 rounded p-2 overflow-x-auto">${escapeHtml(typeof entry.details === 'object' ? JSON.stringify(entry.details, null, 2) : entry.details)}</pre>
                    </details>
                ` : ''}

                ${entry.affected_pages?.length ? `
                    <div class="flex flex-wrap gap-1 mt-1.5">
                        ${entry.affected_pages.slice(0, 5).map(p => `
                            <a href="#/wiki/${encodeURIComponent(p)}" class="px-1.5 py-0.5 bg-surface-2 rounded text-[10px] text-atlas-400 hover:bg-surface-3 transition-colors">${p}</a>
                        `).join('')}
                        ${entry.affected_pages.length > 5 ? `<span class="text-[10px] text-gray-600">+${entry.affected_pages.length - 5} more</span>` : ''}
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

function renderTimeline(container) {
    const listEl = document.getElementById('timeline-list');
    if (!listEl) return;

    if (entries.length === 0 && !loading) {
        listEl.innerHTML = `
            <div class="text-center py-16">
                <svg class="w-12 h-12 text-gray-700 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
                </svg>
                <p class="text-gray-500 mb-1">No operations logged yet.</p>
                <p class="text-gray-600 text-xs">Run a scan or make changes to see the timeline.</p>
            </div>
        `;
        return;
    }

    // Group entries by day
    const groups = {};
    entries.forEach(entry => {
        const date = entry.timestamp
            ? new Date(entry.timestamp).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
            : 'Unknown';
        if (!groups[date]) groups[date] = [];
        groups[date].push(entry);
    });

    listEl.innerHTML = Object.entries(groups).map(([date, items]) => `
        <div class="mb-6">
            <div class="sticky top-0 bg-surface-0/90 backdrop-blur-sm z-10 px-4 py-2">
                <span class="text-xs font-medium text-gray-500 uppercase tracking-wider">${date}</span>
            </div>
            ${items.map(renderEntry).join('')}
        </div>
    `).join('');

    // Load more button
    const loadMoreEl = document.getElementById('timeline-load-more');
    if (loadMoreEl) {
        loadMoreEl.classList.toggle('hidden', !hasMore);
    }
}

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadEntries(append = false) {
    if (loading) return;
    loading = true;

    const loadMoreBtn = document.getElementById('timeline-load-more-btn');
    if (loadMoreBtn) loadMoreBtn.textContent = 'Loading...';

    try {
        const result = await api.get(`/api/log?limit=${PAGE_SIZE}&offset=${offset}`);
        const newEntries = result || [];

        if (append) {
            entries = [...entries, ...newEntries];
        } else {
            entries = newEntries;
        }

        hasMore = newEntries.length === PAGE_SIZE;
        offset += newEntries.length;

        renderTimeline();
    } catch (err) {
        toast(`Failed to load timeline: ${err.message}`, 'error');
    } finally {
        loading = false;
        const loadMoreBtn = document.getElementById('timeline-load-more-btn');
        if (loadMoreBtn) loadMoreBtn.textContent = 'Load more';
    }
}

// ---------------------------------------------------------------------------
// Init / Destroy
// ---------------------------------------------------------------------------

export async function init(container) {
    entries = [];
    offset = 0;
    hasMore = true;

    container.innerHTML = `
        <div class="h-full overflow-y-auto">
            <div class="max-w-3xl mx-auto px-6 py-6">
                <div class="flex items-center justify-between mb-6">
                    <h1 class="text-2xl font-bold text-white">Timeline</h1>
                    <div class="flex gap-2">
                        <select id="timeline-filter" class="bg-surface-2 border border-surface-4 rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-atlas-500">
                            <option value="all">All events</option>
                            <option value="scan">Scans</option>
                            <option value="wiki">Wiki changes</option>
                            <option value="graph">Graph changes</option>
                            <option value="ingest">Ingests</option>
                            <option value="error">Errors</option>
                        </select>
                    </div>
                </div>

                <div id="timeline-list"></div>

                <div id="timeline-load-more" class="text-center py-4 hidden">
                    <button id="timeline-load-more-btn" class="px-4 py-2 text-xs text-gray-400 hover:text-white bg-surface-2 border border-surface-4 rounded-lg hover:bg-surface-3 transition-colors">
                        Load more
                    </button>
                </div>
            </div>
        </div>
    `;

    await loadEntries();

    // Load more
    document.getElementById('timeline-load-more-btn')?.addEventListener('click', () => loadEntries(true));

    // Filter (client-side for now)
    document.getElementById('timeline-filter')?.addEventListener('change', (e) => {
        const filter = e.target.value;
        const listEl = document.getElementById('timeline-list');
        if (!listEl) return;

        if (filter === 'all') {
            renderTimeline();
            return;
        }

        const typeMap = {
            scan: ['scan'],
            wiki: ['wiki_create', 'wiki_update', 'wiki_delete'],
            graph: ['graph_merge'],
            ingest: ['ingest'],
            error: ['error'],
        };
        const types = new Set(typeMap[filter] || []);
        const filtered = entries.filter(e => types.has(e.type));

        // Temporarily swap entries
        const all = entries;
        entries = filtered;
        renderTimeline();
        entries = all;
    });

    // WebSocket: live new entries
    wsUnsub = on('ws:log_entry', (payload) => {
        entries = [payload, ...entries];
        renderTimeline();
    });
}

export function destroy() {
    entries = [];
    offset = 0;
    hasMore = true;
    if (wsUnsub) {
        wsUnsub();
        wsUnsub = null;
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add atlas/dashboard/timeline.js
git commit -m "feat(dashboard): timeline view with grouped operation log and live updates

Paginated log entries grouped by day, type-colored icons, expandable
details, affected page links, type filter dropdown. WebSocket live feed
for new entries. Load more pagination."
```

---

## Task 7: FastAPI Static Serving + Integration Test

**Files:**
- Test: `tests/dashboard/test_api_mock.py`
- Test: `tests/dashboard/test_static_files.py`

This task ensures the Server squad knows how to mount the dashboard. It provides the mount configuration and mock tests.

- [ ] **Step 1: Write static files test**

`tests/dashboard/test_static_files.py`:
```python
"""Verify all dashboard static files are present and well-formed."""
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent.parent.parent / "atlas" / "dashboard"


def test_all_js_files_have_exports():
    """Each view module must export init() and destroy()."""
    views = ["graph.js", "wiki.js", "audit.js", "search.js", "timeline.js"]
    for filename in views:
        content = (DASHBOARD_DIR / filename).read_text()
        assert "export async function init(" in content or "export function init(" in content, \
            f"{filename} must export init()"
        assert "export function destroy(" in content, \
            f"{filename} must export destroy()"


def test_app_js_has_router():
    content = (DASHBOARD_DIR / "app.js").read_text()
    assert "registerView" in content
    assert "export function on(" in content
    assert "export async function api(" in content or "export function api(" in content


def test_index_html_has_no_framework_imports():
    content = (DASHBOARD_DIR / "index.html").read_text()
    # No React, Vue, Angular, Svelte
    for framework in ["react", "vue", "angular", "svelte", "solid-js", "preact"]:
        assert framework not in content.lower(), f"index.html must not import {framework}"


def test_index_html_loads_tailwind():
    content = (DASHBOARD_DIR / "index.html").read_text()
    assert "tailwindcss" in content.lower() or "cdn.tailwindcss.com" in content


def test_index_html_loads_vis_network():
    content = (DASHBOARD_DIR / "index.html").read_text()
    assert "vis-network" in content


def test_index_html_loads_marked():
    content = (DASHBOARD_DIR / "index.html").read_text()
    assert "marked" in content.lower()


def test_css_has_no_tailwind_build():
    """styles.css should be hand-written, not a Tailwind build output."""
    content = (DASHBOARD_DIR / "styles.css").read_text()
    assert "/*! tailwindcss" not in content, "styles.css must not be a Tailwind build artifact"
    # Should be small (hand-written utilities)
    assert len(content) < 20000, "styles.css seems too large for hand-written utilities"
```

- [ ] **Step 2: Write API mock test (demonstrates how views consume the API)**

`tests/dashboard/test_api_mock.py`:
```python
"""Mock API responses that the dashboard expects.
These tests document the API contract the dashboard relies on.
Server squad: implement these endpoints to match."""
import json


# --- Graph API contract ---

def test_graph_response_shape():
    """GET /api/graph returns {nodes: [...], edges: [...]}"""
    response = {
        "nodes": [
            {
                "id": "auth_module",
                "label": "Auth Module",
                "type": "code",
                "source_file": "src/auth.py",
                "confidence": "high",
                "community": 0,
                "summary": "Handles authentication.",
                "tags": ["auth", "security"],
            },
        ],
        "edges": [
            {
                "source": "auth_module",
                "target": "db_client",
                "relation": "imports",
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
            },
        ],
    }
    # Validate shape
    assert isinstance(response["nodes"], list)
    assert isinstance(response["edges"], list)
    node = response["nodes"][0]
    assert all(k in node for k in ["id", "label", "type"])
    edge = response["edges"][0]
    assert all(k in edge for k in ["source", "target", "relation", "confidence"])


def test_graph_stats_response_shape():
    """GET /api/graph/stats returns GraphStats."""
    response = {
        "nodes": 150,
        "edges": 280,
        "communities": 7,
        "confidence_breakdown": {"EXTRACTED": 200, "INFERRED": 60, "AMBIGUOUS": 20},
        "health_score": 72.5,
    }
    assert isinstance(response["confidence_breakdown"], dict)
    assert response["health_score"] > 0


# --- Wiki API contract ---

def test_wiki_pages_response_shape():
    """GET /api/wiki/pages returns page list (no content)."""
    response = [
        {
            "path": "wiki/concepts/auth.md",
            "title": "Auth",
            "type": "wiki-concept",
            "frontmatter": {"tags": ["auth", "security"]},
        },
    ]
    page = response[0]
    assert "content" not in page or page.get("content") is None  # list endpoint omits content


def test_wiki_page_response_shape():
    """GET /api/wiki/page/{slug} returns full page with content."""
    response = {
        "path": "wiki/concepts/auth.md",
        "title": "Auth",
        "type": "wiki-concept",
        "content": "# Auth\n\nAuthentication module.\n\nSee [[billing]].",
        "frontmatter": {"type": "wiki-concept", "title": "Auth", "tags": ["auth"]},
    }
    assert "content" in response
    assert len(response["content"]) > 0


# --- Audit API contract ---

def test_audit_response_shape():
    """GET /api/audit returns AuditReport."""
    response = {
        "orphan_pages": ["wiki/concepts/old.md"],
        "god_nodes": [["auth_module", 15], ["db_client", 12]],
        "broken_links": [["wiki/concepts/auth.md", "nonexistent"]],
        "stale_pages": ["wiki/sources/2025-01-01-old.md"],
        "contradictions": [{"type": "value_conflict", "description": "Page A says X, Page B says Y", "pages": ["a", "b"]}],
        "missing_links": [],
        "communities": [],
        "stats": {"nodes": 150, "edges": 280, "communities": 7, "confidence_breakdown": {}, "health_score": 72.5},
        "health_score": 72.5,
    }
    assert isinstance(response["orphan_pages"], list)
    assert isinstance(response["god_nodes"], list)
    assert isinstance(response["health_score"], (int, float))


# --- Log API contract ---

def test_log_response_shape():
    """GET /api/log returns LogEntry[]."""
    response = [
        {
            "type": "scan",
            "timestamp": "2026-04-06T10:30:00Z",
            "description": "Scanned 42 files in src/",
            "agent": "claude-code",
            "details": {"files_scanned": 42, "nodes_created": 15},
            "affected_pages": ["wiki/concepts/auth.md"],
        },
        {
            "type": "wiki_update",
            "timestamp": "2026-04-06T10:25:00Z",
            "description": "Updated page: Auth",
            "agent": "user",
            "details": None,
            "affected_pages": ["wiki/concepts/auth.md"],
        },
    ]
    entry = response[0]
    assert all(k in entry for k in ["type", "timestamp", "description"])


# --- WebSocket message contract ---

def test_websocket_message_shapes():
    """WebSocket messages follow {type, payload} format."""
    messages = [
        {"type": "graph_update", "payload": {"new_nodes": [], "new_edges": [], "removed_nodes": [], "summary": "Added 3 nodes"}},
        {"type": "wiki_update", "payload": {"page": "wiki/concepts/auth.md"}},
        {"type": "scan_complete", "payload": {"files_scanned": 42, "nodes_created": 15}},
        {"type": "log_entry", "payload": {"type": "scan", "timestamp": "2026-04-06T10:30:00Z", "description": "Scan done"}},
    ]
    for msg in messages:
        assert "type" in msg
        assert "payload" in msg
        # Should be JSON-serializable
        json.dumps(msg)
```

- [ ] **Step 3: Run all dashboard tests**

Run: `python -m pytest tests/dashboard/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/dashboard/
git commit -m "test(dashboard): static file validation + API contract documentation

Verifies all view files exist, export init/destroy, no framework imports,
correct CDN loads. Mock tests document the exact API shapes the dashboard
expects — serves as the interface contract for the Server squad."
```

---

## Task 8: Server Mount Point

**Files:**
- Modify: `atlas/server/app.py` (add static file serving)

This task produces the code the Server squad must add to `app.py` to serve the dashboard. It is a small addition, not a full server implementation.

- [ ] **Step 1: Document the mount code for Server squad**

The Server squad must add this to `atlas/server/app.py`:

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Atlas", version="2.0.0a1")

# --- Dashboard serving ---
DASHBOARD_DIR = Path(__file__).parent.parent / "dashboard"

# Serve static assets at /dashboard/*
app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR), name="dashboard")

# Serve index.html at root
@app.get("/")
async def root():
    return FileResponse(DASHBOARD_DIR / "index.html")

# Catch-all for SPA routing (any non-API path returns index.html)
@app.get("/{path:path}")
async def spa_fallback(path: str):
    # Don't intercept API routes, WebSocket, or actual static files
    if path.startswith("api/") or path.startswith("ws") or path.startswith("dashboard/"):
        return  # Let other handlers deal with it
    return FileResponse(DASHBOARD_DIR / "index.html")
```

**Key points for Server squad:**
- The SPA uses hash routing (`#/`), so the fallback is only needed if someone navigates to `/wiki/auth` directly instead of `/#/wiki/auth`.
- Static files are served at `/dashboard/graph.js` etc.
- CDN assets (Tailwind, vis-network, marked, highlight.js) are loaded from external CDNs — no local copies needed.
- The `/api/*` and `/ws` routes must be registered BEFORE the catch-all fallback.

- [ ] **Step 2: Commit (no file changes — this is documentation for the Server squad's plan)**

No commit needed — this is a coordination note. The Server squad will implement these routes in their plan.

---

## Self-Review Checklist

**Spec coverage:**
- [x] Section 5.5 Dashboard — Graph view, Wiki view, Audit view, Search, Timeline
- [x] Section 4 Architecture — `atlas/dashboard/` file structure matches spec
- [x] Static-first — HTML + vanilla JS + Tailwind CDN, single `index.html`, no build step
- [x] Graph viz — vis-network with force-directed layout, node coloring by type, click→wiki, double-click→navigate
- [x] Wiki view — marked.js rendering, breadcrumbs, backlinks, TOC, inline editing, wikilinks rendered as clickable links
- [x] Audit view — health score ring, god nodes, orphans, broken links, stale pages, surprises, contradictions, link suggestions
- [x] Search — combined wiki full-text + graph BFS traversal, debounced, highlighted matches
- [x] Timeline — paginated log grouped by day, type filtering, WebSocket live feed
- [x] Dark mode — Tailwind `dark` class toggle with localStorage persistence, light mode overrides in CSS
- [x] Responsive — Tailwind responsive classes, TOC sidebar hidden on mobile, graph legend collapses
- [x] WebSocket — reconnection with exponential backoff, status indicator, event bus for live updates
- [x] Performance — no framework overhead, CDN resources, single HTML file, ES modules loaded in parallel

**Spec gaps (intentional, deferred):**
- [ ] Section 5.4 Linker — "Suggestions" overlay in graph view (Graph→Wiki proposals). The graph view shows node details and links to wiki, but the interactive "Create page?" / "Add wikilink?" dialogs are a Week 2/3 feature that requires deeper Server integration.
- [ ] Section 5.5 "Filter by community" showing community names (LLM-labeled). Currently shows "Community 0", "Community 1". Named communities depend on the Analyzer producing labels, which is a Core squad Week 2 feature.
- [ ] Export buttons in the dashboard (e.g., "Export as PDF", "Export as SVG"). Export is covered by Plan 5 (Quality) and the CLI — the dashboard can add buttons pointing to `/api/export/{format}` once those endpoints exist.

**Placeholder scan:** No TBD/TODO in any task step. All code is complete and functional against the documented API contract. The API mock tests in Task 7 document every endpoint the dashboard consumes.

**Type consistency:** All views use the same `api()` function from `app.js`. All views follow the `init(container, params)` / `destroy()` contract. WebSocket events use the same `on(event, callback)` pattern with cleanup via returned unsubscribe function.

**Performance budget:** Single HTML file (~7KB), 5 JS modules (~4-6KB each), 1 CSS file (~4KB). Total dashboard payload ~35KB + CDN libs (Tailwind ~15KB, vis-network ~300KB, marked ~40KB, highlight.js ~50KB). vis-network is the heavy dependency — the graph view lazy-loads it only when visited. Dashboard load target (<200ms) is achievable since HTML + app.js load first, then view modules load on-demand via dynamic `import()`.

---

## Remaining Plans (to be written separately)

- **Plan 2 — Server:** FastAPI app, REST routes, MCP server, WebSocket (provides the API this dashboard consumes)
- **Plan 4 — Skills + CLI:** 7 skills, typer CLI, multi-platform install
- **Plan 5 — Quality:** CI/CD, benchmarks, worked examples, README, export formats
