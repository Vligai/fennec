"""Task 4.5: ResponseParser tests — valid parse, invalid JSON retry, double failure fallback."""

import json
import pytest
from fennec.llm.response import LLMVerdict, ResponseParser, Severity


def _valid_payload(**overrides) -> str:
    base = {
        "sanitization_present": False,
        "sanitization_bypassable": None,
        "severity": "high",
        "confidence": 0.9,
        "fix": "Use parameterized queries.",
        "needs_more_context": False,
    }
    return json.dumps({**base, **overrides})


parser = ResponseParser()


# --- Valid response ---

def test_valid_json_parses_correctly():
    verdict = parser.parse(_valid_payload())
    assert isinstance(verdict, LLMVerdict)
    assert verdict.severity is Severity.HIGH
    assert verdict.confidence == pytest.approx(0.9)
    assert verdict.sanitization_present is False
    assert verdict.fix == "Use parameterized queries."
    assert verdict.needs_more_context is False


def test_all_severity_values_parsed():
    for sev in ("critical", "high", "medium", "low", "false_positive"):
        verdict = parser.parse(_valid_payload(severity=sev))
        assert verdict.severity == Severity(sev)


def test_needs_more_context_true():
    verdict = parser.parse(_valid_payload(needs_more_context=True))
    assert verdict.needs_more_context is True


# --- Invalid severity → UNKNOWN ---

def test_invalid_severity_falls_back_to_unknown():
    verdict = parser.parse(_valid_payload(severity="catastrophic"))
    assert verdict.severity is Severity.UNKNOWN


# --- Retry on invalid JSON ---

def test_invalid_json_triggers_retry():
    call_count = {"n": 0}

    def retry_fn(prompt: str) -> str:
        call_count["n"] += 1
        return _valid_payload(severity="medium")

    verdict = parser.parse("not json at all", retry_fn=retry_fn)

    assert call_count["n"] == 1
    assert verdict.severity is Severity.MEDIUM


def test_missing_required_field_triggers_retry():
    payload_missing_field = json.dumps({"severity": "high", "confidence": 0.5, "fix": "fix"})

    def retry_fn(prompt: str) -> str:
        return _valid_payload()

    verdict = parser.parse(payload_missing_field, retry_fn=retry_fn)
    assert verdict.severity is Severity.HIGH


# --- Double failure → fallback ---

def test_double_failure_returns_fallback_verdict():
    def always_bad(prompt: str) -> str:
        return "still not json"

    verdict = parser.parse("not json", retry_fn=always_bad)

    assert verdict.confidence == pytest.approx(0.0)
    assert verdict.severity is Severity.UNKNOWN
    assert verdict.needs_more_context is False


def test_no_retry_fn_returns_fallback_on_failure():
    verdict = parser.parse("garbage response", retry_fn=None)

    assert verdict.confidence == pytest.approx(0.0)
    assert verdict.severity is Severity.UNKNOWN
