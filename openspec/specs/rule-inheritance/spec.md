## Requirements

### Requirement: Org and repo rule merge
The system SHALL merge org-level and repo-level rules at scan time, with repo rules taking precedence on conflict.

#### Scenario: Repo rule overrides org rule
- **WHEN** the org has a source rule for pattern `X` and the repo `custom_rules.yaml` has a different definition for pattern `X`
- **THEN** the repo definition is used and the org definition is ignored

#### Scenario: Non-conflicting rules combined
- **WHEN** the org has rules for patterns A and B, and the repo has rules for pattern C
- **THEN** the effective rule set contains all three patterns

### Requirement: Repo opt-out of inherited rule
The system SHALL support explicit disable of an inherited org rule in `custom_rules.yaml`.

#### Scenario: Repo disables org sanitizer
- **WHEN** `custom_rules.yaml` contains an override entry with `action: disable` for an org pattern
- **THEN** that pattern is NOT treated as a sanitizer in this repo, regardless of org-level trust

### Requirement: Effective rule audit
The system SHALL log the effective rule set (org rules + repo rules after merge) at scan startup in debug mode.

#### Scenario: Debug log shows effective rules
- **WHEN** `--debug` flag is set
- **THEN** the scan logs a list of all effective rules with their source (org or repo) at startup
