# Install agent-wiki

You are an LLM agent. A human wants to set up agent-wiki. Guide them through it conversationally.

## Rules

- **NEVER overwrite or delete** any existing config file
- When adding to an existing file, **append a small section** — don't replace the file
- **Ask before doing** — confirm with the user before modifying anything outside this repo
- Be concise. Don't explain the architecture. Just get it working.

## Step 1: Detect the environment (silent)

Check which agent tools are installed:

```bash
[ -d ~/.claude ] && echo "Claude Code: detected"
[ -d ~/.codex ] || [ -d ~/.agents ] && echo "Codex: detected"
[ -d ~/.cursor ] && echo "Cursor: detected"
[ -d ~/.hermes ] && echo "Hermes: detected"
```

Report what you found.

## Step 2: Ask 2 setup questions

### Question 1: Which agents?

"I detected [X, Y, Z] on your machine. Do you want agent-wiki installed for all of them, or just some?"

### Question 2: Where should the wiki live?

"Two options:
- **Here** — this repo becomes your wiki (In-Wiki mode). Simplest way to start.
- **Somewhere else** — you already have a folder, vault, or repo where you want the wiki to live. I'll point agent-wiki there (Second-Brain mode).

Where do you want it?"

If they give a path, check if raw/, wiki/, and outputs/ exist there. If not, create them.

If they chose "here", personalize the `## What This Is` section in AGENTS.md based on the repo context. If they chose another path, note that the wiki will be used as a second brain across repos. Keep it to 2-3 sentences.

## Step 3: Make wikictl available everywhere

The skill commands call `wikictl` behind the scenes. It needs to be accessible from any directory, not just this repo.

```bash
chmod +x ./tools/wikictl
./tools/wikictl init
```

Add wikictl to PATH so it works from any repo (second-brain mode):

```bash
ln -sfn "$(pwd)/tools/wikictl" /usr/local/bin/wikictl
```

If /usr/local/bin/ requires sudo or doesn't exist, use ~/bin/ or ~/.local/bin/ instead:

```bash
mkdir -p ~/.local/bin
ln -sfn "$(pwd)/tools/wikictl" ~/.local/bin/wikictl
```

Verify: `wikictl status` should work from any directory.

## Step 4: Install the skill

Install one canonical copy:

```bash
mkdir -p ~/.agents/skills/agent-wiki
cp SKILL.md ~/.agents/skills/agent-wiki/SKILL.md
```

Symlink into each agent the user selected:

```bash
# Claude Code
mkdir -p ~/.claude/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.claude/skills/agent-wiki

# Codex (already in ~/.agents/skills/)

# Cursor
mkdir -p ~/.cursor/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.cursor/skills/agent-wiki

# Hermes
mkdir -p ~/.hermes/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.hermes/skills/agent-wiki
# Also for Hermes profiles:
for d in ~/.hermes/profiles/*/; do
  [ -d "$d" ] && mkdir -p "${d}skills" && ln -sfn ~/.agents/skills/agent-wiki "${d}skills/agent-wiki"
done
```

## Step 5: Add wiki awareness to existing configs

For each selected agent, check if they have a global config and **append** a small section. Never replace the file.

### Claude Code (~/.claude/CLAUDE.md)

If the file exists, append:

```markdown

## Agent Wiki

agent-wiki is available as a shared knowledge base.
Use /agent-wiki start at the beginning of a session and /agent-wiki finish at the end.
Wiki location: [path to wiki]
```

If the file doesn't exist, skip. The skill is enough.

### Codex (~/.codex/AGENTS.md or ~/.agents/AGENTS.md)

If the file exists, append the same short section.

### Hermes (SOUL.md per profile)

If the user has Hermes profiles, ask: "Do you want me to add a note about agent-wiki to your Hermes profiles?"

If yes, find each profile's SOUL.md and append:

```markdown

## Agent Wiki

agent-wiki is available as a shared knowledge base.
The skill agent-wiki handles start/progress/finish workflows.
Wiki location: [path to wiki]
```

### Cursor

If ~/.cursor/rules/ exists, you can add a small rule file. Otherwise skip.

## Step 6: Configure instance (if wiki lives elsewhere)

If the user chose a different location in Question 2:

```bash
mkdir -p ~/.agent-wiki/instances
cat > ~/.agent-wiki/instances/[name].conf << EOF
WIKI_ROOT=[path]/wiki
RAW_ROOT=[path]/raw
EOF
```

Test: `./tools/wikictl --instance [name] status`

## Step 7: Verify and report

```bash
./tools/wikictl status
./tools/wikictl lint
```

Report to the user:

- Which agents got the skill
- Where the wiki lives
- What was added to their configs (quote the exact lines)
- What was NOT touched
- How to start: "Open your agent and type /agent-wiki start"
