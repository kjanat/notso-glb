"""Command-line interface for GLB export optimizer."""

import os
import sys
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

try:
    __version__ = version("notso-glb")
except PackageNotFoundError:
    __version__ = "unknown"

from notso_glb.utils.constants import DEFAULT_CONFIG
from notso_glb.utils.gltfpack import find_gltfpack

app = typer.Typer(
    name="notso-glb",
    help="Optimize GLB/glTF/blend files for web delivery",
    add_completion=False,
    rich_markup_mode="rich",
    suggest_commands=True,
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        print(f"notso-glb {__version__}")
        raise typer.Exit()


class ExportFormat(Enum):
    """Output format for glTF export."""

    glb = "glb"
    gltf = "gltf"
    gltf_embedded = "gltf-embedded"


@app.command()
def optimize(
    input_path: Annotated[
        Path,
        typer.Argument(
            help="Input file ([bold green].blend[/], [bold green].glb[/], or [bold green].gltf[/])",
            metavar="FILE",
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output path (default: [italic]input_optimized.\\[glb|gltf][/])",
            rich_help_panel="Core Options",
        ),
    ] = DEFAULT_CONFIG["output_path"],
    export_format: Annotated[
        ExportFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format",
            rich_help_panel="Core Options",
        ),
    ] = ExportFormat.glb,
    use_draco: Annotated[
        bool,
        typer.Option(
            "--draco/--no-draco",
            help="Enable/Disable Draco compression",
            rich_help_panel="Compression & Textures",
        ),
    ] = DEFAULT_CONFIG["use_draco"],
    use_webp: Annotated[
        bool,
        typer.Option(
            "--webp/--no-webp",
            help="Enable/Disable WebP textures",
            rich_help_panel="Compression & Textures",
        ),
    ] = DEFAULT_CONFIG["use_webp"],
    max_texture_size: Annotated[
        int,
        typer.Option(
            help="Max texture size (0=no resize)",
            rich_help_panel="Compression & Textures",
            metavar="PIXELS",
        ),
    ] = DEFAULT_CONFIG["max_texture_size"],
    force_pot: Annotated[
        bool,
        typer.Option(
            "--force-pot/",
            help="Force power-of-two texture dimensions (better GPU compatibility)",
            rich_help_panel="Compression & Textures",
        ),
    ] = DEFAULT_CONFIG["force_pot_textures"],
    analyze_animations: Annotated[
        bool,
        typer.Option(
            "--analyze-animations/--skip-animation-analysis",
            help="Analyze bones for static/animated properties",
            rich_help_panel="Analysis & Optimization",
        ),
    ] = DEFAULT_CONFIG["analyze_animations"],
    check_bloat: Annotated[
        bool,
        typer.Option(
            "--check-bloat/--skip-bloat-check",
            help="Analyze meshes for unreasonable complexity",
            rich_help_panel="Analysis & Optimization",
        ),
    ] = DEFAULT_CONFIG["check_bloat"],
    autofix: Annotated[
        bool,
        typer.Option(
            "--autofix/--stable",
            help="Auto-decimate bloated props, remove unused UVs",
            rich_help_panel="[bold red][EXPERIMENTAL][/]",
        ),
    ] = DEFAULT_CONFIG["experimental_autofix"],
    use_gltfpack: Annotated[
        bool,
        typer.Option(
            "--gltfpack/--no-gltfpack",
            help="Post-process with gltfpack for extra compression",
            rich_help_panel="Compression & Textures",
        ),
    ] = find_gltfpack() is not None,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet/--verbose",
            "-q/-v",
            help="Suppress Blender's verbose output (show only warnings/errors)",
            rich_help_panel="Output",
        ),
    ] = DEFAULT_CONFIG["quiet"],
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = None,
) -> None:
    """
    Optimize and export 3D models for the web.
    """
    # Verify input existence before expensive imports
    abs_input_path = os.path.abspath(input_path)
    if not os.path.isfile(abs_input_path):
        console.print(f"[bold red][ERROR][/] File not found: {abs_input_path}")
        raise typer.Exit(code=1)

    ext = os.path.splitext(abs_input_path)[1].lower()

    # Lazy import to keep CLI snappy and avoid bpy issues in help
    from notso_glb.exporters import optimize_and_export

    # Determine if we need to import
    # GLB/glTF files: pass to optimize_and_export for import with timing
    # .blend files: already loaded if running via `blender --python`
    input_for_import: str | None = None
    if ext in (".glb", ".gltf"):
        input_for_import = abs_input_path
    elif ext != ".blend":
        console.print(f"[bold red][ERROR][/] Unsupported format: {ext}")
        console.print("        Supported: .blend, .glb, .gltf")
        raise typer.Exit(code=1)

    # Map CLI format to Blender format
    format_map = {
        "glb": "GLB",
        "gltf": "GLTF_SEPARATE",
        "gltf-embedded": "GLTF_EMBEDDED",
    }
    blender_export_format = format_map.get(export_format.value, "GLB")
    out_ext = ".gltf" if export_format.value.startswith("gltf") else ".glb"

    # Determine output path
    final_output_path: Path
    if output is None:
        base = os.path.splitext(abs_input_path)[0]
        final_output_path = Path(f"{base}_optimized{out_ext}")
    else:
        final_output_path = output.resolve()

    # Run optimization
    result = optimize_and_export(
        output_path=final_output_path,
        export_format=blender_export_format,
        use_draco=use_draco,
        use_webp=use_webp,
        max_texture_size=max_texture_size,
        force_pot_textures=force_pot,
        analyze_animations=analyze_animations,
        check_bloat=check_bloat,
        experimental_autofix=autofix,
        quiet=quiet,
        input_path=input_for_import,
    )

    if not result:
        raise typer.Exit(code=1)

    # Post-process with gltfpack if enabled
    if use_gltfpack:
        from notso_glb.utils.gltfpack import find_gltfpack, run_gltfpack
        from notso_glb.utils.logging import format_bytes

        if not find_gltfpack():
            console.print("[bold yellow][WARN][/] gltfpack not found in PATH, skipping")
        else:
            console.print("\n[bold cyan]Running gltfpack...[/]")
            original_size = Path(result).stat().st_size

            success, packed_path, msg = run_gltfpack(
                Path(result),
                output_path=Path(result),  # Overwrite original
                texture_compress=True,
                mesh_compress=True,
            )

            if success:
                new_size = packed_path.stat().st_size
                reduction = ((original_size - new_size) / original_size) * 100
                console.print(
                    f"  [green]gltfpack:[/] {format_bytes(original_size)} -> "
                    f"{format_bytes(new_size)} ([bold green]-{reduction:.0f}%[/])"
                )
            else:
                console.print(f"  [bold red][ERROR][/] {msg}")


def main() -> None:
    """Entry point - handles both CLI and Blender UI execution."""
    # Detect execution mode:
    # 1. Direct: ./script.py input.glb
    # 2. Blender: blender --python script.py -- input.glb

    args = sys.argv[1:]

    # Check for '--' separator used in Blender execution
    if "--" in sys.argv:
        idx = sys.argv.index("--")
        args = sys.argv[idx + 1 :]
    elif len(sys.argv) > 0:
        # Check if we are inside Blender (executable check)
        # If running as `blender script.py`, argv[0] is blender.
        executable = os.path.basename(sys.argv[0]).lower()
        if "blender" in executable:
            # Running in Blender without '--' -> UI mode, run with defaults?
            # Or just show help?
            # Original code ran with defaults if no args.
            # Let's try to run the command with empty args if that was the intent,
            # or just pass empty list which might trigger help if arg is required.
            pass

        # Typer expects the program name as the first "arg" in sys.argv usually,
        # but when calling app() directly with list of args, it processes that list.
        # app(args) processes the arguments.

        # However, if we run `notso-glb --help`, args is ['--help'].

        # If we are in "Blender UI mode" (no args provided to script),
        # original code ran `optimize_and_export` with defaults.
        # The 'optimize' command REQUIRES 'input_path'.
        # So if we have no args, we can't run the CLI command easily.
        # But original code handled "UI mode" by running defaults?
        # Wait, original code: `if args is None: optimize_and_export(...)`
        # That assumed `bpy.data.filepath` was set (i.e. open file in Blender).

        if not args and "blender" in os.path.basename(sys.argv[0]).lower():
            # UI Mode fallback (Running inside blender with open file, no CLI args)
            from notso_glb.exporters import optimize_and_export

            optimize_and_export(
                output_path=DEFAULT_CONFIG["output_path"],
                use_draco=DEFAULT_CONFIG["use_draco"],
                use_webp=DEFAULT_CONFIG["use_webp"],
                max_texture_size=DEFAULT_CONFIG["max_texture_size"],
                force_pot_textures=DEFAULT_CONFIG["force_pot_textures"],
                analyze_animations=DEFAULT_CONFIG["analyze_animations"],
                check_bloat=DEFAULT_CONFIG["check_bloat"],
                experimental_autofix=DEFAULT_CONFIG["experimental_autofix"],
            )
            return

        if not args:
            # If no arguments provided, print help to stderr preserving colors
            # We do this by invoking the 'optimize' command's help but redirected to stderr
            old_stdout = sys.stdout
            sys.stdout = sys.stderr
            try:
                # invoke 'optimize --help' so we see the command args, not the group help
                app(args=["optimize", "--help"], standalone_mode=False)
            except (SystemExit, typer.Exit):
                pass
            finally:
                sys.stdout = old_stdout
            sys.exit(1)

        # Single-command Typer apps automatically use the command as default
        # No need to prepend 'optimize' - Typer handles this
        app(args=args, standalone_mode=True)


if __name__ == "__main__":
    main()
