"""Duplicate name detection for glTF export issues."""

from collections import Counter, defaultdict

import bpy  # type: ignore[import-untyped]

from notso_glb.utils import sanitize_gltf_name


def analyze_duplicate_names() -> list[dict[str, object]]:
    """
    Detect duplicate names that will cause glTF export issues.

    Checks both:
    1. Exact duplicates in Blender
    2. Names that collide after glTF sanitization (e.g., 'Cube.155' and 'Cube_155')

    Returns list of duplicates grouped by type.
    """
    duplicates: list[dict[str, object]] = []

    def check_collection(items, type_name: str) -> None:
        """Check a collection for exact and sanitized duplicates."""
        names = [item.name for item in items]

        # 1. Exact duplicates
        for name, count in Counter(names).items():
            if count > 1:
                duplicates.append({
                    "type": type_name,
                    "name": name,
                    "count": count,
                    "issue": "EXACT_DUPLICATE",
                })

        # 2. Sanitization collisions
        sanitized_map: dict[str, list[str]] = defaultdict(list)
        for name in names:
            sanitized = sanitize_gltf_name(name)
            sanitized_map[sanitized].append(name)

        for sanitized, originals in sanitized_map.items():
            if len(originals) > 1:
                unique_originals = set(originals)
                if len(unique_originals) > 1:
                    duplicates.append({
                        "type": type_name,
                        "name": f"{sanitized} <- {list(unique_originals)}",
                        "count": len(originals),
                        "issue": "SANITIZATION_COLLISION",
                    })

    # Check all relevant collections
    check_collection(bpy.data.objects, "OBJECT")
    check_collection(bpy.data.meshes, "MESH")
    check_collection(bpy.data.materials, "MATERIAL")
    check_collection(bpy.data.actions, "ACTION")

    # Special handling for bones (per armature)
    for arm in bpy.data.armatures:
        bone_names = [bone.name for bone in arm.bones]
        for name, count in Counter(bone_names).items():
            if count > 1:
                duplicates.append({
                    "type": "BONE",
                    "name": f"{arm.name}/{name}",
                    "count": count,
                    "issue": "EXACT_DUPLICATE",
                })

    return duplicates
