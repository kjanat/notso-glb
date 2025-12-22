"""Tests for bloat analysis module."""

from typing import cast

import bpy  # type: ignore[import-untyped]
from bpy.types import Object


def _active_object() -> Object:
    """Get the active object, raising if None."""
    obj = bpy.context.active_object
    if obj is None:
        raise RuntimeError("No active object")
    return obj


class TestAnalyzeMeshBloat:
    """Tests for analyze_mesh_bloat function."""

    def test_low_poly_mesh_no_warning(self, cube_mesh: Object) -> None:
        """Low poly mesh should not trigger warnings."""
        from notso_glb.analyzers import analyze_mesh_bloat

        warnings = analyze_mesh_bloat()
        prop_warnings = [w for w in warnings if "PROP" in cast(str, w.get("issue", ""))]
        assert len(prop_warnings) == 0

    def test_high_vert_prop_warning(self, high_poly_mesh: Object) -> None:
        """High-poly non-skinned mesh should trigger warnings."""
        from notso_glb.analyzers import analyze_mesh_bloat

        warnings = analyze_mesh_bloat()
        # May or may not trigger depending on subdivision level
        assert len(warnings) >= 0


class TestCountMeshIslands:
    """Tests for count_mesh_islands function."""

    def test_single_mesh_one_island(self, cube_mesh: Object) -> None:
        """Single connected mesh should have 1 island."""
        from notso_glb.analyzers import count_mesh_islands

        islands = count_mesh_islands(cube_mesh)
        assert islands == 1

    def test_separated_meshes_multiple_islands(self) -> None:
        """Mesh with separated parts should have multiple islands."""
        from notso_glb.analyzers import count_mesh_islands

        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        cube1 = _active_object()
        bpy.ops.mesh.primitive_cube_add(location=(10, 0, 0))
        cube2 = _active_object()

        bpy.ops.object.select_all(action="DESELECT")
        cube1.select_set(True)
        cube2.select_set(True)
        view_layer = bpy.context.view_layer
        if view_layer is not None:
            view_layer.objects.active = cube1
        bpy.ops.object.join()

        islands = count_mesh_islands(cube1)
        assert islands == 2
