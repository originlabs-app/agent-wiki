# Agent Wiki Schema

This project follows the LLM Wiki pattern.

## Core folders

- `raw/` contains immutable source material.
- `wiki/` contains the compiled knowledge base maintained by the agent.
- `outputs/` contains generated answers, reports, and other derived artifacts.

## Rules

1. Never edit files in `raw/`.
2. Keep `wiki/index.md` current.
3. Append meaningful operations to `wiki/log.md`.
4. Prefer updating the wiki over leaving knowledge in chat history.
5. Good outputs may be filed back into relevant wiki pages.

## Read order

1. `wiki/index.md`
2. relevant pages in `wiki/projects/`, `wiki/sources/`, `wiki/decisions/`
3. `raw/` only when more detail is needed

## Operations

- `ingest`: integrate new sources from `raw/` into the wiki
- `query`: answer questions against the wiki with citations
- `lint`: detect contradictions, gaps, dead links, orphan pages, and stale content
