## Context

Multiple repos within an org can share rules. The sharing model must not leak code: only pattern strings (function names/signatures) are shared, never source code, stack traces, or taint paths. Repo-level rules take precedence over org-level rules, enabling repos to opt out or refine inherited rules.

## Goals / Non-Goals

**Goals:**
- Org-scoped rule storage (hosted service stores rules per org ID)
- Rule merge at scan time: `effective_rules = org_rules UNION repo_rules` (repo overrides on conflict)
- Privacy: patterns shared, code never shared
- Admin-managed org rules: only designated org admins can publish to org scope

**Non-Goals:**
- Cross-org sharing
- RBAC beyond admin/non-admin
- Rule versioning at org scope (managed via API, not git, for shared rules)

## Decisions

**Decision 1: Org rule storage model**

Org rules stored in the Fennec hosted service DB (not in repo files):
- Table: `org_rules(org_id, rule_id, type, pattern, taint_type, scope_glob, mode, created_by, created_at)`
- Served via authenticated API: `GET /api/v1/org/{org_id}/rules` returns JSON rule list

Repo rules remain in `custom_rules.yaml` in the repository.

**Decision 2: Rule merge precedence**

At scan startup:
1. Fetch org rules from API (cached locally with 5-minute TTL)
2. Load repo `custom_rules.yaml`
3. Merge: for same `pattern`, repo rule wins over org rule
4. For sanitizers specifically: if repo rule marks a pattern as NOT a sanitizer (explicit deny), it overrides org trust

**Decision 3: Privacy boundary**

Shared data: `pattern` (function name/signature string), `taint_type`, `scope_glob`, `mode`  
Never shared: code content, file paths beyond glob, taint paths, stack traces, verdicts

Org rule patterns are not derived from code analysis — they are manually authored or approved by a human admin. This prevents automated leakage of internal function names from one repo to another (even within the same org) via AI suggest.

**Decision 4: Admin model**

Org admin is a boolean flag on the Fennec user record. Only org admins can:
- Publish a pattern to org scope
- Unpublish / disable an org rule

Non-admins can see org rules at scan time (via API) but cannot modify them.

**Decision 5: Repo opt-out**

A repo can suppress an inherited org rule by adding an explicit entry in `custom_rules.yaml`:

```yaml
overrides:
  - pattern: "internal_security.sanitize_cmd()"
    action: disable   # disables the inherited org rule for this repo
```

## Cross-Component Interfaces

- **Org rule API → Rule loader**: loader fetches org rules via authenticated GET before merging with local YAML
- **Rule loader merge logic**: extends `custom-rules-schema` loader; same `CustomRules` output type
- **Signal store propagation → Org rule API**: does NOT write to org rules automatically; propagation updates `sanitizer_trust` only; org rule publishing is always human-initiated

## Risks / Trade-offs

- **API availability in CI** → If org rule API is down, scan must fall back to repo rules only with a warning (not fail). Mitigation: local cache with TTL.
- **Pattern namespace collisions** → Two different internal functions in two repos have the same name. Mitigation: scope_glob limits where a pattern applies; patterns without scope are org-wide only.
- **Admin scope creep** → Over time, org rule list grows and no one removes stale rules. Mitigation: show rule age and last-match count in admin dashboard (phase 2).

## Open Questions

- Should org rules be publishable from the CLI (`fennec rules publish --org`) or only from the web UI? (Support both — CLI for security engineers, web for non-technical security leads.)
- Should there be a TTL on org rule API cache? What if a rule is revoked mid-scan? (5-minute TTL is acceptable; revocation takes effect on next scan.)
