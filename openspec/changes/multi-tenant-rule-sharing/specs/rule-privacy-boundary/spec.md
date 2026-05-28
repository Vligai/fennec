## ADDED Requirements

### Requirement: Pattern-only sharing
The system SHALL share only pattern strings, taint types, scope globs, and modes in org rules — never source code, file paths, taint paths, or stack traces.

#### Scenario: Org rule API response contains no code
- **WHEN** the org rule API responds with the org rule list
- **THEN** no field in the response contains source code content, full file paths, or taint path details

### Requirement: AI suggest does not auto-publish
The system SHALL require explicit human approval and admin action before an AI suggest candidate reaches org scope. AI suggest operates only at repo scope.

#### Scenario: AI suggested pattern stays at repo scope
- **WHEN** a user approves an AI suggest candidate in `custom_rules.yaml`
- **THEN** the rule is written to the local repo file only, not automatically published to org scope

#### Scenario: Org publish requires separate explicit action
- **WHEN** an admin wants to promote a repo rule to org scope
- **THEN** they must explicitly run `fennec rules publish --org --pattern "<pattern>"` (or equivalent web UI action)
