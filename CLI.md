# notso-glb

Optimize and export 3D models for the web.

**Usage**:

```bash
notso-glb [OPTIONS] FILE
```

**Arguments**:

* `FILE`: Input file (.blend, .glb, or .gltf)  \[required\]

**Options**:

* `-o, --output PATH`: Output path (default: input_optimized.\[glb|gltf\])
* `-f, --format [glb|gltf|gltf-embedded]`: Output format  \[default: glb\]
* `--draco / --no-draco`: Enable/Disable Draco compression  \[default: draco\]
* `--webp / --no-webp`: Enable/Disable WebP textures  \[default: webp\]
* `--max-texture-size PIXELS`: Max texture size (0=no resize)  \[default: 1024\]
* `--force-pot`: Force power-of-two texture dimensions (better GPU compatibility)
* `--analyze-animations / --skip-animation-analysis`: Analyze bones for static/animated properties  \[default: analyze-animations\]
* `--check-bloat / --skip-bloat-check`: Analyze meshes for unreasonable complexity  \[default: check-bloat\]
* `--autofix / --stable`: Auto-decimate bloated props, remove unused UVs  \[default: stable\]
* `--gltfpack / --no-gltfpack`: Post-process with gltfpack for extra compression  \[default: gltfpack\]
* `-q, --quiet / -v, --verbose`: Suppress Blender's verbose output (show only warnings/errors)  \[default: quiet\]
* `-V, --version`: Show the version and exit.
* `--help`: Show this message and exit.
