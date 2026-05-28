import logging
from dataclasses import dataclass, field
from enum import Enum

import tiktoken

logger = logging.getLogger(__name__)

_ENCODING = "cl100k_base"
_OVERHEAD_FACTOR = 1.2


class TerminationReason(str, Enum):
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    LLM_DECISION = "llm_decision"
    HOP_LIMIT = "hop_limit"
    TOKEN_BUDGET = "token_budget"
    SINGLE_SHOT = "single_shot"


@dataclass
class ScanCostConfig:
    max_hops: int = 5
    path_token_budget: int = 20_000
    scan_token_budget: int = 500_000
    confidence_threshold: float = 0.85
    forced_termination_confidence_cap: float = 0.7


@dataclass
class PathAuditRecord:
    path_hash: str
    hop_count: int
    tokens_used: int
    termination_reason: TerminationReason


@dataclass
class ScanCostReport:
    total_tokens_used: int
    paths_analyzed: int
    paths_using_agent_loop: int
    avg_hops_per_loop_path: float
    budget_exhausted: bool
    audit_records: list[PathAuditRecord] = field(default_factory=list)


def estimate_tokens(prompt: str) -> int:
    """Estimate token count with 20% overhead buffer using tiktoken cl100k_base."""
    enc = tiktoken.get_encoding(_ENCODING)
    raw = len(enc.encode(prompt))
    return int(raw * _OVERHEAD_FACTOR)


class CostLedger:
    """Tracks per-path and scan-level token usage; enforces budget caps."""

    def __init__(self, config: ScanCostConfig) -> None:
        self._config = config
        self._scan_tokens: int = 0
        self._path_tokens: int = 0
        self._audit_records: list[PathAuditRecord] = []
        self._scan_budget_exhausted: bool = False

    def start_path(self) -> None:
        self._path_tokens = 0

    def record_hop(self, estimated_tokens: int) -> None:
        self._path_tokens += estimated_tokens
        self._scan_tokens += estimated_tokens
        if self._scan_tokens >= self._config.scan_token_budget:
            self._scan_budget_exhausted = True

    def can_proceed(self, estimated_tokens: int) -> bool:
        """Return True if making a call with this cost would stay within both budgets."""
        if self._scan_budget_exhausted:
            return False
        if self._scan_tokens + estimated_tokens > self._config.scan_token_budget:
            return False
        if self._path_tokens + estimated_tokens > self._config.path_token_budget:
            return False
        return True

    def finish_path(
        self,
        path_hash: str,
        hop_count: int,
        reason: TerminationReason,
    ) -> PathAuditRecord:
        record = PathAuditRecord(
            path_hash=path_hash,
            hop_count=hop_count,
            tokens_used=self._path_tokens,
            termination_reason=reason,
        )
        self._audit_records.append(record)
        return record

    def is_scan_budget_exhausted(self) -> bool:
        return self._scan_budget_exhausted

    def generate_report(self) -> ScanCostReport:
        loop_records = [
            r for r in self._audit_records
            if r.termination_reason != TerminationReason.SINGLE_SHOT
        ]
        avg_hops = (
            sum(r.hop_count for r in loop_records) / len(loop_records)
            if loop_records else 0.0
        )
        return ScanCostReport(
            total_tokens_used=self._scan_tokens,
            paths_analyzed=len(self._audit_records),
            paths_using_agent_loop=len(loop_records),
            avg_hops_per_loop_path=avg_hops,
            budget_exhausted=self._scan_budget_exhausted,
            audit_records=list(self._audit_records),
        )
