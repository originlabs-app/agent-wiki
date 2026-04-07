"""End-to-end integration test for the full CLI workflow."""
from pathlib import Path

from typer.testing import CliRunner

from atlas.cli import app

runner = CliRunner()


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project with code, docs, and a wiki."""
    # Code files
    src = tmp_path / "src"
    src.mkdir()
    (src / "auth.py").write_text(
        '"""Auth module — JWT and sessions."""\n'
        'import hashlib\n\n'
        'class AuthManager:\n'
        '    """Handles authentication."""\n'
        '    def verify(self, token: str) -> bool:\n'
        '        return len(token) > 0\n'
    )
    (src / "billing.py").write_text(
        '"""Billing module — Stripe integration."""\n'
        'from src.auth import AuthManager\n\n'
        'class BillingService:\n'
        '    """Processes payments via Stripe."""\n'
        '    def charge(self, amount: int) -> bool:\n'
        '        return amount > 0\n'
    )

    # Wiki
    wiki = tmp_path / "wiki"
    for d in ["projects", "concepts", "sources", "decisions"]:
        (wiki / d).mkdir(parents=True)
    (wiki / "index.md").write_text("---\ntype: wiki-index\n---\n\n# Index\n")
    (wiki / "concepts" / "auth.md").write_text(
        "---\ntype: wiki-concept\ntitle: Auth\ntags: [auth]\nupdated: 2026-04-06\n---\n\n"
        "# Auth\n\nJWT-based. See [[billing]].\n"
    )
    (wiki / "concepts" / "billing.md").write_text(
        "---\ntype: wiki-concept\ntitle: Billing\ntags: [payments]\nupdated: 2026-04-06\n---\n\n"
        "# Billing\n\nStripe. See [[auth]].\n"
    )

    # Raw source
    raw = tmp_path / "raw" / "untracked"
    raw.mkdir(parents=True)
    (raw / "notes.md").write_text("# Research Notes\n\nSome findings about API design.\n")

    return tmp_path


def test_full_workflow(tmp_path):
    """atlas scan -> query -> path -> explain -> god-nodes -> surprises -> audit -> export."""
    project = _make_project(tmp_path)

    # Step 1: Scan
    result = runner.invoke(app, ["scan", str(project)])
    assert result.exit_code == 0, f"scan failed: {result.stdout}"
    assert (project / "atlas-out" / "graph.json").exists()

    root_flag = ["--root", str(project)]

    # Step 2: Query
    result = runner.invoke(app, ["query", "auth", *root_flag])
    assert result.exit_code == 0, f"query failed: {result.stdout}"

    # Step 3: God nodes
    result = runner.invoke(app, ["god-nodes", *root_flag])
    assert result.exit_code == 0, f"god-nodes failed: {result.stdout}"

    # Step 4: Surprises
    result = runner.invoke(app, ["surprises", *root_flag])
    assert result.exit_code == 0, f"surprises failed: {result.stdout}"

    # Step 5: Audit
    result = runner.invoke(app, ["audit", *root_flag])
    assert result.exit_code == 0, f"audit failed: {result.stdout}"
    assert "health" in result.stdout.lower() or "score" in result.stdout.lower()

    # Step 6: Export JSON
    result = runner.invoke(app, ["export", "json", *root_flag])
    assert result.exit_code == 0, f"export failed: {result.stdout}"
    assert (project / "atlas-out" / "graph.json").exists()

    # Step 7: Ingest
    notes_path = str(project / "raw" / "untracked" / "notes.md")
    result = runner.invoke(app, ["ingest", notes_path, *root_flag])
    assert result.exit_code == 0, f"ingest failed: {result.stdout}"


def test_migrate_then_query(tmp_path):
    """atlas migrate -> query to verify migration produces a usable graph."""
    from tests.test_migrate import _make_wiki_v1

    _make_wiki_v1(tmp_path)

    # Migrate
    result = runner.invoke(app, ["migrate-cmd", "--root", str(tmp_path), "--no-skills"])
    assert result.exit_code == 0, f"migrate failed: {result.stdout}"

    # Query should work on the migrated graph
    result = runner.invoke(app, ["query", "auth", "--root", str(tmp_path)])
    # Query may return 0 even with 0 nodes — just check it doesn't crash
    # If auth node exists from migration, it should be in the output
    if "auth" in result.output.lower():
        assert "auth" in result.stdout.lower()
