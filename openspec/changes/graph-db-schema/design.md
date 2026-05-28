## Context

The code graph index (pipeline stage 2) is the structural backbone of Fennec. Every other stage reads from or writes to it: parsers populate it, the taint tracker queries it, the context assembler walks it, and the feedback loop annotates it. The schema must be expressive enough for multi-language cross-service taint paths while staying fast enough for sub-second path queries on repos with ~100k functions.

## Goals / Non-Goals

**Goals:**
- Select a graph DB with strong Cypher or Gremlin query support and a Python client
- Define node/edge schema stable enough to build all other pipeline stages against
- Specify the incremental update protocol (diff → graph mutation)
- Define indexing strategy for source-to-sink traversal

**Non-Goals:**
- Parser implementation (feeds this schema, not part of this change)
- Vector DB integration
- Multi-tenant data isolation (future work)

## Decisions

**Decision 1: Neo4j as primary graph DB**

Neo4j over alternatives (Amazon Neptune, Apache AGE):
- Native Cypher query language is the most readable for path traversal
- Official Python driver (`neo4j` package) is mature and well-documented
- Local embedded mode (`neo4j-embedded` / via Docker) works for dev without cloud dependency
- Neptune is AWS-only and adds operational complexity too early; AGE requires Postgres with an extension that adds friction

*Alternative kept open*: Apache AGE on Postgres if we later need to colocate with relational data (signal store). Decision can be revisited after signal store design.

**Decision 2: Node schema**

| Label | Key properties |
|---|---|
| `Function` | `id`, `name`, `file_path`, `line_start`, `line_end`, `language`, `is_source`, `is_sink`, `is_sanitizer`, `taint_types[]` |
| `File` | `id`, `path`, `language`, `repo_id`, `last_parsed_commit` |
| `Module` | `id`, `name`, `language`, `file_path` |
| `Service` | `id`, `name`, `repo_id` |

`Function` is the primary traversal node. Files and modules are parents for scoping queries. Service nodes enable cross-service edge representation.

**Decision 3: Edge schema**

| Type | From → To | Key properties |
|---|---|---|
| `CALLS` | Function → Function | `call_site_line`, `conditional` |
| `DATA_FLOW` | Function → Function | `variable`, `param_index` |
| `IMPORTS` | File → Module | `import_alias` |
| `DEFINED_IN` | Function → File | — |
| `BELONGS_TO` | File → Service | — |
| `CROSS_SERVICE` | Function → Function | `protocol` (http/grpc/kafka), `endpoint` |

`DATA_FLOW` edges carry the taint — they represent a variable flowing from one function to another. `CALLS` edges represent control flow. Both are needed; taint traversal primarily follows `DATA_FLOW`, with `CALLS` used to assemble code context.

**Decision 4: Indexing**

- Index `Function.is_source` and `Function.is_sink` for fast source/sink enumeration at scan start
- Index `Function.file_path` + `Function.name` for parser upsert lookups
- Index `File.last_parsed_commit` for incremental diff check

**Decision 5: Incremental update protocol**

On PR diff:
1. Parse list of changed files from diff
2. For each changed file: delete all `DEFINED_IN`, `CALLS`, `DATA_FLOW` edges originating from functions in that file
3. Re-parse changed files and upsert new nodes/edges
4. Orphaned `Function` nodes (no `DEFINED_IN` edge) are pruned

This avoids full graph rebuild on every PR while keeping the graph consistent.

## Cross-Component Interfaces

- **Parser → Graph**: parsers call `graph.upsert_function()`, `graph.add_edge()`, `graph.delete_file_edges()` via a thin Python client wrapper
- **Taint tracker → Graph**: issues Cypher `MATCH` path queries; returns `List[TaintPath]`
- **Context assembler → Graph**: fetches N-hop neighbors of a function node; returns `List[Function]`
- **Feedback loop → Graph**: annotates `Function` nodes with `trusted_sanitizer=true` via property update

## Risks / Trade-offs

- **Schema migrations** → Neo4j is schemaless; property additions are safe, but edge type renames require a migration script. Document all schema changes in a `SCHEMA_CHANGELOG.md`.
- **Local vs. hosted Neo4j** → Free Community edition lacks clustering. AuraDB (cloud) adds latency. For initial version: local Docker is sufficient; AuraDB for production.
- **`DATA_FLOW` edge completeness** → Static analysis is an approximation. Missing edges = missed vulns; extra edges = false positives. Accept imperfection; let LLM reasoning compensate for borderline cases.
- **Cost at scale** → Large monorepos (>500k functions) may need graph partitioning by service. Defer; not a day-1 problem.

## Open Questions

- Should `CROSS_SERVICE` edges be inferred statically or require manual annotation via custom rules? (Lean toward custom rules initially — static inference is hard.)
- Does the signal store (separate change) live in the same Neo4j instance or a separate DB? (Prefer separate for clean separation of concerns.)
