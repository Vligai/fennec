import pytest
from fennec.signal.store import SignalStore


@pytest.fixture
def store():
    return SignalStore("sqlite:///:memory:")


def make_verdict(**overrides) -> dict:
    base = {
        "path_hash": "hash-abc",
        "verdict": "real_vuln",
        "reviewer_id": "reviewer-1",
        "repo_id": "repo-1",
        "service_id": "svc-a",
        "org_id": "org-1",
        "pattern_fingerprint": "shlex.quote()",
    }
    return {**base, **overrides}
