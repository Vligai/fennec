## ADDED Requirements

### Requirement: Extension-based language detection
The system SHALL identify the programming language of a file from its file extension.

#### Scenario: Python file detected
- **WHEN** a file with extension `.py` is submitted for language detection
- **THEN** the detected language is `python`

#### Scenario: TypeScript file detected
- **WHEN** a file with extension `.ts` or `.tsx` is submitted
- **THEN** the detected language is `typescript`

#### Scenario: Unknown extension
- **WHEN** a file with an unrecognized extension is submitted
- **THEN** the system falls back to shebang detection before returning `unknown`

### Requirement: Shebang-based detection fallback
The system SHALL read the first line of a file to detect language from a shebang directive when extension detection is inconclusive.

#### Scenario: Python shebang detected
- **WHEN** a file's first line is `#!/usr/bin/env python3` and has no recognized extension
- **THEN** the detected language is `python`

### Requirement: Unsupported language skip
The system SHALL skip files whose detected language is not in the supported language set without raising an error.

#### Scenario: Unsupported language skipped
- **WHEN** a file is detected as an unsupported language (e.g., Ruby)
- **THEN** the file is skipped and a warning is logged with the file path and detected language
