## Why

The LLM reasoning engine's output quality is directly determined by prompt quality. Open-ended prompts produce noisy, inconsistent verdicts. Constrained, per-vuln-class prompts with structured output format are the stated design principle. Without a prompt library, every engineer on the team writes their own prompts ad hoc, leading to drift and untestable behavior.

## What Changes

- Define the standard prompt structure for vulnerability analysis (shown in README)
- Implement a prompt template per vuln class: SQLi, CMDi, XSS, SSRF, IDSN, path traversal
- Define a structured response schema (JSON) for LLM verdicts
- Implement a prompt renderer that assembles a final prompt from taint path + code context + vuln class
- Implement a response parser that extracts verdict, confidence, severity, and fix suggestion

## Non-goals

- Model fine-tuning or RLHF
- Open-ended "find all vulns" prompts
- Prompt versioning / A/B testing (phase 2)

## Capabilities

### New Capabilities

- `llm-prompt-templates`: Per-vuln-class prompt templates and the renderer that assembles them
- `llm-response-schema`: Structured JSON response schema and parser for LLM verdicts

### Modified Capabilities

<!-- none — greenfield -->

## Impact

- All LLM calls go through the prompt library — no ad hoc prompt construction elsewhere
- Response schema determines what fields the finding synthesizer can consume
- Prompt quality directly determines FP rate; this is a product-level artifact, not just code
