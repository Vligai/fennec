## Why

Developer verdicts (real vuln / false positive / won't fix) are the primary feedback mechanism for improving Fennec's FP rate over time. Without a well-designed signal store, verdicts are lost and the model cannot learn. The schema must support both per-repo learning and cross-service sanitizer trust propagation.

## What Changes

- Define the signal store schema (relational — SQLite for local, Postgres for hosted)
- Implement CRUD for verdict storage
- Implement the propagation rule: trusted sanitizer in service A propagates to all services using the same function
- Enforce the "won't fix" firewall: these verdicts are stored for suppression but never exposed to model training

## Non-goals

- Model fine-tuning pipeline (the signal store feeds it, but training is a separate concern)
- Real-time propagation (async batch is sufficient)
- Cross-org rule sharing (phase 2)

## Capabilities

### New Capabilities

- `signal-store`: Verdict storage with schema, CRUD, and audit fields
- `sanitizer-propagation`: Cross-service trust propagation for sanitizer verdicts

### Modified Capabilities

<!-- none — greenfield -->

## Impact

- LLM reasoning engine writes findings; finding synthesizer reads them
- Feedback loop writes verdicts; LLM engine reads sanitizer trust scores at scan time
- "Won't fix" suppression must be enforced at the query layer — never returned as training signal
