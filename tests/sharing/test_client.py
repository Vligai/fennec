"""Task 2.3: OrgRuleClient cache tests — hit skips API, miss fetches, error uses stale cache."""

import time
from unittest.mock import MagicMock, patch

import pytest
import httpx

from fennec.sharing.client import OrgRule, OrgRuleClient

_RULE = {"rule_id": "r1", "org_id": "org-1", "type": "sanitizer",
         "pattern": "sanitize()", "taint_type": "cmdi",
         "scope_glob": "", "mode": "advisory", "created_by": "admin"}


def _make_resp(data: list | None = None, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = data or [_RULE]
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


# --- Cache hit skips API call ---

def test_cache_hit_skips_api_call():
    client = OrgRuleClient("http://fennec.example.com", "api-key", cache_ttl=300)

    with patch("fennec.sharing.client.httpx.Client") as mock_cls:
        http = MagicMock()
        mock_cls.return_value.__enter__.return_value = http
        http.get.return_value = _make_resp()

        rules1 = client.fetch("org-1")
        rules2 = client.fetch("org-1")  # second call — should use cache

    assert http.get.call_count == 1  # only one API call
    assert len(rules1) == 1
    assert rules2 == rules1


# --- Cache miss fetches fresh data ---

def test_cache_miss_triggers_fetch():
    client = OrgRuleClient("http://fennec.example.com", "api-key", cache_ttl=0)  # TTL=0 → always expired

    with patch("fennec.sharing.client.httpx.Client") as mock_cls:
        http = MagicMock()
        mock_cls.return_value.__enter__.return_value = http
        http.get.return_value = _make_resp()

        client.fetch("org-1")
        client.fetch("org-1")

    assert http.get.call_count == 2


# --- API error uses stale cache ---

def test_api_error_uses_stale_cache():
    client = OrgRuleClient("http://fennec.example.com", "api-key", cache_ttl=0)
    # Pre-populate cache manually
    client._cache = [OrgRule(**_RULE)]
    client._cache_time = time.monotonic() - 1  # expired

    with patch("fennec.sharing.client.httpx.Client") as mock_cls:
        http = MagicMock()
        mock_cls.return_value.__enter__.return_value = http
        http.get.side_effect = httpx.RequestError("connection refused")

        rules = client.fetch("org-1")

    assert len(rules) == 1  # stale cache returned
    assert rules[0].pattern == "sanitize()"


# --- API error with no cache returns empty list ---

def test_api_error_no_cache_returns_empty():
    client = OrgRuleClient("http://fennec.example.com", "api-key", cache_ttl=300)

    with patch("fennec.sharing.client.httpx.Client") as mock_cls:
        http = MagicMock()
        mock_cls.return_value.__enter__.return_value = http
        http.get.side_effect = httpx.RequestError("connection refused")

        rules = client.fetch("org-1")

    assert rules == []


# --- Cache invalidation ---

def test_invalidate_cache():
    client = OrgRuleClient("http://fennec.example.com", "api-key", cache_ttl=300)
    client._cache = [OrgRule(**_RULE)]
    client._cache_time = time.monotonic()

    client.invalidate_cache()

    with patch("fennec.sharing.client.httpx.Client") as mock_cls:
        http = MagicMock()
        mock_cls.return_value.__enter__.return_value = http
        http.get.return_value = _make_resp()
        client.fetch("org-1")

    assert http.get.call_count == 1  # cache was cleared, fresh fetch happened
