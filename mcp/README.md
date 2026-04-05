# MCP

This transport is optional.

`agent-wiki` works with:

- `SKILL.md` as the user-facing workflow
- `cli/wikictl` as the local engine
- `mcp/server.mjs` as an optional tool transport for agents that speak MCP

Run:

```bash
npm install
npm run mcp
```

Or attach to an external instance:

```bash
npm run mcp -- --instance origin-labs
```
