## Why

Findings are worthless if they can't reach the people who need to act on them. The three required output destinations are: IDEs and CI platforms (SARIF), pull request reviews (PR comment), and ticketing systems (Jira webhook). Each has a distinct consumer with different formatting requirements.

## What Changes

- Specify the SARIF 2.1.0 output schema mapping (Fennec finding → SARIF result)
- Specify the PR comment template (GitHub and GitLab)
- Specify the Jira webhook payload format and trigger conditions
- Implement the finding-to-output renderer for each format
- Define the internal `Finding` model that all renderers consume

## Non-goals

- Dashboard / web UI (phase 2)
- Slack notifications (phase 2)
- Linear or other ticket systems (Jira only for v1)

## Capabilities

### New Capabilities

- `finding-model`: Internal `Finding` dataclass — canonical representation consumed by all renderers
- `sarif-output`: SARIF 2.1.0 renderer mapping Fennec findings to SARIF results
- `pr-comment-output`: PR comment renderer for GitHub and GitLab
- `jira-webhook-output`: Jira webhook payload builder and delivery

### Modified Capabilities

<!-- none — greenfield -->

## Impact

- All output paths read from the `Finding` model — finding synthesizer writes to it, all renderers read from it
- SARIF renderer is consumed by the CI integration (`ci-integration-spec`)
- PR comment renderer is also consumed by CI integration
