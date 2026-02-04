"""WASM gltfpack runner - executes gltfpack via WASM."""

from __future__ import annotations

from pathlib import Path

from .runtime import GltfpackWasm

# Singleton instance
_gltfpack: GltfpackWasm | None = None


def get_gltfpack() -> GltfpackWasm:
    """Get or create singleton GltfpackWasm instance."""
    global _gltfpack
    if _gltfpack is None:
        _gltfpack = GltfpackWasm()
    return _gltfpack


def reset_gltfpack() -> None:
    """Reset singleton instance (for testing/cleanup)."""
    global _gltfpack
    _gltfpack = None


def _resolve_output_path(input_path: Path, output_path: str | Path | None) -> Path:
    """Resolve output path, defaulting to input_packed.glb."""
    if output_path is not None:
        return Path(output_path)
    stem = input_path.stem
    if stem.endswith("_packed"):
        stem = stem[:-7]
    return input_path.parent / f"{stem}_packed{input_path.suffix}"


def _build_args(
    mesh_compress: bool,
    simplify_ratio: float | None,
) -> tuple[list[str], str | None]:
    """Build gltfpack args, return (args, error_message)."""
    args: list[str] = []
    if mesh_compress:
        args.append("-cc")
    if simplify_ratio is not None:
        if not (0.0 <= simplify_ratio <= 1.0):
            return [], f"simplify_ratio must be [0.0, 1.0]: {simplify_ratio}"
        args.extend(["-si", str(simplify_ratio)])
    return args, None


def _execute(
    input_path: Path,
    output_path: Path,
    args: list[str],
) -> tuple[bool, Path, str]:
    """Execute gltfpack WASM and handle errors."""
    try:
        gltfpack = get_gltfpack()
        input_data = input_path.read_bytes()
        success, output_data, log = gltfpack.pack(
            input_data,
            input_name=input_path.name,
            output_name=output_path.name,
            args=args,
        )

        if not success:
            return False, output_path, f"gltfpack failed: {log}"

        output_path.write_bytes(output_data)
        return True, output_path, "Success"

    except UnicodeDecodeError as e:
        return False, output_path, f"Log decode error: {e}"
    except OSError as e:
        return False, output_path, f"File I/O error: {e}"
    except (ValueError, TypeError) as e:
        return False, output_path, f"Argument error: {e}"


def run_gltfpack_wasm(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    texture_compress: bool = True,
    mesh_compress: bool = True,
    simplify_ratio: float | None = None,
    texture_quality: int | None = None,
) -> tuple[bool, Path, str]:
    """
    Run gltfpack via WASM on a GLB/glTF file.

    Args:
        input_path: Input GLB/glTF file
        output_path: Output path (default: replaces input with _packed suffix)
        texture_compress: Enable texture compression (-tc)
        mesh_compress: Enable mesh compression (-cc)
        simplify_ratio: Simplify meshes to ratio (0.0-1.0), None = no simplify
        texture_quality: Texture quality 1-10, None = default

    Returns:
        Tuple of (success, output_path, message)
    """
    from . import get_wasm_path, is_available

    input_path = Path(input_path)

    if not is_available():
        wasm_path = get_wasm_path()
        if not wasm_path.exists():
            return (
                False,
                input_path,
                f"WASM file not found at {wasm_path}. "
                "Run: uv run scripts/update_wasm.py",
            )
        return False, input_path, "WASM runtime not available (wasmtime not installed)"

    if not input_path.is_file():
        return False, input_path, f"Input file not found: {input_path}"

    resolved_output = _resolve_output_path(input_path, output_path)

    if texture_compress:
        from notso_glb.utils.logging import log_warn

        log_warn("WASM gltfpack lacks BasisU support, skipping texture compression")

    # texture_quality only applies with -tc, which WASM doesn't support
    del texture_quality

    args, error = _build_args(mesh_compress, simplify_ratio)
    if error:
        return False, input_path, error

    return _execute(input_path, resolved_output, args)
