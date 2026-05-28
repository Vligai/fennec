#!/usr/bin/env bash
set -euo pipefail

# Mask the API key before any output so it never appears in logs
echo "::add-mask::${FENNEC_API_KEY}"

SCAN_MODE="${INPUT_SCAN_MODE:-diff}"
FAIL_ON="${INPUT_FAIL_ON:-blocking}"
POST_COMMENT="${INPUT_POST_COMMENT:-true}"
SARIF_OUTPUT="fennec-results.sarif"

echo "::group::Fennec Security Scan (mode=${SCAN_MODE}, fail-on=${FAIL_ON})"

# Validate that the API key is present
if [[ -z "${FENNEC_API_KEY:-}" ]]; then
    echo "::error::FENNEC_API_KEY is required. Set it as a repository secret."
    exit 1
fi

# Run the scan
if [[ "${SCAN_MODE}" == "diff" ]]; then
    fennec scan --diff --format sarif --output "${SARIF_OUTPUT}" --fail-on "${FAIL_ON}" || SCAN_EXIT=$?
else
    fennec scan --full --format sarif --output "${SARIF_OUTPUT}" --fail-on "${FAIL_ON}" || SCAN_EXIT=$?
fi

SCAN_EXIT="${SCAN_EXIT:-0}"

echo "::endgroup::"

# Export outputs for subsequent steps
echo "sarif-path=${SARIF_OUTPUT}" >> "${GITHUB_OUTPUT}"

# Post PR comment if enabled and we have a token and PR number
if [[ "${POST_COMMENT}" == "true" && -n "${GITHUB_TOKEN:-}" && -n "${PR_NUMBER:-}" ]]; then
    echo "::group::Posting PR comment"
    python -m fennec.ci.github \
        --sarif "${SARIF_OUTPUT}" \
        --token "${GITHUB_TOKEN}" \
        --repo "${GITHUB_REPOSITORY}" \
        --pr "${PR_NUMBER}" || echo "::warning::PR comment posting failed (non-fatal)"
    echo "::endgroup::"
fi

exit "${SCAN_EXIT}"
