# GLB Export Optimizer for Mascot Models

> Cleans up Blender files and exports optimized GLB for web delivery.

```bash
uvx notso-glb [OPTIONS] FILE
```

<p align="center">
  <a href="https://github.com/kjanat/notso-glb/blob/master/CLI.md" target="_blank" rel="noopener" title="View CLI Options">
    <img alt="Screenshot with cli options" width="100%" src="https://raw.githubusercontent.com/kjanat/notso-glb/refs/heads/master/screenshot.webp">
  </a>
</p>

<p align="center">
  <a href="https://pypi.org/project/notso-glb/"><img src="https://img.shields.io/pypi/v/notso-glb" alt="PyPI"></a>
  <a href="https://pypi.org/project/notso-glb/"><img src="https://img.shields.io/pypi/dm/notso-glb" alt="Downloads"></a>  <!--<a href="https://github.com/kjanat/notso-glb/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/kjanat/notso-glb/ci.yml?branch=master" alt="CI"></a>-->
  <a href="https://github.com/kjanat/notso-glb/blob/master/LICENSE"><img src="https://img.shields.io/github/license/kjanat/notso-glb" alt="License"></a>  <!--<a href="https://notso-glb.kjanat.com"><img src="https://img.shields.io/badge/docs-mkdocs-blue" alt="Docs"></a>-->
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11">
</p>

## Install

```bash
uv tool install notso-glb
```

```bash
# Or install directly from GitHub:
uv tool install -p3.11 git+https://github.com/kjanat/notso-glb
```

then just run `notso-glb` from the command line.

### Upgrade

```bash
uv tool upgrade notso-glb
```

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

Experimental Auto-fix (`--autofix`):

- BMesh cleanup (remove doubles, degenerate geometry, loose verts)
- Decimate bloated props to ~1600 verts
- Auto-rename duplicate objects/meshes/materials/actions (using pointer ID)
- Remove unused UV maps

## Usage

See [CLI.md]

## Requirements

- Blender 5.0+
- Python 3.11 (same as bundled with Blender)
- uv (optional, for easy install/upgrade)
- gltfpack (optional, for extra compression - WASM fallback included)

## Development Setup

For local development, download the gltfpack WASM binary:

```bash
# Download latest WASM from npm
uv run scripts/update_wasm.py

# Or check current version
uv run scripts/update_wasm.py --show-version

# Download specific version
uv run scripts/update_wasm.py --version 1.0.0
```

The WASM binary (`src/notso_glb/wasm/gltfpack.wasm`) is not committed to git and
must be downloaded locally. CI/CD pipelines handle this automatically.

## Useful Links

- [glTF 2.0 Specification]
- [glTF 2.0 API Reference Guide]
- [Khronos Resources]
- [Blender 5.0 glTF 2.0]
- [Blender 5.0 Python API Documentation]
- [Blender 5.0 Reference Manual]

## License

This project is licensed under the GNU General Public License v3.0 - see the
[LICENSE] file for details.

This project uses [Blender] as a Python module (bpy), which is also GPL-3.0
licensed.

[Khronos Resources]: https://github.khronos.org/
[glTF 2.0 Specification]: https://www.khronos.org/gltf/#gltf-spec
[glTF 2.0 API Reference Guide]: https://www.khronos.org/files/gltf20-reference-guide.pdf
[Blender 5.0 Reference Manual]: https://docs.blender.org/manual/en/latest
[Blender 5.0 glTF 2.0]: https://docs.blender.org/manual/en/5.0/addons/import_export/scene_gltf2.html
[Blender 5.0 Python API Documentation]: https://docs.blender.org/api/current/index.html
[Blender]: https://www.blender.org/
[CLI.md]: https://github.com/kjanat/notso-glb/blob/master/CLI.md
[LICENSE]: https://github.com/kjanat/notso-glb/blob/master/LICENSE

<!-- markdownlint-disable-file MD033 -->
