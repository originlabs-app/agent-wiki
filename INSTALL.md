# Install agent-wiki

You are an LLM agent. A human has asked you to set up agent-wiki on their machine. Follow these instructions carefully.

**Rules:**
- **NEVER overwrite or modify any existing config file** (CLAUDE.md, AGENTS.md, SOUL.md, etc.)
- **Install the skill ONCE, symlink for each agent**
- **If unsure, ask the user before modifying anything**

## Step 1: Ensure the repo is ready

```bash
chmod +x ./cli/wikictl
./cli/wikictl init
```

## Step 2: Install the skill

The skill lives in ONE place. Each agent gets a symlink. This is the same pattern used by agent-browser.

### Install source skill

```bash
mkdir -p ~/.agents/skills/agent-wiki
cp SKILL.md ~/.agents/skills/agent-wiki/SKILL.md
```

### Symlink for each detected agent

Only create symlinks for agents that are actually installed on the machine.

```bash
# Claude Code (if ~/.claude/ exists)
[ -d ~/.claude ] && mkdir -p ~/.claude/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.claude/skills/agent-wiki

# Codex (already in ~/.agents/skills/, nothing to do)

# Cursor (if ~/.cursor/ exists)
[ -d ~/.cursor ] && mkdir -p ~/.cursor/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.cursor/skills/agent-wiki

# Hermes (if ~/.hermes/ exists)
[ -d ~/.hermes ] && mkdir -p ~/.hermes/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.hermes/skills/agent-wiki
```

### Hermes profiles

If Hermes has multiple profiles (e.g., `~/.hermes/profiles/marc/`), symlink into each:

```bash
for profile_dir in ~/.hermes/profiles/*/; do
  [ -d "$profile_dir" ] && mkdir -p "${profile_dir}skills" && ln -sfn ~/.agents/skills/agent-wiki "${profile_dir}skills/agent-wiki"
done
```

## Step 3: Configure an instance (optional)

If the user has an existing vault or folder they want agent-wiki to point to:

1. Ask: "What name for this instance?" (e.g., `my-vault`)
2. Ask: "Where is your wiki folder?" (e.g., `~/Documents/my-vault/wiki`)
3. Ask: "Where should raw sources go?" (e.g., `~/Documents/my-vault/raw`)
4. Create the config:

```bash
mkdir -p ~/.agent-wiki/instances
cat > ~/.agent-wiki/instances/<name>.conf << EOF
WIKI_ROOT=/path/to/wiki
RAW_ROOT=/path/to/raw
EOF
```

5. Test: `./cli/wikictl --instance <name> status`

If the user doesn't have an existing vault, skip this. The wiki in the repo works as default.

## Step 4: Verify

```bash
./cli/wikictl status
./cli/wikictl lint
```

Check that the symlinks resolve:
```bash
ls -la ~/.claude/skills/agent-wiki 2>/dev/null
ls -la ~/.agents/skills/agent-wiki 2>/dev/null
ls -la ~/.hermes/skills/agent-wiki 2>/dev/null
```

Report results to the user.

## Step 5: Clean up old installs (if needed)

If previous versions of agent-wiki were installed differently (bootstrap-local.sh, direct file copies, etc.), clean them up:

- Remove old symlinks to `adapters/` directory (no longer exists)
- Remove duplicate skills (e.g., `~/.hermes/skills/llm-wiki-maintainer/` if it was an old version)
- **Do NOT remove user-created files** — ask before deleting anything you didn't create

## Summary

```
~/.agents/skills/agent-wiki/SKILL.md   ← source (one copy)
~/.claude/skills/agent-wiki/           ← symlink → ~/.agents/skills/agent-wiki
~/.cursor/skills/agent-wiki/           ← symlink → ~/.agents/skills/agent-wiki
~/.hermes/skills/agent-wiki/           ← symlink → ~/.agents/skills/agent-wiki
~/.agent-wiki/instances/<name>.conf    ← instance config (optional)
```

What was NOT modified:
- No global configs (CLAUDE.md, AGENTS.md, SOUL.md)
- No existing skills overwritten
- No files outside of skills directories
