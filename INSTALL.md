# Install agent-wiki

You are an LLM agent. A human wants to set up agent-wiki. Guide them through it conversationally.

Source repo: https://github.com/originlabs-app/agent-wiki

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

## Step 2: Ask 3 setup questions

### Question 1: Which agents?

"I detected [X, Y, Z] on your machine. Do you want agent-wiki installed for all of them, or just some?"

### Question 2: Where should the wiki live?

"Where do you want your wiki installed? Give me a path, or I'll use the default `~/agent-wiki/`."

Examples:
- `~/agent-wiki/` — default, standalone wiki
- `~/Documents/my-vault/` — existing Obsidian vault
- `~/dev/knowledge/` — custom location
- `.` — right here in the current directory

### Question 3: What will you use it for?

"Quick question so I can set it up right — what's your main use case?
- **Research** — articles, papers, long-term synthesis
- **Software development** — architecture decisions, project context across sessions
- **Business** — client notes, meeting transcripts, strategy
- **General** — a bit of everything"

## Step 3: Clone the repo (if needed)

If agent-wiki is not already cloned at the chosen location:

```bash
git clone https://github.com/originlabs-app/agent-wiki.git [chosen-path]
cd [chosen-path]
```

If the user chose an existing directory (vault, repo), clone agent-wiki there or add the wiki layer:

```bash
cd [chosen-path]
# If raw/, wiki/, outputs/ don't exist, create them:
mkdir -p raw/untracked raw/ingested wiki/projects wiki/sources wiki/decisions outputs
# Copy the essential files from the repo:
curl -sL https://raw.githubusercontent.com/originlabs-app/agent-wiki/main/SKILL.md -o SKILL.md
curl -sL https://raw.githubusercontent.com/originlabs-app/agent-wiki/main/AGENTS.md -o AGENTS.md
mkdir -p tools && curl -sL https://raw.githubusercontent.com/originlabs-app/agent-wiki/main/tools/wikictl -o tools/wikictl && chmod +x tools/wikictl
```

## Step 4: Make wikictl available everywhere

```bash
chmod +x ./tools/wikictl
./tools/wikictl init
```

Add wikictl to PATH so it works from any directory. Use a wrapper script (not a symlink — symlinks break the path resolution):

```bash
mkdir -p ~/.local/bin
printf '#!/usr/bin/env bash\nexec "%s/tools/wikictl" "$@"\n' "$(pwd)" > ~/.local/bin/wikictl
chmod +x ~/.local/bin/wikictl
```

If ~/.local/bin is not in PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc  # or ~/.zshrc
```

Verify: `wikictl status` should work from any directory.

## Step 5: Install the skill

Install one canonical copy:

```bash
mkdir -p ~/.agents/skills/agent-wiki
cp SKILL.md ~/.agents/skills/agent-wiki/SKILL.md
```

Symlink into each agent the user selected:

```bash
# Claude Code
[ -d ~/.claude ] && mkdir -p ~/.claude/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.claude/skills/agent-wiki

# Codex (already in ~/.agents/skills/)

# Cursor
[ -d ~/.cursor ] && mkdir -p ~/.cursor/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.cursor/skills/agent-wiki

# Hermes
[ -d ~/.hermes ] && mkdir -p ~/.hermes/skills && ln -sfn ~/.agents/skills/agent-wiki ~/.hermes/skills/agent-wiki
for d in ~/.hermes/profiles/*/; do
  [ -d "$d" ] && mkdir -p "${d}skills" && ln -sfn ~/.agents/skills/agent-wiki "${d}skills/agent-wiki"
done
```

## Step 6: Add wiki awareness to existing configs

For each selected agent, **append** a small section to their global config. Never replace the file.

### Claude Code (~/.claude/CLAUDE.md)

If the file exists, append:

```markdown

## Agent Wiki

agent-wiki is available as a shared knowledge base.
Use /agent-wiki start at the beginning of a session and /agent-wiki finish at the end.
Wiki location: [path to wiki]
```

### Codex (~/.codex/AGENTS.md or ~/.agents/AGENTS.md)

If the file exists, append the same short section.

### Hermes (SOUL.md per profile)

Ask: "Do you want me to add a note about agent-wiki to your Hermes profiles?"

If yes, find each profile's SOUL.md and append the same section.

### Cursor

If ~/.cursor/rules/ exists, add a small rule file. Otherwise skip.

## Step 7: Personalize

Based on Question 3 (use case), personalize the `## What This Is` section in AGENTS.md. Replace the placeholder with a concrete 2-3 sentence description.

If they said "software development", suggest creating an initial project page:
"Want me to create a wiki page for a current project? Give me the name."

## Step 8: Verify and report

```bash
wikictl status
wikictl lint
```

Report:

- Where the wiki was installed
- Which agents got the skill
- What was added to their configs (quote the exact lines)
- What was NOT touched
- How to start: "Type `/agent-wiki start` in any agent session"
