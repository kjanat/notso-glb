"""Naming and string utility functions."""

import re


def sanitize_gltf_name(name: str) -> str:
    """
    Simulate how glTF export sanitizes names for JS identifiers.
    Dots, spaces, dashes become underscores. Leading digits get prefix.
    """
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized


def nearest_power_of_two(n: int) -> int:
    """Round to nearest power of two."""
    if n <= 1:
        return 1
    bit_len = (n - 1).bit_length()
    lower = 1 << (bit_len - 1)
    upper = 1 << bit_len
    return lower if (n - lower) < (upper - n) else upper
