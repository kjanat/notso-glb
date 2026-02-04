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

# gltfpack version to install
ARG GLTFPACK_VERSION=1.0

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Download gltfpack binary from meshoptimizer releases
RUN curl -fsSL "https://github.com/zeux/meshoptimizer/releases/download/v${GLTFPACK_VERSION}/gltfpack-ubuntu.zip" \
    -o /tmp/gltfpack.zip \
    && unzip /tmp/gltfpack.zip -d /tmp \
    && mv /tmp/gltfpack /usr/local/bin/gltfpack \
    && chmod +x /usr/local/bin/gltfpack \
    && rm /tmp/gltfpack.zip

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

# Clean up unnecessary files from bpy to reduce image size
# bpy bundles a full Blender installation - we only need the core Python modules
RUN find .venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
    && find .venv -type f -name "*.pyc" -delete 2>/dev/null || true \
    && find .venv -type f -name "*.pyo" -delete 2>/dev/null || true \
# Remove Blender datafiles we don't need for headless GLB processing
    && rm -rf .venv/lib/python3.11/site-packages/bpy/5.0/datafiles/locale 2>/dev/null || true \
    && rm -rf .venv/lib/python3.11/site-packages/bpy/5.0/datafiles/fonts 2>/dev/null || true \
    && rm -rf .venv/lib/python3.11/site-packages/bpy/5.0/datafiles/icons 2>/dev/null || true \
    && rm -rf .venv/lib/python3.11/site-packages/bpy/5.0/datafiles/studiolights 2>/dev/null || true \
    && rm -rf .venv/lib/python3.11/site-packages/bpy/5.0/datafiles/colormanagement 2>/dev/null || true \
# Remove Blender's bundled Python (we use system Python)
    && rm -rf .venv/lib/python3.11/site-packages/bpy/5.0/python 2>/dev/null || true \
# Remove unnecessary scripts (keep addons_core for glTF export)
    && rm -rf .venv/lib/python3.11/site-packages/bpy/5.0/scripts/startup 2>/dev/null || true \
    && rm -rf .venv/lib/python3.11/site-packages/bpy/5.0/scripts/templates* 2>/dev/null || true \
    && rm -rf .venv/lib/python3.11/site-packages/bpy/5.0/scripts/presets 2>/dev/null || true \
    && rm -rf .venv/lib/python3.11/site-packages/bpy/5.0/scripts/modules/rna_* 2>/dev/null || true

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

# Copy gltfpack binary from builder
COPY --from=builder /usr/local/bin/gltfpack /usr/local/bin/gltfpack

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
