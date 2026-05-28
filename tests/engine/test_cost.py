"""Task 2.5: estimate_tokens and CostLedger unit tests."""

import pytest
from fennec.engine.cost import (
    CostLedger,
    ScanCostConfig,
    TerminationReason,
    estimate_tokens,
)


# --- estimate_tokens ---

def test_estimate_exceeds_raw_count():
    prompt = "Hello, world!" * 100
    estimated = estimate_tokens(prompt)
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    raw = len(enc.encode(prompt))
    assert estimated > raw


def test_estimate_is_approximately_120_percent():
    prompt = "a " * 1000
    estimated = estimate_tokens(prompt)
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    raw = len(enc.encode(prompt))
    assert abs(estimated - int(raw * 1.2)) <= 1  # rounding tolerance


def test_estimate_empty_string():
    assert estimate_tokens("") == 0


# --- ScanCostConfig defaults ---

def test_default_config_values():
    cfg = ScanCostConfig()
    assert cfg.max_hops == 5
    assert cfg.path_token_budget == 20_000
    assert cfg.scan_token_budget == 500_000
    assert cfg.confidence_threshold == 0.85
    assert cfg.forced_termination_confidence_cap == 0.7


# --- CostLedger.can_proceed ---

def test_can_proceed_within_budget():
    ledger = CostLedger(ScanCostConfig(path_token_budget=1000, scan_token_budget=5000))
    ledger.start_path()
    assert ledger.can_proceed(500) is True


def test_can_proceed_false_when_path_budget_exceeded():
    ledger = CostLedger(ScanCostConfig(path_token_budget=100, scan_token_budget=10_000))
    ledger.start_path()
    ledger.record_hop(90)
    assert ledger.can_proceed(20) is False  # 90 + 20 > 100


def test_can_proceed_false_when_scan_budget_exceeded():
    ledger = CostLedger(ScanCostConfig(path_token_budget=10_000, scan_token_budget=100))
    ledger.start_path()
    ledger.record_hop(90)
    assert ledger.can_proceed(20) is False  # 90 + 20 > 100


def test_can_proceed_false_after_exhaustion_flag():
    ledger = CostLedger(ScanCostConfig(path_token_budget=500, scan_token_budget=100))
    ledger.start_path()
    ledger.record_hop(100)  # exactly at limit → exhausted
    assert ledger.is_scan_budget_exhausted() is True
    assert ledger.can_proceed(1) is False


# --- Audit and report ---

def test_finish_path_creates_audit_record():
    ledger = CostLedger(ScanCostConfig())
    ledger.start_path()
    ledger.record_hop(500)
    record = ledger.finish_path("hash-abc", hop_count=2, reason=TerminationReason.LLM_DECISION)
    assert record.path_hash == "hash-abc"
    assert record.hop_count == 2
    assert record.tokens_used == 500
    assert record.termination_reason == TerminationReason.LLM_DECISION


def test_generate_report_after_multiple_paths():
    ledger = CostLedger(ScanCostConfig())

    ledger.start_path()
    ledger.record_hop(1000)
    ledger.finish_path("h1", 3, TerminationReason.CONFIDENCE_THRESHOLD)

    ledger.start_path()
    ledger.record_hop(500)
    ledger.finish_path("h2", 1, TerminationReason.SINGLE_SHOT)

    report = ledger.generate_report()
    assert report.total_tokens_used == 1500
    assert report.paths_analyzed == 2
    assert report.paths_using_agent_loop == 1  # single_shot excluded
    assert report.avg_hops_per_loop_path == 3.0
    assert not report.budget_exhausted
