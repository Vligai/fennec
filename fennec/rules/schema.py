from __future__ import annotations

from enum import Enum
from pathlib import PurePath

from pydantic import BaseModel, Field


class RuleMode(str, Enum):
    ADVISORY = "advisory"
    BLOCKING = "blocking"


class RuleScope(BaseModel):
    paths: list[str] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)
    mode: RuleMode = RuleMode.ADVISORY

    def matches_file(self, file_path: str) -> bool:
        """Return True if file_path is in scope.

        Patterns are evaluated in order; negation patterns (prefixed with !)
        override previous positive matches (gitignore semantics).
        """
        if not self.paths:
            return True
        matched = False
        for pattern in self.paths:
            if pattern.startswith("!"):
                if PurePath(file_path).match(pattern[1:]):
                    matched = False
            else:
                if PurePath(file_path).match(pattern):
                    matched = True
        return matched


class _BaseRule(BaseModel):
    pattern: str
    scope: RuleScope = Field(default_factory=RuleScope)

    def matches_file(self, file_path: str) -> bool:
        return self.scope.matches_file(file_path)

    def is_blocking(self) -> bool:
        return self.scope.mode == RuleMode.BLOCKING


class SourceRule(_BaseRule):
    type: str  # e.g. "user_input", "external_data"


class SinkRule(_BaseRule):
    type: str  # e.g. "sqli", "cmdi"


class SanitizerRule(_BaseRule):
    covers: str  # vuln class: "cmdi", "sqli", etc.


class NamedRule(BaseModel):
    name: str
    mode: RuleMode = RuleMode.ADVISORY
    branches: list[str] = Field(default_factory=list)


class RuleOverride(BaseModel):
    """Repo-level suppression of an inherited org rule."""
    pattern: str
    action: str  # "disable"


class CustomRules(BaseModel):
    sources: list[SourceRule] = Field(default_factory=list)
    sinks: list[SinkRule] = Field(default_factory=list)
    sanitizers: list[SanitizerRule] = Field(default_factory=list)
    rules: list[NamedRule] = Field(default_factory=list)
    overrides: list[RuleOverride] = Field(default_factory=list)
