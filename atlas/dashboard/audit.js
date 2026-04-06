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
