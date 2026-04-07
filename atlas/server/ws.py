"""WebSocket manager — live updates when wiki or graph changes."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, TYPE_CHECKING

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from atlas.server.deps import EventBus

logger = logging.getLogger("atlas.server.ws")


class WebSocketManager:
    """Manages active WebSocket connections and broadcasts events."""

    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WebSocket connected. Active: %d", self.active_count)
        await ws.send_json({"type": "connected", "message": "Atlas WebSocket connected", "active": self.active_count})

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)
        logger.info("WebSocket disconnected. Active: %d", self.active_count)

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Send an event to all connected WebSocket clients."""
        message = json.dumps({"type": event_type, "data": data})
        dead: list[WebSocket] = []

        async with self._lock:
            connections = list(self._connections)

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self._connections:
                        self._connections.remove(ws)

    def broadcast_sync(self, event_type: str, data: dict[str, Any]) -> None:
        """Synchronous wrapper for broadcast — used from EventBus handlers.

        Gets or creates an event loop and schedules the broadcast.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event_type, data))
        except RuntimeError:
            # No running loop — skip broadcast (happens in sync test context)
            pass


def mount_websocket(app: FastAPI, manager: WebSocketManager, event_bus: EventBus) -> None:
    """Add the /ws endpoint and wire EventBus -> WebSocket broadcasting."""

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await manager.connect(ws)
        try:
            while True:
                data = await ws.receive_text()
                await ws.send_json({"type": "ack", "received": data})
        except WebSocketDisconnect:
            await manager.disconnect(ws)
        except Exception:
            await manager.disconnect(ws)

    # Wire EventBus events to WebSocket broadcasts
    for event in ("wiki.changed", "graph.updated", "scan.completed", "project.switched", "scan.progress"):
        event_bus.subscribe(event, lambda data, evt=event: manager.broadcast_sync(evt, data))
