"""OrgRuleClient — fetches org-scoped rules with a 5-minute local cache."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # 5 minutes


@dataclass
class OrgRule:
    """Pattern-only org rule (no code, no file paths, no taint traces)."""

    rule_id: str
    org_id: str
    type: str         # source | sink | sanitizer
    pattern: str
    taint_type: str = ""
    scope_glob: str = ""
    mode: str = "advisory"
    created_by: str = ""


class OrgRuleClient:
    """Fetches org rules from the Fennec API with a 5-minute local cache.

    Cache behaviour:
    - Within TTL: returns cached rules without an API call
    - Expired: fetches fresh rules; resets cache timer
    - API error: uses stale cache with a warning; on cache miss returns empty list
    """

    def __init__(self, base_url: str, api_key: str, cache_ttl: int = _CACHE_TTL) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._cache_ttl = cache_ttl
        self._cache: list[OrgRule] = []
        self._cache_time: float = 0.0

    def fetch(self, org_id: str) -> list[OrgRule]:
        now = time.monotonic()
        if self._cache and now - self._cache_time < self._cache_ttl:
            logger.debug("Org rule cache hit for org %s", org_id)
            return self._cache

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    f"{self._base_url}/api/v1/org/{org_id}/rules",
                    headers={"x-fennec-api-key": self._api_key},
                )
                resp.raise_for_status()
                self._cache = [OrgRule(**r) for r in resp.json()]
                self._cache_time = now
                logger.debug("Fetched %d org rule(s) for org %s", len(self._cache), org_id)
                return self._cache

        except httpx.RequestError as exc:
            logger.warning("Org rule API error (%s). %s.",
                           exc, "Using cached rules" if self._cache else "No cache available — proceeding without org rules")
            return self._cache

        except httpx.HTTPStatusError as exc:
            logger.warning("Org rule API returned HTTP %d. %s.",
                           exc.response.status_code,
                           "Using cached rules" if self._cache else "No cache — proceeding without org rules")
            return self._cache

    def invalidate_cache(self) -> None:
        self._cache = []
        self._cache_time = 0.0


def fetch_org_rules(org_id: str) -> list[OrgRule]:
    """Convenience function: fetch org rules using FENNEC_* environment variables."""
    import os
    base_url = os.getenv("FENNEC_API_URL", "")
    api_key = os.getenv("FENNEC_API_KEY", "")
    if not base_url or not api_key:
        return []
    return OrgRuleClient(base_url, api_key).fetch(org_id)
