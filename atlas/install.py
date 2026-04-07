"""Multi-platform installer — detect platforms, symlink skills, configure hooks."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Skill source: the SKILL.md files shipped inside the atlas package
# ---------------------------------------------------------------------------

_SKILLS_SRC = Path(__file__).parent / "skills"

_SKILL_NAMES = [
    "atlas-start",
    "atlas-scan",
    "atlas-query",
    "atlas-ingest",
    "atlas-progress",
    "atlas-finish",
    "atlas-health",
]

# ---------------------------------------------------------------------------
# Platform config
# ---------------------------------------------------------------------------

PLATFORM_CONFIG: dict[str, dict] = {
    "claude": {
        "detect_dir": ".claude",
        "skills_dir": Path(".claude") / "skills",
        "has_hook": True,
    },
    "codex": {
        "detect_dir": ".codex",
        "skills_dir": Path(".agents") / "skills",
        "has_hook": False,
    },
    "cursor": {
        "detect_dir": ".cursor",
        "skills_dir": Path(".cursor") / "skills",
        "has_hook": False,
    },
    "hermes": {
        "detect_dir": ".hermes",
        "skills_dir": Path(".hermes") / "skills",
        "has_hook": False,
    },
}

# ---------------------------------------------------------------------------
# Claude Code PreToolUse hook — nudges the agent to read the graph
# ---------------------------------------------------------------------------

_CLAUDE_HOOK = {
    "matcher": "Glob|Grep",
    "hooks": [
        {
            "type": "command",
            "command": (
                "[ -f atlas-out/graph.json ] && "
                "echo 'atlas: Knowledge graph exists at atlas-out/. "
                "Read atlas-out/GRAPH_REPORT.md or run atlas query before searching raw files.' || true"
            ),
        }
    ],
}


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def detect_platforms() -> list[str]:
    """Detect which AI coding platforms are installed on this machine."""
    home = Path.home()
    found = []
    for platform, cfg in PLATFORM_CONFIG.items():
        if (home / cfg["detect_dir"]).is_dir():
            found.append(platform)
    return found


# ---------------------------------------------------------------------------
# Skill installation
# ---------------------------------------------------------------------------

def install_skills(platform: str) -> list[str]:
    """Copy SKILL.md files to the platform's skill directory.

    Returns list of installed skill paths.
    """
    if platform not in PLATFORM_CONFIG:
        raise ValueError(f"Unknown platform '{platform}'. Choose from: {', '.join(PLATFORM_CONFIG)}")

    home = Path.home()
    skills_dst = home / PLATFORM_CONFIG[platform]["skills_dir"]

    installed = []
    for name in _SKILL_NAMES:
        src = _SKILLS_SRC / name / "SKILL.md"
        if not src.exists():
            continue

        dst_dir = skills_dst / name
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / "SKILL.md"

        # Copy (not symlink) — more robust across platforms
        shutil.copy2(src, dst)
        installed.append(str(dst))

    return installed


def uninstall_skills(platform: str) -> list[str]:
    """Remove Atlas skill directories from the platform's skill dir.

    Returns list of removed paths.
    """
    if platform not in PLATFORM_CONFIG:
        raise ValueError(f"Unknown platform '{platform}'. Choose from: {', '.join(PLATFORM_CONFIG)}")

    home = Path.home()
    skills_dst = home / PLATFORM_CONFIG[platform]["skills_dir"]

    removed = []
    for name in _SKILL_NAMES:
        skill_dir = skills_dst / name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            removed.append(str(skill_dir))

    return removed


# ---------------------------------------------------------------------------
# Claude Code hook management
# ---------------------------------------------------------------------------

def install_claude_hook(project_dir: Path) -> None:
    """Add Atlas PreToolUse hook to .claude/settings.json."""
    settings_path = project_dir / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])

    # Check idempotency
    if any(h.get("matcher") == "Glob|Grep" and "atlas" in json.dumps(h) for h in pre_tool):
        return

    pre_tool.append(_CLAUDE_HOOK)
    settings_path.write_text(json.dumps(settings, indent=2))


def uninstall_claude_hook(project_dir: Path) -> None:
    """Remove Atlas PreToolUse hook from .claude/settings.json."""
    settings_path = project_dir / ".claude" / "settings.json"
    if not settings_path.exists():
        return

    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        return

    pre_tool = settings.get("hooks", {}).get("PreToolUse", [])
    filtered = [h for h in pre_tool if not (h.get("matcher") == "Glob|Grep" and "atlas" in json.dumps(h))]

    if len(filtered) == len(pre_tool):
        return  # nothing to remove

    settings["hooks"]["PreToolUse"] = filtered
    settings_path.write_text(json.dumps(settings, indent=2))


# ---------------------------------------------------------------------------
# AGENTS.md management (Codex, Cursor, Hermes)
# ---------------------------------------------------------------------------

_AGENTS_MD_SECTION = """\
## atlas

This project has an Atlas knowledge graph at atlas-out/.

Rules:
- Before answering architecture or codebase questions, run `atlas query "<topic>"` or read atlas-out/GRAPH_REPORT.md
- If wiki/index.md exists, navigate the wiki instead of reading raw files
- Use `/atlas-start` at session start for a briefing
- Use `/atlas-finish` at session end to write back durable knowledge
"""

_AGENTS_MD_MARKER = "## atlas"


def install_agents_md(project_dir: Path) -> bool:
    """Write the Atlas section to AGENTS.md in the project root."""
    target = project_dir / "AGENTS.md"

    if target.exists():
        content = target.read_text()
        if _AGENTS_MD_MARKER in content:
            return False  # already installed
        target.write_text(content.rstrip() + "\n\n" + _AGENTS_MD_SECTION)
    else:
        target.write_text(_AGENTS_MD_SECTION)

    return True


def uninstall_agents_md(project_dir: Path) -> bool:
    """Remove the Atlas section from AGENTS.md."""
    import re

    target = project_dir / "AGENTS.md"
    if not target.exists():
        return False

    content = target.read_text()
    if _AGENTS_MD_MARKER not in content:
        return False

    cleaned = re.sub(
        r"\n*## atlas\n.*?(?=\n## |\Z)",
        "",
        content,
        flags=re.DOTALL,
    ).rstrip()

    if cleaned:
        target.write_text(cleaned + "\n")
    else:
        target.unlink()

    return True
