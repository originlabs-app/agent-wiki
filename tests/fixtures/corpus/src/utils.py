"""Utility functions shared across modules."""
from __future__ import annotations

import hashlib
import time


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix and timestamp."""
    ts = int(time.time() * 1000)
    raw = f"{prefix}-{ts}-{hashlib.md5(str(ts).encode()).hexdigest()[:8]}"
    return raw


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    import re
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]


def hash_file(path: str) -> str:
    """SHA256 hash of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def truncated(text: str, max_len: int = 200, suffix: str = "...") -> str:
    """Truncate text to max_len characters with an optional suffix."""
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)] + suffix
