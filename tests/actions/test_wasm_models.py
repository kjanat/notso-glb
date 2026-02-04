"""Tests for test-wasm-models GitHub action script."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestGetBundledVersion:
    """Tests for get_bundled_version function."""

    def test_returns_version_from_file(self, tmp_path: Path) -> None:
        """Should return version from file."""
        # Import the test module
        sys.path.insert(
            0,
            str(
                Path(__file__).parent.parent.parent
                / ".github"
                / "actions"
                / "test-wasm-models"
            ),
        )

        try:
            from test import get_bundled_version  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        version_file = tmp_path / "gltfpack.version"
        version_file.write_text("1.2.3\n")

        with patch("test.VERSION_PATH", version_file):
            result = get_bundled_version()

        assert result == "1.2.3"

    def test_returns_unknown_when_missing(self, tmp_path: Path) -> None:
        """Should return 'unknown' when file doesn't exist."""
        try:
            from test import get_bundled_version  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        version_file = tmp_path / "nonexistent.version"

        with patch("test.VERSION_PATH", version_file):
            result = get_bundled_version()

        assert result == "unknown"


class TestClassifyFailure:
    """Tests for classify_failure function."""

    def test_identifies_external_resources(self) -> None:
        """Should identify external resource failures."""
        try:
            from test import classify_failure  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        is_expected, category = classify_failure("Error: resource not found")

        assert is_expected is True
        assert category == "external-resources"

    def test_identifies_draco_input(self) -> None:
        """Should identify Draco input failures."""
        try:
            from test import classify_failure  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        is_expected, category = classify_failure("Draco compression error")

        assert is_expected is True
        assert category == "draco-input"

    def test_identifies_missing_extension(self) -> None:
        """Should identify missing extension failures."""
        try:
            from test import classify_failure  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        is_expected, category = classify_failure("file requires KHR_extension")

        assert is_expected is True
        assert category == "missing-extension"

    def test_identifies_missing_feature(self) -> None:
        """Should identify missing feature failures."""
        try:
            from test import classify_failure  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        is_expected, category = classify_failure("Model requires feature X")

        assert is_expected is True
        assert category == "missing-feature"

    def test_identifies_unexpected_failure(self) -> None:
        """Should identify unexpected failures."""
        try:
            from test import classify_failure  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        is_expected, category = classify_failure("Unknown error occurred")

        assert is_expected is False
        assert category == ""


class TestMain:
    """Tests for main function."""

    @patch("test.is_available")
    def test_exits_when_wasm_unavailable(self, mock_is_avail: MagicMock) -> None:
        """Should exit with error when WASM unavailable."""
        try:
            from test import main  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        mock_is_avail.return_value = False

        result = main()

        assert result == 1

    @patch("test.is_available")
    @patch("test.get_wasm_path")
    @patch("test.get_bundled_version")
    def test_displays_wasm_info(
        self,
        mock_version: MagicMock,
        mock_wasm_path: MagicMock,
        mock_is_avail: MagicMock,
        tmp_path: Path,
        capsys,
    ) -> None:
        """Should display WASM version and path info."""
        try:
            from test import main  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        mock_is_avail.return_value = True
        mock_version.return_value = "1.0.0"
        wasm_file = tmp_path / "gltfpack.wasm"
        wasm_file.write_bytes(b"\x00asm" + b"\x00" * 1024)
        mock_wasm_path.return_value = wasm_file

        # Create empty model dir
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        with patch("test.MODEL_DIR", model_dir):
            main()

        captured = capsys.readouterr()
        assert "1.0.0" in captured.out
        assert "gltfpack.wasm" in captured.out

    @patch("test.is_available")
    @patch("test.get_wasm_path")
    @patch("test.get_bundled_version")
    @patch("test.run_gltfpack_wasm")
    def test_processes_glb_files(
        self,
        mock_run_wasm: MagicMock,
        mock_version: MagicMock,
        mock_wasm_path: MagicMock,
        mock_is_avail: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should process .glb files."""
        try:
            from test import main  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        mock_is_avail.return_value = True
        mock_version.return_value = "1.0.0"
        wasm_file = tmp_path / "gltfpack.wasm"
        wasm_file.write_bytes(b"\x00asm")
        mock_wasm_path.return_value = wasm_file

        # Create test model
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        model_file = model_dir / "test.glb"
        model_file.write_bytes(b"fake glb data")

        mock_run_wasm.return_value = (True, tmp_path / "out.glb", "Success")

        with patch("test.MODEL_DIR", model_dir):
            with patch("test.MAX_MODELS", 10):
                result = main()

        assert result == 0
        mock_run_wasm.assert_called()

    @patch("test.is_available")
    @patch("test.get_wasm_path")
    @patch("test.get_bundled_version")
    @patch("test.run_gltfpack_wasm")
    def test_processes_gltf_files(
        self,
        mock_run_wasm: MagicMock,
        mock_version: MagicMock,
        mock_wasm_path: MagicMock,
        mock_is_avail: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should process .gltf files."""
        try:
            from test import main  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        mock_is_avail.return_value = True
        mock_version.return_value = "1.0.0"
        wasm_file = tmp_path / "gltfpack.wasm"
        wasm_file.write_bytes(b"\x00asm")
        mock_wasm_path.return_value = wasm_file

        # Create test model
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        model_file = model_dir / "test.gltf"
        model_file.write_bytes(b"fake gltf data")

        mock_run_wasm.return_value = (True, tmp_path / "out.gltf", "Success")

        with patch("test.MODEL_DIR", model_dir):
            with patch("test.MAX_MODELS", 10):
                result = main()

        assert result == 0

    @patch("test.is_available")
    @patch("test.get_wasm_path")
    @patch("test.get_bundled_version")
    @patch("test.run_gltfpack_wasm")
    def test_respects_max_models_limit(
        self,
        mock_run_wasm: MagicMock,
        mock_version: MagicMock,
        mock_wasm_path: MagicMock,
        mock_is_avail: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should respect MAX_MODELS limit."""
        try:
            from test import main  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        mock_is_avail.return_value = True
        mock_version.return_value = "1.0.0"
        wasm_file = tmp_path / "gltfpack.wasm"
        wasm_file.write_bytes(b"\x00asm")
        mock_wasm_path.return_value = wasm_file

        # Create 5 test models
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        for i in range(5):
            model_file = model_dir / f"test{i}.glb"
            model_file.write_bytes(b"fake glb")

        mock_run_wasm.return_value = (True, tmp_path / "out.glb", "Success")

        with patch("test.MODEL_DIR", model_dir):
            with patch("test.MAX_MODELS", 2):  # Only process 2
                main()

        assert mock_run_wasm.call_count == 2

    @patch("test.is_available")
    @patch("test.get_wasm_path")
    @patch("test.get_bundled_version")
    @patch("test.run_gltfpack_wasm")
    def test_skips_large_files(
        self,
        mock_run_wasm: MagicMock,
        mock_version: MagicMock,
        mock_wasm_path: MagicMock,
        mock_is_avail: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should skip files larger than MAX_FILE_SIZE."""
        try:
            from test import MAX_FILE_SIZE, main  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        mock_is_avail.return_value = True
        mock_version.return_value = "1.0.0"
        wasm_file = tmp_path / "gltfpack.wasm"
        wasm_file.write_bytes(b"\x00asm")
        mock_wasm_path.return_value = wasm_file

        # Create large model
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        large_file = model_dir / "large.glb"
        large_file.write_bytes(b"x" * (MAX_FILE_SIZE + 1))

        with patch("test.MODEL_DIR", model_dir):
            main()

        # Should not call run_gltfpack_wasm for large file
        mock_run_wasm.assert_not_called()

    @patch("test.is_available")
    @patch("test.get_wasm_path")
    @patch("test.get_bundled_version")
    @patch("test.run_gltfpack_wasm")
    def test_returns_error_on_unexpected_failures(
        self,
        mock_run_wasm: MagicMock,
        mock_version: MagicMock,
        mock_wasm_path: MagicMock,
        mock_is_avail: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should return error when unexpected failures occur."""
        try:
            from test import main  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        mock_is_avail.return_value = True
        mock_version.return_value = "1.0.0"
        wasm_file = tmp_path / "gltfpack.wasm"
        wasm_file.write_bytes(b"\x00asm")
        mock_wasm_path.return_value = wasm_file

        # Create test model
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        model_file = model_dir / "test.glb"
        model_file.write_bytes(b"data")

        # Simulate unexpected failure
        mock_run_wasm.return_value = (False, model_file, "Unexpected error")

        with patch("test.MODEL_DIR", model_dir):
            result = main()

        assert result == 1

    @patch("test.is_available")
    @patch("test.get_wasm_path")
    @patch("test.get_bundled_version")
    @patch("test.run_gltfpack_wasm")
    def test_writes_github_output(
        self,
        mock_run_wasm: MagicMock,
        mock_version: MagicMock,
        mock_wasm_path: MagicMock,
        mock_is_avail: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should write results to GITHUB_OUTPUT."""
        try:
            from test import main  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        mock_is_avail.return_value = True
        mock_version.return_value = "1.0.0"
        wasm_file = tmp_path / "gltfpack.wasm"
        wasm_file.write_bytes(b"\x00asm")
        mock_wasm_path.return_value = wasm_file

        # Create test model
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        model_file = model_dir / "test.glb"
        model_file.write_bytes(b"data")

        mock_run_wasm.return_value = (True, tmp_path / "out.glb", "Success")

        github_output = tmp_path / "github_output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

        with patch("test.MODEL_DIR", model_dir):
            main()

        # Check output file was written
        assert github_output.exists()
        content = github_output.read_text()
        assert "passed=" in content
        assert "expected-failed=" in content
        assert "unexpected-failed=" in content

    @patch("test.is_available")
    @patch("test.get_wasm_path")
    @patch("test.get_bundled_version")
    @patch("test.run_gltfpack_wasm")
    def test_handles_exceptions_gracefully(
        self,
        mock_run_wasm: MagicMock,
        mock_version: MagicMock,
        mock_wasm_path: MagicMock,
        mock_is_avail: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should handle exceptions during processing."""
        try:
            from test import main  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("Test script not importable")
            return

        mock_is_avail.return_value = True
        mock_version.return_value = "1.0.0"
        wasm_file = tmp_path / "gltfpack.wasm"
        wasm_file.write_bytes(b"\x00asm")
        mock_wasm_path.return_value = wasm_file

        # Create test model
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        model_file = model_dir / "test.glb"
        model_file.write_bytes(b"data")

        # Simulate exception
        mock_run_wasm.side_effect = Exception("Unexpected error")

        with patch("test.MODEL_DIR", model_dir):
            result = main()

        # Should catch exception and record as unexpected failure
        assert result == 1


class TestCategoryDescriptions:
    """Tests for CATEGORY_DESCRIPTIONS mapping."""

    def test_all_categories_have_descriptions(self) -> None:
        """All expected failure categories should have descriptions."""
        try:
            from test import (  # type: ignore[import-not-found]
                CATEGORY_DESCRIPTIONS,
                EXPECTED_FAILURES,
            )
        except ImportError:
            pytest.skip("Test script not importable")
            return

        categories = {cat for _, cat in EXPECTED_FAILURES}

        for category in categories:
            assert category in CATEGORY_DESCRIPTIONS
            assert len(CATEGORY_DESCRIPTIONS[category]) > 0
