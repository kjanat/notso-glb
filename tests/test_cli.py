"""Tests for CLI module."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from notso_glb.cli import app

runner = CliRunner()


class TestCLIHelp:
    """Tests for CLI help and version."""

    def test_help_shows_options(self) -> None:
        """Help should show available options."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Optimize" in result.output or "GLB" in result.output

    def test_version_flag(self) -> None:
        """Version flag should show version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "notso-glb" in result.output


class TestCLIValidation:
    """Tests for CLI input validation."""

    def test_missing_input_shows_help(self) -> None:
        """Missing input file should show help (no_args_is_help=True)."""
        result = runner.invoke(app, [])
        # Typer shows help when no args provided (via no_args_is_help=True)
        # Exit code 0 because help was shown successfully
        assert "Usage" in result.output or "INPUT" in result.output

    def test_nonexistent_file_shows_error(self) -> None:
        """Non-existent input file should show error."""
        result = runner.invoke(app, ["nonexistent.glb"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "error" in result.output.lower()


class TestCLIOptions:
    """Tests for CLI options parsing."""

    def test_format_option_values(self) -> None:
        """Format option should accept valid values."""
        # We can't fully test without a real file, but we can test that
        # the option is recognized
        result = runner.invoke(app, ["--help"])
        assert "--format" in result.output or "-f" in result.output

    def test_compression_options_in_help(self) -> None:
        """Compression options should be documented."""
        result = runner.invoke(app, ["--help"])
        assert "--draco" in result.output or "Draco" in result.output
        assert "--webp" in result.output or "WebP" in result.output

    def test_analysis_options_in_help(self) -> None:
        """Analysis options should be documented."""
        result = runner.invoke(app, ["--help"])
        assert "animation" in result.output.lower()
        assert "bloat" in result.output.lower()

    def test_autofix_option_in_help(self) -> None:
        """Autofix option should be documented."""
        result = runner.invoke(app, ["--help"])
        assert "--autofix" in result.output or "autofix" in result.output.lower()

    def test_quiet_option_in_help(self) -> None:
        """Quiet option should be documented."""
        result = runner.invoke(app, ["--help"])
        assert "--quiet" in result.output or "-q" in result.output

    def test_gltfpack_option_in_help(self) -> None:
        """Gltfpack option should be documented."""
        result = runner.invoke(app, ["--help"])
        assert "--gltfpack" in result.output or "gltfpack" in result.output.lower()


class TestDracoGltfpackInteraction:
    """Tests for Draco/gltfpack interaction to prevent hangs."""

    @patch("notso_glb.exporters.optimize_and_export")
    def test_draco_disabled_when_gltfpack_enabled(
        self, mock_export: MagicMock, tmp_path: object
    ) -> None:
        """Draco should be disabled at export when gltfpack is enabled."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            # Write minimal GLB header so the file exists
            f.write(b"\x00" * 20)
            f.flush()

            mock_export.return_value = None  # simulate export failure to skip gltfpack

            runner.invoke(app, [f.name, "--draco", "--gltfpack"])

        # The export should have been called with use_draco=False
        mock_export.assert_called_once()
        assert mock_export.call_args.kwargs["use_draco"] is False

    @patch("notso_glb.exporters.optimize_and_export")
    def test_draco_kept_when_gltfpack_disabled(
        self, mock_export: MagicMock, tmp_path: object
    ) -> None:
        """Draco should remain enabled when gltfpack is disabled."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            f.write(b"\x00" * 20)
            f.flush()

            mock_export.return_value = None

            runner.invoke(app, [f.name, "--draco", "--no-gltfpack"])

        mock_export.assert_called_once()
        assert mock_export.call_args.kwargs["use_draco"] is True

    @patch("notso_glb.exporters.optimize_and_export")
    def test_draco_disabled_message_shown(
        self, mock_export: MagicMock, tmp_path: object
    ) -> None:
        """User should be informed when Draco is auto-disabled for gltfpack."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            f.write(b"\x00" * 20)
            f.flush()

            mock_export.return_value = None

            result = runner.invoke(app, [f.name, "--draco", "--gltfpack"])

        assert "draco disabled" in result.output.lower()

    @patch("notso_glb.exporters.optimize_and_export")
    def test_no_draco_message_when_draco_already_off(
        self, mock_export: MagicMock, tmp_path: object
    ) -> None:
        """No Draco-disabled message when user already passed --no-draco."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            f.write(b"\x00" * 20)
            f.flush()

            mock_export.return_value = None

            result = runner.invoke(app, [f.name, "--no-draco", "--gltfpack"])

        # Should NOT show the "Draco disabled" message since user already disabled it
        assert "draco disabled" not in result.output.lower()
