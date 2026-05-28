from importlib.metadata import version, PackageNotFoundError

from fennec.llm.response import Severity
from .model import Finding

try:
    _FENNEC_VERSION = version("fennec")
except PackageNotFoundError:
    _FENNEC_VERSION = "0.1.0"

_SEVERITY_TO_SARIF_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.FALSE_POSITIVE: "note",
    Severity.UNKNOWN: "note",
}

_VULN_CLASS_RULE = {
    "sqli":           ("SqlInjection",             "SQL Injection"),
    "cmdi":           ("CommandInjection",          "Command Injection"),
    "xss":            ("CrossSiteScripting",        "Cross-Site Scripting"),
    "ssrf":           ("ServerSideRequestForgery",  "Server-Side Request Forgery"),
    "deser":          ("Deserialization",           "Insecure Deserialization"),
    "path_traversal": ("PathTraversal",             "Path Traversal"),
}


class SarifRenderer:
    """Produces a SARIF 2.1.0-compliant dict from a list of Finding objects."""

    def render(self, findings: list[Finding]) -> dict:
        rules = self._build_rules(findings)
        results = [self._finding_to_result(f) for f in findings]

        return {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Fennec",
                            "version": _FENNEC_VERSION,
                            "informationUri": "https://github.com/fennec-sec/fennec",
                            "rules": rules,
                        }
                    },
                    "results": results,
                }
            ],
        }

    # ------------------------------------------------------------------ #
    # Private                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_rules(findings: list[Finding]) -> list[dict]:
        seen: set[str] = set()
        rules: list[dict] = []
        for f in findings:
            if f.vuln_class in seen:
                continue
            seen.add(f.vuln_class)
            rule_name, description = _VULN_CLASS_RULE.get(
                f.vuln_class,
                (f.vuln_class, f.vuln_class.replace("_", " ").title()),
            )
            rules.append(
                {
                    "id": f.vuln_class,
                    "name": rule_name,
                    "shortDescription": {"text": description},
                    "helpUri": f"https://cwe.mitre.org/data/definitions/{f.vuln_class}.html",
                }
            )
        return rules

    @staticmethod
    def _finding_to_result(f: Finding) -> dict:
        nodes = f.taint_path.nodes
        source = nodes[0] if nodes else {}
        sink = nodes[-1] if nodes else {}

        result: dict = {
            "ruleId": f.vuln_class,
            "level": _SEVERITY_TO_SARIF_LEVEL.get(f.severity, "note"),
            "message": {
                "text": (
                    f"Potential {f.vuln_class.upper()} detected: "
                    f"{source.get('name', '?')} → {sink.get('name', '?')}. "
                    f"Confidence: {f.confidence:.0%}."
                )
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": source.get("file_path", ""),
                            "uriBaseId": "%SRCROOT%",
                        },
                        "region": {"startLine": source.get("line_start", 1)},
                    }
                }
            ],
            "partialFingerprints": {"fennecFindingId/v1": f.id},
        }

        # Code flow: one location per hop in the taint path
        if nodes:
            thread_locations = [
                {
                    "location": {
                        "physicalLocation": {
                            "artifactLocation": {"uri": n.get("file_path", "")},
                            "region": {"startLine": n.get("line_start", 1)},
                        },
                        "message": {"text": n.get("name", "")},
                    }
                }
                for n in nodes
            ]
            result["codeFlows"] = [
                {"threadFlows": [{"locations": thread_locations}]}
            ]

        # Fix suggestion
        if f.fix:
            result["fixes"] = [
                {
                    "description": {"text": f.fix},
                    "artifactChanges": [],
                }
            ]

        return result
