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
    @uv run pytest {{ args }}

# Run tests with coverage
[group('dev')]
test-cov *args:
    @uv run pytest --cov --cov-report=term-missing {{ args }}

# Run linting
[group('dev')]
lint *args:
    @uv run ruff check {{ args }}

# Run linting with auto-fix
[group('dev')]
lint-fix *args:
    @uv run ruff check --fix-only {{ args }}

# Run formatting
[group('dev')]
fmt *args:
    @dprint fmt {{ args }}

# Check formatting
[group('dev')]
fmt-check *args:
    @dprint check {{ args }}

# Run type checking
[group('dev')]
typecheck *args:
    @uv run ty check {{ args }}

# Run all checks (lint, format check, typecheck, test)
[group('dev')]
check: lint typecheck test fmt-check

# ==============================================================================
# Docker
# ==============================================================================

# Build production Docker image
[group('docker')]
docker-build *args:
    docker build -t notso-glb:latest {{ args }} .

# Build development Docker image
[group('docker')]
docker-build-dev *args:
    docker build -f Dockerfile.dev -t notso-glb:dev {{ args }} .

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
    uv run -q notso-glb {{ args }}

# Show CLI help
[group('cli')]
help *command:
    @uv run -q notso-glb {{ command }} --help

# Show CLI version
[group('cli')]
version:
    @uv run -q notso-glb --version

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
    just sync

# Clean build artifacts
[group('maintenance')]
clean:
    rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .ruff_cache/ .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Download latest WASM from npm
[group('maintenance')]
[working-directory('./.github/actions/download-wasm')]
wasm-download:
    @./download.sh
