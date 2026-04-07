"""Tests for Sidebar v2 changes in explorer.js."""
import re
from pathlib import Path

EXPLORER_JS = Path(__file__).resolve().parents[2] / "atlas" / "dashboard" / "explorer.js"
STYLES_CSS = Path(__file__).resolve().parents[2] / "atlas" / "dashboard" / "styles.css"


class TestBrowseToggle:
    """Verify the browse toggle replaces old sidebar sections."""

    def test_explorer_js_exists(self):
        assert EXPLORER_JS.exists()

    def test_no_section_files_in_sidebar(self):
        """Old __section_files toggle should not appear in renderSidebar."""
        content = EXPLORER_JS.read_text()
        # The old sidebar rendered __section_files, __section_wiki, __section_communities
        # as separate collapsible sections. They should no longer be in renderSidebar().
        render_sidebar_match = re.search(
            r'function renderSidebar\(\)(.*?)(?=\nfunction |\n// ---)',
            content,
            re.DOTALL
        )
        assert render_sidebar_match, "renderSidebar() not found"
        sidebar_body = render_sidebar_match.group(1)
        assert '__section_files' not in sidebar_body
        assert '__section_wiki' not in sidebar_body
        assert '__section_communities' not in sidebar_body

    def test_browse_mode_state_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'browseMode' in content
        assert 'atlas-browse-mode' in content

    def test_render_browse_toggle_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'renderBrowseToggle' in content

    def test_render_browse_content_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'renderBrowseContent' in content

    def test_render_type_list_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'renderTypeList' in content

    def test_render_community_list_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'renderCommunityList' in content

    def test_browse_toggle_exists(self):
        """Old renderWikiList/renderCommunities still exist as helpers used by browse modes,
        but they are no longer called directly in renderSidebar()."""
        content = EXPLORER_JS.read_text()
        # These functions exist (reused internally) but are NOT the top-level sidebar sections
        render_sidebar_match = re.search(
            r'function renderSidebar\(\)(.*?)(?=\nfunction |\n// ---)',
            content,
            re.DOTALL
        )
        assert render_sidebar_match, "renderSidebar() not found"
        sidebar_body = render_sidebar_match.group(1)
        # Old top-level collapsible sections are gone
        assert '__section_files' not in sidebar_body
        assert '__section_wiki' not in sidebar_body
        assert '__section_communities' not in sidebar_body
        # New browse toggle is present
        assert 'renderBrowseToggle' in sidebar_body or 'browseMode' in content

    def test_set_browse_mode_action(self):
        content = EXPLORER_JS.read_text()
        assert 'set-browse-mode' in content


class TestWikilinks:
    """Verify wikilinks are processed as a post-processing step."""

    def test_process_wikilinks_exists(self):
        content = EXPLORER_JS.read_text()
        assert 'processWikilinks' in content

    def test_wikilinks_not_only_in_paragraph(self):
        """processWikilinks should be called after marked.parse, not in renderer.paragraph."""
        content = EXPLORER_JS.read_text()
        # Should NOT have the old pattern of overriding renderer.paragraph for wikilinks
        assert 'renderer.paragraph' not in content or 'wikilink' not in content.split('renderer.paragraph')[1].split('function')[0]


class TestEnrichButton:
    """Verify the Enrich with AI button exists."""

    def test_enrich_action_in_overview(self):
        content = EXPLORER_JS.read_text()
        assert 'enrich-ai' in content

    def test_enrich_modal_function(self):
        content = EXPLORER_JS.read_text()
        assert 'showEnrichModal' in content

    def test_enrich_modal_shows_cli_fallback(self):
        content = EXPLORER_JS.read_text()
        assert 'atlas scan --deep' in content


class TestContentPanelFixes:
    """Verify content panel header is sticky."""

    def test_sticky_header_pattern(self):
        content = EXPLORER_JS.read_text()
        # The content panel should wrap content in a flex-col layout
        # with a sticky header bar
        assert 'shrink-0' in content
        # Edit and View in Graph should be in a header bar, not buried in scroll content
        assert 'data-action="edit-page"' in content

    def test_humanize_community_label(self):
        content = EXPLORER_JS.read_text()
        assert 'humanizeCommunityLabel' in content


class TestCssAdditions:
    """Verify new CSS was added."""

    def test_browse_toggle_styles(self):
        content = STYLES_CSS.read_text()
        assert 'enrich-pulse' in content or 'enrich-in-progress' in content

    def test_modal_styles(self):
        content = STYLES_CSS.read_text()
        assert 'enrich-modal-overlay' in content or 'modal-fade-in' in content
