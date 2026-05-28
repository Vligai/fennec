## ADDED Requirements

### Requirement: PR comment severity summary table
The system SHALL render a PR comment with a severity count table and a collapsible details section.

#### Scenario: Comment rendered with findings
- **WHEN** a scan produces 3 findings of mixed severity
- **THEN** the rendered comment includes a markdown table with per-severity counts

### Requirement: HTML marker for update-in-place
The system SHALL include an HTML marker comment in the PR comment to enable update-in-place detection.

#### Scenario: Existing comment detected
- **WHEN** a PR comment containing `<!-- fennec-scan-result -->` already exists
- **THEN** the renderer returns the comment ID for update rather than creating a new comment

### Requirement: Comment truncation at 10 findings
The system SHALL show at most 10 findings in the collapsible details section, with a note linking to the full SARIF for more.

#### Scenario: More than 10 findings truncated
- **WHEN** a scan produces 15 findings
- **THEN** the comment shows 10 finding details and the note "5 more findings — see SARIF report"

### Requirement: No-findings comment
The system SHALL post a brief "no findings" confirmation comment when a scan produces zero findings.

#### Scenario: Clean scan reported
- **WHEN** a scan produces no findings
- **THEN** the PR comment states "Fennec scan completed. No security findings detected."
