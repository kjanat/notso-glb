"""Mesh cleanup and decimation functions."""

from typing import Literal

import bpy  # type: ignore[import-untyped]
from bpy.types import Modifier, Object

from notso_glb.utils import get_mesh_data, get_view_layer
from notso_glb.utils.constants import BLOAT_THRESHOLDS
from notso_glb.utils.logging import log_warn


def cleanup_mesh_bmesh(obj: Object) -> dict[str, int] | None:
    """
    Clean up mesh using bmesh operations:
    - Remove duplicate vertices (doubles)
    - Dissolve degenerate geometry (zero-area faces, zero-length edges)
    - Remove loose vertices

    Returns dict with cleanup stats or None if failed.
    """
    import bmesh  # type: ignore[import-untyped]

    mesh = get_mesh_data(obj)
    original_verts = len(mesh.vertices)
    original_faces = len(mesh.polygons)

    bm = bmesh.new()
    bm.from_mesh(mesh)

    stats: dict[str, int] = {
        "doubles_merged": 0,
        "degenerate_dissolved": 0,
        "loose_removed": 0,
    }

    # 1. Remove doubles (merge vertices within threshold)
    merge_dist = 0.0001  # 0.1mm threshold
    verts_before_doubles = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=merge_dist)  # ty: ignore[invalid-argument-type]
    stats["doubles_merged"] = verts_before_doubles - len(bm.verts)

    # 2. Dissolve degenerate geometry
    degenerate_faces = [f for f in bm.faces if f.calc_area() < 1e-8]
    if degenerate_faces:
        bmesh.ops.delete(bm, geom=degenerate_faces, context="FACES")
        stats["degenerate_dissolved"] += len(degenerate_faces)

    degenerate_edges = [e for e in bm.edges if e.calc_length() < 1e-8]
    if degenerate_edges:
        bmesh.ops.delete(bm, geom=degenerate_edges, context="EDGES")
        stats["degenerate_dissolved"] += len(degenerate_edges)

    # 3. Remove loose vertices (not connected to any face)
    loose_verts = [v for v in bm.verts if not v.link_faces]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")
        stats["loose_removed"] = len(loose_verts)

    # Write back to mesh
    bm.to_mesh(mesh)
    bm.free()

    mesh.update()

    new_verts = len(mesh.vertices)
    new_faces = len(mesh.polygons)

    stats["verts_before"] = original_verts
    stats["verts_after"] = new_verts
    stats["faces_before"] = original_faces
    stats["faces_after"] = new_faces

    return stats


def decimate_mesh(obj: Object, target_verts: int) -> tuple[int, int] | None:
    """
    Apply decimation to reduce mesh to approximately target vertex count.

    Returns (original_verts, new_verts) or None if failed.
    """
    mesh = get_mesh_data(obj)
    original_verts = len(mesh.vertices)
    if original_verts <= target_verts:
        return None

    ratio: float = target_verts / original_verts

    mod: Modifier = obj.modifiers.new(name="AutoDecimate", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"  # ty:ignore[unresolved-attribute]
    mod.ratio = ratio  # ty:ignore[unresolved-attribute]
    mod.use_collapse_triangulate = True  # ty:ignore[unresolved-attribute]

    view_layer = get_view_layer()
    view_layer.objects.active = obj  # type: ignore[assignment]
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
        new_verts = len(mesh.vertices)
        return (original_verts, new_verts)
    except Exception as e:  # pragma: no cover - defensive
        obj.modifiers.remove(mod)
        log_warn(f"Failed to decimate {obj.name}: {e}")
        return None


def auto_fix_bloat(
    warnings: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    """
    Automatically fix bloated meshes using bmesh cleanup + decimation.

    Pipeline:
    1. Run bmesh cleanup on ALL meshes (doubles, degenerate, loose)
    2. Decimate non-skinned props still flagged as BLOATED_PROP

    Returns dict with cleanup_stats and decimation_fixes.
    """
    results: dict[str, list[dict[str, object]]] = {
        "cleanup": [],
        "decimation": [],
    }

    # Phase 1: BMesh cleanup on ALL meshes
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        mesh = get_mesh_data(obj)
        verts_before = len(mesh.vertices)
        if verts_before < 10:
            continue

        try:
            stats = cleanup_mesh_bmesh(obj)
            if stats and (
                stats["doubles_merged"] > 0
                or stats["degenerate_dissolved"] > 0
                or stats["loose_removed"] > 0
            ):
                results["cleanup"].append({
                    "object": obj.name,
                    "doubles": stats["doubles_merged"],
                    "degenerate": stats["degenerate_dissolved"],
                    "loose": stats["loose_removed"],
                    "verts_saved": stats["verts_before"] - stats["verts_after"],
                })
        except Exception as e:
            log_warn(f"Cleanup failed for {obj.name}: {e}")

    # Phase 2: Decimate bloated props
    bloated_objects = [
        str(w["object"])
        for w in warnings
        if w["issue"] == "BLOATED_PROP" and w["severity"] == "CRITICAL"
    ]

    for obj_name in bloated_objects:
        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != "MESH":
            continue

        is_skinned = any(mod.type == "ARMATURE" for mod in obj.modifiers)
        if is_skinned:
            continue

        mesh = get_mesh_data(obj)
        current_verts = len(mesh.vertices)
        if current_verts <= BLOAT_THRESHOLDS["prop_critical"]:
            continue

        target = int(BLOAT_THRESHOLDS["prop_critical"] * 0.8)

        result = decimate_mesh(obj, target)
        if result:
            orig, new = result
            reduction = ((orig - new) / orig) * 100
            results["decimation"].append({
                "object": obj_name,
                "original": orig,
                "new": new,
                "reduction": reduction,
            })

    return results
