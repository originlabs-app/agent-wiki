/**
 * Atlas Dashboard — Welcome View
 * "Recent Projects" screen shown when no project is loaded.
 * Shown on first launch or when Atlas logo is clicked.
 */

import { api, on, emit } from '/dashboard/app.js';

// ---------------------------------------------------------------------
// State
// ---------------------------------------------------------------------

let projects = [];
let openLoading = false;

// ---------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------

export function init(container) {
    render(container);
    loadProjects();
    setupProjectSwitchListener();
}

export function destroy() {
    // No persistent state to clean up
}

// ---------------------------------------------------------------------
// Load
// ---------------------------------------------------------------------

async function loadProjects() {
    try {
        const data = await api.get('/api/projects');
        projects = (data.projects || []).sort(
            (a, b) => new Date(b.last_opened) - new Date(a.last_opened)
        );
        renderProjects();
    } catch (err) {
        console.error('[welcome] Failed to load projects:', err);
    }
}

function setupProjectSwitchListener() {
    on('project.switched', ({ name }) => {
        // Navigate to graph when a project is activated
        window.location.hash = '#/graph';
    });
}

// ---------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------

function render(container) {
    container.innerHTML = `
        <div class="flex flex-col h-full">
            <div class="flex-1 flex items-center justify-center px-6">
                <div class="w-full max-w-2xl">
                    <!-- Header -->
                    <div class="text-center mb-8">
                        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-atlas-600/20 mb-4">
                            <svg class="w-8 h-8 text-atlas-400" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <circle cx="14" cy="14" r="12" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
                                <circle cx="14" cy="6" r="2.5" fill="currentColor"/>
                                <circle cx="7" cy="18" r="2.5" fill="currentColor"/>
                                <circle cx="21" cy="18" r="2.5" fill="currentColor"/>
                                <line x1="14" y1="8.5" x2="8.5" y2="16" stroke="currentColor" stroke-width="1.2" opacity="0.6"/>
                                <line x1="14" y1="8.5" x2="19.5" y2="16" stroke="currentColor" stroke-width="1.2" opacity="0.6"/>
                                <line x1="9.5" y1="18" x2="18.5" y2="18" stroke="currentColor" stroke-width="1.2" opacity="0.6"/>
                            </svg>
                        </div>
                        <h1 class="text-3xl font-bold text-white mb-2">Welcome to Atlas</h1>
                        <p class="text-gray-400 text-sm">Open a folder to start mapping your knowledge graph</p>
                    </div>

                    <!-- Open Folder -->
                    <div class="mb-8">
                        <div id="open-folder-form" class="flex gap-2">
                            <div class="flex-1 relative">
                                <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                    <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                                </svg>
                                <input
                                    type="text"
                                    id="open-folder-path"
                                    placeholder="Enter folder path, e.g. ~/dev/my-project"
                                    class="w-full pl-10 pr-4 py-2.5 bg-surface-2 border border-surface-3 rounded-lg text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-atlas-500 focus:bg-surface-3 transition-colors"
                                />
                            </div>
                            <button
                                id="open-folder-btn"
                                class="px-5 py-2.5 bg-atlas-600 hover:bg-atlas-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 shrink-0"
                            >
                                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                    <path d="M12 4v16m8-8H4"/>
                                </svg>
                                Open Folder
                            </button>
                        </div>
                        <div id="open-folder-error" class="hidden mt-2 text-xs text-red-400"></div>

                        <!-- Loading state -->
                        <div id="open-folder-loading" class="hidden mt-3">
                            <div class="flex items-center gap-3 text-sm text-gray-400">
                                <svg class="w-4 h-4 animate-spin text-atlas-400" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                                </svg>
                                <span id="open-folder-status">Scanning folder...</span>
                            </div>
                        </div>
                    </div>

                    <!-- Recent Projects -->
                    <div id="recent-projects-section">
                        <div class="flex items-center justify-between mb-3">
                            <h2 class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Recent Projects</h2>
                        </div>
                        <div id="recent-projects-list" class="space-y-2">
                            <div class="text-sm text-gray-600 py-6 text-center">Loading...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Wire up open folder
    const input = document.getElementById('open-folder-path');
    const btn = document.getElementById('open-folder-btn');

    btn.addEventListener('click', handleOpenFolder);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') handleOpenFolder();
    });
}

function renderProjects() {
    const list = document.getElementById('recent-projects-list');
    if (!list) return;

    if (!projects.length) {
        list.innerHTML = `
            <div class="text-sm text-gray-600 py-6 text-center">
                No recent projects. Enter a folder path above to get started.
            </div>
        `;
        return;
    }

    list.innerHTML = projects.slice(0, 10).map(p => {
        const age = formatAge(p.last_opened);
        const healthColor = p.health >= 80 ? 'text-emerald-400' : p.health >= 50 ? 'text-amber-400' : 'text-gray-500';
        const healthBar = healthBarChars(p.health);
        return `
            <button
                class="project-card w-full text-left px-4 py-3 bg-surface-1 hover:bg-surface-2 border border-surface-3 hover:border-surface-4 rounded-lg transition-all group"
                data-path="${escapeAttr(p.path)}"
                data-name="${escapeAttr(p.name)}"
            >
                <div class="flex items-center justify-between mb-1">
                    <div class="flex items-center gap-2 min-w-0">
                        <svg class="w-4 h-4 text-gray-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                        </svg>
                        <span class="text-sm font-medium text-gray-200 group-hover:text-white truncate transition-colors">${escapeHtml(p.name)}</span>
                    </div>
                    <span class="text-xs text-gray-600 shrink-0 ml-2">${age}</span>
                </div>
                <div class="flex items-center gap-3 text-xs text-gray-500 pl-6">
                    <span>${p.nodes} nodes</span>
                    <span class="text-gray-700">&middot;</span>
                    <span>${p.edges} edges</span>
                    <span class="text-gray-700">&middot;</span>
                    <span class="${healthColor}">${p.health.toFixed(0)} ${healthBar}</span>
                </div>
                <div class="text-xs text-gray-600 pl-6 truncate mt-0.5">${escapeHtml(p.path)}</div>
            </button>
        `;
    }).join('');

    // Wire project card clicks
    list.querySelectorAll('.project-card').forEach(card => {
        card.addEventListener('click', () => {
            const path = card.dataset.path;
            const name = card.dataset.name;
            switchToProject(path, name);
        });
    });
}

// ---------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------

async function handleOpenFolder() {
    if (openLoading) return;
    const input = document.getElementById('open-folder-path');
    const btn = document.getElementById('open-folder-btn');
    const errorEl = document.getElementById('open-folder-error');
    const loadingEl = document.getElementById('open-folder-loading');
    const statusEl = document.getElementById('open-folder-status');

    const path = input.value.trim();
    if (!path) {
        showError('Please enter a folder path');
        return;
    }

    openLoading = true;
    btn.disabled = true;
    btn.classList.add('opacity-50', 'cursor-not-allowed');
    hideError();
    loadingEl.classList.remove('hidden');
    statusEl.textContent = `Opening ${path}...`;

    try {
        statusEl.textContent = 'Scanning L0+L1 (free, fast)...';
        await api.post('/api/projects/open', { path });

        // Success — navigate to graph
        window.location.hash = '#/graph';
        // Force reload to reinitialize views with new project data
        window.location.reload();
    } catch (err) {
        showError(err.message || 'Failed to open folder');
        openLoading = false;
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
        loadingEl.classList.add('hidden');
    }
}

async function switchToProject(path, name) {
    try {
        await api.post('/api/projects/switch', { path });
        // Navigate to graph without full reload — emit event so graph reloads its data
        window.location.hash = '#/graph';
    } catch (err) {
        console.error('[welcome] Switch failed:', err);
        showError(`Failed to switch to ${name}: ${err.message}`);
    }
}

// ---------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------

function showError(msg) {
    const el = document.getElementById('open-folder-error');
    if (el) {
        el.textContent = msg;
        el.classList.remove('hidden');
    }
}

function hideError() {
    const el = document.getElementById('open-folder-error');
    if (el) el.classList.add('hidden');
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function escapeAttr(str) {
    return String(str).replace(/"/g, '&quot;');
}

function formatAge(isoString) {
    if (!isoString) return '';
    const diff = Date.now() - new Date(isoString).getTime();
    const mins = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return new Date(isoString).toLocaleDateString();
}

function healthBarChars(score) {
    const filled = Math.round(score / 10);
    return '█'.repeat(filled) + '░'.repeat(10 - filled);
}
