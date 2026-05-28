## 1. Setup

- [x] 1.1 Add `tiktoken` to project dependencies
- [x] 1.2 Create `fennec/engine/` package with `__init__.py`, `loop.py`, `cost.py`
- [x] 1.3 Define `ScanCostConfig` dataclass with defaults in `cost.py`
- [x] 1.4 Define `TerminationReason` enum: `confidence_threshold`, `llm_decision`, `hop_limit`, `token_budget`, `single_shot`

## 2. Cost Model

- [x] 2.1 Implement `estimate_tokens(prompt: str) -> int` using tiktoken cl100k_base + 20% buffer
- [x] 2.2 Implement `CostLedger` class: tracks per-path and scan-level token usage
- [x] 2.3 Implement `CostLedger.can_proceed(estimated_tokens) -> bool` — checks both path and scan budget
- [x] 2.4 Implement `CostLedger.generate_report() -> ScanCostReport`
- [x] 2.5 Write unit tests: estimate is > raw tiktoken count; budget check returns False when exhausted

## 3. Agent Loop Orchestrator

- [x] 3.1 Implement `AgentLoop.analyze(taint_path, config) -> LLMVerdict` orchestrating multi-hop analysis
- [x] 3.2 Implement termination check order: confidence → `needs_more_context=false` → hop limit → token budget
- [x] 3.3 Cap `confidence` at `0.7` when terminating due to hop limit or budget (not LLM decision)
- [x] 3.4 Implement context expansion: fetch requested functions from graph; if none specified, fetch N-hop neighbors
- [x] 3.5 Write unit tests: loop terminates at each condition; confidence is capped correctly; audit record produced

## 4. Single-Shot Mode

- [x] 4.1 Implement `SingleShot.analyze(taint_path, config) -> LLMVerdict` — one call, ignore `needs_more_context`
- [x] 4.2 Wire both modes behind a common `Analyzer` interface with `agent_loop: bool` config flag
- [x] 4.3 Write unit test: single-shot ignores `needs_more_context=true`, returns verdict after one call

## 5. Scan Budget Integration

- [x] 5.1 Implement scan-level budget exhaustion: switch remaining paths to single-shot when cap reached
- [x] 5.2 Log budget exhaustion warning with path count
- [x] 5.3 Emit `ScanCostReport` at end of each scan run
- [x] 5.4 Write integration test: scan with tight budget exhausts mid-scan and switches modes correctly
