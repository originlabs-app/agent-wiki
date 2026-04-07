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
    let viewName = segments[0] || 'welcome';
    let params = segments.slice(1);

    // Backward compat: #/wiki/* -> #/explorer/wiki/*
    if (viewName === 'wiki') {
        const newHash = params.length
            ? `#/explorer/wiki/${params.join('/')}`
            : '#/explorer';
        window.location.hash = newHash;
        return;
    }

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
    emit('view:changed', { view: viewName });

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
// Project Dropdown
// ---------------------------------------------------------------------------

let dropdownOpen = false;

async function initProjectDropdown() {
    const container = document.getElementById('project-dropdown-container');
    const trigger = document.getElementById('project-dropdown-trigger');
    const menu = document.getElementById('project-dropdown-menu');
    const nameEl = document.getElementById('project-dropdown-name');
    const listEl = document.getElementById('project-dropdown-list');
    const openFolderBtn = document.getElementById('dropdown-open-folder');
    const recentBtn = document.getElementById('dropdown-recent-projects');

    if (!container) return;

    // Listen to view changes — hide dropdown on welcome
    on('view:changed', ({ view }) => {
        if (view === 'welcome') {
            container.classList.add('hidden');
        } else {
            container.classList.remove('hidden');
        }
    });

    // Click trigger → toggle menu
    trigger.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (dropdownOpen) {
            closeMenu();
        } else {
            await refreshDropdown();
            menu.classList.remove('hidden');
            dropdownOpen = true;
        }
    });

    // Click outside → close
    document.addEventListener('click', (e) => {
        if (dropdownOpen && !menu.contains(e.target) && e.target !== trigger) {
            closeMenu();
        }
    });

    // Open Folder from dropdown
    openFolderBtn.addEventListener('click', () => {
        closeMenu();
        window.location.hash = '#/';
    });

    // Recent Projects → welcome
    recentBtn.addEventListener('click', () => {
        closeMenu();
        window.location.hash = '#/welcome';
    });

    async function refreshDropdown() {
        const data = await api.get('/api/projects').catch(() => ({ projects: [] }));
        const projects = (data.projects || []).sort(
            (a, b) => new Date(b.last_opened) - new Date(a.last_opened)
        );

        // Set current project name (most recently opened)
        if (projects.length > 0) {
            nameEl.textContent = projects[0].name;
        }

        // Render project list
        listEl.innerHTML = projects.slice(0, 8).map(p => `
            <button class="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-surface-2 hover:text-white transition-colors flex items-center gap-2 group"
                    data-path="${p.path.replace(/"/g, '&quot;')}">
                <svg class="w-4 h-4 text-gray-600 group-hover:text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                </svg>
                <span class="truncate flex-1">${p.name}</span>
                <svg class="w-3 h-3 text-gray-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path d="M9 5l7 7-7 7"/>
                </svg>
            </button>
        `).join('');

        listEl.querySelectorAll('button[data-path]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const path = btn.dataset.path;
                closeMenu();
                try {
                    await api.post('/api/projects/switch', { path });
                    window.location.reload();
                } catch (err) {
                    console.error('[dropdown] switch failed:', err);
                }
            });
        });
    }

    function closeMenu() {
        menu.classList.add('hidden');
        dropdownOpen = false;
    }

    // Initialize: check if we should show
    const hash = window.location.hash;
    const segments = (hash || '#/').split('/').filter(Boolean);
    const viewName = segments[0] || 'welcome';
    if (viewName !== 'welcome') {
        container.classList.remove('hidden');
        refreshDropdown();
    }
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function boot() {
    // Import views
    const [graphMod, explorerMod, auditMod, searchMod, timelineMod, welcomeMod] = await Promise.all([
        import('/dashboard/graph.js'),
        import('/dashboard/explorer.js'),
        import('/dashboard/audit.js'),
        import('/dashboard/search.js'),
        import('/dashboard/timeline.js'),
        import('/dashboard/welcome.js'),
    ]);

    registerView('graph', graphMod);
    registerView('explorer', explorerMod);
    registerView('audit', auditMod);
    registerView('search', searchMod);
    registerView('timeline', timelineMod);
    registerView('welcome', welcomeMod);

    // Initialize
    initQuickSearch();
    initThemeToggle();
    initProjectDropdown();
    connectWebSocket();

    // Route
    window.addEventListener('hashchange', route);
    await route();

    // Emit view changed after first route
    emit('view:changed', { view: state.currentView });

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
