"""Analyzer — god nodes, surprises, gaps, contradictions, audit."""
from __future__ import annotations

from datetime import datetime, timedelta
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
        degrees = [(nid, self.graph._g.degree(nid)) for nid in self.graph._g.nodes]
        degrees.sort(key=lambda x: -x[1])
        return degrees[:top_n]

    def surprises(self, top_n: int = 10) -> list[Edge]:
        """Return edges ranked by surprise score (INFERRED/AMBIGUOUS + cross-community)."""
        scored: list[tuple[float, Edge]] = []
        for u, v, data in self.graph._g.edges(data=True):
            score = 0.0
            conf = data.get("confidence", "EXTRACTED")
            if conf == "AMBIGUOUS":
                score += 3.0
            elif conf == "INFERRED":
                score += 2.0
            else:
                score += 1.0

            # Cross-community bonus
            u_comm = self.graph._g.nodes[u].get("community")
            v_comm = self.graph._g.nodes[v].get("community")
            if u_comm is not None and v_comm is not None and u_comm != v_comm:
                score += 1.0

            # Cross file-type bonus
            u_type = self.graph._g.nodes[u].get("type", "")
            v_type = self.graph._g.nodes[v].get("type", "")
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
            all_links = self.wiki.all_wikilinks()
            page_slugs = {p.slug for p in self.wiki.list_pages()}

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
            for page in self.wiki.list_pages():
                if page.slug not in incoming and page.type != "wiki-index":
                    report.orphan_pages.append(page.path)

            # Stale pages: not updated in 30+ days
            cutoff = (datetime.now() - timedelta(days=STALE_THRESHOLD_DAYS)).strftime("%Y-%m-%d")
            for page in self.wiki.list_pages():
                updated = page.frontmatter.get("updated", "")
                if isinstance(updated, str) and updated and updated < cutoff:
                    report.stale_pages.append(page.path)

        # Health score
        total_issues = len(report.orphan_pages) + len(report.broken_links) + len(report.stale_pages)
        base_score = report.stats.health_score if report.stats else 50.0
        penalty = min(total_issues * 2, 30)
        report.health_score = max(0, base_score - penalty)

        return report
