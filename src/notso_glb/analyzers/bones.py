"""Bone animation analysis for detecting static bones."""

import bpy  # type: ignore[import-untyped]
from bpy.types import Object

from notso_glb.utils import get_scene, get_view_layer
from notso_glb.utils.logging import log_debug


def get_bones_used_for_skinning() -> set[str]:
    """Find all bones that have vertex weights on skinned meshes."""
    used_bones: set[str] = set()

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        # Check if mesh is skinned (has armature modifier)
        has_armature = any(mod.type == "ARMATURE" for mod in obj.modifiers)
        if not has_armature:
            continue

        # All vertex groups on skinned meshes are bone references
        for vg in obj.vertex_groups:
            used_bones.add(vg.name)

    return used_bones


def analyze_bone_animation() -> set[str]:
    """Find bones that never animate across all actions.

    Optimized to batch frame evaluations - evaluates all bones at once per frame
    instead of switching frames per-bone, reducing scene updates from O(bones*actions)
    to O(actions).
    """
    armature: Object | None = None
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            armature = obj
            break

    if not armature or not armature.animation_data or not armature.pose:
        log_debug("No armature with animation data found")
        return set()

    scene = get_scene()
    view_layer = get_view_layer()
    bone_movement: dict[str, float] = {b.name: 0.0 for b in armature.pose.bones}
    num_bones = len(armature.pose.bones)
    num_actions = len(bpy.data.actions)

    log_debug(f"Analyzing {num_bones} bones across {num_actions} actions")

    orig_action = armature.animation_data.action
    orig_frame = scene.frame_current

    for action in bpy.data.actions:
        armature.animation_data.action = action
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])

        # Evaluate start frame ONCE for all bones
        scene.frame_set(frame_start)
        view_layer.update()
        start_poses: dict[str, tuple] = {}
        for bone in armature.pose.bones:
            start_poses[bone.name] = (
                bone.location.copy(),
                bone.rotation_quaternion.copy(),
                bone.rotation_euler.copy(),
                bone.rotation_mode,
            )

        # Evaluate end frame ONCE for all bones
        scene.frame_set(frame_end)
        view_layer.update()

        # Now calculate diffs without any frame switching
        for bone in armature.pose.bones:
            start_loc, start_rot_q, start_rot_e, rot_mode = start_poses[bone.name]
            end_loc = bone.location.copy()
            end_rot_q = bone.rotation_quaternion.copy()
            end_rot_e = bone.rotation_euler.copy()

            loc_diff = (end_loc - start_loc).length  # ty: ignore[unsupported-operator]
            if rot_mode == "QUATERNION":
                rot_diff = (end_rot_q - start_rot_q).magnitude  # ty: ignore[unsupported-operator]
            else:
                rot_diff = (
                    end_rot_e.to_quaternion() - start_rot_e.to_quaternion()
                ).magnitude  # ty: ignore[unsupported-operator]

            bone_movement[bone.name] += loc_diff + rot_diff

    if orig_action:
        armature.animation_data.action = orig_action
    scene.frame_set(orig_frame)

    return {name for name, movement in bone_movement.items() if movement < 0.01}
