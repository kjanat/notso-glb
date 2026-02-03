"""Conftest for WASM tests - no bpy required."""

import pytest


# Override the autouse fixture from parent conftest
@pytest.fixture(autouse=True)
def reset_blender_scene() -> None:
    """No-op fixture for WASM tests."""
    pass
