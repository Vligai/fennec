## Why

The agent loop (LLM requests more context, fetches additional functions, re-runs) is powerful but unbounded without explicit termination conditions. Runaway loops waste LLM tokens and make scan cost unpredictable. The README states "bounded at 3–5 hops max" but doesn't define the full termination logic or cost model. This change specifies both.

## What Changes

- Define all termination conditions: hop limit, confidence threshold, context budget, explicit LLM decision
- Implement the agent loop orchestrator with these conditions enforced
- Define the cost model: token estimation per hop, total budget per taint path, per-scan budget cap
- Implement single-shot fallback: always available as the no-loop mode

## Non-goals

- Dynamic hop limit based on codebase size (fixed limit for v1)
- Cost optimization / prompt compression
- Parallel agent loops across multiple taint paths (sequential for v1)

## Capabilities

### New Capabilities

- `agent-loop`: Orchestrates multi-hop LLM context expansion with explicit termination conditions
- `scan-cost-model`: Token estimation and budget enforcement per taint path and per scan

### Modified Capabilities

<!-- none — greenfield; builds on llm-prompt-library -->

## Impact

- The agent loop wraps the `llm-prompt-library` components
- Cost model must be consulted before each hop; scan will not exceed budget even if LLM keeps requesting context
- Single-shot mode remains the default; agent loop is opt-in per scan configuration
