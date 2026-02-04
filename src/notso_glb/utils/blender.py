"""Utility functions for Blender scene access."""

from typing import cast

import bpy
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
