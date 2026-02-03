"""Constants and thresholds for GLB optimization."""

from pathlib import Path
from typing import TypedDict

# Bloat detection thresholds for web mascots
BLOAT_THRESHOLDS: dict[str, int] = {
    "prop_warning": 1000,  # Non-skinned mesh > this = warning
    "prop_critical": 2000,  # Non-skinned mesh > this = critical
    "repetitive_islands": 10,  # More islands than this...
    "repetitive_verts": 50,  # ...with more verts each = repetitive detail
    "scene_total": 15000,  # Total scene verts for web
}


class OptimizationConfig(TypedDict):
    """Configuration for GLB optimization."""

    output_path: Path | None
    use_draco: bool
    use_webp: bool
    max_texture_size: int
    force_pot_textures: bool
    analyze_animations: bool
    check_bloat: bool
    experimental_autofix: bool
    quiet: bool


# Default configuration for optimization
DEFAULT_CONFIG: OptimizationConfig = {
    "output_path": None,  # None = auto (same folder as input)
    "use_draco": True,  # Mesh compression
    "use_webp": True,  # WebP textures (smaller than PNG)
    "max_texture_size": 1024,  # Resize textures (0 = no resize)
    "force_pot_textures": False,  # Force power-of-two dimensions
    "analyze_animations": True,  # Find static bones (slow but saves MB)
    "check_bloat": True,  # Detect unreasonable mesh complexity
    "experimental_autofix": False,  # [EXPERIMENTAL] Auto-decimate props
    "quiet": True,  # Minimize console output
}
