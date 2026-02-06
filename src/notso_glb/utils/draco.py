"""Utilities for detecting Draco compression in GLB/glTF files."""

from __future__ import annotations

import json
import struct
from pathlib import Path

# GLB magic number (ASCII "glTF")
GLB_MAGIC = 0x46546C67

# GLB chunk types
CHUNK_TYPE_JSON = 0x4E4F534A  # ASCII "JSON"

# The Draco extension identifier
DRACO_EXTENSION = "KHR_draco_mesh_compression"


def has_draco_compression(file_path: str | Path) -> bool:
    """
    Detect if a GLB or glTF file uses Draco mesh compression.

    Args:
        file_path: Path to the GLB or glTF file

    Returns:
        True if the file uses Draco compression, False otherwise.
        Returns False if the file cannot be parsed or doesn't exist.
    """
    file_path = Path(file_path)

    if not file_path.is_file():
        return False

    ext = file_path.suffix.lower()

    try:
        if ext == ".glb":
            return _check_glb_for_draco(file_path)
        elif ext == ".gltf":
            return _check_gltf_for_draco(file_path)
        else:
            return False
    except (OSError, json.JSONDecodeError, struct.error, ValueError):
        # If we can't parse the file, assume no Draco (safer to try processing)
        return False


def _check_glb_for_draco(file_path: Path) -> bool:
    """Check a GLB file for Draco compression by parsing its JSON chunk."""
    with open(file_path, "rb") as f:
        # Read GLB header (12 bytes)
        header = f.read(12)
        if len(header) < 12:
            return False

        magic, version, length = struct.unpack("<III", header)

        # Verify GLB magic number
        if magic != GLB_MAGIC:
            return False

        # Read first chunk header (8 bytes)
        chunk_header = f.read(8)
        if len(chunk_header) < 8:
            return False

        chunk_length, chunk_type = struct.unpack("<II", chunk_header)

        # First chunk should be JSON
        if chunk_type != CHUNK_TYPE_JSON:
            return False

        # Read JSON chunk data
        json_data = f.read(chunk_length)
        if len(json_data) < chunk_length:
            return False

        # Decode and parse JSON
        json_str = json_data.decode("utf-8").rstrip("\x00")
        gltf_json = json.loads(json_str)

        return _json_has_draco(gltf_json)


def _check_gltf_for_draco(file_path: Path) -> bool:
    """Check a glTF JSON file for Draco compression."""
    with open(file_path, encoding="utf-8") as f:
        gltf_json = json.load(f)

    return _json_has_draco(gltf_json)


def _json_has_draco(gltf_json: dict[str, object]) -> bool:
    """Check if the glTF JSON structure indicates Draco compression is used."""
    # Check extensionsUsed array
    extensions_used = gltf_json.get("extensionsUsed", [])
    if isinstance(extensions_used, list) and DRACO_EXTENSION in extensions_used:
        return True

    # Also check extensionsRequired for completeness
    extensions_required = gltf_json.get("extensionsRequired", [])
    if isinstance(extensions_required, list) and DRACO_EXTENSION in extensions_required:
        return True

    return False
