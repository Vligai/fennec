import logging

from tree_sitter_languages import get_parser as ts_get_parser

from .base import CallRef, FunctionDef, ImportDef, ParseError, ParseResult

logger = logging.getLogger(__name__)


class GoParser:
    def __init__(self) -> None:
        self._parser = ts_get_parser("go")

    def parse_file(self, file_path: str, content: str) -> ParseResult:
        src = bytes(content, "utf-8")
        tree = self._parser.parse(src)
        root = tree.root_node

        errors: list[ParseError] = []
        if root.has_error:
            errors = [ParseError(message="Syntax error")]

        functions: list[FunctionDef] = []
        _go_visit(root, file_path, src, functions, parent_func=None)

        imports = _go_extract_imports(root, src)

        return ParseResult(
            file_path=file_path,
            language="go",
            functions=functions,
            imports=imports,
            errors=errors,
        )


def _go_visit(node, file_path: str, src: bytes,
              results: list[FunctionDef], parent_func: FunctionDef | None) -> None:

    if node.type == "function_declaration":
        name_node = node.child_by_field_name("name")
        name = src[name_node.start_byte:name_node.end_byte].decode() if name_node else "?"
        fn = FunctionDef(
            name=name,
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )
        results.append(fn)
        body = node.child_by_field_name("body")
        if body:
            _go_visit(body, file_path, src, results, fn)
        return

    if node.type == "method_declaration":
        name_node = node.child_by_field_name("name")
        name = src[name_node.start_byte:name_node.end_byte].decode() if name_node else "?"
        # Receiver type as class_name
        recv = node.child_by_field_name("receiver")
        class_name: str | None = None
        if recv:
            # Receiver param list: extract the type name
            for child in recv.children:
                if child.type == "parameter_declaration":
                    type_n = child.child_by_field_name("type")
                    if type_n:
                        type_text = src[type_n.start_byte:type_n.end_byte].decode().lstrip("*")
                        class_name = type_text
                        break
        fn = FunctionDef(
            name=name,
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            is_method=True,
            class_name=class_name,
        )
        results.append(fn)
        body = node.child_by_field_name("body")
        if body:
            _go_visit(body, file_path, src, results, fn)
        return

    if node.type == "call_expression" and parent_func is not None:
        func_node = node.child_by_field_name("function")
        if func_node:
            callee = _go_callee_name(func_node, src)
            parent_func.calls.append(CallRef(callee_name=callee, line=node.start_point[0] + 1))

    if node.type == "func_literal" and parent_func is not None:
        # goroutine or inline func literal — calls attach to enclosing function
        body = node.child_by_field_name("body")
        if body:
            _go_visit(body, file_path, src, results, parent_func)
        return

    for child in node.children:
        _go_visit(child, file_path, src, results, parent_func)


def _go_callee_name(func_node, src: bytes) -> str:
    if func_node.type == "identifier":
        return src[func_node.start_byte:func_node.end_byte].decode()
    if func_node.type == "selector_expression":
        field_n = func_node.child_by_field_name("field")
        if field_n:
            return src[field_n.start_byte:field_n.end_byte].decode()
    return src[func_node.start_byte:func_node.end_byte].decode()[:64]


def _go_extract_imports(root, src: bytes) -> list[ImportDef]:
    imports: list[ImportDef] = []

    def walk(node):
        if node.type == "import_spec":
            # path is a string literal
            path_n = node.child_by_field_name("path")
            if path_n:
                module = src[path_n.start_byte:path_n.end_byte].decode().strip('"')
                alias_n = node.child_by_field_name("name")
                alias = src[alias_n.start_byte:alias_n.end_byte].decode() if alias_n else None
                imports.append(ImportDef(module=module, alias=alias, line=node.start_point[0] + 1))
            return
        for child in node.children:
            walk(child)

    walk(root)
    return imports
