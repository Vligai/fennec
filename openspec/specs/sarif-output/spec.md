## Requirements

### Requirement: SARIF 2.1.0 compliance
The system SHALL produce output that validates against the SARIF 2.1.0 JSON schema.

#### Scenario: Output passes schema validation
- **WHEN** a scan produces any number of findings
- **THEN** the SARIF output file validates against the official SARIF 2.1.0 JSON schema without errors

### Requirement: Code flow inclusion
The system SHALL include the full taint path as a SARIF `codeFlow` with one location per hop.

#### Scenario: Multi-hop path in code flow
- **WHEN** a finding has a 4-hop taint path
- **THEN** the SARIF result includes a `codeFlows[0].threadFlows[0].locations` array with 4 entries, each with file and line

### Requirement: Severity to SARIF level mapping
The system SHALL map Fennec severity to SARIF `level` as: critical/high → `error`; medium → `warning`; low → `note`.

#### Scenario: High severity maps to error
- **WHEN** a finding has `Severity.HIGH`
- **THEN** the SARIF result has `"level": "error"`

### Requirement: Fix suggestion in SARIF
The system SHALL include the LLM fix suggestion as a SARIF `fix` with a description text.

#### Scenario: Fix included in result
- **WHEN** a finding has a non-empty `fix` field
- **THEN** the SARIF result includes `fixes[0].description.text` containing the fix suggestion
