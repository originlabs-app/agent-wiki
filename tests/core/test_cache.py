import json

from atlas.core.cache import CacheEngine
from atlas.core.models import Extraction, Node, Edge
from atlas.core.storage import LocalStorage


def test_check_returns_miss_for_new_file(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/doc.md", "# Hello")
    cache = CacheEngine(storage)
    hit = cache.check("raw/doc.md")
    assert hit is None


def test_save_and_check_returns_hit(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/doc.md", "# Hello")
    cache = CacheEngine(storage)
    extraction = Extraction(
        nodes=[Node(id="hello", label="Hello", type="document", source_file="raw/doc.md")],
        edges=[],
    )
    cache.save("raw/doc.md", extraction)
    hit = cache.check("raw/doc.md")
    assert hit is not None
    assert len(hit.nodes) == 1
    assert hit.nodes[0].id == "hello"


def test_cache_invalidated_on_content_change(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/doc.md", "# Hello")
    cache = CacheEngine(storage)
    extraction = Extraction(nodes=[], edges=[])
    cache.save("raw/doc.md", extraction)
    # Change file content
    storage.write("raw/doc.md", "# Changed")
    hit = cache.check("raw/doc.md")
    assert hit is None  # hash changed


def test_manifest_persists(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/doc.md", "# Hello")
    cache = CacheEngine(storage)
    extraction = Extraction(nodes=[], edges=[])
    cache.save("raw/doc.md", extraction)

    # Load a new CacheEngine instance — should read manifest from disk
    cache2 = CacheEngine(storage)
    hit = cache2.check("raw/doc.md")
    assert hit is not None


def test_detect_changed_files(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/a.md", "# A")
    storage.write("raw/b.md", "# B")
    cache = CacheEngine(storage)
    cache.save("raw/a.md", Extraction())
    cache.save("raw/b.md", Extraction())
    # Change a.md
    storage.write("raw/a.md", "# A modified")
    changed = cache.detect_changed(["raw/a.md", "raw/b.md"])
    assert "raw/a.md" in changed
    assert "raw/b.md" not in changed


def test_detect_new_files(tmp_path):
    storage = LocalStorage(root=tmp_path)
    storage.write("raw/a.md", "# A")
    cache = CacheEngine(storage)
    storage.write("raw/new.md", "# New")
    changed = cache.detect_changed(["raw/a.md", "raw/new.md"])
    assert "raw/new.md" in changed
    assert "raw/a.md" in changed  # never cached
