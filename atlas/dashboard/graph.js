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
        <div class="flex" style="height: calc(100vh - 3.5rem);">
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
