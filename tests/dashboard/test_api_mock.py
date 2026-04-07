"""Mock API responses that the dashboard expects.
These tests document the API contract the dashboard relies on.
Server squad: implement these endpoints to match."""
import json


# --- Graph API contract ---

def test_graph_response_shape():
    """GET /api/graph returns {nodes: [...], edges: [...]}"""
    response = {
        "nodes": [
            {
                "id": "auth_module",
                "label": "Auth Module",
                "type": "code",
                "source_file": "src/auth.py",
                "confidence": "high",
                "community": 0,
                "summary": "Handles authentication.",
                "tags": ["auth", "security"],
            },
        ],
        "edges": [
            {
                "source": "auth_module",
                "target": "db_client",
                "relation": "imports",
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
            },
        ],
    }
    # Validate shape
    assert isinstance(response["nodes"], list)
    assert isinstance(response["edges"], list)
    node = response["nodes"][0]
    assert all(k in node for k in ["id", "label", "type"])
    edge = response["edges"][0]
    assert all(k in edge for k in ["source", "target", "relation", "confidence"])


def test_graph_stats_response_shape():
    """GET /api/graph/stats returns GraphStats."""
    response = {
        "nodes": 150,
        "edges": 280,
        "communities": 7,
        "confidence_breakdown": {"EXTRACTED": 200, "INFERRED": 60, "AMBIGUOUS": 20},
        "health_score": 72.5,
    }
    assert isinstance(response["confidence_breakdown"], dict)
    assert response["health_score"] > 0


# --- Wiki API contract ---

def test_wiki_pages_response_shape():
    """GET /api/wiki/pages returns page list (no content)."""
    response = [
        {
            "path": "wiki/concepts/auth.md",
            "title": "Auth",
            "type": "wiki-concept",
            "frontmatter": {"tags": ["auth", "security"]},
        },
    ]
    page = response[0]
    assert "content" not in page or page.get("content") is None  # list endpoint omits content


def test_wiki_page_response_shape():
    """GET /api/wiki/page/{slug} returns full page with content."""
    response = {
        "path": "wiki/concepts/auth.md",
        "title": "Auth",
        "type": "wiki-concept",
        "content": "# Auth\n\nAuthentication module.\n\nSee [[billing]].",
        "frontmatter": {"type": "wiki-concept", "title": "Auth", "tags": ["auth"]},
    }
    assert "content" in response
    assert len(response["content"]) > 0


# --- Audit API contract ---

def test_audit_response_shape():
    """GET /api/audit returns AuditReport."""
    response = {
        "orphan_pages": ["wiki/concepts/old.md"],
        "god_nodes": [["auth_module", 15], ["db_client", 12]],
        "broken_links": [["wiki/concepts/auth.md", "nonexistent"]],
        "stale_pages": ["wiki/sources/2025-01-01-old.md"],
        "contradictions": [{"type": "value_conflict", "description": "Page A says X, Page B says Y", "pages": ["a", "b"]}],
        "missing_links": [],
        "communities": [],
        "stats": {"nodes": 150, "edges": 280, "communities": 7, "confidence_breakdown": {}, "health_score": 72.5},
        "health_score": 72.5,
    }
    assert isinstance(response["orphan_pages"], list)
    assert isinstance(response["god_nodes"], list)
    assert isinstance(response["health_score"], (int, float))


# --- Log API contract ---

def test_log_response_shape():
    """GET /api/log returns LogEntry[]."""
    response = [
        {
            "type": "scan",
            "timestamp": "2026-04-06T10:30:00Z",
            "description": "Scanned 42 files in src/",
            "agent": "claude-code",
            "details": {"files_scanned": 42, "nodes_created": 15},
            "affected_pages": ["wiki/concepts/auth.md"],
        },
        {
            "type": "wiki_update",
            "timestamp": "2026-04-06T10:25:00Z",
            "description": "Updated page: Auth",
            "agent": "user",
            "details": None,
            "affected_pages": ["wiki/concepts/auth.md"],
        },
    ]
    entry = response[0]
    assert all(k in entry for k in ["type", "timestamp", "description"])


# --- WebSocket message contract ---

def test_websocket_message_shapes():
    """WebSocket messages follow {type, payload} format."""
    messages = [
        {"type": "graph_update", "payload": {"new_nodes": [], "new_edges": [], "removed_nodes": [], "summary": "Added 3 nodes"}},
        {"type": "wiki_update", "payload": {"page": "wiki/concepts/auth.md"}},
        {"type": "scan_complete", "payload": {"files_scanned": 42, "nodes_created": 15}},
        {"type": "log_entry", "payload": {"type": "scan", "timestamp": "2026-04-06T10:30:00Z", "description": "Scan done"}},
    ]
    for msg in messages:
        assert "type" in msg
        assert "payload" in msg
        # Should be JSON-serializable
        json.dumps(msg)
