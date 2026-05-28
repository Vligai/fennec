"""Task 4.2: compute_path_hash tests — same IDs same hash, different IDs different hash, order-insensitive."""

from fennec.signal.store import compute_path_hash


def test_same_ids_produce_same_hash():
    ids = ["fn:a.py:foo", "fn:b.py:bar", "fn:c.py:baz"]
    assert compute_path_hash(ids) == compute_path_hash(ids)


def test_order_insensitive():
    ids = ["fn:a.py:foo", "fn:b.py:bar"]
    assert compute_path_hash(ids) == compute_path_hash(list(reversed(ids)))


def test_different_ids_produce_different_hash():
    assert compute_path_hash(["fn:a.py:foo"]) != compute_path_hash(["fn:b.py:bar"])


def test_single_id():
    h = compute_path_hash(["fn:only.py:func"])
    assert isinstance(h, str)
    assert len(h) == 64  # sha256 hex digest


def test_empty_list_is_stable():
    assert compute_path_hash([]) == compute_path_hash([])
