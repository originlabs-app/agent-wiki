"""Migration from agent-wiki v1 to Atlas v2."""
from __future__ import annotations

from pathlib import Path


def detect_wiki_v1(root: Path) -> dict | None:
    """Detect an existing agent-wiki v1 installation.

    Returns a dict with wiki metadata, or None if not found.
    Looks for: wiki/ directory with index.md, raw/ directory, AGENTS.md.
    """
    wiki_dir = root / "wiki"
    if not wiki_dir.is_dir():
        return None

    index = wiki_dir / "index.md"
    if not index.is_file():
        return None

    # Count pages
    page_count = 0
    for md in wiki_dir.rglob("*.md"):
        if md.name not in ("index.md", "log.md", "_template.md"):
            page_count += 1

    has_raw = (root / "raw").is_dir()
    has_agents_md = (root / "AGENTS.md").is_file()
    has_log = (wiki_dir / "log.md").is_file()

    return {
        "wiki_dir": str(wiki_dir),
        "raw_dir": str(root / "raw") if has_raw else None,
        "agents_md": has_agents_md,
        "page_count": page_count,
        "has_log": has_log,
    }


def migrate(
    root: Path,
    install_skills: bool = False,
) -> dict:
    """Migrate from agent-wiki v1 to Atlas v2.

    Steps:
    1. Detect existing wiki structure
    2. Scan wiki to build initial graph.json
    3. Optionally install Atlas skills for detected platforms
    4. Preserve all existing content — zero loss

    Returns a report dict with migration results.
    """
    from atlas.core.graph import GraphEngine
    from atlas.core.linker import Linker
    from atlas.core.storage import LocalStorage
    from atlas.core.wiki import WikiEngine

    report: dict = {"status": "success", "nodes": 0, "edges": 0, "pages_found": 0}

    # Step 1: Detect
    detection = detect_wiki_v1(root)
    if detection is None:
        report["status"] = "no_wiki_found"
        report["message"] = f"No agent-wiki v1 found at {root}. Expected wiki/ directory with index.md."
        return report

    report["pages_found"] = detection["page_count"]

    # Step 2: Build graph from wiki
    storage = LocalStorage(root=root)
    wiki = WikiEngine(storage)
    graph = GraphEngine()
    linker = Linker(wiki=wiki, graph=graph)

    # Sync wiki -> graph (creates nodes for pages, edges for wikilinks)
    changes = linker.sync_wiki_to_graph()
    report["nodes"] = graph.node_count
    report["edges"] = graph.edge_count
    report["graph_changes"] = len(changes)

    # Save graph
    out = root / "atlas-out"
    out.mkdir(parents=True, exist_ok=True)
    graph.save(out / "graph.json")
    report["graph_path"] = str(out / "graph.json")

    # Step 3: Install skills if requested
    if install_skills:
        from atlas.install import detect_platforms, install_skills as _install

        platforms = detect_platforms()
        total_installed = 0
        for platform in platforms:
            installed = _install(platform=platform)
            total_installed += len(installed)
        report["skills_installed"] = total_installed
        report["platforms"] = platforms

    return report
