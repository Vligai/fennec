import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from fennec.graph.queries import TaintPath
from fennec.llm.response import Severity


class RuleMode(str, Enum):
    ADVISORY = "advisory"
    BLOCKING = "blocking"


@dataclass
class Finding:
    id: str                   # deterministic: sha256(vuln_class + path_hash)[:16]
    vuln_class: str           # sqli | cmdi | xss | ssrf | deser | path_traversal
    severity: Severity
    confidence: float         # 0.0–1.0 from LLM verdict
    taint_path: TaintPath
    sanitized: bool
    fix: str                  # one-sentence fix from LLM
    mode: RuleMode
    repo_id: str
    service_id: str
    scan_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def generate_finding_id(vuln_class: str, path_hash: str) -> str:
    """Deterministic 16-char hex ID: sha256(vuln_class:path_hash)[:16]."""
    raw = f"{vuln_class}:{path_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    """Within a single scan, merge findings with the same ID (same vuln_class + path)."""
    seen: dict[str, Finding] = {}
    for f in findings:
        if f.id not in seen:
            seen[f.id] = f
    return list(seen.values())
