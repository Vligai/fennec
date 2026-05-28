## Requirements

### Requirement: Structured JSON response parsing
The system SHALL parse LLM responses into a typed `LLMVerdict` dataclass with required fields.

#### Scenario: Valid response parsed
- **WHEN** the LLM returns a valid JSON object with all required fields
- **THEN** an `LLMVerdict` is returned with `sanitization_present`, `sanitization_bypassable`, `severity`, `confidence`, `fix`, and `needs_more_context` populated

#### Scenario: Severity value validated
- **WHEN** the LLM returns `"severity": "critical"`
- **THEN** the parsed severity is the enum value `Severity.CRITICAL`

#### Scenario: Invalid severity value handled
- **WHEN** the LLM returns an unrecognized severity value
- **THEN** severity is set to `Severity.UNKNOWN` and a warning is logged

### Requirement: Malformed response retry
The system SHALL retry once with a correction prompt when the LLM returns invalid JSON or omits required fields.

#### Scenario: Invalid JSON triggers retry
- **WHEN** the LLM response cannot be parsed as JSON
- **THEN** the system sends a follow-up message requesting JSON-only output and re-parses the response

#### Scenario: Second attempt also malformed
- **WHEN** the retry response is also malformed
- **THEN** `LLMVerdict` is returned with `confidence=0.0` and `severity=Severity.UNKNOWN`, and the failure is logged

### Requirement: More-context flag
The system SHALL support a `needs_more_context` boolean field in the response to signal the agent loop.

#### Scenario: More context requested
- **WHEN** the LLM response includes `"needs_more_context": true`
- **THEN** `LLMVerdict.needs_more_context` is `True` and the agent loop is invoked (if enabled)

#### Scenario: Single-shot mode ignores flag
- **WHEN** the engine is in single-shot mode and LLM returns `"needs_more_context": true`
- **THEN** the flag is ignored and the verdict is accepted as-is
