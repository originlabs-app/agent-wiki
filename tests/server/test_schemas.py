from atlas.server.schemas import (
    ScanRequest,
    ScanResponse,
    QueryRequest,
    QueryResponse,
    PathRequest,
    PathResponse,
    ExplainRequest,
    ExplainResponse,
    GodNodesRequest,
    GodNodesResponse,
    SurprisesRequest,
    SurprisesResponse,
    StatsResponse,
    WikiReadRequest,
    WikiReadResponse,
    WikiWriteRequest,
    WikiWriteResponse,
    WikiSearchRequest,
    WikiSearchResponse,
    AuditResponse,
    SuggestLinksResponse,
    IngestRequest,
    IngestResponse,
    ErrorResponse,
    NodeSchema,
    EdgeSchema,
    PageSchema,
)


def test_scan_request_defaults():
    req = ScanRequest(path="/some/folder")
    assert req.path == "/some/folder"
    assert req.incremental is False
    assert req.force is False


def test_scan_request_with_options():
    req = ScanRequest(path="/code", incremental=True, force=False)
    assert req.incremental is True


def test_query_request():
    req = QueryRequest(question="auth", mode="bfs", depth=3)
    assert req.question == "auth"
    assert req.mode == "bfs"
    assert req.depth == 3


def test_query_request_defaults():
    req = QueryRequest(question="billing")
    assert req.mode == "bfs"
    assert req.depth == 3


def test_path_request():
    req = PathRequest(source="auth", target="billing")
    assert req.source == "auth"


def test_explain_request():
    req = ExplainRequest(concept="auth")
    assert req.concept == "auth"


def test_god_nodes_request_defaults():
    req = GodNodesRequest()
    assert req.top_n == 10


def test_surprises_request_defaults():
    req = SurprisesRequest()
    assert req.top_n == 10


def test_wiki_read_request():
    req = WikiReadRequest(page="wiki/concepts/auth.md")
    assert req.page == "wiki/concepts/auth.md"


def test_wiki_write_request():
    req = WikiWriteRequest(
        page="wiki/concepts/auth.md",
        content="# Auth\n\nUpdated.",
        frontmatter={"type": "wiki-concept", "title": "Auth"},
    )
    assert req.page == "wiki/concepts/auth.md"
    assert req.frontmatter["type"] == "wiki-concept"


def test_wiki_search_request():
    req = WikiSearchRequest(terms="JWT")
    assert req.terms == "JWT"


def test_ingest_request_url():
    req = IngestRequest(url="https://arxiv.org/abs/1706.03762")
    assert req.url == "https://arxiv.org/abs/1706.03762"
    assert req.file_path is None


def test_ingest_request_file():
    req = IngestRequest(file_path="raw/untracked/notes.md", title="My Notes")
    assert req.file_path == "raw/untracked/notes.md"
    assert req.title == "My Notes"


def test_node_schema():
    ns = NodeSchema(id="auth", label="Auth", type="code", source_file="auth.py")
    assert ns.id == "auth"
    assert ns.confidence == "high"


def test_edge_schema():
    es = EdgeSchema(source="auth", target="db", relation="imports", confidence="EXTRACTED")
    assert es.confidence_score == 1.0


def test_error_response():
    err = ErrorResponse(error="not_found", detail="Page not found")
    assert err.error == "not_found"
