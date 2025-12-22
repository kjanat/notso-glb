"""Tests for bone cleanup module."""

from typing import cast

import bpy  # type: ignore[import-untyped]
from bpy.types import Armature, Object


def _active_object() -> Object:
    """Get the active object, raising if None."""
    obj = bpy.context.active_object
    if obj is None:
        raise RuntimeError("No active object")
    return obj


def _get_armature_data(obj: Object) -> Armature:
    """Get armature data from an object, assuming obj.type == 'ARMATURE'."""
    return cast(Armature, obj.data)


class TestDeleteBoneShapeObjects:
    """Tests for delete_bone_shape_objects function."""

    def test_no_objects(self) -> None:
        """Empty scene should return 0."""
        from notso_glb.cleaners import delete_bone_shape_objects

        assert delete_bone_shape_objects() == 0

    def test_deletes_icosphere_named_objects(self, bone_shape_object: Object) -> None:
        """Objects with bone shape names should be deleted."""
        from notso_glb.cleaners import delete_bone_shape_objects

        bpy.ops.mesh.primitive_cube_add()
        _active_object().name = "RegularCube"

        deleted = delete_bone_shape_objects()
        assert deleted == 1
        assert "RegularCube" in [o.name for o in bpy.data.objects]
        assert "WGT_bone_shape" not in [o.name for o in bpy.data.objects]

    def test_deletes_widget_objects(self) -> None:
        """Objects with 'widget' in name should be deleted."""
        from notso_glb.cleaners import delete_bone_shape_objects

        bpy.ops.mesh.primitive_cube_add()
        _active_object().name = "widget_root"

        deleted = delete_bone_shape_objects()
        assert deleted == 1


class TestMarkStaticBonesNonDeform:
    """Tests for mark_static_bones_non_deform function."""

    def test_no_armature(self) -> None:
        """Scene without armature should return (0, 0)."""
        from notso_glb.cleaners import mark_static_bones_non_deform

        marked, skipped = mark_static_bones_non_deform({"Bone1", "Bone2"})
        assert marked == 0
        assert skipped == 0

    def test_marks_static_bones(self, armature_with_bones: Object) -> None:
        """Static bones not used for skinning should be marked non-deform."""
        from notso_glb.cleaners import mark_static_bones_non_deform

        arm_data = _get_armature_data(armature_with_bones)
        bone_names = {b.name for b in arm_data.bones}

        marked, skipped = mark_static_bones_non_deform(bone_names)
        assert marked == len(bone_names)
        assert skipped == 0
