# Dockerfile - Production build installing notso-glb from PyPI
# Multi-stage build for minimal image size and fast cold starts
#
# Build:
# ```sh
# docker build -t notso-glb .
# docker build --build-arg NOTSO_GLB_VERSION="notso-glb==0.1.0" -t notso-glb:0.1.0 .
# ```
#
# Usage (WORKDIR is /data, paths are relative to mount):
# ```sh
# docker run --rm -v /path/to/models:/data notso-glb input.glb
# docker run --rm -v /path/to/models:/data notso-glb input.glb -o output.glb
# docker run --rm -v "$(pwd)":/data notso-glb model.blend --no-draco --no-webp
# ```
#
# Options:
# ```sh
# docker run --rm notso-glb --help
# docker run --rm notso-glb --version
# ```
#
# See CLI.md for full options: https://github.com/kjanat/notso-glb/blob/master/CLI.md

# =============================================================================
# Stage 1: Builder - Install notso-glb from PyPI
# =============================================================================
FROM ghcr.io/astral-sh/uv:0.9.28-python3.11-bookworm-slim AS builder

# gltfpack version to install
ARG GLTFPACK_VERSION=1.0
# notso-glb version (use "notso-glb" for latest, or "notso-glb==0.1.0" for specific)
ARG NOTSO_GLB_VERSION=notso-glb

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# Set up working directory
WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
# Use copy mode for cache mounts
ENV UV_LINK_MODE=copy

# Install notso-glb from PyPI with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python ${NOTSO_GLB_VERSION}

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.11-slim-bookworm AS runtime

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

# Copy virtual environment from builder (includes compiled bytecode)
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
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
ENTRYPOINT ["notso-glb"]

# Default command shows help (override with actual file paths)
CMD ["--help"]
