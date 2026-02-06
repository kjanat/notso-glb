# AGENTS.md

## Build/Test/Lint Commands

```bash
uv run pytest                     # Run all tests
uv run pytest tests/test_foo.py   # Single test file
uv run pytest -k "test_name"      # Single test by name
uv run ruff check .               # Lint
uv run ruff format .              # Format (or: dprint fmt)
uv run ty check                   # Type check
```

## Code Style

- **Python**: 3.11 only, use type hints everywhere
- **Imports**: stdlib first, then third-party (`bpy`), then local; one import
  per line
- **Formatting**: ruff/dprint, 4-space indent, double quotes
- **Naming**: snake_case functions/vars, UPPER_CASE constants, descriptive names
- **Types**: Full annotations, use `# ty:ignore` and `# pyright: ignore` for bpy
  imports
- **Errors**: Use try/except with specific exceptions, print warnings with
  `[WARN]`/`[ERROR]`
- **Docstrings**: Triple-quoted, describe purpose and args for public functions
- **Comments**: Explain "why" not "what", use `# Step N:` for multi-phase logic
