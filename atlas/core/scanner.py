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
    """Coordinates extraction across file types with optional caching."""

    def __init__(self, storage: StorageBackend, cache: CacheEngine | None = None):
        self.storage = storage
        self.cache = cache

    def scan(self, path: Path, incremental: bool = False) -> Extraction:
        """Scan a directory, extract nodes and edges from all supported files.

        If incremental=True and cache is available, only re-extract changed files.
        """
        files = self._collect_files(path)

        if incremental and self.cache:
            rel_paths = [str(f.relative_to(self.storage.root)) if f.is_relative_to(self.storage.root) else str(f) for f in files]
            changed = set(self.cache.detect_changed(rel_paths))
        else:
            changed = None  # process all

        merged = Extraction()

        for file_path in files:
            rel = str(file_path.relative_to(self.storage.root)) if file_path.is_relative_to(self.storage.root) else str(file_path)

            # Check cache first
            if self.cache and changed is not None and rel not in changed:
                cached = self.cache.check(rel)
                if cached:
                    merged = merged.merge(cached)
                    continue

            # Extract
            extraction = self._extract_file(file_path)
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

    def _collect_files(self, path: Path) -> list[Path]:
        if not path.is_dir():
            return [path] if path.is_file() else []
        valid_extensions = CODE_EXTENSIONS | DOC_EXTENSIONS | IMAGE_EXTENSIONS | {".pdf"}
        files = []
        for f in sorted(path.rglob("*")):
            if f.is_file() and f.suffix.lower() in valid_extensions:
                if not any(part.startswith(".") for part in f.relative_to(path).parts):
                    files.append(f)
        return files
