## ADDED Requirements

### Requirement: Function definition extraction
The system SHALL extract all top-level function and class method definitions from a source file.

#### Scenario: Python function extracted
- **WHEN** a Python file containing `def my_func(x, y):` is parsed
- **THEN** a `FunctionDef` is returned with `name="my_func"`, correct `line_start` and `line_end`

#### Scenario: Class method extracted
- **WHEN** a class method is defined inside a class body
- **THEN** a `FunctionDef` is returned for each method with the method's own line range

### Requirement: Call reference extraction
The system SHALL extract all function calls made within each function body.

#### Scenario: Direct call extracted
- **WHEN** a function body contains `result = sanitize(user_input)`
- **THEN** a `CallRef` is recorded in the enclosing function's `calls` list with `callee_name="sanitize"`

#### Scenario: Unresolvable dynamic call flagged
- **WHEN** a function body contains a dynamic dispatch that cannot be statically resolved (e.g., `obj[key]()`)
- **THEN** the call is recorded as a `CallRef` with `resolved=false` rather than being silently dropped

### Requirement: Import statement extraction
The system SHALL extract all import statements from a file.

#### Scenario: Python import extracted
- **WHEN** a Python file contains `import os` or `from pathlib import Path`
- **THEN** an `ImportDef` is recorded with the module name and any aliases

### Requirement: Parse error handling
The system SHALL return a partial `ParseResult` with errors listed rather than raising an exception when a file contains syntax errors.

#### Scenario: Syntax error in file
- **WHEN** a file with a syntax error is parsed
- **THEN** `ParseResult.errors` is non-empty
- **THEN** any successfully parsed functions before the error are still returned

### Requirement: Minified file skip
The system SHALL skip JavaScript/TypeScript files where the average line length exceeds 500 characters, treating them as minified.

#### Scenario: Minified JS skipped
- **WHEN** a JavaScript file has lines averaging over 500 characters
- **THEN** the file is skipped and logged as `skipped_minified`
