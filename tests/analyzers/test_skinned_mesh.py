"""Tests for skinned mesh analysis module."""

from bpy.types import Object


class TestAnalyzeSkinnedMeshParents:
    """Tests for analyze_skinned_mesh_parents function."""

    def test_no_skinned_meshes(self, cube_mesh: Object) -> None:
        """Scene without skinned meshes should return empty list."""
        from notso_glb.analyzers import analyze_skinned_mesh_parents

        assert analyze_skinned_mesh_parents() == []

    def test_skinned_mesh_at_root(self, skinned_mesh: Object) -> None:
        """Skinned mesh parented to armature is normal, detect if has other parent."""
        from notso_glb.analyzers import analyze_skinned_mesh_parents

        warnings = analyze_skinned_mesh_parents()
        assert isinstance(warnings, list)
