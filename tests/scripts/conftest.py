"""Conftest for scripts tests - no bpy required."""

import sys
from pathlib import Path

import pytest

# Add scripts directory to Python path so 'from scripts.xxx import' works
_scripts_dir = Path(__file__).parent.parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir.parent))


# Override the autouse fixture from parent conftest
@pytest.fixture(autouse=True)
def reset_blender_scene() -> None:
    """No-op fixture for scripts tests."""
    pass
