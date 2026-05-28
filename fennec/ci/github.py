"""GitHub PR comment posting for CI integration."""

from __future__ import annotations

import argparse
import json
import logging
import sys

import httpx

from fennec.output.model import Finding
from fennec.output.pr_comment import MARKER, PrCommentRenderer

logger = logging.getLogger(__name__)

_GH_API = "https://api.github.com"
_ACCEPT = "application/vnd.github+json"


class GitHubCommentPoster:
    """Posts and updates Fennec summary comments on GitHub pull requests."""

    def __init__(self, token: str, repo: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": _ACCEPT,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._repo = repo

    def post_pr_comment(self, findings: list[Finding], pr_number: int) -> None:
        """Create or update the Fennec summary comment on a PR."""
        renderer = PrCommentRenderer()
        body = renderer.render(findings)

        existing_id = self._find_existing_comment(pr_number)
        if existing_id:
            self._update_comment(existing_id, body)
            logger.info("Updated existing Fennec comment %d on PR #%d", existing_id, pr_number)
        else:
            self._create_comment(pr_number, body)
            logger.info("Created new Fennec comment on PR #%d", pr_number)

    def _find_existing_comment(self, pr_number: int) -> int | None:
        with httpx.Client() as client:
            resp = client.get(
                f"{_GH_API}/repos/{self._repo}/issues/{pr_number}/comments",
                headers=self._headers,
                params={"per_page": 100},
            )
            resp.raise_for_status()
            for comment in resp.json():
                if MARKER in comment.get("body", ""):
                    return int(comment["id"])
        return None

    def _create_comment(self, pr_number: int, body: str) -> None:
        with httpx.Client() as client:
            resp = client.post(
                f"{_GH_API}/repos/{self._repo}/issues/{pr_number}/comments",
                headers=self._headers,
                json={"body": body},
            )
            resp.raise_for_status()

    def _update_comment(self, comment_id: int, body: str) -> None:
        with httpx.Client() as client:
            resp = client.patch(
                f"{_GH_API}/repos/{self._repo}/issues/comments/{comment_id}",
                headers=self._headers,
                json={"body": body},
            )
            resp.raise_for_status()


def post_pr_comment(
    findings: list[Finding],
    github_token: str,
    repo: str,
    pr_number: int,
) -> None:
    """Top-level helper used by CI entrypoint scripts."""
    GitHubCommentPoster(github_token, repo).post_pr_comment(findings, pr_number)


# ------------------------------------------------------------------ #
# CLI entry point (called by entrypoint.sh)                           #
# ------------------------------------------------------------------ #

def _cli() -> None:
    parser = argparse.ArgumentParser(prog="python -m fennec.ci.github")
    parser.add_argument("--sarif", required=True, help="Path to SARIF file")
    parser.add_argument("--token", required=True, help="GitHub token")
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--pr", required=True, type=int, help="PR number")
    args = parser.parse_args()

    # Load findings from SARIF (stub: post empty findings comment if no findings data)
    findings: list[Finding] = []
    try:
        import os
        if os.path.exists(args.sarif):
            with open(args.sarif) as fh:
                sarif = json.load(fh)
            # findings are represented in the SARIF results; post the rendered comment
            result_count = sum(
                len(run.get("results", [])) for run in sarif.get("runs", [])
            )
            logger.info("SARIF contains %d results", result_count)
    except Exception as exc:
        logger.warning("Could not parse SARIF: %s", exc)

    poster = GitHubCommentPoster(args.token, args.repo)
    renderer = PrCommentRenderer()
    body = renderer.render(findings)

    existing_id = poster._find_existing_comment(args.pr)
    if existing_id:
        poster._update_comment(existing_id, body)
    else:
        poster._create_comment(args.pr, body)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _cli()
