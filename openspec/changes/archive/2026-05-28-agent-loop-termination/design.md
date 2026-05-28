## Context

The agent loop is the mechanism by which the LLM can request additional code context when it is uncertain about a verdict. It must be strictly bounded to prevent runaway token consumption. The cost model enables per-scan budget enforcement and post-scan cost reporting.

## Goals / Non-Goals

**Goals:**
- Four distinct termination conditions, enforced in priority order
- Token estimation before each LLM call (not exact; use tiktoken approximation)
- Per-path and per-scan budget caps (configurable)
- Audit log: record hop count, tokens used, and termination reason per path

**Non-Goals:**
- Prompt compression
- Parallel loops
- Dynamic budget based on finding severity (phase 2)

## Decisions

**Decision 1: Termination conditions (priority order)**

1. **Confidence threshold**: LLM returns `confidence >= 0.85` → terminate, accept verdict
2. **Explicit decision**: LLM returns `needs_more_context: false` → terminate, accept verdict
3. **Hop limit**: reached `max_hops` (default: 5) → terminate, use last verdict with `confidence` as-is
4. **Token budget**: next hop would exceed path budget → terminate, use last verdict

If the loop terminates due to hop limit or budget (not by LLM decision), the verdict confidence is capped at `0.7` regardless of what the LLM returned, signaling that the result is uncertain.

**Decision 2: Context expansion strategy**

Each hop:
1. LLM returns `needs_more_context: true` + optionally `context_request: ["func_name_A", "func_name_B"]`
2. Orchestrator fetches the requested functions from the graph (or the N-hop neighbors if no specific request)
3. Assembles new prompt with the expanded context (adds to, not replaces, the previous context slice)
4. Calls LLM again

**Decision 3: Token estimation**

Use `tiktoken` (cl100k_base encoding) to estimate tokens before each call. Add 20% buffer for safety. If `estimated_tokens + buffer > remaining_budget` → terminate early.

**Decision 4: Cost model**

```python
@dataclass
class ScanCostConfig:
    max_hops: int = 5
    path_token_budget: int = 20_000   # per taint path
    scan_token_budget: int = 500_000  # per full scan run
    confidence_threshold: float = 0.85
```

All configurable via `fennec.yaml` or CLI flags.

**Decision 5: Single-shot fallback**

When `agent_loop: false` (default), the orchestrator makes exactly one LLM call per taint path. The `needs_more_context` flag is ignored. This is the default mode for high-volume, lower-priority paths.

## Cross-Component Interfaces

- **Agent loop ← Taint tracker**: receives `TaintPath`
- **Agent loop → Context assembler**: requests additional function nodes by name or N-hop expansion
- **Agent loop → LLM client**: sends assembled prompt, receives `LLMVerdict`
- **Agent loop → Cost ledger**: records tokens used per hop, checks budget before each call
- **Agent loop → Finding synthesizer**: emits final `LLMVerdict` with termination metadata

## Risks / Trade-offs

- **Confidence threshold gaming** → LLM may always return high confidence to avoid loop. Mitigation: if `confidence >= 0.85` but `sanitization_present` and `sanitization_bypassable` are both `null`, treat as low confidence and continue loop.
- **Token estimation inaccuracy** → Tiktoken estimates can be off by 10–15%. The 20% buffer absorbs this.
- **Runaway cost in edge cases** → Hard scan budget cap prevents worst case. Budget exhaustion is logged and alerted.

## Open Questions

- Should we expose per-finding cost in the output report? (Yes — helps teams tune loop settings.)
- Should the confidence cap on forced termination be 0.7 or configurable? (Lean toward configurable, default 0.7.)
