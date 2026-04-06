from pathlib import Path

from atlas.core.scanner import Scanner
from atlas.core.storage import LocalStorage
from atlas.core.cache import CacheEngine


def test_scan_python_file(tmp_path):
    storage = LocalStorage(root=tmp_path)
    # Copy fixture
    src = Path(__file__).parent.parent / "fixtures" / "sample.py"
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text(src.read_text())

    scanner = Scanner(storage=storage)
    extraction = scanner.scan(Path(tmp_path / "src"))
    assert len(extraction.nodes) > 0
    assert len(extraction.edges) > 0


def test_scan_markdown_file(tmp_path):
    storage = LocalStorage(root=tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "readme.md").write_text("# Project\n\nThis project uses [[auth]] and [[billing]].")

    scanner = Scanner(storage=storage)
    extraction = scanner.scan(Path(tmp_path / "docs"))
    assert len(extraction.nodes) >= 1  # at least the file node


def test_scan_with_cache(tmp_path):
    storage = LocalStorage(root=tmp_path)
    src = Path(__file__).parent.parent / "fixtures" / "sample.py"
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text(src.read_text())

    cache = CacheEngine(storage)
    scanner = Scanner(storage=storage, cache=cache)

    # First scan
    e1 = scanner.scan(Path(tmp_path / "src"))
    assert len(e1.nodes) > 0

    # Second scan (cached) — should return same results
    e2 = scanner.scan(Path(tmp_path / "src"))
    assert len(e2.nodes) == len(e1.nodes)


def test_scan_incremental(tmp_path):
    storage = LocalStorage(root=tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("def hello(): pass")
    (tmp_path / "src" / "b.py").write_text("def world(): pass")

    cache = CacheEngine(storage)
    scanner = Scanner(storage=storage, cache=cache)
    scanner.scan(Path(tmp_path / "src"))

    # Modify only a.py
    (tmp_path / "src" / "a.py").write_text("def hello_changed(): pass")
    e = scanner.scan(Path(tmp_path / "src"), incremental=True)
    # Should still produce results (from cache + re-extracted)
    assert len(e.nodes) >= 2


def test_scan_empty_dir(tmp_path):
    storage = LocalStorage(root=tmp_path)
    (tmp_path / "empty").mkdir()
    scanner = Scanner(storage=storage)
    extraction = scanner.scan(Path(tmp_path / "empty"))
    assert len(extraction.nodes) == 0
