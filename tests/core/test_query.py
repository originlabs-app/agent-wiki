"""Tests for QueryEngine — node lookup, neighborhood, path, search."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from atlas.core.graph import GraphEngine
from atlas.core.models import Edge, Extraction, Node
from atlas.core.query import QueryEngine, QueryResult
from atlas.core.wiki import WikiEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def populated_graph(tmp_path) -> GraphEngine:
    """Graph with a small knowledge graph: auth → jwt → user."""
    g = GraphEngine()
    g.set_node("auth-module", label="Auth Module", type="code", source_file="src/auth.py", confidence="high", summary="Handles authentication and authorization", tags=["auth", "jwt"])
    g.set_node("jwt-token", label="JWT Token", type="code", source_file="src/jwt.py", confidence="high", summary="JSON Web Token implementation", tags=["jwt", "security"])
    g.set_node("user-model", label="User Model", type="code", source_file="src/models.py", confidence="high", summary="User database model")
    g.set_node("login-page", label="Login Page", type="document", source_file="docs/login.md", confidence="medium")
    g.set_node("rbac", label="RBAC System", type="code", source_file="src/rbac.py", confidence="high", tags=["auth", "permissions"])

    g.set_edge("auth-module", "jwt-token", relation="imports", confidence="EXTRACTED", source_file="src/auth.py")
    g.set_edge("auth-module", "user-model", relation="references", confidence="EXTRACTED", source_file="src/auth.py")
    g.set_edge("login-page", "auth-module", relation="documents", confidence="EXTRACTED")
    g.set_edge("auth-module", "rbac", relation="calls", confidence="EXTRACTED", source_file="src/auth.py")
    g.set_edge("rbac", "user-model", relation="references", confidence="INFERRED")
    return g


@pytest.fixture
def wiki_with_pages(tmp_path):
    """Wiki with a few pages that overlap with graph nodes."""
    wiki_dir = tmp_path / "wiki" / "concepts"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "auth-module.md").write_text(textwrap.dedent("""\
        ---
        type: wiki-concept
        title: Auth Module
        updated: 2026-04-08
        confidence: high
        ---
        # Auth Module
        The authentication module handles user login, JWT token management,
        and role-based access control. It was designed to support multi-tenant
        architectures from the start.
    """))
    (wiki_dir / "jwt-token.md").write_text(textwrap.dedent("""\
        ---
        type: wiki-concept
        title: JWT Token
        updated: 2026-04-08
        confidence: high
        ---
        # JWT Token
        JSON Web Tokens are used for stateless authentication.
    """))
    return tmp_path


@pytest.fixture
def engine(populated_graph):
    """QueryEngine without wiki."""
    return QueryEngine(graph=populated_graph)


@pytest.fixture
def engine_with_wiki(populated_graph, wiki_with_pages):
    """QueryEngine with wiki pages."""
    from atlas.core.storage import LocalStorage
    storage = LocalStorage(wiki_with_pages)
    wiki = WikiEngine(storage)
    return QueryEngine(graph=populated_graph, wiki=wiki)


# ---------------------------------------------------------------------------
# Tests: QueryResult
# ---------------------------------------------------------------------------

class TestQueryResult:
    def test_empty_result(self):
        r = QueryResult(query="test", answer="")
        assert r.is_empty

    def test_non_empty_with_answer(self):
        r = QueryResult(query="test", answer="some info")
        assert not r.is_empty

    def test_non_empty_with_evidence(self):
        r = QueryResult(query="test", answer="", evidence=["file.py"])
        assert not r.is_empty


# ---------------------------------------------------------------------------
# Tests: Lookup
# ---------------------------------------------------------------------------

class TestLookup:
    def test_existing_node(self, engine):
        result = engine.lookup("auth-module")
        assert not result.is_empty
        assert "Auth Module" in result.answer
        assert result.confidence == "high"
        assert "src/auth.py" in result.evidence
        assert len(result.related) > 0  # has neighbors

    def test_node_with_tags(self, engine):
        result = engine.lookup("auth-module")
        assert "auth" in result.answer
        assert "jwt" in result.answer

    def test_node_with_summary(self, engine):
        result = engine.lookup("jwt-token")
        assert "JSON Web Token" in result.answer

    def test_node_not_found(self, engine):
        result = engine.lookup("nonexistent")
        assert result.is_empty
        assert result.confidence == "low"

    def test_node_with_no_connections(self, engine):
        engine.graph.set_node("isolated", label="Isolated Node", type="code", source_file="x.py")
        result = engine.lookup("isolated")
        assert not result.is_empty
        assert "Isolated Node" in result.answer
        assert len(result.related) == 0

    def test_lookup_with_wiki(self, engine_with_wiki):
        result = engine_with_wiki.lookup("auth-module")
        assert not result.is_empty
        assert "multi-tenant" in result.answer  # from wiki page content
        assert any("auth-module.md" in e for e in result.evidence)

    def test_lookup_wiki_by_title(self, engine_with_wiki):
        # Even if the node ID doesn't match a wiki slug exactly,
        # the wiki page should be found by title match
        result = engine_with_wiki.lookup("jwt-token")
        assert not result.is_empty
        # Should have wiki enrichment
        assert "JWT Token" in result.answer


# ---------------------------------------------------------------------------
# Tests: Neighborhood
# ---------------------------------------------------------------------------

class TestNeighborhood:
    def test_neighborhood_bfs(self, engine):
        result = engine.neighborhood("auth-module", depth=2)
        assert not result.is_empty
        assert "Auth Module" in result.answer
        assert "Nodes:" in result.answer
        assert result.graph_depth == 2

    def test_neighborhood_dfs(self, engine):
        result = engine.neighborhood("auth-module", depth=2, mode="dfs")
        assert not result.is_empty
        assert "Auth Module" in result.answer

    def test_neighborhood_relationships_grouped(self, engine):
        result = engine.neighborhood("auth-module", depth=1)
        assert "imports" in result.answer or "references" in result.answer

    def test_neighborhood_not_found_with_fuzzy(self, engine):
        result = engine.neighborhood("auth")  # should fuzzy match auth-module
        assert not result.is_empty
        assert "Auth Module" in result.answer

    def test_neighborhood_truly_not_found(self, engine):
        result = engine.neighborhood("zzzzzzzzzzzzzzz")
        assert result.is_empty

    def test_neighborhood_isolated_node(self, engine):
        engine.graph.set_node("lone", label="Lone Node", type="code", source_file="x.py")
        result = engine.neighborhood("lone")
        assert not result.is_empty
        assert "Lone Node" in result.answer
        assert len(result.related) == 0  # no neighbors


# ---------------------------------------------------------------------------
# Tests: Path
# ---------------------------------------------------------------------------

class TestPath:
    def test_direct_path(self, engine):
        result = engine.path("auth-module", "jwt-token")
        assert not result.is_empty
        assert "Auth Module" in result.answer
        assert "JWT Token" in result.answer
        assert "imports" in result.answer
        assert "Hops: 1" in result.answer

    def test_two_hop_path(self, engine):
        result = engine.path("login-page", "jwt-token")
        assert not result.is_empty
        assert "login-page" in result.answer.lower() or "Login" in result.answer
        assert "jwt-token" in result.answer.lower() or "JWT" in result.answer

    def test_path_not_found(self, engine):
        engine.graph.set_node("disconnected", label="Disconnected", type="code", source_file="x.py")
        result = engine.path("disconnected", "auth-module")
        # They might actually be connected via the graph — check
        # disconnected has no edges, so no path
        assert result.is_empty or "No path" in result.answer

    def test_path_source_missing(self, engine):
        result = engine.path("nonexistent", "auth-module")
        assert "not found" in result.answer.lower()

    def test_path_target_missing(self, engine):
        result = engine.path("auth-module", "nonexistent")
        assert "not found" in result.answer.lower()

    def test_path_self(self, engine):
        result = engine.path("auth-module", "auth-module")
        assert "Hops: 0" in result.answer

    def test_path_evidence_collected(self, engine):
        result = engine.path("auth-module", "jwt-token")
        assert len(result.evidence) > 0

    def test_path_related_excludes_endpoints(self, engine):
        result = engine.path("auth-module", "user-model")
        # For a 1-hop path, there are no intermediate nodes
        assert "auth-module" not in result.related
        assert "user-model" not in result.related


# ---------------------------------------------------------------------------
# Tests: Search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_by_label(self, engine):
        results = engine.search("JWT")
        assert len(results) > 0
        assert any("JWT Token" in r.answer for r in results)

    def test_search_by_tag(self, engine):
        results = engine.search("security")
        assert len(results) > 0

    def test_search_by_summary(self, engine):
        results = engine.search("authentication")
        assert len(results) > 0
        assert any("auth-module" in r.query for r in results)

    def test_search_no_results(self, engine):
        results = engine.search("zzzzzzzzzzz")
        assert len(results) == 0

    def test_search_with_wiki(self, engine_with_wiki):
        results = engine_with_wiki.search("multi-tenant")
        assert len(results) > 0

    def test_search_dedupes_graph_and_wiki(self, engine_with_wiki):
        results = engine_with_wiki.search("JWT")
        # Should not duplicate auth-module results
        queries = [r.query for r in results]
        assert len(queries) == len(set(queries)), f"Duplicates found: {queries}"


# ---------------------------------------------------------------------------
# Tests: Fuzzy matching
# ---------------------------------------------------------------------------

class TestFuzzyMatch:
    def test_fuzzy_by_label_substring(self, engine):
        alt = engine._fuzzy_find("jwt")
        assert alt == "jwt-token"

    def test_fuzzy_by_id_substring(self, engine):
        alt = engine._fuzzy_find("rbac")
        assert alt == "rbac"

    def test_fuzzy_no_match(self, engine):
        alt = engine._fuzzy_find("totally-random-nothing")
        assert alt is None

    def test_fuzzy_low_score_rejected(self, engine):
        # A very short query against a long label shouldn't match
        alt = engine._fuzzy_find("a")
        # "a" is too short — score will be low
        # Actually it might match "auth-module" with score 1/11 ≈ 0.09 < 0.3
        # So it should return None
        assert alt is None


# ---------------------------------------------------------------------------
# Tests: Summary extraction
# ---------------------------------------------------------------------------

class TestSummaryExtraction:
    def test_extracts_first_paragraph(self, engine):
        content = "---\ntype: test\n---\n\n# Title\n\nFirst paragraph here.\n\nSecond paragraph."
        summary = engine._extract_summary(content)
        assert "First paragraph" in summary
        assert "Second" not in summary

    def test_no_frontmatter(self, engine):
        content = "# Title\n\nJust a paragraph."
        summary = engine._extract_summary(content)
        assert "Just a paragraph" in summary

    def test_truncates_long_content(self, engine):
        content = "x" * 1000
        summary = engine._extract_summary(content, max_chars=50)
        assert len(summary) <= 53  # 50 + "..."
        assert summary.endswith("...")

    def test_empty_content(self, engine):
        assert engine._extract_summary("") == ""
        assert engine._extract_summary("---\n---\n") == ""
