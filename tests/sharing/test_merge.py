"""Task 3.5: Rule merge/inheritance tests — repo override wins, disable removes, non-conflicting combined."""

from fennec.rules.loader import merge_org_and_repo_rules
from fennec.rules.schema import CustomRules, RuleOverride, SanitizerRule, SourceRule
from fennec.sharing.client import OrgRule


def _org_rule(pattern: str, rule_type: str = "sanitizer", taint_type: str = "cmdi") -> OrgRule:
    return OrgRule(
        rule_id="r1", org_id="org-1",
        type=rule_type, pattern=pattern, taint_type=taint_type,
    )


# --- Repo rule overrides org rule on same pattern ---

def test_repo_rule_overrides_org_rule():
    org = [_org_rule("shlex.quote()", "sanitizer", "cmdi")]
    repo = CustomRules()
    repo.sanitizers.append(SanitizerRule(pattern="shlex.quote()", covers="sqli"))  # different covers

    merged = merge_org_and_repo_rules(org, repo)

    san_patterns = [s for s in merged.sanitizers if s.pattern == "shlex.quote()"]
    assert len(san_patterns) == 1
    assert san_patterns[0].covers == "sqli"  # repo wins


# --- Non-conflicting rules from both levels combined ---

def test_non_conflicting_rules_combined():
    org = [_org_rule("org_sanitize()", "sanitizer", "cmdi")]
    repo = CustomRules()
    repo.sanitizers.append(SanitizerRule(pattern="repo_sanitize()", covers="sqli"))

    merged = merge_org_and_repo_rules(org, repo)

    patterns = {s.pattern for s in merged.sanitizers}
    assert "org_sanitize()" in patterns
    assert "repo_sanitize()" in patterns


# --- disable override removes org rule ---

def test_disable_removes_org_rule():
    org = [_org_rule("dangerous_fn()", "sanitizer", "cmdi")]
    repo = CustomRules()
    repo.overrides.append(RuleOverride(pattern="dangerous_fn()", action="disable"))

    merged = merge_org_and_repo_rules(org, repo)

    patterns = {s.pattern for s in merged.sanitizers}
    assert "dangerous_fn()" not in patterns


# --- Source and sink org rules also merged ---

def test_org_source_rule_merged():
    org = [_org_rule("custom_input()", "source", "user_input")]
    repo = CustomRules()

    merged = merge_org_and_repo_rules(org, repo)

    patterns = {s.pattern for s in merged.sources}
    assert "custom_input()" in patterns


def test_org_sink_rule_merged():
    org = [_org_rule("raw_exec()", "sink", "cmdi")]
    repo = CustomRules()

    merged = merge_org_and_repo_rules(org, repo)

    patterns = {s.pattern for s in merged.sinks}
    assert "raw_exec()" in patterns


# --- Empty org rules → just repo rules ---

def test_empty_org_rules_returns_repo_rules():
    repo = CustomRules()
    repo.sanitizers.append(SanitizerRule(pattern="repo_only()", covers="sqli"))

    merged = merge_org_and_repo_rules([], repo)

    assert len(merged.sanitizers) == 1
    assert merged.sanitizers[0].pattern == "repo_only()"


# --- Debug mode logging (smoke test: no exception) ---

def test_debug_mode_does_not_raise(caplog):
    import logging
    org = [_org_rule("logged_fn()", "sanitizer")]
    repo = CustomRules()

    with caplog.at_level(logging.DEBUG, logger="fennec.rules.loader"):
        merge_org_and_repo_rules(org, repo, debug=True)
