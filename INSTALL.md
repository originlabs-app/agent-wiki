# Install agent-wiki

You are an LLM agent setting up `agent-wiki` for this repo.

Rules:

- do not overwrite existing configs
- append or merge only
- install the shared skill once, then symlink it into each supported agent
- treat this repo as the starting vault

## Step 1: Detect the environment

Check silently which agent environments exist, for example:

- `~/.claude/`
- `~/.codex/`
- `~/.cursor/`
- `~/.hermes/`

Report what you found.

## Step 2: Prepare the repo

Run:

```bash
chmod +x ./cli/wikictl
./cli/wikictl init
```

## Step 3: Install the shared skill

Install one canonical copy:

```bash
mkdir -p ~/.agents/skills/agent-wiki
cp SKILL.md ~/.agents/skills/agent-wiki/SKILL.md
```

Then symlink that shared skill into each detected agent's skill directory if the
agent supports skills.

Never overwrite an unrelated file.

## Step 4: Verify

Run:

```bash
./cli/wikictl status
./cli/wikictl lint
```

Finally, report:

- what you installed
- what you linked
- which files you did not touch
