"""Task 3.6: PrCommentRenderer tests — 0 findings, 5 findings, 15 findings (truncation)."""

from fennec.llm.response import Severity
from fennec.output.pr_comment import MARKER, PrCommentRenderer
from tests.output.conftest import make_finding


renderer = PrCommentRenderer()


# --- 0 findings ---

def test_zero_findings_clean_message():
    comment = renderer.render([])
    assert MARKER in comment
    assert "No security findings detected" in comment


def test_zero_findings_has_marker():
    assert MARKER in renderer.render([])


# --- 5 findings ---

def test_five_findings_has_marker():
    findings = [make_finding(path_hash=str(i)) for i in range(5)]
    comment = renderer.render(findings)
    assert MARKER in comment


def test_five_findings_count_in_heading():
    findings = [make_finding(path_hash=str(i)) for i in range(5)]
    assert "5 findings" in renderer.render(findings)


def test_five_findings_severity_table():
    findings = [make_finding(severity=Severity.HIGH, path_hash=str(i)) for i in range(3)]
    findings += [make_finding(severity=Severity.MEDIUM, path_hash=str(i + 10)) for i in range(2)]
    comment = renderer.render(findings)
    assert "High" in comment
    assert "Medium" in comment


def test_five_findings_collapsible_details():
    findings = [make_finding(path_hash=str(i)) for i in range(5)]
    comment = renderer.render(findings)
    assert "<details>" in comment
    assert "Show findings" in comment


def test_five_findings_no_truncation_note():
    findings = [make_finding(path_hash=str(i)) for i in range(5)]
    comment = renderer.render(findings)
    assert "more findings" not in comment


# --- 15 findings (truncation) ---

def test_fifteen_findings_truncation_note():
    findings = [make_finding(path_hash=str(i)) for i in range(15)]
    comment = renderer.render(findings)
    assert "5 more findings" in comment
    assert "SARIF" in comment


def test_fifteen_findings_only_ten_shown():
    # Each finding has a unique path_hash, shown as vuln_class in details
    findings = [make_finding(path_hash=str(i), fix=f"fix-{i}") for i in range(15)]
    comment = renderer.render(findings)
    # fix-0 through fix-9 shown, fix-10 through fix-14 not
    assert "fix-9" in comment
    assert "fix-10" not in comment


def test_fifteen_findings_has_marker():
    findings = [make_finding(path_hash=str(i)) for i in range(15)]
    assert MARKER in renderer.render(findings)


# --- Details content ---

def test_finding_detail_includes_fix():
    findings = [make_finding(fix="Escape user input.")]
    assert "Escape user input." in renderer.render(findings)


def test_finding_detail_includes_taint_path_names():
    findings = [make_finding()]
    comment = renderer.render(findings)
    assert "get_input" in comment
    assert "execute_query" in comment
