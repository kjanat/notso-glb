"""Tests for bone analysis module."""

from bpy.types import Object


class TestGetBonesUsedForSkinning:
    """Tests for get_bones_used_for_skinning function."""

    def test_no_skinned_meshes(self, _cube_mesh: Object) -> None:
        """Scene without skinned meshes should return empty set."""
        from notso_glb.analyzers import get_bones_used_for_skinning

        assert get_bones_used_for_skinning() == set()

    def test_skinned_mesh_returns_bone_names(self, _skinned_mesh: Object) -> None:
        """Skinned mesh should return vertex group names as bone names."""
        from notso_glb.analyzers import get_bones_used_for_skinning

        bones = get_bones_used_for_skinning()
        assert len(bones) >= 1
