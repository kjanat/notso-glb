"GLB/glTF import and export functions."

import os
from dataclasses import dataclass
from typing import cast

import bpy  # type: ignore[import-untyped]

from notso_glb.analyzers import (
    analyze_bone_animation,
    analyze_duplicate_names,
    analyze_mesh_bloat,
    analyze_skinned_mesh_parents,
    analyze_unused_uv_maps,
)
from notso_glb.cleaners import (
    auto_fix_bloat,
    auto_fix_duplicate_names,
    clean_vertex_groups,
    delete_bone_shape_objects,
    mark_static_bones_non_deform,
    remove_unused_uv_maps,
    resize_textures,
)
from notso_glb.utils import get_scene_stats


@dataclass
class ExportConfig:
    """Configuration for GLB export and optimization."""

    output_path: str | None = None
    export_format: str = "GLB"
    use_draco: bool = True
    use_webp: bool = True
    max_texture_size: int = 1024
    force_pot_textures: bool = False
    analyze_animations: bool = True
    check_bloat: bool = True
    experimental_autofix: bool = False


class StepCounter:
    """Auto-incrementing step counter for progress display."""

    def __init__(self, total: int) -> None:
        self.current = 0
        self.total = total

    def step(self, message: str) -> None:
        """Print step with auto-incremented counter."""
        self.current += 1
        print(f"\n[{self.current}/{self.total}] {message}")


def import_gltf(filepath: str) -> None:
    """Import GLB/glTF file into Blender scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".glb", ".gltf"):
        raise ValueError(f"Unsupported format: {ext}")

    bpy.ops.import_scene.gltf(filepath=filepath)
    print(f"Imported: {filepath}")


def _analyze_bloat(step: StepCounter, config: ExportConfig) -> None:
    """Analyze and optionally fix mesh bloat."""
    if not config.check_bloat:
        step.step("Skipping bloat check")
        return

    step.step("Analyzing mesh complexity...")
    bloat_warnings = analyze_mesh_bloat()

    if not bloat_warnings:
        print("      No bloat issues detected")
        return

    critical_count = sum(1 for w in bloat_warnings if w["severity"] == "CRITICAL")
    warning_count = sum(1 for w in bloat_warnings if w["severity"] == "WARNING")

    print(f"\n{'!' * 60}")
    print(f"  BLOAT WARNINGS: {critical_count} critical, {warning_count} warnings")
    print(f"{'!' * 60}")

    for w in bloat_warnings:
        icon = "!!!" if w["severity"] == "CRITICAL" else " ! "
        print(f"  {icon} [{w['issue']}] {w['object']}")
        print(f"        {w['detail']}")
        print(f"        -> {w['suggestion']}")

    print(f"{'!' * 60}")

    if config.experimental_autofix:
        _run_bloat_autofix(bloat_warnings)
    else:
        print("  Fix these in Blender before export for optimal web delivery.")
        print("  Or use --experimental-autofix to auto-decimate props.")

    print(f"{'!' * 60}\n")


def _run_bloat_autofix(bloat_warnings: list[dict]) -> None:
    """Run experimental autofix for bloat warnings."""
    print("\n  [EXPERIMENTAL] Running auto-fix pipeline...")
    results = auto_fix_bloat(bloat_warnings)

    if results["cleanup"]:
        print("\n  Phase 1: BMesh Cleanup")
        total_saved = 0
        for c in results["cleanup"]:
            details = []
            if c["doubles"]:
                details.append(f"{c['doubles']} doubles")
            if c["degenerate"]:
                details.append(f"{c['degenerate']} degenerate")
            if c["loose"]:
                details.append(f"{c['loose']} loose")
            print(
                f"    {c['object']}: {', '.join(details)} (-{c['verts_saved']} verts)"
            )
            verts_saved = c["verts_saved"]
            total_saved += (
                int(verts_saved) if isinstance(verts_saved, (int, float)) else 0
            )
        print(f"  Cleanup total: {total_saved:,} verts removed")
    else:
        print("\n  Phase 1: No cleanup needed")

    if results["decimation"]:
        print("\n  Phase 2: Decimation")
        for fix in results["decimation"]:
            print(
                f"    {fix['object']}: "
                f"{fix['original']:,} -> {fix['new']:,} verts "
                f"(-{fix['reduction']:.0f}%)"
            )
        print(f"  Decimated {len(results['decimation'])} mesh(es)")
    else:
        print("\n  Phase 2: No decimation needed")
    print("")


def _check_duplicates(step: StepCounter, config: ExportConfig) -> None:
    """Check for and optionally fix duplicate names."""
    step.step("Checking for duplicate names...")
    duplicates = analyze_duplicate_names()

    if not duplicates:
        print("      No duplicate names found")
        return

    print(f"\n{'#' * 60}")
    print(f"  DUPLICATE NAME WARNINGS: {len(duplicates)} found")
    print(f"{'#' * 60}")

    for dup in duplicates:
        issue = dup.get("issue", "DUPLICATE")
        if issue == "SANITIZATION_COLLISION":
            print(f"  [{dup['type']}] COLLISION: {dup['name']}")
        else:
            print(f"  [{dup['type']}] '{dup['name']}' x{dup['count']}")

    if config.experimental_autofix:
        print("\n  [EXPERIMENTAL] Auto-fixing duplicate names...")
        renames = auto_fix_duplicate_names(duplicates)
        for r in renames:
            print(f"    [{r['type']}] {r['old']} -> {r['new']}")
        if renames:
            print(f"  Renamed {len(renames)} item(s)")
        else:
            print("  No renames needed")
    else:
        print("\n  These will cause JS identifier collisions in generated components.")
        print("  Fix in Blender or use --experimental-autofix to auto-rename.")

    print(f"{'#' * 60}\n")


def _check_skinned_meshes(step: StepCounter) -> None:
    """Check skinned mesh hierarchy."""
    step.step("Checking skinned mesh hierarchy...")
    skinned_warnings = analyze_skinned_mesh_parents()

    if not skinned_warnings:
        print("      All skinned meshes at root or have identity-transform parents")
        return

    critical = [w for w in skinned_warnings if w["severity"] == "CRITICAL"]
    warning_only = [w for w in skinned_warnings if w["severity"] == "WARNING"]

    print(f"\n{'~' * 60}")
    print(
        f"  SKINNED MESH WARNINGS: {len(critical)} critical, {len(warning_only)} info"
    )
    print(f"{'~' * 60}")
    print("  (Parent transforms don't affect skinned meshes in glTF)")

    for w in skinned_warnings:
        icon = "!!!" if w["severity"] == "CRITICAL" else " i "
        transform_note = " (has non-identity transform!)" if w["has_transform"] else ""
        print(f"  {icon} {w['mesh']} -> parent: {w['parent']}{transform_note}")

    print(f"{'~' * 60}")
    print("  To fix: Apply parent transforms or reparent to scene root")
    print("")


def _check_uv_maps(step: StepCounter, config: ExportConfig) -> None:
    """Check for and optionally remove unused UV maps."""
    step.step("Checking for unused UV maps...")
    unused_uv_warnings = analyze_unused_uv_maps()

    if not unused_uv_warnings:
        print("      No unused UV maps found")
        return

    total_unused = sum(
        len(cast(list[str], w["unused_uvs"])) for w in unused_uv_warnings
    )
    print(f"\n{'-' * 60}")
    print(
        f"  UNUSED UV MAPS: {total_unused} found in {len(unused_uv_warnings)} mesh(es)"
    )
    print(f"{'-' * 60}")

    for w in unused_uv_warnings:
        unused_uvs = cast(list[str], w["unused_uvs"])
        total_uvs = cast(int, w["total_uvs"])
        print(f"  {w['mesh']}: {unused_uvs} (keeping {total_uvs - len(unused_uvs)})")

    if config.experimental_autofix:
        print("\n  [EXPERIMENTAL] Removing unused UV maps...")
        removed = remove_unused_uv_maps(unused_uv_warnings)
        print(f"  Removed {removed} unused UV map(s)")
    else:
        print("\n  These cause UNUSED_OBJECT warnings in glTF validation.")
        print("  Use --experimental-autofix to auto-remove them.")

    print(f"{'-' * 60}\n")


def _clean_and_optimize(step: StepCounter, config: ExportConfig) -> None:
    """Run cleaning and optimization steps."""
    # Clean bone shapes
    step.step("Cleaning bone shape objects...")
    deleted = delete_bone_shape_objects()
    print(f"      Deleted {deleted} objects")

    # Clean vertex groups
    step.step("Cleaning unused vertex groups...")
    removed_vg = clean_vertex_groups()
    print(f"      Removed {removed_vg} empty vertex groups")

    # Analyze and mark static bones
    if config.analyze_animations:
        step.step("Analyzing bone animations (may take 1-2 minutes)...")
        static_bones = analyze_bone_animation()
        marked, skipped = mark_static_bones_non_deform(static_bones)
        print(f"      Found {len(static_bones)} static bones")
        print(f"      Marked {marked} as non-deform, kept {skipped} for skinning")
    else:
        step.step("Skipping animation analysis")

    # Resize textures
    if config.max_texture_size > 0 or config.force_pot_textures:
        pot_msg = " (forcing POT)" if config.force_pot_textures else ""
        step.step(f"Resizing textures > {config.max_texture_size}px{pot_msg}...")
        resized = resize_textures(
            config.max_texture_size, force_pot=config.force_pot_textures
        )
        print(f"      Resized {resized} textures")
    else:
        step.step("Skipping texture resize")


def _try_export(output_path: str, config: ExportConfig, use_draco: bool) -> str | None:
    """Single export attempt. Returns path on success, None on failure."""
    try:
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format=config.export_format,
            # Bones: deform only
            export_def_bones=True,
            export_hierarchy_flatten_bones=False,
            export_leaf_bone=False,
            # Animation optimization
            export_animations=True,
            export_nla_strips=True,
            export_optimize_animation_size=True,
            export_optimize_animation_keep_anim_armature=True,
            export_force_sampling=True,
            export_frame_step=1,
            export_skins=True,
            # Mesh compression (Draco)
            export_draco_mesh_compression_enable=use_draco,
            export_draco_mesh_compression_level=6,
            export_draco_position_quantization=14,
            export_draco_normal_quantization=10,
            export_draco_texcoord_quantization=12,
            # Textures
            export_image_format="WEBP" if config.use_webp else "AUTO",
            # Standard settings
            export_yup=True,
            export_texcoords=True,
            export_normals=True,
            export_materials="EXPORT",
            export_shared_accessors=True,
        )
        return output_path
    except Exception:
        return None


def _export_file(step: StepCounter, config: ExportConfig) -> str | None:
    """Export with automatic Draco fallback on encoder crash."""
    output_path = config.output_path
    if output_path is None:
        blend_path = bpy.data.filepath
        if blend_path:
            base = os.path.splitext(blend_path)[0]
            output_path = f"{base}_optimized.glb"
        else:
            output_path = os.path.join(os.getcwd(), "optimized_export.glb")

    output_path = bpy.path.abspath(output_path)
    step.step(f"Exporting to: {output_path}")

    if config.use_draco:
        print(f"      Format: {config.export_format}, Draco: ON, WebP: {config.use_webp}")
        result = _try_export(output_path, config, use_draco=True)
        if result:
            return result

        # Draco crashed - fallback
        print("      [WARN] Draco encoder crashed, retrying without compression...")
        result = _try_export(output_path, config, use_draco=False)
        if result:
            print("      [OK] Exported without Draco")
            return result

        print("      [ERROR] Export failed")
        return None

    print(f"      Format: {config.export_format}, Draco: OFF, WebP: {config.use_webp}")
    result = _try_export(output_path, config, use_draco=False)
    if not result:
        print("      [ERROR] Export failed")
    return result


def optimize_and_export(
    output_path: str | None = None,
    export_format: str = "GLB",
    use_draco: bool = True,
    use_webp: bool = True,
    max_texture_size: int = 1024,
    force_pot_textures: bool = False,
    analyze_animations: bool = True,
    check_bloat: bool = True,
    experimental_autofix: bool = False,
) -> str | None:
    """
    Main optimization and export function.

    Args:
        output_path: Where to save the file (default: next to .blend file)
        export_format: 'GLB', 'GLTF_SEPARATE', or 'GLTF_EMBEDDED'
        use_draco: Enable Draco mesh compression
        use_webp: Export textures as WebP
        max_texture_size: Resize textures larger than this (0 = no resize)
        force_pot_textures: Force power-of-two texture dimensions
        analyze_animations: Analyze bones for static/animated (slow but worth it)
        check_bloat: Analyze meshes for unreasonable complexity
        experimental_autofix: Auto-decimate bloated props (EXPERIMENTAL)
    """
    config = ExportConfig(
        output_path=output_path,
        export_format=export_format,
        use_draco=use_draco,
        use_webp=use_webp,
        max_texture_size=max_texture_size,
        force_pot_textures=force_pot_textures,
        analyze_animations=analyze_animations,
        check_bloat=check_bloat,
        experimental_autofix=experimental_autofix,
    )

    step = StepCounter(total=10)

    print("")
    print("=" * 60)
    print("  GLB EXPORT OPTIMIZER")
    print("=" * 60)

    # Show before stats
    stats = get_scene_stats()
    print(
        f"\nScene: {stats['meshes']} meshes, {stats['vertices']:,} verts, "
        f"{stats['bones']} bones, {stats['actions']} animations"
    )

    _analyze_bloat(step, config)
    _check_duplicates(step, config)
    _check_skinned_meshes(step)
    _check_uv_maps(step, config)
    _clean_and_optimize(step, config)

    result_path = _export_file(step, config)

    # Report results
    step.step("Export complete!")

    if result_path and os.path.exists(result_path):
        size = os.path.getsize(result_path)
        print(f"\n{'=' * 60}")
        print(f"  OUTPUT: {os.path.basename(result_path)}")
        print(f"  SIZE:   {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
        print(f"{'=' * 60}")
        return result_path
    else:
        if result_path:  # Path was determined but file missing?
            print("\n[WARNING] Output file not found at expected path")
        return None
