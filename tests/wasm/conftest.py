"""Conftest for WASM tests - no bpy required."""

from __future__ import annotations

import pytest

from notso_glb.wasm.wasi import WasiFilesystem


# Override the autouse fixture from parent conftest
@pytest.fixture(autouse=True)
def reset_blender_scene() -> None:
    """No-op fixture for WASM tests."""
    pass


@pytest.fixture
def mock_wasi_fs(monkeypatch: pytest.MonkeyPatch) -> WasiFilesystem:
    """Create a WasiFilesystem with _refresh_memory neutralized for testing.

    Tests inject ``_memory_array`` directly (a real ``ctypes`` ubyte array
    matching the production type), so ``_refresh_memory`` must not overwrite it.
    ``monkeypatch.setattr`` swaps the method dynamically (and auto-reverts),
    which keeps the fixture typed as the real ``WasiFilesystem`` rather than a
    type-erased ``Any``.
    """
    fs = WasiFilesystem()
    monkeypatch.setattr(fs, "_refresh_memory", lambda: None)
    return fs
