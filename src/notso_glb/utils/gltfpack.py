"""Wrapper for gltfpack mesh/texture compression tool."""

import shutil
import subprocess
import traceback
from pathlib import Path


def find_gltfpack() -> str | None:
    """Find gltfpack executable in PATH."""
    return shutil.which("gltfpack")


def run_gltfpack(
    input_path: Path,
    output_path: Path | None = None,
    *,
    texture_compress: bool = True,
    mesh_compress: bool = True,
    simplify_ratio: float | None = None,
    texture_quality: int | None = None,
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

    Returns:
        Tuple of (success, output_path, message)
    """
    gltfpack = find_gltfpack()
    if not gltfpack:
        return False, input_path, "gltfpack not found in PATH"

    input_path = Path(input_path)
    if not input_path.exists():
        return False, input_path, f"Input file not found: {input_path}"

    # Default output: input_packed.glb
    if output_path is None:
        stem = input_path.stem
        # Remove _packed suffix if already present to avoid _packed_packed
        if stem.endswith("_packed"):
            stem = stem[:-7]
        output_path = input_path.parent / f"{stem}_packed{input_path.suffix}"

    output_path = Path(output_path)

    # Build command
    cmd = [gltfpack, "-i", str(input_path), "-o", str(output_path)]

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
