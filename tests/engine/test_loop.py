"""Tasks 3.5, 4.3: AgentLoop and SingleShot termination condition tests."""

import json
import pytest
from unittest.mock import MagicMock, patch

from fennec.engine.cost import CostLedger, ScanCostConfig, TerminationReason
from fennec.engine.loop import AgentLoop, SingleShot
from fennec.graph.queries import TaintPath
from fennec.llm.renderer import FunctionSource, PromptRenderer
from fennec.llm.response import LLMVerdict, Severity


def _path() -> TaintPath:
    return TaintPath(
        nodes=[
            {"id": "fn:src", "name": "get_input", "file_path": "a.py", "line_start": 1},
            {"id": "fn:snk", "name": "execute", "file_path": "b.py", "line_start": 10},
        ],
        edges=[], sanitized=False, hop_count=1,
    )


def _ctx() -> list[FunctionSource]:
    return [FunctionSource("get_input", "a.py", 1, 5, "def get_input(): ...")]


def _verdict(confidence: float, needs_more: bool = False, context_req: list | None = None) -> LLMVerdict:
    return LLMVerdict(
        sanitization_present=False, sanitization_bypassable=None,
        severity=Severity.HIGH, confidence=confidence,
        fix="fix", needs_more_context=needs_more,
        context_request=context_req or [],
    )


def _mock_llm(verdicts: list[LLMVerdict]) -> MagicMock:
    llm = MagicMock()
    responses = iter(json.dumps({
        "sanitization_present": v.sanitization_present,
        "sanitization_bypassable": v.sanitization_bypassable,
        "severity": v.severity.value,
        "confidence": v.confidence,
        "fix": v.fix,
        "needs_more_context": v.needs_more_context,
        "context_request": v.context_request,
    }) for v in verdicts)
    llm.analyze = MagicMock(side_effect=lambda _: next(responses))
    return llm


def _make_loop(verdicts, max_hops=5, path_budget=100_000, scan_budget=1_000_000,
               confidence_threshold=0.85):
    cfg = ScanCostConfig(max_hops=max_hops, path_token_budget=path_budget,
                         scan_token_budget=scan_budget,
                         confidence_threshold=confidence_threshold)
    ledger = CostLedger(cfg)
    llm = _mock_llm(verdicts)
    renderer = PromptRenderer()
    return AgentLoop(llm, renderer, ledger, cfg), ledger


# --- Confidence threshold termination ---

def test_terminates_at_confidence_threshold():
    loop, ledger = _make_loop([_verdict(0.9, needs_more=True)], confidence_threshold=0.85)
    verdict = loop.analyze(_path(), _ctx(), "sqli", "h1")
    assert verdict.confidence == pytest.approx(0.9)
    records = ledger.generate_report().audit_records
    assert records[0].termination_reason == TerminationReason.CONFIDENCE_THRESHOLD
    assert records[0].hop_count == 1


def test_loops_when_confidence_below_threshold():
    loop, ledger = _make_loop(
        [_verdict(0.5, needs_more=True), _verdict(0.9, needs_more=False)],
        confidence_threshold=0.85,
    )
    loop.analyze(_path(), _ctx(), "sqli", "h1")
    records = ledger.generate_report().audit_records
    assert records[0].hop_count == 2


# --- LLM decision termination ---

def test_terminates_when_needs_more_context_false():
    loop, ledger = _make_loop([_verdict(0.6, needs_more=False)])
    verdict = loop.analyze(_path(), _ctx(), "sqli", "h1")
    assert verdict.confidence == pytest.approx(0.6)
    records = ledger.generate_report().audit_records
    assert records[0].termination_reason == TerminationReason.LLM_DECISION


# --- Hop limit termination ---

def test_terminates_at_hop_limit():
    # All verdicts request more context; loop should stop at max_hops
    verdicts = [_verdict(0.5, needs_more=True)] * 10
    loop, ledger = _make_loop(verdicts, max_hops=3, confidence_threshold=0.99)
    loop.analyze(_path(), _ctx(), "sqli", "h1")
    records = ledger.generate_report().audit_records
    assert records[0].termination_reason == TerminationReason.HOP_LIMIT
    assert records[0].hop_count == 3


def test_confidence_capped_at_hop_limit():
    verdicts = [_verdict(0.95, needs_more=True)] * 10
    loop, ledger = _make_loop(verdicts, max_hops=2, confidence_threshold=0.99)
    verdict = loop.analyze(_path(), _ctx(), "sqli", "h1")
    assert verdict.confidence == pytest.approx(0.7)  # capped at default 0.7


# --- Token budget termination ---

def test_terminates_at_token_budget():
    # Set tiny path budget so it exhausts after first hop
    cfg = ScanCostConfig(max_hops=5, path_token_budget=1, scan_token_budget=1_000_000,
                         confidence_threshold=0.99)
    ledger = CostLedger(cfg)
    llm = _mock_llm([_verdict(0.5, needs_more=True)])
    renderer = PromptRenderer()
    loop = AgentLoop(llm, renderer, ledger, cfg)

    verdict = loop.analyze(_path(), _ctx(), "sqli", "h1")
    records = ledger.generate_report().audit_records
    assert records[0].termination_reason == TerminationReason.TOKEN_BUDGET


def test_confidence_capped_on_budget_termination():
    cfg = ScanCostConfig(max_hops=5, path_token_budget=1, scan_token_budget=1_000_000,
                         confidence_threshold=0.99, forced_termination_confidence_cap=0.7)
    ledger = CostLedger(cfg)
    llm = _mock_llm([_verdict(0.99, needs_more=True)])
    loop = AgentLoop(llm, PromptRenderer(), ledger, cfg)
    verdict = loop.analyze(_path(), _ctx(), "sqli", "h1")
    assert verdict.confidence <= 0.7


# --- Audit record produced ---

def test_audit_record_created():
    loop, ledger = _make_loop([_verdict(0.9)], confidence_threshold=0.85)
    loop.analyze(_path(), _ctx(), "sqli", "my-hash")
    records = ledger.generate_report().audit_records
    assert len(records) == 1
    assert records[0].path_hash == "my-hash"
    assert records[0].tokens_used > 0


# --- SingleShot ---

def test_single_shot_ignores_needs_more_context():
    cfg = ScanCostConfig()
    ledger = CostLedger(cfg)
    llm = _mock_llm([_verdict(0.5, needs_more=True)])
    ss = SingleShot(llm, PromptRenderer(), ledger)

    verdict = ss.analyze(_path(), _ctx(), "sqli", "h1")

    assert verdict.needs_more_context is False
    assert llm.analyze.call_count == 1  # exactly one call


def test_single_shot_produces_single_shot_audit():
    cfg = ScanCostConfig()
    ledger = CostLedger(cfg)
    llm = _mock_llm([_verdict(0.7, needs_more=True)])
    ss = SingleShot(llm, PromptRenderer(), ledger)

    ss.analyze(_path(), _ctx(), "sqli", "h1")

    records = ledger.generate_report().audit_records
    assert records[0].termination_reason == TerminationReason.SINGLE_SHOT
    assert records[0].hop_count == 1
