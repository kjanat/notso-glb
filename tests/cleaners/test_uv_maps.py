"""Tests for UV map cleanup module."""

from typing import cast

from bpy.types import Mesh, Object


def _get_mesh_data(obj: Object) -> Mesh:
    """Get mesh data from an object, assuming obj.type == 'MESH'."""
    return cast(Mesh, obj.data)


class TestRemoveUnusedUvMaps:
    """Tests for remove_unused_uv_maps function."""

    def test_empty_warnings(self) -> None:
        """Empty warnings should return 0."""
        from notso_glb.cleaners import remove_unused_uv_maps

        assert remove_unused_uv_maps([]) == 0

    def test_removes_specified_uv_maps(self, mesh_with_uv_layers: Object) -> None:
        """Should remove UV maps specified in warnings."""
        from notso_glb.cleaners import remove_unused_uv_maps

        mesh = _get_mesh_data(mesh_with_uv_layers)
        initial_count = len(mesh.uv_layers)

        warnings: list[dict[str, object]] = [
            {
                "mesh": mesh_with_uv_layers.name,
                "unused_uvs": ["UVMap.001"],
                "total_uvs": initial_count,
            }
        ]
        removed = remove_unused_uv_maps(warnings)

        assert removed == 1
        assert len(mesh.uv_layers) == initial_count - 1
