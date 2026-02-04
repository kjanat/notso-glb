"""Tests for WASM constants module."""

from __future__ import annotations


class TestWasiConstants:
    """Tests for WASI error code constants."""

    def test_wasi_ebadf_value(self) -> None:
        """WASI_EBADF should be 8."""
        from notso_glb.wasm.constants import WASI_EBADF

        assert WASI_EBADF == 8
        assert isinstance(WASI_EBADF, int)

    def test_wasi_efault_value(self) -> None:
        """WASI_EFAULT should be 21."""
        from notso_glb.wasm.constants import WASI_EFAULT

        assert WASI_EFAULT == 21
        assert isinstance(WASI_EFAULT, int)

    def test_wasi_einval_value(self) -> None:
        """WASI_EINVAL should be 28."""
        from notso_glb.wasm.constants import WASI_EINVAL

        assert WASI_EINVAL == 28
        assert isinstance(WASI_EINVAL, int)

    def test_wasi_eio_value(self) -> None:
        """WASI_EIO should be 29."""
        from notso_glb.wasm.constants import WASI_EIO

        assert WASI_EIO == 29
        assert isinstance(WASI_EIO, int)

    def test_wasi_enosys_value(self) -> None:
        """WASI_ENOSYS should be 52."""
        from notso_glb.wasm.constants import WASI_ENOSYS

        assert WASI_ENOSYS == 52
        assert isinstance(WASI_ENOSYS, int)

    def test_all_constants_unique(self) -> None:
        """All error codes should be unique."""
        from notso_glb.wasm.constants import (
            WASI_EBADF,
            WASI_EFAULT,
            WASI_EINVAL,
            WASI_EIO,
            WASI_ENOSYS,
        )

        values = [WASI_EBADF, WASI_EFAULT, WASI_EINVAL, WASI_EIO, WASI_ENOSYS]
        assert len(values) == len(set(values))

    def test_all_constants_positive(self) -> None:
        """All error codes should be positive integers."""
        from notso_glb.wasm.constants import (
            WASI_EBADF,
            WASI_EFAULT,
            WASI_EINVAL,
            WASI_EIO,
            WASI_ENOSYS,
        )

        for value in [WASI_EBADF, WASI_EFAULT, WASI_EINVAL, WASI_EIO, WASI_ENOSYS]:
            assert value > 0
            assert isinstance(value, int)
