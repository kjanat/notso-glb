"""Bone cleanup functions."""

import bpy
from bpy.types import Object

from notso_glb.analyzers.bones import get_bones_used_for_skinning
from notso_glb.utils import get_armature_data


def mark_static_bones_non_deform(static_bones: set[str]) -> tuple[int, int]:
    """Mark static bones as non-deform, but KEEP bones used for skinning."""
    armature: Object | None = None
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            armature = obj
            break

    if not armature:
        return 0, 0

    # CRITICAL: Don't mark bones as non-deform if they're weighted to meshes
    skinning_bones = get_bones_used_for_skinning()
    safe_to_mark = static_bones - skinning_bones
    skipped = len(static_bones & skinning_bones)

    arm_data = get_armature_data(armature)
    marked = 0
    for bone_name in safe_to_mark:
        bone = arm_data.bones.get(bone_name)
        if not bone or not bone.use_deform:
            continue
        bone.use_deform = False
        marked += 1

    return marked, skipped


def delete_bone_shape_objects() -> int:
    """Remove objects used as bone custom shapes (Icosphere, etc.)."""
    deleted = 0
    shape_names = ["icosphere", "bone_shape", "widget", "wgt_"]

    for obj in list(bpy.data.objects):
        name_lower = obj.name.lower()
        if any(s in name_lower for s in shape_names):
            bpy.data.objects.remove(obj, do_unlink=True)
            deleted += 1

    return deleted
