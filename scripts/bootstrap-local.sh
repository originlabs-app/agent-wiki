#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

link_file() {
  local src="$1"
  local dest="$2"

  mkdir -p "$(dirname "$dest")"
  if [[ -e "$dest" || -L "$dest" ]]; then
    if [[ -L "$dest" && "$(readlink "$dest")" == "$src" ]]; then
      return
    fi
    local backup="${dest}.bak.$(date +%Y%m%d%H%M%S)"
    mv "$dest" "$backup"
    echo "backed up existing file: $dest -> $backup"
  fi
  ln -sfn "$src" "$dest"
}

link_file "$ROOT/adapters/claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
link_file "$ROOT/adapters/codex/AGENTS.md" "$HOME/.codex/AGENTS.md"
link_file "$ROOT/adapters/cursor/AGENTS.md" "$HOME/.cursor/AGENTS.md"
link_file "$ROOT/adapters/cursor/.cursor/rules/agent-wiki.mdc" "$HOME/.cursor/rules/agent-wiki.mdc"
link_file "$ROOT/adapters/hermes/SKILL.md" "$HOME/.hermes/skills/llm-wiki-maintainer/SKILL.md"

echo "Linked local agent configs to:"
echo "  Claude  -> $HOME/.claude/CLAUDE.md"
echo "  Codex   -> $HOME/.codex/AGENTS.md"
echo "  Cursor  -> $HOME/.cursor/AGENTS.md and rules/agent-wiki.mdc"
echo "  Hermès  -> $HOME/.hermes/skills/llm-wiki-maintainer/SKILL.md"
