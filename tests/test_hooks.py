"""Tests for atlas git hooks — post-commit and post-checkout."""
from pathlib import Path
import pytest
from atlas.hooks import install, uninstall, status


def _make_git_repo(tmp_path: Path) -> Path:
    """Create a minimal .git directory."""
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)
    return tmp_path


def test_install_creates_hooks(tmp_path):
    repo = _make_git_repo(tmp_path)
    result = install(repo)
    assert "installed" in result
    assert (repo / ".git" / "hooks" / "post-commit").exists()
    assert (repo / ".git" / "hooks" / "post-checkout").exists()


def test_install_idempotent(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    result = install(repo)
    assert "already installed" in result


def test_uninstall_removes_hooks(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    result = uninstall(repo)
    assert "removed" in result


def test_status_not_installed(tmp_path):
    repo = _make_git_repo(tmp_path)
    result = status(repo)
    assert "not installed" in result


def test_status_after_install(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    result = status(repo)
    assert "installed" in result
    assert "not installed" not in result.replace("already installed", "")


def test_install_not_git_repo(tmp_path):
    with pytest.raises(RuntimeError, match="No git repository"):
        install(tmp_path)


def test_hook_appends_to_existing(tmp_path):
    """If a hook already exists from another tool, atlas appends."""
    repo = _make_git_repo(tmp_path)
    existing_hook = repo / ".git" / "hooks" / "post-commit"
    existing_hook.write_text("#!/bin/bash\necho 'existing hook'\n")

    install(repo)

    content = existing_hook.read_text()
    assert "existing hook" in content
    assert "atlas-hook" in content
