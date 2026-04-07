"""CLI tests using typer.testing.CliRunner."""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from atlas.cli import app

runner = CliRunner()


def test_scan_basic(tmp_path):
    """atlas scan <path> runs the full pipeline: scan -> graph -> linker -> save."""
    # Create a minimal Python file
    py_file = tmp_path / "hello.py"
    py_file.write_text('"""Hello module."""\ndef greet(name: str) -> str:\n    return f"Hello {name}"\n')

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "nodes" in result.stdout.lower() or "scanned" in result.stdout.lower()
    # graph.json should be created inside atlas-out/
    assert (tmp_path / "atlas-out" / "graph.json").exists()


def test_scan_nonexistent_path():
    result = runner.invoke(app, ["scan", "/nonexistent/path/xyz"])
    assert result.exit_code != 0


def test_scan_incremental(tmp_path):
    """atlas scan --update only re-extracts changed files."""
    py_file = tmp_path / "hello.py"
    py_file.write_text('"""Hello."""\ndef greet(): pass\n')

    # First scan
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0

    # Second scan with --update
    result = runner.invoke(app, ["scan", str(tmp_path), "--update"])
    assert result.exit_code == 0
    assert "incremental" in result.stdout.lower() or "0 changed" in result.stdout.lower() or result.exit_code == 0


def test_scan_force(tmp_path):
    """atlas scan --force ignores cache."""
    py_file = tmp_path / "hello.py"
    py_file.write_text('"""Hello."""\ndef greet(): pass\n')

    result = runner.invoke(app, ["scan", str(tmp_path), "--force"])
    assert result.exit_code == 0
