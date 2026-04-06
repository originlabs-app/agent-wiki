import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(seeded_engines, event_bus):
    from atlas.server.app import create_app
    app = create_app(engines=seeded_engines, event_bus=event_bus)
    return TestClient(app)


def test_audit(client):
    resp = client.get("/api/audit")
    assert resp.status_code == 200
    body = resp.json()
    assert "orphan_pages" in body
    assert "god_nodes" in body
    assert "broken_links" in body
    assert "stale_pages" in body
    assert "stats" in body
    assert "health_score" in body
    assert body["stats"]["nodes"] >= 3


def test_audit_god_nodes_structure(client):
    resp = client.get("/api/audit")
    body = resp.json()
    for god in body["god_nodes"]:
        assert "id" in god
        assert "degree" in god


def test_audit_broken_links_structure(client):
    resp = client.get("/api/audit")
    body = resp.json()
    for bl in body["broken_links"]:
        assert "page" in bl
        assert "link" in bl


def test_suggest_links(client):
    resp = client.get("/api/suggest-links")
    assert resp.status_code == 200
    body = resp.json()
    assert "suggestions" in body
    assert isinstance(body["suggestions"], list)


def test_suggest_links_structure(client):
    resp = client.get("/api/suggest-links")
    body = resp.json()
    for s in body["suggestions"]:
        assert "type" in s
        assert "description" in s


def test_audit_after_adding_orphan(client, seeded_engines):
    seeded_engines.wiki.write(
        "wiki/concepts/orphan.md",
        "# Orphan\n\nThis page has no incoming links.",
        frontmatter={"type": "wiki-concept", "title": "Orphan"},
    )
    seeded_engines.linker.sync_wiki_to_graph()

    resp = client.get("/api/audit")
    body = resp.json()
    orphan_paths = body["orphan_pages"]
    assert "wiki/concepts/orphan.md" in orphan_paths


def test_audit_stale_page(client, seeded_engines):
    seeded_engines.wiki.write(
        "wiki/concepts/old.md",
        "# Old Concept",
        frontmatter={"type": "wiki-concept", "title": "Old", "updated": "2025-01-01"},
    )
    seeded_engines.linker.sync_wiki_to_graph()

    resp = client.get("/api/audit")
    body = resp.json()
    assert "wiki/concepts/old.md" in body["stale_pages"]
