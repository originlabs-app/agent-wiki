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
let browseMode = 'folder'; // 'folder' | 'type' | 'community'
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

function loadBrowseMode() {
    try {
        const stored = localStorage.getItem('atlas-browse-mode');
        if (stored && ['folder', 'type', 'community'].includes(stored)) {
            browseMode = stored;
        }
    } catch { /* ignore */ }
}

function saveFolderState() {
    try {
        localStorage.setItem('atlas-explorer-folders', JSON.stringify(folderState));
    } catch { /* ignore */ }
}

function saveBrowseMode() {
    try {
        localStorage.setItem('atlas-browse-mode', browseMode);
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

    // Code blocks with highlight.js
    renderer.code = function (code, language) {
        const lang = language && hljs.getLanguage(language) ? language : 'plaintext';
        const highlighted = hljs.highlight(code, { language: lang }).value;
        return `<pre><code class="hljs language-${lang}">${highlighted}</code></pre>`;
    };

    return renderer;
}

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

// ---------------------------------------------------------------------------
// Sidebar: File Tree Section
// ---------------------------------------------------------------------------

function renderFileTree(nodes, depth = 0) {
    if (!nodes || !nodes.length) {
        if (depth === 0) {
            return `
                <div class="px-3 py-2 text-xs text-gray-500">No files scanned.</div>
            `;
        }
        return '';
    }

    return nodes.map(node => {
        const isDir = node.children !== null && node.children !== undefined;
        const isCollapsed = folderState[node.path] !== false;
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
        return `<div class="px-3 py-2 text-xs text-gray-500">No wiki pages yet.</div>`;
    }

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

                            return `
                                <a href="#/explorer/wiki/${encodeURIComponent(slug)}"
                                   class="flex items-center gap-1.5 px-3 py-1 text-xs cursor-pointer hover:bg-surface-2 transition-colors ${isActive ? 'bg-surface-2' : ''}"
                                   style="padding-left: 28px">
                                    <span class="truncate ${isActive ? 'text-white' : 'text-gray-400 hover:text-gray-200'} transition-colors">${escapeHtml(page.title)}</span>
                                    <span class="ml-auto flex items-center gap-1 shrink-0">
                                        ${tags.slice(0, 2).map(t => `<span class="px-1 py-0 bg-surface-3 rounded text-[9px] text-gray-500">${t}</span>`).join('')}
                                        ${status ? `<span class="text-[10px] text-gray-500">${status}</span>` : ''}
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
// Browse Toggle + Dispatcher
// ---------------------------------------------------------------------------

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

function renderBrowseContent() {
    switch (browseMode) {
        case 'folder':    return renderFileTree(sidebarData.files);
        case 'type':      return renderTypeList();
        case 'community': return renderCommunityList();
        default:          return renderFileTree(sidebarData.files);
    }
}

function renderTypeList() {
    const pages = sidebarData.pages;
    const files = sidebarData.files;

    if ((!pages || !pages.length) && (!files || !files.length)) {
        return `<div class="px-3 py-2 text-xs text-gray-500">No content scanned.</div>`;
    }

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

function humanizeCommunityLabel(label) {
    if (label.includes('/') || /\.\w{1,5}$/.test(label)) {
        const base = label.split('/').pop().replace(/\.\w{1,5}$/, '');
        return base.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }
    return label;
}

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

// ---------------------------------------------------------------------------
// Full Sidebar Render
// ---------------------------------------------------------------------------

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
                <p class="text-gray-500 mb-4">No wiki page for "${escapeHtml(slug)}"</p>
                <a href="#/explorer" class="text-atlas-400 hover:text-atlas-300 text-sm">Back to Explorer</a>
            </div>
        </div>
    `;
}

async function renderWikiReadMode(page, contentEl) {
    const slug = page.path.replace(/\.md$/, '').split('/').pop();

    let body = page.content;
    const fmMatch = body.match(/^---\n[\s\S]*?\n---\n/);
    if (fmMatch) {
        body = body.slice(fmMatch[0].length);
    }

    let html = marked.parse(body, markedOptions);
    html = processWikilinks(html);
    html = addHeadingIds(html);

    const fm = page.frontmatter || {};
    const skipKeys = new Set(['title', 'type']);
    const fmEntries = Object.entries(fm).filter(([k]) => !skipKeys.has(k));

    const parts = page.path.replace(/\.md$/, '').split('/').filter(Boolean);
    const breadcrumbs = [{ label: 'Explorer', href: '#/explorer' }];
    parts.forEach((part, i) => {
        breadcrumbs.push({
            label: part.charAt(0).toUpperCase() + part.slice(1),
            href: i === parts.length - 1 ? null : null,
        });
    });

    const tags = fm.tags || [];

    contentEl.innerHTML = `
        <div class="flex flex-col h-full">
            <!-- Sticky action header -->
            <div class="flex items-center justify-between px-6 py-2 border-b border-surface-3 bg-surface-1 shrink-0">
                <nav class="flex items-center gap-1.5 text-xs text-gray-500">
                    ${breadcrumbs.map((c, i) => {
                        const sep = i > 0 ? '<span class="text-gray-600">/</span>' : '';
                        if (c.href) {
                            return `${sep}<a href="${c.href}" class="hover:text-gray-300 transition-colors">${c.label}</a>`;
                        }
                            return `${sep}<span class="${i === breadcrumbs.length - 1 ? 'text-gray-300' : 'text-gray-500'}">${c.label}</span>`;
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
                    <div>
                        <h1 class="text-2xl font-bold text-white mb-1">${escapeHtml(page.title)}</h1>
                        <div class="flex items-center gap-2 text-xs mt-1">
                            <span class="text-gray-500 font-mono">${escapeHtml(page.path)}</span>
                            ${page.type ? `<span class="px-2 py-0.5 rounded bg-surface-3 text-gray-400">${page.type}</span>` : ''}
                        </div>
                    </div>

                    ${tags.length ? `
                        <div class="flex gap-1 mt-3 mb-4">
                            ${tags.map(t => `<span class="px-1.5 py-0.5 bg-surface-3 rounded text-[10px] text-gray-400">${t}</span>`).join('')}
                        </div>
                    ` : ''}

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

                    <div class="wiki-content">${html}</div>

                    <div id="explorer-backlinks" class="mt-8 pt-4 border-t border-surface-3"></div>
                    <div id="explorer-neighbors" class="mt-4 pt-4 border-t border-surface-3"></div>
                </div>
            </div>
        </div>
    `;

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

    loadNeighbors(slug).then(neighbors => {
        const el = document.getElementById('explorer-neighbors');
        if (el && neighbors.length) {
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
            <div class="flex items-center justify-between px-4 py-2 border-b border-surface-3 bg-surface-1 shrink-0">
                <span class="text-xs text-amber-400 font-medium">Editing ${escapeHtml(page.path)}</span>
                <div class="flex gap-2">
                    <button data-action="cancel-edit" class="px-3 py-1 text-xs text-gray-400 hover:text-gray-200 bg-surface-3 rounded transition-colors">Cancel</button>
                    <button data-action="save-edit" class="px-3 py-1 text-xs text-white bg-atlas-600 rounded hover:bg-atlas-700 transition-colors">Save</button>
                </div>
            </div>

            <div class="flex flex-1 overflow-hidden">
                <div class="flex-1 border-r border-surface-3 flex flex-col">
                    <div class="px-3 py-1 text-[10px] text-gray-500 uppercase tracking-wider bg-surface-2 border-b border-surface-3">Raw Markdown</div>
                    <textarea id="explorer-editor"
                        class="flex-1 w-full bg-surface-0 p-4 text-sm text-gray-300 font-mono leading-relaxed resize-none focus:outline-none"
                    >${escapeHtml(rawContent)}</textarea>
                </div>

                <div class="flex-1 flex flex-col">
                    <div class="px-3 py-1 text-[10px] text-gray-500 uppercase tracking-wider bg-surface-2 border-b border-surface-3">Live Preview</div>
                    <div id="explorer-preview" class="flex-1 overflow-y-auto p-4 wiki-content"></div>
                </div>
            </div>
        </div>
    `;

    const textarea = document.getElementById('explorer-editor');
    const preview = document.getElementById('explorer-preview');

    updatePreview(textarea.value, preview);

    textarea.addEventListener('input', () => {
        clearTimeout(editDebounceTimer);
        editDebounceTimer = setTimeout(() => {
            updatePreview(textarea.value, preview);
        }, 200);
    });

    textarea.focus();
}

function updatePreview(rawContent, previewEl) {
    let body = rawContent;
    const fmMatch = body.match(/^---\n[\s\S]*?\n---\n/);
    if (fmMatch) {
        body = body.slice(fmMatch[0].length);
    }

    let html = marked.parse(body, markedOptions);
    html = processWikilinks(html);
    html = addHeadingIds(html);
    previewEl.innerHTML = html;
}

async function saveEdit(page, contentEl) {
    const textarea = document.getElementById('explorer-editor');
    if (!textarea) return;

    const rawText = textarea.value;

    // Strip frontmatter from raw text — server will re-add it from the frontmatter field
    let newContent = rawText;
    let frontmatter = page.frontmatter || {};
    const fmMatch = rawText.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (fmMatch) {
        try {
            // Parse frontmatter from editor to pick up user edits
            const lines = fmMatch[1].split('\n');
            const parsed = {};
            for (const line of lines) {
                const idx = line.indexOf(':');
                if (idx > 0) {
                    const key = line.slice(0, idx).trim();
                    let val = line.slice(idx + 1).trim();
                    // Strip quotes
                    if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1);
                    // Parse arrays
                    if (val.startsWith('[') && val.endsWith(']')) {
                        try { val = JSON.parse(val.replace(/'/g, '"')); } catch {}
                    }
                    parsed[key] = val;
                }
            }
            frontmatter = { ...frontmatter, ...parsed };
        } catch {}
        newContent = fmMatch[2];
    }

    try {
        await api.post('/api/wiki/write', {
            page: page.path,
            content: newContent,
            frontmatter: frontmatter,
        });

        page.content = newContent;
        isEditing = false;
        toast('Page saved', 'success');
        renderWikiReadMode(page, contentEl);
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
        html = processWikilinks(html);
        html = addHeadingIds(html);
        renderedContent = `<div class="wiki-content">${html}</div>`;
    } else if (isCode) {
        const lang = ext && hljs.getLanguage(ext) ? ext : 'plaintext';
        const highlighted = hljs.highlight(content, { language: lang }).value;
        renderedContent = `<pre class="bg-surface-1 border border-surface-3 rounded-lg p-4 overflow-x-auto"><code class="hljs language-${lang} text-sm">${highlighted}</code></pre>`;
    } else {
        renderedContent = `<pre class="bg-surface-1 border border-surface-3 rounded-lg p-4 overflow-x-auto text-sm text-gray-300 whitespace-pre-wrap">${escapeHtml(content)}</pre>`;
    }

    const graphNode = findGraphNode(path);

    contentEl.innerHTML = `
        <div class="flex flex-col h-full">
            <!-- Sticky action header -->
            <div class="flex items-center justify-between px-6 py-2 border-b border-surface-3 bg-surface-1 shrink-0">
                <nav class="flex items-center gap-1.5 text-xs text-gray-500">
                    <a href="#/explorer" class="hover:text-gray-300 transition-colors">Explorer</a>
                    ${path.split('/').map((part, i, arr) => `
                        <span class="text-gray-600">/</span>
                        <span class="${i === arr.length - 1 ? 'text-gray-300' : 'text-gray-500'}">${part}</span>
                    `).join('')}
                </nav>
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

            <!-- Scrollable content -->
            <div class="flex-1 overflow-y-auto">
                <div class="max-w-3xl mx-auto px-6 py-6">
                    <div class="mb-4">
                        <h1 class="text-2xl font-bold text-white mb-1">${escapeHtml(name)}</h1>
                        <div class="flex items-center gap-2 text-xs">
                            <span class="text-gray-500 font-mono">${escapeHtml(path)}</span>
                            <span class="px-2 py-0.5 rounded bg-surface-3 text-gray-400">${type}</span>
                            ${graphNode ? `<span class="text-gray-500">${graphNode.degree} connections</span>` : ''}
                        </div>
                    </div>

                    ${renderedContent}
                </div>
            </div>
        </div>
    `;
}

function findGraphNode(path) {
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

    const memberDetails = community.members.map(memberId => {
        const fileNode = findGraphNode(memberId);
        return {
            id: memberId,
            degree: fileNode?.degree || 0,
            type: fileNode?.type || 'unknown',
        };
    }).sort((a, b) => b.degree - a.degree);

    const wikiSlugs = new Set(sidebarData.pages.map(p => p.path.replace(/\.md$/, '').split('/').pop().toLowerCase()));
    const coverage = memberDetails.map(m => ({
        ...m,
        hasWiki: wikiSlugs.has(m.id.split('/').pop().replace(/\.[^.]+$/, '').toLowerCase()),
    }));

    contentEl.innerHTML = `
        <div class="max-w-3xl mx-auto px-6 py-6">
            <div class="flex items-start justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-bold text-white mb-1">${escapeHtml(humanizeCommunityLabel(community.label))}</h1>
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

            <div class="mb-6">
                <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Key Members</h2>
                <div class="space-y-1">
                    ${coverage.map(m => {
                        const color = NODE_COLORS[m.type] || NODE_COLORS.unknown;
                        const isGodNode = m.degree >= 10;
                        // Route wiki nodes to wiki view, file nodes to file view
                        const isWikiNode = m.type && m.type.startsWith('wiki-');
                        const href = isWikiNode
                            ? `#/explorer/wiki/${encodeURIComponent(m.id)}`
                            : `#/explorer/file/${encodeURIComponent(m.source_file || m.id)}`;
                        return `
                            <a href="${href}" class="flex items-center gap-2 px-3 py-2 bg-surface-1 border border-surface-3 rounded-lg hover:bg-surface-2 transition-colors group">
                                <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background: ${color}"></span>
                                <span class="text-sm text-gray-300 group-hover:text-white transition-colors truncate">${escapeHtml(humanizeCommunityLabel(m.id))}</span>
                                <span class="text-xs text-gray-500 shrink-0">(${m.degree} connections)</span>
                                ${isGodNode ? '<span class="text-[10px] text-amber-400 shrink-0">god node</span>' : ''}
                            </a>
                        `;
                    }).join('')}
                </div>
            </div>

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
// Enrich Modal
// ---------------------------------------------------------------------------

function showEnrichModal() {
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

// ---------------------------------------------------------------------------
// Event Delegation
// ---------------------------------------------------------------------------

let currentPageData = null;

function attachSidebarListeners() {
    const sidebar = document.getElementById('explorer-sidebar');
    if (!sidebar) return;

    sidebar.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;

        const action = target.dataset.action;

        if (action === 'toggle-folder') {
            const path = target.dataset.path;
            if (path.startsWith('__section_') || path.startsWith('wiki-group-')) {
                folderState[path] = !folderState[path];
            } else {
                folderState[path] = folderState[path] === false ? true : false;
            }
            saveFolderState();
            sidebar.outerHTML = renderSidebar();
            attachSidebarListeners();
        }

        if (action === 'show-all-communities') {
            sidebar.outerHTML = renderSidebar();
            attachSidebarListeners();
        }

        if (action === 'set-browse-mode') {
            const mode = target.dataset.mode;
            if (mode && ['folder', 'type', 'community'].includes(mode)) {
                browseMode = mode;
                saveBrowseMode();
                sidebar.outerHTML = renderSidebar();
                attachSidebarListeners();
            }
        }

        if (action === 'enrich-ai') {
            showEnrichModal();
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
// Router
// ---------------------------------------------------------------------------

async function routeContent(params, contentEl) {
    const type = params[0];
    const rest = params.slice(1).join('/');

    if (!type) {
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
// Init / Destroy
// ---------------------------------------------------------------------------

export async function init(container, params) {
    loadFolderState();
    loadBrowseMode();
    await loadSidebarData();

    container.innerHTML = renderLayout(renderNoSelection());
    attachSidebarListeners();

    const contentEl = document.getElementById('explorer-content');
    if (contentEl) {
        attachContentListeners(contentEl);
    }

    if (contentEl) {
        await routeContent(params || [], contentEl);
    }

    refreshSidebarActive();

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
