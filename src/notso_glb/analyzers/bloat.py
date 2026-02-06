"""Mesh bloat analysis for detecting overly complex geometry."""

import bpy
from bpy.types import Object

from notso_glb.utils import get_mesh_data
from notso_glb.utils.constants import BLOAT_THRESHOLDS


def count_mesh_islands(obj: Object) -> int:
    """Count disconnected mesh parts (islands) using BFS."""
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(get_mesh_data(obj))
    bm.verts.ensure_lookup_table()

    visited: set[int] = set()
    islands = 0

    for v in bm.verts:
        if v.index in visited:
            continue
        islands += 1
        stack = [v]
        while stack:
            current = stack.pop()
            if current.index in visited:
                continue
            visited.add(current.index)
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other.index not in visited:
                    stack.append(other)

    bm.free()
    return islands


def analyze_mesh_bloat() -> list[dict[str, object]]:
    """
    Detect unreasonably complex meshes for web delivery.

    Returns list of warnings with severity levels:
    - CRITICAL: Must fix before web deployment
    - WARNING: Should review, likely bloated
    - INFO: Notable but may be intentional
    """
    warnings: list[dict[str, object]] = []

    total_verts = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        mesh = get_mesh_data(obj)
        verts = len(mesh.vertices)
        total_verts += verts

        if verts < 100:
            continue

        # Check if skinned (character mesh vs prop)
        is_skinned = any(mod.type == "ARMATURE" for mod in obj.modifiers)

        # Count islands for non-skinned meshes (expensive operation)
        islands = 1
        if not is_skinned and verts < 20000:
            islands = count_mesh_islands(obj)

        verts_per_island = verts / max(islands, 1)

        # Bloat detection rules
        if not is_skinned:
            if verts > BLOAT_THRESHOLDS["prop_critical"]:
                warnings.append({
                    "severity": "CRITICAL",
                    "object": obj.name,
                    "issue": "BLOATED_PROP",
                    "detail": f"{verts:,} verts (limit: {BLOAT_THRESHOLDS['prop_critical']:,})",
                    "suggestion": "Decimate or replace with baked texture",
                })
            elif verts > BLOAT_THRESHOLDS["prop_warning"]:
                warnings.append({
                    "severity": "WARNING",
                    "object": obj.name,
                    "issue": "HIGH_VERT_PROP",
                    "detail": f"{verts:,} verts",
                    "suggestion": "Consider simplifying",
                })

            if (
                islands > BLOAT_THRESHOLDS["repetitive_islands"]
                and verts_per_island > BLOAT_THRESHOLDS["repetitive_verts"]
            ):
                warnings.append({
                    "severity": "CRITICAL",
                    "object": obj.name,
                    "issue": "REPETITIVE_DETAIL",
                    "detail": f"{islands} islands x {verts_per_island:.0f} verts each",
                    "suggestion": "Merge islands or use instancing/texture",
                })

    # Scene-level check
    if total_verts > BLOAT_THRESHOLDS["scene_total"]:
        warnings.append({
            "severity": "WARNING",
            "object": "SCENE",
            "issue": "HIGH_TOTAL_VERTS",
            "detail": f"{total_verts:,} verts (target: <{BLOAT_THRESHOLDS['scene_total']:,})",
            "suggestion": "Review all meshes for optimization opportunities",
        })

    # Sort by severity
    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    warnings.sort(key=lambda w: severity_order.get(str(w["severity"]), 99))

    return warnings
