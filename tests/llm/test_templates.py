"""Task 2.3: template rendering tests — each vuln class and unsupported class guard."""

import pytest
from fennec.llm.renderer import FunctionSource, PromptRenderer
from fennec.llm.templates import VULN_CLASS_METADATA
from fennec.graph.queries import TaintPath


def _simple_path() -> TaintPath:
    return TaintPath(
        nodes=[
            {"id": "fn:a.py:source", "name": "get_input", "file_path": "a.py", "line_start": 1},
            {"id": "fn:b.py:sink", "name": "execute_query", "file_path": "b.py", "line_start": 20},
        ],
        edges=[{"type": "DATA_FLOW", "variable": "user_input"}],
        sanitized=False,
        hop_count=1,
    )


def _simple_context() -> list[FunctionSource]:
    return [
        FunctionSource("get_input", "a.py", 1, 5, "def get_input():\n    return request.args['q']"),
        FunctionSource("execute_query", "b.py", 20, 25, "def execute_query(q):\n    db.execute(q)"),
    ]


renderer = PromptRenderer()


@pytest.mark.parametrize("vuln_class", list(VULN_CLASS_METADATA))
def test_each_vuln_class_renders_without_error(vuln_class):
    prompt = renderer.render(_simple_path(), _simple_context(), vuln_class)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_sqli_includes_guidance():
    prompt = renderer.render(_simple_path(), _simple_context(), "sqli")
    assert "parameterized" in prompt.lower()


def test_cmdi_includes_guidance():
    prompt = renderer.render(_simple_path(), _simple_context(), "cmdi")
    assert "shlex" in prompt


def test_unsupported_vuln_class_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported vuln_class"):
        renderer.render(_simple_path(), _simple_context(), "buffer_overflow")


def test_prompt_ends_with_json_instruction():
    prompt = renderer.render(_simple_path(), _simple_context(), "sqli")
    assert "Respond in JSON only" in prompt


def test_taint_path_source_and_sink_in_prompt():
    prompt = renderer.render(_simple_path(), _simple_context(), "sqli")
    assert "get_input" in prompt
    assert "execute_query" in prompt
    assert "Source:" in prompt
    assert "Sink:" in prompt
