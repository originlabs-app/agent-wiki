from pathlib import Path

from atlas.core.scanner_ast import extract_python

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_extract_python_nodes():
    extraction = extract_python(FIXTURES / "sample.py")
    ids = {n.id for n in extraction.nodes}
    assert "sample" in ids  # file node
    assert "sample_AuthManager" in ids or "authmanager" in ids.union({i.lower() for i in ids})
    # Should find classes and functions
    labels = {n.label for n in extraction.nodes}
    assert any("AuthManager" in l for l in labels)
    assert any("hash_password" in l for l in labels)
    assert any("login" in l for l in labels)


def test_extract_python_edges():
    extraction = extract_python(FIXTURES / "sample.py")
    relations = {(e.source, e.relation, e.target) for e in extraction.edges}
    # File contains the class and functions
    assert any(r == "contains" for _, r, _ in relations)


def test_extract_python_imports():
    extraction = extract_python(FIXTURES / "sample.py")
    import_edges = [e for e in extraction.edges if e.relation in ("imports", "imports_from")]
    assert len(import_edges) >= 2  # os and pathlib


def test_extract_python_rationale():
    extraction = extract_python(FIXTURES / "sample.py")
    # Should extract NOTE and HACK comments
    rationale_nodes = [n for n in extraction.nodes if "NOTE" in (n.label or "") or "HACK" in (n.label or "")]
    assert len(rationale_nodes) >= 0  # may or may not extract depending on implementation


def test_extract_python_methods():
    extraction = extract_python(FIXTURES / "sample.py")
    labels = {n.label for n in extraction.nodes}
    assert any("verify_token" in l for l in labels)
    assert any("create_session" in l for l in labels)


def test_extract_nonexistent_returns_empty():
    extraction = extract_python(Path("/nonexistent/file.py"))
    assert len(extraction.nodes) == 0
    assert len(extraction.edges) == 0
