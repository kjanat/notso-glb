# GLB Export Optimizer for Mascot Models

> Cleans up Blender files and exports optimized GLB for web delivery.

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

Bloat Detection:

- CRITICAL: Props >2000 verts, repetitive detail (many islands with high verts)
- WARNING: Props >1000 verts, scene total >15000 verts, non-root skinned meshes

Experimental Auto-fix (--experimental-autofix):

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
    --experimental-autofix      Auto-fix bloated props, unused UVs, duplicates
```

## Requirements

- Blender 5.0+
- Python 3.10+ (bundled with Blender)
