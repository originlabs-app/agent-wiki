---
name: llm-wiki-maintainer
description: Maintain a Karpathy-style raw/wiki knowledge base for multi-agent workflows.
---

# LLM Wiki Maintainer

Read [AGENTS.md](../../AGENTS.md) first.

Use this skill when you need to:

- ingest sources into `raw/`
- compile a project summary into `wiki/projects/*.md`
- update `wiki/index.md`
- append to `wiki/log.md`
- lint the wiki for stale or missing structure

Keep the workflow simple:

1. Read the index.
2. Read the relevant project page.
3. Only open raw sources when necessary.
4. Write the result back into the wiki.

