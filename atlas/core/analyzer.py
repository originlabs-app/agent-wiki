"""Analyzer — god nodes, surprises, gaps, contradictions, audit."""
from __future__ import annotations

from datetime import datetime, date as date_type, timedelta
from typing import TYPE_CHECKING

from atlas.core.models import AuditReport, Edge, GraphStats, LinkSuggestion

if TYPE_CHECKING:
    from atlas.core.graph import GraphEngine
    from atlas.core.wiki import WikiEngine

STALE_THRESHOLD_DAYS = 30


class Analyzer:
    """Analyzes the graph and wiki for structural insights."""

    def __init__(self, graph: GraphEngine, wiki: WikiEngine | None = None):
        self.graph = graph
        self.wiki = wiki

    def god_nodes(self, top_n: int = 10) -> list[tuple[str, int]]:
        """Return top N nodes by degree (most connected)."""
        degrees = [(nid, self.graph.degree(nid)) for nid in self.graph.iter_node_ids()]
        degrees.sort(key=lambda x: -x[1])
        return degrees[:top_n]

    def surprises(self, top_n: int = 10) -> list[Edge]:
        """Return edges ranked by surprise score (INFERRED/AMBIGUOUS + cross-community)."""
        scored: list[tuple[float, Edge]] = []
        for u, v, data in self.graph.iter_edges(data=True):
            score = 0.0
            conf = data.get("confidence", "EXTRACTED")
            if conf == "AMBIGUOUS":
                score += 3.0
            elif conf == "INFERRED":
                score += 2.0
            else:
                score += 1.0

            # Cross-community bonus
            u_data = self.graph.get_node_data(u)
            v_data = self.graph.get_node_data(v)
            u_comm = u_data.get("community")
            v_comm = v_data.get("community")
            if u_comm is not None and v_comm is not None and u_comm != v_comm:
                score += 1.0

            # Cross file-type bonus
            u_type = u_data.get("type", "")
            v_type = v_data.get("type", "")
            if u_type != v_type:
                score += 2.0

            edge = Edge(
                source=u, target=v,
                relation=data.get("relation", "related"),
                confidence=conf,
                confidence_score=data.get("confidence_score", 1.0),
            )
            scored.append((score, edge))

        scored.sort(key=lambda x: -x[0])
        return [edge for _, edge in scored[:top_n]]

    def audit(self) -> AuditReport:
        """Full audit of graph + wiki health."""
        report = AuditReport()
        report.stats = self.graph.stats()
        report.god_nodes = self.god_nodes()

        if self.wiki:
            # Read all pages once to avoid O(n²) re-reads
            all_pages = self.wiki.list_pages()
            all_links: dict[str, list[str]] = {}
            page_slugs: set[str] = set()
            for page in all_pages:
                page_slugs.add(page.slug)
                if page.wikilinks:
                    all_links[page.path] = page.wikilinks

            # Broken links: wikilinks pointing to non-existent pages
            for page_path, links in all_links.items():
                for link in links:
                    link_slug = link.rsplit("/", 1)[-1].removesuffix(".md")
                    if link_slug not in page_slugs:
                        report.broken_links.append((page_path, link))

            # Orphan pages: pages with no incoming wikilinks
            incoming: set[str] = set()
            for links in all_links.values():
                for link in links:
                    incoming.add(link.rsplit("/", 1)[-1].removesuffix(".md"))
            for page in all_pages:
                if page.slug not in incoming and page.type != "wiki-index":
                    report.orphan_pages.append(page.path)

            # Stale pages: not updated in 30+ days
            cutoff = (datetime.now() - timedelta(days=STALE_THRESHOLD_DAYS)).strftime("%Y-%m-%d")
            for page in all_pages:
                updated = page.frontmatter.get("updated", "")
                # Handle both str and datetime.date (YAML safe_load returns date objects)
                if isinstance(updated, date_type):
                    updated = updated.isoformat()
                if isinstance(updated, str) and updated and updated < cutoff:
                    report.stale_pages.append(page.path)

        # Health score
        total_issues = len(report.orphan_pages) + len(report.broken_links) + len(report.stale_pages)
        base_score = report.stats.health_score if report.stats else 50.0
        penalty = min(total_issues * 2, 30)
        report.health_score = max(0, base_score - penalty)

        return report
