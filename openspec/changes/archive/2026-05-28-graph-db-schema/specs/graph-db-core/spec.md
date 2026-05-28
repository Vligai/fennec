## ADDED Requirements

### Requirement: Graph database initialization
The system SHALL initialize a Neo4j database connection and ensure the required schema constraints and indexes exist on startup.

#### Scenario: First-time initialization
- **WHEN** the graph client is instantiated for the first time against an empty database
- **THEN** all node indexes and uniqueness constraints defined in the schema are created without error

#### Scenario: Idempotent re-initialization
- **WHEN** the graph client is instantiated against a database that already has the schema
- **THEN** initialization completes without error and does not duplicate constraints or indexes

### Requirement: Function node upsert
The system SHALL upsert `Function` nodes by a stable unique ID derived from file path, function name, and language.

#### Scenario: New function insertion
- **WHEN** a parser emits a function not previously in the graph
- **THEN** a new `Function` node is created with all required properties (`id`, `name`, `file_path`, `line_start`, `line_end`, `language`)

#### Scenario: Existing function update
- **WHEN** a parser emits a function whose ID already exists in the graph
- **THEN** the existing node's properties are updated in-place without creating a duplicate

### Requirement: Edge creation
The system SHALL create typed directed edges (`CALLS`, `DATA_FLOW`, `IMPORTS`, `DEFINED_IN`, `BELONGS_TO`, `CROSS_SERVICE`) between existing nodes.

#### Scenario: Call edge creation
- **WHEN** a parser identifies that function A calls function B
- **THEN** a `CALLS` edge is created from A to B with `call_site_line` property

#### Scenario: Data flow edge creation
- **WHEN** a parser identifies that a variable from function A flows into function B
- **THEN** a `DATA_FLOW` edge is created from A to B with `variable` property

### Requirement: File-scoped edge deletion
The system SHALL delete all edges originating from functions defined in a specified file, without deleting the function nodes themselves.

#### Scenario: Pre-reparse cleanup
- **WHEN** a file is about to be re-parsed after a diff
- **THEN** all `CALLS` and `DATA_FLOW` edges from functions in that file are deleted
- **THEN** the function nodes themselves remain until the re-parse upserts or orphan-prunes them

### Requirement: Orphan node pruning
The system SHALL remove `Function` nodes that have no `DEFINED_IN` edge after an incremental update completes.

#### Scenario: Deleted function cleanup
- **WHEN** a function is removed in a PR diff and the file is re-parsed
- **THEN** the old `Function` node is deleted from the graph
