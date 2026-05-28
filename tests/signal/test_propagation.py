"""Task 5.3: Propagation integration tests.

Scenario A: 3 false_positive verdicts across 2 services → trust propagated org-wide.
Scenario B: 3 false_positive verdicts from 1 service → NOT propagated.
Also verifies wont_fix is excluded from trust score denominator.
"""

import pytest
from fennec.signal.propagation import PropagationJob
from fennec.signal.store import SignalStore
from tests.signal.conftest import make_verdict


@pytest.fixture
def job(store):
    return PropagationJob(store)


def _write_fps(store, count: int, pattern: str, services: list[str], org_id: str = "org-1") -> None:
    for i in range(count):
        svc = services[i % len(services)]
        store.write_verdict(make_verdict(
            verdict="false_positive",
            pattern_fingerprint=pattern,
            service_id=svc,
            org_id=org_id,
            path_hash=f"hash-{pattern}-{i}",
        ))


# --- Cross-service propagation ---

def test_propagation_across_two_services(store, job):
    """3 FP verdicts across 2 services → org-scoped trust written."""
    _write_fps(store, 3, "safe_escape()", ["svc-a", "svc-b"])

    job.run("org-1")

    scores = store.get_trust_scores("org-1")
    assert "safe_escape()" in scores
    assert scores["safe_escape()"] == pytest.approx(1.0)


def test_no_propagation_single_service(store, job):
    """3 FP verdicts from a single service → NOT propagated org-wide."""
    _write_fps(store, 3, "local_escape()", ["svc-a", "svc-a", "svc-a"])

    job.run("org-1")

    scores = store.get_trust_scores("org-1")
    assert "local_escape()" not in scores


def test_propagation_below_threshold_not_propagated(store, job):
    """2 FP verdicts across 2 services (below threshold=3) → not propagated."""
    _write_fps(store, 2, "weak_escape()", ["svc-a", "svc-b"])

    job.run("org-1")

    scores = store.get_trust_scores("org-1")
    assert "weak_escape()" not in scores


# --- Trust score computation ---

def test_trust_score_excludes_wont_fix(store, job):
    """Trust score denominator only counts non-wont_fix verdicts."""
    pattern = "mixed_pattern()"
    # 3 FP across 2 services (qualifies for propagation)
    _write_fps(store, 3, pattern, ["svc-a", "svc-b"])
    # 1 real_vuln — counted in denominator
    store.write_verdict(make_verdict(verdict="real_vuln", pattern_fingerprint=pattern, org_id="org-1"))
    # 5 wont_fix — must be excluded from denominator
    for i in range(5):
        store.write_verdict(make_verdict(
            verdict="wont_fix", pattern_fingerprint=pattern,
            org_id="org-1", path_hash=f"wf-{i}",
        ))

    job.run("org-1")

    scores = store.get_trust_scores("org-1")
    assert pattern in scores
    # fp_count=3, total_non_wont_fix=4 → 3/4 = 0.75
    assert scores[pattern] == pytest.approx(0.75)


# --- Idempotency ---

def test_propagation_is_idempotent(store, job):
    """Running the propagation job twice produces the same result."""
    _write_fps(store, 3, "stable_escape()", ["svc-a", "svc-b"])

    job.run("org-1")
    first = store.get_trust_scores("org-1").copy()
    job.run("org-1")
    second = store.get_trust_scores("org-1")

    assert first == second


# --- Org isolation ---

def test_propagation_is_org_scoped(store, job):
    """Verdicts in org-1 do not produce trust entries in org-2."""
    _write_fps(store, 3, "org_escape()", ["svc-a", "svc-b"], org_id="org-1")

    job.run("org-1")

    assert store.get_trust_scores("org-2") == {}
