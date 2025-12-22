"""Tests for constants module."""


class TestBloatThresholds:
    """Tests for BLOAT_THRESHOLDS configuration."""

    def test_thresholds_exist(self) -> None:
        """All expected threshold keys should exist."""
        from notso_glb.utils.constants import BLOAT_THRESHOLDS

        assert "prop_warning" in BLOAT_THRESHOLDS
        assert "prop_critical" in BLOAT_THRESHOLDS
        assert "repetitive_islands" in BLOAT_THRESHOLDS
        assert "repetitive_verts" in BLOAT_THRESHOLDS
        assert "scene_total" in BLOAT_THRESHOLDS

    def test_threshold_values_sensible(self) -> None:
        """Threshold values should be sensible for web delivery."""
        from notso_glb.utils.constants import BLOAT_THRESHOLDS

        assert BLOAT_THRESHOLDS["prop_warning"] < BLOAT_THRESHOLDS["prop_critical"]
        assert BLOAT_THRESHOLDS["scene_total"] > BLOAT_THRESHOLDS["prop_critical"]


class TestDefaultConfig:
    """Tests for DEFAULT_CONFIG constant."""

    def test_config_has_required_keys(self) -> None:
        """DEFAULT_CONFIG should have all required keys."""
        from notso_glb.utils.constants import DEFAULT_CONFIG

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
            assert key in DEFAULT_CONFIG

    def test_config_default_values(self) -> None:
        """DEFAULT_CONFIG defaults should be sensible."""
        from notso_glb.utils.constants import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["output_path"] is None
        assert DEFAULT_CONFIG["use_draco"] is True
        assert DEFAULT_CONFIG["use_webp"] is True
        assert DEFAULT_CONFIG["max_texture_size"] == 1024
        assert DEFAULT_CONFIG["experimental_autofix"] is False
