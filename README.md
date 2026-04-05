# Agent Wiki

A shared knowledge base that any LLM agent can read and maintain.
Knowledge compounds across sessions. Inspired by
[Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## Install

### As a skill

```bash
npx skills add originlabs-app/agent-wiki
```

### As a standalone repo

```bash
git clone https://github.com/originlabs-app/agent-wiki.git
cd agent-wiki
./install.sh
```

Open the folder in your agent (Claude Code, Codex, Cursor, Gemini CLI, etc.).
It reads `SKILL.md` automatically.

### Inside an existing repo

Give `INSTALL.md` to your agent:

```
Read INSTALL.md and set up agent-wiki on my machine.
```

## Usage

Two commands. That's it.

### Start your session

```
/agent-wiki start
```

The agent reads the wiki, briefs you on context, asks what you're working on.

### End your session

```
/agent-wiki finish
```

The agent asks what happened, proposes updates, writes them back to the wiki.

### CLI

The `wikictl` CLI handles wiki operations:

```bash
wikictl status                              # health check
wikictl ingest "My Project" raw/source.md   # register a source
wikictl query "search terms"                # search wiki + raw
wikictl sync claude done "finished auth"    # end-of-session write-back
```

## Use cases

See [`docs/examples/`](docs/examples/) for walkthroughs:
research projects, software projects, business operations, analysis dossiers.

## License

MIT

---

Advanced: see `docs/` for MCP, instances, and tool configs.
