# Tool Config Map

agent-wiki uses a single `SKILL.md` that follows the [Agent Skills](https://agentskills.io/) standard.

## Installation

```bash
npx skills add originlabs-app/agent-wiki
```

This installs `SKILL.md` into the correct directory for each detected agent:

| Agent | Skill installed to |
|-------|--------------------|
| Claude Code | `~/.claude/skills/agent-wiki/SKILL.md` |
| Codex | `~/.agents/skills/agent-wiki/SKILL.md` |
| Cursor | `~/.cursor/skills/agent-wiki/SKILL.md` |
| Hermes | `~/.hermes/skills/agent-wiki/SKILL.md` |

## What the skill does

The skill tells the agent:
1. Detect if wikictl is available
2. If yes: read wiki before work, write back after work
3. If no: continue normally, don't fail

## What the skill does NOT do

- Does not overwrite any existing config files
- Does not modify CLAUDE.md, AGENTS.md, or any global config
- Does not install wikictl (it's in the repo or on PATH)
- Does not require MCP

## Manual install (without npx)

Copy `SKILL.md` from the repo root to your agent's skill directory:

```bash
# Claude Code
mkdir -p ~/.claude/skills/agent-wiki
cp SKILL.md ~/.claude/skills/agent-wiki/

# Codex
mkdir -p ~/.agents/skills/agent-wiki
cp SKILL.md ~/.agents/skills/agent-wiki/

# Hermes
mkdir -p ~/.hermes/skills/agent-wiki
cp SKILL.md ~/.hermes/skills/agent-wiki/
```

## Instance configuration

To point wikictl at an external vault:

```bash
mkdir -p ~/.agent-wiki/instances
cat > ~/.agent-wiki/instances/my-vault.conf << EOF
WIKI_ROOT=/path/to/wiki
RAW_ROOT=/path/to/raw
EOF
```

Then: `wikictl --instance my-vault status`

## MCP (optional)

```bash
cd /path/to/agent-wiki
npm install
npm run mcp
```

Adds tool-based access to wikictl operations. Not required for basic usage.
