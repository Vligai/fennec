## Context

AST generation requires language-specific libraries. The choice between a single cross-language framework (tree-sitter) vs. dedicated per-language libraries (ast module for Python, acorn for JS, go/ast for Go) has significant maintenance implications. We need a uniform parser interface so the graph emitter doesn't know what language it's working with.

## Goals / Non-Goals

**Goals:**
- Single parser interface across all languages
- tree-sitter as the primary AST framework (Python bindings: `tree-sitter`, grammars via `tree-sitter-languages`)
- Extract: function definitions, class definitions, function calls, import statements, variable assignments
- Emit into `graph-db-schema` schema (Function, File nodes + CALLS, DATA_FLOW, IMPORTS edges)

**Non-Goals:**
- Full type inference or type checking
- Cross-language resolution
- Parser performance benchmarking (correctness first)

## Decisions

**Decision 1: tree-sitter as the AST framework**

tree-sitter over per-language native parsers:
- Single Python API for all languages
- Incremental parsing built in (only re-parses changed regions — directly supports our diff mode)
- Grammar coverage: Python, JavaScript, TypeScript, Go, Java, Ruby all have maintained grammars
- `tree-sitter-languages` PyPI package bundles compiled grammars — no build toolchain needed

Tradeoff: tree-sitter trees are more generic (CST, not AST) and require more work to extract semantic structures. Acceptable — we write per-language extractors on top of the common tree-sitter API.

**Decision 2: Parser interface**

```python
class LanguageParser(Protocol):
    def parse_file(self, file_path: str, content: str) -> ParseResult: ...

@dataclass
class ParseResult:
    file_path: str
    language: str
    functions: List[FunctionDef]
    imports: List[ImportDef]
    errors: List[ParseError]

@dataclass
class FunctionDef:
    name: str
    file_path: str
    line_start: int
    line_end: int
    calls: List[CallRef]        # functions this function calls
    data_flows: List[FlowRef]   # variables flowing to called functions
```

The graph emitter translates `ParseResult` → graph upsert calls. Parsers never touch the graph directly.

**Decision 3: Tier 1 languages**

| Language | Tree-sitter grammar | Rationale |
|---|---|---|
| Python | `tree-sitter-python` | Core engine language; most common in target customers |
| JavaScript | `tree-sitter-javascript` | Ubiquitous web; covers Node.js backends |
| TypeScript | `tree-sitter-typescript` | TypeScript superset; same extractor with type annotation handling |
| Go | `tree-sitter-go` | Common microservice language; good source of security issues |

**Decision 4: Language detection order**

1. File extension (`.py`, `.js`, `.ts`, `.go`) — covers 95%+ of cases
2. Shebang line (`#!/usr/bin/env python3`) — for extensionless scripts
3. Content heuristics (keyword frequency) — last resort fallback

**Decision 5: Semantic chunking boundaries**

Node boundaries: top-level functions and class methods. Anonymous lambdas/arrow functions attached to their parent function's `FunctionDef`. Class bodies produce one `Function` node per method, not one node for the class.

## Cross-Component Interfaces

- **Parser → Graph emitter**: `ParseResult` dataclass (defined above)
- **Graph emitter → Graph client**: calls `graph.upsert_function()`, `graph.add_edge()` from `graph-db-schema`
- **Ingestion pipeline → Parser**: passes `(file_path, content, language_hint)` to `parse_file()`

## Risks / Trade-offs

- **DATA_FLOW edge accuracy** → Static data flow extraction without type inference is approximate. Interprocedural flows (variable passed to a function that passes it to a sink) require traversal-time inference, not parse-time. Decision: parsers emit best-effort intra-procedural data flow; cross-function flows are inferred during graph traversal.
- **JavaScript dynamic dispatch** → `obj[methodName]()` cannot be statically resolved. Flag as `unresolved_call` rather than silently dropping.
- **tree-sitter grammar quality variance** → Go grammar is more mature than TypeScript. Expect TypeScript extractor to need more edge-case handling.

## Open Questions

- Should we extract data flow edges statically at parse time or derive them from the graph traversal? (Lean toward parse-time for known patterns, traversal-time for cross-function flows.)
- How do we handle minified JS files? Skip them? (Lean toward skip with a warning.)
