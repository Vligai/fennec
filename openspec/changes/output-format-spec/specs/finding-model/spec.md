## ADDED Requirements

### Requirement: Deterministic finding ID
The system SHALL generate a deterministic `Finding.id` from `(vuln_class, path_hash)` so the same finding produces the same ID across runs.

#### Scenario: Same finding same ID
- **WHEN** the same taint path is found in two consecutive scans
- **THEN** both `Finding.id` values are identical

#### Scenario: Different vuln class different ID
- **WHEN** the same taint path is analyzed for both SQLi and CMDi
- **THEN** the two findings have different IDs

### Requirement: Finding deduplication
The system SHALL deduplicate findings within a single scan: multiple taint paths to the same source/sink with the same vuln class produce one finding.

#### Scenario: Duplicate paths merged
- **WHEN** two different taint paths both connect source A to sink B as SQLi
- **THEN** a single finding is produced (not two separate findings)

### Requirement: Severity mapping from LLM verdict
The system SHALL map `LLMVerdict.severity` to `Finding.severity` directly.

#### Scenario: Critical severity mapped
- **WHEN** `LLMVerdict.severity = "critical"`
- **THEN** `Finding.severity = Severity.CRITICAL`
