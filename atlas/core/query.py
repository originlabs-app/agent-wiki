"""Query engine — structured answers from the knowledge graph.

The QueryEngine is the primary interface for agents to query Atlas.
It combines graph traversal, wiki search, and context assembly to produce
structured answers that agents can consume directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas.core.graph import GraphEngine
    from atlas.core.wiki import WikiEngine


@dataclass
class QueryResult:
    """Structured answer to a knowledge query."""
    query: str
    answer: str
    evidence: list[str] = field(default_factory=list)  # paths/IDs of source nodes/pages
    related: list[str] = field(default_factory=list)    # IDs of related concepts
    confidence: str = "medium"                           # high | medium | low
    graph_depth: int = 0                                 # how deep we traversed

    @property
    def is_empty(self) -> bool:
        return not self.answer and not self.evidence


class QueryEngine:
    """Query the knowledge graph for structured answers.

    Three query modes:
    1. Node lookup — find a specific node by ID/label
    2. Neighborhood — explore what's connected to a concept
    3. Path — find how two concepts are related

    All modes return a QueryResult with evidence and related concepts.
    """

    def __init__(self, graph: GraphEngine, wiki: WikiEngine | None = None):
        self.graph = graph
        self.wiki = wiki

    def lookup(self, node_id: str) -> QueryResult:
        """Look up a specific node and assemble its full context.

        Returns the node's details, its direct connections, and any
        wiki page content if available.
        """
        node = self.graph.get_node(node_id)
        if node is None:
            return QueryResult(query=node_id, answer="", confidence="low")

        # Build answer from node data
        parts = [f"# {node.label}", f"Type: {node.type}"]
        if node.summary:
            parts.append(f"Summary: {node.summary}")
        if node.tags:
            parts.append(f"Tags: {', '.join(node.tags)}")

        # Get neighbors
        neighbors = self.graph.get_neighbors(node_id)
        if neighbors:
            parts.append(f"\n## Connections ({len(neighbors)})")
            for neighbor, edge in neighbors:
                direction = "→" if edge.source == node_id else "←"
                parts.append(f"  {direction} {neighbor.label} ({edge.relation})")

        # Try to enrich from wiki
        wiki_evidence: list[str] = []
        if self.wiki:
            wiki_page = self._find_wiki_page(node_id, node.label)
            if wiki_page:
                parts.append(f"\n## Wiki: {wiki_page.title}")
                parts.append(self._extract_summary(wiki_page.content))
                wiki_evidence.append(wiki_page.path)

        # Gather evidence (source files)
        evidence = [node.source_file] if node.source_file else []
        evidence.extend(wiki_evidence)

        # Related concepts from neighbors
        related = []
        for neighbor, _ in neighbors:
            related.append(neighbor.id)

        answer = "\n".join(parts)
        return QueryResult(
            query=node_id,
            answer=answer,
            evidence=evidence,
            related=related,
            confidence=node.confidence,
            graph_depth=1,
        )

    def neighborhood(self, node_id: str, depth: int = 2, mode: str = "bfs") -> QueryResult:
        """Explore the neighborhood around a concept.

        Returns a subgraph-centered answer showing how the concept
        connects to the rest of the knowledge base.
        """
        node = self.graph.get_node(node_id)
        if node is None:
            # Try fuzzy match
            alt = self._fuzzy_find(node_id)
            if alt:
                return self.neighborhood(alt, depth=depth, mode=mode)
            return QueryResult(query=node_id, answer="", confidence="low")

        subgraph = self.graph.query(node_id, mode=mode, depth=depth)
        if not subgraph.nodes:
            return QueryResult(query=node_id, answer=f"Node '{node.label}' exists but has no connections.", confidence="medium")

        # Build structured answer
        parts = [f"# Neighborhood: {node.label}", f"Nodes: {len(subgraph.nodes)}, Edges: {len(subgraph.edges)}"]

        # Group edges by relation type
        relations: dict[str, list[str]] = {}
        for edge in subgraph.edges:
            rel = edge.relation
            if rel not in relations:
                relations[rel] = []
            relations[rel].append(f"{edge.source} → {edge.target}")

        if relations:
            parts.append("\n## Relationships")
            for rel, connections in sorted(relations.items()):
                parts.append(f"### {rel} ({len(connections)})")
                for conn in connections[:10]:  # cap per relation type
                    parts.append(f"  - {conn}")

        # Evidence from source files
        evidence = list({n.source_file for n in subgraph.nodes if n.source_file})
        related = [n.id for n in subgraph.nodes if n.id != node_id]

        return QueryResult(
            query=node_id,
            answer="\n".join(parts),
            evidence=evidence,
            related=related,
            confidence="medium",
            graph_depth=depth,
        )

    def path(self, source_id: str, target_id: str) -> QueryResult:
        """Find how two concepts are related by tracing a path through the graph.

        Returns the shortest path with explanations of each hop.
        """
        source = self.graph.get_node(source_id)
        target = self.graph.get_node(target_id)
        if source is None or target is None:
            missing = []
            if source is None:
                missing.append(source_id)
            if target is None:
                missing.append(target_id)
            return QueryResult(
                query=f"{source_id} → {target_id}",
                answer=f"Node(s) not found: {', '.join(missing)}",
                confidence="low",
            )

        edges = self.graph.path(source_id, target_id)
        if edges is None:
            return QueryResult(
                query=f"{source_id} → {target_id}",
                answer=f"No path found between '{source.label}' and '{target.label}'.",
                confidence="low",
            )

        # Build hop-by-hop explanation
        parts = [f"# Path: {source.label} → {target.label}", f"Hops: {len(edges)}"]

        for i, edge in enumerate(edges, 1):
            src = self.graph.get_node(edge.source)
            tgt = self.graph.get_node(edge.target)
            src_label = src.label if src else edge.source
            tgt_label = tgt.label if tgt else edge.target
            conf_indicator = "✓" if edge.confidence == "EXTRACTED" else "?" if edge.confidence == "INFERRED" else "⚠"
            parts.append(f"\n{i}. {src_label} —[{edge.relation}]→ {tgt_label} {conf_indicator}")
            if edge.confidence_score is not None and edge.confidence_score < 1.0:
                parts.append(f"   Confidence: {edge.confidence_score:.0%}")

        evidence = list({edge.source_file for edge in edges if edge.source_file})
        # All intermediate nodes are "related"
        related = []
        for edge in edges:
            related.append(edge.source)
            related.append(edge.target)
        related = list(dict.fromkeys(related))  # deduplicate preserving order
        related = [r for r in related if r not in (source_id, target_id)]

        return QueryResult(
            query=f"{source_id} → {target_id}",
            answer="\n".join(parts),
            evidence=evidence,
            related=related,
            confidence="medium" if any(e.confidence == "EXTRACTED" for e in edges) else "low",
            graph_depth=len(edges),
        )

    def search(self, terms: str) -> list[QueryResult]:
        """Search across graph nodes and wiki pages for matching terms.

        Returns ranked results with partial matches.
        """
        results: list[QueryResult] = []
        terms_lower = terms.lower()

        # Search graph nodes by label/summary/tags
        for node_id in self.graph.iter_node_ids():
            data = self.graph.get_node_data(node_id)
            label = data.get("label", "")
            summary = data.get("summary", "") or ""
            tags = data.get("tags", []) or []
            searchable = f"{label} {summary} {' '.join(tags)}".lower()

            if terms_lower in searchable:
                node_result = self.lookup(node_id)
                results.append(node_result)

        # Search wiki pages if available
        if self.wiki:
            wiki_results = self.wiki.search(terms)
            for page in wiki_results:
                # Check if we already have this as a graph node
                existing = any(r.query == page.slug for r in results)
                if not existing:
                    summary = self._extract_summary(page.content)
                    results.append(QueryResult(
                        query=page.slug,
                        answer=f"# {page.title}\n{summary}",
                        evidence=[page.path],
                        confidence=page.frontmatter.get("confidence", "medium"),
                    ))

        return results

    def _find_wiki_page(self, node_id: str, label: str | None = None):
        """Try to find a wiki page matching a node."""
        if not self.wiki:
            return None
        # Try by slug match
        for page in self.wiki.list_pages():
            if page.slug == node_id:
                return page
        # Try by title match
        if label:
            for page in self.wiki.list_pages():
                if page.title.lower() == label.lower():
                    return page
        return None

    def _extract_summary(self, content: str, max_chars: int = 500) -> str:
        """Extract the first meaningful paragraph from wiki content."""
        # Strip frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:]

        lines = content.strip().split("\n")
        paragraphs: list[str] = []
        current: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
            elif not stripped.startswith("#") and not stripped.startswith("```"):
                current.append(stripped)

        if current:
            paragraphs.append(" ".join(current))

        if not paragraphs:
            return ""

        summary = paragraphs[0]
        if len(summary) > max_chars:
            summary = summary[:max_chars].rsplit(" ", 1)[0] + "..."
        return summary

    def _fuzzy_find(self, query: str) -> str | None:
        """Find a node ID by fuzzy matching against labels."""
        query_lower = query.lower()
        best_match = None
        best_score = 0

        for node_id in self.graph.iter_node_ids():
            data = self.graph.get_node_data(node_id)
            label = data.get("label", "").lower()

            # Exact label match
            if label == query_lower:
                return node_id

            # Substring match
            if query_lower in label or label in query_lower:
                score = min(len(query_lower), len(label)) / max(len(query_lower), len(label), 1)
                if score > best_score:
                    best_score = score
                    best_match = node_id

            # ID substring match
            if query_lower in node_id.lower():
                score = len(query_lower) / max(len(node_id), 1)
                if score > best_score:
                    best_score = score
                    best_match = node_id

        if best_match and best_score > 0.3:
            return best_match
        return None
