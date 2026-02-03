"""Conftest for WASM tests - no bpy required."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from notso_glb.wasm.wasi import WasiFilesystem


# Override the autouse fixture from parent conftest
@pytest.fixture(autouse=True)
def reset_blender_scene() -> None:
    """No-op fixture for WASM tests."""
    pass


@pytest.fixture
def mock_wasi_fs() -> WasiFilesystem:
    """Create a WasiFilesystem with mocked _refresh_memory for testing.

    This allows tests to set _memory_array directly without needing
    a full WASM runtime initialization.
    """
    from notso_glb.wasm.wasi import WasiFilesystem

    fs = WasiFilesystem()
    # Mock _refresh_memory to do nothing - tests will set _memory_array directly
    fs._refresh_memory = MagicMock()  # type: ignore[method-assign]
    return fs
