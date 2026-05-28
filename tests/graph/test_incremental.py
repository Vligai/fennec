"""Task 5.4: Two-commit scenario — only changed-file edges are updated."""

import os

import pytest
from fennec.graph import GraphClient, EdgeType


def _setup_two_files(client: GraphClient) -> None:
    """Populate graph with two files, each with a function and a CALLS edge."""
    client.upsert_file({"id": "file:alpha.py", "path": "alpha.py", "last_parsed_commit": "commit-v1"})
    client.upsert_file({"id": "file:beta.py",  "path": "beta.py",  "last_parsed_commit": "commit-v1"})

    client.upsert_function({"id": "fn:alpha:a", "name": "a", "file_path": "alpha.py"})
    client.upsert_function({"id": "fn:alpha:b", "name": "b", "file_path": "alpha.py"})
    client.upsert_function({"id": "fn:beta:c",  "name": "c", "file_path": "beta.py"})
    client.upsert_function({"id": "fn:beta:d",  "name": "d", "file_path": "beta.py"})

    client.add_edge("fn:alpha:a", "fn:alpha:b", EdgeType.CALLS)
    client.add_edge("fn:beta:c",  "fn:beta:d",  EdgeType.CALLS)


def _edge_count(client: GraphClient, file_path: str) -> int:
    with client._driver.session() as session:
        result = session.run(
            "MATCH (:Function {file_path: $fp})-[r:CALLS|DATA_FLOW]->() RETURN count(r) AS n",
            fp=file_path,
        )
        return result.single()["n"]


def test_incremental_update_only_touches_changed_file(client):
    _setup_two_files(client)

    assert _edge_count(client, "alpha.py") == 1
    assert _edge_count(client, "beta.py") == 1

    to_reparse = client.incremental_update(["alpha.py"], "commit-v2")

    assert "alpha.py" in to_reparse
    assert "beta.py" not in to_reparse
    assert _edge_count(client, "alpha.py") == 0   # edges deleted
    assert _edge_count(client, "beta.py") == 1    # untouched


def test_incremental_update_skips_same_commit(client):
    _setup_two_files(client)

    # alpha.py is at commit-v1; passing commit-v1 again must skip it
    to_reparse = client.incremental_update(["alpha.py"], "commit-v1")

    assert to_reparse == []
    assert _edge_count(client, "alpha.py") == 1   # edges intact


def test_full_repo_scan_clears_graph(client, tmp_path):
    _setup_two_files(client)

    # full_repo_scan clears all nodes
    client.full_repo_scan(str(tmp_path))

    with client._driver.session() as session:
        count = session.run("MATCH (n) RETURN count(n) AS n").single()["n"]
    assert count == 0


def test_full_repo_scan_returns_source_files(client, tmp_path):
    (tmp_path / "main.py").write_text("")
    (tmp_path / "util.go").write_text("")
    (tmp_path / "README.md").write_text("")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "helper.ts").write_text("")

    files = client.full_repo_scan(str(tmp_path))
    basenames = {os.path.basename(f) for f in files}
    assert "main.py" in basenames
    assert "util.go" in basenames
    assert "helper.ts" in basenames
    assert "README.md" not in basenames
