from datetime import datetime, timezone

from fennec.graph.queries import TaintPath
from fennec.llm.response import Severity
from fennec.output.model import Finding, RuleMode, generate_finding_id


def make_taint_path(source="get_input", sink="execute_query", hops: int = 0) -> TaintPath:
    nodes = [
        {"id": f"fn:{source}", "name": source, "file_path": "views.py", "line_start": 10},
    ]
    for i in range(hops):
        nodes.append(
            {"id": f"fn:mid{i}", "name": f"mid{i}", "file_path": "util.py", "line_start": 20 + i}
        )
    nodes.append(
        {"id": f"fn:{sink}", "name": sink, "file_path": "db.py", "line_start": 45}
    )
    return TaintPath(
        nodes=nodes,
        edges=[{"type": "DATA_FLOW", "variable": "user_input"}] * (len(nodes) - 1),
        sanitized=False,
        hop_count=len(nodes) - 1,
    )


def make_finding(
    vuln_class="sqli",
    severity=Severity.HIGH,
    path_hash="deadbeef",
    **overrides,
) -> Finding:
    defaults = dict(
        id=generate_finding_id(vuln_class, path_hash),
        vuln_class=vuln_class,
        severity=severity,
        confidence=0.9,
        taint_path=make_taint_path(),
        sanitized=False,
        fix="Use parameterized queries.",
        mode=RuleMode.BLOCKING,
        repo_id="repo-1",
        service_id="svc-a",
        scan_id="scan-001",
        created_at=datetime.now(timezone.utc),
    )
    return Finding(**{**defaults, **overrides})
