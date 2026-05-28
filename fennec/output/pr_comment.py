from fennec.llm.response import Severity
from .model import Finding

MARKER = "<!-- fennec-scan-result -->"
_MAX_DETAILS = 10

_SEVERITY_EMOJI = {
    Severity.CRITICAL:       "🔴 Critical",
    Severity.HIGH:           "🟠 High",
    Severity.MEDIUM:         "🟡 Medium",
    Severity.LOW:            "🔵 Low",
    Severity.FALSE_POSITIVE: "⚪ False Positive",
    Severity.UNKNOWN:        "⚫ Unknown",
}

_SEVERITY_ORDER = [
    Severity.CRITICAL,
    Severity.HIGH,
    Severity.MEDIUM,
    Severity.LOW,
    Severity.FALSE_POSITIVE,
    Severity.UNKNOWN,
]


class PrCommentRenderer:
    """Renders scan findings as a GitHub/GitLab PR comment in Markdown."""

    def render(self, findings: list[Finding]) -> str:
        if not findings:
            return self._no_findings_comment()
        return self._findings_comment(findings)

    # ------------------------------------------------------------------ #
    # Private                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _no_findings_comment() -> str:
        return (
            f"{MARKER}\n"
            "## Fennec Security Scan — no findings\n\n"
            "✅ Fennec scan completed. No security findings detected."
        )

    def _findings_comment(self, findings: list[Finding]) -> str:
        counts = {sev: 0 for sev in _SEVERITY_ORDER}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        table = self._severity_table(counts)
        details = self._details_section(findings)

        return (
            f"{MARKER}\n"
            f"## Fennec Security Scan — {len(findings)} finding{'s' if len(findings) != 1 else ''}\n\n"
            f"{table}\n\n"
            f"{details}"
        )

    @staticmethod
    def _severity_table(counts: dict[Severity, int]) -> str:
        rows = "\n".join(
            f"| {_SEVERITY_EMOJI[sev]} | {counts[sev]} |"
            for sev in _SEVERITY_ORDER
            if counts.get(sev, 0) > 0
        )
        if not rows:
            return "| Severity | Count |\n|---|---|\n| (none) | 0 |"
        return f"| Severity | Count |\n|---|---|\n{rows}"

    def _details_section(self, findings: list[Finding]) -> str:
        shown = findings[:_MAX_DETAILS]
        overflow = len(findings) - len(shown)

        items = "\n\n---\n\n".join(self._finding_detail(f) for f in shown)
        truncation_note = (
            f"\n\n_{overflow} more finding{'s' if overflow != 1 else ''} — see SARIF report_"
            if overflow > 0
            else ""
        )

        return (
            f"<details><summary>Show findings ({len(findings)})</summary>\n\n"
            f"{items}"
            f"{truncation_note}\n\n"
            f"</details>"
        )

    @staticmethod
    def _finding_detail(f: Finding) -> str:
        nodes = f.taint_path.nodes
        source = nodes[0] if nodes else {}
        sink = nodes[-1] if nodes else {}
        intermediaries = nodes[1:-1] if len(nodes) > 2 else []

        path_parts = [source.get("name", "?")]
        if intermediaries:
            path_parts.append("…")
        path_parts.append(sink.get("name", "?"))
        path_str = " → ".join(path_parts)

        file_ref = f"{source.get('file_path', '?')}:{source.get('line_start', '?')}"
        sev_label = _SEVERITY_EMOJI.get(f.severity, str(f.severity))

        lines = [
            f"### [{f.vuln_class}] in `{file_ref}`",
            f"**Taint path:** `{path_str}`",
            f"**Severity:** {sev_label} | **Confidence:** {f.confidence:.0%}",
        ]
        if f.fix:
            lines.append(f"**Fix:** {f.fix}")

        return "\n".join(lines)
