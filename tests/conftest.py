"""
Pytest fixtures for GLB Export Optimizer tests.

Uses real bpy module (Blender as Python module).
"""

from __future__ import annotations

from notso_glb._bpy import bpy
import pytest


@pytest.fixture(autouse=True)
def reset_blender_scene() -> None:
    """Reset Blender to factory settings before each test."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


@pytest.fixture
def cube_mesh() -> bpy.types.Object:
    """Create a simple cube mesh object."""
    bpy.ops.mesh.primitive_cube_add()
    return bpy.context.active_object


@pytest.fixture
def high_poly_mesh() -> bpy.types.Object:
    """Create a high-poly mesh (subdivided cube) for bloat testing."""
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    # Subdivide to increase vertex count
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.subdivide(number_cuts=5)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


@pytest.fixture
def armature_with_bones() -> bpy.types.Object:
    """Create an armature with multiple bones."""
    bpy.ops.object.armature_add()
    arm_obj = bpy.context.active_object

    bpy.ops.object.mode_set(mode="EDIT")
    # Add more bones
    bpy.ops.armature.bone_primitive_add(name="Bone.001")
    bpy.ops.armature.bone_primitive_add(name="Bone.002")
    bpy.ops.object.mode_set(mode="OBJECT")

    return arm_obj


@pytest.fixture
def skinned_mesh(
    cube_mesh: bpy.types.Object, armature_with_bones: bpy.types.Object
) -> bpy.types.Object:
    """Create a mesh skinned to an armature."""
    # Select cube, then armature
    bpy.ops.object.select_all(action="DESELECT")
    cube_mesh.select_set(True)
    armature_with_bones.select_set(True)
    bpy.context.view_layer.objects.active = armature_with_bones

    # Parent with automatic weights
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    return cube_mesh


@pytest.fixture
def mesh_with_uv_layers(cube_mesh: bpy.types.Object) -> bpy.types.Object:
    """Create a mesh with multiple UV layers."""
    mesh = cube_mesh.data
    # First UV layer already exists from primitive
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UVMap.001")
    mesh.uv_layers.new(name="UVMap.002")
    return cube_mesh


@pytest.fixture
def bone_shape_object() -> bpy.types.Object:
    """Create an object that looks like a bone shape widget."""
    bpy.ops.mesh.primitive_ico_sphere_add()
    obj = bpy.context.active_object
    obj.name = "WGT_bone_shape"
    return obj


@pytest.fixture
def large_texture() -> bpy.types.Image:
    """Create a large texture for resize testing."""
    img = bpy.data.images.new("LargeTexture", width=2048, height=2048)
    return img
