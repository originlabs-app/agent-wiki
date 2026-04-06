# Install agent-wiki

You are an LLM agent. A human wants to set up agent-wiki. Guide them through it conversationally.

Source repo: https://github.com/originlabs-app/agent-wiki

## Rules

- **NEVER overwrite or delete** any existing config file
- When adding to an existing file, **append the exact text shown** — don't rephrase, don't summarize, don't rewrite
- **Copy skill files exactly as-is** — use `cp -r`, not manual rewriting
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
curl -sL https://raw.githubusercontent.com/originlabs-app/agent-wiki/main/AGENTS.md -o AGENTS.md
# Download skills from the repo
for skill in agent-wiki-start agent-wiki-ingest agent-wiki-progress agent-wiki-finish agent-wiki-health; do
  mkdir -p skills/$skill
  curl -sL https://raw.githubusercontent.com/originlabs-app/agent-wiki/main/skills/$skill/SKILL.md -o skills/$skill/SKILL.md
done
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

## Step 5: Install the skills

Install all 5 skill directories:

```bash
mkdir -p ~/.agents/skills
cp -r skills/agent-wiki-start ~/.agents/skills/
cp -r skills/agent-wiki-ingest ~/.agents/skills/
cp -r skills/agent-wiki-progress ~/.agents/skills/
cp -r skills/agent-wiki-finish ~/.agents/skills/
cp -r skills/agent-wiki-health ~/.agents/skills/
```

Symlink into each agent the user selected:

```bash
# Claude Code
if [ -d ~/.claude ]; then
  mkdir -p ~/.claude/skills
  for skill in agent-wiki-start agent-wiki-ingest agent-wiki-progress agent-wiki-finish agent-wiki-health; do
    ln -sfn ~/.agents/skills/$skill ~/.claude/skills/$skill
  done
fi

# Codex (already in ~/.agents/skills/)

# Cursor
if [ -d ~/.cursor ]; then
  mkdir -p ~/.cursor/skills
  for skill in agent-wiki-start agent-wiki-ingest agent-wiki-progress agent-wiki-finish agent-wiki-health; do
    ln -sfn ~/.agents/skills/$skill ~/.cursor/skills/$skill
  done
fi

# Hermes
if [ -d ~/.hermes ]; then
  mkdir -p ~/.hermes/skills
  for skill in agent-wiki-start agent-wiki-ingest agent-wiki-progress agent-wiki-finish agent-wiki-health; do
    ln -sfn ~/.agents/skills/$skill ~/.hermes/skills/$skill
  done
  for d in ~/.hermes/profiles/*/; do
    [ -d "$d" ] && mkdir -p "${d}skills"
    for skill in agent-wiki-start agent-wiki-ingest agent-wiki-progress agent-wiki-finish agent-wiki-health; do
      ln -sfn ~/.agents/skills/$skill "${d}skills/$skill"
    done
  done
fi
```

## Step 6: Add wiki awareness to existing configs

For each selected agent, **append** the following section to their global config. Copy it EXACTLY as shown — only replace `[wiki-path]` with the actual path from Step 2. Never replace or rewrite the existing file.

The text to append (same for all agents):

```markdown

## Agent Wiki

agent-wiki is available as a shared knowledge base.
Use /agent-wiki-start at the beginning of a session and /agent-wiki-finish at the end.
Wiki location: [wiki-path]
```

Where to append it:

- **Claude Code**: `~/.claude/CLAUDE.md` (if the file exists)
- **Codex**: `~/.codex/AGENTS.md` or `~/.agents/AGENTS.md` (if either exists)
- **Hermes**: Ask the user first: "Do you want me to add a note about agent-wiki to your Hermes profiles?" If yes, append to each profile's SOUL.md (e.g., `~/.hermes/profiles/*/SOUL.md`)
- **Cursor**: If `~/.cursor/rules/` exists, create a new file `~/.cursor/rules/agent-wiki.md` with the text above. Do not modify other rule files.

If the file already contains "## Agent Wiki", skip — it's already installed.

## Step 7: Personalize

Based on Question 3 (use case), personalize the `## What This Is` section in AGENTS.md. Replace the placeholder with a concrete 2-3 sentence description.

If they said "software development", suggest creating an initial project page:
"Want me to create a wiki page for a current project? Give me the name."

## Step 8: Clean up the wiki folder

Now that skills and wikictl are installed on the machine, remove the tool files from the wiki folder. The user's wiki should only contain their content.

```bash
cd [wiki-path]
rm -rf skills/
rm -rf tools/
rm -f INSTALL.md CLAUDE.md README.md LICENSE package.json .gitignore
rm -rf .git
```

What stays:

```
[wiki-path]/
├── raw/
├── wiki/
├── outputs/
└── AGENTS.md
```

AGENTS.md stays because it's the schema — agents read it to know the rules.

## Step 9: Verify and report

```bash
wikictl status
wikictl lint
```

Report:

- Where the wiki lives (clean, only content files)
- Where wikictl is installed (PATH)
- Which agents got the skills
- What was added to their configs (quote the exact lines)
- What was NOT touched
- How to start: "Type `/agent-wiki-start` in any agent session"
