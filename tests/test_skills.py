"""Validate all Atlas skill files follow the agentskills.io standard."""
from pathlib import Path

import pytest
import yaml

SKILLS_DIR = Path(__file__).parent.parent / "atlas" / "skills"

EXPECTED_SKILLS = [
    "atlas-start",
    "atlas-scan",
    "atlas-query",
    "atlas-ingest",
    "atlas-progress",
    "atlas-finish",
    "atlas-health",
]


def _read_skill(name: str) -> str:
    path = SKILLS_DIR / name / "SKILL.md"
    assert path.exists(), f"Missing skill file: {path}"
    return path.read_text()


def _parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from a SKILL.md file."""
    assert content.startswith("---"), "SKILL.md must start with --- frontmatter"
    _, fm_raw, _ = content.split("---", 2)
    return yaml.safe_load(fm_raw)


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_exists(skill_name):
    """Each expected skill has a SKILL.md file."""
    path = SKILLS_DIR / skill_name / "SKILL.md"
    assert path.exists(), f"Missing: {path}"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_has_frontmatter(skill_name):
    """Each skill has valid YAML frontmatter with name and description."""
    content = _read_skill(skill_name)
    fm = _parse_frontmatter(content)
    assert "name" in fm, f"{skill_name}: frontmatter missing 'name'"
    assert "description" in fm, f"{skill_name}: frontmatter missing 'description'"
    assert fm["name"] == skill_name, f"{skill_name}: name mismatch — got '{fm['name']}'"
    assert len(fm["description"]) > 20, f"{skill_name}: description too short"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_has_heading(skill_name):
    """Each skill body starts with a # heading matching the skill name."""
    content = _read_skill(skill_name)
    # Skip frontmatter
    _, _, body = content.split("---", 2)
    body = body.strip()
    assert body.startswith(f"# /{skill_name}"), f"{skill_name}: body must start with '# /{skill_name}'"


_FULL_SKILLS = ["atlas-start", "atlas-progress", "atlas-finish"]

@pytest.mark.parametrize("skill_name", _FULL_SKILLS)
def test_skill_has_rules_section(skill_name):
    """Full skills (start, progress, finish) have a Rules section."""
    content = _read_skill(skill_name)
    assert "## Rules" in content, f"{skill_name}: missing '## Rules' section"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_references_atlas_cli(skill_name):
    """Each skill references atlas CLI commands (not wikictl)."""
    content = _read_skill(skill_name)
    assert "atlas" in content.lower(), f"{skill_name}: must reference atlas CLI"
    # Skills should NOT reference old wikictl commands
    assert "wikictl" not in content, f"{skill_name}: must not reference deprecated wikictl"


@pytest.mark.parametrize("skill_name", _FULL_SKILLS)
def test_skill_references_other_skills(skill_name):
    """Full skills mention at least some other Atlas skills."""
    content = _read_skill(skill_name)
    other_skills = [s for s in EXPECTED_SKILLS if s != skill_name]
    mentioned = [s for s in other_skills if f"/{s}" in content or s in content]
    assert len(mentioned) >= 1, f"{skill_name}: should reference at least 1 other skill, found {len(mentioned)}"


def test_all_skills_present():
    """Verify no skill is missing from the expected list."""
    actual = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
    assert actual == sorted(EXPECTED_SKILLS)


def test_no_python_in_skills():
    """Skills are pure markdown — no .py files inside skill directories."""
    for skill_dir in SKILLS_DIR.iterdir():
        if skill_dir.is_dir():
            py_files = list(skill_dir.glob("*.py"))
            assert not py_files, f"Skill {skill_dir.name} should not contain Python files: {py_files}"
