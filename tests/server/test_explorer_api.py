"""Tests for the 3 Explorer API routes: /api/files, /api/communities, /api/file/read."""
import pytest
from pathlib import Path

from atlas.core.models import Node, Edge, Extraction
from atlas.server.app import create_app
from atlas.server.deps import create_engine_set, EventBus


@pytest.fixture
def engines(tmp_path):
    """Create engine set with a populated graph."""
    root = tmp_path
    # Create some files to scan
    (root / "src").mkdir()
    (root / "src" / "auth.py").write_text("# auth module\nimport jwt\n")
    (root / "src" / "db.py").write_text("# database module\n")
    (root / "docs").mkdir()
    (root / "docs" / "readme.md").write_text("# Project Readme\n")
    # Create wiki pages
    (root / "wiki" / "concepts").mkdir(parents=True)
    (root / "wiki" / "concepts" / "auth.md").write_text(
        "---\ntitle: Auth\ntype: wiki-concept\n---\n\nAuthentication module.\n"
    )

    es = create_engine_set(root)

    # Populate graph with nodes that have source_file pointing to real files
    extraction = Extraction(
        nodes=[
            Node(id="src/auth.py", label="auth.py", type="code", source_file="src/auth.py", community=0),
            Node(id="src/db.py", label="db.py", type="code", source_file="src/db.py", community=0),
            Node(id="docs/readme.md", label="readme.md", type="document", source_file="docs/readme.md", community=1),
            Node(id="wiki/concepts/auth", label="Auth", type="wiki-concept", source_file="wiki/concepts/auth.md", community=0),
        ],
        edges=[
            Edge(source="src/auth.py", target="src/db.py", relation="imports", confidence="EXTRACTED"),
            Edge(source="src/auth.py", target="wiki/concepts/auth", relation="references", confidence="EXTRACTED"),
            Edge(source="docs/readme.md", target="src/auth.py", relation="references", confidence="INFERRED"),
        ],
    )
    es.graph.merge(extraction)
    return es


@pytest.fixture
def client(engines):
    """TestClient for the API."""
    from fastapi.testclient import TestClient
    app = create_app(engines=engines, event_bus=EventBus())
    return TestClient(app)


class TestFilesEndpoint:
    def test_returns_tree_structure(self, client):
        resp = client.get("/api/files")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Should have top-level entries (src/, docs/, wiki/)
        paths = [item["path"] for item in data]
        assert any("src" in p for p in paths)

    def test_nodes_have_required_fields(self, client):
        resp = client.get("/api/files")
        data = resp.json()
        # Flatten to find a file node
        def find_files(nodes):
            files = []
            for n in nodes:
                if n.get("children"):
                    files.extend(find_files(n["children"]))
                else:
                    files.append(n)
            return files
        files = find_files(data)
        assert len(files) > 0
        f = files[0]
        assert "path" in f
        assert "type" in f
        assert "degree" in f

    def test_directory_nodes_have_children(self, client):
        resp = client.get("/api/files")
        data = resp.json()
        dirs = [item for item in data if item.get("children") is not None]
        assert len(dirs) > 0
        for d in dirs:
            assert isinstance(d["children"], list)


class TestCommunitiesEndpoint:
    def test_returns_community_list(self, client):
        resp = client.get("/api/communities")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_community_has_required_fields(self, client):
        resp = client.get("/api/communities")
        data = resp.json()
        if len(data) > 0:
            c = data[0]
            assert "id" in c
            assert "label" in c
            assert "size" in c
            assert "cohesion" in c
            assert "members" in c

    def test_community_members_are_enriched(self, client, engines):
        resp = client.get("/api/communities")
        data = resp.json()
        all_node_ids = set(engines.graph.iter_node_ids())
        for c in data:
            for member in c["members"]:
                assert isinstance(member, dict)
                assert member["id"] in all_node_ids
                assert "type" in member
                assert "degree" in member


class TestFileReadEndpoint:
    def test_read_existing_file(self, client):
        resp = client.get("/api/file/read", params={"path": "src/auth.py"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["path"] == "src/auth.py"
        assert "auth module" in data["content"]

    def test_read_nonexistent_file_returns_404(self, client):
        resp = client.get("/api/file/read", params={"path": "src/nonexistent.py"})
        assert resp.status_code == 404

    def test_path_traversal_blocked(self, client):
        resp = client.get("/api/file/read", params={"path": "../../etc/passwd"})
        assert resp.status_code in (400, 403, 404, 422)

    def test_read_markdown_file(self, client):
        resp = client.get("/api/file/read", params={"path": "docs/readme.md"})
        assert resp.status_code == 200
        data = resp.json()
        assert "Readme" in data["content"]
