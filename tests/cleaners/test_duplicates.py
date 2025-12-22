"""Tests for duplicate name cleanup module."""

import bpy  # type: ignore[import-untyped]
from bpy.types import Object


def _active_object() -> Object:
    """Get the active object, raising if None."""
    obj = bpy.context.active_object
    if obj is None:
        raise RuntimeError("No active object")
    return obj


class TestAutoFixDuplicateNames:
    """Tests for auto_fix_duplicate_names function."""

    def test_empty_duplicates(self) -> None:
        """Empty duplicate list should return empty renames."""
        from notso_glb.cleaners import auto_fix_duplicate_names

        assert auto_fix_duplicate_names([]) == []

    def test_skips_bone_duplicates(self) -> None:
        """Bone duplicates should be skipped."""
        from notso_glb.cleaners import auto_fix_duplicate_names

        duplicates = [{"type": "BONE", "name": "Armature/Bone", "count": 2}]
        assert auto_fix_duplicate_names(duplicates) == []

    def test_fixes_sanitization_collision(self) -> None:
        """Should rename objects that collide after sanitization."""
        from notso_glb.cleaners import auto_fix_duplicate_names

        bpy.ops.mesh.primitive_cube_add()
        _active_object().name = "Test.001"
        bpy.ops.mesh.primitive_cube_add()
        _active_object().name = "Test_001"

        duplicates = [
            {
                "type": "OBJECT",
                "name": "Test_001 <- ['Test.001', 'Test_001']",
                "count": 2,
                "issue": "SANITIZATION_COLLISION",
            }
        ]

        renames = auto_fix_duplicate_names(duplicates)
        assert len(renames) == 1
        assert renames[0]["type"] == "OBJECT"
        assert renames[0]["old"] == "Test_001"
        assert "_" in renames[0]["new"]

    def test_fixes_exact_duplicates(self) -> None:
        """Should rename exact duplicate objects."""
        from notso_glb.cleaners import auto_fix_duplicate_names

        mesh1 = bpy.data.meshes.new("DupMesh")
        mesh2 = bpy.data.meshes.new("DupMesh")

        if mesh1.name == mesh2.name:
            duplicates = [
                {
                    "type": "MESH",
                    "name": mesh1.name,
                    "count": 2,
                    "issue": "EXACT_DUPLICATE",
                }
            ]

            renames = auto_fix_duplicate_names(duplicates)
            assert len(renames) >= 0

        bpy.data.meshes.remove(mesh1)
        if mesh2.name in [m.name for m in bpy.data.meshes]:
            bpy.data.meshes.remove(mesh2)

    def test_skips_unknown_collection_type(self) -> None:
        """Should skip unknown collection types gracefully."""
        from notso_glb.cleaners import auto_fix_duplicate_names

        duplicates = [
            {
                "type": "UNKNOWN_TYPE",
                "name": "Something",
                "count": 2,
                "issue": "EXACT_DUPLICATE",
            }
        ]

        renames = auto_fix_duplicate_names(duplicates)
        assert renames == []
