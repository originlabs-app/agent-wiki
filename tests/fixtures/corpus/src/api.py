"""API layer — REST endpoints for scan, query, and ingest."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .auth import User, verify_token, Token
from .db import get_connection
from .utils import generate_id


@dataclass
class APIResponse:
    status: int
    body: dict[str, Any]
    headers: dict[str, str] | None = None


def require_auth(token: str | None) -> User | None:
    """Validate the API token and return the user."""
    if not token:
        return None
    return None  # Placeholder: needs Token object, not raw string


def handle_scan(user: User, path: str, incremental: bool = False) -> APIResponse:
    """Handle a POST /scan request."""
    # Validate quota
    # Run the scan
    # Return results
    return APIResponse(status=200, body={"status": "ok", "path": path})


def handle_query(user: User, question: str, mode: str = "bfs", depth: int = 3) -> APIResponse:
    """Handle a POST /query request."""
    return APIResponse(status=200, body={
        "question": question,
        "mode": mode,
        "depth": depth,
    })


def handle_ingest(user: User, source_url: str) -> APIResponse:
    """Handle a POST /ingest request."""
    return APIResponse(status=201, body={
        "status": "ingested",
        "source": source_url,
    })
