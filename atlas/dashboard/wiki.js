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
