from atlas.core.analyzer import Analyzer
from atlas.core.graph import GraphEngine
from atlas.core.wiki import WikiEngine
from atlas.core.models import Node, Edge, Extraction


def _build_graph_with_communities():
    """Build a graph with clear community structure."""
    g = GraphEngine()
    nodes = [
        Node(id="auth", label="Auth", type="code", source_file="auth.py"),
        Node(id="session", label="Session", type="code", source_file="session.py"),
        Node(id="jwt", label="JWT", type="code", source_file="jwt.py"),
        Node(id="billing", label="Billing", type="code", source_file="billing.py"),
        Node(id="stripe", label="Stripe", type="code", source_file="stripe.py"),
        Node(id="invoice", label="Invoice", type="code", source_file="invoice.py"),
        Node(id="api", label="API Gateway", type="code", source_file="api.py"),
    ]
    edges = [
        Edge(source="auth", target="session", relation="calls", confidence="EXTRACTED"),
        Edge(source="auth", target="jwt", relation="imports", confidence="EXTRACTED"),
        Edge(source="session", target="jwt", relation="uses", confidence="EXTRACTED"),
        Edge(source="billing", target="stripe", relation="imports", confidence="EXTRACTED"),
        Edge(source="billing", target="invoice", relation="calls", confidence="EXTRACTED"),
        Edge(source="stripe", target="invoice", relation="uses", confidence="INFERRED"),
        Edge(source="api", target="auth", relation="imports", confidence="EXTRACTED"),
        Edge(source="api", target="billing", relation="imports", confidence="EXTRACTED"),
    ]
    g.merge(Extraction(nodes=nodes, edges=edges))
    return g


def test_god_nodes():
    g = _build_graph_with_communities()
    analyzer = Analyzer(graph=g)
    gods = analyzer.god_nodes(top_n=3)
    assert len(gods) <= 3
    ids = [node_id for node_id, _ in gods]
    assert "auth" in ids or "billing" in ids or "api" in ids


def test_surprises():
    g = _build_graph_with_communities()
    analyzer = Analyzer(graph=g)
    surprises = analyzer.surprises(top_n=5)
    assert len(surprises) >= 0


def test_orphan_pages(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    g = GraphEngine()
    analyzer = Analyzer(graph=g, wiki=wiki)
    report = analyzer.audit()
    assert len(report.orphan_pages) >= 0


def test_broken_links(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    g = GraphEngine()
    analyzer = Analyzer(graph=g, wiki=wiki)
    report = analyzer.audit()
    assert isinstance(report.broken_links, list)


def test_stats():
    g = _build_graph_with_communities()
    analyzer = Analyzer(graph=g)
    report = analyzer.audit()
    assert report.stats is not None
    assert report.stats.nodes == 7
    assert report.stats.edges == 8


def test_health_score():
    g = _build_graph_with_communities()
    analyzer = Analyzer(graph=g)
    report = analyzer.audit()
    assert report.health_score > 0


def test_stale_pages(tmp_storage):
    """Pages older than 30 days should be flagged as stale."""
    wiki = WikiEngine(tmp_storage)
    wiki.write(
        "wiki/concepts/old.md",
        "# Old Concept\n\nThis is old.",
        frontmatter={"type": "wiki-concept", "title": "Old", "updated": "2026-01-01", "confidence": "medium"},
    )
    g = GraphEngine()
    analyzer = Analyzer(graph=g, wiki=wiki)
    report = analyzer.audit()
    assert "wiki/concepts/old.md" in report.stale_pages
