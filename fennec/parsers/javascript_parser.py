import logging

from tree_sitter_languages import get_parser as ts_get_parser

from .base import CallRef, FunctionDef, ImportDef, ParseError, ParseResult

logger = logging.getLogger(__name__)

_FUNC_TYPES = frozenset({
    "function_declaration",
    "function_expression",
    "generator_function_declaration",
    "generator_function",
})
_ARROW_FUNC = "arrow_function"
_METHOD_DEF = "method_definition"

_MINIFIED_LINE_THRESHOLD = 500


def _is_minified(content: str) -> bool:
    lines = [l for l in content.split("\n") if l.strip()]
    if not lines:
        return False
    return sum(len(l) for l in lines) / len(lines) > _MINIFIED_LINE_THRESHOLD


class JavaScriptParser:
    _LANGUAGE = "javascript"

    def __init__(self) -> None:
        self._parser = ts_get_parser(self._LANGUAGE)

    def parse_file(self, file_path: str, content: str) -> ParseResult:
        if _is_minified(content):
            logger.info("Skipping minified file: %s", file_path)
            return ParseResult(
                file_path=file_path,
                language="javascript",
                errors=[ParseError(message="skipped_minified")],
            )

        src = bytes(content, "utf-8")
        tree = self._parser.parse(src)
        root = tree.root_node

        errors: list[ParseError] = []
        if root.has_error:
            errors = [ParseError(message="Syntax error", line=None)]

        functions: list[FunctionDef] = []
        _js_visit(root, file_path, src, functions, parent_func=None, class_name=None)

        imports = _js_extract_imports(root, src)

        return ParseResult(
            file_path=file_path,
            language="javascript",
            functions=functions,
            imports=imports,
            errors=errors,
        )


class TypeScriptParser(JavaScriptParser):
    _LANGUAGE = "typescript"

    def parse_file(self, file_path: str, content: str) -> ParseResult:
        result = super().parse_file(file_path, content)
        # Re-tag the language field
        result.language = "typescript"
        return result


class TypeScriptXParser(JavaScriptParser):
    _LANGUAGE = "tsx"

    def parse_file(self, file_path: str, content: str) -> ParseResult:
        result = super().parse_file(file_path, content)
        result.language = "typescript"
        return result


# ------------------------------------------------------------------ #
# Tree traversal (shared by JS and TS)                                #
# ------------------------------------------------------------------ #

def _js_visit(node, file_path: str, src: bytes, results: list[FunctionDef],
              parent_func: FunctionDef | None, class_name: str | None) -> None:

    if node.type in _FUNC_TYPES:
        name_node = node.child_by_field_name("name")
        name = src[name_node.start_byte:name_node.end_byte].decode() if name_node else "(anonymous)"

        if parent_func is None:
            fn = FunctionDef(
                name=name,
                file_path=file_path,
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                is_method=(class_name is not None),
                class_name=class_name,
            )
            results.append(fn)
            body = node.child_by_field_name("body")
            if body:
                _js_visit(body, file_path, src, results, fn, class_name)
        else:
            body = node.child_by_field_name("body")
            if body:
                _js_visit(body, file_path, src, results, parent_func, class_name)
        return

    if node.type == _ARROW_FUNC and parent_func is None:
        # Top-level arrow function assigned to a variable
        fn = FunctionDef(
            name="(arrow)",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )
        results.append(fn)
        body = node.child_by_field_name("body")
        if body:
            _js_visit(body, file_path, src, results, fn, class_name)
        return

    if node.type == "class_declaration":
        name_node = node.child_by_field_name("name")
        cls = src[name_node.start_byte:name_node.end_byte].decode() if name_node else "?"
        body = node.child_by_field_name("body")
        if body:
            _js_visit(body, file_path, src, results, None, cls)
        return

    if node.type == _METHOD_DEF:
        name_node = node.child_by_field_name("name")
        name = src[name_node.start_byte:name_node.end_byte].decode() if name_node else "?"
        fn = FunctionDef(
            name=name,
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            is_method=True,
            class_name=class_name,
        )
        results.append(fn)
        body = node.child_by_field_name("value")
        if body:
            _js_visit(body, file_path, src, results, fn, class_name)
        return

    if node.type == "call_expression" and parent_func is not None:
        func_node = node.child_by_field_name("function")
        if func_node:
            resolved = func_node.type != "subscript_expression"
            callee_name = _js_callee_name(func_node, src)
            parent_func.calls.append(
                CallRef(callee_name=callee_name, line=node.start_point[0] + 1, resolved=resolved)
            )

    for child in node.children:
        _js_visit(child, file_path, src, results, parent_func, class_name)


def _js_callee_name(func_node, src: bytes) -> str:
    if func_node.type == "identifier":
        return src[func_node.start_byte:func_node.end_byte].decode()
    if func_node.type == "member_expression":
        prop = func_node.child_by_field_name("property")
        if prop:
            return src[prop.start_byte:prop.end_byte].decode()
    if func_node.type == "subscript_expression":
        return "[dynamic]"
    return src[func_node.start_byte:func_node.end_byte].decode()[:64]


def _js_extract_imports(root, src: bytes) -> list[ImportDef]:
    imports: list[ImportDef] = []

    def walk(node):
        if node.type == "import_statement":
            source = node.child_by_field_name("source")
            if source:
                module = src[source.start_byte:source.end_byte].decode().strip("'\"")
                imports.append(ImportDef(module=module, line=node.start_point[0] + 1))
            return
        for child in node.children:
            walk(child)

    walk(root)
    return imports
