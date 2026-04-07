# Atlas API Reference

## Base URL

```
http://localhost:7100/api/v1
```

## Authentication

All endpoints require a Bearer token:

```
Authorization: Bearer <token>
```

Tokens are created via the Auth module and include scope restrictions.

## Endpoints

### POST /scan

Scan a directory and build/update the knowledge graph.

**Request:**
```json
{
  "path": "/path/to/repo",
  "incremental": true,
  "force": false
}
```

**Response:**
```json
{
  "nodes_extracted": 142,
  "edges_extracted": 387,
  "graph_nodes": 1420,
  "graph_edges": 3870,
  "communities": 12,
  "health_score": 78.5
}
```

### POST /query

Query the knowledge graph from a start concept.

**Request:**
```json
{
  "question": "auth",
  "mode": "bfs",
  "depth": 3
}
```

**Response:**
```json
{
  "nodes": 24,
  "edges": 31,
  "estimated_tokens": 890,
  "results": ["AuthModule", "DBClient", "APIServer"]
}
```

### POST /ingest

Ingest a URL or file into the knowledge base.

**Request:**
```json
{
  "url": "https://example.com/article",
  "title": "Optional Title"
}
```

**Response:**
```json
{
  "status": "ingested",
  "path": "raw/ingested/2026-04-07-example-com-article.md"
}
```

### GET /audit

Run a health audit of the knowledge base.

**Response:**
```json
{
  "health_score": 72.0,
  "orphan_pages": 3,
  "broken_links": 2,
  "stale_pages": 5,
  "god_nodes": [["auth", 15], ["db", 12]]
}
```

### GET /stats

Quick graph statistics.

**Response:**
```json
{
  "nodes": 1420,
  "edges": 3870,
  "communities": 12,
  "confidence_breakdown": {"EXTRACTED": 2800, "INFERRED": 900, "AMBIGUOUS": 170}
}
```

## Rate Limits

- **Scans**: 10 per hour per user (100 PRO, unlimited ENTERPRISE)
- **Queries**: 60 per minute
- **Ingest**: 30 per hour
- **Audit/Stats**: unlimited
