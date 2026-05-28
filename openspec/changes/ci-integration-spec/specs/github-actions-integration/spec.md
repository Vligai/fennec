## ADDED Requirements

### Requirement: Reusable action definition
The system SHALL provide a reusable GitHub Actions action with documented inputs and outputs.

#### Scenario: Action invoked with minimal config
- **WHEN** a workflow calls the action with only `fennec-api-key` provided
- **THEN** the action runs a diff scan, posts a PR comment, and uploads SARIF with default settings

#### Scenario: Scan mode override
- **WHEN** `scan-mode: full` is specified
- **THEN** the action runs a full-repo scan instead of a diff scan

### Requirement: Exit code mapping
The system SHALL exit with code 0 when no blocking findings exist and non-zero when blocking findings are present (with `fail-on: blocking`).

#### Scenario: Advisory findings do not fail CI
- **WHEN** only advisory-mode findings are detected
- **THEN** the action exits with code 0

#### Scenario: Blocking finding fails CI
- **WHEN** at least one blocking-mode finding is detected
- **THEN** the action exits with code 1

### Requirement: PR comment posting
The system SHALL post a summary comment to the pull request and update (not duplicate) it on re-runs.

#### Scenario: First run posts comment
- **WHEN** the action runs for the first time on a PR
- **THEN** a Fennec summary comment is posted with finding counts by severity

#### Scenario: Re-run updates existing comment
- **WHEN** the action runs again on the same PR
- **THEN** the existing Fennec comment is updated in place rather than a new comment created

### Requirement: SARIF upload
The system SHALL upload the scan results as SARIF 2.1.0 to GitHub Code Scanning when `sarif-upload: true`.

#### Scenario: SARIF uploaded successfully
- **WHEN** the scan completes and `sarif-upload` is enabled
- **THEN** the SARIF file is uploaded via `github/codeql-action/upload-sarif` without error

### Requirement: Token masking
The system SHALL mask `FENNEC_API_KEY` in all action log output.

#### Scenario: API key not visible in logs
- **WHEN** the action runs and logs any output
- **THEN** the `FENNEC_API_KEY` value does not appear in plain text in the logs
