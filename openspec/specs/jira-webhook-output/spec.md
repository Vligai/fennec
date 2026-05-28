## Requirements

### Requirement: Jira ticket creation via webhook
The system SHALL POST a Jira-compatible payload to the configured `JIRA_WEBHOOK_URL` for each finding that meets the severity threshold.

#### Scenario: High-severity finding creates ticket
- **WHEN** a finding with `Severity.HIGH` is produced and `JIRA_WEBHOOK_URL` is configured
- **THEN** a POST request is sent to the webhook URL with the finding summary, description, and labels

#### Scenario: Low-severity finding below threshold not sent
- **WHEN** a finding with `Severity.LOW` is produced and the threshold is `HIGH`
- **THEN** no Jira webhook POST is made for that finding

### Requirement: Deduplication via finding ID
The system SHALL not create a duplicate Jira ticket if a ticket with the same `customfield_fennec_finding_id` already exists.

#### Scenario: Duplicate finding not re-ticketed
- **WHEN** the same finding is detected in a second scan
- **THEN** no new Jira ticket is created; the existing ticket ID is logged

### Requirement: Async webhook delivery
The system SHALL send Jira webhook requests asynchronously after scan completion, not blocking the scan result output.

#### Scenario: Jira POST does not delay CI
- **WHEN** a scan completes and Jira posting is enabled
- **THEN** scan output (SARIF, PR comment, exit code) is available before any Jira POST is attempted

### Requirement: Jira webhook failure handling
The system SHALL log a warning (not fail the scan) when a Jira webhook POST returns a non-2xx status.

#### Scenario: Jira POST fails
- **WHEN** the Jira webhook returns 503
- **THEN** a warning is logged with the finding ID and HTTP status; the scan exits with its normal code
