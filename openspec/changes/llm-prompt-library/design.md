## Context

The README defines the prompt structure and the agent loop behavior. This change operationalizes them: concrete prompt templates per vuln class, a renderer that fills in the taint path and context, a structured JSON response schema, and a parser that extracts actionable fields. The response schema is the contract between the LLM engine and the finding synthesizer.

## Goals / Non-Goals

**Goals:**
- One prompt template per Tier 1 vuln class (SQLi, CMDi, XSS, SSRF, deserialization, path traversal)
- Renderer: assembles final prompt from template + taint path + context slice
- Response schema: JSON with verdict, confidence, severity, sanitization_present, sanitization_bypassable, fix
- Parser: extracts and validates response fields, with fallback handling for malformed output
- Single-shot and agent-loop modes wired to the same template

**Non-Goals:**
- Prompt versioning / A/B testing
- Model selection logic (model is a config parameter)

## Decisions

**Decision 1: Prompt structure (from README)**

```
You are a security engineer reviewing a potential [VULN CLASS] vulnerability.

Taint path:
  Source: [source] [file:line]
  → [intermediary functions with file:line]
  → Sink: [sink] [file:line]

Code context:
[assembled code slice]

Questions:
1. Is there sanitization or parameterization on this path?
2. If yes, can it be bypassed?
3. Severity: critical / high / medium / low / false positive
4. Suggested fix (one sentence).

Respond in JSON only:
{
  "sanitization_present": bool,
  "sanitization_bypassable": bool | null,
  "severity": "critical" | "high" | "medium" | "low" | "false_positive",
  "confidence": 0.0–1.0,
  "fix": "string"
}
```

**Decision 2: Per-vuln-class template variants**

Each vuln class has a small override block that customizes the `[VULN CLASS]` description and adds class-specific guidance:

| Vuln class | Key guidance addition |
|---|---|
| SQLi | "Check for parameterized queries or ORM query builders" |
| CMDi | "Check for shlex.quote, subprocess with list args, or allowlist validation" |
| XSS | "Check for HTML escaping, Content-Security-Policy, or template auto-escaping" |
| SSRF | "Check for URL allowlist, host validation, or metadata endpoint blocking" |
| Deserialization | "Check if data originates from untrusted input before deserialization" |
| Path traversal | "Check for path normalization and directory allowlists" |

**Decision 3: Structured JSON response with retry**

The LLM is instructed to respond in JSON only. If the response is not valid JSON or missing required fields:
1. Retry once with `"Your previous response was not valid JSON. Please respond only with the JSON object."`
2. If second attempt fails: mark verdict as `confidence=0.0, severity="unknown"` and log for review

**Decision 4: Context injection limit**

The assembled code context is truncated to fit the model's context window. Truncation strategy: include the source function, sink function, and the N nearest intermediate functions sorted by proximity to the taint path. Never truncate the taint path itself.

## Cross-Component Interfaces

- **Context assembler → Prompt renderer**: provides `List[FunctionSource]` (name, file, lines, body)
- **Taint tracker → Prompt renderer**: provides `TaintPath` (source, intermediaries, sink)
- **Prompt renderer → LLM client**: returns assembled `str` prompt
- **LLM client → Response parser**: returns raw `str` response
- **Response parser → Finding synthesizer**: returns `LLMVerdict` dataclass

## Risks / Trade-offs

- **Model drift** → Future model versions may respond differently to the same prompt. Mitigation: regression test suite of fixed taint paths with expected severity outputs.
- **Context window overflow** → Very long taint paths + large functions may exceed limit. Mitigation: truncation strategy defined above; log when truncation occurs.
- **JSON parsing failure** → Mitigated by retry + fallback, but a high failure rate indicates a model compatibility issue.

## Open Questions

- Should the fix suggestion be one sentence or a code snippet? (Lean toward one sentence for v1 — code snippets require more validation and post-processing.)
- Should confidence scores drive agent loop invocation, or should the LLM explicitly request more context? (Lean toward LLM explicitly flagging: add `"needs_more_context": bool` to response schema.)
