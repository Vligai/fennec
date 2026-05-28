import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from fennec.llm.client import LLMClient
from .loader import _pattern_to_name

logger = logging.getLogger(__name__)

_SUGGEST_PROMPT = """\
You are a security engineer analyzing a codebase for {vuln_class} vulnerability patterns.

Below are function names found in the codebase graph:
{function_list}

Which of these functions act as {field_label} for {vuln_class} vulnerabilities?

Respond ONLY with a JSON array. Each item: {{"pattern": "function_name()", "confidence": 0.0-1.0}}
Example: [{{"pattern": "sanitize_cmd()", "confidence": 0.95}}]
"""

_FIELD_LABELS = {
    "source":    "taint sources (functions that introduce untrusted data)",
    "sink":      "taint sinks (functions that consume untrusted data dangerously)",
    "sanitizer": "sanitizers (functions that make data safe for the given vuln class)",
}


@dataclass
class Candidate:
    pattern: str
    confidence: float
    evidence: list[dict] = field(default_factory=list)  # [{"name": str, "file_path": str, "line_start": int}]


def suggest_candidates(
    field: str,
    vuln_class: str,
    graph_client,
    llm_client: LLMClient,
    limit: int = 50,
) -> list[Candidate]:
    """Query the graph for function names, send to LLM, filter results against graph."""
    # 1. Sample function nodes from the graph
    graph_nodes = _sample_graph_functions(graph_client, limit=limit)
    if not graph_nodes:
        logger.warning("No function nodes in graph — run a parse first")
        return []

    # 2. Build and send prompt
    function_list = "\n".join(f"- {n['name']} [{n.get('file_path', '?')}:{n.get('line_start', '?')}]"
                              for n in graph_nodes)
    field_label = _FIELD_LABELS.get(field, field)
    prompt = _SUGGEST_PROMPT.format(
        vuln_class=vuln_class,
        function_list=function_list,
        field_label=field_label,
    )
    raw = llm_client.analyze(prompt)

    # 3. Parse LLM response
    raw_candidates = _parse_llm_suggestions(raw)

    # 4. Filter: only keep patterns that match a node in the graph
    node_map: dict[str, dict] = {n["name"]: n for n in graph_nodes}
    verified: list[Candidate] = []
    for rc in raw_candidates:
        name = _pattern_to_name(rc["pattern"])
        if name in node_map:
            node = node_map[name]
            verified.append(Candidate(
                pattern=rc["pattern"],
                confidence=float(rc.get("confidence", 0.5)),
                evidence=[{"name": node["name"], "file_path": node.get("file_path", "?"),
                            "line_start": node.get("line_start", "?")}],
            ))
        else:
            logger.debug("LLM suggested %r but it is not in the graph — discarded", rc["pattern"])

    verified.sort(key=lambda c: c.confidence, reverse=True)
    return verified


def run_approval_loop(
    candidates: list[Candidate],
    field: str,
    vuln_class: str,
    rules_path: Path,
) -> list[Candidate]:
    """Present candidates interactively; write approved ones to rules_path."""
    approved: list[Candidate] = []

    if not candidates:
        print("No verified candidates to review.")
        return approved

    print(f"\n=== AI Suggest: {field} candidates for {vuln_class} ===\n")
    for i, c in enumerate(candidates, 1):
        ev = c.evidence[0] if c.evidence else {}
        print(f"[{i}/{len(candidates)}] Pattern : {c.pattern}")
        print(f"            Confidence: {c.confidence:.0%}")
        print(f"            Evidence  : {ev.get('file_path', '?')}:{ev.get('line_start', '?')}")
        answer = input("            Approve? [y/N] ").strip().lower()
        if answer == "y":
            approved.append(c)
            print(f"  ✓ Approved: {c.pattern}")

    if approved:
        _append_to_rules_file(approved, field, vuln_class, rules_path)
        print(f"\n{len(approved)} rule(s) written to {rules_path}")

    return approved


def _sample_graph_functions(graph_client, limit: int) -> list[dict]:
    try:
        with graph_client._driver.session() as session:
            result = session.run(
                "MATCH (f:Function) RETURN f.name AS name, f.file_path AS file_path, "
                "f.line_start AS line_start LIMIT $limit",
                limit=limit,
            )
            return [dict(r) for r in result]
    except Exception as exc:
        logger.warning("Could not query graph: %s", exc)
        return []


def _parse_llm_suggestions(raw: str) -> list[dict]:
    try:
        data = json.loads(raw.strip())
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict) and "pattern" in d]
    except json.JSONDecodeError:
        pass
    logger.warning("LLM did not return valid JSON for suggestions")
    return []


def _append_to_rules_file(approved: list[Candidate], field: str, vuln_class: str, path: Path) -> None:
    existing: dict = {}
    if path.exists():
        with open(path) as fh:
            existing = yaml.safe_load(fh) or {}

    entries = existing.setdefault(f"{field}s", [])
    for c in approved:
        entry: dict = {"pattern": c.pattern}
        if field == "sanitizer":
            entry["covers"] = vuln_class
        elif field in ("source", "sink"):
            entry["type"] = vuln_class
        entries.append(entry)

    with open(path, "w") as fh:
        yaml.dump(existing, fh, default_flow_style=False, sort_keys=False)
