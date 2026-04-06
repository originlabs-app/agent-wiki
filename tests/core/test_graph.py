import json

from atlas.core.graph import GraphEngine
from atlas.core.models import Node, Edge, Extraction, Subgraph


def test_merge_extraction(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    assert g.node_count == 3
    assert g.edge_count == 3


def test_merge_dedup_nodes():
    g = GraphEngine()
    e1 = Extraction(nodes=[Node(id="a", label="A", type="code", source_file="a.py")], edges=[])
    e2 = Extraction(nodes=[Node(id="a", label="A Updated", type="code", source_file="a.py")], edges=[])
    g.merge(e1)
    g.merge(e2)
    assert g.node_count == 1
    assert g.get_node("a").label == "A Updated"  # last write wins


def test_get_node(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    node = g.get_node("auth")
    assert node is not None
    assert node.label == "Auth Module"


def test_get_neighbors(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    neighbors = g.get_neighbors("api")
    assert len(neighbors) == 2
    ids = {n.id for n, _ in neighbors}
    assert "auth" in ids
    assert "db" in ids


def test_query_bfs(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    result = g.query("auth", mode="bfs", depth=2)
    assert isinstance(result, Subgraph)
    assert len(result.nodes) >= 1


def test_query_dfs(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    result = g.query("api", mode="dfs", depth=3)
    assert isinstance(result, Subgraph)
    assert len(result.nodes) >= 1


def test_shortest_path(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    path = g.path("api", "db")
    assert path is not None
    assert len(path) >= 1


def test_shortest_path_no_route():
    g = GraphEngine()
    e = Extraction(
        nodes=[Node(id="a", label="A", type="code", source_file="a.py"), Node(id="b", label="B", type="code", source_file="b.py")],
        edges=[],
    )
    g.merge(e)
    path = g.path("a", "b")
    assert path is None  # no edges = no path


def test_stats(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    stats = g.stats()
    assert stats.nodes == 3
    assert stats.edges == 3
    assert stats.confidence_breakdown["EXTRACTED"] == 2
    assert stats.confidence_breakdown["INFERRED"] == 1


def test_remove_node(sample_extraction):
    g = GraphEngine()
    g.merge(sample_extraction)
    g.remove_node("auth")
    assert g.node_count == 2
    assert g.get_node("auth") is None
    # Edges involving auth should be removed
    assert g.edge_count == 1  # only api->db remains


def test_serialize_deserialize(sample_extraction, tmp_path):
    g = GraphEngine()
    g.merge(sample_extraction)
    path = tmp_path / "graph.json"
    g.save(path)
    assert path.exists()

    g2 = GraphEngine.load(path)
    assert g2.node_count == 3
    assert g2.edge_count == 3


def test_add_edge():
    g = GraphEngine()
    e = Extraction(
        nodes=[Node(id="a", label="A", type="code", source_file="a.py"), Node(id="b", label="B", type="code", source_file="b.py")],
        edges=[],
    )
    g.merge(e)
    g.add_edge(Edge(source="a", target="b", relation="references", confidence="EXTRACTED"))
    assert g.edge_count == 1


def test_remove_edge():
    g = GraphEngine()
    e = Extraction(
        nodes=[Node(id="a", label="A", type="code", source_file="a.py"), Node(id="b", label="B", type="code", source_file="b.py")],
        edges=[Edge(source="a", target="b", relation="references", confidence="EXTRACTED")],
    )
    g.merge(e)
    g.remove_edge("a", "b")
    assert g.edge_count == 0
