# GLB Export Optimizer for Mascot Models

> Cleans up Blender files and exports optimized GLB for web delivery.

```sh
uvx --python 3.11 --from git+https://github.com/kjanat/notso-glb.git notso-glb --help
```

<p align="center">
  <img alt="Screenshot with cli options" width="100%" src="https://raw.githubusercontent.com/kjanat/notso-glb/refs/heads/master/screenshot.webp">
</p>

## Features

Optimizations:

- Detects bloated props (high-vert non-skinned meshes, repetitive geometry)
- Detects skinned meshes with non-root parents (glTF spec issue)
- Detects unused UV maps (`TEXCOORD` bloat)
- Detects duplicate names and sanitization collisions
- Removes unused vertex groups (bone weight bloat)
- Marks static bones as non-deform (animation bloat)
- Removes bone shape objects (Icosphere artifacts)
- Resizes textures to max 1024px (optional `POT` enforcement)
- Exports with Draco mesh compression
- Exports with WebP textures

Bloat Detection:

- CRITICAL: Props >2000 verts, repetitive detail (many islands with high verts)
- WARNING: Props >1000 verts, scene total >15000 verts, non-root skinned meshes

Experimental Auto-fix (`--experimental-autofix`):

- BMesh cleanup (remove doubles, degenerate geometry, loose verts)
- Decimate bloated props to ~1600 verts
- Auto-rename duplicate objects/meshes/materials/actions (using pointer ID)
- Remove unused UV maps

## Usage

```text
Blender UI:
    Open in Text Editor and Run Script (uses CONFIG dict below)

Blender CLI with .blend:
    blender model.blend --background --python glb_export_optimizer.py

Blender CLI with .glb/.gltf:
    blender --background --python glb_export_optimizer.py -- model.glb
    blender --background --python glb_export_optimizer.py -- model.glb -o output.glb

Direct CLI execution (with uv):
    ./glb_export_optimizer.py model.glb -o output.glb
    ./glb_export_optimizer.py model.glb --format gltf-embedded # which exports .gltf
    ./glb_export_optimizer.py model.gltf --no-draco --max-texture 2048

CLI options (blender: after --):
    input                       Input file (.blend, .glb, .gltf)
    -o, --output                Output path (default: input_optimized.[glb|gltf])
    -f, --format                Output format: glb (default), gltf, gltf-embedded
    --no-draco                  Disable Draco mesh compression
    --no-webp                   Keep original texture format
    --max-texture N             Max texture dimension in px (default: 1024, 0=no resize)
    --force-pot                 Force power-of-two texture dimensions
    --skip-animation-analysis   Skip static bone detection (faster)
    --skip-bloat-check          Skip mesh complexity analysis
    --autofix                   Auto-fix bloated props, unused UVs, duplicates
```

## Requirements

- Blender 5.0+
- Python 3.11 (bundled with Blender)

## Useful Links

- [glTF 2.0 Specification]
- [glTF 2.0 API Reference Guide]
- [Khronos Resources]
- [Blender 5.0 glTF 2.0]
- [Blender 5.0 Python API Documentation]
- [Blender 5.0 Reference Manual]

[Khronos Resources]: https://github.khronos.org/
[glTF 2.0 Specification]: https://www.khronos.org/gltf/#gltf-spec
[glTF 2.0 API Reference Guide]: https://www.khronos.org/files/gltf20-reference-guide.pdf
[Blender 5.0 Reference Manual]: https://docs.blender.org/manual/en/latest
[Blender 5.0 glTF 2.0]: https://docs.blender.org/manual/en/5.0/addons/import_export/scene_gltf2.html
[Blender 5.0 Python API Documentation]: https://docs.blender.org/api/current/index.html

<!-- markdownlint-disable-file MD033 -->
