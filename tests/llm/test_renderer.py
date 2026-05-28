"""Task 3.4: PromptRenderer tests — full context intact; oversized truncates preserving source/sink."""

import pytest
from fennec.llm.renderer import FunctionSource, PromptRenderer
from fennec.graph.queries import TaintPath


def _path_with_names(source: str, sink: str, intermediaries: list[str] | None = None) -> TaintPath:
    nodes = [{"id": f"fn:{source}", "name": source, "file_path": f"{source}.py", "line_start": 1}]
    for name in (intermediaries or []):
        nodes.append({"id": f"fn:{name}", "name": name, "file_path": f"{name}.py", "line_start": 5})
    nodes.append({"id": f"fn:{sink}", "name": sink, "file_path": f"{sink}.py", "line_start": 10})
    return TaintPath(nodes=nodes, edges=[], sanitized=False, hop_count=len(nodes) - 1)


def _fn(name: str, body_size: int = 100) -> FunctionSource:
    return FunctionSource(name, f"{name}.py", 1, 10, "x" * body_size)


# --- Full context (no truncation) ---

def test_full_context_renders_intact():
    renderer = PromptRenderer(max_context_chars=10_000)
    path = _path_with_names("src", "snk")
    context = [_fn("src", 100), _fn("mid", 100), _fn("snk", 100)]

    prompt = renderer.render(path, context, "sqli")

    assert "src" in prompt
    assert "mid" in prompt
    assert "snk" in prompt


def test_multi_hop_path_all_nodes_in_prompt():
    renderer = PromptRenderer(max_context_chars=50_000)
    path = _path_with_names("src", "snk", ["hop1", "hop2", "hop3"])
    context = [_fn(n) for n in ["src", "hop1", "hop2", "hop3", "snk"]]

    prompt = renderer.render(path, context, "cmdi")

    for name in ["src", "hop1", "hop2", "hop3", "snk"]:
        assert name in prompt


# --- Oversized context (truncation) ---

def test_oversized_context_preserves_source_and_sink(caplog):
    import logging
    renderer = PromptRenderer(max_context_chars=300)
    path = _path_with_names("src", "snk")
    # source + sink = 200 chars, mid1 + mid2 would push it over 300
    context = [_fn("src", 100), _fn("mid1", 200), _fn("mid2", 200), _fn("snk", 100)]

    with caplog.at_level(logging.INFO, logger="fennec.llm.renderer"):
        prompt = renderer.render(path, context, "xss")

    assert "src" in prompt
    assert "snk" in prompt
    assert "truncated" in caplog.text.lower()


def test_truncation_removes_intermediates_not_endpoints():
    renderer = PromptRenderer(max_context_chars=250)
    path = _path_with_names("my_source", "my_sink")
    context = [_fn("my_source", 100), _fn("big_middle", 500), _fn("my_sink", 100)]

    prompt = renderer.render(path, context, "ssrf")

    assert "my_source" in prompt
    assert "my_sink" in prompt
    assert "big_middle" not in prompt


# --- Empty / edge cases ---

def test_empty_context_handled():
    renderer = PromptRenderer()
    path = _path_with_names("src", "snk")
    prompt = renderer.render(path, [], "sqli")
    assert "no context provided" in prompt


def test_empty_taint_path_handled():
    renderer = PromptRenderer()
    empty_path = TaintPath(nodes=[], edges=[], sanitized=False, hop_count=0)
    prompt = renderer.render(empty_path, [_fn("fn")], "sqli")
    assert "empty path" in prompt
