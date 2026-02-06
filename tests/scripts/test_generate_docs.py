"""Tests for generate_docs script."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestCleanDocs:
    """Tests for clean_docs function."""

    def test_removes_html_span_tags(self) -> None:
        """Should remove HTML span tags."""
        from scripts.generate_docs import clean_docs

        content = '<span style="color: red">text</span> more text'
        result = clean_docs(content)
        assert "<span" not in result
        assert "</span>" not in result
        assert "text more text" in result

    def test_removes_dollar_signs_from_console(self) -> None:
        """Should remove dollar signs from console prompts."""
        from scripts.generate_docs import clean_docs

        content = "$ notso-glb --help\n$ notso-glb file.glb"
        result = clean_docs(content)
        assert result.count("$") == 0
        assert "notso-glb --help" in result
        assert "notso-glb file.glb" in result

    def test_changes_console_to_bash(self) -> None:
        """Should change console code blocks to bash."""
        from scripts.generate_docs import clean_docs

        content = "```console\ncommand\n```"
        result = clean_docs(content)
        assert "```bash" in result
        assert "```console" not in result

    def test_escapes_brackets_outside_backticks(self) -> None:
        """Should escape square brackets outside of backticks."""
        from scripts.generate_docs import clean_docs

        content = "Option [default: value]"
        result = clean_docs(content)
        assert r"\[default: value\]" in result

    def test_preserves_brackets_inside_backticks(self) -> None:
        """Should preserve square brackets inside backticks."""
        from scripts.generate_docs import clean_docs

        content = "Use `[option]` flag"
        result = clean_docs(content)
        assert "`[option]`" in result
        assert r"`\[option\]`" not in result

    def test_replaces_html_entities(self) -> None:
        """Should replace HTML entities with actual characters."""
        from scripts.generate_docs import clean_docs

        content = "&#x27;quote&#x27; &quot;double&quot; &amp; &lt; &gt;"
        result = clean_docs(content)
        assert "'quote'" in result
        assert '"double"' in result
        assert " & " in result
        assert " < " in result
        assert ">" in result  # May not have spaces around it
        assert "&#x27;" not in result
        assert "&quot;" not in result
        assert "&amp;" not in result
        assert "&lt;" not in result
        assert "&gt;" not in result

    def test_cleans_title_backticks(self) -> None:
        """Should remove backticks around program name in title."""
        from scripts.generate_docs import clean_docs

        content = "# `notso-glb`\n\nDescription"
        result = clean_docs(content)
        assert "# notso-glb\n" in result
        assert "# `notso-glb`" not in result

    def test_normalizes_multiple_newlines(self) -> None:
        """Should normalize multiple newlines to double newlines."""
        from scripts.generate_docs import clean_docs

        content = "Line 1\n\n\n\nLine 2"
        result = clean_docs(content)
        assert "\n\n\n" not in result
        # Should have at most double newlines
        assert "Line 1\n\nLine 2" in result

    def test_skips_bracket_escaping_in_code_blocks(self) -> None:
        """Should not escape brackets inside code blocks."""
        from scripts.generate_docs import clean_docs

        content = "```bash\nnotso-glb [options]\n```"
        result = clean_docs(content)
        assert "```bash\nnotso-glb [options]\n```" in result
        assert r"\[options\]" not in result


class TestEscapeBracketsOutsideBackticks:
    """Tests for escape_brackets_outside_backticks helper."""

    def test_escapes_opening_bracket(self) -> None:
        """Should escape opening brackets."""
        from scripts.generate_docs import clean_docs

        # Test via clean_docs since it's a nested function
        content = "text [bracket"
        result = clean_docs(content)
        assert r"\[bracket" in result

    def test_escapes_closing_bracket(self) -> None:
        """Should escape closing brackets."""
        from scripts.generate_docs import clean_docs

        content = "text bracket]"
        result = clean_docs(content)
        assert r"bracket\]" in result

    def test_multiple_brackets(self) -> None:
        """Should escape multiple bracket pairs."""
        from scripts.generate_docs import clean_docs

        content = "[option1] and [option2]"
        result = clean_docs(content)
        assert r"\[option1\]" in result
        assert r"\[option2\]" in result

    def test_nested_backticks_and_brackets(self) -> None:
        """Should handle nested backticks and brackets correctly."""
        from scripts.generate_docs import clean_docs

        content = "Use `[opt]` for [default: value]"
        result = clean_docs(content)
        assert "`[opt]`" in result
        assert r"\[default: value\]" in result


class TestGenerateRawDocs:
    """Tests for generate_raw_docs function."""

    @patch("scripts.generate_docs.subprocess.run")
    def test_calls_typer_cli(self, mock_run: MagicMock) -> None:
        """Should call typer CLI with correct arguments."""
        from scripts.generate_docs import generate_raw_docs

        mock_run.return_value = MagicMock(stdout="# notso-glb\n\nDocs content")

        result = generate_raw_docs()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args is not None
        args = call_args[0][0]
        assert "typer" in args
        assert "notso_glb.cli" in args
        assert "utils" in args
        assert "docs" in args
        assert "--name" in args
        assert "notso-glb" in args
        assert result == "# notso-glb\n\nDocs content"

    @patch("scripts.generate_docs.subprocess.run")
    def test_raises_on_subprocess_error(self, mock_run: MagicMock) -> None:
        """Should raise CalledProcessError on subprocess failure."""
        from subprocess import CalledProcessError

        from scripts.generate_docs import generate_raw_docs

        mock_run.side_effect = CalledProcessError(1, "typer")

        with pytest.raises(CalledProcessError):
            generate_raw_docs()


class TestMain:
    """Tests for main function."""

    @patch("scripts.generate_docs.subprocess.run")
    @patch("scripts.generate_docs.Path")
    def test_main_workflow(self, mock_path: MagicMock, mock_run: MagicMock) -> None:
        """Should execute full workflow: generate, clean, write, format."""
        from scripts.generate_docs import main

        # Mock subprocess for typer docs
        mock_run.return_value = MagicMock(stdout="# `notso-glb`\n\n$ notso-glb --help")

        # Mock Path operations
        mock_output_path = MagicMock()
        mock_path.return_value.parent.parent = MagicMock()
        mock_path.return_value.parent.parent.__truediv__.return_value = mock_output_path

        main()

        # Verify write was called
        mock_output_path.write_text.assert_called_once()
        written_content = mock_output_path.write_text.call_args[0][0]

        # Verify cleaning happened
        assert "# `notso-glb`" not in written_content
        assert "# notso-glb" in written_content

        # Verify dprint was called (second subprocess call)
        assert mock_run.call_count == 2
        dprint_call = mock_run.call_args_list[1]
        assert "dprint" in str(dprint_call[0][0])


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_content(self) -> None:
        """Should handle empty content."""
        from scripts.generate_docs import clean_docs

        result = clean_docs("")
        # clean_docs adds a trailing newline
        assert result.strip() == ""

    def test_only_backticks(self) -> None:
        """Should handle content with only backticks."""
        from scripts.generate_docs import clean_docs

        content = "```\n```"
        result = clean_docs(content)
        assert "```" in result

    def test_unmatched_backticks(self) -> None:
        """Should handle unmatched backticks gracefully."""
        from scripts.generate_docs import clean_docs

        content = "text `with [bracket] inside"
        result = clean_docs(content)
        # Backtick never closed, so bracket should remain unescaped
        assert "[bracket]" in result

    def test_consecutive_brackets(self) -> None:
        """Should escape consecutive brackets."""
        from scripts.generate_docs import clean_docs

        content = "[[nested]]"
        result = clean_docs(content)
        assert r"\[\[nested\]\]" in result

    def test_preserves_code_block_content(self) -> None:
        """Should preserve all content inside code blocks unchanged."""
        from scripts.generate_docs import clean_docs

        content = "```python\ndef foo():\n    return [1, 2, 3]\n```"
        result = clean_docs(content)
        assert "def foo():" in result
        assert "return [1, 2, 3]" in result
        assert r"\[1" not in result
