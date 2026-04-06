"""Smart URL and file ingestion with type detection and frontmatter."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from atlas.core.storage import StorageBackend


def detect_url_type(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path.lower()

    if "arxiv.org" in host:
        return "arxiv"
    if host in ("x.com", "twitter.com") and "/status/" in path:
        return "tweet"
    if "github.com" in host:
        return "github"
    if path.endswith(".pdf"):
        return "pdf"
    if any(path.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return "image"
    return "webpage"


def slugify_url(url: str) -> str:
    parsed = urlparse(url)
    raw = f"{parsed.hostname or ''}{parsed.path}".strip("/")
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")[:80]


def build_frontmatter(
    url: str,
    url_type: str,
    title: str | None = None,
    author: str | None = None,
    contributor: str | None = None,
) -> dict:
    fm: dict = {
        "source_url": url,
        "type": url_type,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    if title:
        fm["title"] = title
    if author:
        fm["author"] = author
    if contributor:
        fm["contributor"] = contributor
    return fm


class IngestEngine:
    """Ingests URLs and local files into raw/ with frontmatter."""

    def __init__(self, storage: StorageBackend):
        self.storage = storage

    def ingest_file(self, source_path: str, title: str | None = None) -> str | None:
        """Move a local file from raw/untracked/ to raw/ingested/ with frontmatter."""
        content = self.storage.read(source_path)
        if content is None:
            return None

        slug = source_path.rsplit("/", 1)[-1].removesuffix(".md")
        date = datetime.now().strftime("%Y-%m-%d")
        dest_path = f"raw/ingested/{date}-{slug}.md"

        # Add frontmatter if not present
        if not content.startswith("---"):
            fm = f'---\ntitle: "{title or slug}"\ncaptured_at: {datetime.now(timezone.utc).isoformat()}\n---\n\n'
            content = fm + content

        self.storage.write(dest_path, content)
        return dest_path

    async def ingest_url(self, url: str, title: str | None = None, author: str | None = None) -> str | None:
        """Fetch a URL and save to raw/ingested/ with auto-detected frontmatter.

        Requires httpx. Returns the path of the saved file, or None on failure.
        """
        import httpx

        url_type = detect_url_type(url)
        slug = slugify_url(url)
        date = datetime.now().strftime("%Y-%m-%d")
        dest_path = f"raw/ingested/{date}-{slug}.md"

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException):
            return None

        text = resp.text
        fm = build_frontmatter(url=url, url_type=url_type, title=title, author=author)
        fm_lines = ["---"]
        for k, v in fm.items():
            fm_lines.append(f'{k}: "{v}"' if isinstance(v, str) else f"{k}: {v}")
        fm_lines.append("---\n")
        full = "\n".join(fm_lines) + "\n" + text

        self.storage.write(dest_path, full)
        return dest_path
