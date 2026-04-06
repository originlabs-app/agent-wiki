from atlas.core.ingest import IngestEngine, detect_url_type


def test_detect_url_type_arxiv():
    assert detect_url_type("https://arxiv.org/abs/1706.03762") == "arxiv"


def test_detect_url_type_tweet():
    assert detect_url_type("https://x.com/karpathy/status/123456") == "tweet"
    assert detect_url_type("https://twitter.com/someone/status/789") == "tweet"


def test_detect_url_type_github():
    assert detect_url_type("https://github.com/safishamsi/graphify") == "github"


def test_detect_url_type_pdf():
    assert detect_url_type("https://example.com/paper.pdf") == "pdf"


def test_detect_url_type_image():
    assert detect_url_type("https://example.com/diagram.png") == "image"
    assert detect_url_type("https://example.com/photo.jpg") == "image"


def test_detect_url_type_webpage():
    assert detect_url_type("https://example.com/blog/article") == "webpage"


def test_slugify_url():
    from atlas.core.ingest import slugify_url
    assert slugify_url("https://arxiv.org/abs/1706.03762") == "arxiv-org-abs-1706-03762"
    assert slugify_url("https://x.com/karpathy/status/123") == "x-com-karpathy-status-123"


def test_build_frontmatter():
    from atlas.core.ingest import build_frontmatter
    fm = build_frontmatter(
        url="https://arxiv.org/abs/1706.03762",
        url_type="arxiv",
        title="Attention Is All You Need",
        author="Vaswani et al.",
    )
    assert fm["source_url"] == "https://arxiv.org/abs/1706.03762"
    assert fm["type"] == "arxiv"
    assert fm["title"] == "Attention Is All You Need"
    assert fm["author"] == "Vaswani et al."
    assert "captured_at" in fm


def test_ingest_local_file(tmp_path):
    # Create a local file
    src = tmp_path / "raw" / "untracked"
    src.mkdir(parents=True)
    (src / "notes.md").write_text("# My Notes\n\nSome content.")

    from atlas.core.storage import LocalStorage
    storage = LocalStorage(root=tmp_path)
    engine = IngestEngine(storage)
    result = engine.ingest_file("raw/untracked/notes.md", title="My Notes")
    assert result is not None
    assert result.endswith(".md")
    # Should be moved to raw/ingested/
    content = storage.read(result)
    assert "My Notes" in content
