"""Tests for CLI module."""

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
