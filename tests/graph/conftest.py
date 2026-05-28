import os

import pytest
from neo4j import GraphDatabase

from fennec.graph import GraphClient

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "fennecpassword")


def _drop_all_constraints_and_indexes(driver) -> None:
    with driver.session() as session:
        constraints = session.run("SHOW CONSTRAINTS").data()
        for c in constraints:
            session.run(f"DROP CONSTRAINT {c['name']} IF EXISTS")
        indexes = session.run("SHOW INDEXES").data()
        for idx in indexes:
            if idx.get("type") != "LOOKUP":  # built-in lookup indexes cannot be dropped
                session.run(f"DROP INDEX {idx['name']} IF EXISTS")


@pytest.fixture
def neo4j_driver():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    yield driver
    driver.close()


@pytest.fixture
def clean_db(neo4j_driver):
    """Clear all nodes and edges before each test."""
    with neo4j_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    yield neo4j_driver


@pytest.fixture
def empty_db(neo4j_driver):
    """Drop all constraints, indexes, and data — for schema init tests."""
    _drop_all_constraints_and_indexes(neo4j_driver)
    with neo4j_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    yield neo4j_driver


@pytest.fixture
def client(clean_db):
    c = GraphClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    yield c
    c.close()
