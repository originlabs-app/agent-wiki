import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(seeded_engines, event_bus):
    from atlas.server.app import create_app
    app = create_app(engines=seeded_engines, event_bus=event_bus)
    return TestClient(app)


def test_query_bfs(client):
    resp = client.post("/api/query", json={"question": "auth", "mode": "bfs", "depth": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) >= 1
    assert "estimated_tokens" in body


def test_query_dfs(client):
    resp = client.post("/api/query", json={"question": "billing", "mode": "dfs", "depth": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) >= 1


def test_query_nonexistent_node(client):
    resp = client.post("/api/query", json={"question": "nonexistent_xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["nodes"] == []
    assert body["edges"] == []


def test_path_exists(client):
    resp = client.post("/api/path", json={"source": "auth", "target": "billing"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert len(body["edges"]) >= 1


def test_path_not_found(client):
    resp = client.post("/api/path", json={"source": "auth", "target": "nonexistent_xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert body["edges"] == []


def test_explain(client):
    resp = client.post("/api/explain", json={"concept": "auth"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["concept"] == "auth"
    assert body["label"] == "Authentication"
    assert len(body["neighbors"]) >= 1
    assert len(body["edges"]) >= 1


def test_explain_not_found(client):
    resp = client.post("/api/explain", json={"concept": "nonexistent_xyz"})
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "not_found"


def test_god_nodes(client):
    resp = client.post("/api/god-nodes", json={"top_n": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) >= 1
    first = body["nodes"][0]
    assert "id" in first
    assert "label" in first
    assert "degree" in first


def test_god_nodes_default(client):
    resp = client.post("/api/god-nodes", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) >= 1


def test_surprises(client):
    resp = client.post("/api/surprises", json={"top_n": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["edges"], list)


def test_surprises_default(client):
    resp = client.post("/api/surprises", json={})
    assert resp.status_code == 200
