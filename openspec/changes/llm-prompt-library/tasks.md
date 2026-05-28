## 1. Setup

- [x] 1.1 Create `fennec/llm/` package with `__init__.py`, `templates.py`, `renderer.py`, `response.py`, `client.py`
- [x] 1.2 Define `Severity` enum and `LLMVerdict` dataclass in `response.py`

## 2. Prompt Templates

- [x] 2.1 Implement base prompt template in `templates.py` following the README structure
- [x] 2.2 Add vuln-class override blocks for: SQLi, CMDi, XSS, SSRF, deserialization, path traversal
- [x] 2.3 Write unit tests: each vuln class renders without error; unsupported class raises `ValueError`

## 3. Prompt Renderer

- [x] 3.1 Implement `PromptRenderer.render(taint_path, context_slice, vuln_class) -> str`
- [x] 3.2 Implement context window truncation: preserve source/sink, prune intermediates by proximity
- [x] 3.3 Log when truncation occurs (file:line count removed)
- [x] 3.4 Write unit tests: full context renders intact; oversized context truncates and preserves source/sink

## 4. Response Parser

- [x] 4.1 Implement `ResponseParser.parse(raw_response) -> LLMVerdict`
- [x] 4.2 Validate all required fields; fall back to `UNKNOWN` severity on invalid enum values
- [x] 4.3 Implement retry logic: send correction prompt once on invalid JSON or missing fields
- [x] 4.4 Return `confidence=0.0, severity=UNKNOWN` verdict on second failure; log to error log
- [x] 4.5 Write unit tests: valid JSON parses correctly; invalid JSON retries; double failure returns fallback

## 5. LLM Client Wrapper

- [x] 5.1 Implement `LLMClient.analyze(prompt) -> str` wrapping the Anthropic SDK (model configurable)
- [x] 5.2 Support single-shot mode: one call, parse verdict, return
- [x] 5.3 Add `needs_more_context` passthrough: if `True` and agent loop is enabled, caller handles iteration
- [x] 5.4 Write integration test with a fixture taint path against a real model call (opt-in, skipped in CI by default)
