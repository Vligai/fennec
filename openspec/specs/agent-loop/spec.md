## Requirements

### Requirement: Hop limit enforcement
The system SHALL not execute more than `max_hops` LLM calls per taint path in agent loop mode.

#### Scenario: Loop terminates at hop limit
- **WHEN** the LLM continues requesting more context and `max_hops` is reached
- **THEN** the loop terminates and uses the last returned verdict

#### Scenario: Confidence capped on forced termination
- **WHEN** the loop terminates due to hop limit (not LLM decision)
- **THEN** the final `LLMVerdict.confidence` is capped at `0.7`

### Requirement: Confidence threshold termination
The system SHALL terminate the loop early when the LLM returns `confidence >= confidence_threshold`.

#### Scenario: High-confidence verdict accepts early
- **WHEN** the LLM returns `confidence=0.9` on hop 2 of a 5-hop limit
- **THEN** the loop terminates and the verdict is accepted without further hops

### Requirement: Token budget enforcement
The system SHALL not make a LLM call if the estimated token cost would exceed the remaining path budget.

#### Scenario: Budget exhausted before hop limit
- **WHEN** the next hop's estimated token cost would exceed `path_token_budget`
- **THEN** the loop terminates without making the call and uses the last verdict with capped confidence

### Requirement: Scan-level budget cap
The system SHALL track cumulative token usage across all paths in a scan and stop agent loop mode when the scan budget is exhausted.

#### Scenario: Scan budget reached mid-scan
- **WHEN** cumulative tokens used across all paths reaches `scan_token_budget`
- **THEN** remaining paths are processed in single-shot mode for the rest of the scan

### Requirement: Single-shot mode
The system SHALL support a single-shot mode where exactly one LLM call is made per taint path and `needs_more_context` is ignored.

#### Scenario: Single-shot ignores loop request
- **WHEN** the scan is configured with `agent_loop: false` and the LLM returns `needs_more_context: true`
- **THEN** the verdict is accepted as-is without additional hops

### Requirement: Termination audit log
The system SHALL record hop count, tokens used, and termination reason for each analyzed taint path.

#### Scenario: Audit entry created
- **WHEN** a taint path analysis completes
- **THEN** an audit record is produced with: `path_hash`, `hop_count`, `tokens_used`, `termination_reason` (one of: `confidence_threshold`, `llm_decision`, `hop_limit`, `token_budget`, `single_shot`)
