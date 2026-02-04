# https://just.systems
# Run `just` to see available recipes

set shell := ["bash", "-cu"]

alias run := notso-glb

# Default recipe - show help
default:
    @just --list --unsorted

# ==============================================================================
# Development
# ==============================================================================

# Run all tests
[group('dev')]
test *args:
    uv run pytest {{ args }}

# Run tests with coverage
[group('dev')]
test-cov:
    uv run pytest --cov --cov-report=term-missing

# Run linting
[group('dev')]
lint:
    uv run ruff check .

# Run linting with auto-fix
[group('dev')]
lint-fix:
    uv run ruff check --fix .

# Run formatting
[group('dev')]
fmt:
    uv run ruff format .
    dprint fmt

# Run type checking
[group('dev')]
typecheck:
    uv run ty check

# Run all checks (lint, format check, typecheck, test)
[group('dev')]
check: lint typecheck test
    uv run ruff format --check .

# ==============================================================================
# Docker
# ==============================================================================

# Build production Docker image
[group('docker')]
docker-build:
    docker build -t notso-glb:latest .

# Build development Docker image
[group('docker')]
docker-build-dev:
    docker build -f Dockerfile.dev -t notso-glb:dev .

# Test dev image with a GLB file
[group('docker')]
docker-test-dev file:
    docker run --rm -v "$(pwd)":/data notso-glb:dev {{ file }}

# Test prod image with a GLB file
[group('docker')]
docker-test file:
    docker run --rm -v "$(pwd)":/data notso-glb:latest {{ file }}

# Run dev image interactively
[group('docker')]
docker-shell-dev:
    docker run --rm -it --entrypoint bash -v "$(pwd)":/data notso-glb:dev

# Run prod image interactively
[group('docker')]
docker-shell:
    docker run --rm -it --entrypoint bash -v "$(pwd)":/data notso-glb:latest

# Show Docker image sizes
[group('docker')]
docker-sizes:
    @docker images notso-glb

# ==============================================================================
# CLI
# ==============================================================================

# Run CLI directly (requires uv sync first)
[group('cli')]
notso-glb *args:
    uv run notso-glb {{ args }}

# Show CLI help
[group('cli')]
help:
    uv run notso-glb --help

# Show CLI version
[group('cli')]
version:
    uv run notso-glb --version

# ==============================================================================
# Maintenance
# ==============================================================================

# Sync dependencies
[group('maintenance')]
sync:
    uv sync

# Update dependencies
[group('maintenance')]
update:
    uv lock --upgrade
    uv sync

# Clean build artifacts
[group('maintenance')]
clean:
    rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .ruff_cache/ .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Download latest WASM from npm
[group('maintenance')]
download-wasm:
    ./.github/actions/download-wasm/download.sh
