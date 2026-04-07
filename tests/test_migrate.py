"""Tests for atlas migrate — agent-wiki v1 -> Atlas migration."""
from pathlib import Path
from unittest.mock import patch

import pytest

from atlas.migrate import detect_wiki_v1, migrate


def _make_wiki_v1(root: Path) -> None:
    """Create a minimal agent-wiki v1 structure."""
    (root / "wiki" / "projects").mkdir(parents=True)
    (root / "wiki" / "concepts").mkdir(parents=True)
    (root / "wiki" / "sources").mkdir(parents=True)
    (root / "wiki" / "decisions").mkdir(parents=True)
    (root / "raw" / "untracked").mkdir(parents=True)
    (root / "raw" / "ingested").mkdir(parents=True)

    (root / "AGENTS.md").write_text("# Knowledge Base Schema\n\nA wiki.\n")
    (root / "wiki" / "index.md").write_text("---\ntype: wiki-index\n---\n\n# Wiki Index\n")
    (root / "wiki" / "log.md").write_text("# Log\n")
    (root / "wiki" / "projects" / "acme.md").write_text(
        "---\ntype: wiki-page\ntitle: Acme\n---\n\n# Acme\n\nA project. See [[auth]].\n"
    )
    (root / "wiki" / "concepts" / "auth.md").write_text(
        "---\ntype: wiki-concept\ntitle: Authentication\ntags: [auth]\n---\n\n# Auth\n\nJWT-based. Related to [[billing]].\n"
    )
    (root / "wiki" / "concepts" / "billing.md").write_text(
        "---\ntype: wiki-concept\ntitle: Billing\ntags: [payments]\n---\n\n# Billing\n\nStripe. See [[auth]].\n"
    )


def test_detect_wiki_v1(tmp_path):
    _make_wiki_v1(tmp_path)
    result = detect_wiki_v1(tmp_path)
    assert result is not None
    assert result["wiki_dir"] == str(tmp_path / "wiki")
    assert result["page_count"] >= 3


def test_detect_wiki_v1_missing(tmp_path):
    result = detect_wiki_v1(tmp_path)
    assert result is None


def test_migrate_builds_graph(tmp_path):
    _make_wiki_v1(tmp_path)
    report = migrate(tmp_path)

    assert report["status"] == "success"
    assert report["nodes"] > 0
    assert report["edges"] >= 0

    # graph.json should exist
    assert (tmp_path / "atlas-out" / "graph.json").exists()


def test_migrate_preserves_wiki(tmp_path):
    """Migration must not modify existing wiki content."""
    _make_wiki_v1(tmp_path)
    original_auth = (tmp_path / "wiki" / "concepts" / "auth.md").read_text()

    migrate(tmp_path)

    assert (tmp_path / "wiki" / "concepts" / "auth.md").read_text() == original_auth


def test_migrate_installs_skills(tmp_path):
    """Migration installs Atlas skills if a platform is detected."""
    _make_wiki_v1(tmp_path)
    (tmp_path / ".claude").mkdir()

    with patch("atlas.migrate.Path.home", return_value=tmp_path):
        report = migrate(tmp_path, install_skills=True)

    assert "skills_installed" in report
    assert report["skills_installed"] > 0


def test_migrate_idempotent(tmp_path):
    """Running migrate twice doesn't break anything."""
    _make_wiki_v1(tmp_path)
    migrate(tmp_path)
    report = migrate(tmp_path)
    assert report["status"] == "success"
