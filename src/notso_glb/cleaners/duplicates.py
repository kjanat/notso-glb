"""Duplicate name auto-fix functions."""

from __future__ import annotations

import re
from typing import Any

import bpy

# Type alias for rename result
RenameRecord = dict[str, str]


def _get_collection(dtype: str) -> Any | None:
    """Get the appropriate bpy.data collection for a data type."""
    collections = {
        "OBJECT": bpy.data.objects,
        "MESH": bpy.data.meshes,
        "MATERIAL": bpy.data.materials,
        "ACTION": bpy.data.actions,
    }
    return collections.get(dtype)


def _get_ptr_suffix(item: Any) -> str:
    """Get short unique suffix from memory pointer (last 4 hex digits)."""
    return format(item.as_pointer() & 0xFFFF, "04x")


def _parse_colliding_names(name_field: str) -> list[str]:
    """Parse collision info string to extract list of colliding names."""
    match = re.search(r"\[([^\]]+)\]", name_field)
    if not match:
        return []
    names_str = match.group(1)
    return [n.strip().strip("'\"") for n in names_str.split(",")]


def _fix_exact_duplicates(
    collection: Any,
    name: str,
    dtype: str,
    processed: set[str],
    renames: list[RenameRecord],
) -> None:
    """Rename exact duplicates by appending pointer suffix."""
    matching = [item for item in collection if item.name == name]
    for item in matching[1:]:
        if item.name in processed:
            continue
        new_name = f"{name}_{_get_ptr_suffix(item)}"
        item.name = new_name
        processed.add(new_name)
        renames.append({"type": dtype, "old": name, "new": new_name})


def _fix_sanitization_collision(
    collection: Any,
    name_field: str,
    dtype: str,
    processed: set[str],
    renames: list[RenameRecord],
) -> None:
    """Rename colliding names from sanitization by appending pointer suffix."""
    colliding_names = _parse_colliding_names(name_field)
    for name in colliding_names[1:]:
        item = collection.get(name)
        if not item or name in processed:
            continue
        base = re.sub(r"\.", "_", name)
        new_name = f"{base}_{_get_ptr_suffix(item)}"
        item.name = new_name
        processed.add(new_name)
        renames.append({"type": dtype, "old": name, "new": new_name})


def auto_fix_duplicate_names(
    duplicates: list[dict[str, object]],
) -> list[RenameRecord]:
    """
    Automatically rename duplicates by appending memory pointer suffix.

    Uses as_pointer() for deterministic, session-stable unique IDs.
    Handles both exact duplicates and sanitization collisions.
    Returns list of renames performed.
    """
    renames: list[RenameRecord] = []
    processed: set[str] = set()

    for dup in duplicates:
        dtype = str(dup["type"])
        if dtype == "BONE":
            continue

        collection = _get_collection(dtype)
        if not collection:
            continue

        issue = dup.get("issue", "EXACT_DUPLICATE")
        name_field = str(dup["name"])

        if issue == "EXACT_DUPLICATE":
            _fix_exact_duplicates(collection, name_field, dtype, processed, renames)
        elif issue == "SANITIZATION_COLLISION":
            _fix_sanitization_collision(
                collection, name_field, dtype, processed, renames
            )

    return renames
