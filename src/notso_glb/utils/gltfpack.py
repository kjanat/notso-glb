"""Wrapper for gltfpack mesh/texture compression tool."""

from __future__ import annotations

import shutil
import subprocess
import traceback
from pathlib import Path


def find_gltfpack() -> str | None:
    """Find gltfpack executable in PATH."""
    return shutil.which("gltfpack")


def _wasm_available() -> bool:
    """Check if WASM fallback is available."""
    try:
        from notso_glb.wasm import is_available

        return is_available()
    except ImportError:
        return False


def run_gltfpack(
    input_path: Path,
    output_path: Path | None = None,
    *,
    texture_compress: bool = True,
    mesh_compress: bool = True,
    simplify_ratio: float | None = None,
    texture_quality: int | None = None,
    prefer_wasm: bool = False,
) -> tuple[bool, Path, str]:
    """
    Run gltfpack on a GLB/glTF file.

    Args:
        input_path: Input GLB/glTF file
        output_path: Output path (default: replaces input with _packed suffix)
        texture_compress: Enable texture compression (-tc)
        mesh_compress: Enable mesh compression (-cc)
        simplify_ratio: Simplify meshes to ratio (0.0-1.0), None = no simplify
        texture_quality: Texture quality 1-10, None = default
        prefer_wasm: Prefer WASM over native binary (default: False)

    Returns:
        Tuple of (success, output_path, message)
    """
    gltfpack = find_gltfpack()
    use_wasm = False

    if prefer_wasm and _wasm_available():
        use_wasm = True
    elif not gltfpack:
        if _wasm_available():
            use_wasm = True
        else:
            return False, input_path, "gltfpack not found and WASM fallback unavailable"

    if use_wasm:
        from notso_glb.wasm import run_gltfpack_wasm

        return run_gltfpack_wasm(
            input_path,
            output_path,
            texture_compress=texture_compress,
            mesh_compress=mesh_compress,
            simplify_ratio=simplify_ratio,
            texture_quality=texture_quality,
        )

    input_path = Path(input_path)
    if not input_path.is_file():
        return False, input_path, f"Input file not found or is not a file: {input_path}"

    # Default output: input_packed.glb
    if output_path is None:
        stem = input_path.stem
        # Remove _packed suffix if already present to avoid _packed_packed
        if stem.endswith("_packed"):
            stem = stem[:-7]
        output_path = input_path.parent / f"{stem}_packed{input_path.suffix}"

    output_path = Path(output_path)

    # Build command (gltfpack is guaranteed non-None here due to early returns)
    assert gltfpack is not None
    cmd: list[str] = [gltfpack, "-i", str(input_path), "-o", str(output_path)]

    if texture_compress:
        cmd.append("-tc")

    if mesh_compress:
        cmd.append("-cc")

    if simplify_ratio is not None:
        try:
            simplify_ratio = float(simplify_ratio)
        except (TypeError, ValueError):
            return (
                False,
                input_path,
                f"simplify_ratio must be a number, got {type(simplify_ratio).__name__}",
            )
        if not (0.0 <= simplify_ratio <= 1.0):
            return (
                False,
                input_path,
                f"simplify_ratio must be in [0.0, 1.0], got {simplify_ratio}",
            )
        cmd.extend(["-si", str(simplify_ratio)])

    if texture_quality is not None:
        try:
            texture_quality = int(texture_quality)
        except (TypeError, ValueError):
            return (
                False,
                input_path,
                f"texture_quality must be an integer, got {type(texture_quality).__name__}",
            )
        if not (1 <= texture_quality <= 10):
            return (
                False,
                input_path,
                f"texture_quality must be in [1, 10], got {texture_quality}",
            )
        cmd.extend(["-tq", str(texture_quality)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            error_msg = (
                result.stderr.strip() or result.stdout.strip() or "Unknown error"
            )
            return False, output_path, f"gltfpack failed: {error_msg}"

        if not output_path.exists():
            return False, output_path, "gltfpack completed but output file not found"

        return True, output_path, "Success"

    except subprocess.TimeoutExpired:
        return False, output_path, "gltfpack timed out after 5 minutes"
    except subprocess.SubprocessError as e:
        return False, output_path, f"gltfpack subprocess error: {e}"
    except OSError as e:
        return False, output_path, f"gltfpack OS error (cmd={cmd}): {e}"
    except Exception as e:
        return (
            False,
            output_path,
            f"gltfpack unexpected error: {e}\n{traceback.format_exc()}",
        )
