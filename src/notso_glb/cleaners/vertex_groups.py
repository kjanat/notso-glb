"""Vertex group cleanup functions."""

import bpy

from notso_glb.utils import get_mesh_data


def clean_vertex_groups() -> int:
    """Remove vertex groups with no weights (empty bone references)."""
    total_removed = 0

    for obj in bpy.data.objects:
        if obj.type != "MESH" or len(obj.vertex_groups) == 0:
            continue

        mesh = get_mesh_data(obj)
        used_groups: set[int] = set()

        for v in mesh.vertices:
            for g in v.groups:
                if g.weight > 0.0001:
                    used_groups.add(g.group)

        unused_names = [
            vg.name for i, vg in enumerate(obj.vertex_groups) if i not in used_groups
        ]

        for name in unused_names:
            vg = obj.vertex_groups.get(name)
            if vg:
                obj.vertex_groups.remove(vg)
                total_removed += 1

    return total_removed
