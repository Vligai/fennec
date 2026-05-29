## Requirements

### Requirement: GitLab CI component definition
The system SHALL provide a GitLab CI component includable via `include: component:` syntax with the same inputs as the GitHub Actions action.

#### Scenario: Component included in pipeline
- **WHEN** a `.gitlab-ci.yml` includes the Fennec component
- **THEN** a `fennec-scan` job is added to the pipeline that runs on merge request events

### Requirement: MR comment posting
The system SHALL post a summary comment to the merge request using `CI_JOB_TOKEN` for authentication.

#### Scenario: MR comment posted
- **WHEN** the scan completes on a GitLab MR pipeline
- **THEN** a summary comment is posted to the MR using the same format as the GitHub PR comment

### Requirement: GitLab CI exit code mapping
The system SHALL use the same exit code semantics as the GitHub Actions integration.

#### Scenario: Advisory findings do not fail pipeline
- **WHEN** only advisory-mode findings are detected in a GitLab pipeline
- **THEN** the `fennec-scan` job exits with code 0

#### Scenario: Blocking findings fail pipeline
- **WHEN** a blocking finding is detected
- **THEN** the `fennec-scan` job exits with a non-zero code, failing the pipeline
