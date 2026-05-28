"""Task 2.4: GitHubCommentPoster unit tests — create and update-in-place."""

import json
from unittest.mock import MagicMock, patch, call

import pytest

from fennec.ci.github import GitHubCommentPoster
from fennec.output.pr_comment import MARKER


def _make_poster() -> GitHubCommentPoster:
    return GitHubCommentPoster(token="gh-test-token", repo="owner/repo")


def _comment(body: str, comment_id: int = 1) -> dict:
    return {"id": comment_id, "body": body}


# --- New comment created when none exists ---

def test_creates_new_comment_when_none_exists():
    poster = _make_poster()

    list_resp = MagicMock(status_code=200)
    list_resp.json.return_value = []  # no existing comments
    list_resp.raise_for_status = MagicMock()

    create_resp = MagicMock(status_code=201)
    create_resp.raise_for_status = MagicMock()

    with patch("fennec.ci.github.httpx.Client") as mock_client_cls:
        client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = client
        client.get.return_value = list_resp
        client.post.return_value = create_resp

        poster.post_pr_comment([], pr_number=42)

    client.post.assert_called_once()
    post_call_kwargs = client.post.call_args
    assert "/issues/42/comments" in post_call_kwargs.args[0]
    body = post_call_kwargs.kwargs["json"]["body"]
    assert MARKER in body


# --- Existing comment updated on re-run ---

def test_updates_existing_comment_on_rerun():
    poster = _make_poster()
    existing_body = f"{MARKER}\n## Fennec old scan"

    list_resp = MagicMock(status_code=200)
    list_resp.json.return_value = [_comment(existing_body, comment_id=99)]
    list_resp.raise_for_status = MagicMock()

    patch_resp = MagicMock(status_code=200)
    patch_resp.raise_for_status = MagicMock()

    with patch("fennec.ci.github.httpx.Client") as mock_client_cls:
        client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = client
        client.get.return_value = list_resp
        client.patch.return_value = patch_resp

        poster.post_pr_comment([], pr_number=42)

    # Must update, not create
    client.post.assert_not_called()
    client.patch.assert_called_once()
    patch_url = client.patch.call_args.args[0]
    assert "/comments/99" in patch_url


# --- Comment without marker is not mistaken for Fennec comment ---

def test_non_fennec_comment_not_updated():
    poster = _make_poster()

    list_resp = MagicMock(status_code=200)
    list_resp.json.return_value = [_comment("Some other comment without the marker", 7)]
    list_resp.raise_for_status = MagicMock()

    create_resp = MagicMock(status_code=201)
    create_resp.raise_for_status = MagicMock()

    with patch("fennec.ci.github.httpx.Client") as mock_client_cls:
        client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = client
        client.get.return_value = list_resp
        client.post.return_value = create_resp

        poster.post_pr_comment([], pr_number=5)

    client.post.assert_called_once()
    client.patch.assert_not_called()
