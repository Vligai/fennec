"""Task 4.5: JavaScript/TypeScript parser tests."""

import pytest
from fennec.parsers.javascript_parser import JavaScriptParser, TypeScriptParser

js_parser = JavaScriptParser()
ts_parser = TypeScriptParser()


def js_parse(code: str, path: str = "test.js"):
    return js_parser.parse_file(path, code)


def ts_parse(code: str, path: str = "test.ts"):
    return ts_parser.parse_file(path, code)


# --- Arrow functions ---

def test_arrow_function_extracted():
    code = "const greet = (name) => {\n    return `Hello ${name}`;\n};\n"
    result = js_parse(code)
    assert len(result.functions) >= 1


# --- Class methods ---

def test_class_method_extracted():
    code = """\
class UserService {
    getUser(id) {
        return fetchUser(id);
    }
}
"""
    result = js_parse(code)
    names = {f.name for f in result.functions}
    assert "getUser" in names
    fn = next(f for f in result.functions if f.name == "getUser")
    assert fn.is_method
    assert fn.class_name == "UserService"


# --- Call refs ---

def test_call_refs_in_function():
    code = """\
function process(data) {
    const clean = sanitize(data);
    return save(clean);
}
"""
    result = js_parse(code)
    fn = result.functions[0]
    callee_names = {c.callee_name for c in fn.calls}
    assert "sanitize" in callee_names
    assert "save" in callee_names


# --- Dynamic dispatch flagged as unresolved ---

def test_dynamic_dispatch_flagged_unresolved():
    code = """\
function callDynamic(obj, key) {
    obj[key]();
}
"""
    result = js_parse(code)
    fn = result.functions[0]
    dynamic = [c for c in fn.calls if not c.resolved]
    assert len(dynamic) >= 1


# --- Minified file detection ---

def test_minified_file_skipped():
    # A single very long line to simulate minification
    long_line = "x" * 600
    result = js_parse(long_line + "\n", path="bundle.min.js")
    assert any(e.message == "skipped_minified" for e in result.errors)
    assert result.functions == []


def test_non_minified_file_not_skipped():
    code = "function hello() { return 1; }\n"
    result = js_parse(code)
    assert not any(e.message == "skipped_minified" for e in result.errors)


# --- TypeScript ---

def test_typescript_function_extracted():
    code = """\
function add(a: number, b: number): number {
    return a + b;
}
"""
    result = ts_parse(code)
    assert len(result.functions) == 1
    assert result.functions[0].name == "add"
    assert result.language == "typescript"


def test_typescript_class_method():
    code = """\
class Auth {
    login(user: string, pass: string): boolean {
        return validate(user, pass);
    }
}
"""
    result = ts_parse(code)
    assert any(f.name == "login" for f in result.functions)
