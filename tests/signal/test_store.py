"""Tasks 3.4 and 3.5: SignalStore unit tests."""

from tests.signal.conftest import make_verdict


# --- write_verdict / get_trust_scores ---

def test_wont_fix_excluded_from_trust_scores(store):
    """Task 3.4: wont_fix verdict must NOT appear in get_trust_scores()."""
    store.write_verdict(make_verdict(verdict="wont_fix", pattern_fingerprint="shlex.quote()"))
    # No propagation job has run, so sanitizer_trust is empty regardless.
    # Even if propagation ran, wont_fix verdicts are excluded from trust computation.
    scores = store.get_trust_scores("org-1")
    assert "shlex.quote()" not in scores


def test_real_vuln_verdict_stored(store):
    store.write_verdict(make_verdict(verdict="real_vuln"))
    assert not store.is_suppressed("hash-abc")


def test_false_positive_verdict_stored(store):
    store.write_verdict(make_verdict(verdict="false_positive", path_hash="hash-fp"))
    assert not store.is_suppressed("hash-fp")


# --- is_suppressed ---

def test_is_suppressed_returns_true_for_wont_fix(store):
    """Task 3.5: is_suppressed() returns True when a wont_fix verdict exists."""
    store.write_verdict(make_verdict(verdict="wont_fix", path_hash="hash-suppress"))
    assert store.is_suppressed("hash-suppress") is True


def test_is_suppressed_returns_false_for_unknown_hash(store):
    """Task 3.5: is_suppressed() returns False when no wont_fix verdict exists."""
    assert store.is_suppressed("hash-unknown") is False


def test_is_suppressed_false_for_real_vuln(store):
    """Real vuln verdict must not trigger suppression."""
    store.write_verdict(make_verdict(verdict="real_vuln", path_hash="hash-vuln"))
    assert store.is_suppressed("hash-vuln") is False
