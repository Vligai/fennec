"""Task 2.3: detect_language tests."""

from fennec.parsers.detector import SUPPORTED_LANGUAGES, detect_language


# --- Extension-based ---

def test_py_extension_detects_python():
    assert detect_language("app.py") == "python"


def test_ts_extension_detects_typescript():
    assert detect_language("utils.ts") == "typescript"


def test_tsx_extension_detects_typescript():
    assert detect_language("App.tsx") == "typescript"


def test_js_extension_detects_javascript():
    assert detect_language("index.js") == "javascript"


def test_go_extension_detects_go():
    assert detect_language("main.go") == "go"


# --- Shebang fallback ---

def test_shebang_python3_detected():
    content = "#!/usr/bin/env python3\nprint('hello')"
    assert detect_language("script", content) == "python"


def test_shebang_node_detected():
    content = "#!/usr/bin/env node\nconsole.log('hi')"
    assert detect_language("script", content) == "javascript"


def test_unknown_extension_with_python_shebang():
    content = "#!/usr/bin/env python\nx = 1"
    assert detect_language("myscript", content) == "python"


# --- Unsupported / unknown ---

def test_ruby_extension_returns_ruby_not_supported():
    lang = detect_language("app.rb")
    assert lang == "ruby"
    assert lang not in SUPPORTED_LANGUAGES


def test_unknown_extension_no_shebang_returns_none():
    assert detect_language("Makefile", "") is None


def test_supported_languages_set():
    assert "python" in SUPPORTED_LANGUAGES
    assert "javascript" in SUPPORTED_LANGUAGES
    assert "typescript" in SUPPORTED_LANGUAGES
    assert "go" in SUPPORTED_LANGUAGES
    assert "ruby" not in SUPPORTED_LANGUAGES
