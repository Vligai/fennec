"""Task 1.5: Org rule API tests — admin can publish, non-admin rejected, fetch returns correct rules."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from fennec.sharing.api import app, get_engine, _ADMIN_API_KEYS
from fennec.signal.models import Base


@pytest.fixture
def test_engine(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(test_engine):
    app.dependency_overrides[get_engine] = lambda: test_engine
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _admin_headers() -> dict:
    # Use the known admin key from the API module
    return {"x-fennec-api-key": "admin-secret-key"}


def _user_headers() -> dict:
    return {"x-fennec-api-key": "regular-user-key"}


# --- Admin can publish ---

def test_admin_can_publish_rule(client):
    resp = client.post(
        "/api/v1/org/org-1/rules",
        headers=_admin_headers(),
        json={"type": "sanitizer", "pattern": "sanitize_cmd()", "taint_type": "cmdi"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["pattern"] == "sanitize_cmd()"
    assert data["type"] == "sanitizer"
    assert data["org_id"] == "org-1"


# --- Non-admin is rejected with 403 ---

def test_non_admin_rejected(client):
    resp = client.post(
        "/api/v1/org/org-1/rules",
        headers=_user_headers(),
        json={"type": "sanitizer", "pattern": "safe_fn()", "taint_type": "cmdi"},
    )
    assert resp.status_code == 403


# --- Unauthenticated is rejected with 401 ---

def test_unauthenticated_rejected(client):
    resp = client.post("/api/v1/org/org-1/rules", json={"type": "sanitizer", "pattern": "x()"})
    assert resp.status_code in (401, 422)  # missing header


# --- Fetch returns correct rules for org ---

def test_fetch_returns_org_rules(client):
    # Publish two rules for org-1 and one for org-2
    for pattern in ["fn_a()", "fn_b()"]:
        client.post("/api/v1/org/org-1/rules", headers=_admin_headers(),
                    json={"type": "sanitizer", "pattern": pattern, "taint_type": "cmdi"})
    client.post("/api/v1/org/org-2/rules", headers=_admin_headers(),
                json={"type": "sanitizer", "pattern": "fn_c()", "taint_type": "sqli"})

    resp = client.get("/api/v1/org/org-1/rules", headers=_user_headers())
    assert resp.status_code == 200
    rules = resp.json()
    patterns = {r["pattern"] for r in rules}
    assert "fn_a()" in patterns
    assert "fn_b()" in patterns
    assert "fn_c()" not in patterns  # belongs to org-2


def test_fetch_empty_org_returns_empty_list(client):
    resp = client.get("/api/v1/org/unknown-org/rules", headers=_user_headers())
    assert resp.status_code == 200
    assert resp.json() == []


# --- Privacy boundary: response contains no code/paths ---

def test_response_contains_only_pattern_fields(client):
    client.post("/api/v1/org/org-1/rules", headers=_admin_headers(),
                json={"type": "sanitizer", "pattern": "sanitize()", "taint_type": "cmdi"})
    resp = client.get("/api/v1/org/org-1/rules", headers=_user_headers())
    rule = resp.json()[0]
    allowed_keys = {"rule_id", "org_id", "type", "pattern", "taint_type", "scope_glob", "mode", "created_by", "created_at"}
    assert set(rule.keys()) <= allowed_keys
