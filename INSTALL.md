# Install agent-wiki on this machine

You are an LLM agent. A human has asked you to set up agent-wiki on their machine. Follow these instructions carefully. **Do not overwrite any existing config files.** Append or merge only.

## Step 1: Check prerequisites

- Verify `./cli/wikictl` exists and is executable. If not: `chmod +x ./cli/wikictl`
- Run `./cli/wikictl init` to ensure `wiki/` and `raw/` directories exist.

## Step 2: Configure your tool

Find which tool you are running in and add the agent-wiki protocol to its config.

### If Claude Code

Config file: `~/.claude/CLAUDE.md` (global) or `CLAUDE.md` in the project root.

**If the file already exists:** append the section below at the end. Do not replace the file.
**If the file does not exist:** create it with only the section below.

```markdown
## Agent Wiki — Shared Knowledge Base

If `./cli/wikictl` exists in the current repo or `~/dev/internal/agent-wiki/cli/wikictl` is available:

### Before starting work
1. Run `wikictl status` to check if a wiki is configured.
2. If configured, read the wiki index.
3. Find and read the project page matching your current work.

### After completing meaningful work
4. Update the relevant project page with what changed.
5. If a significant decision was made, create a decision page in wiki/decisions/.
6. Run `wikictl sync claude <op> "<description>"`.

### If wikictl is not available
Continue normally. Do not fail.
```

### If Codex

Config file: `~/.codex/AGENTS.md` or `AGENTS.md` in the project root.

Same logic: append if exists, create if not. Use the same section as above but replace `claude` with `codex` in the sync command.

### If Cursor

Config file: `~/.cursor/rules/agent-wiki.mdc` or `AGENTS.md` in the project root.

Same logic: append if exists, create if not. Replace `claude` with `cursor` in the sync command.

### If Hermes

Config file: `~/.hermes/skills/agent-wiki/SKILL.md`

**If the file already exists:** read it, check if agent-wiki protocol is already there. If not, append.
**If the file does not exist:** create it with this content:

```markdown
---
name: agent-wiki
description: Read and write to a shared Karpathy-style wiki. Use wikictl for ingest, query, heal, sync.
tags: [wiki, knowledge-base, memory, multi-agent]
---

# Agent Wiki

## When to activate
- Start of any session where project context would help.
- End of any session where knowledge was produced.
- When the user says "ingest", "query wiki", "lint wiki", "sync".

## Before starting work
1. Run wikictl status to check if a wiki is configured.
2. If configured, read the wiki index.
3. Find and read the project page matching the current work.

## After completing meaningful work
4. Update the relevant project page with what changed.
5. If a significant decision was made, create a decision page.
6. Run wikictl sync hermes <op> "<description>".

## If wikictl is not available
Continue normally. Do not fail.
```

## Step 3: Configure an instance (optional)

If the user has an existing vault or folder they want agent-wiki to use:

1. Create `~/.agent-wiki/instances/` if it doesn't exist.
2. Ask the user: "Where is your wiki folder?" (e.g., `~/Documents/my-vault/wiki`)
3. Ask the user: "Where should raw sources go?" (e.g., `~/Documents/my-vault/raw`)
4. Create a config file:

```
# ~/.agent-wiki/instances/<name>.conf
WIKI_ROOT=/path/to/wiki
RAW_ROOT=/path/to/raw
```

5. Test: `./cli/wikictl --instance <name> status`

If the user doesn't have an existing vault, skip this step. The wiki in the repo itself works as default.

## Step 4: Verify

Run:
- `./cli/wikictl status` — should show wiki project pages count
- `./cli/wikictl lint` — should say "lint: ok"
- `./cli/wikictl query test` — should not error

Report the results to the user.

## Rules

- **NEVER overwrite an existing config file.** Append or merge only.
- **NEVER delete user content.**
- **If unsure, ask the user before modifying any file outside the repo.**
- If a section "Agent Wiki" already exists in a config file, skip — it's already installed.
