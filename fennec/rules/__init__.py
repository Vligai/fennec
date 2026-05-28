from .schema import CustomRules, NamedRule, RuleMode, RuleScope, SanitizerRule, SinkRule, SourceRule
from .loader import (
    RuleValidationError,
    advisory_exit_code,
    annotate_sanitizers,
    apply_scope_filter,
    load_rules,
    merge_sinks,
    merge_sources,
)
from .dry_run import DryRunResult, dry_run_scan, print_dry_run_report
from .suggest import Candidate, suggest_candidates, run_approval_loop

__all__ = [
    "CustomRules", "NamedRule", "RuleMode", "RuleScope",
    "SanitizerRule", "SinkRule", "SourceRule",
    "RuleValidationError", "load_rules",
    "merge_sources", "merge_sinks", "annotate_sanitizers",
    "apply_scope_filter", "advisory_exit_code",
    "DryRunResult", "dry_run_scan", "print_dry_run_report",
    "Candidate", "suggest_candidates", "run_approval_loop",
]
