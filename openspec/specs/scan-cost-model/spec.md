## Requirements

### Requirement: Token estimation before each LLM call
The system SHALL estimate the token count of a prompt before sending it, using tiktoken with a 20% overhead buffer.

#### Scenario: Estimate computed correctly
- **WHEN** a prompt string is submitted for estimation
- **THEN** the estimated token count equals the tiktoken count multiplied by 1.2

### Requirement: Configurable cost parameters
The system SHALL read `max_hops`, `path_token_budget`, `scan_token_budget`, and `confidence_threshold` from scan configuration, with documented defaults.

#### Scenario: Defaults applied when not configured
- **WHEN** no cost configuration is provided
- **THEN** `max_hops=5`, `path_token_budget=20000`, `scan_token_budget=500000`, `confidence_threshold=0.85` are used

### Requirement: Per-scan cost report
The system SHALL produce a cost summary at the end of each scan run.

#### Scenario: Cost report generated
- **WHEN** a scan run completes
- **THEN** the report includes: total tokens used, number of paths analyzed, number of paths that used agent loop, average hops per loop path, and whether scan budget was reached

### Requirement: Budget exhaustion alert
The system SHALL log a warning when scan token budget is exhausted before all paths are analyzed.

#### Scenario: Budget exhaustion logged
- **WHEN** `scan_token_budget` is reached mid-scan
- **THEN** a warning is logged: "Scan token budget exhausted at path N/M. Remaining paths processed in single-shot mode."
