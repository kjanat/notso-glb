"""WASM runtime for gltfpack."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .wasi import WasiFilesystem


def _get_wasm_path() -> Path:
    """Get path to bundled gltfpack.wasm."""
    return Path(__file__).parent / "gltfpack.wasm"


class GltfpackWasm(WasiFilesystem):
    """WASM-based gltfpack runner using wasmtime."""

    def _get_export(self, name: str) -> Any:
        """Get a named export from the WASM instance."""
        exports: Any = self._instance.exports(self._store)  # type: ignore[union-attr]
        return exports[name]

    def _upload_argv(self, argv: list[str]) -> int:
        """Upload argument vector to WASM memory."""
        encoded_args = [arg.encode("utf-8") for arg in argv]
        buf_size = len(argv) * 4
        for arg in encoded_args:
            buf_size += len(arg) + 1

        malloc = self._get_export("malloc")
        buf: int = malloc(self._store, buf_size)
        argp = buf + len(argv) * 4

        self._refresh_memory()
        assert self._memory_array is not None

        for i, arg in enumerate(encoded_args):
            self._set_u32(buf + i * 4, argp)
            # Copy string bytes
            for j, b in enumerate(arg):
                self._memory_array[argp + j] = b
            self._set_u8(argp + len(arg), 0)
            argp += len(arg) + 1

        return buf

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
            Func(self._store, FuncType([ValType.i32()], []), self.wasi_proc_exit),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_close",
            Func(
                self._store,
                FuncType([ValType.i32()], [ValType.i32()]),
                self.wasi_fd_close,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_fdstat_get",
            Func(
                self._store,
                FuncType([ValType.i32(), ValType.i32()], [ValType.i32()]),
                self.wasi_fd_fdstat_get,
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
                self.wasi_path_open32,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "path_filestat_get",
            Func(
                self._store,
                FuncType([ValType.i32()] * 5, [ValType.i32()]),
                self.wasi_path_filestat_get,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_prestat_get",
            Func(
                self._store,
                FuncType([ValType.i32(), ValType.i32()], [ValType.i32()]),
                self.wasi_fd_prestat_get,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_prestat_dir_name",
            Func(
                self._store,
                FuncType([ValType.i32()] * 3, [ValType.i32()]),
                self.wasi_fd_prestat_dir_name,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "path_remove_directory",
            Func(
                self._store,
                FuncType([ValType.i32()] * 3, [ValType.i32()]),
                self.wasi_path_remove_directory,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_fdstat_set_flags",
            Func(
                self._store,
                FuncType([ValType.i32(), ValType.i32()], [ValType.i32()]),
                self.wasi_fd_fdstat_set_flags,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_seek32",
            Func(
                self._store,
                FuncType([ValType.i32()] * 4, [ValType.i32()]),
                self.wasi_fd_seek32,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_read",
            Func(
                self._store,
                FuncType([ValType.i32()] * 4, [ValType.i32()]),
                self.wasi_fd_read,
            ),
        )
        linker.define(
            self._store,
            "wasi_snapshot_preview1",
            "fd_write",
            Func(
                self._store,
                FuncType([ValType.i32()] * 4, [ValType.i32()]),
                self.wasi_fd_write,
            ),
        )

        self._instance = linker.instantiate(self._store, module)

        # Call constructors
        exports: Any = self._instance.exports(self._store)
        ctors = exports.get("__wasm_call_ctors")
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

        pack_fn = self._get_export("pack")
        result: int = pack_fn(self._store, len(argv), buf)

        free_fn = self._get_export("free")
        free_fn(self._store, buf)

        log = self._output_buffer.decode("utf-8", errors="replace")

        if result != 0:
            return False, b"", log

        output_data = self._fs_interface.get(output_name, b"")
        return True, output_data, log
