"""Tests for vertex group cleanup module."""

from bpy.types import Object


class TestCleanVertexGroups:
    """Tests for clean_vertex_groups function."""

    def test_no_meshes(self) -> None:
        """Empty scene should return 0 removed."""
        from notso_glb.cleaners import clean_vertex_groups

        assert clean_vertex_groups() == 0

    def test_mesh_without_vertex_groups(self, cube_mesh: Object) -> None:
        """Mesh without vertex groups should return 0."""
        from notso_glb.cleaners import clean_vertex_groups

        assert clean_vertex_groups() == 0

    def test_removes_empty_vertex_groups(self, cube_mesh: Object) -> None:
        """Empty vertex groups (no weights) should be removed."""
        from notso_glb.cleaners import clean_vertex_groups

        cube_mesh.vertex_groups.new(name="EmptyGroup1")
        cube_mesh.vertex_groups.new(name="EmptyGroup2")

        removed = clean_vertex_groups()
        assert removed == 2

    def test_keeps_weighted_vertex_groups(self, cube_mesh: Object) -> None:
        """Vertex groups with weights should be kept."""
        from notso_glb.cleaners import clean_vertex_groups

        vg = cube_mesh.vertex_groups.new(name="WeightedGroup")
        vg.add([0, 1, 2], 1.0, "REPLACE")
        cube_mesh.vertex_groups.new(name="EmptyGroup")

        removed = clean_vertex_groups()
        assert removed == 1
        assert "WeightedGroup" in [vg.name for vg in cube_mesh.vertex_groups]
