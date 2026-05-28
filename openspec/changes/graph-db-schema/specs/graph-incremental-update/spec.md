## ADDED Requirements

### Requirement: Diff-driven incremental update
The system SHALL accept a list of changed file paths and update only the affected subgraph, leaving unaffected nodes and edges intact.

#### Scenario: Single file changed
- **WHEN** one file is modified in a PR diff
- **THEN** only edges originating from functions in that file are deleted and re-created
- **THEN** functions in all other files are not modified

#### Scenario: Multiple files changed
- **WHEN** multiple files are modified in a single PR diff
- **THEN** all changed files are processed atomically in a single transaction

### Requirement: Commit-level idempotency
The system SHALL store `last_parsed_commit` on each `File` node and skip re-parsing if the commit hash has not changed.

#### Scenario: Same commit re-processed
- **WHEN** the incremental update is triggered for a commit that has already been processed
- **THEN** no graph mutations occur and the operation returns immediately

#### Scenario: New commit processed
- **WHEN** the incremental update is triggered for a new commit SHA
- **THEN** changed files are re-parsed and the `last_parsed_commit` property is updated

### Requirement: Full-repo initial scan
The system SHALL support a full-repo parse mode that populates the graph from scratch, used during initial onboarding.

#### Scenario: Empty graph full scan
- **WHEN** the full-repo scan is triggered on an empty graph
- **THEN** all files in the repository are parsed and their nodes and edges are inserted

#### Scenario: Full scan on existing graph
- **WHEN** the full-repo scan is triggered on a graph with existing data
- **THEN** the graph is cleared and rebuilt from the current repository state
