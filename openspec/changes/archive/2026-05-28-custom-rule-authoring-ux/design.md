## Context

Custom rules extend the built-in taint taxonomy. The schema from the README is already defined (`custom_rules.yaml` with sources, sinks, sanitizers). This change specifies how rules are loaded, validated, suggested, and tested before activation. The key UX insight: sanitizers are the most valuable field and also the hardest to author correctly — AI suggest targets this pain point first.

## Goals / Non-Goals

**Goals:**
- Define and validate the YAML schema
- AI suggest: scan repo, propose patterns, require human approval before activation
- Dry-run: apply candidate rules against HEAD, estimate FP rate delta
- Scope controls: path globs, branch targeting, advisory vs. blocking mode

**Non-Goals:**
- GUI (CLI and YAML file are the authoring surface for v1)
- Rule versioning / rollback (managed via git)
- Cross-org sharing

## Decisions

**Decision 1: YAML schema with pydantic validation**

`custom_rules.yaml` is loaded and validated via pydantic models. Invalid rules raise descriptive errors at load time, not at scan time.

```yaml
sources:
  - pattern: "self.rpc_handler.get_payload()"
    type: user_input
    scope:
      paths: ["src/api/**"]

sinks:
  - pattern: "InternalORM.raw_execute()"
    type: sqli

sanitizers:
  - pattern: "internal_security.sanitize_cmd()"
    covers: cmdi

rules:
  - name: "block-raw-sql"
    mode: blocking        # advisory | blocking
    branches: ["main"]
```

**Decision 2: AI suggest implementation**

AI suggest is a constrained LLM call with codebase context:
- For sanitizers: "Given this codebase, which functions act as sanitizers for [vuln_class]? List function signatures."
- The LLM scans a sampled set of function nodes from the graph (not raw code) to propose candidates
- Output: ranked list of candidate patterns with confidence score
- Human must approve each candidate before it's written to `custom_rules.yaml`

**Decision 3: Dry-run FP estimation**

Dry-run mode:
1. Load candidate rule alongside existing rules
2. Run a simulated scan against HEAD (without LLM calls — graph traversal only)
3. Count paths that would be suppressed by the new sanitizer vs. current findings
4. Estimate FP rate delta: `Δ = (suppressed_previously_flagged / total_previously_flagged)`
5. If estimated FP rate after rule > 10%: display warning, require `--force` to activate

**Decision 4: Scope controls**

```yaml
scope:
  paths: ["src/payments/**", "!src/payments/tests/**"]  # glob with negation
  branches: ["main", "release/*"]                        # branch patterns
  mode: advisory   # advisory = comment only; blocking = fail CI check
```

Rules without scope apply to all paths and branches in advisory mode by default.

## Cross-Component Interfaces

- **Custom rule loader → Taint tracker**: `CustomRules` object passed to scanner at startup; sanitizer patterns merged into graph annotations
- **AI suggest → Graph client**: reads function node names/signatures to build candidate list
- **Dry-run → Scanner**: runs traversal-only scan (no LLM) with candidate rules injected

## Risks / Trade-offs

- **Over-broad sanitizer rules** → A pattern like `str()` as a sanitizer would suppress nearly everything. Mitigation: dry-run FP warning at 10% threshold; require explicit `--force` to bypass.
- **AI suggest hallucination** → LLM may propose non-existent functions. Mitigation: validate each suggested pattern against graph node names before presenting to the user.
- **YAML schema evolution** → Adding fields is backwards compatible; removing fields requires version flag. Document schema version in the YAML header.

## Open Questions

- Should dry-run run against a full repo scan or just the last PR diff? (Lean toward last PR diff — faster and more representative of steady-state impact.)
- Should AI suggest be run per-field or per-session? (Per-field — more focused context, better suggestions.)
