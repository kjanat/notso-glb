# Dockerfile for notso-glb serverless environments
# Multi-stage build for minimal image size and fast cold starts
#
# Usage:
# docker build -t notso-glb .
# docker run -v /path/to/models:/data notso-glb /data/input.glb -o /data/output.glb

# =============================================================================
# Stage 1: Builder - Install dependencies and download WASM
# =============================================================================
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set up working directory
WORKDIR /app

# Copy dependency files first for better layer caching
# README.md is required by pyproject.toml for package metadata
COPY pyproject.toml uv.lock README.md ./

# Install dependencies only (not the project itself yet)
RUN uv sync --no-dev --frozen --no-install-project

# Copy source code and scripts
COPY src/ ./src/
COPY scripts/ ./scripts/

# Now install the project itself
RUN uv sync --no-dev --frozen

# Download gltfpack WASM binary from npm
RUN uv run scripts/update_wasm.py

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.11-slim AS runtime

# Labels for container metadata
LABEL org.opencontainers.image.title="notso-glb"
LABEL org.opencontainers.image.description="GLB Export Optimizer for Mascot Models"
LABEL org.opencontainers.image.source="https://github.com/kjanat/notso-glb"
LABEL org.opencontainers.image.licenses="GPL-3.0"

# Install runtime dependencies required by bpy (Blender Python API)
# These are minimal libraries needed for headless operation
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libice6 \
    libsm6 \
    libxfixes3 \
    libxi6 \
    libxkbcommon0 \
    libxrender1 \
    libxxf86vm1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security (serverless best practice)
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

# Set up working directory
WORKDIR /app

# Copy uv binary from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Disable Blender's splash and UI components for headless operation
ENV BLENDER_USER_CONFIG="/tmp/blender"
ENV BLENDER_USER_SCRIPTS="/tmp/blender/scripts"

# Create data directory for input/output files
RUN mkdir -p /data && chown appuser:appuser /data

# Switch to non-root user
USER appuser

# Create temp directories for Blender with proper permissions
RUN mkdir -p /tmp/blender/scripts

# Health check for serverless platforms that support it
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import notso_glb; print('healthy')" || exit 1

# Set working directory for data processing
WORKDIR /data

# Default entrypoint - run notso-glb CLI
ENTRYPOINT ["python", "-m", "notso_glb"]

# Default command shows help (override with actual file paths)
CMD ["--help"]
