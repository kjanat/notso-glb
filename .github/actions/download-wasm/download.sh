#!/usr/bin/env bash
set -euo pipefail

# Resolve paths relative to action location
ACTION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${ACTION_DIR}/../../.." && pwd)"

VERSION_FILE="${REPO_ROOT}/src/notso_glb/wasm/gltfpack.version"
UPDATE_SCRIPT="${REPO_ROOT}/scripts/update_wasm.py"

# Get version before download
if [[ -f "${VERSION_FILE}" ]]; then
	BEFORE=$(cat "${VERSION_FILE}")
else
	BEFORE="none"
fi

# Download WASM (pass version if specified)
if [[ -n "${WASM_VERSION:-}" ]]; then
	"${UPDATE_SCRIPT}" --version "${WASM_VERSION}"
else
	"${UPDATE_SCRIPT}"
fi

# Get version after download
AFTER=$(cat "${VERSION_FILE}")

# Output to GitHub
# shellcheck disable=SC2154  # GITHUB_OUTPUT is set by GitHub Actions
echo "before=${BEFORE}" >>"${GITHUB_OUTPUT}"
echo "after=${AFTER}" >>"${GITHUB_OUTPUT}"

# Log
echo "WASM version: ${BEFORE} -> ${AFTER}"
