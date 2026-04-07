"""Tests for the 5 project management API routes."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from atlas.core.registry import ProjectRegistry
from atlas.server.app import create_app
from atlas.server.deps import create_engine_set, EventBus, ScanStatus


@pytest.fixture
def project_dir(tmp_path):
    """A project directory with some scannable files."""
    p = tmp_path / "test-project"
    for d in ["wiki/concepts", "raw/untracked"]:
        (p / d).mkdir(parents=True)
    (p / "wiki" / "index.md").write_text("# Index\n")
    (p / "hello.py").write_text("# hello\ndef greet():\n    return 'hi'\n")
    return p


@pytest.fixture
def second_project(tmp_path):
    """A second project directory."""
    p = tmp_path / "second-project"
    for d in ["wiki/concepts", "raw/untracked"]:
        (p / d).mkdir(parents=True)
    (p / "wiki" / "index.md").write_text("# Second\n")
    (p / "world.py").write_text("# world\ndef world():\n    return 'world'\n")
    return p


@pytest.fixture
def registry(tmp_path):
    return ProjectRegistry(config_dir=tmp_path / ".atlas")


@pytest.fixture
def scan_status():
    return ScanStatus()


@pytest.fixture
def client(project_dir, registry, scan_status):
    engines = create_engine_set(project_dir)
    event_bus = EventBus()
    app = create_app(engines=engines, event_bus=event_bus)
    # Attach registry and scan_status to app state for routes
    app.state.registry = registry
    app.state.scan_status = scan_status
    return TestClient(app)


class TestGetProjects:
    def test_empty_registry(self, client):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert data["projects"] == []

    def test_with_registered_projects(self, client, registry, project_dir):
        registry.register(str(project_dir))
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "test-project"


class TestPostProjectsOpen:
    def test_open_new_project(self, client, project_dir):
        resp = client.post("/api/projects/open", json={"path": str(project_dir)})
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"]["path"] == str(project_dir)
        assert data["project"]["name"] == "test-project"

    def test_open_nonexistent_path(self, client):
        resp = client.post("/api/projects/open", json={"path": "/nonexistent/path"})
        assert resp.status_code in (400, 404, 422)

    def test_open_registers_project(self, client, registry, project_dir):
        client.post("/api/projects/open", json={"path": str(project_dir)})
        assert registry.get(str(project_dir)) is not None


class TestPostProjectsSwitch:
    def test_switch_to_registered_project(self, client, registry, project_dir, second_project):
        # Register both projects
        registry.register(str(project_dir))
        registry.register(str(second_project))
        resp = client.post("/api/projects/switch", json={"path": str(second_project)})
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"]["name"] == "second-project"

    def test_switch_to_nonexistent_project(self, client):
        resp = client.post("/api/projects/switch", json={"path": "/nonexistent"})
        assert resp.status_code in (400, 404, 422)


class TestDeleteProject:
    def test_remove_registered_project(self, client, registry, project_dir):
        registry.register(str(project_dir))
        # URL-encode the path
        import urllib.parse
        encoded = urllib.parse.quote(str(project_dir), safe="")
        resp = client.request("DELETE", f"/api/projects/{encoded}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["removed"] is True

    def test_remove_nonexistent(self, client):
        import urllib.parse
        encoded = urllib.parse.quote("/nonexistent", safe="")
        resp = client.request("DELETE", f"/api/projects/{encoded}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["removed"] is False


class TestScanStatusEndpoint:
    def test_idle_status(self, client):
        resp = client.get("/api/scan/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] is False
        assert data["message"] == "Idle"

    def test_active_status(self, client, scan_status):
        scan_status.start("Scanning test-project")
        resp = client.get("/api/scan/status")
        data = resp.json()
        assert data["active"] is True
        assert "test-project" in data["message"]
