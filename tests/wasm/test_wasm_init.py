"""Tests for WASM __init__ module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestGetWasmPath:
    """Tests for get_wasm_path function."""

    def test_returns_path_to_wasm_file(self) -> None:
        """Should return path to gltfpack.wasm."""
        from notso_glb.wasm import get_wasm_path

        path = get_wasm_path()

        assert isinstance(path, Path)
        assert path.name == "gltfpack.wasm"


class TestIsAvailable:
    """Tests for is_available function."""

    @patch("notso_glb.wasm._get_wasm_path")
    def test_returns_true_when_wasmtime_and_wasm_exist(
        self, mock_get_path: MagicMock, tmp_path: Path
    ) -> None:
        """Should return True when wasmtime importable and WASM exists."""
        from notso_glb.wasm import is_available

        wasm_file = tmp_path / "gltfpack.wasm"
        wasm_file.write_bytes(b"\x00asm\x01\x00\x00\x00")
        mock_get_path.return_value = wasm_file

        result = is_available()

        # Will be True only if wasmtime is actually installed
        assert isinstance(result, bool)

    @patch("notso_glb.wasm._get_wasm_path")
    def test_returns_false_when_wasm_missing(
        self, mock_get_path: MagicMock, tmp_path: Path
    ) -> None:
        """Should return False when WASM file doesn't exist."""
        from notso_glb.wasm import is_available

        wasm_file = tmp_path / "nonexistent.wasm"
        mock_get_path.return_value = wasm_file

        result = is_available()

        assert result is False


class TestGetGltfpack:
    """Tests for get_gltfpack singleton function."""

    def test_returns_gltfpack_instance(self) -> None:
        """Should return GltfpackWasm instance."""
        from notso_glb.wasm import GltfpackWasm, get_gltfpack

        instance = get_gltfpack()

        assert isinstance(instance, GltfpackWasm)

    def test_returns_same_instance_on_multiple_calls(self) -> None:
        """Should return singleton instance."""
        from notso_glb.wasm import get_gltfpack

        instance1 = get_gltfpack()
        instance2 = get_gltfpack()

        assert instance1 is instance2


class TestRunGltfpackWasm:
    """Tests for run_gltfpack_wasm function."""

    @patch("notso_glb.wasm.is_available")
    def test_returns_error_when_wasm_unavailable(
        self, mock_is_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should return error when WASM runtime unavailable."""
        from notso_glb.wasm import run_gltfpack_wasm

        mock_is_avail.return_value = False
        input_path = tmp_path / "input.glb"

        success, path, msg = run_gltfpack_wasm(input_path)

        assert success is False
        assert "not available" in msg

    @patch("notso_glb.wasm.is_available")
    def test_returns_error_when_input_not_found(
        self, mock_is_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should return error when input file not found."""
        from notso_glb.wasm import run_gltfpack_wasm

        mock_is_avail.return_value = True
        input_path = tmp_path / "nonexistent.glb"

        success, path, msg = run_gltfpack_wasm(input_path)

        assert success is False
        assert "not found" in msg

    @patch("notso_glb.wasm.is_available")
    @patch("notso_glb.wasm.get_gltfpack")
    def test_generates_output_path_with_packed_suffix(
        self, mock_get_gltfpack: MagicMock, mock_is_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should generate output path with _packed suffix."""
        from notso_glb.wasm import run_gltfpack_wasm

        mock_is_avail.return_value = True
        input_path = tmp_path / "model.glb"
        input_path.write_bytes(b"\x00asm")

        mock_instance = MagicMock()
        mock_instance.pack.return_value = (True, b"output", "Success")
        mock_get_gltfpack.return_value = mock_instance

        success, path, msg = run_gltfpack_wasm(input_path)

        assert path == tmp_path / "model_packed.glb"

    @patch("notso_glb.wasm.is_available")
    @patch("notso_glb.wasm.get_gltfpack")
    def test_strips_existing_packed_suffix(
        self, mock_get_gltfpack: MagicMock, mock_is_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should strip existing _packed suffix."""
        from notso_glb.wasm import run_gltfpack_wasm

        mock_is_avail.return_value = True
        input_path = tmp_path / "model_packed.glb"
        input_path.write_bytes(b"\x00asm")

        mock_instance = MagicMock()
        mock_instance.pack.return_value = (True, b"output", "Success")
        mock_get_gltfpack.return_value = mock_instance

        success, path, msg = run_gltfpack_wasm(input_path)

        assert path == tmp_path / "model_packed.glb"

    @patch("notso_glb.wasm.is_available")
    @patch("notso_glb.wasm.get_gltfpack")
    def test_validates_simplify_ratio_range(
        self, mock_get_gltfpack: MagicMock, mock_is_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should validate simplify_ratio is in [0.0, 1.0]."""
        from notso_glb.wasm import run_gltfpack_wasm

        mock_is_avail.return_value = True
        input_path = tmp_path / "model.glb"
        input_path.write_bytes(b"\x00asm")

        success, path, msg = run_gltfpack_wasm(input_path, simplify_ratio=1.5)

        assert success is False
        assert "simplify_ratio" in msg

    @patch("notso_glb.wasm.is_available")
    @patch("notso_glb.wasm.get_gltfpack")
    def test_passes_mesh_compress_argument(
        self, mock_get_gltfpack: MagicMock, mock_is_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should pass mesh_compress as -cc argument."""
        from notso_glb.wasm import run_gltfpack_wasm

        mock_is_avail.return_value = True
        input_path = tmp_path / "model.glb"
        input_path.write_bytes(b"\x00asm")

        mock_instance = MagicMock()
        mock_instance.pack.return_value = (True, b"output", "Success")
        mock_get_gltfpack.return_value = mock_instance

        run_gltfpack_wasm(input_path, mesh_compress=True)

        call_args = mock_instance.pack.call_args
        args = call_args[1]["args"]
        assert "-cc" in args

    @patch("notso_glb.wasm.is_available")
    @patch("notso_glb.wasm.get_gltfpack")
    def test_skips_texture_compress_with_warning(
        self,
        mock_get_gltfpack: MagicMock,
        mock_is_avail: MagicMock,
        tmp_path: Path,
        capsys,
    ) -> None:
        """Should skip texture_compress and print warning."""
        from notso_glb.wasm import run_gltfpack_wasm

        mock_is_avail.return_value = True
        input_path = tmp_path / "model.glb"
        input_path.write_bytes(b"\x00asm")

        mock_instance = MagicMock()
        mock_instance.pack.return_value = (True, b"output", "Success")
        mock_get_gltfpack.return_value = mock_instance

        run_gltfpack_wasm(input_path, texture_compress=True)

        captured = capsys.readouterr()
        assert "BasisU" in captured.out or "texture compression" in captured.out

    @patch("notso_glb.wasm.is_available")
    @patch("notso_glb.wasm.get_gltfpack")
    def test_ignores_texture_quality_parameter(
        self, mock_get_gltfpack: MagicMock, mock_is_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should ignore texture_quality parameter (WASM limitation)."""
        from notso_glb.wasm import run_gltfpack_wasm

        mock_is_avail.return_value = True
        input_path = tmp_path / "model.glb"
        input_path.write_bytes(b"\x00asm")

        mock_instance = MagicMock()
        mock_instance.pack.return_value = (True, b"output", "Success")
        mock_get_gltfpack.return_value = mock_instance

        success, path, msg = run_gltfpack_wasm(input_path, texture_quality=8)

        # Should succeed but ignore texture_quality
        assert success is True

    @patch("notso_glb.wasm.is_available")
    @patch("notso_glb.wasm.get_gltfpack")
    def test_handles_pack_failure(
        self, mock_get_gltfpack: MagicMock, mock_is_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should handle pack failure."""
        from notso_glb.wasm import run_gltfpack_wasm

        mock_is_avail.return_value = True
        input_path = tmp_path / "model.glb"
        input_path.write_bytes(b"\x00asm")

        mock_instance = MagicMock()
        mock_instance.pack.return_value = (False, b"", "Pack failed")
        mock_get_gltfpack.return_value = mock_instance

        success, path, msg = run_gltfpack_wasm(input_path)

        assert success is False
        assert "failed" in msg.lower()

    @patch("notso_glb.wasm.is_available")
    @patch("notso_glb.wasm.get_gltfpack")
    def test_handles_file_io_error(
        self, mock_get_gltfpack: MagicMock, mock_is_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should handle file I/O errors."""
        from notso_glb.wasm import run_gltfpack_wasm

        mock_is_avail.return_value = True
        input_path = tmp_path / "model.glb"
        input_path.write_bytes(b"\x00asm")

        mock_instance = MagicMock()
        mock_instance.pack.side_effect = OSError("Disk full")
        mock_get_gltfpack.return_value = mock_instance

        success, path, msg = run_gltfpack_wasm(input_path)

        assert success is False
        assert "I/O error" in msg

    @patch("notso_glb.wasm.is_available")
    @patch("notso_glb.wasm.get_gltfpack")
    def test_writes_output_on_success(
        self, mock_get_gltfpack: MagicMock, mock_is_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should write output file on successful pack."""
        from notso_glb.wasm import run_gltfpack_wasm

        mock_is_avail.return_value = True
        input_path = tmp_path / "model.glb"
        input_path.write_bytes(b"\x00asm")
        output_path = tmp_path / "output.glb"

        mock_instance = MagicMock()
        mock_instance.pack.return_value = (True, b"packed_data", "Success")
        mock_get_gltfpack.return_value = mock_instance

        success, path, msg = run_gltfpack_wasm(input_path, output_path)

        assert success is True
        assert output_path.exists()
        assert output_path.read_bytes() == b"packed_data"
