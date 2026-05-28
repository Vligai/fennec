"""Task 5.5: dry_run_scan integration tests — FP rate threshold warning."""

import pytest
from fennec.graph.queries import TaintPath
from fennec.llm.response import Severity
from fennec.output.model import Finding, RuleMode, generate_finding_id
from fennec.rules.dry_run import dry_run_scan
from fennec.rules.schema import CustomRules, SanitizerRule
from datetime import datetime, timezone


def _make_finding(path_hash: str, node_names: list[str]) -> Finding:
    nodes = [{"id": f"fn:{n}", "name": n, "file_path": "f.py", "line_start": 1}
             for n in node_names]
    tp = TaintPath(nodes=nodes, edges=[], sanitized=False, hop_count=len(nodes) - 1)
    return Finding(
        id=generate_finding_id("sqli", path_hash),
        vuln_class="sqli",
        severity=Severity.HIGH,
        confidence=0.9,
        taint_path=tp,
        sanitized=False,
        fix="Use parameterized queries.",
        mode=RuleMode.BLOCKING,
        repo_id="repo-1",
        service_id="svc-a",
        scan_id="scan-001",
        created_at=datetime.now(timezone.utc),
    )


def _rules_with_sanitizer(pattern: str, covers: str = "sqli") -> CustomRules:
    rules = CustomRules()
    rules.sanitizers.append(SanitizerRule(pattern=pattern, covers=covers))
    return rules


# --- Suppression counting ---

def test_no_findings_zero_rate():
    rules = _rules_with_sanitizer("sanitize()")
    result = dry_run_scan(rules, [], threshold=0.10)
    assert result.total_findings == 0
    assert result.suppressed_by_candidate == 0
    assert result.suppression_rate == 0.0
    assert not result.exceeded_threshold


def test_candidate_matches_path_node_suppresses_finding():
    findings = [_make_finding("h1", ["get_input", "sanitize", "execute_query"])]
    rules = _rules_with_sanitizer("sanitize()")
    result = dry_run_scan(rules, findings)
    assert result.suppressed_by_candidate == 1


def test_candidate_not_in_path_no_suppression():
    findings = [_make_finding("h1", ["get_input", "execute_query"])]
    rules = _rules_with_sanitizer("sanitize()")  # not on this path
    result = dry_run_scan(rules, findings)
    assert result.suppressed_by_candidate == 0


# --- FP threshold warning ---

def test_above_10_percent_exceeded(tmp_path):
    """Candidate sanitizer suppressing >10% of findings triggers warning."""
    # 11 findings; sanitizer matches 2 → 18.2% > 10% threshold
    findings = [_make_finding(f"h{i}", ["get_input", "execute_query"]) for i in range(9)]
    findings += [
        _make_finding("h9",  ["get_input", "sanitize", "execute_query"]),
        _make_finding("h10", ["get_input", "sanitize", "execute_query"]),
    ]
    rules = _rules_with_sanitizer("sanitize()")

    result = dry_run_scan(rules, findings, threshold=0.10)

    assert result.total_findings == 11
    assert result.suppressed_by_candidate == 2
    assert result.suppression_rate == pytest.approx(2 / 11)
    assert result.exceeded_threshold is True
    assert any("WARNING" in w for w in result.warnings)


def test_below_10_percent_safe():
    """Candidate suppressing <10% findings does not trigger warning."""
    findings = [_make_finding(f"h{i}", ["get_input", "execute_query"]) for i in range(9)]
    findings.append(_make_finding("h9", ["get_input", "sanitize", "execute_query"]))
    # 1/10 = 10%, exactly at threshold — should NOT trigger (> not >=)
    rules = _rules_with_sanitizer("sanitize()")

    result = dry_run_scan(rules, findings, threshold=0.10)

    assert result.exceeded_threshold is False


def test_dry_run_does_not_modify_rules_object():
    """Dry-run must not write or mutate anything."""
    findings = [_make_finding("h1", ["get_input", "sanitize", "execute_query"])]
    rules = _rules_with_sanitizer("sanitize()")
    original_sanitizer_count = len(rules.sanitizers)

    dry_run_scan(rules, findings)

    assert len(rules.sanitizers) == original_sanitizer_count


# --- Pattern name stripping ---

def test_dotted_pattern_matches_by_func_name():
    """'pkg.sanitize()' should match a node named 'sanitize'."""
    findings = [_make_finding("h1", ["get_input", "sanitize", "execute_query"])]
    rules = _rules_with_sanitizer("internal_security.sanitize()")
    result = dry_run_scan(rules, findings)
    assert result.suppressed_by_candidate == 1
