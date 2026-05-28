## 1. Setup

- [ ] 1.1 Add `pydantic` and `pyyaml` to project dependencies
- [ ] 1.2 Create `fennec/rules/` package with `__init__.py`, `schema.py`, `loader.py`, `suggest.py`, `dry_run.py`

## 2. YAML Schema and Loader

- [ ] 2.1 Define pydantic models: `SourceRule`, `SinkRule`, `SanitizerRule`, `RuleScope`, `CustomRules`
- [ ] 2.2 Implement `load_rules(path) -> CustomRules` — loads and validates YAML, raises `RuleValidationError` on failure
- [ ] 2.3 Implement scope filtering: `rule.matches_file(file_path) -> bool` using glob patterns with negation support
- [ ] 2.4 Implement mode handling: `rule.is_blocking() -> bool`
- [ ] 2.5 Write unit tests: valid YAML loads, missing `pattern` raises error, missing file returns empty rules

## 3. Rule Integration with Scanner

- [ ] 3.1 Merge custom sources into taint source set at scan startup
- [ ] 3.2 Merge custom sinks into taint sink set at scan startup
- [ ] 3.3 Annotate graph nodes with `is_sanitizer=true` for matching sanitizer patterns before traversal
- [ ] 3.4 Apply scope filtering per finding: skip rules that don't match the finding's file path
- [ ] 3.5 Apply mode: advisory findings don't fail CI exit code; blocking ones do

## 4. AI Suggest

- [ ] 4.1 Implement `suggest_candidates(field, vuln_class, graph_client) -> List[Candidate]`
- [ ] 4.2 Build graph-context prompt: sample function names/signatures from graph relevant to vuln_class
- [ ] 4.3 Filter LLM output: discard any suggested pattern not matching a node in the graph
- [ ] 4.4 Implement approval loop: present candidates with evidence (file:line), write approved ones to `custom_rules.yaml`
- [ ] 4.5 Wire as CLI: `fennec rules suggest --field sanitizer --vuln-class cmdi`

## 5. Dry-Run and FP Estimation

- [ ] 5.1 Implement `dry_run_scan(candidate_rules, repo_path) -> DryRunResult` — traversal-only, no LLM
- [ ] 5.2 Compute suppressed count: findings suppressed by candidate vs. current rules
- [ ] 5.3 Implement FP rate threshold warning: print warning if suppression > 10% of total findings
- [ ] 5.4 Implement `fennec rules activate [--force]` — writes to `custom_rules.yaml`, adds `force_activated: true` if `--force` used
- [ ] 5.5 Write integration test: candidate sanitizer suppressing >10% of fixture findings triggers warning
