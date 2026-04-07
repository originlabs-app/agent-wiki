# Ideas — Atlas Roadmap

## Near-term (Next 2 weeks)
- Benchmark suite with automated CI checks (weekly)
- Graph diff — show what changed between scans
- Multi-repo scanning — scan a monorepo vs individual repos

## Mid-term (Next month)
- LLM-powered extraction — tree-sitter for structure, LLM for semantics
- Graph visualization improvements — community coloring, force layout
- Export formats — Mermaid.js diagrams, GraphML, Neo4j import
- Confidence calibration — how accurate are INFERRED edges?

## Long-term (Next quarter)
- ARA cloud storage integration
- Real-time graph updates via file watchers
- Collaborative editing — multiple agents contributing to same wiki
- Plugin system for custom extractors
- Query language — Cypher-like graph queries
- Auto-generated documentation from wiki

## Rejected Ideas
- GraphQL API — overkill for now, REST is simpler and covers all needs
- MongoDB backend — filesystem + JSON is simpler and portable
- React dashboard — static SPA is faster to build and deploy
- Custom graph DB — NetworkX + JSON is good enough for < 100K nodes
