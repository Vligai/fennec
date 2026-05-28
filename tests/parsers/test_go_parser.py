"""Task 5.2: GoParser tests."""

from fennec.parsers.go_parser import GoParser

parser = GoParser()


def go_parse(code: str, path: str = "main.go"):
    return parser.parse_file(path, code)


# --- Package-level function ---

def test_package_level_func_extracted():
    code = """\
package main

func main() {
    fmt.Println("hello")
}
"""
    result = go_parse(code)
    assert any(f.name == "main" for f in result.functions)


# --- Method on struct ---

def test_method_on_struct_extracted():
    code = """\
package main

type Server struct{}

func (s *Server) Start() {
    listen()
}
"""
    result = go_parse(code)
    method = next((f for f in result.functions if f.name == "Start"), None)
    assert method is not None
    assert method.is_method
    assert "Server" in (method.class_name or "")


# --- Call expressions ---

def test_call_expressions_extracted():
    code = """\
package main

func process(data string) {
    cleaned := sanitize(data)
    store(cleaned)
}
"""
    result = go_parse(code)
    fn = next(f for f in result.functions if f.name == "process")
    callee_names = {c.callee_name for c in fn.calls}
    assert "sanitize" in callee_names
    assert "store" in callee_names


# --- Method call via selector ---

def test_selector_call_extracted():
    code = """\
package main

func run(db *DB) {
    db.Connect()
}
"""
    result = go_parse(code)
    fn = result.functions[0]
    callee_names = {c.callee_name for c in fn.calls}
    assert "Connect" in callee_names


# --- Imports ---

def test_imports_extracted():
    code = """\
package main

import (
    "fmt"
    "net/http"
)

func main() {}
"""
    result = go_parse(code)
    modules = {i.module for i in result.imports}
    assert "fmt" in modules
    assert "net/http" in modules


# --- Goroutine call ---

def test_goroutine_call_attached_to_parent():
    code = """\
package main

func server() {
    go func() {
        handle()
    }()
}
"""
    result = go_parse(code)
    fn = next((f for f in result.functions if f.name == "server"), None)
    assert fn is not None
    callee_names = {c.callee_name for c in fn.calls}
    assert "handle" in callee_names
