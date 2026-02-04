"""Texture resizing functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import bpy

from notso_glb.utils.logging import bright_cyan
from notso_glb.utils.logging import dim
from notso_glb.utils.logging import log_detail
from notso_glb.utils.logging import log_warn
from notso_glb.utils.logging import magenta

if TYPE_CHECKING:
    from bpy.types import Image

# Images to skip during resize
_SKIP_IMAGES = frozenset(["Render Result", "Viewer Node"])


def _nearest_pot(n: int) -> int:
    """Round to nearest power of two."""
    if n <= 1:
        return 1
    bl = (n - 1).bit_length()
    lower = 1 << (bl - 1)
    upper = 1 << bl
    return lower if (n - lower) < (upper - n) else upper


def _is_power_of_two(n: int) -> bool:
    """Check if n is a power of two."""
    return n > 0 and (n & (n - 1)) == 0


def _should_skip_image(img: Image, max_size: int, force_pot: bool) -> bool:
    """Determine if image should be skipped."""
    if img.name in _SKIP_IMAGES:
        return True
    w, h = img.size[0], img.size[1]
    if w <= max_size and h <= max_size:
        if not force_pot:
            return True
        if _is_power_of_two(w) and _is_power_of_two(h):
            return True
    return False


def _calc_scaled_size(w: int, h: int, max_size: int) -> tuple[int, int]:
    """Calculate new size maintaining aspect ratio."""
    if w > h:
        new_w = min(max_size, w)
        new_h = int(h * (new_w / w))
    else:
        new_h = min(max_size, h)
        new_w = int(w * (new_h / h))
    return new_w, new_h


def _adjust_to_pot(w: int, h: int, max_size: int) -> tuple[int, int]:
    """Adjust dimensions to power-of-two, clamped to max_size."""
    w = _nearest_pot(w)
    h = _nearest_pot(h)
    while w > max_size:
        w //= 2
    while h > max_size:
        h //= 2
    return w, h


def _adjust_to_even(w: int, h: int) -> tuple[int, int]:
    """Adjust dimensions to even numbers."""
    if w % 2 != 0:
        w += 1
    if h % 2 != 0:
        h += 1
    return w, h


def resize_textures(max_size: int = 1024, force_pot: bool = False) -> int:
    """
    Resize all textures larger than max_size.

    Args:
        max_size: Maximum dimension (default 1024)
        force_pot: Force power-of-two dimensions (better GPU compatibility)
    """
    resized = 0

    for img in bpy.data.images:
        if _should_skip_image(img, max_size, force_pot):
            continue

        w, h = img.size[0], img.size[1]
        new_w, new_h = _calc_scaled_size(w, h, max_size)

        if force_pot:
            new_w, new_h = _adjust_to_pot(new_w, new_h, max_size)
        else:
            new_w, new_h = _adjust_to_even(new_w, new_h)

        if new_w == w and new_h == h:
            continue

        try:
            img.scale(new_w, new_h)
            resized += 1
            pot_note = f" {magenta('(POT)')}" if force_pot else ""
            log_detail(
                f"{img.name}: {dim(f'{w}x{h}')} -> {bright_cyan(f'{new_w}x{new_h}')}{pot_note}"
            )
        except Exception as e:
            log_warn(f"Failed to resize {img.name}: {e}")

    return resized
