import asyncio
import logging

import httpx

from fennec.llm.response import Severity
from .model import Finding

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = [
    Severity.CRITICAL,
    Severity.HIGH,
    Severity.MEDIUM,
    Severity.LOW,
    Severity.FALSE_POSITIVE,
    Severity.UNKNOWN,
]

_SEVERITY_JIRA_PRIORITY = {
    Severity.CRITICAL: "Critical",
    Severity.HIGH:     "High",
    Severity.MEDIUM:   "Medium",
    Severity.LOW:      "Low",
}


def _severity_rank(sev: Severity) -> int:
    try:
        return _SEVERITY_ORDER.index(sev)
    except ValueError:
        return len(_SEVERITY_ORDER)


class JiraWebhookSender:
    """Posts security findings to a Jira webhook asynchronously.

    Configurable via a dict with keys:
      - webhook_url (required): URL to POST new ticket payloads to
      - search_url  (optional): Jira REST search endpoint for dedup check
      - auth        (optional): (email, api_token) tuple for basic auth
    """

    def __init__(
        self,
        threshold: Severity = Severity.HIGH,
    ) -> None:
        self._threshold = threshold

    async def send_async(self, findings: list[Finding], config: dict) -> None:
        """Fire-and-forget: posts qualifying findings to Jira; never raises."""
        webhook_url: str = config["webhook_url"]
        search_url: str | None = config.get("search_url")
        auth: tuple[str, str] | None = config.get("auth")

        threshold_rank = _severity_rank(self._threshold)
        qualifying = [f for f in findings if _severity_rank(f.severity) <= threshold_rank]

        async with httpx.AsyncClient() as client:
            for finding in qualifying:
                await self._post_finding(client, finding, webhook_url, search_url, auth)

    async def _post_finding(
        self,
        client: httpx.AsyncClient,
        finding: Finding,
        webhook_url: str,
        search_url: str | None,
        auth: tuple[str, str] | None,
    ) -> None:
        if search_url and await self._ticket_exists(client, finding.id, search_url, auth):
            logger.info("Jira ticket already exists for finding %s — skipping", finding.id)
            return

        payload = self._build_payload(finding)
        kwargs: dict = {"json": payload}
        if auth:
            kwargs["auth"] = auth

        try:
            resp = await client.post(webhook_url, **kwargs)
            if resp.status_code >= 300:
                logger.warning(
                    "Jira webhook POST failed for finding %s: HTTP %d",
                    finding.id,
                    resp.status_code,
                )
        except httpx.RequestError as exc:
            logger.warning("Jira webhook request error for finding %s: %s", finding.id, exc)

    @staticmethod
    async def _ticket_exists(
        client: httpx.AsyncClient,
        finding_id: str,
        search_url: str,
        auth: tuple[str, str] | None,
    ) -> bool:
        jql = f'cf[fennec_finding_id] = "{finding_id}"'
        kwargs: dict = {"params": {"jql": jql, "maxResults": 1}}
        if auth:
            kwargs["auth"] = auth
        try:
            resp = await client.get(search_url, **kwargs)
            if resp.status_code == 200:
                data = resp.json()
                return int(data.get("total", 0)) > 0
        except (httpx.RequestError, ValueError):
            pass
        return False

    @staticmethod
    def _build_payload(finding: Finding) -> dict:
        nodes = finding.taint_path.nodes
        source = nodes[0] if nodes else {}
        sink = nodes[-1] if nodes else {}
        path_str = " → ".join(n.get("name", "?") for n in nodes)
        file_ref = f"{source.get('file_path', '?')}:{source.get('line_start', '?')}"

        return {
            "summary": f"[Fennec] {finding.vuln_class.upper()} in {file_ref}",
            "description": (
                f"Taint path: {path_str}\n\n"
                f"Fix: {finding.fix}\n\n"
                f"Confidence: {finding.confidence:.0%} | Severity: {finding.severity.value}"
            ),
            "priority": _SEVERITY_JIRA_PRIORITY.get(finding.severity, "Medium"),
            "labels": ["security", "fennec", finding.vuln_class],
            "customfield_fennec_finding_id": finding.id,
            "customfield_fennec_taint_path": path_str,
        }
