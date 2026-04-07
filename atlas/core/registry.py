"""Project registry — CRUD on ~/.atlas/projects.json."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_MAX_PROJECTS = 20


@dataclass
class ProjectEntry:
    """One registered project."""
    path: str
    name: str
    last_opened: str = ""
    nodes: int = 0
    edges: int = 0
    communities: int = 0
    health: float = 0.0

    def __post_init__(self):
        if not self.last_opened:
            self.last_opened = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectEntry:
        return cls(
            path=data["path"],
            name=data["name"],
            last_opened=data.get("last_opened", ""),
            nodes=data.get("nodes", 0),
            edges=data.get("edges", 0),
            communities=data.get("communities", 0),
            health=data.get("health", 0.0),
        )


class ProjectRegistry:
    """Manages ~/.atlas/projects.json — the global list of known projects."""

    def __init__(self, config_dir: Path | str | None = None):
        if config_dir is None:
            config_dir = Path.home() / ".atlas"
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._file = self._config_dir / "projects.json"
        self._projects: list[ProjectEntry] = self._load()

    def _load(self) -> list[ProjectEntry]:
        if not self._file.exists():
            return []
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            return [ProjectEntry.from_dict(d) for d in raw]
        except (json.JSONDecodeError, KeyError):
            return []

    def _save(self) -> None:
        self._file.write_text(
            json.dumps([p.to_dict() for p in self._projects], indent=2),
            encoding="utf-8",
        )

    def list(self) -> list[ProjectEntry]:
        """Return all projects sorted by last_opened descending, capped at _MAX_PROJECTS."""
        sorted_projects = sorted(self._projects, key=lambda p: p.last_opened, reverse=True)
        return sorted_projects[:_MAX_PROJECTS]

    def get(self, path: str) -> ProjectEntry | None:
        """Get a project by its absolute path."""
        resolved = str(Path(path).resolve())
        for p in self._projects:
            if p.path == resolved:
                return p
        return None

    def register(
        self,
        path: str,
        *,
        nodes: int = 0,
        edges: int = 0,
        communities: int = 0,
        health: float = 0.0,
    ) -> ProjectEntry:
        """Register a project or update its last_opened timestamp.

        If the project is already registered, updates last_opened and optionally stats.
        If new, creates the entry. Always persists to disk.
        """
        resolved = str(Path(path).resolve())
        name = Path(resolved).name

        existing = self.get(resolved)
        if existing is not None:
            existing.last_opened = datetime.now(timezone.utc).isoformat()
            if nodes:
                existing.nodes = nodes
            if edges:
                existing.edges = edges
            if communities:
                existing.communities = communities
            if health:
                existing.health = health
            self._save()
            return existing

        entry = ProjectEntry(
            path=resolved,
            name=name,
            nodes=nodes,
            edges=edges,
            communities=communities,
            health=health,
        )
        self._projects.append(entry)
        # Enforce cap: drop oldest if over limit
        if len(self._projects) > _MAX_PROJECTS:
            self._projects.sort(key=lambda p: p.last_opened, reverse=True)
            self._projects = self._projects[:_MAX_PROJECTS]
        self._save()
        return entry

    def remove(self, path: str) -> bool:
        """Unregister a project. Returns True if found and removed."""
        resolved = str(Path(path).resolve())
        before = len(self._projects)
        self._projects = [p for p in self._projects if p.path != resolved]
        if len(self._projects) < before:
            self._save()
            return True
        return False

    def update_stats(
        self,
        path: str,
        *,
        nodes: int | None = None,
        edges: int | None = None,
        communities: int | None = None,
        health: float | None = None,
    ) -> None:
        """Update graph stats for a registered project."""
        entry = self.get(path)
        if entry is None:
            return
        if nodes is not None:
            entry.nodes = nodes
        if edges is not None:
            entry.edges = edges
        if communities is not None:
            entry.communities = communities
        if health is not None:
            entry.health = health
        self._save()

    def needs_rescan(self, path: str) -> bool:
        """Check if a project needs L0+L1 rescan.

        Returns True if:
        - graph.json doesn't exist
        - manifest.json doesn't exist (never fully scanned)
        - Any file in the project has a newer mtime than the manifest records
        """
        project_dir = Path(path).resolve()
        graph_path = project_dir / "atlas-out" / "graph.json"
        if not graph_path.exists():
            return True

        manifest_path = project_dir / "atlas-out" / "manifest.json"
        if not manifest_path.exists():
            # Also check atlas-cache/manifest.json (current location)
            manifest_path = project_dir / "atlas-cache" / "manifest.json"
            if not manifest_path.exists():
                return True

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return True

        # Quick check: are any manifest entries stale?
        for file_path, entry in manifest.items():
            full_path = project_dir / file_path
            if not full_path.exists():
                continue
            current_mtime = full_path.stat().st_mtime
            if current_mtime > entry.get("mtime", 0):
                return True

        return False
