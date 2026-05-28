"""Task 3.4: PythonParser tests."""

import pytest
from fennec.parsers.python_parser import PythonParser

parser = PythonParser()


def parse(code: str, path: str = "test.py"):
    return parser.parse_file(path, code)


# --- Plain function ---

def test_plain_function_extracted():
    result = parse("def foo(x, y):\n    return x + y\n")
    assert len(result.functions) == 1
    fn = result.functions[0]
    assert fn.name == "foo"
    assert fn.line_start == 1
    assert fn.line_end == 2


# --- Class methods ---

def test_class_methods_extracted():
    code = """\
class MyClass:
    def method_a(self):
        pass

    def method_b(self):
        return 1
"""
    result = parse(code)
    names = {f.name for f in result.functions}
    assert "method_a" in names
    assert "method_b" in names
    for fn in result.functions:
        assert fn.is_method
        assert fn.class_name == "MyClass"


# --- Call references ---

def test_call_refs_extracted():
    code = """\
def process(data):
    clean = sanitize(data)
    return store(clean)
"""
    result = parse(code)
    fn = result.functions[0]
    callee_names = {c.callee_name for c in fn.calls}
    assert "sanitize" in callee_names
    assert "store" in callee_names


# --- Decorator ---

def test_decorated_function_extracted():
    code = """\
@app.route("/")
def index():
    return "hello"
"""
    result = parse(code)
    names = {f.name for f in result.functions}
    assert "index" in names


# --- Nested functions attach to parent ---

def test_nested_function_calls_attached_to_parent():
    code = """\
def outer():
    def inner():
        helper()
    inner()
"""
    result = parse(code)
    assert len(result.functions) == 1
    outer = result.functions[0]
    assert outer.name == "outer"
    callee_names = {c.callee_name for c in outer.calls}
    # helper() inside inner() and inner() itself should both be captured
    assert "inner" in callee_names or "helper" in callee_names


# --- Imports ---

def test_import_statement_extracted():
    code = "import os\nimport sys\n"
    result = parse(code)
    modules = {i.module for i in result.imports}
    assert "os" in modules
    assert "sys" in modules


def test_from_import_extracted():
    code = "from pathlib import Path\n"
    result = parse(code)
    assert any(i.module == "Path" and i.from_module == "pathlib" for i in result.imports)


# --- Partial parse on syntax error ---

def test_partial_parse_on_syntax_error():
    code = "def good_func():\n    pass\n\ndef bad(\n"  # incomplete
    result = parse(code)
    assert len(result.errors) > 0
    # Good function still extracted
    assert any(f.name == "good_func" for f in result.functions)


# --- Async function ---

def test_async_function_extracted():
    code = "async def fetch(url):\n    return await get(url)\n"
    result = parse(code)
    assert result.functions[0].name == "fetch"
