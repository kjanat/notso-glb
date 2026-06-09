"""Conftest for WASM tests - no bpy required."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


# Override the autouse fixture from parent conftest
@pytest.fixture(autouse=True)
def reset_blender_scene() -> None:
    """No-op fixture for WASM tests."""
    pass


@pytest.fixture
def mock_wasi_fs() -> Any:
    """Create a WasiFilesystem with mocked _refresh_memory for testing.

    This allows tests to set _memory_array directly (as a plain bytearray)
    without needing a full WASM runtime initialization. The return type is
    ``Any`` because the fixture deliberately injects test doubles
    (``MagicMock`` for ``_refresh_memory`` and a ``bytearray`` for
    ``_memory_array``) that do not match the production attribute types.
    """
    from notso_glb.wasm.wasi import WasiFilesystem

    fs: Any = WasiFilesystem()
    # Mock _refresh_memory to do nothing - tests will set _memory_array directly
    fs._refresh_memory = MagicMock()
    return fs
