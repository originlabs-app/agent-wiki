"""End-to-end server integration test — REST API, event flow, graph sync."""
import pytest
from fastapi.testclient import TestClient

from atlas.server.app import create_app
from atlas.server.deps import create_engine_set, EventBus
from atlas.server.ws import WebSocketManager, mount_websocket


@pytest.fixture
def full_app(tmp_path):
    """Create a fully wired app with WebSocket support."""
    for d in ["wiki/projects", "wiki/concepts", "wiki/decisions", "wiki/sources", "raw/untracked", "raw/ingested"]:
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "wiki" / "index.md").write_text("# Wiki Index\n")

    engines = create_engine_set(tmp_path)
    event_bus = EventBus()
    app = create_app(engines=engines, event_bus=event_bus)

    ws_manager = WebSocketManager()
    mount_websocket(app, ws_manager, event_bus)

    return app, engines, event_bus, tmp_path


def test_full_lifecycle(full_app):
    """Test the complete lifecycle: write wiki, scan, query, audit."""
    app, engines, event_bus, root = full_app
    client = TestClient(app)

    # 1. Health check
    resp = client.get("/health")
    assert resp.status_code == 200

    # 2. Write wiki pages
    client.post("/api/wiki/write", json={
        "page": "wiki/concepts/auth.md",
        "content": "# Auth\n\nJWT-based auth. See [[billing]].",
        "frontmatter": {"type": "wiki-concept", "title": "Auth", "confidence": "high", "tags": ["auth"]},
    })
    client.post("/api/wiki/write", json={
        "page": "wiki/concepts/billing.md",
        "content": "# Billing\n\nStripe integration. See [[auth]].",
        "frontmatter": {"type": "wiki-concept", "title": "Billing", "confidence": "medium"},
    })

    # 3. Verify pages exist
    resp = client.post("/api/wiki/read", json={"page": "wiki/concepts/auth.md"})
    assert resp.json()["page"]["title"] == "Auth"

    # 4. Search wiki
    resp = client.post("/api/wiki/search", json={"terms": "JWT"})
    assert len(resp.json()["results"]) >= 1

    # 5. Check stats (graph should have nodes from wiki sync)
    resp = client.get("/api/stats")
    stats = resp.json()["stats"]
    assert stats["nodes"] >= 2

    # 6. Query the graph
    resp = client.post("/api/query", json={"question": "auth", "mode": "bfs", "depth": 2})
    assert len(resp.json()["nodes"]) >= 1

    # 7. Find path
    resp = client.post("/api/path", json={"source": "auth", "target": "billing"})
    assert resp.json()["found"] is True

    # 8. Explain concept
    resp = client.post("/api/explain", json={"concept": "auth"})
    assert resp.json()["label"] == "Auth"

    # 9. God nodes
    resp = client.post("/api/god-nodes", json={})
    assert len(resp.json()["nodes"]) >= 1

    # 10. Surprises
    resp = client.post("/api/surprises", json={})
    assert resp.status_code == 200

    # 11. Audit
    resp = client.get("/api/audit")
    audit = resp.json()
    assert audit["stats"]["nodes"] >= 2
    assert "health_score" in audit

    # 12. Suggest links
    resp = client.get("/api/suggest-links")
    assert "suggestions" in resp.json()

    # 13. Scan a Python file
    src = root / "raw" / "untracked" / "scanner_test.py"
    src.write_text("class Scanner:\n    def scan(self): pass\n")
    resp = client.post("/api/scan", json={"path": str(root / "raw" / "untracked")})
    assert resp.json()["nodes_found"] >= 1

    # 14. Stats should reflect new nodes
    resp = client.get("/api/stats")
    assert resp.json()["stats"]["nodes"] > 2

    # 15. Ingest a local file
    (root / "raw" / "untracked" / "notes.md").write_text("# Notes\n\nUseful notes.")
    resp = client.post("/api/ingest", json={"file_path": "raw/untracked/notes.md", "title": "Notes"})
    assert resp.json()["path"] is not None


def test_websocket_connect_in_lifecycle(full_app):
    """Test WebSocket connects and receives welcome in the full app context."""
    app, engines, event_bus, root = full_app
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        welcome = ws.receive_json()
        assert welcome["type"] == "connected"
        assert "message" in welcome


def test_mcp_tool_handler_matches_rest(full_app):
    """Verify MCP tool handlers produce equivalent results to REST routes."""
    app, engines, event_bus, root = full_app
    client = TestClient(app)
    from atlas.server.mcp import handle_tool_call

    # Write wiki pages via REST
    client.post("/api/wiki/write", json={
        "page": "wiki/concepts/auth.md",
        "content": "# Auth\n\nJWT auth.",
        "frontmatter": {"type": "wiki-concept", "title": "Auth"},
    })

    # Compare REST stats vs MCP stats
    rest_stats = client.get("/api/stats").json()["stats"]
    mcp_stats = handle_tool_call("atlas.stats", {}, engines=engines, event_bus=event_bus)
    assert rest_stats["nodes"] == mcp_stats["nodes"]
    assert rest_stats["edges"] == mcp_stats["edges"]

    # Compare REST wiki.read vs MCP wiki.read
    rest_page = client.post("/api/wiki/read", json={"page": "wiki/concepts/auth.md"}).json()["page"]
    mcp_page = handle_tool_call("atlas.wiki.read", {"page": "wiki/concepts/auth.md"}, engines=engines, event_bus=event_bus)
    assert rest_page["title"] == mcp_page["title"]
    assert rest_page["content"] == mcp_page["content"]
