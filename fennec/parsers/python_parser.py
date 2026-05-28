import logging

from tree_sitter_languages import get_parser as ts_get_parser

from .base import CallRef, FunctionDef, ImportDef, ParseError, ParseResult

logger = logging.getLogger(__name__)

_FUNC_TYPES = frozenset({"function_definition", "async_function_definition"})


class PythonParser:
    def __init__(self) -> None:
        self._parser = ts_get_parser("python")

    def parse_file(self, file_path: str, content: str) -> ParseResult:
        encoded = bytes(content, "utf-8")
        tree = self._parser.parse(encoded)
        root = tree.root_node

        errors: list[ParseError] = []
        if root.has_error:
            errors = _collect_error_nodes(root, content)

        functions: list[FunctionDef] = []
        _visit(root, file_path, encoded, functions, parent_func=None, class_name=None)

        imports = _extract_imports(root, encoded)

        return ParseResult(
            file_path=file_path,
            language="python",
            functions=functions,
            imports=imports,
            errors=errors,
        )


# ------------------------------------------------------------------ #
# Tree traversal                                                       #
# ------------------------------------------------------------------ #

def _visit(
    node,
    file_path: str,
    src: bytes,
    results: list[FunctionDef],
    parent_func: FunctionDef | None,
    class_name: str | None,
) -> None:
    if node.type in _FUNC_TYPES:
        name_node = node.child_by_field_name("name")
        name = src[name_node.start_byte:name_node.end_byte].decode() if name_node else "?"

        if parent_func is None:
            # Top-level function or class method → new FunctionDef
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
                _visit(body, file_path, src, results, fn, class_name)
        else:
            # Nested function → attach its body's calls to the enclosing scope
            body = node.child_by_field_name("body")
            if body:
                _visit(body, file_path, src, results, parent_func, class_name)
        return

    if node.type == "class_definition":
        name_node = node.child_by_field_name("name")
        cls_name = src[name_node.start_byte:name_node.end_byte].decode() if name_node else "?"
        body = node.child_by_field_name("body")
        if body:
            _visit(body, file_path, src, results, None, cls_name)
        return

    if node.type == "call" and parent_func is not None:
        func_node = node.child_by_field_name("function")
        if func_node:
            callee_name = _extract_callee_name(func_node, src)
            parent_func.calls.append(
                CallRef(callee_name=callee_name, line=node.start_point[0] + 1)
            )
        # Fall through to recurse into arguments (handles nested calls like f(g()))

    for child in node.children:
        _visit(child, file_path, src, results, parent_func, class_name)


def _extract_callee_name(func_node, src: bytes) -> str:
    if func_node.type == "identifier":
        return src[func_node.start_byte:func_node.end_byte].decode()
    if func_node.type == "attribute":
        attr = func_node.child_by_field_name("attribute")
        if attr:
            return src[attr.start_byte:attr.end_byte].decode()
    return src[func_node.start_byte:func_node.end_byte].decode()[:64]


def _extract_imports(root, src: bytes) -> list[ImportDef]:
    imports: list[ImportDef] = []
    _collect_imports(root, src, imports)
    return imports


def _collect_imports(node, src: bytes, out: list[ImportDef]) -> None:
    if node.type == "import_statement":
        # import foo, import foo as bar
        for child in node.children:
            if child.type == "dotted_name":
                out.append(ImportDef(
                    module=src[child.start_byte:child.end_byte].decode(),
                    line=node.start_point[0] + 1,
                ))
            elif child.type == "aliased_import":
                name_n = child.child_by_field_name("name")
                alias_n = child.child_by_field_name("alias")
                if name_n:
                    out.append(ImportDef(
                        module=src[name_n.start_byte:name_n.end_byte].decode(),
                        alias=src[alias_n.start_byte:alias_n.end_byte].decode() if alias_n else None,
                        line=node.start_point[0] + 1,
                    ))
        return

    if node.type == "import_from_statement":
        # from foo import bar, baz
        mod_n = node.child_by_field_name("module_name")
        module = src[mod_n.start_byte:mod_n.end_byte].decode() if mod_n else "?"
        for child in node.children:
            if child.type == "dotted_name":
                if child == mod_n:
                    continue
                out.append(ImportDef(
                    module=src[child.start_byte:child.end_byte].decode(),
                    from_module=module,
                    line=node.start_point[0] + 1,
                ))
            elif child.type == "aliased_import":
                name_n = child.child_by_field_name("name")
                alias_n = child.child_by_field_name("alias")
                if name_n:
                    out.append(ImportDef(
                        module=src[name_n.start_byte:name_n.end_byte].decode(),
                        alias=src[alias_n.start_byte:alias_n.end_byte].decode() if alias_n else None,
                        from_module=module,
                        line=node.start_point[0] + 1,
                    ))
        return

    for child in node.children:
        _collect_imports(child, src, out)


def _collect_error_nodes(root, content: str) -> list[ParseError]:
    errors: list[ParseError] = []

    def walk(node):
        if node.type == "ERROR" or node.is_missing:
            errors.append(ParseError(
                message=f"Syntax error near '{content[node.start_byte:node.end_byte][:40]}'",
                line=node.start_point[0] + 1,
            ))
        for child in node.children:
            walk(child)

    walk(root)
    return errors
