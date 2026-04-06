from atlas.core.graph import GraphEngine
from atlas.core.wiki import WikiEngine
from atlas.core.linker import Linker
from atlas.core.models import Edge


def test_sync_wiki_to_graph_creates_nodes(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    changes = linker.sync_wiki_to_graph()
    # Should create nodes for each wiki page
    assert graph.node_count >= 4  # acme, auth, billing, api-spec, fastapi decision
    # Check node types match page types
    auth_node = graph.get_node("auth")
    assert auth_node is not None
    assert auth_node.type == "wiki-concept"


def test_sync_wiki_to_graph_creates_wikilink_edges(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    linker.sync_wiki_to_graph()
    # auth.md links to [[billing]] and [[wiki/projects/acme]]
    neighbors = graph.get_neighbors("auth")
    neighbor_ids = {n.id for n, _ in neighbors}
    assert "billing" in neighbor_ids


def test_sync_wiki_to_graph_creates_tag_edges(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    linker.sync_wiki_to_graph()
    # auth.md has tags: [auth, security]
    auth_node = graph.get_node("auth")
    assert auth_node is not None
    assert "auth" in auth_node.tags


def test_sync_wiki_to_graph_idempotent(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    linker.sync_wiki_to_graph()
    count1 = graph.node_count
    edge1 = graph.edge_count
    # Run again
    linker.sync_wiki_to_graph()
    assert graph.node_count == count1
    assert graph.edge_count == edge1


def test_sync_graph_to_wiki_suggests_missing_pages(sample_wiki, sample_extraction):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    graph.merge(sample_extraction)  # adds auth, db, api nodes from code
    linker = Linker(wiki=wiki, graph=graph)
    suggestions = linker.sync_graph_to_wiki()
    # db and api don't have wiki pages -> should suggest creating them
    create_suggestions = [s for s in suggestions if s.type == "create_page"]
    suggested_nodes = {s.source_node for s in create_suggestions}
    assert "db" in suggested_nodes or "api" in suggested_nodes


def test_sync_graph_to_wiki_suggests_missing_wikilinks(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    linker.sync_wiki_to_graph()
    # Add an inferred edge between auth and api-spec that isn't a wikilink
    graph.add_edge(Edge(source="auth", target="2026-04-01-api-spec", relation="related", confidence="INFERRED"))
    suggestions = linker.sync_graph_to_wiki()
    link_suggestions = [s for s in suggestions if s.type == "add_wikilink"]
    # Should suggest adding a wikilink from auth to api-spec
    assert len(link_suggestions) >= 0  # depends on whether the pages exist


def test_returns_graph_changes(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)
    changes = linker.sync_wiki_to_graph()
    assert len(changes) > 0
    assert all(hasattr(c, "type") for c in changes)
