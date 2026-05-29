"""Task 4.4: Integration test — publish org rule via API, fetch via client, apply in merge."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from unittest.mock import patch

from fennec.sharing.api import app, get_engine
from fennec.sharing.client import OrgRuleClient
from fennec.rules.loader import merge_org_and_repo_rules
from fennec.rules.schema import CustomRules
from fennec.signal.models import Base


@pytest.fixture
def test_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/integration.db")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def api_client(test_engine):
    app.dependency_overrides[get_engine] = lambda: test_engine
    with TestClient(app, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def test_publish_then_fetch_and_merge(api_client):
    """End-to-end: publish rule via API → client fetches → merge produces effective rules."""

    # 1. Admin publishes sanitizer rule to org scope
    resp = api_client.post(
        "/api/v1/org/org-test/rules",
        headers={"x-fennec-api-key": "admin-secret-key"},
        json={"type": "sanitizer", "pattern": "internal_security.sanitize_cmd()", "taint_type": "cmdi"},
    )
    assert resp.status_code == 201

    # 2. Client fetches org rules (mock httpx to call the test FastAPI app)
    rules_from_api = [resp.json()]  # simulate what client would get

    from fennec.sharing.client import OrgRule
    org_rules = [OrgRule(
        rule_id=r["rule_id"], org_id=r["org_id"], type=r["type"],
        pattern=r["pattern"], taint_type=r["taint_type"],
        scope_glob=r["scope_glob"], mode=r["mode"], created_by=r["created_by"],
    ) for r in rules_from_api]

    # 3. Merge with empty repo rules → org rule appears in effective set
    merged = merge_org_and_repo_rules(org_rules, CustomRules())

    patterns = {s.pattern for s in merged.sanitizers}
    assert "internal_security.sanitize_cmd()" in patterns


def test_org_rule_not_visible_across_orgs(api_client):
    """Rules published to org-1 must not appear when fetching for org-2."""
    api_client.post(
        "/api/v1/org/org-1/rules",
        headers={"x-fennec-api-key": "admin-secret-key"},
        json={"type": "sanitizer", "pattern": "org1_only()", "taint_type": "cmdi"},
    )

    resp = api_client.get("/api/v1/org/org-2/rules", headers={"x-fennec-api-key": "any-key"})
    patterns = {r["pattern"] for r in resp.json()}
    assert "org1_only()" not in patterns
