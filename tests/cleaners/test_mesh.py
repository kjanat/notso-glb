"""Tests for mesh cleanup module."""

from bpy.types import Object


class TestCleanupMeshBmesh:
    """Tests for cleanup_mesh_bmesh function."""

    def test_clean_mesh_no_changes(self, cube_mesh: Object) -> None:
        """Clean mesh should have no changes."""
        from notso_glb.cleaners import cleanup_mesh_bmesh

        stats = cleanup_mesh_bmesh(cube_mesh)
        assert stats is not None

        assert stats["doubles_merged"] == 0
        assert stats["degenerate_dissolved"] == 0
        assert stats["loose_removed"] == 0
        assert stats["verts_before"] == stats["verts_after"]
