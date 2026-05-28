## ADDED Requirements

### Requirement: ParseResult to graph translation
The system SHALL translate a `ParseResult` into graph upsert and edge creation calls without any direct database access.

#### Scenario: Function nodes emitted
- **WHEN** a `ParseResult` containing three `FunctionDef` objects is passed to the graph emitter
- **THEN** three `upsert_function()` calls are made with the correct properties

#### Scenario: Call edges emitted
- **WHEN** a `FunctionDef` contains two `CallRef` entries
- **THEN** two `CALLS` edges are created from the function node to the callee nodes

### Requirement: Stable function ID generation
The system SHALL generate a deterministic function ID from `(repo_id, file_path, function_name, language)`.

#### Scenario: Same function produces same ID
- **WHEN** the same function is parsed twice in different runs
- **THEN** the generated ID is identical, enabling upsert idempotency

#### Scenario: Name collision across files produces different IDs
- **WHEN** two different files each contain a function named `handle_request`
- **THEN** the two functions produce different IDs

### Requirement: Emission idempotency
The system SHALL not create duplicate nodes or edges when the same `ParseResult` is emitted twice.

#### Scenario: Re-emission after re-parse
- **WHEN** a file is parsed and emitted, then parsed and emitted again with no changes
- **THEN** the graph node and edge counts remain unchanged
