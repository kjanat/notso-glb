#!/usr/bin/env bash

GITHUB_OUTPUT="${GITHUB_OUTPUT:-/dev/null}"
GITHUB_ENV="${GITHUB_ENV:-/dev/null}"
GITHUB_PATH="${GITHUB_PATH:-/dev/null}"

if command -v uv >/dev/null 2>&1; then
	echo "uv-available=true" | tee -a "${GITHUB_OUTPUT}"
else
	echo "uv-available=false" | tee -a "${GITHUB_OUTPUT}"
	exit 0
fi

_version=$(uv --version)

UV_VERSION="$(awk '{print $2}' <<<"${_version}")"
UV_PATH="$(command -v uv)"
UVX_PATH="$(command -v uvx)"

echo "uv-version=${UV_VERSION}" | tee -a "${GITHUB_OUTPUT}"
echo "uv-path=${UV_PATH}" | tee -a "${GITHUB_OUTPUT}"
echo "uvx-path=${UVX_PATH}" | tee -a "${GITHUB_OUTPUT}"

# Handle activate-environment when uv is already available
if [[ "${ACTIVATE_ENVIRONMENT:-false}" == "true" && -z "${VIRTUAL_ENV:-}" ]]; then
	VENV_PATH="${GITHUB_WORKSPACE:-.}/.venv"

	# Build uv venv command with optional python version
	UV_VENV_CMD=(uv venv "${VENV_PATH}")
	if [[ -n "${INPUT_PYTHON_VERSION:-}" ]]; then
		UV_VENV_CMD+=(--python "${INPUT_PYTHON_VERSION}")
	fi

	# Create venv if it doesn't exist
	if [[ ! -d "${VENV_PATH}" ]]; then
		echo "Creating venv at ${VENV_PATH}"
		"${UV_VENV_CMD[@]}"
	fi

	# Activate for subsequent steps
	echo "VIRTUAL_ENV=${VENV_PATH}" | tee -a "${GITHUB_ENV}"
	echo "${VENV_PATH}/bin" | tee -a "${GITHUB_PATH}"
	echo "venv=${VENV_PATH}" | tee -a "${GITHUB_OUTPUT}"
elif [[ -n "${VIRTUAL_ENV:-}" ]]; then
	# Detect existing active venv
	echo "venv=${VIRTUAL_ENV}" | tee -a "${GITHUB_OUTPUT}"
fi

# Detect Python version (from UV_PYTHON, input, or active python)
if [[ -n "${INPUT_PYTHON_VERSION:-}" ]]; then
	echo "python-version=${INPUT_PYTHON_VERSION}" | tee -a "${GITHUB_OUTPUT}"
elif [[ -n "${UV_PYTHON:-}" ]]; then
	echo "python-version=${UV_PYTHON}" | tee -a "${GITHUB_OUTPUT}"
elif command -v python >/dev/null 2>&1; then
	PY_VERSION="$(python --version 2>&1 || true)"
	PY_VERSION="$(awk '{print $2}' <<<"${PY_VERSION}")"
	echo "python-version=${PY_VERSION}" | tee -a "${GITHUB_OUTPUT}"
fi
