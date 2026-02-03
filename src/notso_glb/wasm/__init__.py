"""WASM-based gltfpack integration using wasmtime."""

from __future__ import annotations

from pathlib import Path

from .runtime import GltfpackWasm, _get_wasm_path

__all__ = [
    "GltfpackWasm",
    "get_gltfpack",
    "get_wasm_path",
    "is_available",
    "run_gltfpack_wasm",
]


def get_wasm_path() -> Path:
    """Get path to bundled gltfpack.wasm."""
    return _get_wasm_path()


def is_available() -> bool:
    """Check if WASM runtime (wasmtime) is importable and WASM exists."""
    try:
        import wasmtime  # noqa: F401

        return _get_wasm_path().exists()
    except ImportError:
        return False


# Singleton instance
_gltfpack: GltfpackWasm | None = None


def get_gltfpack() -> GltfpackWasm:
    """Get or create singleton GltfpackWasm instance."""
    global _gltfpack
    if _gltfpack is None:
        _gltfpack = GltfpackWasm()
    return _gltfpack


def run_gltfpack_wasm(
    input_path: Path,
    output_path: Path | None = None,
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
    if not is_available():
        return False, input_path, "WASM runtime not available"

    input_path = Path(input_path)
    if not input_path.is_file():
        return False, input_path, f"Input file not found: {input_path}"

    if output_path is None:
        stem = input_path.stem
        if stem.endswith("_packed"):
            stem = stem[:-7]
        output_path = input_path.parent / f"{stem}_packed{input_path.suffix}"

    output_path = Path(output_path)

    args: list[str] = []
    if texture_compress:
        # WASM build lacks BasisU support, skip -tc with warning
        print("[WARN] WASM gltfpack lacks BasisU support, skipping texture compression")
    if mesh_compress:
        args.append("-cc")
    if simplify_ratio is not None:
        if not (0.0 <= simplify_ratio <= 1.0):
            return (
                False,
                input_path,
                f"simplify_ratio must be [0.0, 1.0]: {simplify_ratio}",
            )
        args.extend(["-si", str(simplify_ratio)])
    if texture_quality is not None:
        # texture_quality only applies with -tc, which WASM doesn't support
        pass

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

    except OSError as e:
        return False, output_path, f"File I/O error: {e}"
    except (ValueError, TypeError) as e:
        return False, output_path, f"Argument error: {e}"
    except UnicodeDecodeError as e:
        return False, output_path, f"Log decode error: {e}"
