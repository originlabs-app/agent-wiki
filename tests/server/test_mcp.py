import pytest
from pathlib import Path

from atlas.server.mcp import handle_tool_call, TOOL_DEFINITIONS
from atlas.server.deps import create_engine_set, EventBus


@pytest.fixture
def mcp_engines(engine_root):
    engines = create_engine_set(engine_root)
    engines.wiki.write(
        "wiki/concepts/auth.md",
        "# Authentication\n\nJWT tokens. See [[billing]].",
        frontmatter={"type": "wiki-concept", "title": "Authentication", "confidence": "high", "tags": ["auth"]},
    )
    engines.wiki.write(
        "wiki/concepts/billing.md",
        "# Billing\n\nStripe. See [[auth]].",
        frontmatter={"type": "wiki-concept", "title": "Billing", "confidence": "medium"},
    )
    engines.linker.sync_wiki_to_graph()
    return engines


def test_tool_definitions_count():
    assert len(TOOL_DEFINITIONS) == 12


def test_tool_definitions_names():
    names = {t["name"] for t in TOOL_DEFINITIONS}
    expected = {
        "atlas.scan",
        "atlas.query",
        "atlas.path",
        "atlas.explain",
        "atlas.god_nodes",
        "atlas.stats",
        "atlas.ingest",
        "atlas.wiki.read",
        "atlas.wiki.write",
        "atlas.wiki.search",
        "atlas.audit",
        "atlas.suggest_links",
    }
    assert names == expected


def test_tool_definitions_have_descriptions():
    for tool in TOOL_DEFINITIONS:
        assert "description" in tool
        assert len(tool["description"]) > 10


def test_tool_definitions_have_input_schema():
    for tool in TOOL_DEFINITIONS:
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"


def test_handle_scan(mcp_engines, engine_root):
    event_bus = EventBus()
    (engine_root / "raw" / "untracked" / "mcp_test.py").write_text("class MCP:\n    pass\n")

    result = handle_tool_call(
        "atlas.scan",
        {"path": str(engine_root / "raw" / "untracked")},
        engines=mcp_engines,
        event_bus=event_bus,
    )
    assert result["nodes_found"] >= 1


def test_handle_query(mcp_engines):
    result = handle_tool_call(
        "atlas.query",
        {"question": "auth", "mode": "bfs", "depth": 2},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert len(result["nodes"]) >= 1


def test_handle_path(mcp_engines):
    result = handle_tool_call(
        "atlas.path",
        {"source": "auth", "target": "billing"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["found"] is True


def test_handle_path_not_found(mcp_engines):
    result = handle_tool_call(
        "atlas.path",
        {"source": "auth", "target": "nonexistent"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["found"] is False


def test_handle_explain(mcp_engines):
    result = handle_tool_call(
        "atlas.explain",
        {"concept": "auth"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["concept"] == "auth"
    assert result["label"] == "Authentication"
    assert len(result["neighbors"]) >= 1


def test_handle_explain_not_found(mcp_engines):
    result = handle_tool_call(
        "atlas.explain",
        {"concept": "nonexistent"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert "error" in result


def test_handle_god_nodes(mcp_engines):
    result = handle_tool_call(
        "atlas.god_nodes",
        {"top_n": 5},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert len(result["nodes"]) >= 1


def test_handle_stats(mcp_engines):
    result = handle_tool_call(
        "atlas.stats",
        {},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["nodes"] >= 2
    assert "confidence_breakdown" in result


def test_handle_wiki_read(mcp_engines):
    result = handle_tool_call(
        "atlas.wiki.read",
        {"page": "wiki/concepts/auth.md"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["title"] == "Authentication"
    assert "JWT" in result["content"]


def test_handle_wiki_read_not_found(mcp_engines):
    result = handle_tool_call(
        "atlas.wiki.read",
        {"page": "wiki/concepts/nonexistent.md"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result is None or result.get("error") == "not_found"


def test_handle_wiki_write(mcp_engines):
    result = handle_tool_call(
        "atlas.wiki.write",
        {
            "page": "wiki/concepts/caching.md",
            "content": "# Caching\n\nRedis layer.",
            "frontmatter": {"type": "wiki-concept", "title": "Caching"},
        },
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["page"] == "wiki/concepts/caching.md"

    page = mcp_engines.wiki.read("wiki/concepts/caching.md")
    assert page is not None


def test_handle_wiki_search(mcp_engines):
    result = handle_tool_call(
        "atlas.wiki.search",
        {"terms": "JWT"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert len(result["results"]) >= 1


def test_handle_audit(mcp_engines):
    result = handle_tool_call(
        "atlas.audit",
        {},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert "orphan_pages" in result
    assert "god_nodes" in result
    assert "health_score" in result


def test_handle_suggest_links(mcp_engines):
    result = handle_tool_call(
        "atlas.suggest_links",
        {},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert "suggestions" in result


def test_handle_ingest_file(mcp_engines, engine_root):
    (engine_root / "raw" / "untracked" / "mcp_ingest.md").write_text("# MCP Ingest Test")

    result = handle_tool_call(
        "atlas.ingest",
        {"file_path": "raw/untracked/mcp_ingest.md", "title": "MCP Test"},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert result["path"] is not None
    assert result["path"].startswith("raw/ingested/")


def test_handle_unknown_tool(mcp_engines):
    result = handle_tool_call(
        "atlas.unknown_tool",
        {},
        engines=mcp_engines,
        event_bus=EventBus(),
    )
    assert "error" in result
