# MCP Layer

This directory defines the transport boundary for agents that can talk MCP.

## Rule

Keep the MCP server thin. It should expose the same operations as `wikictl`:

- read the wiki
- search project pages
- append log entries
- lint the structure
- sync compiled knowledge back to `wiki/`

The stable contract lives in `AGENTS.md` and `contract/manifest.yaml`.
The CLI is the local executable reference implementation.

