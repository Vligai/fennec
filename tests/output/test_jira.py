"""Task 4.6: JiraWebhookSender tests — threshold filter, dedup, failure logging."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fennec.llm.response import Severity
from fennec.output.jira import JiraWebhookSender
from tests.output.conftest import make_finding

pytestmark = pytest.mark.asyncio


_CONFIG = {
    "webhook_url": "https://jira.example.com/webhook",
    "search_url": "https://jira.example.com/rest/api/2/search",
    "auth": ("user@example.com", "token"),
}


def _mock_response(status: int, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data or {}
    return resp


# --- Severity threshold filter ---

async def test_high_severity_finding_is_posted():
    sender = JiraWebhookSender(threshold=Severity.HIGH)
    finding = make_finding(severity=Severity.HIGH)

    with patch("fennec.output.jira.httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = client
        client.get = AsyncMock(return_value=_mock_response(200, {"total": 0}))
        client.post = AsyncMock(return_value=_mock_response(201))

        await sender.send_async([finding], _CONFIG)

    client.post.assert_awaited_once()


async def test_low_severity_finding_below_threshold_not_posted():
    sender = JiraWebhookSender(threshold=Severity.HIGH)
    finding = make_finding(severity=Severity.LOW)

    with patch("fennec.output.jira.httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = client
        client.get = AsyncMock(return_value=_mock_response(200, {"total": 0}))
        client.post = AsyncMock(return_value=_mock_response(201))

        await sender.send_async([finding], _CONFIG)

    client.post.assert_not_awaited()


async def test_critical_severity_always_posted_when_threshold_high():
    sender = JiraWebhookSender(threshold=Severity.HIGH)
    finding = make_finding(severity=Severity.CRITICAL)

    with patch("fennec.output.jira.httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = client
        client.get = AsyncMock(return_value=_mock_response(200, {"total": 0}))
        client.post = AsyncMock(return_value=_mock_response(201))

        await sender.send_async([finding], _CONFIG)

    client.post.assert_awaited_once()


# --- Dedup: existing ticket blocks POST ---

async def test_dedup_skips_post_when_ticket_exists():
    sender = JiraWebhookSender()
    finding = make_finding(severity=Severity.HIGH)

    with patch("fennec.output.jira.httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = client
        # Search returns existing ticket
        client.get = AsyncMock(return_value=_mock_response(200, {"total": 1}))
        client.post = AsyncMock(return_value=_mock_response(201))

        await sender.send_async([finding], _CONFIG)

    client.post.assert_not_awaited()


async def test_dedup_posts_when_no_existing_ticket():
    sender = JiraWebhookSender()
    finding = make_finding(severity=Severity.HIGH)

    with patch("fennec.output.jira.httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = client
        client.get = AsyncMock(return_value=_mock_response(200, {"total": 0}))
        client.post = AsyncMock(return_value=_mock_response(201))

        await sender.send_async([finding], _CONFIG)

    client.post.assert_awaited_once()


# --- Failure handling ---

async def test_non_2xx_response_logs_warning_not_raises(caplog):
    import logging
    sender = JiraWebhookSender()
    finding = make_finding(severity=Severity.HIGH)

    config_no_search = {"webhook_url": _CONFIG["webhook_url"]}

    with patch("fennec.output.jira.httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = client
        client.post = AsyncMock(return_value=_mock_response(503))

        with caplog.at_level(logging.WARNING, logger="fennec.output.jira"):
            await sender.send_async([finding], config_no_search)

    assert "503" in caplog.text
    # Must not raise


async def test_request_error_logs_warning_not_raises(caplog):
    import logging
    import httpx
    sender = JiraWebhookSender()
    finding = make_finding(severity=Severity.HIGH)

    config_no_search = {"webhook_url": _CONFIG["webhook_url"]}

    with patch("fennec.output.jira.httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = client
        client.post = AsyncMock(side_effect=httpx.RequestError("connection refused"))

        with caplog.at_level(logging.WARNING, logger="fennec.output.jira"):
            await sender.send_async([finding], config_no_search)

    assert "connection refused" in caplog.text
