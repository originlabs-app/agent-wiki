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
