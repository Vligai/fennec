## 1. Project Setup

- [ ] 1.1 Add `neo4j` Python driver and `docker-compose` Neo4j service to project dependencies
- [ ] 1.2 Create `fennec/graph/` package with `__init__.py`, `client.py`, `schema.py`, `queries.py`
- [ ] 1.3 Write a Docker Compose file with Neo4j Community Edition for local dev (ports 7474/7687)

## 2. Schema Initialization

- [ ] 2.1 Define all node constraints and indexes in `schema.py` (Function, File, Module, Service)
- [ ] 2.2 Implement `GraphClient.__init__()` that runs schema initialization idempotently on startup
- [ ] 2.3 Write a test: empty DB → init → re-init produces no duplicates and no errors

## 3. Core CRUD Operations

- [ ] 3.1 Implement `upsert_function(props)` — merge on stable function ID, update properties
- [ ] 3.2 Implement `upsert_file(props)` and `upsert_module(props)`
- [ ] 3.3 Implement `add_edge(from_id, to_id, edge_type, props)` for all defined edge types
- [ ] 3.4 Implement `delete_file_edges(file_path)` — removes all CALLS and DATA_FLOW edges from functions in the file
- [ ] 3.5 Implement `prune_orphan_functions()` — deletes Function nodes with no DEFINED_IN edge
- [ ] 3.6 Write unit tests for each CRUD operation against a live test Neo4j instance

## 4. Traversal Queries

- [ ] 4.1 Implement `find_taint_paths(source_ids, sink_ids, max_hops)` — returns `List[TaintPath]`
- [ ] 4.2 Implement sanitizer-aware path flagging: `TaintPath.sanitized` based on is_sanitizer nodes on path
- [ ] 4.3 Implement `get_neighbors(function_id, depth)` — returns N-hop neighbor functions for context assembly
- [ ] 4.4 Define `TaintPath` dataclass: `nodes`, `edges`, `sanitized`, `hop_count`
- [ ] 4.5 Write traversal tests: direct path, multi-hop path, no path, sanitized path

## 5. Incremental Update Protocol

- [ ] 5.1 Implement `incremental_update(changed_file_paths, commit_sha)` orchestration method
- [ ] 5.2 Add `last_parsed_commit` check — skip files whose commit SHA matches stored value
- [ ] 5.3 Implement `full_repo_scan(repo_path)` — clears graph and rebuilds from scratch
- [ ] 5.4 Write integration test: two-commit scenario shows only changed-file edges are updated
