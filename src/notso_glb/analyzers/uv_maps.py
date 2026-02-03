"""Unused UV map detection."""

from typing import cast

import bpy
from bpy.types import ShaderNodeUVMap

from notso_glb.utils import get_mesh_data


def analyze_unused_uv_maps() -> list[dict[str, object]]:
    """
    Detect UV maps that aren't used by any material.

    Unused TEXCOORD attributes bloat the glTF file.
    Returns list of meshes with unused UV maps.
    """
    warnings: list[dict[str, object]] = []

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        mesh = get_mesh_data(obj)
        if not mesh.uv_layers:
            continue

        # Get UV maps used by materials
        used_uvs: set[str] = set()
        for mat_slot in obj.material_slots:
            if not mat_slot.material or not mat_slot.material.use_nodes:
                continue
            node_tree = mat_slot.material.node_tree
            if node_tree is None:
                continue
            for node in node_tree.nodes:
                if node.type == "UVMAP":
                    uv_node = cast(ShaderNodeUVMap, node)
                    if uv_node.uv_map:
                        used_uvs.add(uv_node.uv_map)
                # Image textures default to first UV if no explicit UV node
                if node.type == "TEX_IMAGE":
                    if not used_uvs and mesh.uv_layers:
                        used_uvs.add(mesh.uv_layers[0].name)

        # If no explicit UV usage found, assume first UV is used
        if not used_uvs and mesh.uv_layers:
            used_uvs.add(mesh.uv_layers[0].name)

        # Find unused UV maps
        unused = [uv.name for uv in mesh.uv_layers if uv.name not in used_uvs]
        if unused:
            warnings.append({
                "mesh": obj.name,
                "unused_uvs": unused,
                "total_uvs": len(mesh.uv_layers),
            })

    return warnings
