import logging
from dataclasses import dataclass, field

from fennec.output.model import Finding
from .loader import _pattern_to_name
from .schema import CustomRules

logger = logging.getLogger(__name__)

_FP_THRESHOLD = 0.10


@dataclass
class DryRunResult:
    total_findings: int
    suppressed_by_candidate: int
    suppression_rate: float
    exceeded_threshold: bool
    threshold: float = _FP_THRESHOLD
    warnings: list[str] = field(default_factory=list)


def dry_run_scan(
    candidate_rules: CustomRules,
    existing_findings: list[Finding],
    repo_path: str = "",
    threshold: float = _FP_THRESHOLD,
) -> DryRunResult:
    """Estimate how many existing findings would be suppressed by candidate rules.

    Traversal-only — no LLM calls. Works with pre-computed findings.
    Pattern matching: function names stripped of '()' and package prefix are matched
    against node names in each finding's taint path.
    """
    sanitizer_names = {
        _pattern_to_name(rule.pattern)
        for rule in candidate_rules.sanitizers
    }

    suppressed = 0
    for finding in existing_findings:
        path_node_names = {n.get("name", "") for n in finding.taint_path.nodes}
        if sanitizer_names & path_node_names:
            suppressed += 1

    total = len(existing_findings)
    rate = suppressed / total if total > 0 else 0.0
    exceeded = rate > threshold

    warnings: list[str] = []
    if exceeded:
        warnings.append(
            f"WARNING: Estimated FP rate {rate:.0%} exceeds threshold ({threshold:.0%})"
        )

    return DryRunResult(
        total_findings=total,
        suppressed_by_candidate=suppressed,
        suppression_rate=rate,
        exceeded_threshold=exceeded,
        threshold=threshold,
        warnings=warnings,
    )


def print_dry_run_report(result: DryRunResult) -> None:
    print(f"\n=== Dry-run Results ===")
    print(f"Total findings        : {result.total_findings}")
    print(f"Suppressed by rule    : {result.suppressed_by_candidate}")
    print(f"Suppression rate      : {result.suppression_rate:.1%}")

    for w in result.warnings:
        print(f"\n⚠️  {w}")

    if not result.exceeded_threshold:
        print("\n✅ Rule appears safe to activate.")
    else:
        print("\nRun `fennec rules activate --force` to bypass the threshold check.")
