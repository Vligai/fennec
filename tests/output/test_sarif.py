"""Task 2.5: SARIF output structure validation and severity mapping tests."""

import pytest
from fennec.llm.response import Severity
from fennec.output.sarif import SarifRenderer
from tests.output.conftest import make_finding, make_taint_path


renderer = SarifRenderer()


def _render_one(**kwargs) -> dict:
    return renderer.render([make_finding(**kwargs)])


# --- SARIF 2.1.0 structural validation ---

def test_sarif_version_and_schema():
    sarif = renderer.render([])
    assert sarif["version"] == "2.1.0"
    assert "sarif" in sarif["$schema"].lower()


def test_sarif_has_single_run():
    sarif = renderer.render([make_finding()])
    assert len(sarif["runs"]) == 1


def test_sarif_tool_driver_name():
    sarif = renderer.render([make_finding()])
    assert sarif["runs"][0]["tool"]["driver"]["name"] == "Fennec"


def test_sarif_rules_defined():
    sarif = _render_one(vuln_class="sqli")
    rules = sarif["runs"][0]["tool"]["driver"]["rules"]
    assert any(r["id"] == "sqli" for r in rules)


def test_sarif_results_count_matches_findings():
    findings = [make_finding(path_hash=str(i)) for i in range(3)]
    sarif = renderer.render(findings)
    assert len(sarif["runs"][0]["results"]) == 3


def test_sarif_result_rule_id_matches_vuln_class():
    sarif = _render_one(vuln_class="cmdi")
    result = sarif["runs"][0]["results"][0]
    assert result["ruleId"] == "cmdi"


def test_sarif_empty_findings_produces_valid_structure():
    sarif = renderer.render([])
    assert sarif["runs"][0]["results"] == []
    assert sarif["runs"][0]["tool"]["driver"]["rules"] == []


# --- Severity mapping ---

@pytest.mark.parametrize("sev,expected_level", [
    (Severity.CRITICAL, "error"),
    (Severity.HIGH,     "error"),
    (Severity.MEDIUM,   "warning"),
    (Severity.LOW,      "note"),
])
def test_severity_level_mapping(sev, expected_level):
    sarif = _render_one(severity=sev)
    result = sarif["runs"][0]["results"][0]
    assert result["level"] == expected_level


# --- Code flow ---

def test_single_hop_code_flow():
    sarif = _render_one(taint_path=make_taint_path(hops=0))
    result = sarif["runs"][0]["results"][0]
    thread_locs = result["codeFlows"][0]["threadFlows"][0]["locations"]
    assert len(thread_locs) == 2  # source + sink


def test_multi_hop_code_flow():
    sarif = _render_one(taint_path=make_taint_path(hops=2))
    result = sarif["runs"][0]["results"][0]
    thread_locs = result["codeFlows"][0]["threadFlows"][0]["locations"]
    assert len(thread_locs) == 4  # source + 2 hops + sink


def test_code_flow_has_file_and_line():
    sarif = _render_one()
    loc = sarif["runs"][0]["results"][0]["codeFlows"][0]["threadFlows"][0]["locations"][0]
    phys = loc["location"]["physicalLocation"]
    assert "uri" in phys["artifactLocation"]
    assert "startLine" in phys["region"]


# --- Fix suggestion ---

def test_fix_included_in_result():
    sarif = _render_one(fix="Use parameterized queries.")
    result = sarif["runs"][0]["results"][0]
    assert result["fixes"][0]["description"]["text"] == "Use parameterized queries."


def test_no_fix_when_fix_empty():
    sarif = _render_one(fix="")
    result = sarif["runs"][0]["results"][0]
    assert "fixes" not in result


# --- Deduplication of rules ---

def test_multiple_findings_same_vuln_class_one_rule():
    findings = [make_finding(vuln_class="sqli", path_hash=str(i)) for i in range(3)]
    sarif = renderer.render(findings)
    rules = sarif["runs"][0]["tool"]["driver"]["rules"]
    assert len([r for r in rules if r["id"] == "sqli"]) == 1
