"""Git hook integration — install/uninstall post-commit and post-checkout hooks."""
from __future__ import annotations

from pathlib import Path

_HOOK_MARKER = "# atlas-hook"
_CHECKOUT_MARKER = "# atlas-checkout-hook"

_HOOK_SCRIPT = """\
#!/bin/bash
# atlas-hook
# Auto-rebuilds the knowledge graph after each commit.
# Installed by: atlas hook install

CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only HEAD 2>/dev/null)
if [ -z "$CHANGED" ]; then
    exit 0
fi

# Only rebuild if atlas-out/ exists (graph has been built before)
if [ ! -d "atlas-out" ]; then
    exit 0
fi

echo "[atlas] Code changed — rebuilding knowledge graph..."
atlas scan . --update 2>/dev/null || python3 -m atlas.cli scan . --update 2>/dev/null || true
"""

_CHECKOUT_SCRIPT = """\
#!/bin/bash
# atlas-checkout-hook
# Auto-rebuilds the knowledge graph when switching branches.
# Installed by: atlas hook install

PREV_HEAD=$1
NEW_HEAD=$2
BRANCH_SWITCH=$3

# Only run on branch switches, not file checkouts
if [ "$BRANCH_SWITCH" != "1" ]; then
    exit 0
fi

# Only run if atlas-out/ exists (graph has been built before)
if [ ! -d "atlas-out" ]; then
    exit 0
fi

echo "[atlas] Branch switched — rebuilding knowledge graph..."
atlas scan . --update 2>/dev/null || python3 -m atlas.cli scan . --update 2>/dev/null || true
"""


def _git_root(path: Path) -> Path | None:
    """Walk up to find .git directory."""
    current = path.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _install_hook(hooks_dir: Path, name: str, script: str, marker: str) -> str:
    """Install a single git hook, appending if an existing hook is present."""
    hook_path = hooks_dir / name
    if hook_path.exists():
        content = hook_path.read_text()
        if marker in content:
            return f"already installed at {hook_path}"
        hook_path.write_text(content.rstrip() + "\n\n" + script)
        return f"appended to existing {name} hook at {hook_path}"
    hook_path.write_text(script)
    hook_path.chmod(0o755)
    return f"installed at {hook_path}"


def _uninstall_hook(hooks_dir: Path, name: str, marker: str) -> str:
    """Remove atlas section from a git hook."""
    hook_path = hooks_dir / name
    if not hook_path.exists():
        return f"no {name} hook found — nothing to remove."
    content = hook_path.read_text()
    if marker not in content:
        return f"atlas hook not found in {name} — nothing to remove."
    before = content.split(marker)[0].rstrip()
    non_empty = [line for line in before.splitlines() if line.strip() and not line.startswith("#!")]
    if not non_empty:
        hook_path.unlink()
        return f"removed {name} hook at {hook_path}"
    hook_path.write_text(before + "\n")
    return f"atlas removed from {name} at {hook_path} (other hook content preserved)"


def install(path: Path = Path(".")) -> str:
    """Install atlas post-commit and post-checkout hooks."""
    root = _git_root(path)
    if root is None:
        raise RuntimeError(f"No git repository found at or above {path.resolve()}")

    hooks_dir = root / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    commit_msg = _install_hook(hooks_dir, "post-commit", _HOOK_SCRIPT, _HOOK_MARKER)
    checkout_msg = _install_hook(hooks_dir, "post-checkout", _CHECKOUT_SCRIPT, _CHECKOUT_MARKER)

    return f"post-commit: {commit_msg}\npost-checkout: {checkout_msg}"


def uninstall(path: Path = Path(".")) -> str:
    """Remove atlas post-commit and post-checkout hooks."""
    root = _git_root(path)
    if root is None:
        raise RuntimeError(f"No git repository found at or above {path.resolve()}")

    hooks_dir = root / ".git" / "hooks"
    commit_msg = _uninstall_hook(hooks_dir, "post-commit", _HOOK_MARKER)
    checkout_msg = _uninstall_hook(hooks_dir, "post-checkout", _CHECKOUT_MARKER)

    return f"post-commit: {commit_msg}\npost-checkout: {checkout_msg}"


def status(path: Path = Path(".")) -> str:
    """Check if atlas hooks are installed."""
    root = _git_root(path)
    if root is None:
        return "Not in a git repository."

    hooks_dir = root / ".git" / "hooks"

    def _check(name: str, marker: str) -> str:
        p = hooks_dir / name
        if not p.exists():
            return "not installed"
        return "installed" if marker in p.read_text() else "not installed (hook exists but atlas not found)"

    commit = _check("post-commit", _HOOK_MARKER)
    checkout = _check("post-checkout", _CHECKOUT_MARKER)
    return f"post-commit: {commit}\npost-checkout: {checkout}"
