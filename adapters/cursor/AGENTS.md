# Agent Wiki — Cursor Adapter

Read `AGENTS.md` for the full contract.

## Wiki Protocol

If `./cli/wikictl` exists in this repo or is available on PATH:

### Before starting work

1. Run `./cli/wikictl status` to check if a wiki is configured.
2. If configured, read the wiki index it points to.
3. Find and read the project page matching your current work.
4. You now have context — decisions, failures, current status, next steps.

### After completing meaningful work

5. Update the relevant project page with what changed.
6. If you made a significant decision, create a decision page.
7. Run `./cli/wikictl sync cursor <op> "<description>"`.

### If wikictl is not available

Continue normally. Do not fail. Do not ask the user to install anything.

## Keep it simple

This adapter just tells you to use wikictl. The contract is in `AGENTS.md`. The config is in `~/.agent-wiki/instances/` or resolved by wikictl automatically.
