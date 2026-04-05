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

## Step 2: Ask 3-5 setup questions

### Question 1: Which agents?

"I detected [X, Y, Z] on your machine. Do you want agent-wiki installed for all of them, or just some?"

### Question 2: Where should the wiki live?

"Two options:
- **Here** — this repo becomes your wiki. Simplest way to start.
- **Somewhere else** — you already have a folder, vault, or repo where you want the wiki to live. I'll point agent-wiki there.

Where do you want it?"

If they give a path, check if wiki/ and raw/ exist there. If not, create them.

### Question 3: How will you use it?

"What's your main use case?
- **Research** — accumulating knowledge from articles, papers, sources over time
- **Software development** — tracking architecture decisions, project context across coding sessions
- **Business / project management** — client notes, meeting transcripts, strategy docs
- **Documentation** — maintaining a living knowledge base
- **All of the above**

This helps me set up the right starting structure."

Based on the answer, you can suggest project pages to create or skip this if they want to start empty.

### Question 4: Mode?

"Will you use this wiki:
- **As your main workspace** — you open your agent directly in the wiki repo
- **As a second brain** — you code in other repos and the wiki lives alongside as shared memory
- **Both**"

## Step 3: Install the skill

Install one canonical copy:

```bash
chmod +x ./cli/wikictl
./cli/wikictl init
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

## Step 4: Add wiki awareness to existing configs

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

## Step 5: Configure instance (if wiki lives elsewhere)

If the user chose a different location in Question 2:

```bash
mkdir -p ~/.agent-wiki/instances
cat > ~/.agent-wiki/instances/[name].conf << EOF
WIKI_ROOT=[path]/wiki
RAW_ROOT=[path]/raw
EOF
```

Test: `./cli/wikictl --instance [name] status`

## Step 6: Verify and report

```bash
./cli/wikictl status
./cli/wikictl lint
```

Report to the user:

- Which agents got the skill
- Where the wiki lives
- What was added to their configs (quote the exact lines)
- What was NOT touched
- How to start: "Open your agent and type /agent-wiki start"
