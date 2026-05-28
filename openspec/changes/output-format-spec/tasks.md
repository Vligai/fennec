## 1. Finding Model

- [x] 1.1 Define `Finding` dataclass in `fennec/output/model.py` with all fields from design
- [x] 1.2 Implement deterministic ID generation: `sha256(vuln_class + path_hash)[:16]`
- [x] 1.3 Implement finding deduplication in finding synthesizer: merge same-ID findings within a scan
- [x] 1.4 Write unit tests: same input → same ID; different vuln class → different ID; dedup merges correctly

## 2. SARIF Renderer

- [x] 2.1 Create `fennec/output/sarif.py` with `SarifRenderer.render(findings: List[Finding]) -> dict`
- [x] 2.2 Map severity: CRITICAL/HIGH → `error`, MEDIUM → `warning`, LOW → `note`
- [x] 2.3 Render taint path as `codeFlows[0].threadFlows[0].locations` array
- [x] 2.4 Include fix suggestion in `result.fixes[0].description.text`
- [x] 2.5 Write unit tests: output validates against SARIF 2.1.0 JSON schema; severity mapping correct

## 3. PR Comment Renderer

- [x] 3.1 Create `fennec/output/pr_comment.py` with `PrCommentRenderer.render(findings) -> str`
- [x] 3.2 Render severity table with per-severity counts
- [x] 3.3 Render collapsible details with up to 10 findings; truncation note for more
- [x] 3.4 Include `<!-- fennec-scan-result -->` HTML marker in output
- [x] 3.5 Implement no-findings variant: returns clean scan message
- [x] 3.6 Write unit tests: 0 findings, 5 findings, 15 findings (truncation)

## 4. Jira Webhook Output

- [x] 4.1 Create `fennec/output/jira.py` with `JiraWebhookSender.send_async(findings, config)`
- [x] 4.2 Implement severity threshold filter: skip findings below configured threshold
- [x] 4.3 Implement dedup check: search for existing ticket by `customfield_fennec_finding_id` before create
- [x] 4.4 Implement async delivery using `asyncio` — does not block scan result
- [x] 4.5 Log warning on non-2xx response; never raise exception or affect exit code
- [x] 4.6 Write unit tests: threshold filter; dedup search blocks duplicate POST; failure logs warning
