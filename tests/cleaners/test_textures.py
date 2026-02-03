"""Tests for texture cleanup module."""

import bpy


class TestResizeTextures:
    """Tests for resize_textures function."""

    def test_no_images(self) -> None:
        """Empty image list should return 0."""
        from notso_glb.cleaners import resize_textures

        assert resize_textures() == 0

    def test_skips_small_images(self) -> None:
        """Images within max_size should not be resized."""
        from notso_glb.cleaners import resize_textures

        img = bpy.data.images.new("SmallTex", width=512, height=512)

        resized = resize_textures(max_size=1024)
        assert resized == 0

        bpy.data.images.remove(img)

    def test_resizes_large_images(self, large_texture: bpy.types.Image) -> None:
        """Images larger than max_size should be resized."""
        from notso_glb.cleaners import resize_textures

        resized = resize_textures(max_size=1024)
        assert resized == 1
        assert large_texture.size[0] <= 1024
        assert large_texture.size[1] <= 1024
