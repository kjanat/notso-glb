"""Tests for WASI filesystem implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from notso_glb.wasm.wasi import WasiFilesystem


class TestWasiExit:
    """Tests for WasiExit exception."""

    def test_stores_exit_code(self) -> None:
        """Should store exit code."""
        from notso_glb.wasm.wasi import WasiExit

        exc = WasiExit(42)

        assert exc.exit_code == 42

    def test_has_message(self) -> None:
        """Should have descriptive message."""
        from notso_glb.wasm.wasi import WasiExit

        exc = WasiExit(1)

        assert "1" in str(exc)
        assert "exit" in str(exc).lower()

    def test_is_exception(self) -> None:
        """Should be an Exception subclass."""
        from notso_glb.wasm.wasi import WasiExit

        exc = WasiExit(0)

        assert isinstance(exc, Exception)


class TestWasiFilesystemInit:
    """Tests for WasiFilesystem initialization."""

    def test_initializes_with_none_values(self) -> None:
        """Should initialize with None values."""
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()

        assert fs._store is None
        assert fs._instance is None
        assert fs._fs_interface is None

    def test_initializes_empty_collections(self) -> None:
        """Should initialize empty collections."""
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()

        assert isinstance(fs._output_buffer, bytearray)
        assert len(fs._output_buffer) == 0
        assert isinstance(fs._fds, dict)


class TestInitFds:
    """Tests for _init_fds method."""

    def test_creates_stdout_and_stderr(self) -> None:
        """Should create stdout and stderr file descriptors."""
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()
        fs._init_fds()

        assert 1 in fs._fds  # stdout
        assert 2 in fs._fds  # stderr
        assert fs._fds[1]["type"] == "output"
        assert fs._fds[2]["type"] == "output"

    def test_creates_mount_points(self) -> None:
        """Should create mount point file descriptors."""
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()
        fs._init_fds()

        assert 3 in fs._fds
        assert 4 in fs._fds
        assert "mount" in fs._fds[3]
        assert "mount" in fs._fds[4]

    def test_resets_output_buffer(self) -> None:
        """Should reset output buffer."""
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()
        fs._output_buffer = bytearray(b"old data")
        fs._init_fds()

        assert len(fs._output_buffer) == 0


class TestNextFd:
    """Tests for _next_fd method."""

    def test_returns_first_available_fd(self) -> None:
        """Should return first available fd."""
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()
        fs._init_fds()

        fd = fs._next_fd()

        assert fd >= 5

    def test_skips_existing_fds(self) -> None:
        """Should skip existing file descriptors."""
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()
        fs._init_fds()
        fs._fds[5] = {"test": "data"}

        fd = fs._next_fd()

        assert fd != 5


class TestMemoryAccess:
    """Tests for memory access methods."""

    def test_get_memory_requires_initialization(self) -> None:
        """Should raise error if not initialized."""
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()

        with pytest.raises(RuntimeError, match="not initialized"):
            fs._get_memory()

    def test_check_bounds_validates_offset(
        self, mock_wasi_fs: "WasiFilesystem"
    ) -> None:
        """Should validate memory offset bounds."""
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]

        with pytest.raises(ValueError, match="negative offset"):
            mock_wasi_fs._check_bounds("test", -1, 10)

    def test_check_bounds_validates_length(
        self, mock_wasi_fs: "WasiFilesystem"
    ) -> None:
        """Should validate memory access length."""
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]

        with pytest.raises(ValueError, match="out of bounds"):
            mock_wasi_fs._check_bounds("test", 90, 20)

    def test_set_u8_writes_byte(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should write single byte to memory."""
        mock_wasi_fs._memory_array = bytearray(10)  # type: ignore[assignment]

        mock_wasi_fs._set_u8(5, 42)

        assert mock_wasi_fs._memory_array[5] == 42  # type: ignore[index]

    def test_set_u8_masks_to_byte(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should mask value to single byte."""
        mock_wasi_fs._memory_array = bytearray(10)  # type: ignore[assignment]

        mock_wasi_fs._set_u8(5, 0x1FF)

        assert mock_wasi_fs._memory_array[5] == 0xFF  # type: ignore[index]

    def test_set_u32_writes_little_endian(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should write uint32 in little-endian format."""
        mock_wasi_fs._memory_array = bytearray(10)  # type: ignore[assignment]

        mock_wasi_fs._set_u32(0, 0x12345678)

        assert mock_wasi_fs._memory_array[0] == 0x78  # type: ignore[index]
        assert mock_wasi_fs._memory_array[1] == 0x56  # type: ignore[index]
        assert mock_wasi_fs._memory_array[2] == 0x34  # type: ignore[index]
        assert mock_wasi_fs._memory_array[3] == 0x12  # type: ignore[index]

    def test_get_u32_reads_little_endian(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should read uint32 in little-endian format."""
        mock_wasi_fs._memory_array = bytearray(  # type: ignore[assignment]
            [0x78, 0x56, 0x34, 0x12]
        )

        value = mock_wasi_fs._get_u32(0)

        assert value == 0x12345678

    def test_get_string_decodes_utf8(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should decode UTF-8 string from memory."""
        mock_wasi_fs._memory_array = bytearray(b"Hello\x00World")  # type: ignore[assignment]

        text = mock_wasi_fs._get_string(0, 5)

        assert text == "Hello"


class TestWasiSyscalls:
    """Tests for WASI syscall implementations."""

    def test_proc_exit_raises_wasi_exit(self) -> None:
        """Should raise WasiExit with exit code."""
        from notso_glb.wasm.wasi import WasiExit, WasiFilesystem

        fs = WasiFilesystem()

        with pytest.raises(WasiExit) as exc_info:
            fs.wasi_proc_exit(42)

        assert exc_info.value.exit_code == 42

    def test_fd_close_removes_fd(self) -> None:
        """Should remove file descriptor."""
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()
        fs._init_fds()
        fs._fds[10] = {"test": "data"}

        result = fs.wasi_fd_close(10)

        assert result == 0
        assert 10 not in fs._fds

    def test_fd_close_returns_ebadf_for_invalid_fd(self) -> None:
        """Should return EBADF for invalid fd."""
        from notso_glb.wasm.constants import WASI_EBADF
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()
        fs._init_fds()

        result = fs.wasi_fd_close(999)

        assert result == WASI_EBADF

    def test_fd_fdstat_get_identifies_output_fd(
        self, mock_wasi_fs: "WasiFilesystem"
    ) -> None:
        """Should identify output FDs (stdout/stderr)."""
        mock_wasi_fs._init_fds()
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]

        result = mock_wasi_fs.wasi_fd_fdstat_get(1, 0)

        assert result == 0
        # Check filetype is character device (2)
        assert mock_wasi_fs._memory_array[0] == 2  # type: ignore[index]

    def test_fd_fdstat_get_identifies_directory(
        self, mock_wasi_fs: "WasiFilesystem"
    ) -> None:
        """Should identify directory FDs."""
        mock_wasi_fs._init_fds()
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]

        result = mock_wasi_fs.wasi_fd_fdstat_get(3, 0)

        assert result == 0
        # Check filetype is directory (3)
        assert mock_wasi_fs._memory_array[0] == 3  # type: ignore[index]

    def test_fd_write_appends_to_output_buffer(
        self, mock_wasi_fs: "WasiFilesystem"
    ) -> None:
        """Should append to output buffer for stdout/stderr."""
        mock_wasi_fs._init_fds()
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]

        # Write "Hello" to memory at offset 0
        mock_wasi_fs._memory_array[0:5] = b"Hello"  # type: ignore[index]

        # Set up iovec: [ptr=0, len=5]
        mock_wasi_fs._set_u32(10, 0)  # buffer ptr
        mock_wasi_fs._set_u32(14, 5)  # buffer len

        result = mock_wasi_fs.wasi_fd_write(1, 10, 1, 20)

        assert result == 0
        assert mock_wasi_fs._output_buffer == b"Hello"
        assert mock_wasi_fs._get_u32(20) == 5  # bytes written

    def test_fd_read_reads_from_file(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should read from file data."""
        mock_wasi_fs._init_fds()
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]

        # Set up a file descriptor with data
        mock_wasi_fs._fds[10] = {
            "data": bytearray(b"Test data"),
            "size": 9,
            "position": 0,
        }

        # Set up iovec: [ptr=50, len=5]
        mock_wasi_fs._set_u32(0, 50)  # buffer ptr
        mock_wasi_fs._set_u32(4, 5)  # buffer len

        result = mock_wasi_fs.wasi_fd_read(10, 0, 1, 10)

        assert result == 0
        assert bytes(mock_wasi_fs._memory_array[50:55]) == b"Test "  # type: ignore[index]
        assert mock_wasi_fs._get_u32(10) == 5  # bytes read
        assert mock_wasi_fs._fds[10]["position"] == 5

    def test_fd_seek_updates_position(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should update file position."""
        mock_wasi_fs._init_fds()
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]
        mock_wasi_fs._fds[10] = {"size": 100, "position": 0}

        result = mock_wasi_fs.wasi_fd_seek32(10, 50, 0, 0)  # SEEK_SET

        assert result == 0
        assert mock_wasi_fs._fds[10]["position"] == 50

    def test_fd_seek_seek_cur(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should seek relative to current position."""
        mock_wasi_fs._init_fds()
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]
        mock_wasi_fs._fds[10] = {"size": 100, "position": 20}

        result = mock_wasi_fs.wasi_fd_seek32(10, 10, 1, 0)  # SEEK_CUR

        assert result == 0
        assert mock_wasi_fs._fds[10]["position"] == 30

    def test_fd_seek_seek_end(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should seek relative to end."""
        mock_wasi_fs._init_fds()
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]
        mock_wasi_fs._fds[10] = {"size": 100, "position": 0}

        result = mock_wasi_fs.wasi_fd_seek32(10, -10, 2, 0)  # SEEK_END

        assert result == 0
        assert mock_wasi_fs._fds[10]["position"] == 90

    def test_fd_seek_validates_bounds(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should validate seek position bounds."""
        from notso_glb.wasm.constants import WASI_EINVAL

        mock_wasi_fs._init_fds()
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]
        mock_wasi_fs._fds[10] = {"size": 100, "position": 0}

        result = mock_wasi_fs.wasi_fd_seek32(10, -10, 0, 0)  # Negative position

        assert result == WASI_EINVAL

    def test_path_remove_directory_returns_einval(self) -> None:
        """Should return EINVAL (not supported)."""
        from notso_glb.wasm.constants import WASI_EINVAL
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()

        result = fs.wasi_path_remove_directory(3, 0, 0)

        assert result == WASI_EINVAL

    def test_fd_fdstat_set_flags_returns_enosys(self) -> None:
        """Should return ENOSYS (not implemented)."""
        from notso_glb.wasm.constants import WASI_ENOSYS
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()

        result = fs.wasi_fd_fdstat_set_flags(1, 0)

        assert result == WASI_ENOSYS


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_fd_write_grows_file_buffer(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should grow file buffer when writing beyond capacity."""
        mock_wasi_fs._init_fds()
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]

        # Small initial buffer
        mock_wasi_fs._fds[10] = {
            "data": bytearray(10),
            "size": 0,
            "position": 0,
        }

        # Write 50 bytes
        mock_wasi_fs._memory_array[0:50] = b"X" * 50  # type: ignore[index]
        mock_wasi_fs._set_u32(60, 0)  # buffer ptr
        mock_wasi_fs._set_u32(64, 50)  # buffer len

        result = mock_wasi_fs.wasi_fd_write(10, 60, 1, 70)

        assert result == 0
        assert len(mock_wasi_fs._fds[10]["data"]) >= 50

    def test_fd_read_at_eof(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should handle read at EOF."""
        mock_wasi_fs._init_fds()
        mock_wasi_fs._memory_array = bytearray(100)  # type: ignore[assignment]

        mock_wasi_fs._fds[10] = {
            "data": bytearray(b"Test"),
            "size": 4,
            "position": 4,  # At EOF
        }

        mock_wasi_fs._set_u32(0, 50)  # buffer ptr
        mock_wasi_fs._set_u32(4, 10)  # buffer len

        result = mock_wasi_fs.wasi_fd_read(10, 0, 1, 10)

        assert result == 0
        assert mock_wasi_fs._get_u32(10) == 0  # 0 bytes read

    def test_handles_unicode_in_strings(self, mock_wasi_fs: "WasiFilesystem") -> None:
        """Should handle Unicode strings."""
        unicode_text = "Hello 世界 🌍"
        encoded = unicode_text.encode("utf-8")
        mock_wasi_fs._memory_array = bytearray(len(encoded))  # type: ignore[assignment]
        mock_wasi_fs._memory_array[:] = encoded  # type: ignore[index]

        text = mock_wasi_fs._get_string(0, len(encoded))

        assert text == unicode_text

    def test_fd_close_with_close_data_flag(self) -> None:
        """Should save file data when close_data flag is set."""
        from notso_glb.wasm.wasi import WasiFilesystem

        fs = WasiFilesystem()
        fs._init_fds()
        fs._fs_interface = {}
        fs._fds[10] = {
            "name": "output.glb",
            "data": bytearray(b"test data"),
            "size": 9,
            "close_data": True,
        }

        result = fs.wasi_fd_close(10)

        assert result == 0
        assert fs._fs_interface["output.glb"] == b"test data"
