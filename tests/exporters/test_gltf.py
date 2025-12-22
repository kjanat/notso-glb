"""Tests for glTF export module."""

import pytest


class TestImportGltf:
    """Tests for import_gltf function."""

    def test_unsupported_format_raises(self) -> None:
        """Unsupported format should raise ValueError."""
        from notso_glb.exporters import import_gltf

        with pytest.raises(ValueError, match="Unsupported format"):
            import_gltf("/path/to/model.fbx")
