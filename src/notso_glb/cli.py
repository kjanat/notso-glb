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


class NeuralNetwork(Enum):
    glb = "glb"
    gltf = "gltf"
    gltf_embedded = "gltf-embedded"


@app.command()
def optimize(
    input_path: Annotated[
        str,
        typer.Argument(
            help="Input file ([bold green].blend[/], [bold green].glb[/], or [bold green].gltf[/])",
            metavar="INPUT",
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output path (default: [italic]input_optimized.\[glb|gltf][/])",
            rich_help_panel="Core Options",
        ),
    ] = None,
    export_format: Annotated[
        NeuralNetwork,
        typer.Option(
            "--format",
            "-f",
            help="Output format",
            rich_help_panel="Core Options",
        ),
    ] = NeuralNetwork["glb"],
    use_draco: Annotated[
        bool,
        typer.Option(
            "--draco/--no-draco",
            help="Enable/Disable Draco compression",
            rich_help_panel="Compression & Textures",
        ),
    ] = True,
    use_webp: Annotated[
        bool,
        typer.Option(
            "--webp/--no-webp",
            help="Enable/Disable WebP textures",
            rich_help_panel="Compression & Textures",
        ),
    ] = True,
    max_texture_size: Annotated[
        int,
        typer.Option(
            help="Max texture size (0=no resize)",
            rich_help_panel="Compression & Textures",
        ),
    ] = 1024,
    force_pot: Annotated[
        bool,
        typer.Option(
            "--force-pot/",
            help="Force power-of-two texture dimensions (better GPU compatibility)",
            rich_help_panel="Compression & Textures",
        ),
    ] = False,
    analyze_animations: Annotated[
        bool,
        typer.Option(
            "--analyze-animations/--skip-animation-analysis",
            help="Analyze bones for static/animated properties",
            rich_help_panel="Analysis & Optimization",
        ),
    ] = True,
    check_bloat: Annotated[
        bool,
        typer.Option(
            "--check-bloat/--skip-bloat-check",
            help="Analyze meshes for unreasonable complexity",
            rich_help_panel="Analysis & Optimization",
        ),
    ] = True,
    autofix: Annotated[
        bool,
        typer.Option(
            "--autofix/--stable",
            help="Auto-decimate bloated props, remove unused UVs",
            rich_help_panel="[bold red][EXPERIMENTAL][/]",
        ),
    ] = False,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
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
    from notso_glb.exporters import import_gltf, optimize_and_export

    # Import if GLB/glTF (blend files are already loaded if we are inside Blender,
    # but if running standalone with bpy module, we might need to open it?)
    # For now, we assume if it's .glb/.gltf we import it.
    if ext in (".glb", ".gltf"):
        import_gltf(abs_input_path)
    elif ext != ".blend":
        console.print(f"[bold red][ERROR][/] Unsupported format: {ext}")
        console.print("        Supported: .blend, .glb, .gltf")
        raise typer.Exit(code=1)

    # If it is a .blend file and we are running this script via `blender --python`,
    # the file is already open.
    # If we are running via `uv run` with `bpy` installed, we might need to open it?
    # The original code didn't explicitly open .blend files, implying reliance on
    # `blender file.blend --python ...` OR `bpy.ops.wm.open_mainfile` if strictly standalone.
    # However, `import_gltf` does `bpy.ops.object.delete()`.

    # Map CLI format to Blender format
    format_map = {
        "glb": "GLB",
        "gltf": "GLTF_SEPARATE",
        "gltf-embedded": "GLTF_EMBEDDED",
    }
    blender_export_format = format_map.get(export_format.value, "GLB")
    out_ext = ".gltf" if export_format.value.startswith("gltf") else ".glb"

    # Determine output path
    final_output_path: str
    if output is None:
        base = os.path.splitext(abs_input_path)[0]
        final_output_path = f"{base}_optimized{out_ext}"
    else:
        final_output_path = os.path.abspath(str(output))

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
    )

    if not result:
        raise typer.Exit(code=1)


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

        # Make 'optimize' the default command by prepending it
        # This allows 'notso-glb input.glb' to map to 'notso-glb optimize input.glb'
        args = ["optimize"] + args
        app(args=args, standalone_mode=True)


if __name__ == "__main__":
    main()
