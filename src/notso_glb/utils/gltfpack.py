"""Wrapper for gltfpack mesh/texture compression tool."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TypeAlias

# Environment variables to force a specific backend (for testing)
ENV_FORCE_NATIVE: str = "NOTSO_GLB_FORCE_GLTFPACK_NATIVE"
ENV_FORCE_WASM: str = "NOTSO_GLB_FORCE_GLTFPACK_WASM"

# Result type alias for clarity
GltfpackResult: TypeAlias = tuple[bool, Path, str]


def find_gltfpack() -> str | None:
    """Find gltfpack executable in PATH."""
    return shutil.which("gltfpack")


def _wasm_available() -> bool:
    """Check if WASM fallback is available."""
    try:
        from notso_glb.wasm import is_available

        return is_available()
    except (ImportError, OSError):
        return False


def _select_backend(
    input_path: Path,
    prefer_wasm: bool,
    gltfpack: str | None,
) -> tuple[bool | None, GltfpackResult | None]:
    """
    Select backend based on env vars and availability.

    Returns:
        (use_wasm, error_result) - use_wasm is None if error_result is set.
    """
    force_native = os.environ.get(ENV_FORCE_NATIVE, "").lower() in ("1", "true", "yes")
    force_wasm = os.environ.get(ENV_FORCE_WASM, "").lower() in ("1", "true", "yes")

    if force_native and force_wasm:
        return None, (False, input_path, "Cannot force both native and WASM backends")

    if force_native:
        if not gltfpack:
            return None, (
                False,
                input_path,
                f"{ENV_FORCE_NATIVE} set but native gltfpack not found",
            )
        return False, None

    if force_wasm:
        if not _wasm_available():
            return None, (
                False,
                input_path,
                f"{ENV_FORCE_WASM} set but WASM runtime unavailable",
            )
        return True, None

    if prefer_wasm:
        if _wasm_available():
            return True, None
        if gltfpack:
            from notso_glb.utils.logging import log_warn

            log_warn("prefer_wasm=True but WASM unavailable, falling back to native")
            return False, None
        return None, (
            False,
            input_path,
            "prefer_wasm=True but WASM unavailable and no native fallback",
        )

    if not gltfpack:
        if _wasm_available():
            return True, None
        return None, (
            False,
            input_path,
            "gltfpack not found and WASM fallback unavailable",
        )

    return False, None


def _resolve_output_path(input_path: Path, output_path: str | Path | None) -> Path:
    """Resolve output path, defaulting to input_packed.glb."""
    if output_path is not None:
        return Path(output_path)
    stem = input_path.stem
    if stem.endswith("_packed"):
        stem = stem[:-7]
    return input_path.parent / f"{stem}_packed{input_path.suffix}"


def _validate_simplify_ratio(
    ratio: float | None,
    input_path: Path,
) -> tuple[float | None, GltfpackResult | None]:
    """Validate simplify_ratio, return (validated_value, error_or_none)."""
    if ratio is None:
        return None, None
    try:
        ratio = float(ratio)
    except (TypeError, ValueError):
        return None, (
            False,
            input_path,
            f"simplify_ratio must be a number, got {type(ratio).__name__}",
        )
    if not (0.0 <= ratio <= 1.0):
        return None, (
            False,
            input_path,
            f"simplify_ratio must be in [0.0, 1.0], got {ratio}",
        )
    return ratio, None


def _validate_texture_quality(
    quality: int | float | None,
    input_path: Path,
) -> tuple[int | None, GltfpackResult | None]:
    """Validate texture_quality, return (validated_value, error_or_none)."""
    if quality is None:
        return None, None
    # Reject bool explicitly (bool is subclass of int)
    if isinstance(quality, bool):
        return None, (
            False,
            input_path,
            "texture_quality must be an integer, bool provided",
        )
    # Reject non-integer floats
    if isinstance(quality, float):
        if not quality.is_integer():
            return None, (
                False,
                input_path,
                "texture_quality must be an integer, non-integer float provided",
            )
        quality = int(quality)
    else:
        try:
            quality = int(quality)
        except (TypeError, ValueError):
            return None, (
                False,
                input_path,
                f"texture_quality must be an integer, got {type(quality).__name__}",
            )
    if not (1 <= quality <= 10):
        return None, (
            False,
            input_path,
            f"texture_quality must be in [1, 10], got {quality}",
        )
    return quality, None


def _run_native_gltfpack(
    cmd: list[str],
    output_path: Path,
) -> GltfpackResult:
    """Execute native gltfpack subprocess."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
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


def run_gltfpack(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    texture_compress: bool = True,
    mesh_compress: bool = True,
    simplify_ratio: float | None = None,
    texture_quality: int | None = None,
    prefer_wasm: bool = False,
) -> GltfpackResult:
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
    input_path = Path(input_path)
    gltfpack = find_gltfpack()

    # Step 1: Select backend
    use_wasm, error = _select_backend(input_path, prefer_wasm, gltfpack)
    if error:
        return error

    # Step 2: Delegate to WASM if selected
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

    # Step 3: Validate input file
    if not input_path.is_file():
        return False, input_path, f"Input file not found or is not a file: {input_path}"

    # Step 4: Resolve output path
    output_path = _resolve_output_path(input_path, output_path)

    # Step 5: Validate optional arguments
    simplify_ratio, error = _validate_simplify_ratio(simplify_ratio, input_path)
    if error:
        return error

    texture_quality, error = _validate_texture_quality(texture_quality, input_path)
    if error:
        return error

    # Step 6: Build command
    assert gltfpack is not None
    cmd: list[str] = [gltfpack, "-i", str(input_path), "-o", str(output_path)]
    if texture_compress:
        cmd.append("-tc")
    if mesh_compress:
        cmd.append("-cc")
    if simplify_ratio is not None:
        cmd.extend(["-si", str(simplify_ratio)])
    if texture_quality is not None:
        cmd.extend(["-tq", str(texture_quality)])

    # Step 7: Execute
    return _run_native_gltfpack(cmd, output_path)
