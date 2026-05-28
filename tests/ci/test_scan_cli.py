"""Tasks 5.1–5.3: scan CLI exit code mapping, advisory/blocking mode, SARIF output validity."""

import json
import pytest
from datetime import datetime, timezone

from fennec.ci.scanner import FailOn, map_exit_code
from fennec.graph.queries import TaintPath
from fennec.llm.response import Severity
from fennec.output.model import Finding, RuleMode, generate_finding_id
from fennec.output.sarif import SarifRenderer


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

def _taint_path() -> TaintPath:
    return TaintPath(
        nodes=[
            {"id": "fn:src", "name": "get_input", "file_path": "views.py", "line_start": 10},
            {"id": "fn:snk", "name": "execute",   "file_path": "db.py",    "line_start": 45},
        ],
        edges=[], sanitized=False, hop_count=1,
    )


def _finding(mode: RuleMode = RuleMode.BLOCKING, severity: Severity = Severity.HIGH) -> Finding:
    return Finding(
        id=generate_finding_id("sqli", "abc"),
        vuln_class="sqli",
        severity=severity,
        confidence=0.9,
        taint_path=_taint_path(),
        sanitized=False,
        fix="Use parameterized queries.",
        mode=mode,
        repo_id="repo-1",
        service_id="svc-a",
        scan_id="scan-001",
        created_at=datetime.now(timezone.utc),
    )


# ------------------------------------------------------------------ #
# Task 5.2: advisory findings → exit 0                                #
# ------------------------------------------------------------------ #

def test_advisory_findings_exit_zero():
    findings = [_finding(mode=RuleMode.ADVISORY)]
    assert map_exit_code(findings, FailOn.BLOCKING) == 0


def test_no_findings_exit_zero():
    assert map_exit_code([], FailOn.BLOCKING) == 0
    assert map_exit_code([], FailOn.ANY) == 0
    assert map_exit_code([], FailOn.NONE) == 0


# ------------------------------------------------------------------ #
# Task 5.1: blocking finding → non-zero exit                          #
# ------------------------------------------------------------------ #

def test_blocking_finding_exits_nonzero():
    findings = [_finding(mode=RuleMode.BLOCKING)]
    assert map_exit_code(findings, FailOn.BLOCKING) == 1


def test_fail_on_any_exits_nonzero_for_advisory():
    findings = [_finding(mode=RuleMode.ADVISORY)]
    assert map_exit_code(findings, FailOn.ANY) == 1


def test_fail_on_none_always_exits_zero():
    blocking = [_finding(mode=RuleMode.BLOCKING)]
    assert map_exit_code(blocking, FailOn.NONE) == 0


# Exit code table coverage
@pytest.mark.parametrize("mode,fail_on,expected", [
    (RuleMode.ADVISORY, "blocking", 0),
    (RuleMode.BLOCKING, "blocking", 1),
    (RuleMode.ADVISORY, "any",      1),
    (RuleMode.BLOCKING, "any",      1),
    (RuleMode.ADVISORY, "none",     0),
    (RuleMode.BLOCKING, "none",     0),
])
def test_exit_code_matrix(mode, fail_on, expected):
    findings = [_finding(mode=mode)]
    assert map_exit_code(findings, fail_on) == expected


# ------------------------------------------------------------------ #
# Task 5.3: SARIF output valid 2.1.0 structure                        #
# ------------------------------------------------------------------ #

def test_sarif_output_valid_structure():
    findings = [_finding()]
    renderer = SarifRenderer()
    sarif = renderer.render(findings)

    # Top-level structure
    assert sarif["version"] == "2.1.0"
    assert "$schema" in sarif
    assert len(sarif["runs"]) == 1

    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "Fennec"
    assert isinstance(run["tool"]["driver"]["rules"], list)
    assert isinstance(run["results"], list)
    assert len(run["results"]) == 1


def test_sarif_json_serialisable():
    findings = [_finding()]
    sarif = SarifRenderer().render(findings)
    dumped = json.dumps(sarif)
    reloaded = json.loads(dumped)
    assert reloaded["version"] == "2.1.0"


def test_sarif_empty_findings_valid():
    sarif = SarifRenderer().render([])
    assert sarif["runs"][0]["results"] == []
    assert sarif["runs"][0]["tool"]["driver"]["rules"] == []


def test_sarif_result_has_code_flow():
    findings = [_finding()]
    sarif = SarifRenderer().render(findings)
    result = sarif["runs"][0]["results"][0]
    assert "codeFlows" in result
    thread_locs = result["codeFlows"][0]["threadFlows"][0]["locations"]
    assert len(thread_locs) == 2  # source + sink
