#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Download and update bundled gltfpack WASM from npm.

Usage:
    uv run scripts/update_wasm.py                  # Update to latest
    uv run scripts/update_wasm.py --version 1.0.0  # Update to specific version
    uv run scripts/update_wasm.py --check          # Check if update available
    uv run scripts/update_wasm.py --show-version   # Show current bundled version
"""

from __future__ import annotations

import io
import json
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

NPM_REGISTRY_URL = "https://registry.npmjs.org/gltfpack"
WASM_FILENAME = "library.wasm"
BUNDLE_PATH = (
    Path(__file__).parent.parent / "src" / "notso_glb" / "wasm" / "gltfpack.wasm"
)
VERSION_PATH = BUNDLE_PATH.with_suffix(".version")


def get_npm_info() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fetch full npm package info."""
    with urllib.request.urlopen(NPM_REGISTRY_URL, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_version_info(version: str | None = None) -> tuple[str, str]:
    """
    Fetch tarball URL and version from npm.

    Args:
        version: Specific version to resolve, or None for latest.

    Returns:
        Tuple of (tarball_url, resolved_version).
    """
    data = get_npm_info()

    resolved_version: str = (
        version if version is not None else data["dist-tags"]["latest"]
    )

    if resolved_version not in data["versions"]:
        available = sorted(data["versions"].keys())[-5:]
        raise ValueError(
            f"Version {resolved_version} not found. Recent: {', '.join(available)}"
        )

    tarball_url: str = data["versions"][resolved_version]["dist"]["tarball"]
    return tarball_url, resolved_version


def download_wasm(tarball_url: str) -> bytes:
    """
    Download and extract WASM from npm tarball.

    Args:
        tarball_url: URL of the npm tarball to download.

    Returns:
        Raw WASM bytes.
    """
    with urllib.request.urlopen(tarball_url, timeout=60) as resp:
        tarball_data = resp.read()

    with tarfile.open(fileobj=io.BytesIO(tarball_data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.name.endswith(WASM_FILENAME):
                f = tar.extractfile(member)
                if f:
                    return f.read()

    raise FileNotFoundError(f"{WASM_FILENAME} not found in npm package")


def get_bundled_version() -> str | None:
    """Get version of bundled WASM, or None if unknown."""
    if VERSION_PATH.exists():
        return VERSION_PATH.read_text().strip()
    return None


def update_bundle(target_version: str | None = None) -> tuple[bool, str]:
    """
    Download WASM and update the bundle.

    Args:
        target_version: Specific version to download, or None for latest.

    Returns:
        Tuple of (updated, message)
    """
    tarball_url, version = get_version_info(target_version)
    current_version = get_bundled_version()

    # Skip download only if version matches AND wasm file exists
    if current_version == version and target_version is None and BUNDLE_PATH.exists():
        return False, f"Already at latest version: {version}"

    print(f"[INFO] Downloading gltfpack WASM v{version} from npm...")
    print(f"[INFO] Source: {tarball_url}")
    wasm_data = download_wasm(tarball_url)

    # Verify it's valid WASM (magic bytes: \0asm)
    if not wasm_data.startswith(b"\x00asm"):
        raise ValueError("Downloaded file is not valid WASM")

    # Update bundle
    BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ = BUNDLE_PATH.write_bytes(wasm_data)
    _ = VERSION_PATH.write_text(f"{version}\n")

    size_kb = len(wasm_data) / 1024
    msg = f"Updated: {current_version or 'unknown'} -> {version} ({size_kb:.1f} KB)"
    return True, msg


def main() -> int:
    """CLI entry point."""
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    if "--show-version" in args:
        version = get_bundled_version()
        print(f"Bundled gltfpack WASM: {version or 'unknown'}")
        return 0

    if "--check" in args:
        current = get_bundled_version()
        _, latest = get_version_info()
        print(f"Bundled: {current or 'unknown'}")
        print(f"Latest:  {latest}")
        if current != latest:
            print("Update available!")
            return 1
        print("Up to date.")
        return 0

    # Parse --version argument
    target_version = None
    if "--version" in args:
        idx = args.index("--version")
        if idx + 1 < len(args):
            target_version = args[idx + 1]
        else:
            print("[ERROR] --version requires a version argument", file=sys.stderr)
            return 1

    # Update
    try:
        updated, msg = update_bundle(target_version)
        print(f"[INFO] {msg}")
        return 0 if updated or "Already" in msg else 1
    except (
        OSError,
        ValueError,
        tarfile.TarError,
        json.JSONDecodeError,
        urllib.error.URLError,
    ) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
