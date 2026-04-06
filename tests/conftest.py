"""Shared test fixtures."""
import shutil
from pathlib import Path

import pytest

from atlas.core.models import Node, Edge, Extraction, Page
from atlas.core.storage import LocalStorage

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_storage(tmp_path):
    """A LocalStorage instance pointed at a temp directory with wiki/ and raw/ structure."""
    wiki = tmp_path / "wiki"
    raw = tmp_path / "raw"
    for d in [wiki / "projects", wiki / "concepts", wiki / "decisions", wiki / "sources", raw / "untracked", raw / "ingested"]:
        d.mkdir(parents=True)
    (wiki / "index.md").write_text("# Wiki Index\n")
    (wiki / "log.md").write_text("# Wiki Log\n")
    return LocalStorage(root=tmp_path)


@pytest.fixture
def sample_wiki(tmp_storage):
    """A LocalStorage pre-populated with sample pages."""
    src = FIXTURES / "sample_wiki"
    if src.exists():
        shutil.copytree(src, tmp_storage.root / "wiki", dirs_exist_ok=True)
    return tmp_storage


@pytest.fixture
def sample_extraction():
    """A minimal Extraction for testing graph merge."""
    return Extraction(
        nodes=[
            Node(id="auth", label="Auth Module", type="code", source_file="src/auth.py"),
            Node(id="db", label="Database", type="code", source_file="src/db.py"),
            Node(id="api", label="API", type="code", source_file="src/api.py"),
        ],
        edges=[
            Edge(source="api", target="auth", relation="imports", confidence="EXTRACTED"),
            Edge(source="api", target="db", relation="imports", confidence="EXTRACTED"),
            Edge(source="auth", target="db", relation="calls", confidence="INFERRED"),
        ],
    )
