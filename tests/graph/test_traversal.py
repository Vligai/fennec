"""Task 4.5: Traversal tests — direct path, multi-hop, no path, sanitized path."""

import pytest
from fennec.graph import GraphClient, EdgeType


def _fn(client: GraphClient, fn_id: str, **extra) -> None:
    client.upsert_function({"id": fn_id, "name": fn_id, "file_path": "f.py", **extra})


def _flow(client: GraphClient, a: str, b: str) -> None:
    client.add_edge(a, b, EdgeType.DATA_FLOW, {"variable": "x"})


# --- find_taint_paths ---

def test_direct_taint_path(client):
    _fn(client, "source1", is_source=True)
    _fn(client, "sink1", is_sink=True)
    _flow(client, "source1", "sink1")

    paths = client.find_taint_paths(["source1"], ["sink1"])
    assert len(paths) == 1
    assert paths[0].hop_count == 1
    assert not paths[0].sanitized


def test_multi_hop_taint_path(client):
    _fn(client, "src")
    _fn(client, "mid")
    _fn(client, "snk")
    _flow(client, "src", "mid")
    _flow(client, "mid", "snk")

    paths = client.find_taint_paths(["src"], ["snk"])
    assert len(paths) >= 1
    assert any(p.hop_count == 2 for p in paths)
    node_ids = [n["id"] for n in paths[0].nodes]
    assert "mid" in node_ids


def test_no_path_returns_empty(client):
    _fn(client, "isolated_src")
    _fn(client, "isolated_snk")

    paths = client.find_taint_paths(["isolated_src"], ["isolated_snk"])
    assert paths == []


def test_sanitized_path_flagged(client):
    _fn(client, "san_src")
    _fn(client, "san_mid", is_sanitizer=True)
    _fn(client, "san_snk")
    _flow(client, "san_src", "san_mid")
    _flow(client, "san_mid", "san_snk")

    paths = client.find_taint_paths(["san_src"], ["san_snk"])
    assert len(paths) >= 1
    assert any(p.sanitized for p in paths)


def test_unsanitized_path_not_flagged(client):
    _fn(client, "u_src")
    _fn(client, "u_snk")
    _flow(client, "u_src", "u_snk")

    paths = client.find_taint_paths(["u_src"], ["u_snk"])
    assert len(paths) == 1
    assert not paths[0].sanitized


# --- get_neighbors ---

def test_get_neighbors_depth_1(client):
    _fn(client, "center")
    _fn(client, "neighbor_a")
    _fn(client, "neighbor_b")
    client.add_edge("center", "neighbor_a", EdgeType.CALLS)
    client.add_edge("neighbor_b", "center", EdgeType.CALLS)

    neighbors = client.get_neighbors("center", depth=1)
    ids = {n["id"] for n in neighbors}
    assert "neighbor_a" in ids
    assert "neighbor_b" in ids
    assert "center" not in ids


def test_get_neighbors_depth_2(client):
    _fn(client, "hub")
    _fn(client, "hop1")
    _fn(client, "hop2")
    client.add_edge("hub", "hop1", EdgeType.CALLS)
    client.add_edge("hop1", "hop2", EdgeType.CALLS)

    neighbors = client.get_neighbors("hub", depth=2)
    ids = {n["id"] for n in neighbors}
    assert "hop2" in ids
