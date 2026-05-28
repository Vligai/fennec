## Why

Fennec's value is realized in CI — every PR gets scanned before merge. Without a working GitHub Actions and GitLab CI integration, the tool exists only as a CLI that security engineers run manually, which is not the steady-state use case. The incremental diff mode was designed specifically to be fast enough for CI.

## What Changes

- Define the GitHub Actions workflow template (reusable action)
- Define the GitLab CI component template
- Specify the CI authentication model (API token, scoped permissions)
- Specify CI exit codes: advisory vs. blocking findings map to exit 0 vs. non-zero
- Specify PR comment posting behavior (inline SARIF annotations + summary comment)
- Specify the scan trigger model: PR diff scan on `pull_request` event; full scan on `schedule`

## Non-goals

- Jenkins, CircleCI, or other CI systems (phase 2)
- Self-hosted action runner requirements (assume GitHub-hosted runners)
- Dashboard integration (covered by output-format-spec)

## Capabilities

### New Capabilities

- `github-actions-integration`: Reusable GitHub Action definition and workflow template
- `gitlab-ci-integration`: GitLab CI component definition and pipeline template
- `ci-auth-model`: Token-based authentication spec for CI environments

### Modified Capabilities

<!-- none — greenfield -->

## Impact

- CI integration consumes the scanner CLI and SARIF output; depends on `output-format-spec`
- Advisory vs. blocking mode (from `custom-rules-schema`) maps to CI exit codes
- PR comment posting requires repository write permissions via the CI token
