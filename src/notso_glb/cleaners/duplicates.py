"""Duplicate name auto-fix functions."""

import re

import bpy


def auto_fix_duplicate_names(
    duplicates: list[dict[str, object]],
) -> list[dict[str, str]]:
    """
    Automatically rename duplicates by appending memory pointer suffix.

    Uses as_pointer() for deterministic, session-stable unique IDs.
    Handles both exact duplicates and sanitization collisions.
    Returns list of renames performed.
    """
    renames: list[dict[str, str]] = []
    processed: set[str] = set()

    def get_collection(dtype: str):
        """Get the appropriate bpy.data collection."""
        if dtype == "OBJECT":
            return bpy.data.objects
        elif dtype == "MESH":
            return bpy.data.meshes
        elif dtype == "MATERIAL":
            return bpy.data.materials
        elif dtype == "ACTION":
            return bpy.data.actions
        return None

    def get_ptr_suffix(item) -> str:
        """Get short unique suffix from memory pointer (last 4 hex digits)."""
        return format(item.as_pointer() & 0xFFFF, "04x")

    def rename_item(collection, old_name: str, new_name: str, dtype: str) -> bool:
        """Rename an item and track it."""
        item = collection.get(old_name)
        if item and old_name not in processed:
            item.name = new_name
            processed.add(new_name)
            renames.append({"type": dtype, "old": old_name, "new": new_name})
            return True
        return False

    for dup in duplicates:
        dtype = str(dup["type"])
        issue = dup.get("issue", "EXACT_DUPLICATE")

        if dtype == "BONE":
            continue  # Skip bones for now (complex to rename)

        collection = get_collection(dtype)
        if not collection:
            continue

        if issue == "EXACT_DUPLICATE":
            name = str(dup["name"])
            matching = [item for item in collection if item.name == name]
            # Keep first, rename rest with pointer suffix
            for item in matching[1:]:
                suffix = get_ptr_suffix(item)
                new_name = f"{name}_{suffix}"
                rename_item(collection, item.name, new_name, dtype)

        elif issue == "SANITIZATION_COLLISION":
            # Parse the collision info: "sanitized <- ['name1', 'name2']"
            match = re.search(r"\[([^\]]+)\]", str(dup["name"]))
            if match:
                names_str = match.group(1)
                colliding_names = [n.strip().strip("'\"") for n in names_str.split(",")]

                # Keep first, rename rest with pointer suffix
                for name in colliding_names[1:]:
                    item = collection.get(name)
                    if item and name not in processed:
                        base = re.sub(r"\.", "_", name)
                        suffix = get_ptr_suffix(item)
                        new_name = f"{base}_{suffix}"
                        rename_item(collection, name, new_name, dtype)

    return renames
