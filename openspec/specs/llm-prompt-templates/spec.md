## Requirements

### Requirement: Per-vuln-class prompt templates
The system SHALL provide a distinct prompt template for each supported vulnerability class: SQLi, CMDi, XSS, SSRF, deserialization, and path traversal.

#### Scenario: SQLi template selected
- **WHEN** the prompt renderer is called with `vuln_class="sqli"`
- **THEN** the rendered prompt includes the SQLi-specific guidance about parameterized queries

#### Scenario: Unsupported vuln class
- **WHEN** the prompt renderer is called with an unrecognized `vuln_class`
- **THEN** a `ValueError` is raised with the unsupported class name

### Requirement: Taint path injection
The system SHALL render the full taint path (source, intermediaries, sink) with file and line references into the prompt.

#### Scenario: Multi-hop path rendered
- **WHEN** a taint path with 3 intermediary functions is passed to the renderer
- **THEN** all 5 nodes (source + 3 + sink) appear in the prompt with `file:line` references

### Requirement: Code context injection
The system SHALL inject the assembled code slice into the prompt, truncated to fit the model's context window.

#### Scenario: Context fits without truncation
- **WHEN** the total assembled context is within the context window limit
- **THEN** the full context is included in the prompt

#### Scenario: Context truncated
- **WHEN** the assembled context exceeds the context window limit
- **THEN** the source and sink functions are preserved, intermediate functions are pruned by distance from the taint path, and truncation is logged

### Requirement: JSON-only response instruction
The system SHALL instruct the LLM to respond in JSON only, with no surrounding prose.

#### Scenario: JSON instruction present
- **WHEN** any prompt is rendered
- **THEN** the prompt ends with explicit instruction to respond only with the JSON object
