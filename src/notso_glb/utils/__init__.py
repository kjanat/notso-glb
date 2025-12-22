"""Utility functions for Blender scene access."""

from typing import cast

import bpy  # type: ignore[import-untyped]
from bpy.types import Armature, Mesh, Object, Scene, ViewLayer


def get_scene() -> Scene:
    """Get the current scene, raising if None."""
    scene = bpy.context.scene
    if scene is None:
        raise RuntimeError("No active scene")
    return scene


def get_view_layer() -> ViewLayer:
    """Get the current view layer, raising if None."""
    view_layer = bpy.context.view_layer
    if view_layer is None:
        raise RuntimeError("No active view layer")
    return view_layer


def get_mesh_data(obj: Object) -> Mesh:
    """Get mesh data from an object, assuming obj.type == 'MESH'."""
    return cast(Mesh, obj.data)


def get_armature_data(obj: Object) -> Armature:
    """Get armature data from an object, assuming obj.type == 'ARMATURE'."""
    return cast(Armature, obj.data)


def get_scene_stats() -> dict[str, int]:
    """Get current scene statistics."""
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]

    total_verts = sum(len(get_mesh_data(o).vertices) for o in meshes)
    total_bones = sum(len(get_armature_data(a).bones) for a in armatures)
    total_actions = len(bpy.data.actions)

    return {
        "meshes": len(meshes),
        "vertices": total_verts,
        "bones": total_bones,
        "actions": total_actions,
    }


def sanitize_gltf_name(name: str) -> str:
    """
    Simulate how glTF export sanitizes names for JS identifiers.
    Dots, spaces, dashes become underscores. Leading digits get prefix.
    """
    import re

    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized


def nearest_power_of_two(n: int) -> int:
    """Round to nearest power of two."""
    if n <= 1:
        return 1
    bit_len = (n - 1).bit_length()
    lower = 1 << (bit_len - 1)
    upper = 1 << bit_len
    return lower if (n - lower) < (upper - n) else upper
