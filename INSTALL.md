# Install agent-wiki

You are an LLM agent. A human has asked you to set up agent-wiki on their machine.

## Rules

- **NEVER overwrite or modify any existing config file** (CLAUDE.md, AGENTS.md, SOUL.md, etc.)
- **Install the skill ONCE, symlink for each agent**
- **If unsure, ask the user before modifying anything outside of skills directories**

## Step 1: Detect what's installed

Run silently — do not ask the user. Just check what exists:

```bash
[ -d ~/.claude ] && echo "Claude Code: detected" || echo "Claude Code: not found"
[ -d ~/.codex ] || [ -d ~/.agents ] && echo "Codex: detected" || echo "Codex: not found"
[ -d ~/.cursor ] && echo "Cursor: detected" || echo "Cursor: not found"
[ -d ~/.hermes ] && echo "Hermes: detected" || echo "Hermes: not found"
```

Report to the user: "I detected [agents]. I'll install the agent-wiki skill for each of them."

## Step 2: Ask ONE question

Ask the user:

> Do you have an existing folder or Obsidian vault where you want to store the wiki?
> If yes, give me the path (e.g., `~/Documents/my-vault`).
> If no, I'll use the wiki built into this repo.

**If the user gives a path:**
- Check if `wiki/` and `raw/` exist inside that path.
- If they don't exist, create them: `mkdir -p <path>/wiki <path>/raw`
- Create an instance config:

```bash
mkdir -p ~/.agent-wiki/instances
# Ask: "What name for this instance?" (e.g., my-vault, work, research)
cat > ~/.agent-wiki/instances/<name>.conf << EOF
WIKI_ROOT=<path>/wiki
RAW_ROOT=<path>/raw
EOF
```

**If the user says no (or doesn't have a vault):**
- Skip this step. The repo's built-in `wiki/` and `raw/` work as default.

## Step 3: Install the skill

```bash
# Ensure repo is ready
chmod +x ./cli/wikictl
./cli/wikictl init

# Install source skill (one copy)
mkdir -p ~/.agents/skills/agent-wiki
cp SKILL.md ~/.agents/skills/agent-wiki/SKILL.md
```

## Step 4: Symlink for each detected agent

Only create symlinks for agents detected in Step 1.

```bash
# Claude Code
[ -d ~/.claude ] && mkdir -p ~/.claude/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.claude/skills/agent-wiki

# Codex — already in ~/.agents/skills/, nothing to do

# Cursor
[ -d ~/.cursor ] && mkdir -p ~/.cursor/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.cursor/skills/agent-wiki

# Hermes (default profile)
[ -d ~/.hermes ] && mkdir -p ~/.hermes/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.hermes/skills/agent-wiki

# Hermes additional profiles
for profile_dir in ~/.hermes/profiles/*/; do
  [ -d "$profile_dir" ] && mkdir -p "${profile_dir}skills" && ln -sfn ~/.agents/skills/agent-wiki "${profile_dir}skills/agent-wiki"
done
```

## Step 5: Verify

```bash
./cli/wikictl status
./cli/wikictl lint
ls -la ~/.agents/skills/agent-wiki/SKILL.md
```

If an instance was configured:
```bash
./cli/wikictl --instance <name> status
```

## Step 6: Report to the user

Tell the user what was done:

```
Installed agent-wiki skill for: [list of detected agents]
Source: ~/.agents/skills/agent-wiki/SKILL.md
Instance: [name → path] (or: using built-in wiki)

What was NOT modified:
- Your global configs (CLAUDE.md, AGENTS.md, SOUL.md)
- Your existing skills
- Any files outside of skills directories

Next: open any agent in this repo. It will read the skill automatically.
```
