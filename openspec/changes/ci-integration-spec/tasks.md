## 1. GitHub Actions Action

- [ ] 1.1 Create `action.yml` with inputs: `fennec-api-key`, `scan-mode`, `fail-on`, `sarif-upload`, `post-comment`
- [ ] 1.2 Write `entrypoint.sh`: install Fennec CLI, run scan, capture exit code and SARIF output
- [ ] 1.3 Implement exit code mapping logic per `fail-on` input value
- [ ] 1.4 Mask `FENNEC_API_KEY` using `::add-mask::` before any logging
- [ ] 1.5 Implement SARIF upload step using `github/codeql-action/upload-sarif@v3`

## 2. PR Comment Posting

- [ ] 2.1 Implement `post_pr_comment(findings, github_token, repo, pr_number)` using GitHub REST API
- [ ] 2.2 Implement comment update: search for existing Fennec comment by marker string, update if found
- [ ] 2.3 Write PR comment template with severity table and collapsible details section
- [ ] 2.4 Write unit tests: new comment created when none exists; existing comment updated on re-run

## 3. GitLab CI Component

- [ ] 3.1 Create `fennec.gitlab-ci.yml` component template with matching inputs to GitHub action
- [ ] 3.2 Implement MR comment posting using GitLab MR Notes API with `CI_JOB_TOKEN`
- [ ] 3.3 Use same PR comment format as GitHub integration

## 4. Scanner CLI CI Mode

- [ ] 4.1 Implement `fennec scan --diff` CLI command: detects changed files from `GIT_BASE_SHA` env var, runs incremental scan
- [ ] 4.2 Implement `fennec scan --full` CLI command: full-repo scan mode
- [ ] 4.3 Implement `--format sarif` output flag writing SARIF 2.1.0 to `--output <path>`
- [ ] 4.4 Map exit code based on finding severity + `--fail-on` flag

## 5. Integration Tests

- [ ] 5.1 Write end-to-end test: fixture repo with a known SQLi → action runs → non-zero exit
- [ ] 5.2 Write test: advisory-only findings → action exits 0
- [ ] 5.3 Write test: SARIF output is valid SARIF 2.1.0 (validate against JSON schema)
