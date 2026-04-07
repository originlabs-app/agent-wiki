"""Tests for ProjectRegistry — CRUD on ~/.atlas/projects.json."""
import json
import time
from pathlib import Path

import pytest

from atlas.core.registry import ProjectRegistry, ProjectEntry


@pytest.fixture
def registry_dir(tmp_path):
    """Use a temp dir instead of ~/.atlas/ for isolation."""
    return tmp_path / ".atlas"


@pytest.fixture
def registry(registry_dir):
    return ProjectRegistry(config_dir=registry_dir)


@pytest.fixture
def sample_project(tmp_path):
    """Create a fake project directory with an atlas-out/graph.json."""
    project = tmp_path / "my-project"
    project.mkdir()
    (project / "atlas-out").mkdir()
    (project / "atlas-out" / "graph.json").write_text(json.dumps({
        "nodes": [{"id": "a", "label": "A", "type": "code", "source_file": "a.py"}],
        "edges": [],
    }))
    return project


class TestProjectEntry:
    def test_create_entry(self):
        entry = ProjectEntry(
            path="/Users/me/project",
            name="project",
        )
        assert entry.path == "/Users/me/project"
        assert entry.name == "project"
        assert entry.nodes == 0
        assert entry.edges == 0
        assert entry.communities == 0
        assert entry.health == 0.0
        assert entry.last_opened is not None

    def test_to_dict_roundtrip(self):
        entry = ProjectEntry(path="/tmp/x", name="x", nodes=10, edges=5)
        d = entry.to_dict()
        restored = ProjectEntry.from_dict(d)
        assert restored.path == entry.path
        assert restored.name == entry.name
        assert restored.nodes == entry.nodes
        assert restored.edges == entry.edges


class TestRegistryInit:
    def test_creates_config_dir_on_init(self, registry, registry_dir):
        assert registry_dir.is_dir()

    def test_empty_registry_returns_empty_list(self, registry):
        assert registry.list() == []

    def test_loads_existing_file(self, registry_dir):
        registry_dir.mkdir(parents=True, exist_ok=True)
        data = [{"path": "/tmp/proj", "name": "proj", "last_opened": "2026-04-07T10:00:00",
                 "nodes": 0, "edges": 0, "communities": 0, "health": 0.0}]
        (registry_dir / "projects.json").write_text(json.dumps(data))
        reg = ProjectRegistry(config_dir=registry_dir)
        assert len(reg.list()) == 1
        assert reg.list()[0].path == "/tmp/proj"


class TestRegistryRegister:
    def test_register_new_project(self, registry, sample_project):
        entry = registry.register(str(sample_project))
        assert entry.path == str(sample_project)
        assert entry.name == sample_project.name
        assert len(registry.list()) == 1

    def test_register_sets_name_from_directory(self, registry, sample_project):
        entry = registry.register(str(sample_project))
        assert entry.name == "my-project"

    def test_register_same_project_twice_updates_last_opened(self, registry, sample_project):
        e1 = registry.register(str(sample_project))
        time.sleep(0.01)
        e2 = registry.register(str(sample_project))
        assert len(registry.list()) == 1
        assert e2.last_opened >= e1.last_opened

    def test_register_persists_to_disk(self, registry, registry_dir, sample_project):
        registry.register(str(sample_project))
        raw = json.loads((registry_dir / "projects.json").read_text())
        assert len(raw) == 1
        assert raw[0]["path"] == str(sample_project)

    def test_register_with_stats(self, registry, sample_project):
        entry = registry.register(
            str(sample_project),
            nodes=100, edges=50, communities=5, health=85.0,
        )
        assert entry.nodes == 100
        assert entry.edges == 50
        assert entry.communities == 5
        assert entry.health == 85.0


class TestRegistryRemove:
    def test_remove_existing(self, registry, sample_project):
        registry.register(str(sample_project))
        removed = registry.remove(str(sample_project))
        assert removed is True
        assert len(registry.list()) == 0

    def test_remove_nonexistent(self, registry):
        removed = registry.remove("/nonexistent/path")
        assert removed is False

    def test_remove_persists(self, registry, registry_dir, sample_project):
        registry.register(str(sample_project))
        registry.remove(str(sample_project))
        raw = json.loads((registry_dir / "projects.json").read_text())
        assert len(raw) == 0


class TestRegistryGet:
    def test_get_existing(self, registry, sample_project):
        registry.register(str(sample_project))
        entry = registry.get(str(sample_project))
        assert entry is not None
        assert entry.path == str(sample_project)

    def test_get_nonexistent(self, registry):
        assert registry.get("/nonexistent") is None


class TestRegistryUpdateStats:
    def test_update_stats(self, registry, sample_project):
        registry.register(str(sample_project))
        registry.update_stats(str(sample_project), nodes=200, edges=100, communities=10, health=92.5)
        entry = registry.get(str(sample_project))
        assert entry.nodes == 200
        assert entry.edges == 100
        assert entry.communities == 10
        assert entry.health == 92.5

    def test_update_stats_nonexistent_is_noop(self, registry):
        # Should not raise
        registry.update_stats("/nonexistent", nodes=1)


class TestRegistryList:
    def test_list_sorted_by_last_opened(self, registry, tmp_path):
        p1 = tmp_path / "proj1"
        p2 = tmp_path / "proj2"
        p1.mkdir()
        p2.mkdir()
        registry.register(str(p1))
        time.sleep(0.01)
        registry.register(str(p2))
        projects = registry.list()
        assert projects[0].path == str(p2)  # most recent first
        assert projects[1].path == str(p1)

    def test_list_max_projects_cap(self, registry, tmp_path):
        for i in range(25):
            p = tmp_path / f"proj{i}"
            p.mkdir()
            registry.register(str(p))
        projects = registry.list()
        assert len(projects) == 20  # default cap


class TestRegistryNeedsRescan:
    def test_needs_rescan_no_graph(self, registry, tmp_path):
        p = tmp_path / "empty-project"
        p.mkdir()
        registry.register(str(p))
        assert registry.needs_rescan(str(p)) is True

    def test_needs_rescan_graph_exists_no_manifest(self, registry, sample_project):
        registry.register(str(sample_project))
        # graph.json exists but no manifest → needs rescan (first time)
        assert registry.needs_rescan(str(sample_project)) is True

    def test_needs_rescan_with_matching_manifest(self, registry, sample_project):
        # Create a manifest where the recorded mtime matches the file's current mtime
        # → needs_rescan should return False (manifest is up to date)
        src = sample_project / "hello.py"
        src.write_text("print('hello')")
        manifest = {"hello.py": {"hash": "abc", "mtime": src.stat().st_mtime}}
        (sample_project / "atlas-out" / "manifest.json").write_text(json.dumps(manifest))
        registry.register(str(sample_project))
        # Manifest mtime matches file mtime → no rescan needed
        assert registry.needs_rescan(str(sample_project)) is False

    def test_needs_rescan_with_stale_manifest(self, registry, sample_project):
        # Create a manifest with an OLD mtime → file is newer → needs rescan
        src = sample_project / "hello.py"
        src.write_text("print('hello')")
        manifest = {"hello.py": {"hash": "abc", "mtime": 0}}  # mtime=0 = stale
        (sample_project / "atlas-out" / "manifest.json").write_text(json.dumps(manifest))
        registry.register(str(sample_project))
        assert registry.needs_rescan(str(sample_project)) is True
