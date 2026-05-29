## ADDED Requirements

### Requirement: API key authentication
The system SHALL authenticate to the Fennec scan service using a `FENNEC_API_KEY` environment variable in CI.

#### Scenario: Valid API key accepted
- **WHEN** `FENNEC_API_KEY` is set to a valid token
- **THEN** the scan runs without authentication errors

#### Scenario: Missing API key fails clearly
- **WHEN** `FENNEC_API_KEY` is not set
- **THEN** the scan exits with a clear error: "FENNEC_API_KEY is required. Set it as a repository secret."

### Requirement: Repository token scoping
The system SHALL use the CI-provided repository token (GITHUB_TOKEN or CI_JOB_TOKEN) only for PR/MR comment posting and SARIF upload, not for scan authentication.

#### Scenario: Minimal repository token permissions
- **WHEN** the action documents required permissions
- **THEN** required permissions are: `pull-requests: write` and `security-events: write` only
