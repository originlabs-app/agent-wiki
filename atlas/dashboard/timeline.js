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
