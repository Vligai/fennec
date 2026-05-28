## Why

Generic source/sink taxonomies cover ~80% of common vulnerabilities. The remaining 20% — internal RPCs, proprietary ORMs, custom sanitizers — require org-specific rules. Without a good authoring UX, security teams either skip custom rules (accepting 20% miss rate) or write them incorrectly (spiking FP rate). Sanitizers are the highest-leverage field: every correctly defined sanitizer reduces false positives directly.

## What Changes

- Define the `custom_rules.yaml` schema (sources, sinks, sanitizers, scope)
- Implement YAML loading and validation
- Implement "AI suggest" per field — scans the codebase and proposes candidates for human review
- Implement dry-run mode with live FP rate estimate before a rule is activated
- Add scope controls: path glob, branch targeting, advisory vs. blocking mode
- Surface a warning when estimated FP rate exceeds 10%

## Non-goals

- Rule versioning or rollback (store in git)
- Multi-tenant rule sharing (separate change)
- Rule analytics dashboard (phase 2)

## Capabilities

### New Capabilities

- `custom-rules-schema`: YAML schema definition, loader, and validator
- `rule-ai-suggest`: AI-powered candidate suggestion per source/sink/sanitizer field
- `rule-dry-run`: Dry-run mode with FP rate estimation before rule activation

### Modified Capabilities

<!-- none — greenfield -->

## Impact

- Custom rules augment the built-in taint taxonomy at scan time
- Sanitizer rules directly reduce FP rate — must be merged into graph annotations before traversal
- AI suggest requires read access to the codebase at rule authoring time
