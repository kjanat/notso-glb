#!/usr/bin/env -S uv run
"""Test WASM gltfpack against three.js glTF models."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from notso_glb.wasm import get_wasm_path, is_available, run_gltfpack_wasm

MODEL_DIR = Path(
    os.environ.get("MODEL_DIR", "test-models/three.js/examples/models/gltf")
)
VERSION_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "src"
    / "notso_glb"
    / "wasm"
    / "gltfpack.version"
)
MAX_FILE_SIZE = 10_000_000  # 10MB
MAX_MODELS = int(os.environ.get("MAX_MODELS", "30"))


def get_bundled_version() -> str:
    """Get bundled WASM version."""
    if VERSION_PATH.exists():
        return VERSION_PATH.read_text().strip()
    return "unknown"


def main() -> int:
    """Run WASM gltfpack tests on three.js models."""
    print("=== WASM gltfpack Test ===")
    print()

    if not is_available():
        print("ERROR: WASM runtime not available")
        print(f"  WASM path: {get_wasm_path()}")
        print(f"  WASM exists: {get_wasm_path().exists()}")
        return 1

    wasm_path = get_wasm_path()
    version = get_bundled_version()
    print(f"WASM version: {version}")
    print(f"WASM path: {wasm_path}")
    print(f"WASM size: {wasm_path.stat().st_size / 1024:.1f} KB")
    print()

    # Find test models
    models = list(MODEL_DIR.glob("**/*.glb")) + list(MODEL_DIR.glob("**/*.gltf"))
    models = [m for m in models if m.stat().st_size < MAX_FILE_SIZE]
    print(f"Found {len(models)} test models (<{MAX_FILE_SIZE // 1_000_000}MB)")
    print()

    passed = 0
    failed = 0
    skipped = 0

    for model in sorted(models)[:MAX_MODELS]:
        rel_path = model.relative_to(MODEL_DIR)
        size_kb = model.stat().st_size / 1024

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=True) as tmp:
            out_path = Path(tmp.name)
            try:
                success, _, msg = run_gltfpack_wasm(
                    model,
                    out_path,
                    texture_compress=False,  # WASM lacks BasisU
                    mesh_compress=True,
                )
                if success:
                    out_size = out_path.stat().st_size / 1024
                    delta = (1 - out_size / size_kb) * 100 if size_kb > 0 else 0
                    print(
                        f"  PASS {rel_path}: {size_kb:.1f}KB -> {out_size:.1f}KB ({delta:+.1f}%)"
                    )
                    passed += 1
                elif "Draco" in msg or "requires" in msg:
                    # Expected failures (Draco input, etc.)
                    print(f"  SKIP {rel_path}: {msg[:60]}")
                    skipped += 1
                else:
                    print(f"  FAIL {rel_path}: {msg[:80]}")
                    failed += 1
            except Exception as e:
                print(f"  ERROR {rel_path}: {e}")
                failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")

    # Write to GITHUB_OUTPUT if available
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"passed={passed}\n")
            f.write(f"failed={failed}\n")
            f.write(f"skipped={skipped}\n")

    # Allow up to 20% failures
    if failed > len(models) * 0.2:
        print("ERROR: Too many failures")
        return 1

    print("SUCCESS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
