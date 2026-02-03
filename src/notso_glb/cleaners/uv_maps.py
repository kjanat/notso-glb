"""UV map cleanup functions."""

from typing import cast

import bpy

from notso_glb.utils import get_mesh_data


def remove_unused_uv_maps(warnings: list[dict[str, object]]) -> int:
    """Remove unused UV maps detected by analyze_unused_uv_maps."""
    removed = 0

    for warn in warnings:
        mesh_name = cast(str, warn["mesh"])
        obj = bpy.data.objects.get(mesh_name)
        if not obj or obj.type != "MESH":
            continue

        mesh = get_mesh_data(obj)
        uv_names = cast(list[str], warn["unused_uvs"])
        for uv_name in uv_names:
            uv_layer = mesh.uv_layers.get(uv_name)
            if uv_layer:
                mesh.uv_layers.remove(uv_layer)
                removed += 1
                print(f"    Removed unused UV '{uv_name}' from {obj.name}")

    return removed
