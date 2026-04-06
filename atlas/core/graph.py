"""Graph engine — build, merge, query, BFS/DFS, serialize."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from dataclasses import asdict

import networkx as nx

from atlas.core.models import Node, Edge, Extraction, Subgraph, GraphStats


class GraphEngine:
    """In-memory graph backed by NetworkX. Serializes to graph.json."""

    def __init__(self):
        self._g = nx.Graph()

    @property
    def node_count(self) -> int:
        return self._g.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._g.number_of_edges()

    def merge(self, extraction: Extraction) -> None:
        for node in extraction.nodes:
            self._g.add_node(node.id, **{k: v for k, v in asdict(node).items() if k != "id"})
        for edge in extraction.edges:
            if edge.source in self._g and edge.target in self._g:
                self._g.add_edge(
                    edge.source,
                    edge.target,
                    relation=edge.relation,
                    confidence=edge.confidence,
                    confidence_score=edge.confidence_score,
                    source_file=edge.source_file,
                    weight=edge.weight,
                )

    def get_node(self, node_id: str) -> Node | None:
        if node_id not in self._g:
            return None
        data = self._g.nodes[node_id]
        return Node(id=node_id, **{k: v for k, v in data.items() if k in Node.__dataclass_fields__ and k != "id"})

    def get_neighbors(self, node_id: str) -> list[tuple[Node, Edge]]:
        if node_id not in self._g:
            return []
        result = []
        for neighbor_id in self._g.neighbors(node_id):
            node = self.get_node(neighbor_id)
            edge_data = self._g.edges[node_id, neighbor_id]
            edge = Edge(
                source=node_id,
                target=neighbor_id,
                relation=edge_data.get("relation", "related"),
                confidence=edge_data.get("confidence", "EXTRACTED"),
                confidence_score=edge_data.get("confidence_score", 1.0),
            )
            result.append((node, edge))
        return result

    def add_edge(self, edge: Edge) -> None:
        self._g.add_edge(
            edge.source,
            edge.target,
            relation=edge.relation,
            confidence=edge.confidence,
            confidence_score=edge.confidence_score,
            weight=edge.weight,
        )

    def remove_edge(self, source: str, target: str) -> None:
        if self._g.has_edge(source, target):
            self._g.remove_edge(source, target)

    def remove_node(self, node_id: str) -> None:
        if node_id in self._g:
            self._g.remove_node(node_id)

    def query(self, start: str, mode: str = "bfs", depth: int = 3) -> Subgraph:
        if start not in self._g:
            return Subgraph()
        visited_nodes = set()
        visited_edges = []

        if mode == "bfs":
            queue = deque([(start, 0)])
            visited_nodes.add(start)
            while queue:
                current, d = queue.popleft()
                if d >= depth:
                    continue
                for neighbor in self._g.neighbors(current):
                    edge_data = self._g.edges[current, neighbor]
                    visited_edges.append(Edge(
                        source=current, target=neighbor,
                        relation=edge_data.get("relation", "related"),
                        confidence=edge_data.get("confidence", "EXTRACTED"),
                        confidence_score=edge_data.get("confidence_score", 1.0),
                    ))
                    if neighbor not in visited_nodes:
                        visited_nodes.add(neighbor)
                        queue.append((neighbor, d + 1))
        else:  # dfs
            stack = [(start, 0)]
            while stack:
                current, d = stack.pop()
                if current in visited_nodes and current != start:
                    continue
                visited_nodes.add(current)
                if d >= depth:
                    continue
                for neighbor in self._g.neighbors(current):
                    edge_data = self._g.edges[current, neighbor]
                    visited_edges.append(Edge(
                        source=current, target=neighbor,
                        relation=edge_data.get("relation", "related"),
                        confidence=edge_data.get("confidence", "EXTRACTED"),
                        confidence_score=edge_data.get("confidence_score", 1.0),
                    ))
                    if neighbor not in visited_nodes:
                        stack.append((neighbor, d + 1))

        nodes = [self.get_node(nid) for nid in visited_nodes if self.get_node(nid)]
        return Subgraph(nodes=nodes, edges=visited_edges)

    def path(self, source: str, target: str) -> list[Edge] | None:
        if source not in self._g or target not in self._g:
            return None
        try:
            node_path = nx.shortest_path(self._g, source, target)
        except nx.NetworkXNoPath:
            return None
        edges = []
        for i in range(len(node_path) - 1):
            a, b = node_path[i], node_path[i + 1]
            ed = self._g.edges[a, b]
            edges.append(Edge(
                source=a, target=b,
                relation=ed.get("relation", "related"),
                confidence=ed.get("confidence", "EXTRACTED"),
                confidence_score=ed.get("confidence_score", 1.0),
            ))
        return edges

    def stats(self) -> GraphStats:
        breakdown: dict[str, int] = {"EXTRACTED": 0, "INFERRED": 0, "AMBIGUOUS": 0}
        for _, _, data in self._g.edges(data=True):
            conf = data.get("confidence", "EXTRACTED")
            breakdown[conf] = breakdown.get(conf, 0) + 1
        communities = set()
        for _, data in self._g.nodes(data=True):
            c = data.get("community")
            if c is not None:
                communities.add(c)
        return GraphStats(
            nodes=self.node_count,
            edges=self.edge_count,
            communities=len(communities),
            confidence_breakdown=breakdown,
        )

    def save(self, path: Path | str) -> None:
        path = Path(path)
        data = nx.node_link_data(self._g)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> GraphEngine:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        engine = cls()
        engine._g = nx.node_link_graph(data)
        return engine
