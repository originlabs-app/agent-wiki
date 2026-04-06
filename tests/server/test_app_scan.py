import pytest
from fastapi.testclient import TestClient
from pathlib import Path


@pytest.fixture
def client(engines, event_bus):
    from atlas.server.app import create_app
    app = create_app(engines=engines, event_bus=event_bus)
    return TestClient(app)


@pytest.fixture
def seeded_client(seeded_engines, event_bus):
    from atlas.server.app import create_app
    app = create_app(engines=seeded_engines, event_bus=event_bus)
    return TestClient(app)


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_scan_endpoint(client, engine_root):
    src = engine_root / "raw" / "untracked" / "sample.py"
    src.write_text("class Foo:\n    pass\n")

    resp = client.post("/api/scan", json={"path": str(engine_root / "raw" / "untracked")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["nodes_found"] >= 1
    assert body["message"] == "Scan complete"


def test_scan_nonexistent_path(client):
    resp = client.post("/api/scan", json={"path": "/nonexistent/path/xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["nodes_found"] == 0


def test_scan_incremental(client, engine_root):
    src = engine_root / "raw" / "untracked" / "code.py"
    src.write_text("def hello(): pass")

    resp1 = client.post("/api/scan", json={"path": str(engine_root / "raw" / "untracked")})
    assert resp1.status_code == 200

    resp2 = client.post("/api/scan", json={"path": str(engine_root / "raw" / "untracked"), "incremental": True})
    assert resp2.status_code == 200


def test_stats_endpoint(seeded_client):
    resp = seeded_client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    stats = body["stats"]
    assert stats["nodes"] >= 3
    assert isinstance(stats["communities"], int)
    assert isinstance(stats["confidence_breakdown"], dict)


def test_scan_emits_event(engines, event_bus, engine_root):
    from atlas.server.app import create_app

    received = []
    event_bus.subscribe("scan.completed", lambda e: received.append(e))
    event_bus.subscribe("graph.updated", lambda e: received.append(e))

    app = create_app(engines=engines, event_bus=event_bus)
    client = TestClient(app)

    src = engine_root / "raw" / "untracked" / "test.py"
    src.write_text("x = 1")
    client.post("/api/scan", json={"path": str(engine_root / "raw" / "untracked")})

    events = [e.get("event") for e in received if isinstance(e, dict)]
    assert "scan.completed" in events or len(received) > 0
