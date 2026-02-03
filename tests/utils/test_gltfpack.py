"""Tests for gltfpack utility wrapper."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestFindGltfpack:
    """Tests for find_gltfpack function."""

    @patch("notso_glb.utils.gltfpack.shutil.which")
    def test_finds_gltfpack_in_path(self, mock_which: MagicMock) -> None:
        """Should find gltfpack executable in PATH."""
        from notso_glb.utils.gltfpack import find_gltfpack

        mock_which.return_value = "/usr/local/bin/gltfpack"

        result = find_gltfpack()

        assert result == "/usr/local/bin/gltfpack"
        mock_which.assert_called_once_with("gltfpack")

    @patch("notso_glb.utils.gltfpack.shutil.which")
    def test_returns_none_when_not_found(self, mock_which: MagicMock) -> None:
        """Should return None when gltfpack not in PATH."""
        from notso_glb.utils.gltfpack import find_gltfpack

        mock_which.return_value = None

        result = find_gltfpack()

        assert result is None


class TestSelectBackend:
    """Tests for _select_backend function."""

    @patch("notso_glb.utils.gltfpack._wasm_available")
    def test_forces_native_backend(
        self, mock_wasm_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should force native backend when ENV_FORCE_NATIVE is set."""
        from notso_glb.utils.gltfpack import _select_backend

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")

        with patch.dict("os.environ", {"NOTSO_GLB_FORCE_GLTFPACK_NATIVE": "1"}):
            use_wasm, error = _select_backend(input_path, False, "/usr/bin/gltfpack")

        assert use_wasm is False
        assert error is None

    @patch("notso_glb.utils.gltfpack._wasm_available")
    def test_forces_wasm_backend(
        self, mock_wasm_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should force WASM backend when ENV_FORCE_WASM is set."""
        from notso_glb.utils.gltfpack import _select_backend

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")
        mock_wasm_avail.return_value = True

        with patch.dict("os.environ", {"NOTSO_GLB_FORCE_GLTFPACK_WASM": "1"}):
            use_wasm, error = _select_backend(input_path, False, None)

        assert use_wasm is True
        assert error is None

    def test_errors_when_both_force_flags_set(self, tmp_path: Path) -> None:
        """Should error when both force flags are set."""
        from notso_glb.utils.gltfpack import _select_backend

        input_path = tmp_path / "input.glb"

        with patch.dict(
            "os.environ",
            {
                "NOTSO_GLB_FORCE_GLTFPACK_NATIVE": "1",
                "NOTSO_GLB_FORCE_GLTFPACK_WASM": "1",
            },
        ):
            use_wasm, error = _select_backend(input_path, False, None)

        assert use_wasm is None
        assert error is not None
        assert error[0] is False

    @patch("notso_glb.utils.gltfpack._wasm_available")
    def test_prefers_native_by_default(
        self, mock_wasm_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should prefer native over WASM by default."""
        from notso_glb.utils.gltfpack import _select_backend

        input_path = tmp_path / "input.glb"
        mock_wasm_avail.return_value = True

        use_wasm, error = _select_backend(input_path, False, "/usr/bin/gltfpack")

        assert use_wasm is False
        assert error is None

    @patch("notso_glb.utils.gltfpack._wasm_available")
    def test_uses_wasm_when_prefer_wasm_true(
        self, mock_wasm_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should use WASM when prefer_wasm=True."""
        from notso_glb.utils.gltfpack import _select_backend

        input_path = tmp_path / "input.glb"
        mock_wasm_avail.return_value = True

        use_wasm, error = _select_backend(input_path, True, "/usr/bin/gltfpack")

        assert use_wasm is True
        assert error is None

    @patch("notso_glb.utils.gltfpack._wasm_available")
    def test_falls_back_to_native_when_wasm_unavailable(
        self, mock_wasm_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should fall back to native when WASM unavailable."""
        from notso_glb.utils.gltfpack import _select_backend

        input_path = tmp_path / "input.glb"
        mock_wasm_avail.return_value = False

        use_wasm, error = _select_backend(input_path, True, "/usr/bin/gltfpack")

        assert use_wasm is False
        assert error is None

    @patch("notso_glb.utils.gltfpack._wasm_available")
    def test_errors_when_no_backend_available(
        self, mock_wasm_avail: MagicMock, tmp_path: Path
    ) -> None:
        """Should error when no backend available."""
        from notso_glb.utils.gltfpack import _select_backend

        input_path = tmp_path / "input.glb"
        mock_wasm_avail.return_value = False

        use_wasm, error = _select_backend(input_path, False, None)

        assert use_wasm is None
        assert error is not None
        assert "not found" in error[2]


class TestResolveOutputPath:
    """Tests for _resolve_output_path function."""

    def test_uses_provided_output_path(self, tmp_path: Path) -> None:
        """Should use provided output path."""
        from notso_glb.utils.gltfpack import _resolve_output_path

        input_path = tmp_path / "input.glb"
        output_path = tmp_path / "output.glb"

        result = _resolve_output_path(input_path, output_path)

        assert result == output_path

    def test_defaults_to_packed_suffix(self, tmp_path: Path) -> None:
        """Should default to _packed suffix."""
        from notso_glb.utils.gltfpack import _resolve_output_path

        input_path = tmp_path / "model.glb"

        result = _resolve_output_path(input_path, None)

        assert result == tmp_path / "model_packed.glb"

    def test_strips_existing_packed_suffix(self, tmp_path: Path) -> None:
        """Should strip existing _packed suffix."""
        from notso_glb.utils.gltfpack import _resolve_output_path

        input_path = tmp_path / "model_packed.glb"

        result = _resolve_output_path(input_path, None)

        assert result == tmp_path / "model_packed.glb"


class TestValidateSimplifyRatio:
    """Tests for _validate_simplify_ratio function."""

    def test_accepts_valid_ratio(self, tmp_path: Path) -> None:
        """Should accept valid ratio in range [0.0, 1.0]."""
        from notso_glb.utils.gltfpack import _validate_simplify_ratio

        input_path = tmp_path / "input.glb"

        ratio, error = _validate_simplify_ratio(0.5, input_path)

        assert ratio == 0.5
        assert error is None

    def test_accepts_none(self, tmp_path: Path) -> None:
        """Should accept None."""
        from notso_glb.utils.gltfpack import _validate_simplify_ratio

        input_path = tmp_path / "input.glb"

        ratio, error = _validate_simplify_ratio(None, input_path)

        assert ratio is None
        assert error is None

    def test_rejects_ratio_below_zero(self, tmp_path: Path) -> None:
        """Should reject ratio below 0.0."""
        from notso_glb.utils.gltfpack import _validate_simplify_ratio

        input_path = tmp_path / "input.glb"

        ratio, error = _validate_simplify_ratio(-0.1, input_path)

        assert ratio is None
        assert error is not None
        assert "must be in [0.0, 1.0]" in error[2]

    def test_rejects_ratio_above_one(self, tmp_path: Path) -> None:
        """Should reject ratio above 1.0."""
        from notso_glb.utils.gltfpack import _validate_simplify_ratio

        input_path = tmp_path / "input.glb"

        ratio, error = _validate_simplify_ratio(1.5, input_path)

        assert ratio is None
        assert error is not None


class TestValidateTextureQuality:
    """Tests for _validate_texture_quality function."""

    def test_accepts_valid_quality(self, tmp_path: Path) -> None:
        """Should accept valid quality in range [1, 10]."""
        from notso_glb.utils.gltfpack import _validate_texture_quality

        input_path = tmp_path / "input.glb"

        quality, error = _validate_texture_quality(8, input_path)

        assert quality == 8
        assert error is None

    def test_accepts_none(self, tmp_path: Path) -> None:
        """Should accept None."""
        from notso_glb.utils.gltfpack import _validate_texture_quality

        input_path = tmp_path / "input.glb"

        quality, error = _validate_texture_quality(None, input_path)

        assert quality is None
        assert error is None

    def test_rejects_quality_below_one(self, tmp_path: Path) -> None:
        """Should reject quality below 1."""
        from notso_glb.utils.gltfpack import _validate_texture_quality

        input_path = tmp_path / "input.glb"

        quality, error = _validate_texture_quality(0, input_path)

        assert quality is None
        assert error is not None

    def test_rejects_quality_above_ten(self, tmp_path: Path) -> None:
        """Should reject quality above 10."""
        from notso_glb.utils.gltfpack import _validate_texture_quality

        input_path = tmp_path / "input.glb"

        quality, error = _validate_texture_quality(11, input_path)

        assert quality is None
        assert error is not None

    def test_rejects_boolean(self, tmp_path: Path) -> None:
        """Should reject boolean values."""
        from notso_glb.utils.gltfpack import _validate_texture_quality

        input_path = tmp_path / "input.glb"

        quality, error = _validate_texture_quality(True, input_path)

        assert quality is None
        assert error is not None

    def test_converts_integer_float(self, tmp_path: Path) -> None:
        """Should convert integer float to int."""
        from notso_glb.utils.gltfpack import _validate_texture_quality

        input_path = tmp_path / "input.glb"

        quality, error = _validate_texture_quality(5.0, input_path)

        assert quality == 5
        assert error is None

    def test_rejects_non_integer_float(self, tmp_path: Path) -> None:
        """Should reject non-integer float."""
        from notso_glb.utils.gltfpack import _validate_texture_quality

        input_path = tmp_path / "input.glb"

        quality, error = _validate_texture_quality(5.5, input_path)

        assert quality is None
        assert error is not None


class TestRunNativeGltfpack:
    """Tests for _run_native_gltfpack function."""

    @patch("notso_glb.utils.gltfpack.subprocess.run")
    def test_successful_execution(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should execute gltfpack successfully."""
        from notso_glb.utils.gltfpack import _run_native_gltfpack

        output_path = tmp_path / "output.glb"
        output_path.write_bytes(b"test")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        success, path, msg = _run_native_gltfpack(
            ["gltfpack", "-i", "input.glb", "-o", str(output_path)], output_path
        )

        assert success is True
        assert path == output_path
        assert msg == "Success"

    @patch("notso_glb.utils.gltfpack.subprocess.run")
    def test_handles_nonzero_returncode(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Should handle non-zero return code."""
        from notso_glb.utils.gltfpack import _run_native_gltfpack

        output_path = tmp_path / "output.glb"

        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Error processing file"
        )

        success, path, msg = _run_native_gltfpack(["gltfpack"], output_path)

        assert success is False
        assert "failed" in msg.lower()

    @patch("notso_glb.utils.gltfpack.subprocess.run")
    def test_handles_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should handle subprocess timeout."""
        from notso_glb.utils.gltfpack import _run_native_gltfpack

        output_path = tmp_path / "output.glb"
        mock_run.side_effect = subprocess.TimeoutExpired("gltfpack", 300)

        success, path, msg = _run_native_gltfpack(["gltfpack"], output_path)

        assert success is False
        assert "timed out" in msg.lower()

    @patch("notso_glb.utils.gltfpack.subprocess.run")
    def test_handles_subprocess_error(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Should handle subprocess errors."""
        from notso_glb.utils.gltfpack import _run_native_gltfpack

        output_path = tmp_path / "output.glb"
        mock_run.side_effect = OSError("Command not found")

        success, path, msg = _run_native_gltfpack(["gltfpack"], output_path)

        assert success is False
        assert "error" in msg.lower()


class TestRunGltfpack:
    """Tests for run_gltfpack function."""

    @patch("notso_glb.utils.gltfpack.find_gltfpack")
    @patch("notso_glb.utils.gltfpack._run_native_gltfpack")
    def test_runs_with_native_backend(
        self, mock_run_native: MagicMock, mock_find: MagicMock, tmp_path: Path
    ) -> None:
        """Should run with native backend."""
        from notso_glb.utils.gltfpack import run_gltfpack

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")
        output_path = tmp_path / "output.glb"

        mock_find.return_value = "/usr/bin/gltfpack"
        mock_run_native.return_value = (True, output_path, "Success")

        success, path, msg = run_gltfpack(input_path, output_path)

        assert success is True
        assert path == output_path
        mock_run_native.assert_called_once()

    @patch("notso_glb.utils.gltfpack.find_gltfpack")
    @patch("notso_glb.utils.gltfpack._wasm_available")
    def test_delegates_to_wasm_when_prefer_wasm(
        self, mock_wasm_avail: MagicMock, mock_find: MagicMock, tmp_path: Path
    ) -> None:
        """Should delegate to WASM when prefer_wasm=True."""
        from notso_glb.utils.gltfpack import run_gltfpack

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")

        mock_find.return_value = None
        mock_wasm_avail.return_value = True

        with patch("notso_glb.wasm.run_gltfpack_wasm") as mock_wasm_run:
            mock_wasm_run.return_value = (True, input_path, "Success")
            success, path, msg = run_gltfpack(input_path, prefer_wasm=True)

        assert success is True
        mock_wasm_run.assert_called_once()

    def test_validates_input_file_exists(self, tmp_path: Path) -> None:
        """Should validate input file exists."""
        from notso_glb.utils.gltfpack import run_gltfpack

        input_path = tmp_path / "nonexistent.glb"

        with patch(
            "notso_glb.utils.gltfpack.find_gltfpack", return_value="/usr/bin/gltfpack"
        ):
            success, path, msg = run_gltfpack(input_path)

        assert success is False
        assert "not found" in msg.lower()

    @patch("notso_glb.utils.gltfpack.find_gltfpack")
    @patch("notso_glb.utils.gltfpack._run_native_gltfpack")
    def test_validates_simplify_ratio(
        self, mock_run_native: MagicMock, mock_find: MagicMock, tmp_path: Path
    ) -> None:
        """Should validate simplify_ratio parameter."""
        from notso_glb.utils.gltfpack import run_gltfpack

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")

        mock_find.return_value = "/usr/bin/gltfpack"

        success, path, msg = run_gltfpack(input_path, simplify_ratio=1.5)

        assert success is False
        assert "simplify_ratio" in msg.lower()

    @patch("notso_glb.utils.gltfpack.find_gltfpack")
    @patch("notso_glb.utils.gltfpack._run_native_gltfpack")
    def test_validates_texture_quality(
        self, mock_run_native: MagicMock, mock_find: MagicMock, tmp_path: Path
    ) -> None:
        """Should validate texture_quality parameter."""
        from notso_glb.utils.gltfpack import run_gltfpack

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")

        mock_find.return_value = "/usr/bin/gltfpack"

        success, path, msg = run_gltfpack(input_path, texture_quality=11)

        assert success is False
        assert "texture_quality" in msg.lower()

    @patch("notso_glb.utils.gltfpack.find_gltfpack")
    @patch("notso_glb.utils.gltfpack._run_native_gltfpack")
    def test_builds_command_with_all_options(
        self, mock_run_native: MagicMock, mock_find: MagicMock, tmp_path: Path
    ) -> None:
        """Should build command with all compression options."""
        from notso_glb.utils.gltfpack import run_gltfpack

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")
        output_path = tmp_path / "output.glb"

        mock_find.return_value = "/usr/bin/gltfpack"
        mock_run_native.return_value = (True, output_path, "Success")

        run_gltfpack(
            input_path,
            output_path,
            texture_compress=True,
            mesh_compress=True,
            simplify_ratio=0.5,
            texture_quality=8,
        )

        call_args = mock_run_native.call_args[0][0]
        assert "-tc" in call_args
        assert "-cc" in call_args
        assert "-si" in call_args
        assert "0.5" in call_args
        assert "-tq" in call_args
        assert "8" in call_args

    @patch("notso_glb.utils.gltfpack.find_gltfpack")
    @patch("notso_glb.utils.gltfpack._run_native_gltfpack")
    def test_skips_compression_flags_when_disabled(
        self, mock_run_native: MagicMock, mock_find: MagicMock, tmp_path: Path
    ) -> None:
        """Should skip compression flags when disabled."""
        from notso_glb.utils.gltfpack import run_gltfpack

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")
        output_path = tmp_path / "output.glb"

        mock_find.return_value = "/usr/bin/gltfpack"
        mock_run_native.return_value = (True, output_path, "Success")

        run_gltfpack(
            input_path, output_path, texture_compress=False, mesh_compress=False
        )

        call_args = mock_run_native.call_args[0][0]
        assert "-tc" not in call_args
        assert "-cc" not in call_args


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_handles_pathlib_path(self, tmp_path: Path) -> None:
        """Should handle Path objects."""
        from notso_glb.utils.gltfpack import run_gltfpack

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")

        with patch("notso_glb.utils.gltfpack.find_gltfpack", return_value=None):
            with patch("notso_glb.utils.gltfpack._wasm_available", return_value=False):
                success, path, msg = run_gltfpack(input_path)

        assert success is False
        assert isinstance(path, Path)

    @patch("notso_glb.utils.gltfpack.find_gltfpack")
    @patch("notso_glb.utils.gltfpack._run_native_gltfpack")
    def test_handles_string_path(
        self, mock_run_native: MagicMock, mock_find: MagicMock, tmp_path: Path
    ) -> None:
        """Should handle string paths."""
        from notso_glb.utils.gltfpack import run_gltfpack

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")
        output_path = tmp_path / "output.glb"

        mock_find.return_value = "/usr/bin/gltfpack"
        mock_run_native.return_value = (True, output_path, "Success")

        success, path, msg = run_gltfpack(str(input_path), str(output_path))

        assert success is True

    def test_handles_zero_simplify_ratio(self, tmp_path: Path) -> None:
        """Should handle simplify_ratio=0.0."""
        from notso_glb.utils.gltfpack import run_gltfpack

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")

        with patch(
            "notso_glb.utils.gltfpack.find_gltfpack", return_value="/usr/bin/gltfpack"
        ):
            with patch("notso_glb.utils.gltfpack._run_native_gltfpack") as mock_run:
                mock_run.return_value = (True, input_path, "Success")
                success, path, msg = run_gltfpack(input_path, simplify_ratio=0.0)

        assert success is True

    def test_handles_one_simplify_ratio(self, tmp_path: Path) -> None:
        """Should handle simplify_ratio=1.0."""
        from notso_glb.utils.gltfpack import run_gltfpack

        input_path = tmp_path / "input.glb"
        input_path.write_bytes(b"test")

        with patch(
            "notso_glb.utils.gltfpack.find_gltfpack", return_value="/usr/bin/gltfpack"
        ):
            with patch("notso_glb.utils.gltfpack._run_native_gltfpack") as mock_run:
                mock_run.return_value = (True, input_path, "Success")
                success, path, msg = run_gltfpack(input_path, simplify_ratio=1.0)

        assert success is True
