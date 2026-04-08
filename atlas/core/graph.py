"""Graph engine — build, merge, query, BFS/DFS, serialize."""
from __future__ import annotations

import json
import logging
from collections import deque
from pathlib import Path
from dataclasses import asdict

import networkx as nx

from atlas.core.models import Node, Edge, Extraction, Subgraph, GraphStats

logger = logging.getLogger(__name__)


class GraphEngine:
    """In-memory graph backed by NetworkX DiGraph. Serializes to graph.json."""

    def __init__(self):
        self._g = nx.DiGraph()

    @property
    def node_count(self) -> int:
        return self._g.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._g.number_of_edges()

    # --- Public node/edge access (encapsulation layer) ---

    def has_node(self, node_id: str) -> bool:
        return node_id in self._g

    def iter_node_ids(self) -> list[str]:
        return list(self._g.nodes)

    def get_node_data(self, node_id: str) -> dict:
        """Return raw attribute dict for a node. Empty dict if not found."""
        if node_id not in self._g:
            return {}
        return dict(self._g.nodes[node_id])

    def set_node(self, node_id: str, **attrs) -> bool:
        """Add or update a node with arbitrary attributes. Returns True if new."""
        is_new = node_id not in self._g
        self._g.add_node(node_id, **attrs)
        return is_new

    def has_edge(self, source: str, target: str) -> bool:
        return self._g.has_edge(source, target)

    def get_edge_data(self, source: str, target: str) -> dict:
        """Return raw attribute dict for an edge. Empty dict if not found."""
        if not self._g.has_edge(source, target):
            return {}
        return dict(self._g.edges[source, target])

    def set_edge(self, source: str, target: str, **attrs) -> None:
        """Add or update a directed edge with arbitrary attributes."""
        self._g.add_edge(source, target, **attrs)

    def iter_edges(self, data: bool = True):
        """Iterate edges. Yields (u, v, data_dict) if data=True, else (u, v)."""
        return self._g.edges(data=data)

    def degree(self, node_id: str) -> int:
        """Total degree (in + out) for a node."""
        if node_id not in self._g:
            return 0
        return self._g.in_degree(node_id) + self._g.out_degree(node_id)

    # --- Core operations ---

    def merge(self, extraction: Extraction) -> list[Edge]:
        """Merge an extraction into the graph. Returns list of dropped edges."""
        dropped: list[Edge] = []
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
            else:
                missing = []
                if edge.source not in self._g:
                    missing.append(f"source '{edge.source}'")
                if edge.target not in self._g:
                    missing.append(f"target '{edge.target}'")
                logger.warning("Dropped edge %s->%s (%s): missing %s", edge.source, edge.target, edge.relation, ", ".join(missing))
                dropped.append(edge)
        return dropped

    def get_node(self, node_id: str) -> Node | None:
        if node_id not in self._g:
            return None
        data = self._g.nodes[node_id]
        return Node(id=node_id, **{k: v for k, v in data.items() if k in Node.__dataclass_fields__ and k != "id"})

    def get_neighbors(self, node_id: str) -> list[tuple[Node, Edge]]:
        """Return all neighbors (both successors and predecessors) with their edges."""
        if node_id not in self._g:
            return []
        result = []
        seen = set()
        # Outgoing edges
        for neighbor_id in self._g.successors(node_id):
            if neighbor_id not in seen:
                seen.add(neighbor_id)
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
        # Incoming edges
        for neighbor_id in self._g.predecessors(node_id):
            if neighbor_id not in seen:
                seen.add(neighbor_id)
                node = self.get_node(neighbor_id)
                edge_data = self._g.edges[neighbor_id, node_id]
                edge = Edge(
                    source=neighbor_id,
                    target=node_id,
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
        visited_edge_keys: set[tuple[str, str]] = set()
        visited_edges: list[Edge] = []

        # Use undirected view for traversal (follow edges in both directions)
        undirected = self._g.to_undirected(as_view=True)

        if mode == "bfs":
            queue = deque([(start, 0)])
            visited_nodes.add(start)
            while queue:
                current, d = queue.popleft()
                if d >= depth:
                    continue
                for neighbor in undirected.neighbors(current):
                    # Record edge (use actual direction from digraph)
                    for u, v in [(current, neighbor), (neighbor, current)]:
                        if self._g.has_edge(u, v) and (u, v) not in visited_edge_keys:
                            visited_edge_keys.add((u, v))
                            edge_data = self._g.edges[u, v]
                            visited_edges.append(Edge(
                                source=u, target=v,
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
                for neighbor in undirected.neighbors(current):
                    for u, v in [(current, neighbor), (neighbor, current)]:
                        if self._g.has_edge(u, v) and (u, v) not in visited_edge_keys:
                            visited_edge_keys.add((u, v))
                            edge_data = self._g.edges[u, v]
                            visited_edges.append(Edge(
                                source=u, target=v,
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
            # Use undirected view for pathfinding
            undirected = self._g.to_undirected(as_view=True)
            node_path = nx.shortest_path(undirected, source, target)
        except nx.NetworkXNoPath:
            return None
        edges = []
        for i in range(len(node_path) - 1):
            a, b = node_path[i], node_path[i + 1]
            # Find the actual directed edge
            if self._g.has_edge(a, b):
                ed = self._g.edges[a, b]
                edges.append(Edge(
                    source=a, target=b,
                    relation=ed.get("relation", "related"),
                    confidence=ed.get("confidence", "EXTRACTED"),
                    confidence_score=ed.get("confidence_score", 1.0),
                    source_file=ed.get("source_file"),
                    weight=ed.get("weight", 1.0),
                ))
            elif self._g.has_edge(b, a):
                ed = self._g.edges[b, a]
                edges.append(Edge(
                    source=b, target=a,
                    relation=ed.get("relation", "related"),
                    confidence=ed.get("confidence", "EXTRACTED"),
                    confidence_score=ed.get("confidence_score", 1.0),
                    source_file=ed.get("source_file"),
                    weight=ed.get("weight", 1.0),
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
        engine._g = nx.node_link_graph(data, directed=True)
        return engine
