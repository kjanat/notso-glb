"""
Blender Python API wrapper for type checking.

Re-exports bpy with type suppression so the rest of the codebase
can import from here without ty errors.

Usage:
    from notso_glb._bpy import bpy
    # or for bmesh (must be imported at runtime inside functions)
    from notso_glb._bpy import bmesh
"""

from typing import Any

# type: ignore - bpy is Blender's dynamic module, not statically typed
import bpy as _bpy  # noqa: PLC0414

# Re-export with Any type to suppress downstream ty errors
bpy: Any = _bpy

# bmesh is a submodule of bpy, import lazily
try:
    import bmesh as _bmesh  # noqa: PLC0414  # ty:ignore[unresolved-import]

    bmesh: Any = _bmesh
except ImportError:
    bmesh: Any = None  # type: ignore[no-redef]
