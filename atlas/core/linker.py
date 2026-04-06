"""Linker — bidirectional graph <-> wiki synchronization."""
from __future__ import annotations

from atlas.core.graph import GraphEngine
from atlas.core.models import Edge, GraphChange, Node, WikiSuggestion
from atlas.core.wiki import WikiEngine


class Linker:
    """Synchronizes the wiki and graph bidirectionally.

    wiki -> graph: automatic, synchronous (wikilinks become edges).
    graph -> wiki: suggestions only (never writes without validation).
    """

    def __init__(self, wiki: WikiEngine, graph: GraphEngine):
        self.wiki = wiki
        self.graph = graph

    def sync_wiki_to_graph(self) -> list[GraphChange]:
        """Parse all wiki pages, create/update nodes and edges in the graph.

        Returns list of changes applied.
        """
        changes: list[GraphChange] = []
        pages = self.wiki.list_pages()

        # Build set of current wiki page slugs for edge resolution
        slug_to_path: dict[str, str] = {}
        for page in pages:
            slug_to_path[page.slug] = page.path

        # Track existing wiki-managed nodes
        existing_wiki_nodes = {
            nid for nid in self.graph.iter_node_ids()
            if self.graph.get_node_data(nid).get("_wiki_managed")
        }

        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str]] = set()

        for page in pages:
            node_id = page.slug
            seen_nodes.add(node_id)

            # Create or update node
            is_new = self.graph.set_node(
                node_id,
                _wiki_managed=True,
                label=page.title,
                type=page.type,
                source_file=page.path,
                confidence=page.frontmatter.get("confidence", "medium"),
                summary=page.frontmatter.get("description"),
                tags=page.frontmatter.get("tags", []) if isinstance(page.frontmatter.get("tags"), list) else [],
            )

            if is_new:
                changes.append(GraphChange(type="add_node", node_id=node_id, details=f"Wiki page: {page.title}"))
            else:
                changes.append(GraphChange(type="update_node", node_id=node_id, details=f"Updated: {page.title}"))

            # Create edges from wikilinks
            for link in page.wikilinks:
                target_slug = link.rsplit("/", 1)[-1].removesuffix(".md")
                if target_slug in slug_to_path and target_slug != node_id:
                    edge_key = (node_id, target_slug)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        if not self.graph.has_edge(node_id, target_slug) or \
                                self.graph.get_edge_data(node_id, target_slug).get("_wiki_managed"):
                            self.graph.set_edge(
                                node_id, target_slug,
                                relation="references",
                                confidence="EXTRACTED",
                                confidence_score=1.0,
                                _wiki_managed=True,
                            )
                            changes.append(GraphChange(
                                type="add_edge",
                                edge=Edge(source=node_id, target=target_slug, relation="references", confidence="EXTRACTED"),
                                details=f"Wikilink: {node_id} -> {target_slug}",
                            ))

        # Remove wiki-managed nodes that no longer have pages
        for old_node in existing_wiki_nodes - seen_nodes:
            self.graph.remove_node(old_node)
            changes.append(GraphChange(type="remove_node", node_id=old_node, details="Page deleted"))

        # Remove wiki-managed edges that no longer exist as wikilinks
        edges_to_remove = []
        for u, v, data in self.graph.iter_edges(data=True):
            if data.get("_wiki_managed") and (u, v) not in seen_edges and (v, u) not in seen_edges:
                edges_to_remove.append((u, v))
        for u, v in edges_to_remove:
            self.graph.remove_edge(u, v)
            changes.append(GraphChange(type="remove_edge", edge=Edge(source=u, target=v, relation="removed"), details="Wikilink removed"))

        return changes

    def sync_graph_to_wiki(self) -> list[WikiSuggestion]:
        """Analyze the graph and suggest wiki improvements.

        Returns suggestions — never writes automatically.
        """
        suggestions: list[WikiSuggestion] = []
        wiki_slugs = {p.slug for p in self.wiki.list_pages()}

        # Suggest pages for graph nodes without wiki pages
        for node_id in self.graph.iter_node_ids():
            data = self.graph.get_node_data(node_id)
            if not data.get("_wiki_managed") and node_id not in wiki_slugs:
                label = data.get("label", node_id)
                suggestions.append(WikiSuggestion(
                    type="create_page",
                    description=f"Node '{label}' exists in the graph but has no wiki page.",
                    source_node=node_id,
                    reason=f"Discovered via scan. Type: {data.get('type', 'unknown')}. Degree: {self.graph.degree(node_id)}.",
                ))

        # Suggest wikilinks for INFERRED edges between pages that exist
        for u, v, data in self.graph.iter_edges(data=True):
            if data.get("confidence") == "INFERRED" and not data.get("_wiki_managed"):
                if u in wiki_slugs and v in wiki_slugs:
                    suggestions.append(WikiSuggestion(
                        type="add_wikilink",
                        description=f"INFERRED relationship between '{u}' and '{v}' — consider adding a [[wikilink]].",
                        target_page=u,
                        source_node=u,
                        target_node=v,
                        reason=f"Relation: {data.get('relation', 'related')}. Confidence: {data.get('confidence_score', 0.7):.1f}.",
                    ))

        # Suggest clarification for AMBIGUOUS edges
        for u, v, data in self.graph.iter_edges(data=True):
            if data.get("confidence") == "AMBIGUOUS":
                suggestions.append(WikiSuggestion(
                    type="clarify_relation",
                    description=f"AMBIGUOUS relationship between '{u}' and '{v}' needs clarification.",
                    source_node=u,
                    target_node=v,
                    reason=f"Relation: {data.get('relation', 'unknown')}. Score: {data.get('confidence_score', 0.2):.1f}.",
                ))

        return suggestions
