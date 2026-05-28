## Context

CI integration is a thin wrapper around the Fennec CLI. The action/component runs `fennec scan --diff` on PR events and posts results as PR comments and SARIF annotations. The design must handle both advisory (comment, no fail) and blocking (fail CI) modes per the custom rules configuration.

## Goals / Non-Goals

**Goals:**
- GitHub Actions: reusable action publishable to the GitHub Marketplace
- GitLab CI: component publishable to the GitLab CI Catalog
- Authentication: Fennec API token (for hosted) + repository token (for PR comments)
- Exit codes: 0 for advisory-only findings, non-zero for any blocking finding
- PR comment: summary comment + inline annotations on changed files

**Non-Goals:**
- Jenkins, CircleCI
- Self-hosted runner setup
- Caching scan results across PRs (phase 2)

## Decisions

**Decision 1: GitHub Actions reusable action structure**

```
.github/
  actions/
    fennec-scan/
      action.yml    ← reusable action definition
      entrypoint.sh ← runs fennec CLI, posts results
```

Inputs:
- `fennec-api-key` (required): Fennec API token (stored as secret)
- `scan-mode`: `diff` (default) | `full`
- `fail-on`: `blocking` (default) | `any` | `none`
- `sarif-upload`: `true` (default) — uploads SARIF to GitHub code scanning
- `post-comment`: `true` (default) — posts PR summary comment

**Decision 2: Exit code mapping**

| Findings | `fail-on: blocking` | `fail-on: any` | `fail-on: none` |
|---|---|---|---|
| No findings | 0 | 0 | 0 |
| Advisory only | 0 | 1 | 0 |
| Any blocking | 1 | 1 | 0 |

**Decision 3: PR comment format**

Posted as a single collapsible comment (updates existing comment on re-run):

```
## Fennec Security Scan — N findings

| Severity | Count |
|---|---|
| Critical | 1 |
| High | 2 |
| Medium | 3 |

<details><summary>Details</summary>
[inline finding summaries with file:line links]
</details>

[Powered by Fennec](https://fennec.dev)
```

**Decision 4: Authentication model**

Two tokens:
1. `FENNEC_API_KEY` — authenticates to Fennec's scan service (stored in repo secrets)
2. `GITHUB_TOKEN` — provided by Actions automatically; used for SARIF upload and PR comment

For GitLab: `FENNEC_API_KEY` stored as CI variable; `CI_JOB_TOKEN` for MR comments.

**Decision 5: Scan triggers**

```yaml
# GitHub Actions trigger
on:
  pull_request:
    types: [opened, synchronize]  # diff scan
  schedule:
    - cron: '0 2 * * 1'           # weekly full scan
```

## Cross-Component Interfaces

- **CI action → Fennec CLI**: invokes `fennec scan --diff --format sarif --output results.sarif`
- **CI action → GitHub API**: uploads SARIF via `github/codeql-action/upload-sarif`; posts PR comment via REST API
- **Fennec CLI → CI exit code**: maps finding severity + mode to exit code per Decision 2

## Risks / Trade-offs

- **Token exposure** → `FENNEC_API_KEY` in logs. Mitigation: mask the token in all log output; document in action README.
- **PR comment spam** → Creating a new comment on each run clutters PRs. Mitigation: update existing Fennec comment via comment ID stored in action state.
- **SARIF schema version** → GitHub requires SARIF 2.1.0. Must validate output before upload.

## Open Questions

- Should the action support a `baseline` mode (only report new findings vs. last scan)? (Useful but complex — defer to phase 2.)
- Should GitLab MR comments use the same format as GitHub PR comments? (Yes, same template.)
