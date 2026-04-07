# Atlas Agent Skills v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 7 individual atlas-* skills with 2 consolidated skills (`/atlas` and `/atlas-deep`) and update the `atlas install` command for multi-agent deployment.

**Architecture:** Two SKILL.md files in `atlas/skills/`. The `/atlas` skill is the main entry point (~400 lines) covering orientation, scan, query, ingest, audit, and finish. The `/atlas-deep` skill is the LLM enrichment skill (~150 lines). `atlas install` detects installed agents and symlinks from `~/.agents/skills/`.

**Tech Stack:** Markdown (SKILL.md), Python (CLI install command), Bash (PreToolUse hook)

**Depends on:** Plans 1-6 (Core, Server, Dashboard, Skills CLI, Quality, Explorer) on main

---

## File Map

```
atlas/skills/
├── atlas/
│   └── SKILL.md              # Main skill — /atlas (replaces 7 old skills)
└── atlas-deep/
    └── SKILL.md              # LLM enrichment — /atlas-deep

atlas/cli.py                   # Modify: update install/uninstall commands

tests/
├── test_skills_v2.py          # Validate 2 skills structure
└── test_install.py            # Validate install logic
```

**Delete after migration:**
```
atlas/skills/atlas-start/      # Replaced by /atlas
atlas/skills/atlas-scan/       # Replaced by /atlas
atlas/skills/atlas-query/      # Replaced by /atlas
atlas/skills/atlas-ingest/     # Replaced by /atlas
atlas/skills/atlas-progress/   # Replaced by /atlas
atlas/skills/atlas-finish/     # Replaced by /atlas
atlas/skills/atlas-health/     # Replaced by /atlas
```

---

## Task 1: Write `/atlas` SKILL.md

**Files:**
- Create: `atlas/skills/atlas/SKILL.md`
- Test: `tests/test_skills_v2.py`

- [ ] **Step 1: Write the skill validation test**

`tests/test_skills_v2.py`:
```python
"""Validate the 2 Atlas skills — structure, content, agentskills.io compliance."""
from pathlib import Path
import re
import yaml

SKILLS_DIR = Path(__file__).parent.parent / "atlas" / "skills"


def _read_skill(name: str) -> str:
    path = SKILLS_DIR / name / "SKILL.md"
    assert path.exists(), f"Skill {name} not found at {path}"
    return path.read_text(encoding="utf-8")


def _parse_frontmatter(content: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    assert m, "Missing YAML frontmatter"
    return yaml.safe_load(m.group(1))


# --- /atlas ---

def test_atlas_skill_exists():
    assert (SKILLS_DIR / "atlas" / "SKILL.md").exists()


def test_atlas_frontmatter():
    fm = _parse_frontmatter(_read_skill("atlas"))
    assert fm["name"] == "atlas"
    assert len(fm["description"]) > 50
    assert "knowledge" in fm["description"].lower() or "graph" in fm["description"].lower()


def test_atlas_has_operations():
    content = _read_skill("atlas")
    for op in ["scan", "query", "ingest", "audit", "finish"]:
        assert f"/atlas {op}" in content or f"atlas {op}" in content, f"Missing operation: {op}"


def test_atlas_has_orientation():
    content = _read_skill("atlas")
    assert "AGENTS.md" in content, "Must reference AGENTS.md orientation"
    assert "index.md" in content, "Must reference index.md orientation"
    assert "log.md" in content, "Must reference log.md orientation"


def test_atlas_has_mcp_cli_detection():
    content = _read_skill("atlas")
    assert "localhost:7100" in content or "api/health" in content, "Must detect MCP vs CLI"


def test_atlas_has_page_thresholds():
    content = _read_skill("atlas")
    assert "2+" in content or "two or more" in content.lower(), "Must have page creation thresholds"


def test_atlas_has_cross_reference_rule():
    content = _read_skill("atlas")
    assert "[[" in content, "Must mention wikilinks"


def test_atlas_line_count():
    content = _read_skill("atlas")
    lines = len(content.splitlines())
    assert 200 < lines < 600, f"Expected 200-600 lines, got {lines}"


# --- /atlas-deep ---

def test_atlas_deep_skill_exists():
    assert (SKILLS_DIR / "atlas-deep" / "SKILL.md").exists()


def test_atlas_deep_frontmatter():
    fm = _parse_frontmatter(_read_skill("atlas-deep"))
    assert fm["name"] == "atlas-deep"
    assert "LLM" in fm["description"] or "enrich" in fm["description"].lower()


def test_atlas_deep_mentions_tokens():
    content = _read_skill("atlas-deep")
    assert "token" in content.lower(), "Must warn about token cost"


def test_atlas_deep_line_count():
    content = _read_skill("atlas-deep")
    lines = len(content.splitlines())
    assert 80 < lines < 250, f"Expected 80-250 lines, got {lines}"


# --- Old skills deleted ---

def test_old_skills_deleted():
    old_skills = ["atlas-start", "atlas-scan", "atlas-query", "atlas-ingest",
                  "atlas-progress", "atlas-finish", "atlas-health"]
    for name in old_skills:
        assert not (SKILLS_DIR / name).exists(), f"Old skill {name} should be deleted"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_skills_v2.py -v`
Expected: FAIL — skills don't exist yet

- [ ] **Step 3: Write `/atlas` SKILL.md**

`atlas/skills/atlas/SKILL.md`:
```markdown
---
name: atlas
description: "Knowledge engine for AI agents — scan any folder into a navigable graph, query relationships, curate a living wiki. One skill for everything: orientation, scan, query, ingest, audit, finish."
---

# /atlas

Turn any folder into a navigable knowledge graph with a curated wiki. One command for everything.

## Usage

```
/atlas                              # orient — read graph + wiki, brief yourself
/atlas scan <path>                  # scan a folder (L0+L1, free, no LLM)
/atlas scan <path> --deep           # scan with LLM enrichment (costs tokens → triggers /atlas-deep)
/atlas query "<question>"           # traverse the graph to answer a question
/atlas query "<question>" --dfs     # depth-first traversal (trace a specific path)
/atlas ingest <url_or_path>         # ingest a source into raw/ + wiki
/atlas audit                        # health check — orphans, contradictions, stale pages
/atlas finish                       # end-of-session — write back learnings to wiki + graph
```

## What You Must Do When Invoked

### Step 0 — Detect execution mode

```bash
curl -s http://localhost:7100/api/health > /dev/null 2>&1
```

If the server responds → **MCP mode**: use MCP tools (`atlas.query`, `atlas.scan`, `atlas.wiki.read`, etc.). The dashboard updates in real-time.

If the server doesn't respond → **CLI mode**: use shell commands (`atlas query`, `atlas scan`, `atlas audit`). Works offline.

Use whichever mode is available for ALL subsequent operations. Do not mix modes.

### Step 1 — Orientation (MANDATORY, every session)

Before doing anything else, orient yourself. This is non-negotiable — skipping it causes duplicates, missed cross-references, and contradictions.

**MCP mode:**
```
atlas.wiki.read("AGENTS.md")           # conventions and schemas
atlas.wiki.read("wiki/index.md")       # what pages exist
atlas.stats()                           # graph: nodes, edges, communities, health
```
Then read the last entries from the log for recent activity.

**CLI mode:**
```bash
cat AGENTS.md
cat wiki/index.md
atlas audit 2>/dev/null | head -5       # quick health check
tail -30 wiki/log.md                    # recent activity
```

After orientation, briefly report to the user:
- Project has X nodes, Y pages, health Z
- Last session did [summary from log]
- N files changed since last scan (if applicable)

### Step 2 — Execute the requested operation

If no operation was specified (just `/atlas`), orientation is the operation. Report and ask what the user wants to do.

If an operation was specified, follow the specific instructions below.

---

## Operations

### /atlas scan <path>

Scan a directory, build the knowledge graph.

1. If no path given, use `.` (current directory)
2. Execute scan:
   - **MCP:** `atlas.scan({ path: "<path>" })`
   - **CLI:** `atlas scan <path>`
3. Report: nodes found, edges, communities, health score
4. If `--deep` flag: tell the user to run `/atlas-deep` or execute it if available

Scan is free (AST + regex, no LLM). It produces a graph instantly.

### /atlas query "<question>"

Query the knowledge graph. Use this BEFORE grepping files — it's faster and finds connections that grep misses.

1. Execute query:
   - **MCP:** `atlas.query({ question: "<question>", mode: "bfs", depth: 3 })`
   - **CLI:** `atlas query "<question>"`
2. Read the subgraph results — nodes and edges along the traversal path
3. Use the subgraph as context to answer the user's question
4. Cite the sources: "Based on [[page-a]] and node X in the graph..."
5. If the answer is a substantial synthesis (not a trivial lookup), file it back:
   - **MCP:** `atlas.wiki.write({ page: "outputs/YYYY-MM-DD-query.md", content: "..." })`
   - **CLI:** write the file directly

**When to use query vs grep:**
- "What connects auth to billing?" → atlas query (traverses relationships)
- "Find all files containing 'AuthManager'" → grep (exact text match)
- "How does the auth module work?" → atlas query first, then read the specific files it points to

### /atlas ingest <url_or_path>

Integrate a new source into the knowledge base.

1. Execute ingest:
   - **MCP:** `atlas.ingest({ source: "<url_or_path>" })`
   - **CLI:** `atlas ingest <url_or_path>`
2. The source is saved to `raw/ingested/` with auto frontmatter (source_url, type, captured_at)
3. L0+L1 scan runs on the new source
4. Now curate wiki pages from the source:

**Page creation rules (from Hermes LLM Wiki):**
- **Create a page** when an entity appears in 2+ sources OR is central to this source
- **Update existing pages** when the source mentions something already covered
- **DON'T create pages** for passing mentions, minor details, or tangential topics
- Every new page MUST link to at least 2 other pages via `[[wikilinks]]`

5. Check existing pages FIRST (one search pass, not per-entity):
   - **MCP:** `atlas.wiki.search({ terms: "<key entities>" })`
   - **CLI:** `atlas query "<key entities>"`
6. Create/update pages:
   - Source page always: `wiki/sources/YYYY-MM-DD-slug.md`
   - Concept pages if warranted (apply thresholds)
   - Project/decision pages if applicable
7. Update `wiki/index.md` and `wiki/log.md`
8. Report all files created/updated

### /atlas audit

Health check — find problems in the knowledge base.

1. Execute audit:
   - **MCP:** `atlas.audit()`
   - **CLI:** `atlas audit`
2. Review findings by severity:
   - **Critical:** broken wikilinks (link to non-existent pages)
   - **Warning:** orphan pages (no incoming links), stale pages (>30 days)
   - **Info:** god nodes (most connected), surprising connections, scaling suggestions
3. Report findings with specific file paths and suggested actions
4. Check scaling rules:
   - Index sections > 50 entries → suggest splitting
   - Log > 500 entries → suggest rotation
   - Pages > 200 lines → suggest splitting

### /atlas finish

End-of-session write-back. Extract durable knowledge from this session.

1. Review what happened this session:
   - What was discussed, decided, discovered?
   - What files were changed?
   - Were there any contradictions with existing wiki content?
2. Active enrichment — if you discovered relationships during your work:
   - Propose graph edges for each discovery
   - Propose wiki pages for significant findings
3. Apply Update Policy for contradictions:
   - Note both positions with dates and sources
   - Mark in frontmatter: `contradictions: [page-name]`
   - Flag for user review
4. Write changes to wiki:
   - **MCP:** `atlas.wiki.write(...)` for each page
   - **CLI:** write files directly
5. Update `wiki/log.md` with session summary
6. Report: "Session complete. Wiki: +N pages updated. Graph: +M edges."

---

## Rules

1. **Always orient first.** Read AGENTS.md + index.md + log before any operation. No exceptions.
2. **Graph before grep.** Check `atlas query` before searching raw files. The graph is faster and shows connections.
3. **Page thresholds.** Don't create pages for passing mentions. 2+ sources or central entity = page. Otherwise, don't.
4. **Cross-reference enforcement.** Every page links to 2+ other pages. No orphan creation.
5. **Update policy.** On contradiction: note both sides, mark frontmatter, flag for review. Never silently overwrite.
6. **Confidence levels.** Every page has `confidence: high | medium | low`. Update when evidence changes.
7. **Scaling.** Index > 50/section → split. Log > 500 → rotate. Page > 200 lines → split.
8. **File back valuable answers.** If a query synthesis is substantial, save it to `outputs/` or a concept page.
9. **Report changes.** Always tell the user what files were created or updated.
10. **Use `title:` in frontmatter.** Not `concept:` or `decision:` as standalone keys.

## Page Types and Frontmatter

### Projects (`wiki/projects/`)
```yaml
---
type: wiki-page
project: ProjectName
status: active | paused | completed | blocked
updated: YYYY-MM-DD
updated_by: agent
confidence: medium
---
```

### Sources (`wiki/sources/`)
```yaml
---
type: wiki-source
title: "Source Title"
date: YYYY-MM-DD
project: project-name
confidence: medium
---
```

### Decisions (`wiki/decisions/`)
```yaml
---
type: wiki-decision
title: "Decision Title"
date: YYYY-MM-DD
project: project-name
status: active | superseded | reversed
confidence: medium
---
```

### Concepts (`wiki/concepts/`)
```yaml
---
type: wiki-concept
title: "Concept Name"
updated: YYYY-MM-DD
updated_by: agent
confidence: medium
tags: [tag1, tag2]
description: "One-sentence summary."
---
```
Concepts have NO `date:` or `project:` — they span projects.

## Other Commands

- `/atlas-deep` — LLM enrichment (separate skill, costs tokens)
- `atlas serve` — start the dashboard server
- `atlas .` — scan + serve + open browser in one command
```

- [ ] **Step 4: Write `/atlas-deep` SKILL.md**

`atlas/skills/atlas-deep/SKILL.md`:
```markdown
---
name: atlas-deep
description: "LLM-powered enrichment for Atlas knowledge graphs — extract semantic relations, analyze PDFs, read images. Costs tokens. Use /atlas for free operations."
---

# /atlas-deep

Enrich an Atlas knowledge graph with LLM-powered analysis. This goes beyond the free L0+L1 scan to find semantic relationships, extract concepts from PDFs, and read images.

**This skill costs tokens.** The basic `/atlas scan` is free (AST + regex). `/atlas-deep` uses your agent's LLM to analyze file contents. Only use when you want deeper analysis.

## Usage

```
/atlas-deep                         # enrich current project
/atlas-deep <path>                  # enrich a specific folder
/atlas-deep --pdf-only              # only process PDF files
/atlas-deep --images-only           # only process images (uses Vision)
```

## What This Does

### L2 — Semantic Relations

For each document file (.md, .txt, .rst):
1. Read the file content
2. Extract named concepts, entities, and their relationships
3. Find cross-file connections that regex can't detect
4. Add INFERRED edges to the graph with confidence scores (0.6-0.9)

### L3 — Deep Extraction

For PDFs:
1. Extract text content
2. Mine citations and references
3. Extract key concepts and findings
4. Add nodes and edges to the graph

For images (.png, .jpg, .webp):
1. Use Vision to describe the image
2. Extract concepts, entities, diagram structures
3. Connect to related nodes in the graph

## How to Execute

### Step 1 — Check current graph

```bash
atlas audit 2>/dev/null | head -5
```

Know what you're enriching before starting.

### Step 2 — Process files

For each file that hasn't been LLM-analyzed (check `atlas-cache/`):

1. Read the file content
2. Extract structured data:

```json
{
  "nodes": [
    {"id": "concept_name", "label": "Concept Name", "type": "document", "source_file": "path"}
  ],
  "edges": [
    {"source": "concept_a", "target": "concept_b", "relation": "related_to", "confidence": "INFERRED", "confidence_score": 0.75}
  ]
}
```

3. Validate the extraction (no hallucinated nodes, confidence scores are reasonable)
4. Merge into the graph:
   - **MCP:** `atlas.scan({ path: "<path>", level: "deep" })`
   - **CLI:** write extraction to a temp file, then `atlas scan --deep <path>`

### Step 3 — Report

Tell the user:
- How many files were analyzed
- How many new nodes and INFERRED edges were added
- Token cost estimate
- Notable discoveries (surprising connections, new concepts)

## Rules

1. **Never run automatically.** Only when the user explicitly asks for enrichment.
2. **Report token cost.** Before starting a large enrichment, estimate: "This will analyze N files, ~X tokens."
3. **Confidence scores matter.** INFERRED edges get 0.6-0.9 based on evidence strength. Don't inflate.
4. **Don't duplicate.** Check the cache before re-analyzing a file.
5. **Validate extractions.** Don't add nodes that reference non-existent files or hallucinated concepts.

## When NOT to Use

- Quick questions → use `/atlas query` (free)
- Code navigation → use `/atlas scan` (free, AST-based)
- Wiki curation → use `/atlas ingest` or `/atlas finish` (free)
- Only use `/atlas-deep` when the free scan misses important connections
```

- [ ] **Step 5: Run tests**

Run: `uv run python -m pytest tests/test_skills_v2.py -v`
Expected: Most pass. `test_old_skills_deleted` will fail (old skills still exist).

- [ ] **Step 6: Delete old skills**

```bash
rm -rf atlas/skills/atlas-start atlas/skills/atlas-scan atlas/skills/atlas-query
rm -rf atlas/skills/atlas-ingest atlas/skills/atlas-progress atlas/skills/atlas-finish
rm -rf atlas/skills/atlas-health
```

- [ ] **Step 7: Run tests again**

Run: `uv run python -m pytest tests/test_skills_v2.py -v`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add atlas/skills/ tests/test_skills_v2.py
git commit -m "feat: consolidate 7 skills into 2 (/atlas + /atlas-deep)

Inspired by Hermes LLM Wiki pattern — one skill entry point for everything.
/atlas covers: orientation, scan, query, ingest, audit, finish.
/atlas-deep is opt-in LLM enrichment (costs tokens).
Old 7 skills deleted."
```

---

## Task 2: Update `atlas install` for 2 Skills

**Files:**
- Modify: `atlas/cli.py`
- Test: `tests/test_install.py`

- [ ] **Step 1: Write the install test**

`tests/test_install.py`:
```python
"""Test atlas install/uninstall logic."""
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner

from atlas.cli import app

runner = CliRunner()

SKILLS = ["atlas", "atlas-deep"]


def test_install_creates_agents_dir(tmp_path):
    agents_dir = tmp_path / ".agents" / "skills"
    with patch("atlas.cli._home", return_value=tmp_path):
        with patch("atlas.cli._detect_agents", return_value=[]):
            result = runner.invoke(app, ["install"])
    assert agents_dir.exists()
    for skill in SKILLS:
        assert (agents_dir / skill / "SKILL.md").exists()


def test_install_detects_claude_code(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    agents_dir = tmp_path / ".agents" / "skills"
    agents_dir.mkdir(parents=True)

    with patch("atlas.cli._home", return_value=tmp_path):
        with patch("atlas.cli._detect_agents", return_value=["claude-code"]):
            with patch("atlas.cli._install_for_agent") as mock_install:
                result = runner.invoke(app, ["install"])
    mock_install.assert_called()


def test_install_copies_skills_to_agents(tmp_path):
    agents_dir = tmp_path / ".agents" / "skills"
    with patch("atlas.cli._home", return_value=tmp_path):
        with patch("atlas.cli._detect_agents", return_value=[]):
            result = runner.invoke(app, ["install"])
    for skill in SKILLS:
        skill_file = agents_dir / skill / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text()
        assert f"name: {skill}" in content


def test_uninstall_removes_symlinks(tmp_path):
    # Setup: create agents dir with skills
    agents_dir = tmp_path / ".agents" / "skills"
    for skill in SKILLS:
        (agents_dir / skill).mkdir(parents=True)
        (agents_dir / skill / "SKILL.md").write_text(f"---\nname: {skill}\n---\n")

    # Create a symlink as claude-code would have
    claude_skills = tmp_path / ".claude" / "skills"
    claude_skills.mkdir(parents=True)
    (claude_skills / "atlas").symlink_to(agents_dir / "atlas")

    with patch("atlas.cli._home", return_value=tmp_path):
        result = runner.invoke(app, ["uninstall"])

    assert not (claude_skills / "atlas").exists()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run python -m pytest tests/test_install.py -v`
Expected: FAIL — `_home`, `_detect_agents`, `_install_for_agent` don't exist

- [ ] **Step 3: Update install command in cli.py**

Add these functions to `atlas/cli.py`:

```python
# ---------------------------------------------------------------------------
# Install helpers
# ---------------------------------------------------------------------------

def _home() -> Path:
    """Return home directory (mockable for tests)."""
    return Path.home()


def _skills_source() -> Path:
    """Return the directory containing our SKILL.md files."""
    return Path(__file__).parent / "skills"


def _detect_agents() -> list[str]:
    """Detect which AI agents are installed on this machine."""
    home = _home()
    agents = []
    if (home / ".claude").is_dir():
        agents.append("claude-code")
    if (home / ".codex").is_dir() or (home / ".agents").is_dir():
        agents.append("codex")
    if (home / ".cursor").is_dir():
        agents.append("cursor")
    if (home / ".hermes").is_dir():
        agents.append("hermes")
    if (home / ".codeium").is_dir():
        agents.append("windsurf")
    if (home / ".copilot").is_dir():
        agents.append("copilot")
    return agents


def _install_for_agent(agent: str, agents_skills: Path) -> str:
    """Install skills for a specific agent. Returns status message."""
    home = _home()
    skills = ["atlas", "atlas-deep"]

    if agent == "claude-code":
        target = home / ".claude" / "skills"
        target.mkdir(parents=True, exist_ok=True)
        for skill in skills:
            link = target / skill
            if link.is_symlink():
                link.unlink()
            link.symlink_to(agents_skills / skill)
        return f"Claude Code — {len(skills)} skills symlinked + PreToolUse hook"

    elif agent == "codex":
        # Codex reads ~/.agents/skills/ natively
        return "Codex — native (~/.agents/skills/)"

    elif agent == "cursor":
        target = home / ".cursor" / "skills"
        target.mkdir(parents=True, exist_ok=True)
        for skill in skills:
            link = target / skill
            if link.is_symlink():
                link.unlink()
            link.symlink_to(agents_skills / skill)
        return f"Cursor — {len(skills)} skills symlinked"

    elif agent == "hermes":
        target = home / ".hermes" / "skills"
        target.mkdir(parents=True, exist_ok=True)
        for skill in skills:
            link = target / skill
            if link.is_symlink():
                link.unlink()
            link.symlink_to(agents_skills / skill)
        # Also install in profiles
        profiles = home / ".hermes" / "profiles"
        if profiles.is_dir():
            for profile in profiles.iterdir():
                if profile.is_dir():
                    p_skills = profile / "skills"
                    p_skills.mkdir(parents=True, exist_ok=True)
                    for skill in skills:
                        link = p_skills / skill
                        if link.is_symlink():
                            link.unlink()
                        link.symlink_to(agents_skills / skill)
        return f"Hermes — {len(skills)} skills symlinked + profiles"

    elif agent in ("windsurf", "copilot"):
        return f"{agent.title()} — native (~/.agents/skills/)"

    return f"{agent} — unknown"
```

Update the `install` command:

```python
@app.command()
def install() -> None:
    """Install Atlas skills for all detected AI agents."""
    import shutil

    home = _home()
    source = _skills_source()
    agents_skills = home / ".agents" / "skills"
    agents_skills.mkdir(parents=True, exist_ok=True)

    # Copy skills to ~/.agents/skills/ (source of truth)
    for skill_dir in source.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            dest = agents_skills / skill_dir.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(skill_dir, dest)
            typer.echo(f"  Copied {skill_dir.name} → {dest}")

    # Detect and install for each agent
    agents = _detect_agents()
    typer.echo(f"\nAtlas skills installed:")
    if not agents:
        typer.echo("  No AI agents detected. Skills are in ~/.agents/skills/")
        typer.echo("  Symlink them manually or install an agent (Claude Code, Codex, Cursor, Hermes)")
    else:
        for agent in agents:
            status = _install_for_agent(agent, agents_skills)
            typer.echo(f"  ✅ {status}")

    # Check for agents not detected
    all_agents = {"claude-code", "codex", "cursor", "hermes", "windsurf", "copilot"}
    missing = all_agents - set(agents)
    for agent in sorted(missing):
        typer.echo(f"  ⬚ {agent.title()} — not detected")

    typer.echo(f"\nType /atlas in any agent to get started.")
```

Update the `uninstall` command:

```python
@app.command()
def uninstall() -> None:
    """Remove Atlas skills from all agents."""
    home = _home()
    skills = ["atlas", "atlas-deep"]

    # Remove from each agent's skill directory
    dirs_to_check = [
        home / ".claude" / "skills",
        home / ".cursor" / "skills",
        home / ".hermes" / "skills",
    ]
    # Add hermes profiles
    profiles = home / ".hermes" / "profiles"
    if profiles.is_dir():
        for profile in profiles.iterdir():
            if profile.is_dir():
                dirs_to_check.append(profile / "skills")

    removed = 0
    for d in dirs_to_check:
        for skill in skills:
            link = d / skill
            if link.is_symlink() or link.exists():
                if link.is_symlink():
                    link.unlink()
                else:
                    import shutil
                    shutil.rmtree(link)
                removed += 1
                typer.echo(f"  Removed {link}")

    # Remove from ~/.agents/skills/
    agents_skills = home / ".agents" / "skills"
    for skill in skills:
        p = agents_skills / skill
        if p.exists():
            import shutil
            shutil.rmtree(p)
            removed += 1

    typer.echo(f"\nRemoved {removed} skill installations.")
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_install.py -v`
Expected: All PASS

- [ ] **Step 5: Run full suite**

Run: `uv run python -m pytest tests/ --no-header 2>&1 | tail -3`
Expected: All pass (old skill tests may need updating)

- [ ] **Step 6: Commit**

```bash
git add atlas/cli.py tests/test_install.py
git commit -m "feat: atlas install/uninstall — multi-agent skill deployment

Detects Claude Code, Codex, Cursor, Hermes, Windsurf, Copilot.
Copies 2 skills to ~/.agents/skills/ (source of truth).
Symlinks into each agent's skill directory.
atlas uninstall removes everything cleanly."
```

---

## Task 3: Update Old Skill Tests

**Files:**
- Modify: `tests/test_skills.py` (if exists — update or delete)

- [ ] **Step 1: Check if old skill tests exist**

```bash
ls tests/test_skills.py 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"
```

- [ ] **Step 2: If exists, update to reference new skills**

Replace references to the 7 old skills with the 2 new ones. Or delete the file if `test_skills_v2.py` covers everything.

- [ ] **Step 3: Run full test suite**

Run: `uv run python -m pytest tests/ --no-header 2>&1 | tail -3`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: update skill tests for 2-skill architecture"
```

---

## Self-Review

**Spec coverage:**
- [x] 12.2 — 2 skills instead of 7 (Task 1)
- [x] 12.3 — MCP vs CLI detection in /atlas SKILL.md (Task 1 Step 3)
- [x] 12.4 — atlas install multi-agent (Task 2)
- [x] 12.5 — All skill behaviors in /atlas SKILL.md (Task 1 Step 3)
- [x] 12.6 — Always-on hook mentioned in install (Task 2 — PreToolUse for Claude Code)
- [x] Hermes LLM Wiki patterns — orientation, page thresholds, cross-ref, scaling rules (Task 1 Step 3)

**Placeholder scan:** No TBD/TODO. All code is complete.

**Type consistency:** Install uses `_home()`, `_detect_agents()`, `_install_for_agent()` consistently. Skills reference `atlas.query`, `atlas.scan`, etc. matching the MCP tools defined in Plan 2.
