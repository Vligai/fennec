"""Per-vuln-class prompt templates.

Each entry in VULN_CLASS_METADATA provides the human-readable label and
class-specific guidance injected into the base prompt. The base template
follows the structure defined in the project README.
"""

VULN_CLASS_METADATA: dict[str, dict[str, str]] = {
    "sqli": {
        "label": "SQL Injection (SQLi)",
        "guidance": "Check for parameterized queries or ORM query builders.",
    },
    "cmdi": {
        "label": "Command Injection (CMDi)",
        "guidance": "Check for shlex.quote, subprocess with list args, or allowlist validation.",
    },
    "xss": {
        "label": "Cross-Site Scripting (XSS)",
        "guidance": "Check for HTML escaping, Content-Security-Policy, or template auto-escaping.",
    },
    "ssrf": {
        "label": "Server-Side Request Forgery (SSRF)",
        "guidance": "Check for URL allowlist, host validation, or metadata endpoint blocking.",
    },
    "deser": {
        "label": "Deserialization",
        "guidance": "Check if data originates from untrusted input before deserialization.",
    },
    "path_traversal": {
        "label": "Path Traversal",
        "guidance": "Check for path normalization and directory allowlists.",
    },
}

# Braces that are part of the JSON schema example are doubled to escape them
# from str.format().
BASE_TEMPLATE = """\
You are a security engineer reviewing a potential {vuln_label} vulnerability.

Taint path:
{taint_path_section}

Code context:
{context_section}

{guidance}

Questions:
1. Is there sanitization or parameterization on this path?
2. If yes, can it be bypassed?
3. Severity: critical / high / medium / low / false positive
4. Suggested fix (one sentence).

Respond in JSON only:
{{
  "sanitization_present": true|false,
  "sanitization_bypassable": true|false|null,
  "severity": "critical"|"high"|"medium"|"low"|"false_positive",
  "confidence": 0.0-1.0,
  "fix": "string",
  "needs_more_context": true|false
}}\
"""
