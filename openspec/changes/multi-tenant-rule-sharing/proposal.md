## Why

Orgs with multiple repos or teams need to share custom rules and sanitizer trust across boundaries without leaking internal implementation details. Without this, each repo independently rediscovers the same sanitizers — wasting dev review cycles and leaving FP rates high in newer repos that haven't accumulated verdicts yet.

## What Changes

- Define the org-level rule sharing model: org rules + repo overrides, with inheritance
- Define what can be shared vs. what stays private (pattern names but not internal function bodies)
- Implement org rule storage: rules scoped to an org ID, served to all repos in that org
- Implement the privacy boundary: sharing patterns without exposing call stacks or code content
- Define repo-level override precedence: repo rules can shadow org rules

## Non-goals

- Cross-org sharing (orgs are isolated)
- Rule marketplace (sharing between unrelated orgs)
- Role-based access control within an org (phase 2)

## Capabilities

### New Capabilities

- `org-rule-store`: Storage and serving of org-scoped custom rules
- `rule-inheritance`: Repo-level rules inherit and can override org-level rules
- `rule-privacy-boundary`: Pattern sharing without code content exposure

### Modified Capabilities

<!-- none — extends custom-rules-schema without changing its spec -->

## Impact

- Custom rule loader (from `custom-rules-schema`) must be extended to merge org-level + repo-level rules
- Signal store propagation job (from `signal-store-data-model`) already operates at org scope — rule sharing reuses that boundary
- Privacy boundary is critical: patterns are identifiers, not code; must not leak function bodies
