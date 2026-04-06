"""Shared test fixtures for the server test suite."""
from pathlib import Path

import pytest

from atlas.server.deps import create_engine_set, EngineSet, EventBus


@pytest.fixture
def engine_root(tmp_path):
    """Create a temp directory with wiki + raw structure."""
    for d in ["wiki/projects", "wiki/concepts", "wiki/decisions", "wiki/sources", "raw/untracked", "raw/ingested"]:
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "wiki" / "index.md").write_text("# Wiki Index\n")
    (tmp_path / "wiki" / "log.md").write_text("# Wiki Log\n")
    return tmp_path


@pytest.fixture
def engines(engine_root) -> EngineSet:
    """A fully initialized EngineSet backed by a temp directory."""
    return create_engine_set(engine_root)


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def seeded_engines(engines) -> EngineSet:
    """EngineSet with pre-populated wiki pages and graph data."""
    engines.wiki.write(
        "wiki/concepts/auth.md",
        "# Authentication\n\nHandles JWT tokens. See [[billing]].",
        frontmatter={"type": "wiki-concept", "title": "Authentication", "confidence": "high", "tags": ["auth", "security"]},
    )
    engines.wiki.write(
        "wiki/concepts/billing.md",
        "# Billing\n\nStripe integration. See [[auth]].",
        frontmatter={"type": "wiki-concept", "title": "Billing", "confidence": "medium", "tags": ["billing"]},
    )
    engines.wiki.write(
        "wiki/projects/acme.md",
        "# Acme\n\nTest project.",
        frontmatter={"type": "wiki-page", "title": "Acme", "project": "Acme", "confidence": "high"},
    )
    # Sync wiki to graph so we have nodes and edges
    engines.linker.sync_wiki_to_graph()
    return engines
