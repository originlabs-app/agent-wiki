"""Pydantic request/response models for the Atlas REST API and MCP server."""
from __future__ import annotations

from pydantic import BaseModel, Field


# --- Shared sub-schemas ---

class NodeSchema(BaseModel):
    id: str
    label: str
    type: str
    source_file: str
    source_location: str | None = None
    source_url: str | None = None
    confidence: str = "high"
    community: int | None = None
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_core(cls, node) -> NodeSchema:
        """Convert atlas.core.models.Node to schema."""
        return cls(
            id=node.id,
            label=node.label,
            type=node.type,
            source_file=node.source_file,
            source_location=node.source_location,
            source_url=node.source_url,
            confidence=node.confidence,
            community=node.community,
            summary=node.summary,
            tags=node.tags or [],
        )


class EdgeSchema(BaseModel):
    source: str
    target: str
    relation: str
    confidence: str = "EXTRACTED"
    confidence_score: float = 1.0
    weight: float = 1.0

    def __init__(self, **data):
        if "confidence_score" not in data or data.get("confidence_score") is None:
            conf = data.get("confidence", "EXTRACTED")
            data["confidence_score"] = {"EXTRACTED": 1.0, "INFERRED": 0.7, "AMBIGUOUS": 0.2}.get(conf, 0.5)
        super().__init__(**data)

    @classmethod
    def from_core(cls, edge) -> EdgeSchema:
        return cls(
            source=edge.source,
            target=edge.target,
            relation=edge.relation,
            confidence=edge.confidence,
            confidence_score=edge.confidence_score or 1.0,
            weight=edge.weight,
        )


class PageSchema(BaseModel):
    path: str
    title: str
    type: str
    content: str
    frontmatter: dict = Field(default_factory=dict)
    wikilinks: list[str] = Field(default_factory=list)

    @classmethod
    def from_core(cls, page) -> PageSchema:
        return cls(
            path=page.path,
            title=page.title,
            type=page.type,
            content=page.content,
            frontmatter=page.frontmatter,
            wikilinks=page.wikilinks,
        )


class LinkSuggestionSchema(BaseModel):
    from_page: str
    to_page: str
    reason: str
    confidence: str = "INFERRED"


class WikiSuggestionSchema(BaseModel):
    type: str
    description: str
    target_page: str | None = None
    source_node: str | None = None
    target_node: str | None = None
    reason: str | None = None


class GraphStatsSchema(BaseModel):
    nodes: int
    edges: int
    communities: int
    confidence_breakdown: dict[str, int] = Field(default_factory=dict)
    health_score: float = 0.0


# --- Request models ---

class ScanRequest(BaseModel):
    path: str
    incremental: bool = False
    force: bool = False


class QueryRequest(BaseModel):
    question: str = ""
    start: str = ""  # alias used by dashboard
    mode: str = "bfs"
    depth: int = 3

    @property
    def effective_question(self) -> str:
        return self.question or self.start


class PathRequest(BaseModel):
    source: str
    target: str


class ExplainRequest(BaseModel):
    concept: str


class GodNodesRequest(BaseModel):
    top_n: int = 10


class SurprisesRequest(BaseModel):
    top_n: int = 10


class WikiReadRequest(BaseModel):
    page: str


class WikiWriteRequest(BaseModel):
    page: str
    content: str
    frontmatter: dict = Field(default_factory=dict)


class WikiSearchRequest(BaseModel):
    terms: str


class IngestRequest(BaseModel):
    url: str | None = None
    file_path: str | None = None
    title: str | None = None
    author: str | None = None


# --- Response models ---

class ScanResponse(BaseModel):
    nodes_found: int
    edges_found: int
    files_scanned: int = 0
    message: str = "Scan complete"


class QueryResponse(BaseModel):
    nodes: list[NodeSchema]
    edges: list[EdgeSchema]
    estimated_tokens: int = 0


class PathResponse(BaseModel):
    edges: list[EdgeSchema]
    found: bool = True


class ExplainResponse(BaseModel):
    concept: str
    label: str
    type: str
    summary: str | None = None
    neighbors: list[NodeSchema]
    edges: list[EdgeSchema]


class GodNodesResponse(BaseModel):
    nodes: list[dict]  # [{id, label, degree}]


class SurprisesResponse(BaseModel):
    edges: list[EdgeSchema]


class StatsResponse(BaseModel):
    stats: GraphStatsSchema


class WikiReadResponse(BaseModel):
    page: PageSchema | None


class WikiWriteResponse(BaseModel):
    page: str
    message: str = "Page saved"


class WikiSearchResponse(BaseModel):
    results: list[PageSchema]


class AuditResponse(BaseModel):
    orphan_pages: list[str] = Field(default_factory=list)
    god_nodes: list[dict] = Field(default_factory=list)
    broken_links: list[dict] = Field(default_factory=list)
    stale_pages: list[str] = Field(default_factory=list)
    contradictions: list[dict] = Field(default_factory=list)
    missing_links: list[LinkSuggestionSchema] = Field(default_factory=list)
    communities: list[dict] = Field(default_factory=list)
    stats: GraphStatsSchema | None = None
    health_score: float = 0.0


class SuggestLinksResponse(BaseModel):
    suggestions: list[WikiSuggestionSchema]


class IngestResponse(BaseModel):
    path: str | None
    message: str = "Ingested"


class FileTreeNode(BaseModel):
    """A node in the file tree (file or directory)."""
    path: str
    name: str
    type: str  # "directory" | node type (code, document, etc.)
    degree: int = 0
    children: list["FileTreeNode"] | None = None  # None for files, list for dirs


class CommunityMemberSchema(BaseModel):
    """A member node within a community."""
    id: str
    label: str
    type: str = "unknown"
    source_file: str = ""
    degree: int = 0


class CommunitySchema(BaseModel):
    """A detected community cluster."""
    id: int
    label: str
    size: int
    cohesion: float = 0.0
    members: list[CommunityMemberSchema] = Field(default_factory=list)


class FileReadResponse(BaseModel):
    """Raw file content response."""
    path: str
    content: str
    type: str  # guessed file type


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


# --- Project management ---


class ProjectEntrySchema(BaseModel):
    path: str
    name: str
    last_opened: str = ""
    nodes: int = 0
    edges: int = 0
    communities: int = 0
    health: float = 0.0

    @classmethod
    def from_registry(cls, entry) -> ProjectEntrySchema:
        """Convert atlas.core.registry.ProjectEntry to schema."""
        return cls(
            path=entry.path,
            name=entry.name,
            last_opened=entry.last_opened,
            nodes=entry.nodes,
            edges=entry.edges,
            communities=entry.communities,
            health=entry.health,
        )


class ProjectOpenRequest(BaseModel):
    path: str


class ProjectOpenResponse(BaseModel):
    project: ProjectEntrySchema
    scanned: bool = False


class ProjectSwitchRequest(BaseModel):
    path: str


class ProjectSwitchResponse(BaseModel):
    project: ProjectEntrySchema


class ProjectRemoveResponse(BaseModel):
    removed: bool


class ProjectListResponse(BaseModel):
    projects: list[ProjectEntrySchema] = Field(default_factory=list)


class ScanStatusResponse(BaseModel):
    active: bool = False
    progress: float = 0.0
    message: str = "Idle"
