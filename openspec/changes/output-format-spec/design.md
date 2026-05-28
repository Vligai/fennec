## Context

Three output formats, one internal model. The `Finding` model is the serialization boundary — all upstream components write to it, all renderers read from it. This design keeps renderers dumb (pure transformation) and the finding model rich enough to feed all three.

## Goals / Non-Goals

**Goals:**
- Define `Finding` dataclass with all fields needed by all three renderers
- SARIF 2.1.0 with correct rule definitions and location mappings
- PR comment: severity table + collapsible details, update-in-place on re-run
- Jira: webhook POST with configurable field mapping; trigger on critical/high by default

**Non-Goals:**
- Slack, Linear, other integrations
- Dashboard
- Finding retention / persistence (findings are ephemeral per scan; signal store handles verdicts)

## Decisions

**Decision 1: Finding model**

```python
@dataclass
class Finding:
    id: str                      # deterministic: hash(vuln_class + path_hash)
    vuln_class: str              # 'sqli' | 'cmdi' | 'xss' | 'ssrf' | 'deser' | 'path_traversal'
    severity: Severity           # CRITICAL | HIGH | MEDIUM | LOW | FALSE_POSITIVE
    confidence: float            # 0.0–1.0 from LLM verdict
    taint_path: TaintPath        # source, intermediaries, sink
    sanitized: bool
    fix: str                     # one-sentence fix from LLM
    mode: RuleMode               # ADVISORY | BLOCKING
    repo_id: str
    service_id: str
    scan_id: str
    created_at: datetime
```

**Decision 2: SARIF 2.1.0 mapping**

| Fennec field | SARIF field |
|---|---|
| `Finding.id` | `result.ruleId` |
| `Finding.vuln_class` | `run.tool.driver.rules[].id` |
| `Finding.severity` | `result.level` (error=critical/high, warning=medium, note=low) |
| `Finding.taint_path.source` | `result.locations[0].physicalLocation` |
| `Finding.taint_path` all hops | `result.codeFlows[0].threadFlows[0].locations` |
| `Finding.fix` | `result.fixes[0].description.text` |

`run.tool.driver.name = "Fennec"`, `version` from package version.

**Decision 3: PR comment template**

Single comment per PR, identified by HTML marker comment. Updated (not recreated) on re-run.

```html
<!-- fennec-scan-result -->
## Fennec Security Scan — N findings

| Severity | Count |
|---|---|
| 🔴 Critical | N |
| 🟠 High | N |
| 🟡 Medium | N |
| 🔵 Low | N |

<details><summary>Show findings</summary>

### [vuln_class] in `file.py:line`
**Taint path:** `source` → `...` → `sink`
**Fix:** one-sentence suggestion

</details>
```

**Decision 4: Jira webhook**

POST to configured `JIRA_WEBHOOK_URL` on each scan. Payload:

```json
{
  "summary": "[Fennec] SQLi in payments/checkout.py:42",
  "description": "...",
  "priority": "Critical",
  "labels": ["security", "fennec", "sqli"],
  "customfield_fennec_finding_id": "<id>",
  "customfield_fennec_taint_path": "<serialized path>"
}
```

Trigger threshold configurable (default: severity >= HIGH). Deduplication: don't re-create ticket if `finding_id` already exists in Jira (check via search before create).

## Cross-Component Interfaces

- **Finding synthesizer → Finding model**: writes `Finding` objects
- **SARIF renderer → CI integration**: writes `results.sarif` file consumed by action
- **PR comment renderer → CI integration**: returns comment markdown string
- **Jira renderer → External Jira API**: HTTP POST on finding creation

## Risks / Trade-offs

- **SARIF schema compliance** → GitHub rejects invalid SARIF silently. Mitigation: validate output against SARIF JSON schema in tests.
- **Jira dedup cost** → Search-before-create adds latency. Mitigation: run Jira posting asynchronously after scan completes.
- **PR comment size limits** → GitHub truncates comments >65,536 chars. Mitigation: limit collapsible details to top 10 findings; link to full SARIF for more.
