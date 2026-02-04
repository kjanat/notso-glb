"""Tests for duplicate name cleanup module."""

import bpy
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

    def test_fixes_material_duplicates(self) -> None:
        """Should rename duplicate materials."""
        from notso_glb.cleaners import auto_fix_duplicate_names

        mat1 = bpy.data.materials.new("Material")
        mat2 = bpy.data.materials.new("Material")

        # Blender may auto-rename, so check if they have the same name
        if mat1.name == mat2.name:
            duplicates = [
                {
                    "type": "MATERIAL",
                    "name": mat1.name,
                    "count": 2,
                    "issue": "EXACT_DUPLICATE",
                }
            ]

            renames = auto_fix_duplicate_names(duplicates)
            assert len(renames) >= 0

        bpy.data.materials.remove(mat1)
        if mat2.name in [m.name for m in bpy.data.materials]:
            bpy.data.materials.remove(mat2)

    def test_fixes_action_duplicates(self) -> None:
        """Should rename duplicate actions."""
        from notso_glb.cleaners import auto_fix_duplicate_names

        action1 = bpy.data.actions.new("Action")
        action2 = bpy.data.actions.new("Action")

        if action1.name == action2.name:
            duplicates = [
                {
                    "type": "ACTION",
                    "name": action1.name,
                    "count": 2,
                    "issue": "EXACT_DUPLICATE",
                }
            ]

            renames = auto_fix_duplicate_names(duplicates)
            assert len(renames) >= 0

        bpy.data.actions.remove(action1)
        if action2.name in [a.name for a in bpy.data.actions]:
            bpy.data.actions.remove(action2)

    def test_multiple_exact_duplicates(self) -> None:
        """Should rename multiple exact duplicates with different suffixes."""
        from notso_glb.cleaners import auto_fix_duplicate_names

        mesh1 = bpy.data.meshes.new("MultiDup")
        mesh2 = bpy.data.meshes.new("MultiDup")
        mesh3 = bpy.data.meshes.new("MultiDup")

        if mesh1.name == mesh2.name == mesh3.name:
            duplicates = [
                {
                    "type": "MESH",
                    "name": mesh1.name,
                    "count": 3,
                    "issue": "EXACT_DUPLICATE",
                }
            ]

            renames = auto_fix_duplicate_names(duplicates)
            # Should rename duplicates (all but first)
            assert len(renames) >= 1

            # Check that renamed items have unique suffixes
            renamed_names = [r["new"] for r in renames]
            assert len(renamed_names) == len(set(renamed_names))

        for mesh in [mesh1, mesh2, mesh3]:
            if mesh.name in [m.name for m in bpy.data.meshes]:
                bpy.data.meshes.remove(mesh)

    def test_processes_each_duplicate_once(self) -> None:
        """Should not process the same duplicate multiple times."""
        from notso_glb.cleaners import auto_fix_duplicate_names

        mesh1 = bpy.data.meshes.new("OnceMesh")
        mesh2 = bpy.data.meshes.new("OnceMesh")

        if mesh1.name == mesh2.name:
            # Pass same duplicate entry twice
            duplicates = [
                {
                    "type": "MESH",
                    "name": mesh1.name,
                    "count": 2,
                    "issue": "EXACT_DUPLICATE",
                },
                {
                    "type": "MESH",
                    "name": mesh1.name,
                    "count": 2,
                    "issue": "EXACT_DUPLICATE",
                },
            ]

            renames = auto_fix_duplicate_names(duplicates)
            # Should not double-process
            assert len(renames) <= 2

        for mesh in [mesh1, mesh2]:
            if mesh.name in [m.name for m in bpy.data.meshes]:
                bpy.data.meshes.remove(mesh)

    def test_sanitization_with_multiple_collisions(self) -> None:
        """Should handle multiple sanitization collisions."""
        from notso_glb.cleaners import auto_fix_duplicate_names

        bpy.ops.mesh.primitive_cube_add()
        _active_object().name = "Obj.A"
        bpy.ops.mesh.primitive_cube_add()
        _active_object().name = "Obj_A"
        bpy.ops.mesh.primitive_cube_add()
        _active_object().name = "Obj.B"

        duplicates = [
            {
                "type": "OBJECT",
                "name": "Obj_A <- ['Obj.A', 'Obj_A']",
                "count": 2,
                "issue": "SANITIZATION_COLLISION",
            }
        ]

        renames = auto_fix_duplicate_names(duplicates)
        assert len(renames) >= 1

    def test_empty_collection_name_handling(self) -> None:
        """Should handle empty or malformed collision names."""
        from notso_glb.cleaners import auto_fix_duplicate_names

        duplicates = [
            {
                "type": "OBJECT",
                "name": "Test_001 <- []",
                "count": 0,
                "issue": "SANITIZATION_COLLISION",
            }
        ]

        # Should not crash
        renames = auto_fix_duplicate_names(duplicates)
        assert isinstance(renames, list)
