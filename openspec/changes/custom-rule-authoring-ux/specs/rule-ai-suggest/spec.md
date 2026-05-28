## ADDED Requirements

### Requirement: AI-powered candidate suggestion
The system SHALL use an LLM call with graph context to propose candidate patterns for a specified field (source, sink, or sanitizer) and vulnerability class.

#### Scenario: Sanitizer candidates proposed
- **WHEN** the user runs `fennec rules suggest --field sanitizer --vuln-class cmdi`
- **THEN** the system queries the graph for function names, sends them to the LLM, and returns a ranked list of candidate sanitizer patterns with confidence scores

#### Scenario: Only graph-verified candidates returned
- **WHEN** the LLM proposes a pattern that does not match any function node in the graph
- **THEN** that candidate is filtered out before being presented to the user

### Requirement: Human approval before activation
The system SHALL require explicit human approval for each suggested candidate before writing it to `custom_rules.yaml`.

#### Scenario: Approval flow
- **WHEN** the user selects a candidate from the suggestion list
- **THEN** the system appends the approved entry to `custom_rules.yaml` and reports the file path

#### Scenario: Rejected candidate not written
- **WHEN** the user rejects a candidate
- **THEN** the candidate is not written to `custom_rules.yaml`

### Requirement: Suggestion validated against codebase
The system SHALL display the file paths and line numbers where each suggested pattern appears, so the user can verify it before approving.

#### Scenario: Pattern evidence shown
- **WHEN** a candidate pattern is presented for approval
- **THEN** the system shows at least one file path and line number where the pattern appears in the current codebase
