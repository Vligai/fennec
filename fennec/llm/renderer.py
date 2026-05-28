import logging
from dataclasses import dataclass

from fennec.graph.queries import TaintPath
from .templates import BASE_TEMPLATE, VULN_CLASS_METADATA

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONTEXT_CHARS = 80_000


@dataclass
class FunctionSource:
    """Source code record for a single function, provided by the context assembler."""

    name: str
    file_path: str
    line_start: int
    line_end: int
    body: str


class PromptRenderer:
    def __init__(self, max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS) -> None:
        self._max_context_chars = max_context_chars

    def render(
        self,
        taint_path: TaintPath,
        context_slice: list[FunctionSource],
        vuln_class: str,
    ) -> str:
        """Assemble the final LLM prompt from a taint path, context, and vuln class.

        Raises ValueError for unrecognised vuln_class values.
        """
        if vuln_class not in VULN_CLASS_METADATA:
            raise ValueError(
                f"Unsupported vuln_class: {vuln_class!r}. "
                f"Supported: {sorted(VULN_CLASS_METADATA)}"
            )

        meta = VULN_CLASS_METADATA[vuln_class]
        return BASE_TEMPLATE.format(
            vuln_label=meta["label"],
            taint_path_section=self._format_taint_path(taint_path),
            context_section=self._format_context(context_slice, taint_path),
            guidance=meta["guidance"],
        )

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _format_taint_path(self, taint_path: TaintPath) -> str:
        nodes = taint_path.nodes
        if not nodes:
            return "  (empty path)"

        lines: list[str] = []
        for i, node in enumerate(nodes):
            name = node.get("name") or node.get("id", "?")
            ref = f"{node.get('file_path', '?')}:{node.get('line_start', '?')}"
            if i == 0:
                lines.append(f"  Source: {name} [{ref}]")
            elif i == len(nodes) - 1:
                lines.append(f"  → Sink: {name} [{ref}]")
            else:
                lines.append(f"  → {name} [{ref}]")

        return "\n".join(lines)

    def _format_context(self, context_slice: list[FunctionSource], taint_path: TaintPath) -> str:
        if not context_slice:
            return "(no context provided)"

        total = sum(len(fn.body) for fn in context_slice)
        if total <= self._max_context_chars:
            return self._render_functions(context_slice)

        return self._truncate_context(context_slice, taint_path)

    def _truncate_context(
        self,
        context_slice: list[FunctionSource],
        taint_path: TaintPath,
    ) -> str:
        nodes = taint_path.nodes
        source_name = nodes[0].get("name") if nodes else None
        sink_name = nodes[-1].get("name") if nodes else None

        must_keep: list[FunctionSource] = []
        optionals: list[FunctionSource] = []
        for fn in context_slice:
            if fn.name in {source_name, sink_name}:
                must_keep.append(fn)
            else:
                optionals.append(fn)

        budget = self._max_context_chars - sum(len(fn.body) for fn in must_keep)
        included = list(must_keep)
        removed = 0

        for fn in optionals:
            if len(fn.body) <= budget:
                included.append(fn)
                budget -= len(fn.body)
            else:
                removed += 1

        if removed:
            logger.info(
                "Context truncated: %d function(s) pruned to fit %d-char context window",
                removed,
                self._max_context_chars,
            )

        return self._render_functions(included)

    @staticmethod
    def _render_functions(fns: list[FunctionSource]) -> str:
        parts: list[str] = []
        for fn in fns:
            header = f"# {fn.name} [{fn.file_path}:{fn.line_start}-{fn.line_end}]"
            parts.append(f"{header}\n{fn.body}")
        return "\n\n".join(parts)
