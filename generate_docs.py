#!/usr/bin/env -S uv run
"""Generate CLI documentation from Typer app and clean up the output."""

import re
import subprocess
import sys
from pathlib import Path


def generate_raw_docs() -> str:
    """Generate raw docs using typer CLI."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "typer",
            "notso_glb.cli",
            "utils",
            "docs",
            "--name",
            "notso-glb",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def clean_docs(content: str) -> str:
    """Clean up the generated markdown."""
    # Remove HTML span tags (color styling)
    content = re.sub(r"<span[^>]*>", "", content)
    content = re.sub(r"</span>", "", content)

    # Remove dollar signs from console examples
    content = re.sub(r"^\$ ", "", content, flags=re.MULTILINE)

    # Change console code blocks to bash
    content = content.replace("```console", "```bash")

    # Escape square brackets in [default: ...], [required], and other bracket patterns
    # that appear outside of backticks in option descriptions
    def escape_brackets_outside_backticks(line: str) -> str:
        """Escape [] outside of backtick-quoted sections."""
        result = []
        in_backticks = False
        i = 0
        while i < len(line):
            char = line[i]
            if char == "`":
                in_backticks = not in_backticks
                result.append(char)
            elif char in "[]" and not in_backticks:
                result.append("\\" + char)
            else:
                result.append(char)
            i += 1
        return "".join(result)

    # Process lines, but skip code blocks
    lines = content.split("\n")
    in_code_block = False
    processed_lines = []
    for line in lines:
        if line.startswith("```"):
            in_code_block = not in_code_block
            processed_lines.append(line)
        elif in_code_block:
            processed_lines.append(line)
        else:
            processed_lines.append(escape_brackets_outside_backticks(line))
    content = "\n".join(processed_lines)

    # Fix HTML entities
    content = content.replace("&#x27;", "'")
    content = content.replace("&quot;", '"')
    content = content.replace("&amp;", "&")
    content = content.replace("&lt;", "<")
    content = content.replace("&gt;", ">")

    # Clean up the title (remove backticks around program name)
    content = re.sub(r"^# `([^`]+)`", r"# \1", content)

    # Ensure consistent newlines
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content.strip() + "\n"


def main() -> None:
    """Generate and clean CLI docs."""
    output_path = Path("CLI.md")

    print("Generating CLI documentation...")

    # Generate raw docs
    raw_docs = generate_raw_docs()

    # Clean up
    clean_content = clean_docs(raw_docs)

    # Write output
    output_path.write_text(clean_content)
    print(f"Docs saved to: {output_path}")


if __name__ == "__main__":
    main()
