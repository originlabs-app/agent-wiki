# Atlas Architecture

## Overview

Atlas is a knowledge engine for AI agents. It scans codebases, documents, and research papers to build a persistent knowledge graph.

## Core Components

### Scanner

Multi-modal extraction engine:
- **AST parsing** via tree-sitter for code files
- **Semantic extraction** via LLM dispatch for docs and images
- **Incremental mode** with SHA256 cache

### Graph Engine

NetworkX-backed graph with:
- Node/Edge persistence as JSON
- BFS/DFS traversal with configurable depth
- Shortest path between concepts
- Community detection (Leiden algorithm)

### Wiki Engine

Markdown-first knowledge base:
- Frontmatter-powered pages (projects, sources, decisions, concepts)
- [[wikilink]] cross-references
- Confidence scoring per page

### Linker

Bidirectional sync between graph and wiki:
- Graph → Wiki: suggests pages and connections
- Wiki → Graph: extracts structure from wikilinks

## Data Flow

```
Source files → Scanner → Extraction → GraphEngine ─→ Analyzer
     ↓                                                  ↓
   Wiki ←── Linker ←──── Graph ←─── Linker ←─── Suggestions
```

## Design Decisions

1. **Wiki is source of truth**, graph is derived
2. **Protocol-based storage** for local/cloud portability
3. **No in-memory state** — all data persisted as JSON/Markdown
