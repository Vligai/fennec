## Requirements

### Requirement: YAML schema load and validation
The system SHALL load `custom_rules.yaml` and validate it against the defined schema, reporting descriptive errors for invalid fields.

#### Scenario: Valid rules file loaded
- **WHEN** a valid `custom_rules.yaml` is present at the configured path
- **THEN** the system loads it without error and makes rules available to the scanner

#### Scenario: Invalid pattern field
- **WHEN** a rule entry is missing the required `pattern` field
- **THEN** the system raises a `RuleValidationError` with the field name, rule index, and a description of the violation

#### Scenario: Missing rules file
- **WHEN** no `custom_rules.yaml` is present
- **THEN** the scanner proceeds with built-in rules only, without error

### Requirement: Source rule extension
The system SHALL merge custom sources with the built-in source taxonomy at scan time.

#### Scenario: Custom source used in taint path
- **WHEN** a custom source pattern matches a function in the codebase
- **THEN** that function is treated as a taint source during traversal, in addition to built-in sources

### Requirement: Sanitizer rule extension
The system SHALL merge custom sanitizers with the built-in sanitizer set and annotate matching graph nodes before traversal.

#### Scenario: Custom sanitizer suppresses finding
- **WHEN** a custom sanitizer pattern matches a function on a taint path
- **THEN** the taint path is marked `sanitized=true` and not surfaced as a finding

### Requirement: Scope filtering
The system SHALL apply a rule only to files matching its configured `scope.paths` glob patterns.

#### Scenario: Rule scoped to payments directory
- **WHEN** a rule has `scope.paths: ["src/payments/**"]` and a finding originates in `src/api/`
- **THEN** the rule is NOT applied to that finding

#### Scenario: Negation glob excludes test files
- **WHEN** a rule has `scope.paths: ["src/**", "!src/**/tests/**"]`
- **THEN** findings in test files are excluded from the rule's scope

### Requirement: Advisory vs. blocking mode
The system SHALL respect the `mode` field on each rule, treating `advisory` rules as comment-only and `blocking` rules as CI gate failures.

#### Scenario: Advisory rule does not fail CI
- **WHEN** a rule with `mode: advisory` fires
- **THEN** a comment is posted but the CI check exits with code 0

#### Scenario: Blocking rule fails CI
- **WHEN** a rule with `mode: blocking` fires
- **THEN** the CI check exits with a non-zero code
