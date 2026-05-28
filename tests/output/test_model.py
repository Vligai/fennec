"""Task 1.4: Finding ID generation and deduplication tests."""

from fennec.output.model import deduplicate_findings, generate_finding_id
from tests.output.conftest import make_finding


# --- ID generation ---

def test_same_input_same_id():
    id1 = generate_finding_id("sqli", "abc123")
    id2 = generate_finding_id("sqli", "abc123")
    assert id1 == id2


def test_different_vuln_class_different_id():
    sqli_id = generate_finding_id("sqli", "abc123")
    cmdi_id = generate_finding_id("cmdi", "abc123")
    assert sqli_id != cmdi_id


def test_different_path_hash_different_id():
    id1 = generate_finding_id("sqli", "hash_a")
    id2 = generate_finding_id("sqli", "hash_b")
    assert id1 != id2


def test_id_is_16_hex_chars():
    finding_id = generate_finding_id("sqli", "somepath")
    assert len(finding_id) == 16
    assert all(c in "0123456789abcdef" for c in finding_id)


# --- Deduplication ---

def test_dedup_removes_duplicate_findings():
    f1 = make_finding(vuln_class="sqli", path_hash="same_hash")
    f2 = make_finding(vuln_class="sqli", path_hash="same_hash")
    # Both have the same ID since same vuln_class + path_hash
    assert f1.id == f2.id

    result = deduplicate_findings([f1, f2])
    assert len(result) == 1


def test_dedup_keeps_distinct_findings():
    f1 = make_finding(vuln_class="sqli", path_hash="hash_a")
    f2 = make_finding(vuln_class="sqli", path_hash="hash_b")
    f3 = make_finding(vuln_class="cmdi", path_hash="hash_a")

    result = deduplicate_findings([f1, f2, f3])
    assert len(result) == 3


def test_dedup_preserves_first_occurrence():
    f1 = make_finding(vuln_class="sqli", path_hash="same", confidence=0.9)
    f2 = make_finding(vuln_class="sqli", path_hash="same", confidence=0.5)

    result = deduplicate_findings([f1, f2])
    assert result[0].confidence == 0.9


def test_dedup_empty_list():
    assert deduplicate_findings([]) == []
