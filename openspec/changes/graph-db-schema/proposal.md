## Why

Fennec's core engine traverses call graphs and data flow paths — a fundamentally graph-shaped problem. We need to select a graph database and define its schema before any other code can be written, since every downstream component (taint tracker, context assembler, feedback loop) depends on how nodes and edges are modeled.

## What Changes

- Select and integrate a graph DB (primary candidate: Neo4j; alternatives: Amazon Neptune, Apache AGE on Postgres)
- Define the node types: `Function`, `File`, `Module`, `Service`
- Define the edge types: `CALLS`, `DATA_FLOW`, `IMPORTS`, `CROSS_SERVICE`
- Define taint-specific properties: `is_source`, `is_sink`, `is_sanitizer`, `taint_type`
- Specify indexing strategy for fast traversal (source-to-sink path queries)
- Specify incremental update protocol (insert/delete edges on PR diff)

## Non-goals

- Vector DB integration (separate concern, optional layer)
- Language-specific parser implementation (covered by `language-parser-coverage` change)
- Populating the graph (depends on parser output)

## Capabilities

### New Capabilities

- `graph-db-core`: Graph database connection, schema initialization, and CRUD operations for nodes and edges
- `graph-traversal`: Taint path traversal queries — source-to-sink walks, shortest path, reachability checks
- `graph-incremental-update`: Diff-based edge insertion and deletion protocol for PR incremental mode

### Modified Capabilities

<!-- none — this is a greenfield component -->

## Impact

- All other pipeline stages depend on this schema being stable before implementation
- Language parsers emit into this schema; context assembler reads from it
- Performance characteristics of path traversal queries directly affect scan latency
