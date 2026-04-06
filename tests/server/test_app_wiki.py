import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(seeded_engines, event_bus):
    from atlas.server.app import create_app
    app = create_app(engines=seeded_engines, event_bus=event_bus)
    return TestClient(app)


def test_wiki_read_existing(client):
    resp = client.post("/api/wiki/read", json={"page": "wiki/concepts/auth.md"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] is not None
    assert body["page"]["title"] == "Authentication"
    assert "JWT" in body["page"]["content"]
    assert "billing" in body["page"]["wikilinks"]


def test_wiki_read_nonexistent(client):
    resp = client.post("/api/wiki/read", json={"page": "wiki/concepts/nonexistent.md"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] is None


def test_wiki_write_new_page(client, seeded_engines, event_bus):
    received = []
    event_bus.subscribe("wiki.changed", lambda e: received.append(e))

    resp = client.post("/api/wiki/write", json={
        "page": "wiki/concepts/caching.md",
        "content": "# Caching\n\nRedis caching layer. See [[auth]].",
        "frontmatter": {"type": "wiki-concept", "title": "Caching", "confidence": "medium", "tags": ["cache"]},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == "wiki/concepts/caching.md"
    assert body["message"] == "Page saved"

    read_resp = client.post("/api/wiki/read", json={"page": "wiki/concepts/caching.md"})
    assert read_resp.json()["page"]["title"] == "Caching"

    assert len(received) >= 1
    assert received[0]["page"] == "wiki/concepts/caching.md"


def test_wiki_write_updates_graph(client, seeded_engines):
    client.post("/api/wiki/write", json={
        "page": "wiki/concepts/sessions.md",
        "content": "# Sessions\n\nSession management. See [[auth]].",
        "frontmatter": {"type": "wiki-concept", "title": "Sessions"},
    })

    node = seeded_engines.graph.get_node("sessions")
    assert node is not None
    assert node.label == "Sessions"


def test_wiki_search(client):
    resp = client.post("/api/wiki/search", json={"terms": "JWT"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) >= 1
    assert any(p["title"] == "Authentication" for p in body["results"])


def test_wiki_search_no_results(client):
    resp = client.post("/api/wiki/search", json={"terms": "nonexistent_term_xyz_123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"] == []
