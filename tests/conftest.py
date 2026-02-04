"""
Pytest fixtures for GLB Export Optimizer tests.

Uses real bpy module (Blender as Python module).
"""

from __future__ import annotations

from typing import cast

import pytest

# Conditionally import bpy - only needed for tests that use Blender
try:
    import bpy
    from bpy.types import Image, Mesh, Object

    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    bpy = None  # type: ignore
    Image = None  # type: ignore
    Mesh = None  # type: ignore
    Object = None  # type: ignore


def _active_object() -> Object:
    """Get the active object, raising if None."""
    obj = bpy.context.active_object
    if obj is None:
        raise RuntimeError("No active object")
    return obj


def _get_mesh_data(obj: Object) -> Mesh:
    """Get mesh data from an object, assuming obj.type == 'MESH'."""
    return cast(Mesh, obj.data)


@pytest.fixture(autouse=True)
def reset_blender_scene() -> None:
    """Reset Blender to factory settings before each test."""
    if not HAS_BPY:
        pytest.skip("Blender (bpy) not available")
    bpy.ops.wm.read_factory_settings(use_empty=True)


@pytest.fixture
def cube_mesh() -> Object:
    """Create a simple cube mesh object."""
    bpy.ops.mesh.primitive_cube_add()
    return _active_object()


@pytest.fixture
def high_poly_mesh() -> Object:
    """Create a high-poly mesh (subdivided cube) for bloat testing."""
    bpy.ops.mesh.primitive_cube_add()
    obj = _active_object()
    # Subdivide to increase vertex count
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.subdivide(number_cuts=5)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


@pytest.fixture
def armature_with_bones() -> Object:
    """Create an armature with multiple bones."""
    bpy.ops.object.armature_add()
    arm_obj = _active_object()

    bpy.ops.object.mode_set(mode="EDIT")
    # Add more bones
    bpy.ops.armature.bone_primitive_add(name="Bone.001")
    bpy.ops.armature.bone_primitive_add(name="Bone.002")
    bpy.ops.object.mode_set(mode="OBJECT")

    return arm_obj


@pytest.fixture
def skinned_mesh(cube_mesh: Object, armature_with_bones: Object) -> Object:
    """Create a mesh skinned to an armature."""
    # Select cube, then armature
    bpy.ops.object.select_all(action="DESELECT")
    cube_mesh.select_set(True)
    armature_with_bones.select_set(True)
    view_layer = bpy.context.view_layer
    if view_layer is not None:
        view_layer.objects.active = armature_with_bones

    # Parent with automatic weights
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    return cube_mesh


@pytest.fixture
def mesh_with_uv_layers(cube_mesh: Object) -> Object:
    """Create a mesh with multiple UV layers."""
    mesh = _get_mesh_data(cube_mesh)
    # First UV layer already exists from primitive
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UVMap.001")
    mesh.uv_layers.new(name="UVMap.002")
    return cube_mesh


@pytest.fixture
def bone_shape_object() -> Object:
    """Create an object that looks like a bone shape widget."""
    bpy.ops.mesh.primitive_ico_sphere_add()
    obj = _active_object()
    obj.name = "WGT_bone_shape"
    return obj


@pytest.fixture
def large_texture() -> Image:
    """Create a large texture for resize testing."""
    img = bpy.data.images.new("LargeTexture", width=2048, height=2048)
    return img
