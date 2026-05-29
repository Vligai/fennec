## ADDED Requirements

### Requirement: Org rule fetch
The system SHALL fetch org-scoped rules from the Fennec API at scan startup using the configured org ID and API key.

#### Scenario: Org rules fetched successfully
- **WHEN** the scan starts and `FENNEC_ORG_ID` is configured
- **THEN** org rules are fetched from `GET /api/v1/org/{org_id}/rules` and available for merge

#### Scenario: API unavailable falls back to cache
- **WHEN** the org rule API returns a network error
- **THEN** the last cached rules (up to 5 minutes old) are used and a warning is logged

#### Scenario: No org ID configured
- **WHEN** `FENNEC_ORG_ID` is not set
- **THEN** no org rules are fetched and the scan proceeds with repo rules only

### Requirement: Org rule local cache
The system SHALL cache fetched org rules locally with a 5-minute TTL to avoid per-scan API calls in CI.

#### Scenario: Cache used within TTL
- **WHEN** org rules were fetched less than 5 minutes ago
- **THEN** the cached rules are used without an API call

#### Scenario: Cache expired
- **WHEN** the cached rules are older than 5 minutes
- **THEN** a fresh fetch is performed

### Requirement: Admin-only org rule publication
The system SHALL reject org rule publication requests from non-admin users.

#### Scenario: Admin publishes rule
- **WHEN** an org admin publishes a pattern via `fennec rules publish --org`
- **THEN** the rule is stored at org scope and returned in future API responses for that org

#### Scenario: Non-admin blocked
- **WHEN** a non-admin user attempts to publish to org scope
- **THEN** the API returns 403 and the rule is not stored
