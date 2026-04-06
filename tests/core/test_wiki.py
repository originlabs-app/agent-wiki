from atlas.core.wiki import WikiEngine


def test_list_pages(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    pages = wiki.list_pages()
    slugs = [p.slug for p in pages]
    assert "acme" in slugs
    assert "auth" in slugs
    assert "billing" in slugs


def test_list_pages_by_type(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    concepts = wiki.list_pages(type="wiki-concept")
    assert all(p.type == "wiki-concept" for p in concepts)
    assert len(concepts) == 2


def test_read_page(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    page = wiki.read("wiki/concepts/auth.md")
    assert page is not None
    assert page.title == "Authentication"
    assert page.type == "wiki-concept"
    assert "JWT" in page.content
    assert page.frontmatter["tags"] == ["auth", "security"]


def test_read_nonexistent(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    assert wiki.read("wiki/concepts/nope.md") is None


def test_write_page(tmp_storage):
    wiki = WikiEngine(tmp_storage)
    wiki.write(
        path="wiki/concepts/caching.md",
        content="# Caching\n\nRedis-based caching layer.",
        frontmatter={"type": "wiki-concept", "title": "Caching", "confidence": "medium", "tags": ["cache", "redis"]},
    )
    page = wiki.read("wiki/concepts/caching.md")
    assert page.title == "Caching"
    assert page.frontmatter["tags"] == ["cache", "redis"]
    assert "Redis-based" in page.content


def test_write_preserves_frontmatter_order(tmp_storage):
    wiki = WikiEngine(tmp_storage)
    wiki.write(
        path="wiki/concepts/test.md",
        content="# Test\n\nBody.",
        frontmatter={"type": "wiki-concept", "title": "Test", "confidence": "high"},
    )
    raw = tmp_storage.read("wiki/concepts/test.md")
    assert raw.startswith("---\n")
    assert "type: wiki-concept" in raw


def test_search(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    results = wiki.search("JWT")
    assert len(results) >= 1
    assert any(p.slug == "auth" for p in results)


def test_search_no_results(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    results = wiki.search("nonexistent_term_xyz")
    assert results == []


def test_extract_wikilinks(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    page = wiki.read("wiki/concepts/auth.md")
    assert "billing" in page.wikilinks
    assert "wiki/projects/acme" in page.wikilinks


def test_all_wikilinks(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    links = wiki.all_wikilinks()
    # Returns dict: page_path -> [list of wikilink targets]
    assert "wiki/concepts/auth.md" in links
    assert "billing" in links["wiki/concepts/auth.md"]


def test_backlinks(sample_wiki):
    wiki = WikiEngine(sample_wiki)
    backlinks = wiki.backlinks("billing")
    assert "wiki/concepts/auth.md" in backlinks


def test_delete_page(tmp_storage):
    wiki = WikiEngine(tmp_storage)
    wiki.write("wiki/concepts/temp.md", "# Temp", frontmatter={"type": "wiki-concept", "title": "Temp"})
    assert wiki.read("wiki/concepts/temp.md") is not None
    wiki.delete("wiki/concepts/temp.md")
    assert wiki.read("wiki/concepts/temp.md") is None
