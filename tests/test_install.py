"""Tests for atlas install — multi-platform skill deployment."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from atlas.install import (
    detect_platforms,
    install_skills,
    uninstall_skills,
    install_claude_hook,
    uninstall_claude_hook,
    PLATFORM_CONFIG,
)


def test_detect_claude(tmp_path):
    """Detects Claude Code when ~/.claude/ exists."""
    (tmp_path / ".claude").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        platforms = detect_platforms()
    assert "claude" in platforms


def test_detect_codex(tmp_path):
    """Detects Codex when ~/.codex/ exists."""
    (tmp_path / ".codex").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        platforms = detect_platforms()
    assert "codex" in platforms


def test_detect_cursor(tmp_path):
    """Detects Cursor when ~/.cursor/ exists."""
    (tmp_path / ".cursor").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        platforms = detect_platforms()
    assert "cursor" in platforms


def test_detect_hermes(tmp_path):
    """Detects Hermes when ~/.hermes/ exists."""
    (tmp_path / ".hermes").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        platforms = detect_platforms()
    assert "hermes" in platforms


def test_detect_nothing(tmp_path):
    """Returns empty list when no platforms detected."""
    with patch("atlas.install.Path.home", return_value=tmp_path):
        platforms = detect_platforms()
    assert platforms == []


def test_install_skills_claude(tmp_path):
    """Install creates symlinks in ~/.claude/skills/ for Claude Code."""
    (tmp_path / ".claude").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        install_skills(platform="claude")

    skills_dir = tmp_path / ".claude" / "skills"
    expected_skills = ["atlas-start", "atlas-scan", "atlas-query", "atlas-ingest", "atlas-progress", "atlas-finish", "atlas-health"]
    for skill_name in expected_skills:
        skill_file = skills_dir / skill_name / "SKILL.md"
        assert skill_file.exists(), f"Missing skill: {skill_name}"


def test_install_skills_codex(tmp_path):
    """Install creates symlinks in ~/.agents/skills/ for Codex."""
    (tmp_path / ".codex").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        install_skills(platform="codex")

    skills_dir = tmp_path / ".agents" / "skills"
    assert (skills_dir / "atlas-start" / "SKILL.md").exists()


def test_install_skills_hermes(tmp_path):
    """Install creates symlinks in ~/.hermes/skills/ for Hermes."""
    (tmp_path / ".hermes").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        install_skills(platform="hermes")

    skills_dir = tmp_path / ".hermes" / "skills"
    assert (skills_dir / "atlas-start" / "SKILL.md").exists()


def test_uninstall_skills(tmp_path):
    """Uninstall removes the skill symlinks."""
    (tmp_path / ".claude").mkdir()
    with patch("atlas.install.Path.home", return_value=tmp_path):
        install_skills(platform="claude")
        uninstall_skills(platform="claude")

    skills_dir = tmp_path / ".claude" / "skills"
    for name in ["atlas-start", "atlas-scan", "atlas-query", "atlas-ingest", "atlas-progress", "atlas-finish", "atlas-health"]:
        assert not (skills_dir / name / "SKILL.md").exists()


def test_install_claude_hook(tmp_path):
    """Install writes PreToolUse hook to .claude/settings.json."""
    project = tmp_path / "myproject"
    project.mkdir()
    install_claude_hook(project)

    settings = json.loads((project / ".claude" / "settings.json").read_text())
    hooks = settings.get("hooks", {}).get("PreToolUse", [])
    assert any("atlas" in json.dumps(h) for h in hooks)


def test_install_claude_hook_idempotent(tmp_path):
    """Second install doesn't duplicate the hook."""
    project = tmp_path / "myproject"
    project.mkdir()
    install_claude_hook(project)
    install_claude_hook(project)

    settings = json.loads((project / ".claude" / "settings.json").read_text())
    hooks = settings["hooks"]["PreToolUse"]
    atlas_hooks = [h for h in hooks if "atlas" in json.dumps(h)]
    assert len(atlas_hooks) == 1


def test_uninstall_claude_hook(tmp_path):
    """Uninstall removes the hook from settings.json."""
    project = tmp_path / "myproject"
    project.mkdir()
    install_claude_hook(project)
    uninstall_claude_hook(project)

    settings = json.loads((project / ".claude" / "settings.json").read_text())
    hooks = settings.get("hooks", {}).get("PreToolUse", [])
    assert not any("atlas" in json.dumps(h) for h in hooks)
