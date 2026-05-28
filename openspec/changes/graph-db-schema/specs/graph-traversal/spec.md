## ADDED Requirements

### Requirement: Source-to-sink path enumeration
The system SHALL enumerate all paths from a given set of source `Function` nodes to a given set of sink `Function` nodes following `DATA_FLOW` and `CALLS` edges.

#### Scenario: Direct path found
- **WHEN** a source function directly passes user input to a sink function via a data flow edge
- **THEN** the traversal returns a `TaintPath` containing both nodes and the connecting edge

#### Scenario: Multi-hop path found
- **WHEN** user input flows through two or more intermediate functions before reaching a sink
- **THEN** the traversal returns a `TaintPath` listing all intermediate functions with file and line references

#### Scenario: No path exists
- **WHEN** there is no data flow or call chain connecting a source to any sink
- **THEN** the traversal returns an empty result set without error

### Requirement: Path length limit
The system SHALL not return taint paths longer than a configurable maximum hop count (default: 10).

#### Scenario: Long path truncated
- **WHEN** the shortest path between a source and sink exceeds the configured maximum hops
- **THEN** the path is not returned and a warning is logged indicating truncation

### Requirement: Sanitizer-aware traversal
The system SHALL flag taint paths that pass through a node marked `is_sanitizer=true`.

#### Scenario: Sanitized path detected
- **WHEN** a taint path passes through a function with `is_sanitizer=true` for the relevant `taint_type`
- **THEN** the returned `TaintPath` is marked `sanitized=true`

#### Scenario: Unsanitized path detected
- **WHEN** no sanitizer function appears on the taint path
- **THEN** the returned `TaintPath` is marked `sanitized=false`

### Requirement: N-hop neighbor fetch
The system SHALL return all `Function` nodes reachable from a given function within N hops via any edge type.

#### Scenario: Context window assembly
- **WHEN** the context assembler requests neighbors of a function with depth=2
- **THEN** the query returns all functions directly called by or calling that function, plus their direct neighbors
