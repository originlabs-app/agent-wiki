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
