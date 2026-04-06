"""SHA256 incremental extraction cache."""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

from atlas.core.models import Extraction, Node, Edge

if TYPE_CHECKING:
    from atlas.core.storage import StorageBackend

MANIFEST_PATH = "atlas-cache/manifest.json"
CACHE_DIR = "atlas-cache/extractions"


class CacheEngine:
    """Content-hash based extraction cache.

    Stores extraction results keyed by SHA256 of the source file content.
    Detects changes by comparing current hash with cached hash.
    """

    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self._manifest = self._load_manifest()

    def check(self, file_path: str) -> Extraction | None:
        current_hash = self.storage.hash(file_path)
        if current_hash is None:
            return None
        entry = self._manifest.get(file_path)
        if entry is None or entry.get("hash") != current_hash:
            return None
        cache_path = f"{CACHE_DIR}/{current_hash}.json"
        cached = self.storage.read(cache_path)
        if cached is None:
            return None
        return self._deserialize(cached)

    def save(self, file_path: str, extraction: Extraction) -> None:
        current_hash = self.storage.hash(file_path)
        if current_hash is None:
            return
        cache_path = f"{CACHE_DIR}/{current_hash}.json"
        self.storage.write(cache_path, self._serialize(extraction))
        self._manifest[file_path] = {
            "hash": current_hash,
            "mtime": self.storage.mtime(file_path),
        }
        self._save_manifest()

    def detect_changed(self, file_paths: list[str]) -> list[str]:
        changed = []
        for fp in file_paths:
            current_hash = self.storage.hash(fp)
            entry = self._manifest.get(fp)
            if entry is None or entry.get("hash") != current_hash:
                changed.append(fp)
        return changed

    def _load_manifest(self) -> dict:
        raw = self.storage.read(MANIFEST_PATH)
        if raw is None:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _save_manifest(self) -> None:
        self.storage.write(MANIFEST_PATH, json.dumps(self._manifest, indent=2))

    @staticmethod
    def _serialize(extraction: Extraction) -> str:
        return json.dumps({
            "nodes": [asdict(n) for n in extraction.nodes],
            "edges": [asdict(e) for e in extraction.edges],
            "input_tokens": extraction.input_tokens,
            "output_tokens": extraction.output_tokens,
        }, ensure_ascii=False, indent=2)

    @staticmethod
    def _deserialize(raw: str) -> Extraction:
        data = json.loads(raw)
        nodes = [Node(**n) for n in data.get("nodes", [])]
        edges = [Edge(**e) for e in data.get("edges", [])]
        return Extraction(
            nodes=nodes,
            edges=edges,
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
        )
