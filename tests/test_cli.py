"""Tests for CLI module."""

from unittest.mock import patch


class TestParseCLIArgs:
    """Tests for parse_cli_args function."""

    def test_no_args_returns_none(self) -> None:
        """No CLI args (Blender UI mode) should return None."""
        from notso_glb.cli import parse_cli_args

        with patch("sys.argv", ["blender"]):
            assert parse_cli_args() is None

    def test_basic_input_file(self) -> None:
        """Basic input file should be parsed."""
        from notso_glb.cli import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb"]):
            args = parse_cli_args()
            assert args is not None
            assert args.input == "model.glb"

    def test_blender_cli_mode(self) -> None:
        """Blender CLI mode with -- separator should work."""
        from notso_glb.cli import parse_cli_args

        with patch(
            "sys.argv",
            ["blender", "--background", "--python", "script.py", "--", "model.glb"],
        ):
            args = parse_cli_args()
            assert args is not None
            assert args.input == "model.glb"

    def test_output_option(self) -> None:
        """Output option should be parsed."""
        from notso_glb.cli import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "-o", "output.glb"]):
            args = parse_cli_args()
            assert args is not None
            assert args.output == "output.glb"

    def test_format_option(self) -> None:
        """Format option should be parsed."""
        from notso_glb.cli import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "-f", "gltf-embedded"]):
            args = parse_cli_args()
            assert args is not None
            assert args.format == "gltf-embedded"

    def test_no_draco_flag(self) -> None:
        """--no-draco flag should be parsed."""
        from notso_glb.cli import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--no-draco"]):
            args = parse_cli_args()
            assert args is not None
            assert args.no_draco is True

    def test_no_webp_flag(self) -> None:
        """--no-webp flag should be parsed."""
        from notso_glb.cli import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--no-webp"]):
            args = parse_cli_args()
            assert args is not None
            assert args.no_webp is True

    def test_max_texture_option(self) -> None:
        """--max-texture option should be parsed."""
        from notso_glb.cli import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--max-texture", "2048"]):
            args = parse_cli_args()
            assert args is not None
            assert args.max_texture == 2048

    def test_force_pot_flag(self) -> None:
        """--force-pot flag should be parsed."""
        from notso_glb.cli import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--force-pot"]):
            args = parse_cli_args()
            assert args is not None
            assert args.force_pot is True

    def test_skip_animation_analysis_flag(self) -> None:
        """--skip-animation-analysis flag should be parsed."""
        from notso_glb.cli import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--skip-animation-analysis"]):
            args = parse_cli_args()
            assert args is not None
            assert args.skip_animation_analysis is True

    def test_skip_bloat_check_flag(self) -> None:
        """--skip-bloat-check flag should be parsed."""
        from notso_glb.cli import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--skip-bloat-check"]):
            args = parse_cli_args()
            assert args is not None
            assert args.skip_bloat_check is True

    def test_experimental_autofix_flag(self) -> None:
        """--experimental-autofix flag should be parsed."""
        from notso_glb.cli import parse_cli_args

        with patch("sys.argv", ["script.py", "model.glb", "--experimental-autofix"]):
            args = parse_cli_args()
            assert args is not None
            assert args.experimental_autofix is True
