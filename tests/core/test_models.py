from atlas.core.models import Node, Edge, Extraction, Page, Subgraph, GraphStats, AuditReport, WikiSuggestion, GraphChange, LinkSuggestion


def test_node_creation():
    node = Node(id="auth_module", label="Auth Module", type="code", source_file="src/auth.py")
    assert node.id == "auth_module"
    assert node.label == "Auth Module"
    assert node.type == "code"
    assert node.source_file == "src/auth.py"
    assert node.confidence == "high"  # default
    assert node.community is None


def test_edge_creation():
    edge = Edge(source="auth_module", target="db_client", relation="imports", confidence="EXTRACTED")
    assert edge.source == "auth_module"
    assert edge.target == "db_client"
    assert edge.confidence_score == 1.0  # EXTRACTED default


def test_edge_inferred_default_score():
    edge = Edge(source="a", target="b", relation="related", confidence="INFERRED")
    assert edge.confidence_score == 0.7


def test_extraction_merge():
    e1 = Extraction(nodes=[Node(id="a", label="A", type="code", source_file="a.py")], edges=[])
    e2 = Extraction(nodes=[Node(id="b", label="B", type="code", source_file="b.py")], edges=[])
    merged = e1.merge(e2)
    assert len(merged.nodes) == 2
    assert len(merged.edges) == 0


def test_page_creation():
    page = Page(
        path="wiki/concepts/auth.md",
        title="Auth",
        type="wiki-concept",
        content="# Auth\n\nAuthentication module.",
        frontmatter={"type": "wiki-concept", "title": "Auth", "confidence": "high", "tags": ["auth"]},
    )
    assert page.title == "Auth"
    assert page.wikilinks == []


def test_page_extract_wikilinks():
    page = Page(
        path="wiki/concepts/auth.md",
        title="Auth",
        type="wiki-concept",
        content="# Auth\n\nSee [[billing]] and [[wiki/projects/acme]].",
        frontmatter={},
    )
    assert page.wikilinks == ["billing", "wiki/projects/acme"]


def test_subgraph_token_count():
    nodes = [Node(id="a", label="A", type="code", source_file="a.py")]
    edges = [Edge(source="a", target="b", relation="calls", confidence="EXTRACTED")]
    sg = Subgraph(nodes=nodes, edges=edges)
    assert sg.estimated_tokens > 0


def test_graph_stats():
    stats = GraphStats(nodes=100, edges=200, communities=5, confidence_breakdown={"EXTRACTED": 120, "INFERRED": 70, "AMBIGUOUS": 10})
    assert stats.health_score > 0  # higher EXTRACTED ratio = higher score
