"""Skinned mesh parent hierarchy analysis."""

import bpy


def analyze_skinned_mesh_parents() -> list[dict[str, object]]:
    """
    Detect skinned meshes that are not at scene root.

    glTF spec: parent transforms don't affect skinned meshes, so non-root
    skinned meshes can have unexpected positioning.

    Returns list of warnings for each non-root skinned mesh.
    """
    warnings: list[dict[str, object]] = []

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        # Check if mesh is skinned (has armature modifier)
        has_armature = any(mod.type == "ARMATURE" for mod in obj.modifiers)
        if not has_armature:
            continue

        # Check if it has a parent (not at root)
        parent = obj.parent
        if parent is not None:
            # Check if parent has non-identity transform
            has_transform = (
                parent.location.length > 0.0001
                or parent.rotation_euler.x != 0
                or parent.rotation_euler.y != 0
                or parent.rotation_euler.z != 0
                or abs(parent.scale.x - 1) > 0.0001
                or abs(parent.scale.y - 1) > 0.0001
                or abs(parent.scale.z - 1) > 0.0001
            )

            warnings.append({
                "mesh": obj.name,
                "parent": parent.name,
                "has_transform": has_transform,
                "severity": "CRITICAL" if has_transform else "WARNING",
            })

    return warnings
