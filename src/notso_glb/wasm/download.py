"""Download gltfpack WASM from npm."""

from __future__ import annotations

import io
import tarfile
import urllib.request
from pathlib import Path

# npm registry URL for gltfpack
NPM_REGISTRY_URL = "https://registry.npmjs.org/gltfpack"
WASM_FILENAME = "library.wasm"
CACHE_DIR = Path(__file__).parent / ".cache"


def _get_latest_tarball_url() -> tuple[str, str]:
    """Fetch latest gltfpack tarball URL and version from npm."""
    import json

    with urllib.request.urlopen(NPM_REGISTRY_URL, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    latest_version = data["dist-tags"]["latest"]
    tarball_url = data["versions"][latest_version]["dist"]["tarball"]
    return tarball_url, latest_version


def _download_wasm_from_tarball(tarball_url: str) -> bytes:
    """Download and extract WASM from npm tarball."""
    with urllib.request.urlopen(tarball_url, timeout=60) as resp:
        tarball_data = resp.read()

    with tarfile.open(fileobj=io.BytesIO(tarball_data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.name.endswith(WASM_FILENAME):
                f = tar.extractfile(member)
                if f:
                    return f.read()

    raise FileNotFoundError(f"{WASM_FILENAME} not found in npm package")


def get_wasm_path() -> Path:
    """
    Get path to gltfpack WASM, downloading from npm if needed.

    Returns cached WASM if available, otherwise downloads latest from npm.
    """
    CACHE_DIR.mkdir(exist_ok=True)
    version_file = CACHE_DIR / "version.txt"
    wasm_file = CACHE_DIR / "gltfpack.wasm"

    # Check if we need to download
    try:
        tarball_url, latest_version = _get_latest_tarball_url()
    except Exception as e:
        # Offline or npm unavailable - use cached if exists
        if wasm_file.exists():
            return wasm_file
        raise RuntimeError(f"Cannot fetch WASM version from npm: {e}") from e

    # Check cached version
    if wasm_file.exists() and version_file.exists():
        cached_version = version_file.read_text().strip()
        if cached_version == latest_version:
            return wasm_file

    # Download latest
    print(f"[INFO] Downloading gltfpack WASM v{latest_version} from npm...")
    wasm_data = _download_wasm_from_tarball(tarball_url)

    # Verify it's valid WASM (starts with \0asm)
    if not wasm_data.startswith(b"\x00asm"):
        raise ValueError("Downloaded file is not valid WASM")

    # Write cache
    wasm_file.write_bytes(wasm_data)
    version_file.write_text(latest_version)
    print(f"[INFO] Cached gltfpack WASM ({len(wasm_data) / 1024:.1f} KB)")

    return wasm_file


def get_cached_version() -> str | None:
    """Get cached WASM version, or None if not cached."""
    version_file = CACHE_DIR / "version.txt"
    if version_file.exists():
        return version_file.read_text().strip()
    return None


def clear_cache() -> None:
    """Clear cached WASM files."""
    import shutil

    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
