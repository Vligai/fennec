"""Task 5.4: Integration test — tight scan budget exhausts mid-scan and switches modes."""

import json
import pytest
from unittest.mock import MagicMock

from fennec.engine.cost import CostLedger, ScanCostConfig, TerminationReason
from fennec.engine.loop import AgentLoop, ScanRunner, SingleShot
from fennec.graph.queries import TaintPath
from fennec.llm.renderer import FunctionSource, PromptRenderer
from fennec.llm.response import LLMVerdict, Severity


def _verdict_json(needs_more: bool = True, confidence: float = 0.5) -> str:
    return json.dumps({
        "sanitization_present": False,
        "sanitization_bypassable": None,
        "severity": "high",
        "confidence": confidence,
        "fix": "fix it",
        "needs_more_context": needs_more,
        "context_request": [],
    })


def _path(name: str = "src") -> TaintPath:
    return TaintPath(
        nodes=[
            {"id": f"fn:{name}", "name": name, "file_path": "a.py", "line_start": 1},
            {"id": "fn:snk", "name": "sink", "file_path": "b.py", "line_start": 5},
        ],
        edges=[], sanitized=False, hop_count=1,
    )


def _ctx() -> list[FunctionSource]:
    return [FunctionSource("src", "a.py", 1, 3, "def src(): ...")]


def test_scan_switches_to_single_shot_after_budget_exhausted(caplog):
    """Tight scan budget → first path uses agent loop, subsequent paths use single-shot."""
    import logging

    # Make the LLM return many 'needs more context' responses
    call_count = {"n": 0}

    def fake_analyze(_prompt):
        call_count["n"] += 1
        # After first call consume lots of tokens via the ledger tracking
        return _verdict_json(needs_more=True, confidence=0.3)

    llm = MagicMock()
    llm.analyze = MagicMock(side_effect=fake_analyze)

    # Tiny scan budget: enough for ~1 path worth of hops, not 3
    # estimate_tokens for a short prompt ≈ 50–200 tokens; set budget to allow ~1 hop
    cfg = ScanCostConfig(
        max_hops=5,
        path_token_budget=50_000,
        scan_token_budget=300,   # very tight — exhausts after first hop
        confidence_threshold=0.99,
    )
    ledger = CostLedger(cfg)
    renderer = PromptRenderer()

    agent_loop = AgentLoop(llm, renderer, ledger, cfg)
    single_shot = SingleShot(llm, renderer, ledger)
    runner = ScanRunner(agent_loop, single_shot, ledger)

    paths = [
        (_path(f"src{i}"), _ctx(), "sqli", f"hash-{i}")
        for i in range(4)
    ]

    with caplog.at_level(logging.WARNING, logger="fennec.engine.loop"):
        results = runner.run(paths)

    assert len(results) == 4

    report = runner.generate_report()
    audit_reasons = [r.termination_reason for r in report.audit_records]

    # After budget exhaustion, paths should use SINGLE_SHOT
    assert TerminationReason.SINGLE_SHOT in audit_reasons

    # Budget exhaustion warning logged
    assert any("budget exhausted" in msg.lower() for msg in caplog.messages)


def test_cost_report_emitted_after_scan():
    """ScanRunner.generate_report() returns a populated ScanCostReport."""
    llm = MagicMock()
    llm.analyze = MagicMock(return_value=_verdict_json(needs_more=False, confidence=0.9))

    cfg = ScanCostConfig(max_hops=3, confidence_threshold=0.85)
    ledger = CostLedger(cfg)
    runner = ScanRunner(
        AgentLoop(llm, PromptRenderer(), ledger, cfg),
        SingleShot(llm, PromptRenderer(), ledger),
        ledger,
    )

    paths = [(_path(), _ctx(), "sqli", f"h{i}") for i in range(2)]
    runner.run(paths)

    report = runner.generate_report()
    assert report.paths_analyzed == 2
    assert report.total_tokens_used > 0
