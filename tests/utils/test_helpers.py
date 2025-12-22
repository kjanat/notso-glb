"""Tests for utility helper functions."""

from bpy.types import Object


class TestSanitizeGltfName:
    """Tests for sanitize_gltf_name function."""

    def test_simple_name_unchanged(self) -> None:
        """Simple alphanumeric names should remain unchanged."""
        from notso_glb.utils import sanitize_gltf_name

        assert sanitize_gltf_name("Cube") == "Cube"
        assert sanitize_gltf_name("mesh_001") == "mesh_001"
        assert sanitize_gltf_name("MyObject") == "MyObject"

    def test_dots_replaced_with_underscores(self) -> None:
        """Dots should be replaced with underscores."""
        from notso_glb.utils import sanitize_gltf_name

        assert sanitize_gltf_name("Cube.001") == "Cube_001"
        assert sanitize_gltf_name("mesh.data.001") == "mesh_data_001"

    def test_spaces_replaced_with_underscores(self) -> None:
        """Spaces should be replaced with underscores."""
        from notso_glb.utils import sanitize_gltf_name

        assert sanitize_gltf_name("My Object") == "My_Object"
        assert sanitize_gltf_name("a b c") == "a_b_c"

    def test_dashes_replaced_with_underscores(self) -> None:
        """Dashes should be replaced with underscores."""
        from notso_glb.utils import sanitize_gltf_name

        assert sanitize_gltf_name("my-object") == "my_object"
        assert sanitize_gltf_name("mesh-001-final") == "mesh_001_final"

    def test_leading_digit_gets_prefix(self) -> None:
        """Names starting with digits should get underscore prefix."""
        from notso_glb.utils import sanitize_gltf_name

        assert sanitize_gltf_name("001_cube") == "_001_cube"
        assert sanitize_gltf_name("3DModel") == "_3DModel"

    def test_special_characters_replaced(self) -> None:
        """Special characters should be replaced with underscores."""
        from notso_glb.utils import sanitize_gltf_name

        assert sanitize_gltf_name("cube@home") == "cube_home"
        assert sanitize_gltf_name("mesh#1") == "mesh_1"
        assert sanitize_gltf_name("a!b@c#d") == "a_b_c_d"

    def test_empty_string(self) -> None:
        """Empty string should return empty string."""
        from notso_glb.utils import sanitize_gltf_name

        assert sanitize_gltf_name("") == ""


class TestNearestPowerOfTwo:
    """Tests for nearest_power_of_two function."""

    def test_exact_powers_of_two(self) -> None:
        """Exact powers of two should return themselves."""
        from notso_glb.utils import nearest_power_of_two

        assert nearest_power_of_two(1) == 1
        assert nearest_power_of_two(2) == 2
        assert nearest_power_of_two(4) == 4
        assert nearest_power_of_two(256) == 256
        assert nearest_power_of_two(1024) == 1024
        assert nearest_power_of_two(2048) == 2048

    def test_rounds_up(self) -> None:
        """Values closer to higher power should round up."""
        from notso_glb.utils import nearest_power_of_two

        assert nearest_power_of_two(3) == 4
        assert nearest_power_of_two(7) == 8
        assert nearest_power_of_two(1600) == 2048

    def test_rounds_down(self) -> None:
        """Values closer to lower power should round down."""
        from notso_glb.utils import nearest_power_of_two

        assert nearest_power_of_two(5) == 4
        assert nearest_power_of_two(1000) == 1024

    def test_zero_and_negative(self) -> None:
        """Zero and negative values should return 1."""
        from notso_glb.utils import nearest_power_of_two

        assert nearest_power_of_two(0) == 1
        assert nearest_power_of_two(-5) == 1


class TestGetSceneStats:
    """Tests for get_scene_stats function."""

    def test_empty_scene(self) -> None:
        """Empty scene should return zeros."""
        from notso_glb.utils import get_scene_stats

        stats = get_scene_stats()
        assert stats["meshes"] == 0
        assert stats["vertices"] == 0
        assert stats["bones"] == 0
        assert stats["actions"] == 0

    def test_scene_with_meshes(self, cube_mesh: Object) -> None:
        """Scene with meshes should count correctly."""
        from notso_glb.utils import get_scene_stats

        stats = get_scene_stats()
        assert stats["meshes"] == 1
        assert stats["vertices"] == 8  # Cube has 8 vertices

    def test_scene_with_armature(self, armature_with_bones: Object) -> None:
        """Scene with armature should count bones."""
        from notso_glb.utils import get_scene_stats

        stats = get_scene_stats()
        assert stats["bones"] >= 1
