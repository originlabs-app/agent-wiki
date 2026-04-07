"""Tests for project-related Pydantic schemas."""
from atlas.server.schemas import (
    ProjectEntrySchema,
    ProjectOpenRequest,
    ProjectOpenResponse,
    ProjectSwitchRequest,
    ProjectSwitchResponse,
    ProjectRemoveResponse,
    ProjectListResponse,
    ScanStatusResponse,
)


def test_project_entry_schema():
    entry = ProjectEntrySchema(
        path="/tmp/proj",
        name="proj",
        last_opened="2026-04-07T10:00:00",
        nodes=100,
        edges=50,
        communities=5,
        health=85.0,
    )
    assert entry.path == "/tmp/proj"
    assert entry.name == "proj"
    assert entry.nodes == 100


def test_project_entry_defaults():
    entry = ProjectEntrySchema(path="/tmp/proj", name="proj")
    assert entry.nodes == 0
    assert entry.edges == 0
    assert entry.communities == 0
    assert entry.health == 0.0


def test_project_open_request():
    req = ProjectOpenRequest(path="/tmp/myproject")
    assert req.path == "/tmp/myproject"


def test_project_open_response():
    resp = ProjectOpenResponse(
        project=ProjectEntrySchema(path="/tmp/p", name="p"),
        scanned=True,
    )
    assert resp.scanned is True


def test_project_switch_request():
    req = ProjectSwitchRequest(path="/tmp/other")
    assert req.path == "/tmp/other"


def test_project_switch_response():
    resp = ProjectSwitchResponse(
        project=ProjectEntrySchema(path="/tmp/p", name="p"),
    )
    assert resp.project.name == "p"


def test_project_remove_response():
    resp = ProjectRemoveResponse(removed=True)
    assert resp.removed is True


def test_project_list_response():
    resp = ProjectListResponse(projects=[
        ProjectEntrySchema(path="/tmp/a", name="a"),
        ProjectEntrySchema(path="/tmp/b", name="b"),
    ])
    assert len(resp.projects) == 2


def test_scan_status_response_idle():
    resp = ScanStatusResponse(active=False, progress=0.0, message="Idle")
    assert resp.active is False


def test_scan_status_response_scanning():
    resp = ScanStatusResponse(active=True, progress=0.45, message="Scanning src/...")
    assert resp.active is True
    assert resp.progress == 0.45
