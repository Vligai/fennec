import logging
from dataclasses import replace
from typing import Protocol, runtime_checkable

from fennec.graph.queries import TaintPath
from fennec.llm.client import LLMClient
from fennec.llm.renderer import FunctionSource, PromptRenderer
from fennec.llm.response import LLMVerdict
from .cost import CostLedger, ScanCostConfig, TerminationReason, PathAuditRecord, estimate_tokens

logger = logging.getLogger(__name__)


@runtime_checkable
class Analyzer(Protocol):
    def analyze(
        self,
        taint_path: TaintPath,
        context_slice: list[FunctionSource],
        vuln_class: str,
        path_hash: str = "",
    ) -> LLMVerdict: ...


class AgentLoop:
    """Multi-hop LLM analysis with explicit termination conditions.

    Termination priority order (highest to lowest):
      1. confidence >= confidence_threshold → accept verdict
      2. needs_more_context == False → accept verdict
      3. hop_limit reached → cap confidence, use last verdict
      4. token budget exhausted → cap confidence, use last verdict
    """

    def __init__(
        self,
        llm_client: LLMClient,
        renderer: PromptRenderer,
        ledger: CostLedger,
        config: ScanCostConfig,
        graph_client=None,
    ) -> None:
        self._llm = llm_client
        self._renderer = renderer
        self._ledger = ledger
        self._config = config
        self._graph_client = graph_client

    def analyze(
        self,
        taint_path: TaintPath,
        context_slice: list[FunctionSource],
        vuln_class: str,
        path_hash: str = "",
    ) -> LLMVerdict:
        self._ledger.start_path()
        current_context = list(context_slice)
        last_verdict: LLMVerdict | None = None
        hop = 0
        reason = TerminationReason.HOP_LIMIT

        while hop < self._config.max_hops:
            prompt = self._renderer.render(taint_path, current_context, vuln_class)
            estimated = estimate_tokens(prompt)

            if not self._ledger.can_proceed(estimated):
                reason = TerminationReason.TOKEN_BUDGET
                break

            raw = self._llm.analyze(prompt)
            from fennec.llm.response import ResponseParser
            verdict = ResponseParser().parse(raw)
            self._ledger.record_hop(estimated)
            hop += 1
            last_verdict = verdict

            # Termination condition 1: confidence threshold
            if verdict.confidence >= self._config.confidence_threshold:
                reason = TerminationReason.CONFIDENCE_THRESHOLD
                break

            # Termination condition 2: LLM explicitly done
            if not verdict.needs_more_context:
                reason = TerminationReason.LLM_DECISION
                break

            # Need more context — expand and loop
            current_context = self._expand_context(
                taint_path, current_context, verdict.context_request
            )
        else:
            reason = TerminationReason.HOP_LIMIT

        if last_verdict is None:
            # Budget exhausted before first call
            from fennec.llm.response import Severity
            last_verdict = LLMVerdict(
                sanitization_present=False,
                sanitization_bypassable=None,
                severity=Severity.UNKNOWN,
                confidence=0.0,
                fix="",
                needs_more_context=False,
            )

        # Cap confidence on forced termination (not by LLM decision)
        if reason in (TerminationReason.HOP_LIMIT, TerminationReason.TOKEN_BUDGET):
            cap = self._config.forced_termination_confidence_cap
            if last_verdict.confidence > cap:
                last_verdict = replace(last_verdict, confidence=cap)

        self._ledger.finish_path(path_hash, hop, reason)
        return last_verdict

    def _expand_context(
        self,
        taint_path: TaintPath,
        current: list[FunctionSource],
        context_request: list[str],
    ) -> list[FunctionSource]:
        if self._graph_client is None:
            return current

        extra: list[FunctionSource] = []
        if context_request:
            extra = self._fetch_named(context_request)
        else:
            source_id = taint_path.nodes[0].get("id", "") if taint_path.nodes else ""
            if source_id:
                neighbors = self._graph_client.get_neighbors(source_id, depth=1)
                extra = [
                    FunctionSource(
                        name=n.get("name", ""),
                        file_path=n.get("file_path", ""),
                        line_start=n.get("line_start", 0),
                        line_end=n.get("line_end", 0),
                        body="",
                    )
                    for n in neighbors
                ]

        seen = {f.name for f in current}
        return current + [f for f in extra if f.name not in seen]

    def _fetch_named(self, names: list[str]) -> list[FunctionSource]:
        results: list[FunctionSource] = []
        try:
            with self._graph_client._driver.session() as session:
                for name in names:
                    rec = session.run(
                        "MATCH (f:Function {name: $name}) "
                        "RETURN f.name AS name, f.file_path AS fp, f.line_start AS ls, f.line_end AS le LIMIT 1",
                        name=name,
                    ).single()
                    if rec:
                        results.append(FunctionSource(
                            name=rec["name"], file_path=rec["fp"] or "",
                            line_start=rec["ls"] or 0, line_end=rec["le"] or 0, body="",
                        ))
        except Exception as exc:
            logger.warning("Graph fetch failed for %s: %s", names, exc)
        return results


class SingleShot:
    """One-call-per-path analyzer; ignores needs_more_context."""

    def __init__(
        self,
        llm_client: LLMClient,
        renderer: PromptRenderer,
        ledger: CostLedger,
    ) -> None:
        self._llm = llm_client
        self._renderer = renderer
        self._ledger = ledger

    def analyze(
        self,
        taint_path: TaintPath,
        context_slice: list[FunctionSource],
        vuln_class: str,
        path_hash: str = "",
    ) -> LLMVerdict:
        self._ledger.start_path()
        prompt = self._renderer.render(taint_path, context_slice, vuln_class)
        estimated = estimate_tokens(prompt)

        if self._ledger.can_proceed(estimated):
            raw = self._llm.analyze(prompt)
            from fennec.llm.response import ResponseParser
            verdict = ResponseParser().parse(raw)
            self._ledger.record_hop(estimated)
            # Always ignore needs_more_context in single-shot mode
            verdict = replace(verdict, needs_more_context=False)
        else:
            from fennec.llm.response import Severity
            verdict = LLMVerdict(
                sanitization_present=False,
                sanitization_bypassable=None,
                severity=Severity.UNKNOWN,
                confidence=0.0,
                fix="",
                needs_more_context=False,
            )

        self._ledger.finish_path(path_hash, hop_count=1, reason=TerminationReason.SINGLE_SHOT)
        return verdict


class ScanRunner:
    """Orchestrates multi-path analysis; switches to single-shot when scan budget exhausted."""

    def __init__(
        self,
        agent_loop: AgentLoop,
        single_shot: SingleShot,
        ledger: CostLedger,
    ) -> None:
        self._agent_loop = agent_loop
        self._single_shot = single_shot
        self._ledger = ledger
        self._switched_at: int | None = None

    def run(
        self,
        paths: list[tuple[TaintPath, list[FunctionSource], str, str]],
    ) -> list[LLMVerdict]:
        """Analyze all (taint_path, context, vuln_class, path_hash) tuples."""
        results: list[LLMVerdict] = []
        total = len(paths)

        for i, (taint_path, context, vuln_class, path_hash) in enumerate(paths):
            if self._ledger.is_scan_budget_exhausted():
                if self._switched_at is None:
                    self._switched_at = i
                    remaining = total - i
                    logger.warning(
                        "Scan token budget exhausted at path %d/%d. "
                        "%d remaining path(s) processed in single-shot mode.",
                        i + 1, total, remaining,
                    )
                analyzer: Analyzer = self._single_shot
            else:
                analyzer = self._agent_loop

            verdict = analyzer.analyze(taint_path, context, vuln_class, path_hash)
            results.append(verdict)

        return results

    def generate_report(self):
        return self._ledger.generate_report()
