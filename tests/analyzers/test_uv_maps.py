"""Tests for UV map analysis module."""

from typing import cast

from bpy.types import Mesh, Object


def _get_mesh_data(obj: Object) -> Mesh:
    """Get mesh data from an object, assuming obj.type == 'MESH'."""
    return cast(Mesh, obj.data)


class TestAnalyzeUnusedUvMaps:
    """Tests for analyze_unused_uv_maps function."""

    def test_no_meshes(self) -> None:
        """Empty scene should return empty list."""
        from notso_glb.analyzers import analyze_unused_uv_maps

        assert analyze_unused_uv_maps() == []

    def test_mesh_without_uv_maps(self, cube_mesh: Object) -> None:
        """Mesh without UV maps should not warn."""
        from notso_glb.analyzers import analyze_unused_uv_maps

        mesh = _get_mesh_data(cube_mesh)
        while mesh.uv_layers:
            mesh.uv_layers.remove(mesh.uv_layers[0])

        assert analyze_unused_uv_maps() == []

    def test_detects_unused_secondary_uv(self, mesh_with_uv_layers: Object) -> None:
        """Secondary UV maps not referenced by materials should be detected."""
        from notso_glb.analyzers import analyze_unused_uv_maps

        warnings = analyze_unused_uv_maps()
        assert len(warnings) >= 1
        total_unused = sum(len(cast(list[str], w["unused_uvs"])) for w in warnings)
        assert total_unused >= 1
