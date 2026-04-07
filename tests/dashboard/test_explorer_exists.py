"""Verify explorer.js exists and has the required module exports."""
from pathlib import Path


def test_explorer_js_exists():
    explorer = Path(__file__).parent.parent.parent / "atlas" / "dashboard" / "explorer.js"
    assert explorer.exists(), "explorer.js must exist in atlas/dashboard/"
    content = explorer.read_text()
    assert "export async function init" in content
    assert "export function destroy" in content


def test_explorer_has_sidebar_sections():
    explorer = Path(__file__).parent.parent.parent / "atlas" / "dashboard" / "explorer.js"
    content = explorer.read_text()
    # Sidebar must reference all 4 sections
    assert "Overview" in content or "overview" in content
    assert "Files" in content or "file-tree" in content
    assert "Wiki" in content or "wiki-list" in content
    assert "Communities" in content or "communities" in content


def test_explorer_imports_app():
    explorer = Path(__file__).parent.parent.parent / "atlas" / "dashboard" / "explorer.js"
    content = explorer.read_text()
    assert "from '/dashboard/app.js'" in content or "from \"/dashboard/app.js\"" in content
