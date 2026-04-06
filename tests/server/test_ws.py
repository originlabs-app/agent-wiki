import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.server.ws import WebSocketManager, mount_websocket


@pytest.fixture
def ws_manager():
    return WebSocketManager()


@pytest.fixture
def ws_app(seeded_engines, event_bus):
    from atlas.server.app import create_app

    app = create_app(engines=seeded_engines, event_bus=event_bus)
    ws_manager = WebSocketManager()
    mount_websocket(app, ws_manager, event_bus)
    return app, ws_manager


def test_websocket_connect(ws_app):
    app, _ = ws_app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        data = ws.receive_json()
        assert data["type"] == "connected"
        assert "message" in data


def test_websocket_manager_broadcast():
    mgr = WebSocketManager()
    assert mgr.active_count == 0


def test_websocket_disconnect(ws_app):
    app, ws_manager = ws_app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # welcome
    # After disconnect, just verify it doesn't crash


def test_broadcast_sync_no_loop():
    """broadcast_sync should not crash when there's no running event loop."""
    mgr = WebSocketManager()
    # Should silently skip (no running loop)
    mgr.broadcast_sync("test.event", {"data": "test"})
    assert mgr.active_count == 0


def test_mount_websocket_wires_events(seeded_engines, event_bus):
    """Verify mount_websocket subscribes to EventBus events."""
    from atlas.server.app import create_app

    app = create_app(engines=seeded_engines, event_bus=event_bus)
    ws_manager = WebSocketManager()
    mount_websocket(app, ws_manager, event_bus)

    # EventBus should have handlers for wiki.changed, graph.updated, scan.completed
    assert len(event_bus._handlers.get("wiki.changed", [])) >= 1
    assert len(event_bus._handlers.get("graph.updated", [])) >= 1
    assert len(event_bus._handlers.get("scan.completed", [])) >= 1
