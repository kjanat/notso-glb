"GLB/glTF import and export functions."

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

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
from notso_glb.utils.logging import (
    StepTimer,
    bold,
    bright_cyan,
    bright_green,
    bright_red,
    bright_yellow,
    cyan,
    dim,
    format_bytes,
    format_duration,
    green,
    log_detail,
    log_error,
    log_info,
    log_ok,
    log_warn,
    magenta,
    print_header,
    timed,
    yellow,
)


@dataclass
class ExportConfig:
    """Configuration for GLB export and optimization."""

    output_path: Path | None = None
    export_format: str = "GLB"
    use_draco: bool = True
    use_webp: bool = True
    max_texture_size: int = 1024
    force_pot_textures: bool = False
    analyze_animations: bool = True
    check_bloat: bool = True
    experimental_autofix: bool = False
    quiet: bool = False


def import_gltf(filepath: str, quiet: bool = False) -> None:
    """Import GLB/glTF file into Blender scene (standalone, no step timing)."""
    _do_import_gltf(filepath, quiet=quiet, step=None)


def _do_import_gltf(
    filepath: str, quiet: bool = False, step: StepTimer | None = None
) -> None:
    """Import GLB/glTF file into Blender scene.

    Args:
        filepath: Path to GLB/glTF file
        quiet: Suppress verbose Blender output
        step: Optional StepTimer for progress tracking
    """
    from notso_glb.utils.logging import filter_blender_output

    with timed("Clearing scene", print_on_exit=False):
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".glb", ".gltf"):
        raise ValueError(f"Unsupported format: {ext}")

    # Log level: 0=all, 10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR, 50=CRITICAL
    log_level = 30 if quiet else 0  # WARNING level when quiet

    if step:
        step.step("Importing into Blender...")
        log_detail(dim(os.path.basename(filepath)))
    else:
        log_info(f"Importing {cyan(os.path.basename(filepath))}...")

    if quiet:
        with filter_blender_output():
            with timed("glTF import", print_on_exit=False) as t:
                bpy.ops.import_scene.gltf(filepath=filepath, loglevel=log_level)
    else:
        with timed("glTF import") as t:
            bpy.ops.import_scene.gltf(filepath=filepath, loglevel=log_level)

    msg = f"Imported in {bright_cyan(format_duration(t.elapsed))}"
    if step:
        log_detail(msg)
    else:
        log_ok(msg)


def _analyze_bloat(step: StepTimer, config: ExportConfig) -> None:
    """Analyze and optionally fix mesh bloat."""
    if not config.check_bloat:
        step.step("Skipping bloat check")
        log_detail(dim("--skip-bloat-check flag set"))
        return

    step.step("Analyzing mesh complexity...")

    with timed("Bloat analysis", print_on_exit=False) as t:
        bloat_warnings = analyze_mesh_bloat()

    if not bloat_warnings:
        log_detail(
            f"{green('No bloat issues detected')} {dim(f'({format_duration(t.elapsed)})')}"
        )
        return

    critical_count = sum(1 for w in bloat_warnings if w["severity"] == "CRITICAL")
    warning_count = sum(1 for w in bloat_warnings if w["severity"] == "WARNING")

    # Print warning box
    border = "!" * 60
    if critical_count > 0:
        print(f"\n{bright_red(border)}")
        print(
            f"  {bright_red('BLOAT WARNINGS')}: {bright_red(str(critical_count))} critical, {yellow(str(warning_count))} warnings"
        )
    else:
        print(f"\n{bright_yellow(border)}")
        print(
            f"  {bright_yellow('BLOAT WARNINGS')}: {yellow(str(warning_count))} warnings"
        )
    print(f"{bright_yellow(border) if critical_count == 0 else bright_red(border)}")

    for w in bloat_warnings:
        if w["severity"] == "CRITICAL":
            icon = bright_red("!!!")
            obj_str = bright_red(f"[{w['issue']}]") + f" {w['object']}"
        else:
            icon = yellow(" ! ")
            obj_str = yellow(f"[{w['issue']}]") + f" {w['object']}"
        print(f"  {icon} {obj_str}")
        print(f"        {dim(str(w['detail']))}")
        print(f"        {dim('->')} {w['suggestion']}")

    print(f"{bright_yellow(border) if critical_count == 0 else bright_red(border)}")

    if config.experimental_autofix:
        _run_bloat_autofix(bloat_warnings)
    else:
        print(
            f"  {dim('Fix these in Blender before export for optimal web delivery.')}"
        )
        print(f"  {dim('Or use')} {cyan('--autofix')} {dim('to auto-decimate props.')}")

    print(f"{bright_yellow(border) if critical_count == 0 else bright_red(border)}\n")


def _run_bloat_autofix(bloat_warnings: list[dict]) -> None:
    """Run experimental autofix for bloat warnings."""
    print(f"\n  {magenta('[EXPERIMENTAL]')} Running auto-fix pipeline...")

    with timed("Auto-fix pipeline", print_on_exit=False) as t:
        results = auto_fix_bloat(bloat_warnings)

    if results["cleanup"]:
        print(f"\n  {cyan('Phase 1: BMesh Cleanup')}")
        total_saved = 0
        for c in results["cleanup"]:
            details = []
            if c["doubles"]:
                details.append(f"{c['doubles']} doubles")
            if c["degenerate"]:
                details.append(f"{c['degenerate']} degenerate")
            if c["loose"]:
                details.append(f"{c['loose']} loose")
            verts_saved = c["verts_saved"]
            saved_int = int(verts_saved) if isinstance(verts_saved, (int, float)) else 0
            total_saved += saved_int
            print(
                f"    {c['object']}: {', '.join(details)} ({bright_green(f'-{saved_int}')} verts)"
            )
        print(
            f"  {bold('Cleanup total')}: {bright_green(f'{total_saved:,}')} verts removed"
        )
    else:
        print(f"\n  {cyan('Phase 1')}: {dim('No cleanup needed')}")

    if results["decimation"]:
        print(f"\n  {cyan('Phase 2: Decimation')}")
        for fix in results["decimation"]:
            reduction_str = bright_green(f"-{fix['reduction']:.0f}%")
            print(
                f"    {fix['object']}: "
                f"{fix['original']:,} -> {fix['new']:,} verts "
                f"({reduction_str})"
            )
        print(f"  {bold('Decimated')} {len(results['decimation'])} mesh(es)")
    else:
        print(f"\n  {cyan('Phase 2')}: {dim('No decimation needed')}")

    print(f"  {dim(f'Auto-fix completed in {format_duration(t.elapsed)}')}")


def _check_duplicates(step: StepTimer, config: ExportConfig) -> None:
    """Check for and optionally fix duplicate names."""
    step.step("Checking for duplicate names...")

    with timed("Duplicate name check", print_on_exit=False) as t:
        duplicates = analyze_duplicate_names()

    if not duplicates:
        log_detail(
            f"{green('No duplicate names found')} {dim(f'({format_duration(t.elapsed)})')}"
        )
        return

    border = "#" * 60
    print(f"\n{yellow(border)}")
    print(f"  {yellow('DUPLICATE NAME WARNINGS')}: {len(duplicates)} found")
    print(f"{yellow(border)}")

    for dup in duplicates:
        issue = dup.get("issue", "DUPLICATE")
        if issue == "SANITIZATION_COLLISION":
            print(f"  [{dup['type']}] {bright_yellow('COLLISION')}: {dup['name']}")
        else:
            print(f"  [{dup['type']}] '{dup['name']}' x{dup['count']}")

    if config.experimental_autofix:
        print(f"\n  {magenta('[EXPERIMENTAL]')} Auto-fixing duplicate names...")
        with timed("Rename duplicates", print_on_exit=False) as t2:
            renames = auto_fix_duplicate_names(duplicates)
        for r in renames:
            print(f"    [{r['type']}] {r['old']} -> {green(r['new'])}")
        if renames:
            print(
                f"  {bold('Renamed')} {len(renames)} item(s) {dim(f'({format_duration(t2.elapsed)})')}"
            )
        else:
            log_detail(dim("No renames needed"))
    else:
        print(
            f"\n  {dim('These will cause JS identifier collisions in generated components.')}"
        )
        print(
            f"  {dim('Fix in Blender or use')} {cyan('--autofix')} {dim('to auto-rename.')}"
        )

    print(f"{yellow(border)}\n")


def _check_skinned_meshes(step: StepTimer) -> None:
    """Check skinned mesh hierarchy."""
    step.step("Checking skinned mesh hierarchy...")

    with timed("Skinned mesh check", print_on_exit=False) as t:
        skinned_warnings = analyze_skinned_mesh_parents()

    if not skinned_warnings:
        log_detail(
            f"{green('All skinned meshes OK')} {dim(f'({format_duration(t.elapsed)})')}"
        )
        return

    critical = [w for w in skinned_warnings if w["severity"] == "CRITICAL"]
    info_only = [w for w in skinned_warnings if w["severity"] != "CRITICAL"]

    border = "~" * 60
    print(f"\n{cyan(border)}")
    print(
        f"  {cyan('SKINNED MESH WARNINGS')}: "
        f"{bright_red(str(len(critical)))} critical, "
        f"{dim(str(len(info_only)))} info"
    )
    print(f"{cyan(border)}")
    print(f"  {dim('(Parent transforms do not affect skinned meshes in glTF)')}")

    # Group by parent
    by_parent: dict[str, list[dict]] = {}
    for w in skinned_warnings:
        parent = str(w["parent"])
        if parent not in by_parent:
            by_parent[parent] = []
        by_parent[parent].append(w)

    # Display grouped by parent in columns
    col_width = 20
    num_cols = 3

    for parent, items in sorted(by_parent.items()):
        # Check if any in this group are critical
        has_critical = any(w["severity"] == "CRITICAL" for w in items)
        parent_color = bright_red if has_critical else dim
        print(f"\n  parent: {parent_color(parent)} ({len(items)})")

        # Sort items by mesh name
        sorted_items = sorted(items, key=lambda w: str(w["mesh"]))

        # Build display items with icons
        display_items: list[str] = []
        for w in sorted_items:
            mesh_name = str(w["mesh"])
            if w["severity"] == "CRITICAL":
                icon = bright_red("!!!")
                name = bright_red(mesh_name[: col_width - 5])
            elif w["has_transform"]:
                icon = yellow(" ! ")
                name = yellow(mesh_name[: col_width - 5])
            else:
                icon = dim(" i ")
                name = mesh_name[: col_width - 5]
            display_items.append(f"{icon} {name:<{col_width - 5}}")

        # Print in columns
        for i in range(0, len(display_items), num_cols):
            row = display_items[i : i + num_cols]
            print(f"    {''.join(row)}")

    print(f"{cyan(border)}")
    print(f"  {dim('To fix: Apply parent transforms or reparent to scene root')}")
    print("")


def _check_uv_maps(step: StepTimer, config: ExportConfig) -> None:
    """Check for and optionally remove unused UV maps."""
    step.step("Checking for unused UV maps...")

    with timed("UV map check", print_on_exit=False) as t:
        unused_uv_warnings = analyze_unused_uv_maps()

    if not unused_uv_warnings:
        log_detail(
            f"{green('No unused UV maps found')} {dim(f'({format_duration(t.elapsed)})')}"
        )
        return

    total_unused = sum(
        len(cast(list[str], w["unused_uvs"])) for w in unused_uv_warnings
    )

    border = "-" * 60
    print(f"\n{dim(border)}")
    print(
        f"  {yellow('UNUSED UV MAPS')}: {total_unused} found in {len(unused_uv_warnings)} mesh(es)"
    )
    print(f"{dim(border)}")

    for w in unused_uv_warnings:
        unused_uvs = cast(list[str], w["unused_uvs"])
        total_uvs = cast(int, w["total_uvs"])
        print(
            f"  {w['mesh']}: {yellow(str(unused_uvs))} {dim(f'(keeping {total_uvs - len(unused_uvs)})')}"
        )

    if config.experimental_autofix:
        print(f"\n  {magenta('[EXPERIMENTAL]')} Removing unused UV maps...")
        with timed("Remove UVs", print_on_exit=False) as t2:
            removed = remove_unused_uv_maps(unused_uv_warnings)
        print(
            f"  {bold('Removed')} {bright_green(str(removed))} unused UV map(s) {dim(f'({format_duration(t2.elapsed)})')}"
        )
    else:
        print(f"\n  {dim('These cause UNUSED_OBJECT warnings in glTF validation.')}")
        print(f"  {dim('Use')} {cyan('--autofix')} {dim('to auto-remove them.')}")

    print(f"{dim(border)}\n")


def _clean_and_optimize(step: StepTimer, config: ExportConfig) -> None:
    """Run cleaning and optimization steps."""
    # Clean bone shapes
    step.step("Cleaning bone shape objects...")
    with timed("Delete bone shapes", print_on_exit=False) as t:
        deleted = delete_bone_shape_objects()
    log_detail(
        f"Deleted {bright_cyan(str(deleted))} objects {dim(f'({format_duration(t.elapsed)})')}"
    )

    # Clean vertex groups
    step.step("Cleaning unused vertex groups...")
    with timed("Clean vertex groups", print_on_exit=False) as t:
        removed_vg = clean_vertex_groups()
    log_detail(
        f"Removed {bright_cyan(f'{removed_vg:,}')} empty vertex groups {dim(f'({format_duration(t.elapsed)})')}"
    )

    # Analyze and mark static bones
    if config.analyze_animations:
        step.step("Analyzing bone animations...")
        with timed("Bone animation analysis") as t:
            static_bones = analyze_bone_animation()
        with timed("Mark non-deform bones", print_on_exit=False) as t2:
            marked, skipped = mark_static_bones_non_deform(static_bones)
        log_detail(f"Found {cyan(str(len(static_bones)))} static bones")
        log_detail(
            f"Marked {bright_green(str(marked))} as non-deform, kept {yellow(str(skipped))} for skinning {dim(f'({format_duration(t2.elapsed)})')}"
        )
    else:
        step.step("Skipping animation analysis")
        log_detail(dim("--skip-animation-analysis flag set"))

    # Resize textures
    if config.max_texture_size > 0 or config.force_pot_textures:
        pot_msg = f" {magenta('(forcing POT)')}" if config.force_pot_textures else ""
        step.step(f"Resizing textures > {config.max_texture_size}px{pot_msg}")
        with timed("Texture resize", print_on_exit=False) as t:
            resized = resize_textures(
                config.max_texture_size, force_pot=config.force_pot_textures
            )
        if resized > 0:
            log_detail(
                f"Resized {bright_cyan(str(resized))} textures {dim(f'({format_duration(t.elapsed)})')}"
            )
        else:
            log_detail(
                f"{green('No textures needed resizing')} {dim(f'({format_duration(t.elapsed)})')}"
            )
    else:
        step.step("Skipping texture resize")
        log_detail(dim("max_texture_size=0"))


def _do_export(output_path: str, config: ExportConfig, use_draco: bool) -> None:
    """Execute the actual glTF export call."""
    export_params: dict[str, Any] = {
        "filepath": output_path,
        "export_format": config.export_format,
        # Bones: deform only
        "export_def_bones": True,
        "export_hierarchy_flatten_bones": False,
        "export_leaf_bone": False,
        # Animation optimization
        "export_animations": True,
        "export_nla_strips": True,
        "export_optimize_animation_size": True,
        "export_optimize_animation_keep_anim_armature": True,
        "export_force_sampling": True,
        "export_frame_step": 1,
        "export_skins": True,
        # Mesh compression (Draco)
        "export_draco_mesh_compression_enable": use_draco,
        "export_draco_mesh_compression_level": 6,
        "export_draco_position_quantization": 14,
        "export_draco_normal_quantization": 10,
        "export_draco_texcoord_quantization": 12,
        # Textures
        "export_image_format": "WEBP" if config.use_webp else "AUTO",
        # Standard settings
        "export_yup": True,
        "export_texcoords": True,
        "export_normals": True,
        "export_materials": "EXPORT",
        "export_shared_accessors": True,
    }

    # Blender 5.0+ requires export_loglevel for proper logging initialization
    # The addon only sets internal 'loglevel' when export_loglevel < 0
    if bpy.app.version >= (5, 0, 0):
        export_params["export_loglevel"] = -1

    bpy.ops.export_scene.gltf(**export_params)  # pyright: ignore[reportCallIssue]


def _try_export(output_path: str, config: ExportConfig, use_draco: bool) -> str | None:
    """Single export attempt. Returns path on success, None on failure."""
    from notso_glb.utils.logging import filter_blender_output, log_error

    try:
        if config.quiet:
            with filter_blender_output():
                _do_export(output_path, config, use_draco)
        else:
            _do_export(output_path, config, use_draco)
        return output_path
    except Exception as e:
        log_error(f"Export exception: {e}")
        return None


def _export_file(step: StepTimer, config: ExportConfig) -> str | None:
    """Export with automatic Draco fallback on encoder crash."""
    output_path_str: str
    if config.output_path is None:
        blend_path = bpy.data.filepath
        if blend_path:
            base = os.path.splitext(blend_path)[0]
            output_path_str = f"{base}_optimized.glb"
        else:
            output_path_str = os.path.join(os.getcwd(), "optimized_export.glb")
    else:
        output_path_str = str(config.output_path)

    output_path_str = bpy.path.abspath(output_path_str)
    ext = "GLB" if config.export_format == "GLB" else "glTF"
    step.step(f"Exporting {ext}...")
    log_detail(dim(output_path_str))

    draco_str = bright_green("ON") if config.use_draco else dim("OFF")
    webp_str = bright_green("ON") if config.use_webp else dim("OFF")
    log_detail(
        f"Format: {cyan(config.export_format)}, Draco: {draco_str}, WebP: {webp_str}"
    )

    if config.use_draco:
        log_detail(f"{dim('Attempting export with Draco compression...')}")
        with timed("glTF export (Draco)", print_on_exit=False) as t:
            result = _try_export(output_path_str, config, use_draco=True)
        if result:
            log_detail(
                f"{bright_green('Export successful')} {dim(f'({format_duration(t.elapsed)})')}"
            )
            return result

        # Draco crashed - fallback
        log_warn("Draco encoder crashed, retrying without compression...")
        with timed("glTF export (no Draco)", print_on_exit=False) as t:
            result = _try_export(output_path_str, config, use_draco=False)
        if result:
            log_ok(f"Exported without Draco {dim(f'({format_duration(t.elapsed)})')}")
            return result

        log_error("Export failed")
        return None

    with timed("glTF export", print_on_exit=False) as t:
        result = _try_export(output_path_str, config, use_draco=False)
    if result:
        log_detail(
            f"{bright_green('Export successful')} {dim(f'({format_duration(t.elapsed)})')}"
        )
    else:
        log_error("Export failed")
    return result


def optimize_and_export(
    output_path: Path | None = None,
    export_format: str = "GLB",
    use_draco: bool = True,
    use_webp: bool = True,
    max_texture_size: int = 1024,
    force_pot_textures: bool = False,
    analyze_animations: bool = True,
    check_bloat: bool = True,
    experimental_autofix: bool = False,
    quiet: bool = False,
    input_path: str | None = None,
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
        quiet: Suppress Blender's verbose output (show only warnings/errors)
        input_path: Path to GLB/glTF file to import (if None, uses current scene)
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
        quiet=quiet,
    )

    # 10 steps if no import, 11 if importing
    total_steps = 11 if input_path else 10
    step = StepTimer(total_steps=total_steps)

    # Header
    print_header("GLB EXPORT OPTIMIZER")

    # Import if path provided
    if input_path:
        _do_import_gltf(input_path, quiet=quiet, step=step)

    # Show before stats
    stats = get_scene_stats()
    verts_str = f"{stats['vertices']:,}"
    print(
        f"\n  Scene: {cyan(str(stats['meshes']))} meshes, "
        f"{cyan(verts_str)} verts, "
        f"{cyan(str(stats['bones']))} bones, "
        f"{cyan(str(stats['actions']))} animations"
    )

    _analyze_bloat(step, config)
    _check_duplicates(step, config)
    _check_skinned_meshes(step)
    _check_uv_maps(step, config)
    _clean_and_optimize(step, config)

    result_path = _export_file(step, config)

    # Finalize timing
    step.finish()

    # Report results based on success/failure
    if result_path and os.path.exists(result_path):
        step.final_message("Export complete!", success=True)
        size = os.path.getsize(result_path)
        print(f"\n{cyan('=' * 60)}")
        print(f"  {bold('OUTPUT')}: {bright_green(os.path.basename(result_path))}")
        print(f"  {bold('SIZE')}:   {bright_cyan(format_bytes(size))} ({size:,} bytes)")
        print(
            f"  {bold('TIME')}:   {bright_cyan(format_duration(step.total_elapsed()))}"
        )
        print(f"{cyan('=' * 60)}")

        # Print timing summary
        step.print_summary()

        return result_path
    else:
        step.final_message("Export FAILED", success=False)
        if result_path:  # Path was determined but file missing?
            log_warn("Output file not found at expected path")
        return None
