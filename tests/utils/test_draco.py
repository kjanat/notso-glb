"""Tests for Draco compression detection utility."""

from __future__ import annotations

import json
import struct
from pathlib import Path


class TestHasDracoCompression:
    """Tests for has_draco_compression function."""

    def test_detects_draco_in_glb_extensions_used(self, tmp_path: Path) -> None:
        """Should detect Draco compression in GLB extensionsUsed."""
        from notso_glb.utils.draco import has_draco_compression

        glb_path = tmp_path / "draco.glb"
        _create_glb_file(
            glb_path, {"extensionsUsed": ["KHR_draco_mesh_compression"]}
        )

        result = has_draco_compression(glb_path)

        assert result is True

    def test_detects_draco_in_glb_extensions_required(self, tmp_path: Path) -> None:
        """Should detect Draco compression in GLB extensionsRequired."""
        from notso_glb.utils.draco import has_draco_compression

        glb_path = tmp_path / "draco.glb"
        _create_glb_file(
            glb_path, {"extensionsRequired": ["KHR_draco_mesh_compression"]}
        )

        result = has_draco_compression(glb_path)

        assert result is True

    def test_returns_false_for_glb_without_draco(self, tmp_path: Path) -> None:
        """Should return False for GLB without Draco compression."""
        from notso_glb.utils.draco import has_draco_compression

        glb_path = tmp_path / "no_draco.glb"
        _create_glb_file(glb_path, {"asset": {"version": "2.0"}})

        result = has_draco_compression(glb_path)

        assert result is False

    def test_detects_draco_in_gltf_extensions_used(self, tmp_path: Path) -> None:
        """Should detect Draco compression in glTF extensionsUsed."""
        from notso_glb.utils.draco import has_draco_compression

        gltf_path = tmp_path / "draco.gltf"
        gltf_json = {
            "asset": {"version": "2.0"},
            "extensionsUsed": ["KHR_draco_mesh_compression"],
        }
        gltf_path.write_text(json.dumps(gltf_json), encoding="utf-8")

        result = has_draco_compression(gltf_path)

        assert result is True

    def test_detects_draco_in_gltf_extensions_required(self, tmp_path: Path) -> None:
        """Should detect Draco compression in glTF extensionsRequired."""
        from notso_glb.utils.draco import has_draco_compression

        gltf_path = tmp_path / "draco.gltf"
        gltf_json = {
            "asset": {"version": "2.0"},
            "extensionsRequired": ["KHR_draco_mesh_compression"],
        }
        gltf_path.write_text(json.dumps(gltf_json), encoding="utf-8")

        result = has_draco_compression(gltf_path)

        assert result is True

    def test_returns_false_for_gltf_without_draco(self, tmp_path: Path) -> None:
        """Should return False for glTF without Draco compression."""
        from notso_glb.utils.draco import has_draco_compression

        gltf_path = tmp_path / "no_draco.gltf"
        gltf_json = {"asset": {"version": "2.0"}}
        gltf_path.write_text(json.dumps(gltf_json), encoding="utf-8")

        result = has_draco_compression(gltf_path)

        assert result is False

    def test_returns_false_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Should return False for non-existent file."""
        from notso_glb.utils.draco import has_draco_compression

        nonexistent = tmp_path / "nonexistent.glb"

        result = has_draco_compression(nonexistent)

        assert result is False

    def test_returns_false_for_unsupported_extension(self, tmp_path: Path) -> None:
        """Should return False for unsupported file extension."""
        from notso_glb.utils.draco import has_draco_compression

        txt_path = tmp_path / "file.txt"
        txt_path.write_text("not a gltf file")

        result = has_draco_compression(txt_path)

        assert result is False

    def test_returns_false_for_invalid_glb(self, tmp_path: Path) -> None:
        """Should return False for invalid GLB file."""
        from notso_glb.utils.draco import has_draco_compression

        glb_path = tmp_path / "invalid.glb"
        glb_path.write_bytes(b"not a valid glb")

        result = has_draco_compression(glb_path)

        assert result is False

    def test_returns_false_for_invalid_gltf(self, tmp_path: Path) -> None:
        """Should return False for invalid glTF JSON."""
        from notso_glb.utils.draco import has_draco_compression

        gltf_path = tmp_path / "invalid.gltf"
        gltf_path.write_text("not valid json", encoding="utf-8")

        result = has_draco_compression(gltf_path)

        assert result is False

    def test_returns_false_for_truncated_glb(self, tmp_path: Path) -> None:
        """Should return False for truncated GLB file."""
        from notso_glb.utils.draco import has_draco_compression

        glb_path = tmp_path / "truncated.glb"
        # Only write the magic number, truncated header
        glb_path.write_bytes(struct.pack("<I", 0x46546C67))

        result = has_draco_compression(glb_path)

        assert result is False

    def test_handles_glb_with_other_extensions(self, tmp_path: Path) -> None:
        """Should return False when GLB has other extensions but not Draco."""
        from notso_glb.utils.draco import has_draco_compression

        glb_path = tmp_path / "other_ext.glb"
        _create_glb_file(
            glb_path,
            {
                "asset": {"version": "2.0"},
                "extensionsUsed": ["KHR_materials_unlit", "KHR_texture_transform"],
            },
        )

        result = has_draco_compression(glb_path)

        assert result is False

    def test_handles_pathlib_path(self, tmp_path: Path) -> None:
        """Should handle Path objects."""
        from notso_glb.utils.draco import has_draco_compression

        glb_path = tmp_path / "test.glb"
        _create_glb_file(
            glb_path, {"extensionsUsed": ["KHR_draco_mesh_compression"]}
        )

        result = has_draco_compression(glb_path)

        assert result is True

    def test_handles_string_path(self, tmp_path: Path) -> None:
        """Should handle string paths."""
        from notso_glb.utils.draco import has_draco_compression

        glb_path = tmp_path / "test.glb"
        _create_glb_file(
            glb_path, {"extensionsUsed": ["KHR_draco_mesh_compression"]}
        )

        result = has_draco_compression(str(glb_path))

        assert result is True


class TestCheckGlbForDraco:
    """Tests for _check_glb_for_draco internal function."""

    def test_handles_glb_with_padding(self, tmp_path: Path) -> None:
        """Should handle GLB files with null-padded JSON chunk."""
        from notso_glb.utils.draco import _check_glb_for_draco

        glb_path = tmp_path / "padded.glb"
        _create_glb_file(
            glb_path,
            {"extensionsUsed": ["KHR_draco_mesh_compression"]},
            add_padding=True,
        )

        result = _check_glb_for_draco(glb_path)

        assert result is True

    def test_returns_false_for_wrong_magic(self, tmp_path: Path) -> None:
        """Should return False for file with wrong magic number."""
        from notso_glb.utils.draco import _check_glb_for_draco

        glb_path = tmp_path / "wrong_magic.glb"
        # Write header with wrong magic number
        header = struct.pack("<III", 0x12345678, 2, 24)
        glb_path.write_bytes(header)

        result = _check_glb_for_draco(glb_path)

        assert result is False


class TestJsonHasDraco:
    """Tests for _json_has_draco internal function."""

    def test_detects_draco_in_extensions_used(self) -> None:
        """Should detect Draco in extensionsUsed."""
        from notso_glb.utils.draco import _json_has_draco

        gltf_json = {"extensionsUsed": ["KHR_draco_mesh_compression"]}

        result = _json_has_draco(gltf_json)

        assert result is True

    def test_detects_draco_in_extensions_required(self) -> None:
        """Should detect Draco in extensionsRequired."""
        from notso_glb.utils.draco import _json_has_draco

        gltf_json = {"extensionsRequired": ["KHR_draco_mesh_compression"]}

        result = _json_has_draco(gltf_json)

        assert result is True

    def test_detects_draco_in_both_arrays(self) -> None:
        """Should detect Draco when in both extensionsUsed and extensionsRequired."""
        from notso_glb.utils.draco import _json_has_draco

        gltf_json = {
            "extensionsUsed": ["KHR_draco_mesh_compression"],
            "extensionsRequired": ["KHR_draco_mesh_compression"],
        }

        result = _json_has_draco(gltf_json)

        assert result is True

    def test_returns_false_for_empty_dict(self) -> None:
        """Should return False for empty glTF JSON."""
        from notso_glb.utils.draco import _json_has_draco

        result = _json_has_draco({})

        assert result is False

    def test_returns_false_for_empty_extensions_arrays(self) -> None:
        """Should return False when extension arrays are empty."""
        from notso_glb.utils.draco import _json_has_draco

        gltf_json = {"extensionsUsed": [], "extensionsRequired": []}

        result = _json_has_draco(gltf_json)

        assert result is False


def _create_glb_file(
    path: Path, gltf_json: dict, add_padding: bool = False
) -> None:
    """Helper to create a minimal GLB file for testing."""
    # Encode JSON
    json_str = json.dumps(gltf_json)
    json_bytes = json_str.encode("utf-8")

    # Add padding to align to 4 bytes (GLB spec requirement)
    padding_length = (4 - (len(json_bytes) % 4)) % 4
    if add_padding:
        padding_length += 4  # Add extra padding for testing
    json_bytes += b"\x00" * padding_length

    # JSON chunk: length + type (0x4E4F534A = "JSON") + data
    json_chunk = struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes

    # GLB header: magic + version + total length
    total_length = 12 + len(json_chunk)
    header = struct.pack("<III", 0x46546C67, 2, total_length)

    # Write GLB file
    path.write_bytes(header + json_chunk)
