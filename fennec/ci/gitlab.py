"""GitLab MR comment posting for CI integration."""

from __future__ import annotations

import argparse
import logging

import httpx

from fennec.output.model import Finding
from fennec.output.pr_comment import PrCommentRenderer

logger = logging.getLogger(__name__)


class GitLabCommentPoster:
    """Posts Fennec summary comments to GitLab merge requests."""

    def __init__(self, token: str, project_id: str, gitlab_url: str = "https://gitlab.com") -> None:
        self._headers = {"JOB-TOKEN": token}
        self._project_id = project_id
        self._base = f"{gitlab_url}/api/v4/projects/{project_id}"

    def post_mr_comment(self, findings: list[Finding], mr_iid: int) -> None:
        """Post a summary comment to a GitLab MR (same format as GitHub PR comment)."""
        renderer = PrCommentRenderer()
        body = renderer.render(findings)

        with httpx.Client() as client:
            resp = client.post(
                f"{self._base}/merge_requests/{mr_iid}/notes",
                headers=self._headers,
                json={"body": body},
            )
            if resp.status_code >= 300:
                logger.warning(
                    "GitLab MR comment POST returned HTTP %d for MR !%d",
                    resp.status_code, mr_iid,
                )
            else:
                logger.info("Posted Fennec comment to MR !%d", mr_iid)


# ------------------------------------------------------------------ #
# CLI entry point (called by GitLab CI script block)                  #
# ------------------------------------------------------------------ #

def _cli() -> None:
    parser = argparse.ArgumentParser(prog="python -m fennec.ci.gitlab")
    parser.add_argument("--sarif", required=True)
    parser.add_argument("--token", required=True, help="CI_JOB_TOKEN")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--mr-iid", required=True, type=int)
    parser.add_argument("--gitlab-url", default="https://gitlab.com")
    args = parser.parse_args()

    poster = GitLabCommentPoster(args.token, args.project_id, args.gitlab_url)
    poster.post_mr_comment([], args.mr_iid)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _cli()
