## 1. Setup

- [ ] 1.1 Add `tiktoken` to project dependencies
- [ ] 1.2 Create `fennec/engine/` package with `__init__.py`, `loop.py`, `cost.py`
- [ ] 1.3 Define `ScanCostConfig` dataclass with defaults in `cost.py`
- [ ] 1.4 Define `TerminationReason` enum: `confidence_threshold`, `llm_decision`, `hop_limit`, `token_budget`, `single_shot`

## 2. Cost Model

- [ ] 2.1 Implement `estimate_tokens(prompt: str) -> int` using tiktoken cl100k_base + 20% buffer
- [ ] 2.2 Implement `CostLedger` class: tracks per-path and scan-level token usage
- [ ] 2.3 Implement `CostLedger.can_proceed(estimated_tokens) -> bool` — checks both path and scan budget
- [ ] 2.4 Implement `CostLedger.generate_report() -> ScanCostReport`
- [ ] 2.5 Write unit tests: estimate is > raw tiktoken count; budget check returns False when exhausted

## 3. Agent Loop Orchestrator

- [ ] 3.1 Implement `AgentLoop.analyze(taint_path, config) -> LLMVerdict` orchestrating multi-hop analysis
- [ ] 3.2 Implement termination check order: confidence → `needs_more_context=false` → hop limit → token budget
- [ ] 3.3 Cap `confidence` at `0.7` when terminating due to hop limit or budget (not LLM decision)
- [ ] 3.4 Implement context expansion: fetch requested functions from graph; if none specified, fetch N-hop neighbors
- [ ] 3.5 Write unit tests: loop terminates at each condition; confidence is capped correctly; audit record produced

## 4. Single-Shot Mode

- [ ] 4.1 Implement `SingleShot.analyze(taint_path, config) -> LLMVerdict` — one call, ignore `needs_more_context`
- [ ] 4.2 Wire both modes behind a common `Analyzer` interface with `agent_loop: bool` config flag
- [ ] 4.3 Write unit test: single-shot ignores `needs_more_context=true`, returns verdict after one call

## 5. Scan Budget Integration

- [ ] 5.1 Implement scan-level budget exhaustion: switch remaining paths to single-shot when cap reached
- [ ] 5.2 Log budget exhaustion warning with path count
- [ ] 5.3 Emit `ScanCostReport` at end of each scan run
- [ ] 5.4 Write integration test: scan with tight budget exhausts mid-scan and switches modes correctly
