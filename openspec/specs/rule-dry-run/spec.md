## Requirements

### Requirement: Dry-run scan with candidate rules
The system SHALL run a traversal-only scan (no LLM calls) against HEAD with candidate rules injected, without modifying `custom_rules.yaml`.

#### Scenario: Dry-run produces FP estimate
- **WHEN** the user runs `fennec rules dry-run --rule-file candidate_rules.yaml`
- **THEN** the system reports how many currently-flagged findings would be suppressed by the candidate rules

#### Scenario: Dry-run does not persist rules
- **WHEN** the dry-run completes
- **THEN** `custom_rules.yaml` is unchanged

### Requirement: FP rate warning at 10% threshold
The system SHALL display a warning when the estimated FP rate after applying a candidate rule exceeds 10% of total findings.

#### Scenario: High-FP rule warned
- **WHEN** a candidate sanitizer would suppress more than 10% of current findings
- **THEN** the dry-run output displays a prominently formatted warning: "WARNING: Estimated FP rate {N}% exceeds threshold (10%)"

#### Scenario: Safe rule confirmed
- **WHEN** a candidate sanitizer suppresses fewer than 10% of current findings
- **THEN** the dry-run output indicates the rule appears safe to activate

### Requirement: Force flag to bypass threshold
The system SHALL allow the user to activate a rule that exceeds the FP threshold with an explicit `--force` flag.

#### Scenario: Force flag bypasses warning
- **WHEN** the user runs `fennec rules activate --force` for a rule exceeding the threshold
- **THEN** the rule is written to `custom_rules.yaml` with a `force_activated: true` annotation
