## 1. Setup

- [x] 1.1 Add `tree-sitter` and `tree-sitter-languages` to project dependencies
- [x] 1.2 Create `fennec/parsers/` package with `__init__.py`, `base.py`, `detector.py`, `emitter.py`
- [x] 1.3 Define `ParseResult`, `FunctionDef`, `CallRef`, `ImportDef`, `ParseError` dataclasses in `base.py`
- [x] 1.4 Define `LanguageParser` protocol in `base.py`

## 2. Language Detection

- [x] 2.1 Implement `detect_language(file_path, content)` with extension lookup table
- [x] 2.2 Add shebang fallback: parse first line for `#!/usr/bin/env <lang>` patterns
- [x] 2.3 Write unit tests: `.py` → `python`, `.ts` → `typescript`, unknown extension with shebang, skip unsupported

## 3. Python Parser

- [x] 3.1 Implement `PythonParser` using tree-sitter: extract function defs, method defs, call refs, imports
- [x] 3.2 Handle nested functions: attach to nearest enclosing function scope
- [x] 3.3 Handle partial parse: return `ParseResult` with errors for files with syntax issues
- [x] 3.4 Write parser tests against representative Python fixtures (plain function, class, decorator, lambda)

## 4. JavaScript / TypeScript Parser

- [x] 4.1 Implement `JavaScriptParser` for `.js` files using `tree-sitter-javascript`
- [x] 4.2 Extend to `TypeScriptParser` for `.ts`/`.tsx` using `tree-sitter-typescript`
- [x] 4.3 Flag dynamic dispatch calls (`obj[key]()`) as `resolved=false`
- [x] 4.4 Implement minified file detection (avg line length > 500 chars → skip)
- [x] 4.5 Write parser tests: arrow functions, class methods, dynamic dispatch, minified skip

## 5. Go Parser

- [x] 5.1 Implement `GoParser` using `tree-sitter-go`: extract func declarations, method receivers, call expressions
- [x] 5.2 Write parser tests: package-level func, method on struct, goroutine call

## 6. Graph Emitter

- [x] 6.1 Implement `GraphEmitter.emit(parse_result)` — translates `ParseResult` → graph upsert calls
- [x] 6.2 Implement stable function ID generation: `sha256(repo_id + file_path + func_name + language)[:16]`
- [x] 6.3 Emit `DEFINED_IN` edges from each function to its file node
- [x] 6.4 Emit `CALLS` edges from `CallRef` entries
- [x] 6.5 Emit `IMPORTS` edges from `ImportDef` entries
- [x] 6.6 Write integration test: parse a Python file end-to-end and verify graph node/edge counts
