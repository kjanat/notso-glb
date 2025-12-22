"""Cleaners for mesh, bones, textures, and vertex groups."""

from notso_glb.cleaners.bones import (
    delete_bone_shape_objects,
    mark_static_bones_non_deform,
)
from notso_glb.cleaners.duplicates import auto_fix_duplicate_names
from notso_glb.cleaners.mesh import auto_fix_bloat, cleanup_mesh_bmesh, decimate_mesh
from notso_glb.cleaners.textures import resize_textures
from notso_glb.cleaners.uv_maps import remove_unused_uv_maps
from notso_glb.cleaners.vertex_groups import clean_vertex_groups

__all__ = [
    "auto_fix_bloat",
    "auto_fix_duplicate_names",
    "clean_vertex_groups",
    "cleanup_mesh_bmesh",
    "decimate_mesh",
    "delete_bone_shape_objects",
    "mark_static_bones_non_deform",
    "remove_unused_uv_maps",
    "resize_textures",
]
