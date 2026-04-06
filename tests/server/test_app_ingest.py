import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(engines, event_bus, engine_root):
    from atlas.server.app import create_app
    app = create_app(engines=engines, event_bus=event_bus)
    return TestClient(app)


def test_ingest_local_file(client, engine_root, engines):
    src = engine_root / "raw" / "untracked" / "notes.md"
    src.write_text("# My Notes\n\nSome content about architecture.")

    resp = client.post("/api/ingest", json={
        "file_path": "raw/untracked/notes.md",
        "title": "My Notes",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["path"] is not None
    assert body["path"].startswith("raw/ingested/")
    assert body["message"] == "Ingested"


def test_ingest_local_file_not_found(client):
    resp = client.post("/api/ingest", json={
        "file_path": "raw/untracked/nonexistent.md",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["path"] is None


def test_ingest_no_source(client):
    resp = client.post("/api/ingest", json={})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "validation_error"


def test_ingest_emits_event(engines, event_bus, engine_root):
    from atlas.server.app import create_app

    received = []
    event_bus.subscribe("wiki.changed", lambda e: received.append(e))

    app = create_app(engines=engines, event_bus=event_bus)
    client = TestClient(app)

    src = engine_root / "raw" / "untracked" / "event_test.md"
    src.write_text("# Event Test\n\nContent.")

    client.post("/api/ingest", json={"file_path": "raw/untracked/event_test.md"})
    assert len(received) >= 1
    assert received[0]["action"] == "ingest"
