"""Unit tests for scanner_semantic.extract_markdown()."""
from pathlib import Path

from atlas.core.scanner_semantic import extract_markdown
from atlas.core.models import Extraction


def test_extract_markdown_file_node(tmp_path):
    """Should always produce a file node with stem as id."""
    f = tmp_path / "readme.md"
    f.write_text("# Hello\n\nSome text.")
    extraction = extract_markdown(f)
    assert len(extraction.nodes) >= 1
    assert extraction.nodes[0].id == "readme"
    assert extraction.nodes[0].label == "readme.md"
    assert extraction.nodes[0].type == "document"


def test_extract_markdown_headings(tmp_path):
    """Should extract headings as child concept nodes."""
    f = tmp_path / "doc.md"
    f.write_text("# Title\n\n## Section A\n\n### Section B\n\nBody text.")
    extraction = extract_markdown(f)
    ids = {n.id for n in extraction.nodes}
    labels = {n.label for n in extraction.nodes}
    # File node
    assert "doc" in ids
    # Headings
    assert any("section_a" in nid for nid in ids)
    assert any("Section B" in l for l in labels)


def test_extract_markdown_heading_contains_edges(tmp_path):
    """Headings should be linked to the file node via 'contains' edges."""
    f = tmp_path / "notes.md"
    f.write_text("# Notes\n\n## Architecture\n\n## Testing\n\nContent.")
    extraction = extract_markdown(f)
    contains = [e for e in extraction.edges if e.relation == "contains"]
    assert len(contains) >= 2  # architecture + testing


def test_extract_markdown_wikilinks(tmp_path):
    """Should extract [[wikilinks]] as 'references' edges."""
    f = tmp_path / "page.md"
    f.write_text("# Page\n\nSee [[auth]] and [[billing]] for details.")
    extraction = extract_markdown(f)
    refs = [e for e in extraction.edges if e.relation == "references"]
    targets = {e.target for e in refs}
    assert "auth" in targets
    assert "billing" in targets


def test_extract_markdown_wikilink_with_alias(tmp_path):
    """Should handle [[target|display text]] syntax."""
    f = tmp_path / "aliases.md"
    f.write_text("# Aliases\n\nCheck [[authentication|Auth System]].")
    extraction = extract_markdown(f)
    refs = [e for e in extraction.edges if e.relation == "references"]
    targets = {e.target for e in refs}
    assert "authentication" in targets


def test_extract_markdown_wikilink_with_path(tmp_path):
    """Should handle [[projects/my-project]] paths — use last segment as slug."""
    f = tmp_path / "index.md"
    f.write_text("# Index\n\nRelated: [[projects/ara]] and [[decisions/2026-04-01-mvp]].")
    extraction = extract_markdown(f)
    refs = [e for e in extraction.edges if e.relation == "references"]
    targets = {e.target for e in refs}
    assert "ara" in targets
    assert "2026_04_01_mvp" in targets


def test_extract_markdown_no_self_reference(tmp_path):
    """Should not create edges from a file to itself."""
    f = tmp_path / "readme.md"
    f.write_text("# README\n\nSee also [[readme]].")
    extraction = extract_markdown(f)
    refs = [e for e in extraction.edges if e.relation == "references"]
    # The target "readme" should not produce an edge since it equals the file node id
    for e in refs:
        assert e.target != "readme"


def test_extract_markdown_duplicate_wikilinks(tmp_path):
    """Should not duplicate edges for the same wikilink target."""
    f = tmp_path / "dups.md"
    f.write_text("# Dups\n\nSee [[auth]] and again [[auth]].")
    extraction = extract_markdown(f)
    refs = [(e.source, e.target) for e in extraction.edges if e.relation == "references"]
    # Should have at most one edge from "dups" to "auth"
    auth_refs = [(s, t) for s, t in refs if t == "auth"]
    assert len(auth_refs) <= 1


def test_extract_markdown_nonexistent_file():
    """Should return empty extraction for non-existent file."""
    extraction = extract_markdown(Path("/nonexistent/file.md"))
    assert len(extraction.nodes) == 0
    assert len(extraction.edges) == 0


def test_extract_markdown_empty_file(tmp_path):
    """Empty file should produce just the file node."""
    f = tmp_path / "empty.md"
    f.write_text("")
    extraction = extract_markdown(f)
    assert len(extraction.nodes) == 1
    assert extraction.nodes[0].id == "empty"
    assert len(extraction.edges) == 0


def test_extract_markdown_unicode_error(tmp_path):
    """Should return empty extraction for binary/corrupt files."""
    f = tmp_path / "binary.md"
    f.write_bytes(b"\x80\x81\x82\x83\xff")
    extraction = extract_markdown(f)
    assert len(extraction.nodes) == 0
    assert len(extraction.edges) == 0


def test_extract_markdown_only_text_no_structure(tmp_path):
    """Plain text with no headings or links should just produce a file node."""
    f = tmp_path / "plain.md"
    f.write_text("Just some plain text without any markdown structure.")
    extraction = extract_markdown(f)
    assert len(extraction.nodes) == 1
    assert len(extraction.edges) == 0


def test_extract_markdown_source_file_set(tmp_path):
    """All nodes and the extraction should have source_file set."""
    f = tmp_path / "sourced.md"
    f.write_text("# Sourced\n\n## Sub\n\n[[link]].")
    extraction = extract_markdown(f)
    assert extraction.source_file == str(f)
    for node in extraction.nodes:
        assert node.source_file == str(f)


def test_extract_markdown_txt_treated_as_markdown(tmp_path):
    """The scanner routes .txt to extract_markdown — verify it works."""
    f = tmp_path / "notes.txt"
    f.write_text("# Notes\n\n## Section\n\n[[reference]].")
    extraction = extract_markdown(f)
    assert len(extraction.nodes) >= 2
    refs = [e for e in extraction.edges if e.relation == "references"]
    assert any(e.target == "reference" for e in refs)
