"""Scan orchestration and exit code mapping for CI integration."""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum

from fennec.output.model import Finding, RuleMode

logger = logging.getLogger(__name__)


class FailOn(str, Enum):
    BLOCKING = "blocking"
    ANY = "any"
    NONE = "none"


@dataclass
class ScanResult:
    findings: list[Finding] = field(default_factory=list)
    sarif_path: str = ""
    error: str | None = None


def map_exit_code(findings: list[Finding], fail_on: FailOn | str) -> int:
    """Map findings + fail-on policy to a CI exit code.

    Policy table:
      fail-on: none     → always 0
      fail-on: any      → 0 if no findings, 1 if any findings
      fail-on: blocking → 0 if no blocking findings, 1 if any blocking
    """
    mode = FailOn(fail_on) if isinstance(fail_on, str) else fail_on

    if mode == FailOn.NONE:
        return 0

    if mode == FailOn.ANY:
        return 1 if findings else 0

    # FailOn.BLOCKING (default)
    has_blocking = any(f.mode == RuleMode.BLOCKING for f in findings)
    return 1 if has_blocking else 0


def _get_changed_files(base_sha: str, repo_path: str) -> list[str]:
    """Return files changed between base_sha and HEAD."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_sha, "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return [f for f in result.stdout.strip().splitlines() if f]
    except subprocess.CalledProcessError as exc:
        logger.warning("git diff failed: %s", exc)
        return []


def run_diff_scan(
    repo_path: str = ".",
    base_sha: str | None = None,
    custom_rules_path: str | None = None,
) -> list[Finding]:
    """Run an incremental scan on changed files.

    In production, this wires parsers → graph emitter → taint tracker →
    LLM engine. Currently returns an empty list (scaffolding).
    """
    if base_sha is None:
        base_sha = os.getenv("GIT_BASE_SHA", "HEAD~1")

    changed = _get_changed_files(base_sha, repo_path)
    logger.info("Diff scan: %d changed file(s) from %s", len(changed), base_sha)

    # TODO: wire to parsers → graph_client.incremental_update → taint tracker → LLM
    return []


def run_full_scan(
    repo_path: str = ".",
    custom_rules_path: str | None = None,
) -> list[Finding]:
    """Run a full-repository scan.

    In production, this wires parsers → graph emitter → taint tracker →
    LLM engine. Currently returns an empty list (scaffolding).
    """
    logger.info("Full scan: %s", repo_path)

    # TODO: wire to parsers → graph_client.full_repo_scan → taint tracker → LLM
    return []
