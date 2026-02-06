"""WASM-based gltfpack integration using wasmtime."""

from __future__ import annotations

from pathlib import Path

from .runner import get_gltfpack, reset_gltfpack, run_gltfpack_wasm
from .runtime import GltfpackWasm, get_wasm_path

__all__ = [
    "GltfpackWasm",
    "get_gltfpack",
    "get_wasm_path",
    "is_available",
    "reset_gltfpack",
    "run_gltfpack_wasm",
]


def is_available() -> bool:
    """Check if WASM runtime (wasmtime) is importable and WASM exists."""
    try:
        import wasmtime  # noqa: F401

        return get_wasm_path().exists()
    except ImportError:
        return False
