"""Storage abstraction — local filesystem for standalone, cloud for ARA."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for storage backends. Core engine calls this, never touches filesystem directly."""

    def read(self, path: str) -> str | None: ...
    def write(self, path: str, content: str) -> None: ...
    def list(self, prefix: str, exclude_prefix: str | None = None) -> list[str]: ...
    def delete(self, path: str) -> None: ...
    def exists(self, path: str) -> bool: ...
    def mtime(self, path: str) -> float: ...
    def hash(self, path: str) -> str | None: ...


class LocalStorage:
    """Local filesystem storage backend."""

    def __init__(self, root: Path | str):
        self.root = Path(root)

    def _resolve(self, path: str) -> Path:
        return self.root / path

    def read(self, path: str) -> str | None:
        p = self._resolve(path)
        if not p.is_file():
            return None
        return p.read_text(encoding="utf-8")

    def write(self, path: str, content: str) -> None:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def list(self, prefix: str, exclude_prefix: str | None = None) -> list[str]:
        d = self._resolve(prefix)
        if not d.is_dir():
            return []
        results = []
        for f in sorted(d.iterdir()):
            if not f.is_file() or not f.suffix == ".md":
                continue
            if exclude_prefix and f.name.startswith(exclude_prefix):
                continue
            results.append(f"{prefix}{f.name}")
        return results

    def delete(self, path: str) -> None:
        p = self._resolve(path)
        if p.is_file():
            p.unlink()

    def exists(self, path: str) -> bool:
        return self._resolve(path).is_file()

    def mtime(self, path: str) -> float:
        p = self._resolve(path)
        return p.stat().st_mtime if p.is_file() else 0.0

    def hash(self, path: str) -> str | None:
        p = self._resolve(path)
        if not p.is_file():
            return None
        return hashlib.sha256(p.read_bytes()).hexdigest()
