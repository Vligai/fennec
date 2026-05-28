import logging
import os
import re

logger = logging.getLogger(__name__)

_EXTENSION_MAP: dict[str, str] = {
    ".py":   "python",
    ".js":   "javascript",
    ".jsx":  "javascript",
    ".mjs":  "javascript",
    ".cjs":  "javascript",
    ".ts":   "typescript",
    ".tsx":  "typescript",
    ".go":   "go",
    ".java": "java",
    ".rb":   "ruby",
    ".c":    "c",
    ".cpp":  "cpp",
    ".cs":   "csharp",
}

_SHEBANG_MAP: dict[str, str] = {
    "python":  "python",
    "python3": "python",
    "python2": "python",
    "node":    "javascript",
    "nodejs":  "javascript",
}

SUPPORTED_LANGUAGES: frozenset[str] = frozenset({"python", "javascript", "typescript", "go"})

_SHEBANG_RE = re.compile(r"^#!.*?/(?:env\s+)?(\w+)")


def detect_language(file_path: str, content: str = "") -> str | None:
    """Detect the programming language of a file.

    Returns the detected language name (e.g. 'python', 'go') or None when
    detection is inconclusive. Does NOT filter by SUPPORTED_LANGUAGES —
    callers should check that separately.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in _EXTENSION_MAP:
        return _EXTENSION_MAP[ext]

    # Shebang fallback for extensionless files
    if content:
        first_line = content.split("\n")[0]
        m = _SHEBANG_RE.match(first_line)
        if m:
            interp = m.group(1).lower()
            if interp in _SHEBANG_MAP:
                return _SHEBANG_MAP[interp]

    return None
