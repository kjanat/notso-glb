"""WASM-based gltfpack integration using wasmtime."""

from __future__ import annotations

import ctypes
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wasmtime import Instance, Store

# WASI error codes
WASI_EBADF = 8
WASI_EINVAL = 28
WASI_EIO = 29
WASI_ENOSYS = 52


def _get_wasm_path() -> Path:
    """Get path to bundled gltfpack.wasm."""
    return Path(__file__).parent / "gltfpack.wasm"


def is_available() -> bool:
    """Check if WASM runtime is available."""
    try:
        import wasmtime  # noqa: F401

        return _get_wasm_path().exists()
    except ImportError:
        return False


class GltfpackWasm:
    """WASM-based gltfpack runner using wasmtime."""

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

    def _refresh_memory(self) -> None:
        """Refresh memory array reference (needed after memory growth)."""
        memory = self._instance.exports(self._store)["memory"]  # type: ignore
        ptr = memory.data_ptr(self._store)
        size = memory.data_len(self._store)
        self._memory_array = (ctypes.c_ubyte * size).from_address(
            ctypes.addressof(ptr.contents)
        )

    def _get_string(self, offset: int, length: int) -> str:
        """Read string from WASM memory."""
        self._refresh_memory()
        return bytes(self._memory_array[offset : offset + length]).decode("utf-8")

    def _set_u8(self, offset: int, value: int) -> None:
        """Write uint8 to WASM memory."""
        self._refresh_memory()
        self._memory_array[offset] = value & 0xFF

    def _set_u32(self, offset: int, value: int) -> None:
        """Write uint32 (little-endian) to WASM memory."""
        self._refresh_memory()
        val_bytes = value.to_bytes(4, "little")
        for i, b in enumerate(val_bytes):
            self._memory_array[offset + i] = b

    def _get_u32(self, offset: int) -> int:
        """Read uint32 (little-endian) from WASM memory."""
        self._refresh_memory()
        return int.from_bytes(bytes(self._memory_array[offset : offset + 4]), "little")

    def _upload_argv(self, argv: list[str]) -> int:
        """Upload argument vector to WASM memory."""
        encoded_args = [arg.encode("utf-8") for arg in argv]
        buf_size = len(argv) * 4
        for arg in encoded_args:
            buf_size += len(arg) + 1

        malloc = self._instance.exports(self._store)["malloc"]  # type: ignore
        buf = malloc(self._store, buf_size)
        argp = buf + len(argv) * 4

        self._refresh_memory()

        for i, arg in enumerate(encoded_args):
            self._set_u32(buf + i * 4, argp)
            # Copy string bytes
            for j, b in enumerate(arg):
                self._memory_array[argp + j] = b
            self._set_u8(argp + len(arg), 0)
            argp += len(arg) + 1

        return buf

    # WASI implementations
    def _wasi_proc_exit(self, rval: int) -> None:
        pass

    def _wasi_fd_close(self, fd: int) -> int:
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

    def _wasi_fd_fdstat_get(self, fd: int, stat: int) -> int:
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

    def _wasi_path_open32(
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

    def _wasi_path_filestat_get(
        self, parent_fd: int, flags: int, path: int, path_len: int, buf: int
    ) -> int:
        if parent_fd not in self._fds or "path" not in self._fds[parent_fd]:
            return WASI_EBADF

        name = self._get_string(path, path_len)
        for i in range(64):
            self._set_u8(buf + i, 0)

        filetype = 3 if name == "." else 4
        self._set_u8(buf + 16, filetype)
        return 0

    def _wasi_fd_prestat_get(self, fd: int, buf: int) -> int:
        if fd not in self._fds or "path" not in self._fds[fd]:
            return WASI_EBADF

        mount = self._fds[fd].get("mount", "").encode("utf-8")
        self._set_u8(buf, 0)
        self._set_u32(buf + 4, len(mount))
        return 0

    def _wasi_fd_prestat_dir_name(self, fd: int, path: int, path_len: int) -> int:
        if fd not in self._fds or "path" not in self._fds[fd]:
            return WASI_EBADF

        mount = self._fds[fd].get("mount", "").encode("utf-8")
        if path_len != len(mount):
            return WASI_EINVAL

        self._refresh_memory()
        for i, b in enumerate(mount):
            self._memory_array[path + i] = b
        return 0

    def _wasi_path_remove_directory(
        self, parent_fd: int, path: int, path_len: int
    ) -> int:
        return WASI_EINVAL

    def _wasi_fd_fdstat_set_flags(self, fd: int, flags: int) -> int:
        return WASI_ENOSYS

    def _wasi_fd_seek32(self, fd: int, offset: int, whence: int, newoffset: int) -> int:
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

    def _wasi_fd_read(self, fd: int, iovs: int, iovs_len: int, nread: int) -> int:
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
            for j in range(read_len):
                self._memory_array[buf + j] = data[pos + j]

            fd_info["position"] = pos + read_len
            total_read += read_len

        self._set_u32(nread, total_read)
        return 0

    def _wasi_fd_write(self, fd: int, iovs: int, iovs_len: int, nwritten: int) -> int:
        if fd not in self._fds:
            return WASI_EBADF

        fd_info = self._fds[fd]
        total_written = 0

        for i in range(iovs_len):
            buf = self._get_u32(iovs + 8 * i)
            buf_len = self._get_u32(iovs + 8 * i + 4)

            self._refresh_memory()
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

    def _initialize(self) -> None:
        """Initialize WASM instance with wasmtime."""
        if self._instance is not None:
            return

        from wasmtime import Engine, Func, FuncType, Linker, Module, Store, ValType

        engine = Engine()
        self._store = Store(engine)
        wasm_bytes = _get_wasm_path().read_bytes()
        module = Module(engine, wasm_bytes)

        linker = Linker(engine)

        # Define WASI functions
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "proc_exit",
            Func(self._store, FuncType([ValType.i32()], []), self._wasi_proc_exit),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_close",
            Func(
                self._store,
                FuncType([ValType.i32()], [ValType.i32()]),
                self._wasi_fd_close,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_fdstat_get",
            Func(
                self._store,
                FuncType([ValType.i32(), ValType.i32()], [ValType.i32()]),
                self._wasi_fd_fdstat_get,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "path_open32",
            Func(
                self._store,
                FuncType(
                    [ValType.i32()] * 9,
                    [ValType.i32()],
                ),
                self._wasi_path_open32,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "path_filestat_get",
            Func(
                self._store,
                FuncType([ValType.i32()] * 5, [ValType.i32()]),
                self._wasi_path_filestat_get,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_prestat_get",
            Func(
                self._store,
                FuncType([ValType.i32(), ValType.i32()], [ValType.i32()]),
                self._wasi_fd_prestat_get,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_prestat_dir_name",
            Func(
                self._store,
                FuncType([ValType.i32()] * 3, [ValType.i32()]),
                self._wasi_fd_prestat_dir_name,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "path_remove_directory",
            Func(
                self._store,
                FuncType([ValType.i32()] * 3, [ValType.i32()]),
                self._wasi_path_remove_directory,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_fdstat_set_flags",
            Func(
                self._store,
                FuncType([ValType.i32(), ValType.i32()], [ValType.i32()]),
                self._wasi_fd_fdstat_set_flags,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_seek32",
            Func(
                self._store,
                FuncType([ValType.i32()] * 4, [ValType.i32()]),
                self._wasi_fd_seek32,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_read",
            Func(
                self._store,
                FuncType([ValType.i32()] * 4, [ValType.i32()]),
                self._wasi_fd_read,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_write",
            Func(
                self._store,
                FuncType([ValType.i32()] * 4, [ValType.i32()]),
                self._wasi_fd_write,
            ),
        )

        self._instance = linker.instantiate(self._store, module)

        # Call constructors
        ctors = self._instance.exports(self._store).get("__wasm_call_ctors")
        if ctors:
            ctors(self._store)

    def pack(
        self,
        input_data: bytes,
        input_name: str = "input.glb",
        output_name: str = "output.glb",
        args: list[str] | None = None,
    ) -> tuple[bool, bytes, str]:
        """
        Run gltfpack on input data.

        Args:
            input_data: Input GLB/glTF bytes
            input_name: Virtual input filename
            output_name: Virtual output filename
            args: Additional gltfpack arguments

        Returns:
            Tuple of (success, output_bytes, log_message)
        """
        self._initialize()
        self._init_fds()

        self._fs_interface = {input_name: input_data}

        argv = ["gltfpack", "-i", input_name, "-o", output_name]
        if args:
            argv.extend(args)

        buf = self._upload_argv(argv)

        pack_fn = self._instance.exports(self._store)["pack"]  # type: ignore
        result = pack_fn(self._store, len(argv), buf)

        free_fn = self._instance.exports(self._store)["free"]  # type: ignore
        free_fn(self._store, buf)

        log = self._output_buffer.decode("utf-8", errors="replace")

        if result != 0:
            return False, b"", log

        output_data = self._fs_interface.get(output_name, b"")
        return True, output_data, log


# Singleton instance
_gltfpack: GltfpackWasm | None = None


def get_gltfpack() -> GltfpackWasm:
    """Get or create singleton GltfpackWasm instance."""
    global _gltfpack
    if _gltfpack is None:
        _gltfpack = GltfpackWasm()
    return _gltfpack


def run_gltfpack_wasm(
    input_path: Path,
    output_path: Path | None = None,
    *,
    texture_compress: bool = True,
    mesh_compress: bool = True,
    simplify_ratio: float | None = None,
    texture_quality: int | None = None,
) -> tuple[bool, Path, str]:
    """
    Run gltfpack via WASM on a GLB/glTF file.

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
    if not is_available():
        return False, input_path, "WASM runtime not available"

    input_path = Path(input_path)
    if not input_path.is_file():
        return False, input_path, f"Input file not found: {input_path}"

    if output_path is None:
        stem = input_path.stem
        if stem.endswith("_packed"):
            stem = stem[:-7]
        output_path = input_path.parent / f"{stem}_packed{input_path.suffix}"

    output_path = Path(output_path)

    args: list[str] = []
    if texture_compress:
        args.append("-tc")
    if mesh_compress:
        args.append("-cc")
    if simplify_ratio is not None:
        if not (0.0 <= simplify_ratio <= 1.0):
            return (
                False,
                input_path,
                f"simplify_ratio must be [0.0, 1.0]: {simplify_ratio}",
            )
        args.extend(["-si", str(simplify_ratio)])
    if texture_quality is not None:
        if not (1 <= texture_quality <= 10):
            return (
                False,
                input_path,
                f"texture_quality must be [1, 10]: {texture_quality}",
            )
        args.extend(["-tq", str(texture_quality)])

    try:
        gltfpack = get_gltfpack()
        input_data = input_path.read_bytes()
        success, output_data, log = gltfpack.pack(
            input_data,
            input_name=input_path.name,
            output_name=output_path.name,
            args=args,
        )

        if not success:
            return False, output_path, f"gltfpack failed: {log}"

        output_path.write_bytes(output_data)
        return True, output_path, "Success"

    except Exception as e:
        return False, output_path, f"WASM error: {e}"
