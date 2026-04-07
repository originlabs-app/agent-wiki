"""Tests for EngineSet rebuild and ScanStatus tracking."""
import json
from pathlib import Path

import pytest

from atlas.server.deps import create_engine_set, ScanStatus


@pytest.fixture
def project_a(tmp_path):
    p = tmp_path / "project-a"
    for d in ["wiki/concepts", "raw/untracked"]:
        (p / d).mkdir(parents=True)
    (p / "wiki" / "index.md").write_text("# Index A\n")
    (p / "hello.py").write_text("print('hello')\n")
    return p


@pytest.fixture
def project_b(tmp_path):
    p = tmp_path / "project-b"
    for d in ["wiki/concepts", "raw/untracked"]:
        (p / d).mkdir(parents=True)
    (p / "wiki" / "index.md").write_text("# Index B\n")
    (p / "world.py").write_text("print('world')\n")
    return p


class TestCreateEngineSet:
    def test_different_roots_give_different_engines(self, project_a, project_b):
        es_a = create_engine_set(project_a)
        es_b = create_engine_set(project_b)
        assert es_a.root != es_b.root
        assert es_a.root == project_a
        assert es_b.root == project_b


class TestScanStatus:
    def test_initial_state(self):
        status = ScanStatus()
        assert status.active is False
        assert status.progress == 0.0
        assert status.message == "Idle"

    def test_start(self):
        status = ScanStatus()
        status.start("Scanning project-a")
        assert status.active is True
        assert status.progress == 0.0
        assert status.message == "Scanning project-a"

    def test_update_progress(self):
        status = ScanStatus()
        status.start("Scanning")
        status.update(0.5, "50% complete")
        assert status.progress == 0.5
        assert status.message == "50% complete"

    def test_finish(self):
        status = ScanStatus()
        status.start("Scanning")
        status.update(0.5, "halfway")
        status.finish()
        assert status.active is False
        assert status.progress == 1.0
        assert status.message == "Complete"

    def test_to_dict(self):
        status = ScanStatus()
        status.start("Working")
        d = status.to_dict()
        assert d["active"] is True
        assert "progress" in d
        assert "message" in d
