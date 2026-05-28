## Requirements

### Requirement: Sanitizer trust score computation
The system SHALL compute a trust score for each `pattern_fingerprint` by counting `false_positive` verdicts where that pattern appeared and dividing by total non-`wont_fix` verdicts for that pattern.

#### Scenario: Trust score computed from verdicts
- **WHEN** a pattern has 4 `false_positive` verdicts and 1 `real_vuln` verdict
- **THEN** the computed trust score is `0.8` (4 / 5)

#### Scenario: Trust score excludes wont_fix
- **WHEN** a pattern has 3 `false_positive`, 1 `real_vuln`, and 5 `wont_fix` verdicts
- **THEN** the trust score is computed as `0.75` (3 / 4), ignoring the 5 `wont_fix` entries

### Requirement: Cross-service propagation
The system SHALL propagate sanitizer trust to all services in the same org when a pattern reaches the trust threshold.

#### Scenario: Trust propagated to new service
- **WHEN** a sanitizer pattern reaches trust threshold (default: 3 false_positive verdicts across ≥ 2 services)
- **THEN** `sanitizer_trust` is upserted for that pattern at org scope, not just per-service

#### Scenario: Single-service pattern not propagated
- **WHEN** all verdicts for a pattern come from a single service
- **THEN** trust is stored at service scope only, not propagated org-wide

### Requirement: Trust score read at scan time
The system SHALL expose sanitizer trust scores so the scan engine can pre-annotate function nodes before traversal begins.

#### Scenario: High-trust pattern pre-annotated
- **WHEN** a function matches a pattern with `trust_score >= 0.8`
- **THEN** the function node is annotated with `is_sanitizer=true` for the relevant `taint_type`

#### Scenario: Low-trust pattern not annotated
- **WHEN** a function matches a pattern with `trust_score < 0.8`
- **THEN** the function node is NOT annotated as a sanitizer (LLM reasons about it instead)

### Requirement: Async propagation job
The system SHALL run trust score recomputation as an async batch job, not synchronously on each verdict write.

#### Scenario: Propagation job runs on schedule
- **WHEN** the propagation job is triggered
- **THEN** all `sanitizer_trust` rows are recomputed from current `verdicts` data
- **THEN** the job completes without blocking the scan engine
