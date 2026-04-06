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
