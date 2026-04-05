# Install agent-wiki

You are an LLM agent setting up agent-wiki.

Rules: never overwrite existing configs. Install once, symlink for each agent.

## Step 1: Detect agents

Check silently which agents are installed (~/.claude, ~/.codex, ~/.cursor,
~/.hermes). Report what you found.

## Step 2: Ask one question

> Do you have an existing folder or vault for the wiki?
> If yes, give me the path. If no, I'll use the built-in wiki/ and raw/.

If given a path, write a config to `~/.agent-wiki/instances/<name>.conf`
with WIKI_ROOT and RAW_ROOT.

## Step 3: Install

```bash
chmod +x ./cli/wikictl && ./cli/wikictl init
mkdir -p ~/.agents/skills/agent-wiki
cp SKILL.md ~/.agents/skills/agent-wiki/SKILL.md
```

Symlink into each detected agent's skills directory:
`ln -sfn ~/.agents/skills/agent-wiki ~/.claude/skills/agent-wiki` (etc.)

## Step 4: Verify

Run `./cli/wikictl status`. Tell the user what was installed.
