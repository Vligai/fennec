from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class CallRef:
    callee_name: str
    line: int | None = None
    resolved: bool = True


@dataclass
class FlowRef:
    variable: str
    callee_name: str
    param_index: int | None = None


@dataclass
class ImportDef:
    module: str
    alias: str | None = None
    from_module: str | None = None
    line: int | None = None


@dataclass
class FunctionDef:
    name: str
    file_path: str
    line_start: int
    line_end: int
    calls: list[CallRef] = field(default_factory=list)
    data_flows: list[FlowRef] = field(default_factory=list)
    is_method: bool = False
    class_name: str | None = None


@dataclass
class ParseError:
    message: str
    line: int | None = None


@dataclass
class ParseResult:
    file_path: str
    language: str
    functions: list[FunctionDef] = field(default_factory=list)
    imports: list[ImportDef] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)


@runtime_checkable
class LanguageParser(Protocol):
    def parse_file(self, file_path: str, content: str) -> ParseResult: ...
