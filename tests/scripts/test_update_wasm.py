"""Tests for update_wasm script."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest


class TestGetNpmInfo:
    """Tests for get_npm_info function."""

    @patch("scripts.update_wasm.urllib.request.urlopen")
    def test_fetches_npm_registry_data(self, mock_urlopen: MagicMock) -> None:
        """Should fetch and parse npm registry JSON."""
        from scripts.update_wasm import get_npm_info

        mock_data = {"name": "gltfpack", "dist-tags": {"latest": "1.0.0"}}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = get_npm_info()

        assert result == mock_data
        mock_urlopen.assert_called_once()

    @patch("scripts.update_wasm.urllib.request.urlopen")
    def test_handles_network_timeout(self, mock_urlopen: MagicMock) -> None:
        """Should raise on network timeout."""
        from urllib.error import URLError

        from scripts.update_wasm import get_npm_info

        mock_urlopen.side_effect = URLError("timeout")

        with pytest.raises(URLError):
            get_npm_info()


class TestGetVersionInfo:
    """Tests for get_version_info function."""

    @patch("scripts.update_wasm.get_npm_info")
    def test_returns_latest_version_by_default(self, mock_get_info: MagicMock) -> None:
        """Should return latest version when no version specified."""
        from scripts.update_wasm import get_version_info

        mock_get_info.return_value = {
            "dist-tags": {"latest": "1.2.3"},
            "versions": {
                "1.2.3": {"dist": {"tarball": "https://example.com/gltfpack-1.2.3.tgz"}}
            },
        }

        url, version = get_version_info()

        assert version == "1.2.3"
        assert "1.2.3" in url

    @patch("scripts.update_wasm.get_npm_info")
    def test_returns_specific_version(self, mock_get_info: MagicMock) -> None:
        """Should return specific version when requested."""
        from scripts.update_wasm import get_version_info

        mock_get_info.return_value = {
            "dist-tags": {"latest": "1.2.3"},
            "versions": {
                "1.0.0": {"dist": {"tarball": "https://example.com/gltfpack-1.0.0.tgz"}},
                "1.2.3": {"dist": {"tarball": "https://example.com/gltfpack-1.2.3.tgz"}},
            },
        }

        url, version = get_version_info("1.0.0")

        assert version == "1.0.0"
        assert "1.0.0" in url

    @patch("scripts.update_wasm.get_npm_info")
    def test_raises_on_invalid_version(self, mock_get_info: MagicMock) -> None:
        """Should raise ValueError for invalid version."""
        from scripts.update_wasm import get_version_info

        mock_get_info.return_value = {
            "dist-tags": {"latest": "1.2.3"},
            "versions": {
                "1.2.3": {"dist": {"tarball": "https://example.com/gltfpack-1.2.3.tgz"}},
                "1.2.2": {"dist": {"tarball": "https://example.com/gltfpack-1.2.2.tgz"}},
                "1.2.1": {"dist": {"tarball": "https://example.com/gltfpack-1.2.1.tgz"}},
                "1.2.0": {"dist": {"tarball": "https://example.com/gltfpack-1.2.0.tgz"}},
                "1.1.0": {"dist": {"tarball": "https://example.com/gltfpack-1.1.0.tgz"}},
            },
        }

        with pytest.raises(ValueError, match="Version 9.9.9 not found"):
            get_version_info("9.9.9")


class TestDownloadWasm:
    """Tests for download_wasm function."""

    @patch("scripts.update_wasm.urllib.request.urlopen")
    def test_extracts_wasm_from_tarball(self, mock_urlopen: MagicMock) -> None:
        """Should extract library.wasm from npm tarball."""
        from scripts.update_wasm import download_wasm

        # Create a valid tar.gz with library.wasm
        wasm_data = b"\x00asm\x01\x00\x00\x00"  # Valid WASM magic bytes
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="package/library.wasm")
            info.size = len(wasm_data)
            tar.addfile(info, io.BytesIO(wasm_data))
        tar_buffer.seek(0)

        mock_response = MagicMock()
        mock_response.read.return_value = tar_buffer.read()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = download_wasm("https://example.com/package.tgz")

        assert result == wasm_data

    @patch("scripts.update_wasm.urllib.request.urlopen")
    def test_raises_when_wasm_not_found(self, mock_urlopen: MagicMock) -> None:
        """Should raise FileNotFoundError if WASM not in tarball."""
        from scripts.update_wasm import download_wasm

        # Create tarball without library.wasm
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="package/other_file.txt")
            info.size = 5
            tar.addfile(info, io.BytesIO(b"hello"))
        tar_buffer.seek(0)

        mock_response = MagicMock()
        mock_response.read.return_value = tar_buffer.read()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with pytest.raises(FileNotFoundError, match="library.wasm not found"):
            download_wasm("https://example.com/package.tgz")


class TestGetBundledVersion:
    """Tests for get_bundled_version function."""

    def test_returns_version_when_file_exists(self, tmp_path: Path) -> None:
        """Should return version from file."""
        from scripts.update_wasm import get_bundled_version

        version_file = tmp_path / "gltfpack.version"
        version_file.write_text("1.0.0\n")

        with patch("scripts.update_wasm.VERSION_PATH", version_file):
            result = get_bundled_version()

        assert result == "1.0.0"

    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        """Should return None when version file doesn't exist."""
        from scripts.update_wasm import get_bundled_version

        version_file = tmp_path / "nonexistent.version"

        with patch("scripts.update_wasm.VERSION_PATH", version_file):
            result = get_bundled_version()

        assert result is None


class TestUpdateBundle:
    """Tests for update_bundle function."""

    @patch("scripts.update_wasm.download_wasm")
    @patch("scripts.update_wasm.get_version_info")
    @patch("scripts.update_wasm.get_bundled_version")
    def test_downloads_and_saves_wasm(
        self,
        mock_get_bundled: MagicMock,
        mock_get_version: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should download WASM and save version."""
        from scripts.update_wasm import update_bundle

        mock_get_bundled.return_value = None
        mock_get_version.return_value = ("https://example.com/package.tgz", "1.0.0")
        mock_download.return_value = b"\x00asm\x01\x00\x00\x00test"

        bundle_path = tmp_path / "gltfpack.wasm"
        version_path = tmp_path / "gltfpack.version"

        with patch("scripts.update_wasm.BUNDLE_PATH", bundle_path):
            with patch("scripts.update_wasm.VERSION_PATH", version_path):
                updated, msg = update_bundle()

        assert updated is True
        assert "1.0.0" in msg
        assert bundle_path.exists()
        assert version_path.read_text().strip() == "1.0.0"

    @patch("scripts.update_wasm.get_version_info")
    @patch("scripts.update_wasm.get_bundled_version")
    def test_skips_download_if_already_latest(
        self,
        mock_get_bundled: MagicMock,
        mock_get_version: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should skip download if already at latest version."""
        from scripts.update_wasm import update_bundle

        mock_get_bundled.return_value = "1.0.0"
        mock_get_version.return_value = ("https://example.com/package.tgz", "1.0.0")

        bundle_path = tmp_path / "gltfpack.wasm"
        bundle_path.write_bytes(b"\x00asm")

        with patch("scripts.update_wasm.BUNDLE_PATH", bundle_path):
            updated, msg = update_bundle()

        assert updated is False
        assert "Already at latest" in msg

    @patch("scripts.update_wasm.download_wasm")
    @patch("scripts.update_wasm.get_version_info")
    @patch("scripts.update_wasm.get_bundled_version")
    def test_validates_wasm_magic_bytes(
        self,
        mock_get_bundled: MagicMock,
        mock_get_version: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should validate WASM magic bytes."""
        from scripts.update_wasm import update_bundle

        mock_get_bundled.return_value = None
        mock_get_version.return_value = ("https://example.com/package.tgz", "1.0.0")
        mock_download.return_value = b"invalid data"

        bundle_path = tmp_path / "gltfpack.wasm"
        version_path = tmp_path / "gltfpack.version"

        with patch("scripts.update_wasm.BUNDLE_PATH", bundle_path):
            with patch("scripts.update_wasm.VERSION_PATH", version_path):
                with pytest.raises(ValueError, match="not valid WASM"):
                    update_bundle()

    @patch("scripts.update_wasm.download_wasm")
    @patch("scripts.update_wasm.get_version_info")
    @patch("scripts.update_wasm.get_bundled_version")
    def test_forces_download_for_specific_version(
        self,
        mock_get_bundled: MagicMock,
        mock_get_version: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should force download when specific version requested."""
        from scripts.update_wasm import update_bundle

        mock_get_bundled.return_value = "1.0.0"
        mock_get_version.return_value = ("https://example.com/package.tgz", "1.0.0")
        mock_download.return_value = b"\x00asm\x01\x00\x00\x00"

        bundle_path = tmp_path / "gltfpack.wasm"
        version_path = tmp_path / "gltfpack.version"

        with patch("scripts.update_wasm.BUNDLE_PATH", bundle_path):
            with patch("scripts.update_wasm.VERSION_PATH", version_path):
                updated, msg = update_bundle(target_version="1.0.0")

        assert updated is True
        assert "1.0.0" in msg


class TestMainFunction:
    """Tests for main CLI function."""

    def test_help_flag(self) -> None:
        """Should show help and exit with 0."""
        from scripts.update_wasm import main

        with patch("sys.argv", ["update_wasm.py", "--help"]):
            result = main()

        assert result == 0

    @patch("scripts.update_wasm.get_bundled_version")
    def test_show_version_flag(self, mock_get_bundled: MagicMock) -> None:
        """Should show current version."""
        from scripts.update_wasm import main

        mock_get_bundled.return_value = "1.0.0"

        with patch("sys.argv", ["update_wasm.py", "--show-version"]):
            result = main()

        assert result == 0

    @patch("scripts.update_wasm.get_version_info")
    @patch("scripts.update_wasm.get_bundled_version")
    def test_check_flag_up_to_date(
        self, mock_get_bundled: MagicMock, mock_get_version: MagicMock
    ) -> None:
        """Should check if update available."""
        from scripts.update_wasm import main

        mock_get_bundled.return_value = "1.0.0"
        mock_get_version.return_value = ("url", "1.0.0")

        with patch("sys.argv", ["update_wasm.py", "--check"]):
            result = main()

        assert result == 0

    @patch("scripts.update_wasm.get_version_info")
    @patch("scripts.update_wasm.get_bundled_version")
    def test_check_flag_update_available(
        self, mock_get_bundled: MagicMock, mock_get_version: MagicMock
    ) -> None:
        """Should return 1 when update available."""
        from scripts.update_wasm import main

        mock_get_bundled.return_value = "1.0.0"
        mock_get_version.return_value = ("url", "1.2.0")

        with patch("sys.argv", ["update_wasm.py", "--check"]):
            result = main()

        assert result == 1

    @patch("scripts.update_wasm.update_bundle")
    def test_update_without_version(self, mock_update: MagicMock) -> None:
        """Should update to latest version."""
        from scripts.update_wasm import main

        mock_update.return_value = (True, "Updated: unknown -> 1.0.0")

        with patch("sys.argv", ["update_wasm.py"]):
            result = main()

        assert result == 0
        mock_update.assert_called_once_with(None)

    @patch("scripts.update_wasm.update_bundle")
    def test_update_with_specific_version(self, mock_update: MagicMock) -> None:
        """Should update to specific version."""
        from scripts.update_wasm import main

        mock_update.return_value = (True, "Updated: 1.0.0 -> 1.2.0")

        with patch("sys.argv", ["update_wasm.py", "--version", "1.2.0"]):
            result = main()

        assert result == 0
        mock_update.assert_called_once_with("1.2.0")

    def test_version_flag_without_argument(self) -> None:
        """Should error when --version has no argument."""
        from scripts.update_wasm import main

        with patch("sys.argv", ["update_wasm.py", "--version"]):
            result = main()

        assert result == 1

    @patch("scripts.update_wasm.update_bundle")
    def test_handles_update_exception(self, mock_update: MagicMock) -> None:
        """Should return 1 on update exception."""
        from scripts.update_wasm import main

        mock_update.side_effect = ValueError("Network error")

        with patch("sys.argv", ["update_wasm.py"]):
            result = main()

        assert result == 1


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @patch("scripts.update_wasm.urllib.request.urlopen")
    def test_handles_malformed_json(self, mock_urlopen: MagicMock) -> None:
        """Should raise on malformed JSON from npm."""
        from scripts.update_wasm import get_npm_info

        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json {"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with pytest.raises(json.JSONDecodeError):
            get_npm_info()

    @patch("scripts.update_wasm.urllib.request.urlopen")
    def test_handles_empty_tarball(self, mock_urlopen: MagicMock) -> None:
        """Should handle empty tarball gracefully."""
        from scripts.update_wasm import download_wasm

        # Create empty tarball
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
            pass
        tar_buffer.seek(0)

        mock_response = MagicMock()
        mock_response.read.return_value = tar_buffer.read()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with pytest.raises(FileNotFoundError):
            download_wasm("https://example.com/package.tgz")

    def test_bundled_version_strips_whitespace(self, tmp_path: Path) -> None:
        """Should strip whitespace from version file."""
        from scripts.update_wasm import get_bundled_version

        version_file = tmp_path / "gltfpack.version"
        version_file.write_text("  1.0.0  \n\n")

        with patch("scripts.update_wasm.VERSION_PATH", version_file):
            result = get_bundled_version()

        assert result == "1.0.0"

    @patch("scripts.update_wasm.download_wasm")
    @patch("scripts.update_wasm.get_version_info")
    @patch("scripts.update_wasm.get_bundled_version")
    def test_handles_very_large_wasm(
        self,
        mock_get_bundled: MagicMock,
        mock_get_version: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should handle very large WASM files."""
        from scripts.update_wasm import update_bundle

        mock_get_bundled.return_value = None
        mock_get_version.return_value = ("https://example.com/package.tgz", "2.0.0")
        # Create 10MB WASM (simulating large file)
        large_wasm = b"\x00asm\x01\x00\x00\x00" + b"\x00" * (10 * 1024 * 1024)
        mock_download.return_value = large_wasm

        bundle_path = tmp_path / "gltfpack.wasm"
        version_path = tmp_path / "gltfpack.version"

        with patch("scripts.update_wasm.BUNDLE_PATH", bundle_path):
            with patch("scripts.update_wasm.VERSION_PATH", version_path):
                updated, msg = update_bundle()

        assert updated is True
        assert bundle_path.stat().st_size > 10 * 1024 * 1024