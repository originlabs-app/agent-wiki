# Vault Organization

`agent-wiki` is agnostic about the rest of your vault or repo.

## Minimum required

This is all `agent-wiki` needs:

```text
your-vault/
├── wiki/
└── raw/
```

- `wiki/` is the compiled knowledge layer written by agents.
- `raw/` is the immutable drop zone for sources.

Everything else is your organization, not `agent-wiki`'s concern.

## Recommended layout

```text
your-vault/
├── wiki/
│   ├── index.md
│   ├── log.md
│   ├── projects/
│   ├── sources/
│   └── decisions/
├── raw/
│   ├── transcripts/
│   ├── briefs/
│   ├── docs/
│   └── mails/
└── ...your own folders
```

Examples of `...your own folders`:

- `01-Projects/`, `02-Clients/`
- one folder per client
- one folder per date
- nothing at all beyond `wiki/` and `raw/`

## Attach mode

If you already have a vault, keep it as-is and point `agent-wiki` at it with a config file:

```text
~/.agent-wiki/instances/origin-labs.conf
```

Example:

```bash
INSTANCE_NAME=origin-labs
WIKI_ROOT=/Users/you/Documents/second-brain/wiki
RAW_ROOT=/Users/you/Documents/second-brain/raw
SOURCE_DIRS=/Users/you/Documents/second-brain/01-Projects:/Users/you/Documents/second-brain/02-Clients
```

Then run:

```bash
./cli/wikictl --instance origin-labs status
```

Obsidian is optional. `agent-wiki` only needs Markdown directories.
