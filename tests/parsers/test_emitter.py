"""Task 6.6: GraphEmitter unit tests and integration test."""

import os
from unittest.mock import MagicMock, call, patch

import pytest

from fennec.graph.schema import EdgeType
from fennec.parsers.base import CallRef, FunctionDef, ImportDef, ParseResult
from fennec.parsers.emitter import GraphEmitter, make_function_id


def _make_result(functions=None, imports=None) -> ParseResult:
    return ParseResult(
        file_path="app.py",
        language="python",
        functions=functions or [],
        imports=imports or [],
    )


def _make_fn(name: str, calls: list[str] | None = None) -> FunctionDef:
    fn = FunctionDef(name=name, file_path="app.py", line_start=1, line_end=5)
    for c in (calls or []):
        fn.calls.append(CallRef(callee_name=c))
    return fn


# ------------------------------------------------------------------ #
# Stable function ID                                                  #
# ------------------------------------------------------------------ #

def test_same_inputs_same_id():
    a = make_function_id("repo", "a.py", "foo", "python")
    b = make_function_id("repo", "a.py", "foo", "python")
    assert a == b


def test_different_file_different_id():
    a = make_function_id("repo", "a.py", "foo", "python")
    b = make_function_id("repo", "b.py", "foo", "python")
    assert a != b


def test_id_is_16_hex_chars():
    fn_id = make_function_id("r", "f.py", "fn", "python")
    assert len(fn_id) == 16


# ------------------------------------------------------------------ #
# Emit unit tests (mocked GraphClient)                                #
# ------------------------------------------------------------------ #

def _make_mock_client():
    client = MagicMock()
    client.upsert_function = MagicMock()
    client.upsert_file = MagicMock()
    client.upsert_module = MagicMock()
    client.add_edge = MagicMock()
    return client


def test_upsert_function_called_for_each_function():
    client = _make_mock_client()
    emitter = GraphEmitter(client, "repo-1")
    result = _make_result(functions=[_make_fn("foo"), _make_fn("bar"), _make_fn("baz")])

    emitter.emit(result)

    assert client.upsert_function.call_count == 3


def test_defined_in_edge_emitted_for_each_function():
    client = _make_mock_client()
    emitter = GraphEmitter(client, "repo-1")
    result = _make_result(functions=[_make_fn("foo"), _make_fn("bar")])

    emitter.emit(result)

    defined_in_calls = [
        c for c in client.add_edge.call_args_list
        if c.args[2] == EdgeType.DEFINED_IN
    ]
    assert len(defined_in_calls) == 2


def test_calls_edge_emitted_for_intra_file_call():
    client = _make_mock_client()
    emitter = GraphEmitter(client, "repo-1")
    result = _make_result(functions=[_make_fn("caller", calls=["callee"]), _make_fn("callee")])

    emitter.emit(result)

    calls_edges = [
        c for c in client.add_edge.call_args_list
        if c.args[2] == EdgeType.CALLS
    ]
    assert len(calls_edges) == 1


def test_cross_file_call_not_emitted():
    client = _make_mock_client()
    emitter = GraphEmitter(client, "repo-1")
    result = _make_result(functions=[_make_fn("caller", calls=["external_fn"])])

    emitter.emit(result)

    calls_edges = [
        c for c in client.add_edge.call_args_list
        if c.args[2] == EdgeType.CALLS
    ]
    assert len(calls_edges) == 0


def test_imports_edge_emitted():
    client = _make_mock_client()
    emitter = GraphEmitter(client, "repo-1")
    imports = [ImportDef(module="os"), ImportDef(module="sys")]
    result = _make_result(imports=imports)

    emitter.emit(result)

    imports_edges = [
        c for c in client.add_edge.call_args_list
        if c.args[2] == EdgeType.IMPORTS
    ]
    assert len(imports_edges) == 2


def test_emit_idempotent_same_function_twice():
    client = _make_mock_client()
    emitter = GraphEmitter(client, "repo-1")
    result = _make_result(functions=[_make_fn("foo")])

    emitter.emit(result)
    emitter.emit(result)

    # upsert_function called twice (idempotency is handled by graph-db-schema MERGE)
    assert client.upsert_function.call_count == 2


# ------------------------------------------------------------------ #
# Integration test: parse Python file → emit → check counts          #
# (requires running Neo4j — opt-in via FENNEC_INTEGRATION_TESTS=1)   #
# ------------------------------------------------------------------ #

_PYTHON_FIXTURE = """\
def get_user(user_id):
    raw = fetch_from_db(user_id)
    return sanitize(raw)

def fetch_from_db(uid):
    return db.query(uid)

def sanitize(value):
    return value.strip()
"""


@pytest.mark.skipif(
    os.getenv("FENNEC_INTEGRATION_TESTS") != "1",
    reason="Set FENNEC_INTEGRATION_TESTS=1 to run live graph tests",
)
def test_parse_and_emit_python_file():
    import os as _os
    from fennec.graph.client import GraphClient
    from fennec.parsers.python_parser import PythonParser

    uri = _os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = _os.getenv("NEO4J_USER", "neo4j")
    password = _os.getenv("NEO4J_PASSWORD", "fennecpassword")

    with GraphClient(uri, user, password) as client:
        # Clear test data
        with client._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

        parser = PythonParser()
        result = parser.parse_file("app.py", _PYTHON_FIXTURE)
        emitter = GraphEmitter(client, "test-repo")
        emitter.emit(result)

        with client._driver.session() as session:
            fn_count = session.run("MATCH (f:Function) RETURN count(f) AS n").single()["n"]
            edge_count = session.run("MATCH ()-[r:DEFINED_IN]->() RETURN count(r) AS n").single()["n"]

        assert fn_count == 3, f"Expected 3 functions, got {fn_count}"
        assert edge_count == 3, f"Expected 3 DEFINED_IN edges, got {edge_count}"
