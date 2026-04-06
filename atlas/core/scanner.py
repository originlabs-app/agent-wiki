"""Scanner coordinator — dispatches to AST or semantic extractors based on file type."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from atlas.core.models import Extraction
from atlas.core.scanner_ast import extract_python
from atlas.core.scanner_semantic import extract_markdown

if TYPE_CHECKING:
    from atlas.core.cache import CacheEngine
    from atlas.core.storage import StorageBackend

CODE_EXTENSIONS = {".py", ".ts", ".js", ".go", ".rs", ".java", ".c", ".cpp", ".rb", ".cs", ".kt", ".scala", ".php"}
DOC_EXTENSIONS = {".md", ".txt", ".rst"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALL_EXTENSIONS = CODE_EXTENSIONS | DOC_EXTENSIONS | IMAGE_EXTENSIONS | {".pdf"}

# Map extensions to extractors (expand as more languages are added)
_AST_EXTRACTORS = {
    ".py": extract_python,
    # ".ts": extract_typescript,  # TODO: add with tree-sitter
    # ".js": extract_javascript,
    # ".go": extract_go,
}

_SEMANTIC_EXTRACTORS = {
    ".md": extract_markdown,
    ".txt": extract_markdown,  # treat .txt as markdown
}


class Scanner:
    """Coordinates extraction across file types with optional caching.

    Uses storage.walk() for file discovery — works with any StorageBackend,
    not just local filesystem.
    """

    def __init__(self, storage: StorageBackend, cache: CacheEngine | None = None):
        self.storage = storage
        self.cache = cache

    def scan(self, path: Path | str, incremental: bool = False) -> Extraction:
        """Scan a directory, extract nodes and edges from all supported files.

        Args:
            path: Directory to scan. Can be a Path object or a string prefix
                  relative to the storage root.
            incremental: If True and cache is available, only re-extract changed files.
        """
        # Normalize to a relative prefix string for storage.walk()
        prefix = self._normalize_prefix(path)
        rel_paths = self.storage.walk(prefix, suffixes=ALL_EXTENSIONS)

        if incremental and self.cache:
            changed = set(self.cache.detect_changed(rel_paths))
        else:
            changed = None  # process all

        merged = Extraction()

        for rel in rel_paths:
            # Check cache first
            if self.cache and changed is not None and rel not in changed:
                cached = self.cache.check(rel)
                if cached:
                    merged = merged.merge(cached)
                    continue

            # Extract — resolve to absolute path for extractors that need filesystem access
            abs_path = Path(self.storage.root) / rel if hasattr(self.storage, "root") else Path(rel)
            extraction = self._extract_file(abs_path)
            if extraction.nodes:
                merged = merged.merge(extraction)
                if self.cache:
                    self.cache.save(rel, extraction)

        return merged

    def _extract_file(self, path: Path) -> Extraction:
        suffix = path.suffix.lower()
        extractor = _AST_EXTRACTORS.get(suffix) or _SEMANTIC_EXTRACTORS.get(suffix)
        if extractor:
            return extractor(path)
        return Extraction()

    def _normalize_prefix(self, path: Path | str) -> str:
        """Convert a Path or string to a relative prefix suitable for storage.walk()."""
        p = Path(path)
        if hasattr(self.storage, "root"):
            root = Path(self.storage.root).resolve()
            resolved = p.resolve()
            if resolved.is_relative_to(root):
                rel = str(resolved.relative_to(root))
                return rel + "/" if not rel.endswith("/") else rel
        # Already a relative string prefix
        s = str(path)
        return s if s.endswith("/") else s + "/"
