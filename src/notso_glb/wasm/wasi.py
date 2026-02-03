"""WASI filesystem implementation for gltfpack WASM."""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING, Any

from .constants import WASI_EBADF, WASI_EINVAL, WASI_EIO, WASI_ENOSYS

if TYPE_CHECKING:
    from wasmtime import Instance, Memory, Store


class WasiFilesystem:
    """WASI filesystem implementation for in-memory file operations."""

    def __init__(self) -> None:
        self._store: Store | None = None
        self._instance: Instance | None = None
        self._fs_interface: dict[str, bytes] | None = None
        self._output_buffer: bytearray = bytearray()
        self._fds: dict[int, dict] = {}
        self._memory_array: ctypes.Array | None = None

    def _init_fds(self) -> None:
        """Initialize file descriptors."""
        self._output_buffer = bytearray()
        self._fds = {
            1: {"type": "output"},  # stdout
            2: {"type": "output"},  # stderr
            3: {"mount": "/", "path": "/"},
            4: {"mount": "/gltfpack-$pwd", "path": ""},
        }

    def _next_fd(self) -> int:
        """Get next available file descriptor."""
        fd = 5
        while fd in self._fds:
            fd += 1
        return fd

    # Memory access methods

    def _get_memory(self) -> Memory:
        """Get WASM memory export."""
        from wasmtime import Memory

        exports: Any = self._instance.exports(self._store)  # type: ignore[union-attr]
        memory = exports["memory"]
        assert isinstance(memory, Memory)
        return memory

    def _refresh_memory(self) -> None:
        """Refresh memory array reference (needed after memory growth)."""
        memory = self._get_memory()
        ptr = memory.data_ptr(self._store)  # type: ignore[arg-type]
        size = memory.data_len(self._store)  # type: ignore[arg-type]
        self._memory_array = (ctypes.c_ubyte * size).from_address(
            ctypes.addressof(ptr.contents)
        )

    def _get_string(self, offset: int, length: int) -> str:
        """Read string from WASM memory."""
        self._refresh_memory()
        assert self._memory_array is not None
        return bytes(self._memory_array[offset : offset + length]).decode("utf-8")

    def _set_u8(self, offset: int, value: int) -> None:
        """Write uint8 to WASM memory."""
        self._refresh_memory()
        assert self._memory_array is not None
        self._memory_array[offset] = value & 0xFF

    def _set_u32(self, offset: int, value: int) -> None:
        """Write uint32 (little-endian) to WASM memory."""
        self._refresh_memory()
        assert self._memory_array is not None
        val_bytes = value.to_bytes(4, "little")
        for i, b in enumerate(val_bytes):
            self._memory_array[offset + i] = b

    def _get_u32(self, offset: int) -> int:
        """Read uint32 (little-endian) from WASM memory."""
        self._refresh_memory()
        assert self._memory_array is not None
        return int.from_bytes(bytes(self._memory_array[offset : offset + 4]), "little")

    # WASI syscall implementations

    def wasi_proc_exit(self, rval: int) -> None:
        """WASI proc_exit syscall."""
        pass

    def wasi_fd_close(self, fd: int) -> int:
        """WASI fd_close syscall."""
        if fd not in self._fds:
            return WASI_EBADF
        try:
            fd_info = self._fds[fd]
            if "close_data" in fd_info and self._fs_interface is not None:
                name = fd_info.get("name", "")
                data = fd_info["data"][: fd_info["size"]]
                self._fs_interface[name] = bytes(data)
            del self._fds[fd]
            return 0
        except Exception:
            if fd in self._fds:
                del self._fds[fd]
            return WASI_EIO

    def wasi_fd_fdstat_get(self, fd: int, stat: int) -> int:
        """WASI fd_fdstat_get syscall."""
        if fd not in self._fds:
            return WASI_EBADF
        fd_info = self._fds[fd]
        filetype = 3 if "path" in fd_info else 4
        self._set_u8(stat + 0, filetype)
        self._set_u32(stat + 2, 0)
        self._set_u32(stat + 8, 0)
        self._set_u32(stat + 12, 0)
        self._set_u32(stat + 16, 0)
        self._set_u32(stat + 20, 0)
        return 0

    def wasi_path_open32(
        self,
        parent_fd: int,
        dirflags: int,
        path: int,
        path_len: int,
        oflags: int,
        fs_rights_base: int,
        fs_rights_inheriting: int,
        fdflags: int,
        opened_fd: int,
    ) -> int:
        """WASI path_open syscall (32-bit variant)."""
        if parent_fd not in self._fds or "path" not in self._fds[parent_fd]:
            return WASI_EBADF

        file_path = self._fds[parent_fd]["path"] + self._get_string(path, path_len)

        file_info: dict = {
            "name": file_path,
            "position": 0,
        }

        if oflags & 1:  # O_CREAT
            file_info["data"] = bytearray(4096)
            file_info["size"] = 0
            file_info["close_data"] = True
        else:
            if self._fs_interface is None or file_path not in self._fs_interface:
                return WASI_EIO
            file_info["data"] = bytearray(self._fs_interface[file_path])
            file_info["size"] = len(file_info["data"])

        fd = self._next_fd()
        self._fds[fd] = file_info
        self._set_u32(opened_fd, fd)
        return 0

    def wasi_path_filestat_get(
        self, parent_fd: int, flags: int, path: int, path_len: int, buf: int
    ) -> int:
        """WASI path_filestat_get syscall."""
        if parent_fd not in self._fds or "path" not in self._fds[parent_fd]:
            return WASI_EBADF

        name = self._get_string(path, path_len)
        for i in range(64):
            self._set_u8(buf + i, 0)

        filetype = 3 if name == "." else 4
        self._set_u8(buf + 16, filetype)
        return 0

    def wasi_fd_prestat_get(self, fd: int, buf: int) -> int:
        """WASI fd_prestat_get syscall."""
        if fd not in self._fds or "path" not in self._fds[fd]:
            return WASI_EBADF

        mount = self._fds[fd].get("mount", "").encode("utf-8")
        self._set_u8(buf, 0)
        self._set_u32(buf + 4, len(mount))
        return 0

    def wasi_fd_prestat_dir_name(self, fd: int, path: int, path_len: int) -> int:
        """WASI fd_prestat_dir_name syscall."""
        if fd not in self._fds or "path" not in self._fds[fd]:
            return WASI_EBADF

        mount = self._fds[fd].get("mount", "").encode("utf-8")
        if path_len != len(mount):
            return WASI_EINVAL

        self._refresh_memory()
        assert self._memory_array is not None
        for i, b in enumerate(mount):
            self._memory_array[path + i] = b
        return 0

    def wasi_path_remove_directory(
        self, parent_fd: int, path: int, path_len: int
    ) -> int:
        """WASI path_remove_directory syscall."""
        return WASI_EINVAL

    def wasi_fd_fdstat_set_flags(self, fd: int, flags: int) -> int:
        """WASI fd_fdstat_set_flags syscall."""
        return WASI_ENOSYS

    def wasi_fd_seek32(self, fd: int, offset: int, whence: int, newoffset: int) -> int:
        """WASI fd_seek syscall (32-bit variant)."""
        if fd not in self._fds:
            return WASI_EBADF

        fd_info = self._fds[fd]
        if whence == 0:
            new_pos = offset
        elif whence == 1:
            new_pos = fd_info.get("position", 0) + offset
        elif whence == 2:
            new_pos = fd_info.get("size", 0)
        else:
            return WASI_EINVAL

        if new_pos > fd_info.get("size", 0):
            return WASI_EINVAL

        fd_info["position"] = new_pos
        self._set_u32(newoffset, new_pos)
        return 0

    def wasi_fd_read(self, fd: int, iovs: int, iovs_len: int, nread: int) -> int:
        """WASI fd_read syscall."""
        if fd not in self._fds:
            return WASI_EBADF

        fd_info = self._fds[fd]
        total_read = 0

        for i in range(iovs_len):
            buf = self._get_u32(iovs + 8 * i)
            buf_len = self._get_u32(iovs + 8 * i + 4)

            pos = fd_info.get("position", 0)
            size = fd_info.get("size", 0)
            data = fd_info.get("data", b"")

            read_len = min(size - pos, buf_len)
            self._refresh_memory()
            assert self._memory_array is not None
            for j in range(read_len):
                self._memory_array[buf + j] = data[pos + j]

            fd_info["position"] = pos + read_len
            total_read += read_len

        self._set_u32(nread, total_read)
        return 0

    def wasi_fd_write(self, fd: int, iovs: int, iovs_len: int, nwritten: int) -> int:
        """WASI fd_write syscall."""
        if fd not in self._fds:
            return WASI_EBADF

        fd_info = self._fds[fd]
        total_written = 0

        for i in range(iovs_len):
            buf = self._get_u32(iovs + 8 * i)
            buf_len = self._get_u32(iovs + 8 * i + 4)

            self._refresh_memory()
            assert self._memory_array is not None
            write_data = bytes(self._memory_array[buf : buf + buf_len])

            if fd_info.get("type") == "output":
                self._output_buffer.extend(write_data)
            else:
                pos = fd_info.get("position", 0)
                data = fd_info.get("data", bytearray())

                if pos + buf_len > len(data):
                    new_len = max(len(data) * 2, pos + buf_len)
                    new_data = bytearray(new_len)
                    new_data[: len(data)] = data
                    fd_info["data"] = new_data
                    data = fd_info["data"]

                data[pos : pos + buf_len] = write_data
                fd_info["position"] = pos + buf_len
                fd_info["size"] = max(fd_info.get("size", 0), pos + buf_len)

            total_written += buf_len

        self._set_u32(nwritten, total_written)
        return 0
