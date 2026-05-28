"""Task 3.6: CRUD operation tests against a live Neo4j instance."""

import pytest
from fennec.graph import GraphClient, EdgeType


def _query_one(client: GraphClient, cypher: str, **params) -> dict | None:
    with client._driver.session() as session:
        result = session.run(cypher, **params)
        record = result.single()
        return dict(record[0]) if record else None


def _count(client: GraphClient, cypher: str, **params) -> int:
    with client._driver.session() as session:
        result = session.run(cypher, **params)
        record = result.single()
        return record[0] if record else 0


# --- upsert_function ---

def test_upsert_function_creates_new(client):
    client.upsert_function({
        "id": "fn:a.py:foo",
        "name": "foo",
        "file_path": "a.py",
        "line_start": 1,
        "line_end": 10,
        "language": "python",
    })
    node = _query_one(client, "MATCH (f:Function {id: $id}) RETURN f", id="fn:a.py:foo")
    assert node is not None
    assert node["name"] == "foo"
    assert node["file_path"] == "a.py"


def test_upsert_function_updates_existing(client):
    props = {"id": "fn:a.py:foo", "name": "foo", "file_path": "a.py"}
    client.upsert_function(props)
    client.upsert_function({**props, "line_start": 99})
    node = _query_one(client, "MATCH (f:Function {id: $id}) RETURN f", id="fn:a.py:foo")
    assert node["line_start"] == 99
    count = _count(client, "MATCH (f:Function {id: $id}) RETURN count(f)", id="fn:a.py:foo")
    assert count == 1


# --- upsert_file ---

def test_upsert_file_creates_and_updates(client):
    client.upsert_file({"id": "file:a.py", "path": "a.py", "language": "python", "repo_id": "repo1"})
    node = _query_one(client, "MATCH (f:File {id: $id}) RETURN f", id="file:a.py")
    assert node["path"] == "a.py"

    client.upsert_file({"id": "file:a.py", "path": "a.py", "language": "python", "repo_id": "repo1", "last_parsed_commit": "abc123"})
    node = _query_one(client, "MATCH (f:File {id: $id}) RETURN f", id="file:a.py")
    assert node["last_parsed_commit"] == "abc123"
    count = _count(client, "MATCH (f:File {id: $id}) RETURN count(f)", id="file:a.py")
    assert count == 1


# --- upsert_module ---

def test_upsert_module(client):
    client.upsert_module({"id": "mod:utils", "name": "utils", "language": "python", "file_path": "utils.py"})
    node = _query_one(client, "MATCH (m:Module {id: $id}) RETURN m", id="mod:utils")
    assert node["name"] == "utils"


# --- add_edge ---

def _make_two_functions(client):
    client.upsert_function({"id": "fn:a.py:foo", "name": "foo", "file_path": "a.py"})
    client.upsert_function({"id": "fn:b.py:bar", "name": "bar", "file_path": "b.py"})


def test_add_calls_edge(client):
    _make_two_functions(client)
    client.add_edge("fn:a.py:foo", "fn:b.py:bar", EdgeType.CALLS, {"call_site_line": 5})
    count = _count(
        client,
        "MATCH (:Function {id: $a})-[r:CALLS]->(:Function {id: $b}) RETURN count(r)",
        a="fn:a.py:foo", b="fn:b.py:bar",
    )
    assert count == 1


def test_add_data_flow_edge(client):
    _make_two_functions(client)
    client.add_edge("fn:a.py:foo", "fn:b.py:bar", EdgeType.DATA_FLOW, {"variable": "user_input"})
    count = _count(
        client,
        "MATCH (:Function {id: $a})-[r:DATA_FLOW]->(:Function {id: $b}) RETURN count(r)",
        a="fn:a.py:foo", b="fn:b.py:bar",
    )
    assert count == 1


def test_add_edge_rejects_invalid_type(client):
    _make_two_functions(client)
    with pytest.raises(ValueError):
        client.add_edge("fn:a.py:foo", "fn:b.py:bar", "INVALID")  # type: ignore[arg-type]


# --- delete_file_edges ---

def test_delete_file_edges_removes_calls_and_data_flow(client):
    _make_two_functions(client)
    client.add_edge("fn:a.py:foo", "fn:b.py:bar", EdgeType.CALLS)
    client.add_edge("fn:a.py:foo", "fn:b.py:bar", EdgeType.DATA_FLOW)

    client.delete_file_edges("a.py")

    remaining = _count(
        client,
        "MATCH (:Function {file_path: 'a.py'})-[r:CALLS|DATA_FLOW]->() RETURN count(r)",
    )
    assert remaining == 0


def test_delete_file_edges_preserves_function_nodes(client):
    _make_two_functions(client)
    client.add_edge("fn:a.py:foo", "fn:b.py:bar", EdgeType.CALLS)

    client.delete_file_edges("a.py")

    node = _query_one(client, "MATCH (f:Function {id: 'fn:a.py:foo'}) RETURN f")
    assert node is not None


# --- prune_orphan_functions ---

def test_prune_orphan_functions(client):
    client.upsert_function({"id": "fn:a.py:orphan", "name": "orphan", "file_path": "a.py"})
    client.upsert_function({"id": "fn:b.py:kept", "name": "kept", "file_path": "b.py"})
    client.upsert_file({"id": "file:b.py", "path": "b.py"})
    client.add_edge("fn:b.py:kept", "file:b.py", EdgeType.DEFINED_IN)

    client.prune_orphan_functions()

    orphan = _query_one(client, "MATCH (f:Function {id: 'fn:a.py:orphan'}) RETURN f")
    kept = _query_one(client, "MATCH (f:Function {id: 'fn:b.py:kept'}) RETURN f")
    assert orphan is None
    assert kept is not None
