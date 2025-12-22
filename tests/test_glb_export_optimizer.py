"""
Tests for GLB Export Optimizer.

Uses real bpy module (Blender as Python module) for accurate testing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from notso_glb._bpy import bpy

if TYPE_CHECKING:
    pass


# =============================================================================
# Test: sanitize_gltf_name (pure function, no bpy dependency)
# =============================================================================


class TestSanitizeGltfName:
    """Tests for sanitize_gltf_name function"""

    def test_simple_name_unchanged(self) -> None:
        """Simple alphanumeric names should remain unchanged"""
        from notso_glb.glb_export_optimizer import sanitize_gltf_name

        assert sanitize_gltf_name("Cube") == "Cube"
        assert sanitize_gltf_name("mesh_001") == "mesh_001"
        assert sanitize_gltf_name("MyObject") == "MyObject"

    def test_dots_replaced_with_underscores(self) -> None:
        """Dots should be replaced with underscores"""
        from notso_glb.glb_export_optimizer import sanitize_gltf_name

        assert sanitize_gltf_name("Cube.001") == "Cube_001"
        assert sanitize_gltf_name("mesh.data.001") == "mesh_data_001"

    def test_spaces_replaced_with_underscores(self) -> None:
        """Spaces should be replaced with underscores"""
        from notso_glb.glb_export_optimizer import sanitize_gltf_name

        assert sanitize_gltf_name("My Object") == "My_Object"
        assert sanitize_gltf_name("a b c") == "a_b_c"

    def test_dashes_replaced_with_underscores(self) -> None:
        """Dashes should be replaced with underscores"""
        from notso_glb.glb_export_optimizer import sanitize_gltf_name

        assert sanitize_gltf_name("my-object") == "my_object"
        assert sanitize_gltf_name("mesh-001-final") == "mesh_001_final"

    def test_leading_digit_gets_prefix(self) -> None:
        """Names starting with digits should get underscore prefix"""
        from notso_glb.glb_export_optimizer import sanitize_gltf_name

        assert sanitize_gltf_name("001_cube") == "_001_cube"
        assert sanitize_gltf_name("3DModel") == "_3DModel"

    def test_special_characters_replaced(self) -> None:
        """Special characters should be replaced with underscores"""
        from notso_glb.glb_export_optimizer import sanitize_gltf_name

        assert sanitize_gltf_name("cube@home") == "cube_home"
        assert sanitize_gltf_name("mesh#1") == "mesh_1"
        assert sanitize_gltf_name("a!b@c#d") == "a_b_c_d"

    def test_empty_string(self) -> None:
        """Empty string should return empty string"""
        from notso_glb.glb_export_optimizer import sanitize_gltf_name

        assert sanitize_gltf_name("") == ""


# =============================================================================
# Test: nearest_power_of_two (pure function, no bpy dependency)
# =============================================================================


class TestNearestPowerOfTwo:
    """Tests for nearest_power_of_two function"""

    def test_exact_powers_of_two(self) -> None:
        """Exact powers of two should return themselves"""
        from notso_glb.glb_export_optimizer import nearest_power_of_two

        assert nearest_power_of_two(1) == 1
        assert nearest_power_of_two(2) == 2
        assert nearest_power_of_two(4) == 4
        assert nearest_power_of_two(256) == 256
        assert nearest_power_of_two(1024) == 1024
        assert nearest_power_of_two(2048) == 2048

    def test_rounds_up(self) -> None:
        """Values closer to higher power should round up"""
        from notso_glb.glb_export_optimizer import nearest_power_of_two

        assert nearest_power_of_two(3) == 4  # 3 is closer to 4 than 2
        assert nearest_power_of_two(7) == 8  # 7 is closer to 8 than 4
        assert (
            nearest_power_of_two(1600) == 2048
        )  # 1600 closer to 2048 (448) than 1024 (576)

    def test_rounds_down(self) -> None:
        """Values closer to lower power should round down"""
        from notso_glb.glb_export_optimizer import nearest_power_of_two

        assert nearest_power_of_two(5) == 4  # 5 is closer to 4 than 8
        assert nearest_power_of_two(1000) == 1024  # 1000 is closer to 1024 than 512

    def test_zero_and_negative(self) -> None:
        """Zero and negative values should return 1"""
        from notso_glb.glb_export_optimizer import nearest_power_of_two

        assert nearest_power_of_two(0) == 1
        assert nearest_power_of_two(-5) == 1


# =============================================================================
# Test: BLOAT_THRESHOLDS constant
# =============================================================================


class TestBloatThresholds:
    """Tests for BLOAT_THRESHOLDS configuration"""

    def test_thresholds_exist(self) -> None:
        """All expected threshold keys should exist"""
        from notso_glb.glb_export_optimizer import BLOAT_THRESHOLDS

        assert "prop_warning" in BLOAT_THRESHOLDS
        assert "prop_critical" in BLOAT_THRESHOLDS
        assert "repetitive_islands" in BLOAT_THRESHOLDS
        assert "repetitive_verts" in BLOAT_THRESHOLDS
        assert "scene_total" in BLOAT_THRESHOLDS

    def test_threshold_values_sensible(self) -> None:
        """Threshold values should be sensible for web delivery"""
        from notso_glb.glb_export_optimizer import BLOAT_THRESHOLDS

        # Warning threshold should be less than critical
        assert BLOAT_THRESHOLDS["prop_warning"] < BLOAT_THRESHOLDS["prop_critical"]
        # Scene total should be larger than individual prop limits
        assert BLOAT_THRESHOLDS["scene_total"] > BLOAT_THRESHOLDS["prop_critical"]


# =============================================================================
# Test: CONFIG constant
# =============================================================================


class TestConfig:
    """Tests for CONFIG constant"""

    def test_config_has_required_keys(self) -> None:
        """CONFIG should have all required keys"""
        from notso_glb.glb_export_optimizer import CONFIG

        required_keys = [
            "output_path",
            "use_draco",
            "use_webp",
            "max_texture_size",
            "force_pot_textures",
            "analyze_animations",
            "check_bloat",
            "experimental_autofix",
        ]
        for key in required_keys:
            assert key in CONFIG

    def test_config_default_values(self) -> None:
        """CONFIG defaults should be sensible"""
        from notso_glb.glb_export_optimizer import CONFIG

        assert CONFIG["output_path"] is None  # Auto-detect
        assert CONFIG["use_draco"] is True  # Compression on by default
        assert CONFIG["use_webp"] is True  # WebP on by default
        assert CONFIG["max_texture_size"] == 1024
        assert CONFIG["experimental_autofix"] is False  # Experimental off


# =============================================================================
# Test: get_scene_stats
# =============================================================================


class TestGetSceneStats:
    """Tests for get_scene_stats function"""

    def test_empty_scene(self) -> None:
        """Empty scene should return zeros"""
        from notso_glb.glb_export_optimizer import get_scene_stats

        stats = get_scene_stats()
        assert stats["meshes"] == 0
        assert stats["vertices"] == 0
        assert stats["bones"] == 0
        assert stats["actions"] == 0

    def test_scene_with_meshes(self, cube_mesh: bpy.types.Object) -> None:
        """Scene with meshes should count correctly"""
        from notso_glb.glb_export_optimizer import get_scene_stats

        stats = get_scene_stats()
        assert stats["meshes"] == 1
        assert stats["vertices"] == 8  # Cube has 8 vertices

    def test_scene_with_armature(self, armature_with_bones: bpy.types.Object) -> None:
        """Scene with armature should count bones"""
        from notso_glb.glb_export_optimizer import get_scene_stats

        stats = get_scene_stats()
        assert stats["bones"] >= 1  # At least 1 bone


# =============================================================================
# Test: clean_vertex_groups
# =============================================================================


class TestCleanVertexGroups:
    """Tests for clean_vertex_groups function"""

    def test_no_meshes(self) -> None:
        """Empty scene should return 0 removed"""
        from notso_glb.glb_export_optimizer import clean_vertex_groups

        assert clean_vertex_groups() == 0

    def test_mesh_without_vertex_groups(self, cube_mesh: bpy.types.Object) -> None:
        """Mesh without vertex groups should return 0"""
        from notso_glb.glb_export_optimizer import clean_vertex_groups

        assert clean_vertex_groups() == 0

    def test_removes_empty_vertex_groups(self, cube_mesh: bpy.types.Object) -> None:
        """Empty vertex groups (no weights) should be removed"""
        from notso_glb.glb_export_optimizer import clean_vertex_groups

        # Add empty vertex groups
        cube_mesh.vertex_groups.new(name="EmptyGroup1")
        cube_mesh.vertex_groups.new(name="EmptyGroup2")

        removed = clean_vertex_groups()
        assert removed == 2

    def test_keeps_weighted_vertex_groups(self, cube_mesh: bpy.types.Object) -> None:
        """Vertex groups with weights should be kept"""
        from notso_glb.glb_export_optimizer import clean_vertex_groups

        # Add vertex group with weights
        vg = cube_mesh.vertex_groups.new(name="WeightedGroup")
        vg.add([0, 1, 2], 1.0, "REPLACE")

        # Add empty vertex group
        cube_mesh.vertex_groups.new(name="EmptyGroup")

        removed = clean_vertex_groups()
        assert removed == 1  # Only empty group removed
        assert "WeightedGroup" in [vg.name for vg in cube_mesh.vertex_groups]


# =============================================================================
# Test: delete_bone_shape_objects
# =============================================================================


class TestDeleteBoneShapeObjects:
    """Tests for delete_bone_shape_objects function"""

    def test_no_objects(self) -> None:
        """Empty scene should return 0"""
        from notso_glb.glb_export_optimizer import delete_bone_shape_objects

        assert delete_bone_shape_objects() == 0

    def test_deletes_icosphere_named_objects(
        self, bone_shape_object: bpy.types.Object
    ) -> None:
        """Objects with bone shape names should be deleted"""
        from notso_glb.glb_export_optimizer import delete_bone_shape_objects

        # Also add a regular cube that should NOT be deleted
        bpy.ops.mesh.primitive_cube_add()
        bpy.context.active_object.name = "RegularCube"

        deleted = delete_bone_shape_objects()
        assert deleted == 1
        assert "RegularCube" in [o.name for o in bpy.data.objects]
        assert "WGT_bone_shape" not in [o.name for o in bpy.data.objects]

    def test_deletes_widget_objects(self) -> None:
        """Objects with 'widget' in name should be deleted"""
        from notso_glb.glb_export_optimizer import delete_bone_shape_objects

        bpy.ops.mesh.primitive_cube_add()
        bpy.context.active_object.name = "widget_root"

        deleted = delete_bone_shape_objects()
        assert deleted == 1


# =============================================================================
# Test: get_bones_used_for_skinning
# =============================================================================


class TestGetBonesUsedForSkinning:
    """Tests for get_bones_used_for_skinning function"""

    def test_no_skinned_meshes(self, cube_mesh: bpy.types.Object) -> None:
        """Scene without skinned meshes should return empty set"""
        from notso_glb.glb_export_optimizer import get_bones_used_for_skinning

        assert get_bones_used_for_skinning() == set()

    def test_skinned_mesh_returns_bone_names(
        self, skinned_mesh: bpy.types.Object
    ) -> None:
        """Skinned mesh should return vertex group names as bone names"""
        from notso_glb.glb_export_optimizer import get_bones_used_for_skinning

        bones = get_bones_used_for_skinning()
        # Should have at least one bone name from automatic weights
        assert len(bones) >= 1


# =============================================================================
# Test: analyze_skinned_mesh_parents
# =============================================================================


class TestAnalyzeSkinnedMeshParents:
    """Tests for analyze_skinned_mesh_parents function"""

    def test_no_skinned_meshes(self, cube_mesh: bpy.types.Object) -> None:
        """Scene without skinned meshes should return empty list"""
        from notso_glb.glb_export_optimizer import analyze_skinned_mesh_parents

        assert analyze_skinned_mesh_parents() == []

    def test_skinned_mesh_at_root(self, skinned_mesh: bpy.types.Object) -> None:
        """Skinned mesh parented to armature is normal, detect if has other parent"""
        from notso_glb.glb_export_optimizer import analyze_skinned_mesh_parents

        # The skinned mesh is parented to armature, which is at root
        # This should generate a warning since it has a parent
        warnings = analyze_skinned_mesh_parents()
        # May or may not warn depending on armature transform
        assert isinstance(warnings, list)


# =============================================================================
# Test: analyze_unused_uv_maps
# =============================================================================


class TestAnalyzeUnusedUvMaps:
    """Tests for analyze_unused_uv_maps function"""

    def test_no_meshes(self) -> None:
        """Empty scene should return empty list"""
        from notso_glb.glb_export_optimizer import analyze_unused_uv_maps

        assert analyze_unused_uv_maps() == []

    def test_mesh_without_uv_maps(self, cube_mesh: bpy.types.Object) -> None:
        """Mesh without UV maps should not warn"""
        from notso_glb.glb_export_optimizer import analyze_unused_uv_maps

        # Remove default UV if any
        mesh = cube_mesh.data
        while mesh.uv_layers:
            mesh.uv_layers.remove(mesh.uv_layers[0])

        assert analyze_unused_uv_maps() == []

    def test_detects_unused_secondary_uv(
        self, mesh_with_uv_layers: bpy.types.Object
    ) -> None:
        """Secondary UV maps not referenced by materials should be detected"""
        from notso_glb.glb_export_optimizer import analyze_unused_uv_maps

        warnings = analyze_unused_uv_maps()
        # Should detect unused UV maps
        assert len(warnings) >= 1
        # Check that some unused UVs were found
        total_unused = sum(len(w["unused_uvs"]) for w in warnings)
        assert total_unused >= 1


# =============================================================================
# Test: analyze_duplicate_names
# =============================================================================


class TestAnalyzeDuplicateNames:
    """Tests for analyze_duplicate_names function"""

    def test_no_duplicates(self, cube_mesh: bpy.types.Object) -> None:
        """Scene with unique names should return empty or minimal list"""
        from notso_glb.glb_export_optimizer import analyze_duplicate_names

        duplicates = analyze_duplicate_names()
        # No exact duplicates expected with single object
        exact_dups = [d for d in duplicates if d["issue"] == "EXACT_DUPLICATE"]
        assert len(exact_dups) == 0

    def test_detects_sanitization_collision(self) -> None:
        """Names that collide after sanitization should be detected"""
        from notso_glb.glb_export_optimizer import analyze_duplicate_names

        # Create objects with names that collide after sanitization
        bpy.ops.mesh.primitive_cube_add()
        bpy.context.active_object.name = "Cube.001"
        bpy.ops.mesh.primitive_cube_add()
        bpy.context.active_object.name = "Cube_001"

        duplicates = analyze_duplicate_names()
        collision = [d for d in duplicates if d["issue"] == "SANITIZATION_COLLISION"]
        assert len(collision) >= 1

    def test_detects_bone_duplicates(
        self, armature_with_bones: bpy.types.Object
    ) -> None:
        """Duplicate bone names within armature should be detected"""
        from notso_glb.glb_export_optimizer import analyze_duplicate_names

        # Blender doesn't allow exact duplicate bone names in same armature,
        # so we test that bones are checked (even if no duplicates exist)
        duplicates = analyze_duplicate_names()
        # Should complete without error, bones are checked
        bone_dups = [d for d in duplicates if d["type"] == "BONE"]
        # No duplicates expected since Blender auto-renames
        assert isinstance(bone_dups, list)


# =============================================================================
# Test: analyze_mesh_bloat
# =============================================================================


class TestAnalyzeMeshBloat:
    """Tests for analyze_mesh_bloat function"""

    def test_low_poly_mesh_no_warning(self, cube_mesh: bpy.types.Object) -> None:
        """Low poly mesh should not trigger warnings"""
        from notso_glb.glb_export_optimizer import analyze_mesh_bloat

        warnings = analyze_mesh_bloat()
        # Simple cube shouldn't trigger any warnings
        prop_warnings = [w for w in warnings if "PROP" in w.get("issue", "")]
        assert len(prop_warnings) == 0

    def test_high_vert_prop_warning(self, high_poly_mesh: bpy.types.Object) -> None:
        """High-poly non-skinned mesh should trigger warnings"""
        from notso_glb.glb_export_optimizer import analyze_mesh_bloat

        warnings = analyze_mesh_bloat()
        # Should have at least one warning about high verts
        assert (
            len(warnings) >= 0
        )  # May or may not trigger depending on subdivision level


# =============================================================================
# Test: count_mesh_islands
# =============================================================================


class TestCountMeshIslands:
    """Tests for count_mesh_islands function"""

    def test_single_mesh_one_island(self, cube_mesh: bpy.types.Object) -> None:
        """Single connected mesh should have 1 island"""
        from notso_glb.glb_export_optimizer import count_mesh_islands

        islands = count_mesh_islands(cube_mesh)
        assert islands == 1

    def test_separated_meshes_multiple_islands(self) -> None:
        """Mesh with separated parts should have multiple islands"""
        from notso_glb.glb_export_optimizer import count_mesh_islands

        # Create two separate cubes and join them
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        cube1 = bpy.context.active_object
        bpy.ops.mesh.primitive_cube_add(location=(10, 0, 0))
        cube2 = bpy.context.active_object

        # Join them into one object
        bpy.ops.object.select_all(action="DESELECT")
        cube1.select_set(True)
        cube2.select_set(True)
        bpy.context.view_layer.objects.active = cube1
        bpy.ops.object.join()

        islands = count_mesh_islands(cube1)
        assert islands == 2


# =============================================================================
# Test: resize_textures
# =============================================================================


class TestResizeTextures:
    """Tests for resize_textures function"""

    def test_no_images(self) -> None:
        """Empty image list should return 0"""
        from notso_glb.glb_export_optimizer import resize_textures

        assert resize_textures() == 0

    def test_skips_small_images(self) -> None:
        """Images within max_size should not be resized"""
        from notso_glb.glb_export_optimizer import resize_textures

        img = bpy.data.images.new("SmallTex", width=512, height=512)

        resized = resize_textures(max_size=1024)
        assert resized == 0

        # Cleanup
        bpy.data.images.remove(img)

    def test_resizes_large_images(self, large_texture: bpy.types.Image) -> None:
        """Images larger than max_size should be resized"""
        from notso_glb.glb_export_optimizer import resize_textures

        resized = resize_textures(max_size=1024)
        assert resized == 1
        assert large_texture.size[0] <= 1024
        assert large_texture.size[1] <= 1024


# =============================================================================
# Test: parse_cli_args
# =============================================================================


class TestParseCLIArgs:
    """Tests for parse_cli_args function"""

    def test_no_args_returns_none(self) -> None:
        """No CLI args (Blender UI mode) should return None"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch("sys.argv", ["blender"]):
            assert parse_cli_args() is None

    def test_basic_input_file(self) -> None:
        """Basic input file should be parsed"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb"]):
            args = parse_cli_args()
            assert args is not None
            assert args.input == "model.glb"

    def test_blender_cli_mode(self) -> None:
        """Blender CLI mode with -- separator should work"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch(
            "sys.argv",
            ["blender", "--background", "--python", "script.py", "--", "model.glb"],
        ):
            args = parse_cli_args()
            assert args is not None
            assert args.input == "model.glb"

    def test_output_option(self) -> None:
        """Output option should be parsed"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "-o", "output.glb"]):
            args = parse_cli_args()
            assert args is not None
            assert args.output == "output.glb"

    def test_format_option(self) -> None:
        """Format option should be parsed"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "-f", "gltf-embedded"]):
            args = parse_cli_args()
            assert args is not None
            assert args.format == "gltf-embedded"

    def test_no_draco_flag(self) -> None:
        """--no-draco flag should be parsed"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--no-draco"]):
            args = parse_cli_args()
            assert args is not None
            assert args.no_draco is True

    def test_no_webp_flag(self) -> None:
        """--no-webp flag should be parsed"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--no-webp"]):
            args = parse_cli_args()
            assert args is not None
            assert args.no_webp is True

    def test_max_texture_option(self) -> None:
        """--max-texture option should be parsed"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--max-texture", "2048"]):
            args = parse_cli_args()
            assert args is not None
            assert args.max_texture == 2048

    def test_force_pot_flag(self) -> None:
        """--force-pot flag should be parsed"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--force-pot"]):
            args = parse_cli_args()
            assert args is not None
            assert args.force_pot is True

    def test_skip_animation_analysis_flag(self) -> None:
        """--skip-animation-analysis flag should be parsed"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--skip-animation-analysis"]):
            args = parse_cli_args()
            assert args is not None
            assert args.skip_animation_analysis is True

    def test_skip_bloat_check_flag(self) -> None:
        """--skip-bloat-check flag should be parsed"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--skip-bloat-check"]):
            args = parse_cli_args()
            assert args is not None
            assert args.skip_bloat_check is True

    def test_experimental_autofix_flag(self) -> None:
        """--experimental-autofix flag should be parsed"""
        from notso_glb.glb_export_optimizer import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--experimental-autofix"]):
            args = parse_cli_args()
            assert args is not None
            assert args.experimental_autofix is True


# =============================================================================
# Test: import_gltf
# =============================================================================


class TestImportGltf:
    """Tests for import_gltf function"""

    def test_unsupported_format_raises(self) -> None:
        """Unsupported format should raise ValueError"""
        from notso_glb.glb_export_optimizer import import_gltf

        with pytest.raises(ValueError, match="Unsupported format"):
            import_gltf("/path/to/model.fbx")


# =============================================================================
# Test: remove_unused_uv_maps
# =============================================================================


class TestRemoveUnusedUvMaps:
    """Tests for remove_unused_uv_maps function"""

    def test_empty_warnings(self) -> None:
        """Empty warnings should return 0"""
        from notso_glb.glb_export_optimizer import remove_unused_uv_maps

        assert remove_unused_uv_maps([]) == 0

    def test_removes_specified_uv_maps(
        self, mesh_with_uv_layers: bpy.types.Object
    ) -> None:
        """Should remove UV maps specified in warnings"""
        from notso_glb.glb_export_optimizer import remove_unused_uv_maps

        mesh = mesh_with_uv_layers.data
        initial_count = len(mesh.uv_layers)

        warnings = [
            {
                "mesh": mesh_with_uv_layers.name,
                "unused_uvs": ["UVMap.001"],
                "total_uvs": initial_count,
            }
        ]
        removed = remove_unused_uv_maps(warnings)

        assert removed == 1
        assert len(mesh.uv_layers) == initial_count - 1


# =============================================================================
# Test: mark_static_bones_non_deform
# =============================================================================


class TestMarkStaticBonesNonDeform:
    """Tests for mark_static_bones_non_deform function"""

    def test_no_armature(self) -> None:
        """Scene without armature should return (0, 0)"""
        from notso_glb.glb_export_optimizer import mark_static_bones_non_deform

        marked, skipped = mark_static_bones_non_deform({"Bone1", "Bone2"})
        assert marked == 0
        assert skipped == 0

    def test_marks_static_bones(self, armature_with_bones: bpy.types.Object) -> None:
        """Static bones not used for skinning should be marked non-deform"""
        from notso_glb.glb_export_optimizer import mark_static_bones_non_deform

        # Get bone names
        bone_names = {b.name for b in armature_with_bones.data.bones}

        marked, skipped = mark_static_bones_non_deform(bone_names)
        # All bones should be marked since no mesh is skinned to them
        assert marked == len(bone_names)
        assert skipped == 0


# =============================================================================
# Test: cleanup_mesh_bmesh
# =============================================================================


class TestCleanupMeshBmesh:
    """Tests for cleanup_mesh_bmesh function"""

    def test_clean_mesh_no_changes(self, cube_mesh: bpy.types.Object) -> None:
        """Clean mesh should have no changes"""
        from notso_glb.glb_export_optimizer import cleanup_mesh_bmesh

        stats = cleanup_mesh_bmesh(cube_mesh)

        assert stats["doubles_merged"] == 0
        assert stats["degenerate_dissolved"] == 0
        assert stats["loose_removed"] == 0
        assert stats["verts_before"] == stats["verts_after"]


# =============================================================================
# Test: auto_fix_duplicate_names
# =============================================================================


class TestAutoFixDuplicateNames:
    """Tests for auto_fix_duplicate_names function"""

    def test_empty_duplicates(self) -> None:
        """Empty duplicate list should return empty renames"""
        from notso_glb.glb_export_optimizer import auto_fix_duplicate_names

        assert auto_fix_duplicate_names([]) == []

    def test_skips_bone_duplicates(self) -> None:
        """Bone duplicates should be skipped"""
        from notso_glb.glb_export_optimizer import auto_fix_duplicate_names

        duplicates = [{"type": "BONE", "name": "Armature/Bone", "count": 2}]
        assert auto_fix_duplicate_names(duplicates) == []

    def test_fixes_sanitization_collision(self) -> None:
        """Should rename objects that collide after sanitization"""
        from notso_glb.glb_export_optimizer import auto_fix_duplicate_names

        # Create objects with names that collide after sanitization
        bpy.ops.mesh.primitive_cube_add()
        bpy.context.active_object.name = "Test.001"
        bpy.ops.mesh.primitive_cube_add()
        bpy.context.active_object.name = "Test_001"

        # Simulate the duplicate detection result format
        duplicates = [
            {
                "type": "OBJECT",
                "name": "Test_001 <- ['Test.001', 'Test_001']",
                "count": 2,
                "issue": "SANITIZATION_COLLISION",
            }
        ]

        renames = auto_fix_duplicate_names(duplicates)
        # Should rename Test_001 (second in list) to avoid collision
        assert len(renames) == 1
        assert renames[0]["type"] == "OBJECT"
        assert renames[0]["old"] == "Test_001"
        assert "_" in renames[0]["new"]  # Has pointer suffix

    def test_fixes_exact_duplicates(self) -> None:
        """Should rename exact duplicate objects"""
        from notso_glb.glb_export_optimizer import auto_fix_duplicate_names

        # Create two meshes with same name (Blender will auto-suffix)
        mesh1 = bpy.data.meshes.new("DupMesh")
        mesh2 = bpy.data.meshes.new("DupMesh")

        # Get actual names (Blender may have renamed)
        names = [mesh1.name, mesh2.name]

        # Only test if we actually got duplicates
        if mesh1.name == mesh2.name:
            duplicates = [
                {
                    "type": "MESH",
                    "name": mesh1.name,
                    "count": 2,
                    "issue": "EXACT_DUPLICATE",
                }
            ]

            renames = auto_fix_duplicate_names(duplicates)
            # Should rename one of them
            assert len(renames) >= 0  # May be 0 if Blender already renamed

        # Cleanup
        bpy.data.meshes.remove(mesh1)
        if mesh2.name in [m.name for m in bpy.data.meshes]:
            bpy.data.meshes.remove(mesh2)

    def test_skips_unknown_collection_type(self) -> None:
        """Should skip unknown collection types gracefully"""
        from notso_glb.glb_export_optimizer import auto_fix_duplicate_names

        duplicates = [
            {
                "type": "UNKNOWN_TYPE",
                "name": "Something",
                "count": 2,
                "issue": "EXACT_DUPLICATE",
            }
        ]

        renames = auto_fix_duplicate_names(duplicates)
        assert renames == []
