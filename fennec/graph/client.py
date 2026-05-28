import logging
import os

from neo4j import GraphDatabase, Driver

from .schema import SCHEMA_INIT_STATEMENTS, EdgeType
from .queries import (
    TaintPath,
    UPSERT_FUNCTION,
    UPSERT_FILE,
    UPSERT_MODULE,
    UPSERT_SERVICE,
    ADD_EDGE_TEMPLATE,
    DELETE_FILE_EDGES,
    PRUNE_ORPHAN_FUNCTIONS,
    GET_FILE_COMMIT,
    CLEAR_GRAPH,
    FIND_TAINT_PATHS_TEMPLATE,
    GET_NEIGHBORS_TEMPLATE,
)

logger = logging.getLogger(__name__)

_SOURCE_EXTENSIONS = frozenset(
    {".py", ".js", ".ts", ".go", ".java", ".rb", ".c", ".cpp", ".cs"}
)


class GraphClient:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        self._init_schema()

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> "GraphClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # Schema                                                               #
    # ------------------------------------------------------------------ #

    def _init_schema(self) -> None:
        with self._driver.session() as session:
            for stmt in SCHEMA_INIT_STATEMENTS:
                session.run(stmt)

    # ------------------------------------------------------------------ #
    # Node upserts                                                         #
    # ------------------------------------------------------------------ #

    def upsert_function(self, props: dict) -> None:
        fn_id = props["id"]
        fn_props = {
            "name": props["name"],
            "file_path": props["file_path"],
            "line_start": props.get("line_start"),
            "line_end": props.get("line_end"),
            "language": props.get("language", ""),
            "is_source": props.get("is_source", False),
            "is_sink": props.get("is_sink", False),
            "is_sanitizer": props.get("is_sanitizer", False),
            "taint_types": props.get("taint_types", []),
        }
        with self._driver.session() as session:
            session.run(UPSERT_FUNCTION, id=fn_id, props=fn_props)

    def upsert_file(self, props: dict) -> None:
        file_id = props["id"]
        file_props = {
            "path": props["path"],
            "language": props.get("language", ""),
            "repo_id": props.get("repo_id", ""),
            "last_parsed_commit": props.get("last_parsed_commit", ""),
        }
        with self._driver.session() as session:
            session.run(UPSERT_FILE, id=file_id, props=file_props)

    def upsert_module(self, props: dict) -> None:
        mod_id = props["id"]
        mod_props = {
            "name": props["name"],
            "language": props.get("language", ""),
            "file_path": props.get("file_path", ""),
        }
        with self._driver.session() as session:
            session.run(UPSERT_MODULE, id=mod_id, props=mod_props)

    def upsert_service(self, props: dict) -> None:
        svc_id = props["id"]
        svc_props = {
            "name": props["name"],
            "repo_id": props.get("repo_id", ""),
        }
        with self._driver.session() as session:
            session.run(UPSERT_SERVICE, id=svc_id, props=svc_props)

    # ------------------------------------------------------------------ #
    # Edge operations                                                      #
    # ------------------------------------------------------------------ #

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        edge_type: EdgeType,
        props: dict | None = None,
    ) -> None:
        if not isinstance(edge_type, EdgeType):
            raise ValueError(f"Invalid edge type: {edge_type!r}")
        query = ADD_EDGE_TEMPLATE.format(edge_type=edge_type.value)
        with self._driver.session() as session:
            session.run(query, from_id=from_id, to_id=to_id, props=props or {})

    def delete_file_edges(self, file_path: str) -> None:
        with self._driver.session() as session:
            session.run(DELETE_FILE_EDGES, file_path=file_path)

    def prune_orphan_functions(self) -> None:
        with self._driver.session() as session:
            session.run(PRUNE_ORPHAN_FUNCTIONS)

    # ------------------------------------------------------------------ #
    # Traversal queries                                                    #
    # ------------------------------------------------------------------ #

    def find_taint_paths(
        self,
        source_ids: list[str],
        sink_ids: list[str],
        max_hops: int = 10,
    ) -> list[TaintPath]:
        query = FIND_TAINT_PATHS_TEMPLATE.format(max_hops=max_hops)
        paths: list[TaintPath] = []
        with self._driver.session() as session:
            result = session.run(query, source_ids=source_ids, sink_ids=sink_ids)
            for record in result:
                neo4j_path = record["path"]
                nodes = [dict(n) for n in neo4j_path.nodes]
                edges = [
                    {"type": r.type, **dict(r)} for r in neo4j_path.relationships
                ]
                hop_count = len(neo4j_path.relationships)
                if hop_count > max_hops:
                    logger.warning("Path with %d hops exceeds max_hops=%d, skipping", hop_count, max_hops)
                    continue
                sanitized = any(n.get("is_sanitizer", False) for n in nodes)
                paths.append(TaintPath(nodes=nodes, edges=edges, sanitized=sanitized, hop_count=hop_count))
        return paths

    def get_neighbors(self, function_id: str, depth: int = 2) -> list[dict]:
        query = GET_NEIGHBORS_TEMPLATE.format(depth=depth)
        with self._driver.session() as session:
            result = session.run(query, function_id=function_id)
            return [dict(record["n"]) for record in result]

    # ------------------------------------------------------------------ #
    # Incremental update protocol                                          #
    # ------------------------------------------------------------------ #

    def incremental_update(
        self,
        changed_file_paths: list[str],
        commit_sha: str,
    ) -> list[str]:
        """Delete edges for changed files; return paths that need re-parsing.

        Skips files whose stored last_parsed_commit already matches commit_sha.
        The caller must re-parse returned files (upsert nodes/edges) and then
        call prune_orphan_functions().
        """
        to_reparse: list[str] = []
        with self._driver.session() as session:
            for fp in changed_file_paths:
                record = session.run(GET_FILE_COMMIT, path=fp).single()
                stored = record["commit"] if record else None
                if stored != commit_sha:
                    to_reparse.append(fp)

            if to_reparse:
                session.execute_write(
                    lambda tx: [tx.run(DELETE_FILE_EDGES, file_path=fp) for fp in to_reparse]
                )

        return to_reparse

    def full_repo_scan(self, repo_path: str) -> list[str]:
        """Clear the graph and return all source files in the repo.

        The caller is responsible for parsing each returned file and upserting
        the resulting nodes and edges.
        """
        with self._driver.session() as session:
            session.run(CLEAR_GRAPH)
        return _collect_source_files(repo_path)


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _collect_source_files(repo_path: str) -> list[str]:
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
        for fname in filenames:
            if os.path.splitext(fname)[1] in _SOURCE_EXTENSIONS:
                files.append(os.path.join(dirpath, fname))
    return files
