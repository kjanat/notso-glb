"""
GLB Export Optimizer for Mascot Models
======================================
Cleans up Blender files and exports optimized GLB for web delivery.

Optimizations:
- Detects bloated props (high-vert non-skinned meshes, repetitive geometry)
- Detects skinned meshes with non-root parents (glTF spec issue)
- Detects unused UV maps (TEXCOORD bloat)
- Detects duplicate names and sanitization collisions
- Removes unused vertex groups (bone weight bloat)
- Marks static bones as non-deform (animation bloat)
- Removes bone shape objects (Icosphere artifacts)
- Resizes textures to max 1024px (optional POT enforcement)
- Exports with Draco mesh compression
- Exports with WebP textures

Usage:
    CLI:
        notso-glb model.glb -o output.glb
        notso-glb model.blend --format gltf-embedded
        notso-glb model.gltf --no-draco --max-texture 2048

    Python:
        from notso_glb import main
        main()
"""

from importlib.metadata import PackageNotFoundError, version

from notso_glb.cli import main

try:
    __version__ = version("notso-glb")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["main"]
