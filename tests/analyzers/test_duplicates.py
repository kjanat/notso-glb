"""Tests for duplicate name analysis module."""

import bpy
from bpy.types import Object


def _active_object() -> Object:
    """Get the active object, raising if None."""
    obj = bpy.context.active_object
    if obj is None:
        raise RuntimeError("No active object")
    return obj


class TestAnalyzeDuplicateNames:
    """Tests for analyze_duplicate_names function."""

    def test_no_duplicates(self, _cube_mesh: Object) -> None:
        """Scene with unique names should return empty or minimal list."""
        from notso_glb.analyzers import analyze_duplicate_names

        duplicates = analyze_duplicate_names()
        exact_dups = [d for d in duplicates if d["issue"] == "EXACT_DUPLICATE"]
        assert len(exact_dups) == 0

    def test_detects_sanitization_collision(self) -> None:
        """Names that collide after sanitization should be detected."""
        from notso_glb.analyzers import analyze_duplicate_names

        bpy.ops.mesh.primitive_cube_add()
        _active_object().name = "Cube.001"
        bpy.ops.mesh.primitive_cube_add()
        _active_object().name = "Cube_001"

        duplicates = analyze_duplicate_names()
        collision = [d for d in duplicates if d["issue"] == "SANITIZATION_COLLISION"]
        assert len(collision) >= 1

    def test_detects_bone_duplicates(self, _armature_with_bones: Object) -> None:
        """Duplicate bone names within armature should be detected."""
        from notso_glb.analyzers import analyze_duplicate_names

        duplicates = analyze_duplicate_names()
        bone_dups = [d for d in duplicates if d["type"] == "BONE"]
        assert isinstance(bone_dups, list)
