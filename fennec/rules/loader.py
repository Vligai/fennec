import logging
import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from .schema import CustomRules, SanitizerRule

logger = logging.getLogger(__name__)


class RuleValidationError(Exception):
    pass


def load_rules(path: str | Path) -> CustomRules:
    """Load and validate custom_rules.yaml.

    Returns an empty CustomRules if the file does not exist.
    Raises RuleValidationError on YAML or schema errors.
    """
    p = Path(path)
    if not p.exists():
        return CustomRules()

    try:
        with open(p) as fh:
            data = yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        raise RuleValidationError(f"Invalid YAML in {p}: {exc}") from exc

    try:
        return CustomRules.model_validate(data)
    except ValidationError as exc:
        raise RuleValidationError(f"Rule validation failed in {p}: {exc}") from exc


# ------------------------------------------------------------------ #
# Built-in taint taxonomy (seed layer)                               #
# ------------------------------------------------------------------ #

BUILTIN_SOURCES: dict[str, list[str]] = {
    "http":  ["request.body", "req.params", "request.GET", "ctx.query"],
    "env":   ["os.environ", "process.env", "getenv()"],
    "file":  ["open()", "fs.readFile", "File.read()"],
    "db":    ["cursor.fetchone()"],
}

BUILTIN_SINKS: dict[str, list[str]] = {
    "sqli":  ["cursor.execute()", "db.query()", ".raw()", "knex.raw()"],
    "cmdi":  ["subprocess.call()", "exec()", "child_process.exec()"],
    "xss":   ["innerHTML", "document.write()", "res.send(user_input)"],
    "ssrf":  ["requests.get(url)", "fetch(url)"],
    "deser": ["pickle.loads()", "yaml.load()", "JSON.parse()"],
}


def merge_sources(custom_rules: CustomRules) -> set[str]:
    """Return the union of built-in sources and custom sources."""
    sources: set[str] = set()
    for patterns in BUILTIN_SOURCES.values():
        sources.update(patterns)
    for rule in custom_rules.sources:
        sources.add(rule.pattern)
    return sources


def merge_sinks(custom_rules: CustomRules) -> dict[str, set[str]]:
    """Return built-in sinks merged with custom sinks, keyed by vuln class."""
    sinks: dict[str, set[str]] = {k: set(v) for k, v in BUILTIN_SINKS.items()}
    for rule in custom_rules.sinks:
        sinks.setdefault(rule.type, set()).add(rule.pattern)
    return sinks


def annotate_sanitizers(custom_rules: CustomRules, graph_client) -> None:
    """Annotate Function nodes in the graph with is_sanitizer=True for matching patterns.

    Pattern matching: strip trailing '()' and match against Function.name.
    """
    for san_rule in custom_rules.sanitizers:
        func_name = _pattern_to_name(san_rule.pattern)
        _set_sanitizer_flag(graph_client, func_name, san_rule.covers)


def _pattern_to_name(pattern: str) -> str:
    """Extract base function name from a pattern like 'pkg.func()' → 'func'."""
    name = pattern.rstrip("()")
    return name.rsplit(".", 1)[-1]


def _set_sanitizer_flag(graph_client, func_name: str, taint_type: str) -> None:
    with graph_client._driver.session() as session:
        session.run(
            "MATCH (f:Function {name: $name}) "
            "SET f.is_sanitizer = true, f.taint_types = coalesce(f.taint_types, []) + [$taint_type]",
            name=func_name,
            taint_type=taint_type,
        )


def apply_scope_filter(rules: list, file_path: str) -> list:
    """Return only rules whose scope matches file_path."""
    return [r for r in rules if r.matches_file(file_path)]


def advisory_exit_code(rules: list, has_findings: bool) -> int:
    """Return 0 if all fired rules are advisory, 1 if any are blocking."""
    if not has_findings:
        return 0
    for rule in rules:
        if rule.is_blocking():
            return 1
    return 0
