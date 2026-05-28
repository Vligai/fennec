## ADDED Requirements

### Requirement: Verdict storage
The system SHALL store developer verdicts with all fields defined in the signal store schema.

#### Scenario: Real vulnerability verdict stored
- **WHEN** a developer marks a finding as `real_vuln`
- **THEN** a verdict record is created with `verdict="real_vuln"`, `path_hash`, `reviewer_id`, `repo_id`, `service_id`, `pattern_fingerprint`, and `created_at`

#### Scenario: False positive verdict stored
- **WHEN** a developer marks a finding as `false_positive`
- **THEN** a verdict record is created with `verdict="false_positive"` and all required fields

### Requirement: "Won't fix" suppression firewall
The system SHALL store `wont_fix` verdicts for suppression lookup but SHALL NEVER return them from queries that feed trust scores or training signals.

#### Scenario: Won't fix verdict stored
- **WHEN** a developer marks a finding as `wont_fix`
- **THEN** a verdict record is stored with `verdict="wont_fix"`

#### Scenario: Won't fix excluded from trust queries
- **WHEN** the trust score query is executed for any pattern
- **THEN** verdicts with `verdict="wont_fix"` are excluded from all aggregations

### Requirement: Suppression lookup
The system SHALL return whether a given `path_hash` has an active `wont_fix` verdict.

#### Scenario: Suppressed finding identified
- **WHEN** a scan produces a finding whose `path_hash` matches a `wont_fix` verdict
- **THEN** the finding is marked as suppressed and not surfaced to the developer

### Requirement: Path hash computation
The system SHALL compute `path_hash` as `sha256` of the sorted list of function node IDs on the taint path.

#### Scenario: Same path produces same hash
- **WHEN** the same taint path is hashed twice
- **THEN** both computations produce the same `path_hash`

#### Scenario: Different paths produce different hashes
- **WHEN** two taint paths differ by at least one function node
- **THEN** their `path_hash` values are different
