"""Semantic extraction via LLM for docs, PDFs, and images.

This is a stub — full implementation requires LLM integration (Claude/GPT).
For now, it extracts basic structure from markdown files.
"""
from __future__ import annotations

import re
from pathlib import Path

from atlas.core.models import Edge, Extraction, Node

_HEADING_RE = re.compile(r"^#+\s+(.+)$", re.MULTILINE)
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def extract_markdown(path: Path) -> Extraction:
    """Extract nodes and edges from a markdown file.

    Basic extraction: file node, heading concepts, wikilinks as edges.
    Full LLM extraction will be added when the server squad integrates Claude.
    """
    if not path.is_file():
        return Extraction()

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return Extraction()

    stem = path.stem
    nodes: list[Node] = []
    edges: list[Edge] = []

    # File node
    file_id = stem
    nodes.append(Node(id=file_id, label=path.name, type="document", source_file=str(path)))

    # Extract headings as concept nodes
    for match in _HEADING_RE.finditer(content):
        heading = match.group(1).strip()
        heading_id = f"{stem}_{re.sub(r'[^a-z0-9]+', '_', heading.lower()).strip('_')}"
        if heading_id != file_id:
            nodes.append(Node(id=heading_id, label=heading, type="document", source_file=str(path)))
            edges.append(Edge(source=file_id, target=heading_id, relation="contains", confidence="EXTRACTED"))

    # Extract wikilinks as edges (deduplicated by target)
    seen_targets: set[str] = set()
    for match in _WIKILINK_RE.finditer(content):
        target = match.group(1)
        target_slug = target.rsplit("/", 1)[-1].removesuffix(".md")
        target_id = re.sub(r"[^a-z0-9]+", "_", target_slug.lower()).strip("_")
        if target_id != file_id and target_id not in seen_targets:
            seen_targets.add(target_id)
            edges.append(Edge(source=file_id, target=target_id, relation="references", confidence="EXTRACTED"))

    return Extraction(nodes=nodes, edges=edges, source_file=str(path))
