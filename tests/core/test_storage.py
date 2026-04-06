from pathlib import Path

from atlas.core.storage import LocalStorage


def test_write_and_read(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth\n\nAuth module.")
    content = s.read("wiki/concepts/auth.md")
    assert content == "# Auth\n\nAuth module."


def test_read_nonexistent(tmp_path):
    s = LocalStorage(root=tmp_path)
    assert s.read("wiki/nope.md") is None


def test_list_files(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth")
    s.write("wiki/concepts/billing.md", "# Billing")
    s.write("wiki/projects/acme.md", "# Acme")
    result = s.list("wiki/concepts/")
    assert sorted(result) == ["wiki/concepts/auth.md", "wiki/concepts/billing.md"]


def test_list_with_suffix_filter(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth")
    s.write("wiki/concepts/_template.md", "# Template")
    result = s.list("wiki/concepts/", exclude_prefix="_")
    assert result == ["wiki/concepts/auth.md"]


def test_delete(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth")
    s.delete("wiki/concepts/auth.md")
    assert s.read("wiki/concepts/auth.md") is None


def test_exists(tmp_path):
    s = LocalStorage(root=tmp_path)
    assert not s.exists("wiki/concepts/auth.md")
    s.write("wiki/concepts/auth.md", "# Auth")
    assert s.exists("wiki/concepts/auth.md")


def test_mtime(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth")
    mtime = s.mtime("wiki/concepts/auth.md")
    assert mtime > 0


def test_hash(tmp_path):
    s = LocalStorage(root=tmp_path)
    s.write("wiki/concepts/auth.md", "# Auth")
    h = s.hash("wiki/concepts/auth.md")
    assert len(h) == 64  # SHA256 hex digest
    # Same content = same hash
    s.write("wiki/concepts/auth2.md", "# Auth")
    assert s.hash("wiki/concepts/auth2.md") == h
