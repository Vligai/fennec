import hashlib
import logging

from fennec.graph.client import GraphClient
from fennec.graph.schema import EdgeType
from .base import ParseResult

logger = logging.getLogger(__name__)


def make_function_id(repo_id: str, file_path: str, func_name: str, language: str) -> str:
    """Deterministic 16-char hex function ID: sha256(repo_id:file_path:func_name:language)[:16]."""
    raw = f"{repo_id}:{file_path}:{func_name}:{language}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class GraphEmitter:
    """Translates a ParseResult into graph upsert and edge calls.

    The emitter never touches the database directly — all writes go through
    the GraphClient interface defined in graph-db-schema.
    """

    def __init__(self, client: GraphClient, repo_id: str) -> None:
        self._client = client
        self._repo_id = repo_id

    def emit(self, parse_result: ParseResult) -> None:
        file_id = f"file:{self._repo_id}:{parse_result.file_path}"

        # Upsert the file node
        self._client.upsert_file({
            "id": file_id,
            "path": parse_result.file_path,
            "language": parse_result.language,
            "repo_id": self._repo_id,
        })

        # Build a name → id lookup for functions in this file (for resolving local calls)
        fn_id_by_name: dict[str, str] = {}
        for fn in parse_result.functions:
            fn_id = make_function_id(self._repo_id, fn.file_path, fn.name, parse_result.language)
            fn_id_by_name[fn.name] = fn_id

            self._client.upsert_function({
                "id": fn_id,
                "name": fn.name,
                "file_path": fn.file_path,
                "line_start": fn.line_start,
                "line_end": fn.line_end,
                "language": parse_result.language,
            })

            # DEFINED_IN edge: function → file
            self._client.add_edge(fn_id, file_id, EdgeType.DEFINED_IN)

        # CALLS edges: resolved intra-file calls only
        for fn in parse_result.functions:
            caller_id = fn_id_by_name[fn.name]
            for call in fn.calls:
                if call.callee_name in fn_id_by_name:
                    callee_id = fn_id_by_name[call.callee_name]
                    self._client.add_edge(
                        caller_id,
                        callee_id,
                        EdgeType.CALLS,
                        {"call_site_line": call.line or 0, "resolved": call.resolved},
                    )
                else:
                    logger.debug(
                        "Unresolved cross-file call %s → %s in %s (deferred to graph traversal)",
                        fn.name, call.callee_name, parse_result.file_path,
                    )

        # IMPORTS edges: file → module
        for imp in parse_result.imports:
            mod_id = f"module:{imp.module}"
            self._client.upsert_module({
                "id": mod_id,
                "name": imp.module,
                "language": parse_result.language,
                "file_path": "",
            })
            self._client.add_edge(
                file_id,
                mod_id,
                EdgeType.IMPORTS,
                {"import_alias": imp.alias or ""},
            )
