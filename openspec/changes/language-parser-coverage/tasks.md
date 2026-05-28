## 1. Setup

- [ ] 1.1 Add `tree-sitter` and `tree-sitter-languages` to project dependencies
- [ ] 1.2 Create `fennec/parsers/` package with `__init__.py`, `base.py`, `detector.py`, `emitter.py`
- [ ] 1.3 Define `ParseResult`, `FunctionDef`, `CallRef`, `ImportDef`, `ParseError` dataclasses in `base.py`
- [ ] 1.4 Define `LanguageParser` protocol in `base.py`

## 2. Language Detection

- [ ] 2.1 Implement `detect_language(file_path, content)` with extension lookup table
- [ ] 2.2 Add shebang fallback: parse first line for `#!/usr/bin/env <lang>` patterns
- [ ] 2.3 Write unit tests: `.py` → `python`, `.ts` → `typescript`, unknown extension with shebang, skip unsupported

## 3. Python Parser

- [ ] 3.1 Implement `PythonParser` using tree-sitter: extract function defs, method defs, call refs, imports
- [ ] 3.2 Handle nested functions: attach to nearest enclosing function scope
- [ ] 3.3 Handle partial parse: return `ParseResult` with errors for files with syntax issues
- [ ] 3.4 Write parser tests against representative Python fixtures (plain function, class, decorator, lambda)

## 4. JavaScript / TypeScript Parser

- [ ] 4.1 Implement `JavaScriptParser` for `.js` files using `tree-sitter-javascript`
- [ ] 4.2 Extend to `TypeScriptParser` for `.ts`/`.tsx` using `tree-sitter-typescript`
- [ ] 4.3 Flag dynamic dispatch calls (`obj[key]()`) as `resolved=false`
- [ ] 4.4 Implement minified file detection (avg line length > 500 chars → skip)
- [ ] 4.5 Write parser tests: arrow functions, class methods, dynamic dispatch, minified skip

## 5. Go Parser

- [ ] 5.1 Implement `GoParser` using `tree-sitter-go`: extract func declarations, method receivers, call expressions
- [ ] 5.2 Write parser tests: package-level func, method on struct, goroutine call

## 6. Graph Emitter

- [ ] 6.1 Implement `GraphEmitter.emit(parse_result)` — translates `ParseResult` → graph upsert calls
- [ ] 6.2 Implement stable function ID generation: `sha256(repo_id + file_path + func_name + language)[:16]`
- [ ] 6.3 Emit `DEFINED_IN` edges from each function to its file node
- [ ] 6.4 Emit `CALLS` edges from `CallRef` entries
- [ ] 6.5 Emit `IMPORTS` edges from `ImportDef` entries
- [ ] 6.6 Write integration test: parse a Python file end-to-end and verify graph node/edge counts
