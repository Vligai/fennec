import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import Enum

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = {"sanitization_present", "severity", "confidence", "fix"}

_CORRECTION_PROMPT = (
    "Your previous response was not valid JSON. "
    "Please respond only with the JSON object."
)


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FALSE_POSITIVE = "false_positive"
    UNKNOWN = "unknown"


@dataclass
class LLMVerdict:
    sanitization_present: bool
    sanitization_bypassable: bool | None
    severity: Severity
    confidence: float
    fix: str
    needs_more_context: bool
    context_request: list[str] = field(default_factory=list)


_FALLBACK_VERDICT = LLMVerdict(
    sanitization_present=False,
    sanitization_bypassable=None,
    severity=Severity.UNKNOWN,
    confidence=0.0,
    fix="",
    needs_more_context=False,
    context_request=[],
)


class ResponseParser:
    """Parse raw LLM JSON responses into typed LLMVerdict objects.

    Retries once with a correction prompt on invalid JSON or missing fields.
    Returns a zero-confidence fallback verdict if both attempts fail.
    """

    def parse(
        self,
        raw_response: str,
        retry_fn: Callable[[str], str] | None = None,
    ) -> LLMVerdict:
        try:
            return self._parse_raw(raw_response)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("LLM response parse failed (%s); %s", exc, "retrying" if retry_fn else "no retry")
            if retry_fn is None:
                logger.error("LLM response parsing failed with no retry available")
                return replace(_FALLBACK_VERDICT)

        try:
            retried = retry_fn(_CORRECTION_PROMPT)
            return self._parse_raw(retried)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("LLM response parsing failed after retry (%s)", exc)
            return replace(_FALLBACK_VERDICT)

    def _parse_raw(self, raw: str) -> LLMVerdict:
        data = json.loads(raw.strip())
        missing = _REQUIRED_FIELDS - data.keys()
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        sev_raw = data["severity"]
        try:
            severity = Severity(sev_raw)
        except ValueError:
            logger.warning("Unrecognised severity value %r — defaulting to UNKNOWN", sev_raw)
            severity = Severity.UNKNOWN

        return LLMVerdict(
            sanitization_present=bool(data["sanitization_present"]),
            sanitization_bypassable=data.get("sanitization_bypassable"),
            severity=severity,
            confidence=float(data["confidence"]),
            fix=str(data["fix"]),
            needs_more_context=bool(data.get("needs_more_context", False)),
            context_request=list(data.get("context_request", [])),
        )
