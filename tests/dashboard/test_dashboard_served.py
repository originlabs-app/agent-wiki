"""Verify the dashboard is served correctly by FastAPI."""
from pathlib import Path


def test_index_html_exists():
    index = Path(__file__).parent.parent.parent / "atlas" / "dashboard" / "index.html"
    assert index.exists(), "index.html must exist in atlas/dashboard/"
    content = index.read_text()
    assert "<!DOCTYPE html>" in content
    assert "id=\"app\"" in content
    assert "app.js" in content


def test_static_files_exist():
    dashboard = Path(__file__).parent.parent.parent / "atlas" / "dashboard"
    required = ["index.html", "app.js", "graph.js", "wiki.js", "explorer.js", "audit.js", "search.js", "timeline.js", "styles.css"]
    for f in required:
        assert (dashboard / f).exists(), f"Missing: {f}"


def test_no_build_artifacts():
    dashboard = Path(__file__).parent.parent.parent / "atlas" / "dashboard"
    forbidden = ["node_modules", "package.json", "dist", "build", ".next", "vite.config"]
    for f in forbidden:
        assert not (dashboard / f).exists(), f"Build artifact found: {f} — dashboard must be static-first"
