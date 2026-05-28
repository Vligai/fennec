## Why

Fennec requires full AST generation (not tokenization) to produce accurate call graph and data flow edges. Language coverage defines which codebases can be scanned on day one. Deferring this decision blocks all other pipeline work.

## What Changes

- Select AST libraries per language (tree-sitter as the primary cross-language framework)
- Define the parser interface: input file → emitted graph nodes/edges
- Implement parsers for Python, JavaScript/TypeScript, and Go as the initial tier
- Define semantic chunking strategy: functions and classes as graph node boundaries
- Specify language detection logic (extension + shebang + content heuristics)

## Non-goals

- Java, C/C++, Ruby, or other languages (phase 2)
- Cross-language taint path resolution (separate open research problem)
- Parser performance optimization beyond correctness

## Capabilities

### New Capabilities

- `language-detection`: Detect language of a file from extension, shebang, and content heuristics
- `ast-parser`: Per-language AST generation producing structured function/class/import data
- `graph-emitter`: Transform parsed AST output into graph node/edge upsert calls

### Modified Capabilities

<!-- none — greenfield -->

## Impact

- Directly populates `graph-db-schema` nodes and edges; parser output schema must match graph schema
- Incremental diff mode depends on parser being re-runnable on individual files
- Language coverage list sets the scope of taint taxonomy coverage
