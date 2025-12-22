"""Texture resizing functions."""

import bpy  # type: ignore[import-untyped]

from notso_glb.utils.logging import bright_cyan, dim, log_detail, log_warn, magenta


def resize_textures(max_size: int = 1024, force_pot: bool = False) -> int:
    """
    Resize all textures larger than max_size.

    Args:
        max_size: Maximum dimension (default 1024)
        force_pot: Force power-of-two dimensions (better GPU compatibility)
    """
    resized = 0

    def nearest_pot(n: int) -> int:
        """Round to nearest power of two."""
        if n <= 0:
            return 1
        lower = 1 << (n - 1).bit_length() - 1
        upper = 1 << (n - 1).bit_length()
        return lower if (n - lower) < (upper - n) else upper

    for img in bpy.data.images:
        if img.name in ["Render Result", "Viewer Node"]:
            continue

        w, h = img.size[0], img.size[1]
        if w <= max_size and h <= max_size:
            if not force_pot:
                continue
            if (w & (w - 1) == 0) and (h & (h - 1) == 0):
                continue  # Already POT

        # Calculate new size maintaining aspect ratio
        if w > h:
            new_w = min(max_size, w)
            new_h = int(h * (new_w / w))
        else:
            new_h = min(max_size, h)
            new_w = int(w * (new_h / h))

        if force_pot:
            new_w = nearest_pot(new_w)
            new_h = nearest_pot(new_h)
            while new_w > max_size:
                new_w //= 2
            while new_h > max_size:
                new_h //= 2
        else:
            new_w = new_w if new_w % 2 == 0 else new_w + 1
            new_h = new_h if new_h % 2 == 0 else new_h + 1

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
