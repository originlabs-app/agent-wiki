"""Data models for Atlas core engine."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class NodeType(StrEnum):
    """Valid node types in the knowledge graph."""
    CODE = "code"
    DOCUMENT = "document"
    PAPER = "paper"
    IMAGE = "image"
    WIKI_PAGE = "wiki-page"
    WIKI_CONCEPT = "wiki-concept"
    WIKI_DECISION = "wiki-decision"
    WIKI_SOURCE = "wiki-source"


class Confidence(StrEnum):
    """Confidence levels for nodes and pages."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EdgeConfidence(StrEnum):
    """Confidence levels for edges."""
    EXTRACTED = "EXTRACTED"
    INFERRED = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass
class Node:
    id: str
    label: str
    type: str  # "code" | "document" | "paper" | "image" | "wiki-page" | "wiki-concept" | "wiki-decision" | "wiki-source"
    source_file: str
    source_location: str | None = None
    source_url: str | None = None
    confidence: str = "high"  # "high" | "medium" | "low"
    community: int | None = None
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    captured_at: str | None = None
    author: str | None = None


@dataclass
class Edge:
    source: str
    target: str
    relation: str  # "imports" | "calls" | "references" | "tagged_with" | "semantically_similar_to" | etc.
    confidence: str = "EXTRACTED"  # "EXTRACTED" | "INFERRED" | "AMBIGUOUS"
    confidence_score: float | None = None
    source_file: str | None = None
    weight: float = 1.0

    def __post_init__(self):
        if self.confidence_score is None:
            self.confidence_score = {"EXTRACTED": 1.0, "INFERRED": 0.7, "AMBIGUOUS": 0.2}.get(self.confidence, 0.5)


@dataclass
class Extraction:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    source_file: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0

    def merge(self, other: Extraction) -> Extraction:
        seen_ids = {n.id for n in self.nodes}
        new_nodes = [n for n in other.nodes if n.id not in seen_ids]
        # Deduplicate edges by (source, target, relation), keep higher confidence
        _CONF_RANK = {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}
        edge_map: dict[tuple[str, str, str], Edge] = {}
        for e in self.edges + other.edges:
            key = (e.source, e.target, e.relation)
            existing = edge_map.get(key)
            if existing is None or _CONF_RANK.get(e.confidence, 0) > _CONF_RANK.get(existing.confidence, 0):
                edge_map[key] = e
        return Extraction(
            nodes=self.nodes + new_nodes,
            edges=list(edge_map.values()),
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


@dataclass
class Page:
    path: str
    title: str
    type: str
    content: str
    frontmatter: dict = field(default_factory=dict)

    @property
    def wikilinks(self) -> list[str]:
        return _WIKILINK_RE.findall(self.content)

    @property
    def slug(self) -> str:
        return self.path.rsplit("/", 1)[-1].removesuffix(".md")


@dataclass
class Subgraph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    path_description: str | None = None

    @property
    def estimated_tokens(self) -> int:
        text = "".join(f"{n.id} {n.label} {n.type}" for n in self.nodes)
        text += "".join(f"{e.source} {e.relation} {e.target}" for e in self.edges)
        return max(1, len(text) // 4)


@dataclass
class GraphStats:
    nodes: int
    edges: int
    communities: int
    confidence_breakdown: dict[str, int] = field(default_factory=dict)

    @property
    def health_score(self) -> float:
        total = sum(self.confidence_breakdown.values()) or 1
        extracted = self.confidence_breakdown.get("EXTRACTED", 0)
        ambiguous = self.confidence_breakdown.get("AMBIGUOUS", 0)
        return round((extracted / total) * 100 - (ambiguous / total) * 50, 1)


@dataclass
class WikiSuggestion:
    type: str  # "create_page" | "add_wikilink" | "flag_god_node" | "create_concept" | "clarify_relation" | "contradiction"
    description: str
    target_page: str | None = None
    source_node: str | None = None
    target_node: str | None = None
    reason: str | None = None


@dataclass
class GraphChange:
    type: str  # "add_node" | "remove_node" | "add_edge" | "remove_edge" | "update_node"
    node_id: str | None = None
    edge: Edge | None = None
    details: str | None = None


@dataclass
class LinkSuggestion:
    from_page: str
    to_page: str
    reason: str
    confidence: str = "INFERRED"


@dataclass
class AuditReport:
    orphan_pages: list[str] = field(default_factory=list)
    god_nodes: list[tuple[str, int]] = field(default_factory=list)  # (node_id, degree)
    broken_links: list[tuple[str, str]] = field(default_factory=list)  # (page, broken_link)
    stale_pages: list[str] = field(default_factory=list)
    contradictions: list[dict] = field(default_factory=list)
    missing_links: list[LinkSuggestion] = field(default_factory=list)
    communities: list[dict] = field(default_factory=list)
    stats: GraphStats | None = None
    health_score: float = 0.0
