#!/usr/bin/env -S uv run
"""Test WASM gltfpack against three.js glTF models."""

from __future__ import annotations

import os
import sys
import tempfile
from collections import defaultdict
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

# Expected failure patterns: (substring, category)
EXPECTED_FAILURES: list[tuple[str, str]] = [
    ("resource not found", "external-resources"),
    ("Draco", "draco-input"),
    ("file requires", "missing-extension"),
    ("requires", "missing-feature"),
]

# Human-readable category descriptions
CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "external-resources": "WASM lacks filesystem access for external .bin/.texture files",
    "draco-input": "Draco-compressed input not supported by gltfpack",
    "missing-extension": "Missing required glTF extension",
    "missing-feature": "Missing required feature",
}


def get_bundled_version() -> str:
    """Get bundled WASM version."""
    if VERSION_PATH.exists():
        return VERSION_PATH.read_text().strip()
    return "unknown"


def classify_failure(msg: str) -> tuple[bool, str]:
    """Classify a failure as expected or unexpected.

    Returns:
        (is_expected, category) - category is empty string if unexpected
    """
    for pattern, category in EXPECTED_FAILURES:
        if pattern in msg:
            return True, category
    return False, ""


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
    expected_by_category: dict[str, list[str]] = defaultdict(list)
    unexpected_failed: list[tuple[str, str]] = []  # (model_name, error_msg)

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
                        f"  PASS {rel_path}: "
                        f"{size_kb:.1f}KB -> {out_size:.1f}KB ({delta:+.1f}%)"
                    )
                    passed += 1
                else:
                    is_expected, category = classify_failure(msg)
                    if is_expected:
                        print(f"  EXPECTED [{category}] {rel_path}")
                        expected_by_category[category].append(str(rel_path))
                    else:
                        print(f"  FAIL {rel_path}: {msg[:80]}")
                        unexpected_failed.append((str(rel_path), msg[:120]))
            except Exception as e:
                print(f"  ERROR {rel_path}: {e}")
                unexpected_failed.append((str(rel_path), str(e)[:120]))

    total_expected = sum(len(v) for v in expected_by_category.values())

    # Summary
    print()
    print(
        f"Results: {passed} passed, "
        f"{total_expected} expected failures, "
        f"{len(unexpected_failed)} unexpected failures"
    )

    if expected_by_category:
        print()
        print("Expected failures by category:")
        for category, models_list in sorted(expected_by_category.items()):
            desc = CATEGORY_DESCRIPTIONS.get(category, category)
            print(f"  [{category}] ({len(models_list)}): {desc}")
            for model_name in models_list:
                print(f"    - {model_name}")

    if unexpected_failed:
        print()
        print("UNEXPECTED FAILURES (investigate these):")
        for model_name, error_msg in unexpected_failed:
            print(f"  - {model_name}: {error_msg}")

    # Write to GITHUB_OUTPUT if available
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"passed={passed}\n")
            f.write(f"expected-failed={total_expected}\n")
            f.write(f"unexpected-failed={len(unexpected_failed)}\n")
            # Per-category counts
            for category in CATEGORY_DESCRIPTIONS:
                count = len(expected_by_category.get(category, []))
                f.write(f"expected-{category}={count}\n")

    # Fail only on unexpected failures
    if unexpected_failed:
        print()
        print(f"FAILED: {len(unexpected_failed)} unexpected failure(s)")
        return 1

    print()
    print("SUCCESS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
