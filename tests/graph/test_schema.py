"""Task 2.3: empty DB → init → re-init produces no duplicates and no errors."""

import pytest
from fennec.graph import GraphClient
from tests.graph.conftest import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def _count_constraints(driver) -> int:
    with driver.session() as session:
        return len(session.run("SHOW CONSTRAINTS").data())


def _count_indexes(driver) -> int:
    with driver.session() as session:
        # Exclude built-in LOOKUP indexes
        return sum(1 for r in session.run("SHOW INDEXES").data() if r.get("type") != "LOOKUP")


def test_first_init_creates_schema(empty_db):
    before_constraints = _count_constraints(empty_db)
    before_indexes = _count_indexes(empty_db)
    assert before_constraints == 0
    assert before_indexes == 0

    client = GraphClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    client.close()

    assert _count_constraints(empty_db) == 4  # one per node label
    assert _count_indexes(empty_db) > 0


def test_reinit_is_idempotent(empty_db):
    client1 = GraphClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    client1.close()

    constraints_after_first = _count_constraints(empty_db)
    indexes_after_first = _count_indexes(empty_db)

    # Second instantiation must not duplicate anything
    client2 = GraphClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    client2.close()

    assert _count_constraints(empty_db) == constraints_after_first
    assert _count_indexes(empty_db) == indexes_after_first
