"""Analyzers for mesh bloat, bones, duplicates, and UV maps."""

from notso_glb.analyzers.bloat import analyze_mesh_bloat, count_mesh_islands
from notso_glb.analyzers.bones import (
    analyze_bone_animation,
    get_bones_used_for_skinning,
)
from notso_glb.analyzers.duplicates import analyze_duplicate_names
from notso_glb.analyzers.skinned_mesh import analyze_skinned_mesh_parents
from notso_glb.analyzers.uv_maps import analyze_unused_uv_maps

__all__ = [
    "analyze_bone_animation",
    "analyze_duplicate_names",
    "analyze_mesh_bloat",
    "analyze_skinned_mesh_parents",
    "analyze_unused_uv_maps",
    "count_mesh_islands",
    "get_bones_used_for_skinning",
]
