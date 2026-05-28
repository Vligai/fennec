"""Task 5.4: Integration test against a real Claude model call.

Opt-in: only runs when FENNEC_INTEGRATION_TESTS=1 is set. Skipped in CI by default.
Requires ANTHROPIC_API_KEY in the environment.
"""

import os
import pytest
from fennec.graph.queries import TaintPath
from fennec.llm.client import LLMClient
from fennec.llm.renderer import FunctionSource, PromptRenderer
from fennec.llm.response import Severity

pytestmark = pytest.mark.skipif(
    os.getenv("FENNEC_INTEGRATION_TESTS") != "1",
    reason="Set FENNEC_INTEGRATION_TESTS=1 to run live model tests",
)

_FIXTURE_PATH = TaintPath(
    nodes=[
        {"id": "fn:views.py:get_user", "name": "get_user", "file_path": "views.py", "line_start": 12},
        {"id": "fn:db.py:run_query", "name": "run_query", "file_path": "db.py", "line_start": 45},
    ],
    edges=[{"type": "DATA_FLOW", "variable": "user_id"}],
    sanitized=False,
    hop_count=1,
)

_FIXTURE_CONTEXT = [
    FunctionSource(
        name="get_user",
        file_path="views.py",
        line_start=12,
        line_end=15,
        body='def get_user(request):\n    user_id = request.GET["id"]\n    return run_query(user_id)',
    ),
    FunctionSource(
        name="run_query",
        file_path="db.py",
        line_start=45,
        line_end=48,
        body='def run_query(user_id):\n    cursor.execute(f"SELECT * FROM users WHERE id={user_id}")',
    ),
]


def test_real_sqli_path_returns_verdict():
    renderer = PromptRenderer()
    prompt = renderer.render(_FIXTURE_PATH, _FIXTURE_CONTEXT, "sqli")

    client = LLMClient()
    verdict = client.analyze_and_parse(prompt)

    assert verdict.severity in {Severity.CRITICAL, Severity.HIGH}
    assert verdict.sanitization_present is False
    assert 0.0 <= verdict.confidence <= 1.0
    assert len(verdict.fix) > 0
