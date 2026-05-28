import os
from dataclasses import replace

import anthropic

from .response import LLMVerdict, ResponseParser

DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_MAX_TOKENS = 1024


class LLMClient:
    """Thin wrapper around the Anthropic SDK for single-shot vulnerability analysis.

    In single-shot mode (agent_loop_enabled=False), the needs_more_context flag
    from the LLM is silently cleared — the verdict is accepted as-is and the
    caller does not iterate.

    When agent_loop_enabled=True, the flag is passed through; the caller (agent
    loop) is responsible for fetching more context and re-invoking.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        agent_loop_enabled: bool = False,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self._model = model
        self._agent_loop_enabled = agent_loop_enabled
        self._max_tokens = max_tokens

    def analyze(self, prompt: str) -> str:
        """Send a prompt and return the raw response string."""
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    def analyze_and_parse(self, prompt: str) -> LLMVerdict:
        """Single-shot analyze + parse with automatic retry on malformed responses.

        If agent_loop_enabled is False, clears needs_more_context before returning
        so callers do not need to check the flag.
        """
        raw = self.analyze(prompt)
        parser = ResponseParser()
        verdict = parser.parse(raw, retry_fn=self.analyze)

        if not self._agent_loop_enabled and verdict.needs_more_context:
            verdict = replace(verdict, needs_more_context=False)

        return verdict
