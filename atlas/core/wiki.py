"""Wiki engine — read, write, search, frontmatter, templates, wikilinks."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml

from atlas.core.models import Page

if TYPE_CHECKING:
    from atlas.core.storage import StorageBackend

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_WIKI_DIRS = ["wiki/projects/", "wiki/concepts/", "wiki/decisions/", "wiki/sources/"]


class WikiEngine:
    """Read, write, search wiki pages through a StorageBackend."""

    def __init__(self, storage: StorageBackend):
        self.storage = storage

    def read(self, path: str) -> Page | None:
        content = self.storage.read(path)
        if content is None:
            return None
        frontmatter, body = self._parse_frontmatter(content)
        title = frontmatter.get("title", path.rsplit("/", 1)[-1].removesuffix(".md"))
        page_type = frontmatter.get("type", "unknown")
        return Page(path=path, title=title, type=page_type, content=content, frontmatter=frontmatter)

    def write(self, path: str, content: str, frontmatter: dict | None = None) -> None:
        if frontmatter:
            fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()
            full = f"---\n{fm_str}\n---\n\n{content}\n"
        else:
            full = content
        self.storage.write(path, full)

    def delete(self, path: str) -> None:
        self.storage.delete(path)

    def list_pages(self, type: str | None = None) -> list[Page]:
        pages = []
        for dir_prefix in _WIKI_DIRS:
            for file_path in self.storage.list(dir_prefix, exclude_prefix="_"):
                page = self.read(file_path)
                if page and (type is None or page.type == type):
                    pages.append(page)
        return pages

    def search(self, terms: str) -> list[Page]:
        terms_lower = terms.lower()
        results = []
        for page in self.list_pages():
            if terms_lower in page.content.lower() or terms_lower in page.title.lower():
                results.append(page)
        return results

    def all_wikilinks(self) -> dict[str, list[str]]:
        result = {}
        for page in self.list_pages():
            links = page.wikilinks
            if links:
                result[page.path] = links
        return result

    def backlinks(self, target: str) -> list[str]:
        target_lower = target.lower()
        result = []
        for page_path, links in self.all_wikilinks().items():
            for link in links:
                link_slug = link.rsplit("/", 1)[-1].removesuffix(".md").lower()
                if link_slug == target_lower or link.lower() == target_lower:
                    result.append(page_path)
                    break
        return result

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[dict, str]:
        m = _FRONTMATTER_RE.match(content)
        if not m:
            return {}, content
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            fm = {}
        body = content[m.end():]
        return fm, body
