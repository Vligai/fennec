## 1. Setup

- [x] 1.1 Add `pydantic` and `pyyaml` to project dependencies
- [x] 1.2 Create `fennec/rules/` package with `__init__.py`, `schema.py`, `loader.py`, `suggest.py`, `dry_run.py`

## 2. YAML Schema and Loader

- [x] 2.1 Define pydantic models: `SourceRule`, `SinkRule`, `SanitizerRule`, `RuleScope`, `CustomRules`
- [x] 2.2 Implement `load_rules(path) -> CustomRules` — loads and validates YAML, raises `RuleValidationError` on failure
- [x] 2.3 Implement scope filtering: `rule.matches_file(file_path) -> bool` using glob patterns with negation support
- [x] 2.4 Implement mode handling: `rule.is_blocking() -> bool`
- [x] 2.5 Write unit tests: valid YAML loads, missing `pattern` raises error, missing file returns empty rules

## 3. Rule Integration with Scanner

- [x] 3.1 Merge custom sources into taint source set at scan startup
- [x] 3.2 Merge custom sinks into taint sink set at scan startup
- [x] 3.3 Annotate graph nodes with `is_sanitizer=true` for matching sanitizer patterns before traversal
- [x] 3.4 Apply scope filtering per finding: skip rules that don't match the finding's file path
- [x] 3.5 Apply mode: advisory findings don't fail CI exit code; blocking ones do

## 4. AI Suggest

- [x] 4.1 Implement `suggest_candidates(field, vuln_class, graph_client) -> List[Candidate]`
- [x] 4.2 Build graph-context prompt: sample function names/signatures from graph relevant to vuln_class
- [x] 4.3 Filter LLM output: discard any suggested pattern not matching a node in the graph
- [x] 4.4 Implement approval loop: present candidates with evidence (file:line), write approved ones to `custom_rules.yaml`
- [x] 4.5 Wire as CLI: `fennec rules suggest --field sanitizer --vuln-class cmdi`

## 5. Dry-Run and FP Estimation

- [x] 5.1 Implement `dry_run_scan(candidate_rules, repo_path) -> DryRunResult` — traversal-only, no LLM
- [x] 5.2 Compute suppressed count: findings suppressed by candidate vs. current rules
- [x] 5.3 Implement FP rate threshold warning: print warning if suppression > 10% of total findings
- [x] 5.4 Implement `fennec rules activate [--force]` — writes to `custom_rules.yaml`, adds `force_activated: true` if `--force` used
- [x] 5.5 Write integration test: candidate sanitizer suppressing >10% of fixture findings triggers warning
