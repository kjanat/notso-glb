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

Bloat Detection:
- CRITICAL: Props >2000 verts, repetitive detail (many islands with high verts)
- WARNING: Props >1000 verts, scene total >15000 verts, non-root skinned meshes

Experimental Auto-fix (--experimental-autofix):
- BMesh cleanup (remove doubles, degenerate geometry, loose verts)
- Decimate bloated props to ~1600 verts
- Auto-rename duplicate objects/meshes/materials/actions (using pointer ID)
- Remove unused UV maps

Usage:
    Blender UI:
        Open in Text Editor and Run Script (uses CONFIG dict below)

    CLI with .blend:
        blender model.blend --background --python glb_export_optimizer.py

    CLI with .glb/.gltf:
        blender --background --python glb_export_optimizer.py -- model.glb
        blender --background --python glb_export_optimizer.py -- model.glb -o output.glb

    Direct CLI execution (with uv):
        ./glb_export_optimizer.py model.glb -o output.glb
        ./glb_export_optimizer.py model.glb --format gltf-embedded # which exports .gltf
        ./glb_export_optimizer.py model.gltf --no-draco --max-texture 2048

    CLI options (after --):
        input                 Input file (.blend, .glb, .gltf)
        -o, --output          Output path (default: input_optimized.[glb|gltf])
        -f, --format          Output format: glb (default), gltf, gltf-embedded
        --no-draco            Disable Draco mesh compression
        --no-webp             Keep original texture format
        --max-texture N       Max texture dimension in px (default: 1024, 0=no resize)
        --force-pot           Force power-of-two texture dimensions
        --skip-animation-analysis  Skip static bone detection (faster)
        --skip-bloat-check    Skip mesh complexity analysis
        --experimental-autofix  Auto-fix bloated props, unused UVs, duplicates
"""

import os

from notso_glb._bpy import bpy


def clean_vertex_groups():
    """Remove vertex groups with no weights (empty bone references)"""
    total_removed = 0

    for obj in bpy.data.objects:
        if obj.type != "MESH" or len(obj.vertex_groups) == 0:
            continue

        mesh = obj.data
        used_groups = set()

        for v in mesh.vertices:
            for g in v.groups:
                if g.weight > 0.0001:
                    used_groups.add(g.group)

        unused_names = [
            vg.name for i, vg in enumerate(obj.vertex_groups) if i not in used_groups
        ]

        for name in unused_names:
            vg = obj.vertex_groups.get(name)
            if vg:
                obj.vertex_groups.remove(vg)
                total_removed += 1

    return total_removed


def analyze_bone_animation():
    """Find bones that never animate across all actions"""
    armature = None
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            armature = obj
            break

    if not armature or not armature.animation_data:
        return set()

    bone_movement = {b.name: 0.0 for b in armature.pose.bones}

    orig_action = armature.animation_data.action
    orig_frame = bpy.context.scene.frame_current

    for action in bpy.data.actions:
        armature.animation_data.action = action
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])

        for bone in armature.pose.bones:
            bpy.context.scene.frame_set(frame_start)
            bpy.context.view_layer.update()
            start_loc = bone.location.copy()
            start_rot = (
                bone.rotation_quaternion.copy()
                if bone.rotation_mode == "QUATERNION"
                else bone.rotation_euler.copy()
            )

            bpy.context.scene.frame_set(frame_end)
            bpy.context.view_layer.update()
            end_loc = bone.location.copy()
            end_rot = (
                bone.rotation_quaternion.copy()
                if bone.rotation_mode == "QUATERNION"
                else bone.rotation_euler.copy()
            )

            loc_diff = (end_loc - start_loc).length
            if bone.rotation_mode == "QUATERNION":
                rot_diff = (end_rot - start_rot).magnitude
            else:
                rot_diff = (
                    end_rot.to_quaternion() - start_rot.to_quaternion()
                ).magnitude

            bone_movement[bone.name] += loc_diff + rot_diff

    if orig_action:
        armature.animation_data.action = orig_action
    bpy.context.scene.frame_set(orig_frame)

    return {name for name, movement in bone_movement.items() if movement < 0.01}


def get_bones_used_for_skinning():
    """Find all bones that have vertex weights on skinned meshes"""
    used_bones = set()

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        # Check if mesh is skinned (has armature modifier)
        has_armature = any(mod.type == "ARMATURE" for mod in obj.modifiers)
        if not has_armature:
            continue

        # All vertex groups on skinned meshes are bone references
        for vg in obj.vertex_groups:
            used_bones.add(vg.name)

    return used_bones


def mark_static_bones_non_deform(static_bones):
    """Mark static bones as non-deform, but KEEP bones used for skinning"""
    armature = None
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            armature = obj
            break

    if not armature:
        return 0, 0

    # CRITICAL: Don't mark bones as non-deform if they're weighted to meshes
    skinning_bones = get_bones_used_for_skinning()
    safe_to_mark = static_bones - skinning_bones
    skipped = len(static_bones & skinning_bones)

    marked = 0
    for bone_name in safe_to_mark:
        bone = armature.data.bones.get(bone_name)
        if not bone or not bone.use_deform:
            continue
        bone.use_deform = False
        marked += 1

    return marked, skipped


def delete_bone_shape_objects():
    """Remove objects used as bone custom shapes (Icosphere, etc.)"""
    deleted = 0
    shape_names = ["icosphere", "bone_shape", "widget", "wgt_"]

    for obj in list(bpy.data.objects):
        name_lower = obj.name.lower()
        if any(s in name_lower for s in shape_names):
            bpy.data.objects.remove(obj, do_unlink=True)
            deleted += 1

    return deleted


def resize_textures(max_size=1024, force_pot=False):
    """
    Resize all textures larger than max_size.

    Args:
        max_size: Maximum dimension (default 1024)
        force_pot: Force power-of-two dimensions (better GPU compatibility)
    """
    resized = 0

    def nearest_pot(n):
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
            # Still check for non-POT if force_pot enabled
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
            # Round to nearest power of two
            new_w = nearest_pot(new_w)
            new_h = nearest_pot(new_h)
            # Ensure doesn't exceed max_size
            while new_w > max_size:
                new_w //= 2
            while new_h > max_size:
                new_h //= 2
        else:
            # Just ensure even dimensions (required for some codecs)
            new_w = new_w if new_w % 2 == 0 else new_w + 1
            new_h = new_h if new_h % 2 == 0 else new_h + 1

        if new_w == w and new_h == h:
            continue

        try:
            img.scale(new_w, new_h)
            resized += 1
            pot_note = " (POT)" if force_pot else ""
            print(f"    Resized {img.name}: {w}x{h} -> {new_w}x{new_h}{pot_note}")
        except Exception as e:
            print(f"    Failed to resize {img.name}: {e}")

    return resized


def get_scene_stats():
    """Get current scene statistics"""
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]

    total_verts = sum(len(o.data.vertices) for o in meshes)
    total_bones = sum(len(a.data.bones) for a in armatures)
    total_actions = len(bpy.data.actions)

    return {
        "meshes": len(meshes),
        "vertices": total_verts,
        "bones": total_bones,
        "actions": total_actions,
    }


def count_mesh_islands(obj):
    """Count disconnected mesh parts (islands) using BFS"""
    from notso_glb._bpy import bmesh

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    visited = set()
    islands = 0

    for v in bm.verts:
        if v.index in visited:
            continue
        islands += 1
        stack = [v]
        while stack:
            current = stack.pop()
            if current.index in visited:
                continue
            visited.add(current.index)
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other.index not in visited:
                    stack.append(other)

    bm.free()
    return islands


# Bloat detection thresholds for web mascots
BLOAT_THRESHOLDS = {
    "prop_warning": 1000,  # Non-skinned mesh > this = warning
    "prop_critical": 2000,  # Non-skinned mesh > this = critical
    "repetitive_islands": 10,  # More islands than this...
    "repetitive_verts": 50,  # ...with more verts each = repetitive detail
    "scene_total": 15000,  # Total scene verts for web
}


def cleanup_mesh_bmesh(obj):
    """
    Clean up mesh using bmesh operations:
    - Remove duplicate vertices (doubles)
    - Dissolve degenerate geometry (zero-area faces, zero-length edges)
    - Remove loose vertices

    Returns dict with cleanup stats or None if failed.
    """
    from notso_glb._bpy import bmesh

    original_verts = len(obj.data.vertices)
    original_faces = len(obj.data.polygons)

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    stats = {
        "doubles_merged": 0,
        "degenerate_dissolved": 0,
        "loose_removed": 0,
    }

    # 1. Remove doubles (merge vertices within threshold)
    # Note: remove_doubles modifies in-place, returns None
    merge_dist = 0.0001  # 0.1mm threshold
    verts_before_doubles = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_dist)
    stats["doubles_merged"] = verts_before_doubles - len(bm.verts)

    # 2. Dissolve degenerate geometry
    # First dissolve zero-area faces
    degenerate_faces = [f for f in bm.faces if f.calc_area() < 1e-8]
    if degenerate_faces:
        bmesh.ops.delete(bm, geom=degenerate_faces, context="FACES")
        stats["degenerate_dissolved"] += len(degenerate_faces)

    # Then dissolve zero-length edges
    degenerate_edges = [e for e in bm.edges if e.calc_length() < 1e-8]
    if degenerate_edges:
        bmesh.ops.delete(bm, geom=degenerate_edges, context="EDGES")
        stats["degenerate_dissolved"] += len(degenerate_edges)

    # 3. Remove loose vertices (not connected to any face)
    loose_verts = [v for v in bm.verts if not v.link_faces]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")
        stats["loose_removed"] = len(loose_verts)

    # Write back to mesh
    bm.to_mesh(obj.data)
    bm.free()

    # Update mesh
    obj.data.update()

    new_verts = len(obj.data.vertices)
    new_faces = len(obj.data.polygons)

    stats["verts_before"] = original_verts
    stats["verts_after"] = new_verts
    stats["faces_before"] = original_faces
    stats["faces_after"] = new_faces

    return stats


def decimate_mesh(obj, target_verts):
    """
    Apply decimation to reduce mesh to approximately target vertex count.

    Returns (original_verts, new_verts) or None if failed.
    """
    original_verts = len(obj.data.vertices)
    if original_verts <= target_verts:
        return None

    # Calculate ratio needed
    ratio = target_verts / original_verts

    # Add decimate modifier
    mod = obj.modifiers.new(name="AutoDecimate", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True

    # Apply modifier
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
        new_verts = len(obj.data.vertices)
        return (original_verts, new_verts)
    except Exception as e:
        # Remove modifier if apply failed
        obj.modifiers.remove(mod)
        print(f"    [WARN] Failed to decimate {obj.name}: {e}")
        return None


def auto_fix_bloat(warnings):
    """
    Automatically fix bloated meshes using bmesh cleanup + decimation.

    Pipeline:
    1. Run bmesh cleanup on ALL meshes (doubles, degenerate, loose)
    2. Decimate non-skinned props still flagged as BLOATED_PROP

    Returns dict with cleanup_stats and decimation_fixes.
    """
    results = {
        "cleanup": [],
        "decimation": [],
    }

    # Phase 1: BMesh cleanup on ALL meshes
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        verts_before = len(obj.data.vertices)
        if verts_before < 10:  # Skip tiny meshes
            continue

        try:
            stats = cleanup_mesh_bmesh(obj)
            if stats and (
                stats["doubles_merged"] > 0
                or stats["degenerate_dissolved"] > 0
                or stats["loose_removed"] > 0
            ):
                results["cleanup"].append({
                    "object": obj.name,
                    "doubles": stats["doubles_merged"],
                    "degenerate": stats["degenerate_dissolved"],
                    "loose": stats["loose_removed"],
                    "verts_saved": stats["verts_before"] - stats["verts_after"],
                })
        except Exception as e:
            print(f"    [WARN] Cleanup failed for {obj.name}: {e}")

    # Phase 2: Decimate bloated props
    bloated_objects = [
        w["object"]
        for w in warnings
        if w["issue"] == "BLOATED_PROP" and w["severity"] == "CRITICAL"
    ]

    for obj_name in bloated_objects:
        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != "MESH":
            continue

        # Double-check not skinned
        is_skinned = any(mod.type == "ARMATURE" for mod in obj.modifiers)
        if is_skinned:
            continue

        # Check if cleanup already brought it under threshold
        current_verts = len(obj.data.vertices)
        if current_verts <= BLOAT_THRESHOLDS["prop_critical"]:
            continue

        # Target: bring under critical threshold with some margin
        target = int(BLOAT_THRESHOLDS["prop_critical"] * 0.8)

        result = decimate_mesh(obj, target)
        if result:
            orig, new = result
            reduction = ((orig - new) / orig) * 100
            results["decimation"].append({
                "object": obj_name,
                "original": orig,
                "new": new,
                "reduction": reduction,
            })

    return results


def sanitize_gltf_name(name):
    """
    Simulate how glTF export sanitizes names for JS identifiers.
    Dots, spaces, dashes become underscores. Leading digits get prefix.
    """
    import re

    # Replace non-alphanumeric with underscore
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # Ensure doesn't start with digit
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized


def analyze_skinned_mesh_parents():
    """
    Detect skinned meshes that are not at scene root.

    glTF spec: parent transforms don't affect skinned meshes, so non-root
    skinned meshes can have unexpected positioning.

    Returns list of warnings for each non-root skinned mesh.
    """
    warnings = []

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        # Check if mesh is skinned (has armature modifier)
        has_armature = any(mod.type == "ARMATURE" for mod in obj.modifiers)
        if not has_armature:
            continue

        # Check if it has a parent (not at root)
        if obj.parent is not None:
            # Check if parent has non-identity transform
            parent = obj.parent
            has_transform = (
                parent.location.length > 0.0001
                or parent.rotation_euler.x != 0
                or parent.rotation_euler.y != 0
                or parent.rotation_euler.z != 0
                or abs(parent.scale.x - 1) > 0.0001
                or abs(parent.scale.y - 1) > 0.0001
                or abs(parent.scale.z - 1) > 0.0001
            )

            warnings.append({
                "mesh": obj.name,
                "parent": parent.name,
                "has_transform": has_transform,
                "severity": "CRITICAL" if has_transform else "WARNING",
            })

    return warnings


def analyze_unused_uv_maps():
    """
    Detect UV maps that aren't used by any material.

    Unused TEXCOORD attributes bloat the glTF file.
    Returns list of meshes with unused UV maps.
    """
    warnings = []

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        mesh = obj.data
        if not mesh.uv_layers:
            continue

        # Get UV maps used by materials
        used_uvs = set()
        for mat_slot in obj.material_slots:
            if not mat_slot.material or not mat_slot.material.use_nodes:
                continue
            for node in mat_slot.material.node_tree.nodes:
                if node.type == "UVMAP" and node.uv_map:
                    used_uvs.add(node.uv_map)
                # Image textures default to first UV if no explicit UV node
                if node.type == "TEX_IMAGE":
                    if not used_uvs and mesh.uv_layers:
                        used_uvs.add(mesh.uv_layers[0].name)

        # If no explicit UV usage found, assume first UV is used
        if not used_uvs and mesh.uv_layers:
            used_uvs.add(mesh.uv_layers[0].name)

        # Find unused UV maps
        unused = [uv.name for uv in mesh.uv_layers if uv.name not in used_uvs]
        if unused:
            warnings.append({
                "mesh": obj.name,
                "unused_uvs": unused,
                "total_uvs": len(mesh.uv_layers),
            })

    return warnings


def remove_unused_uv_maps(warnings):
    """Remove unused UV maps detected by analyze_unused_uv_maps."""
    removed = 0

    for warn in warnings:
        obj = bpy.data.objects.get(warn["mesh"])
        if not obj or obj.type != "MESH":
            continue

        mesh = obj.data
        for uv_name in warn["unused_uvs"]:
            uv_layer = mesh.uv_layers.get(uv_name)
            if uv_layer:
                mesh.uv_layers.remove(uv_layer)
                removed += 1
                print(f"    Removed unused UV '{uv_name}' from {obj.name}")

    return removed


def nearest_power_of_two(n: int) -> int:
    """Round to nearest power of two."""
    if n <= 1:
        return 1
    # Find closest power of 2
    # bit_length() gives position of highest bit, so 2^(bit_length-1) <= n < 2^bit_length
    bit_len = (n - 1).bit_length()
    lower = 1 << (bit_len - 1)
    upper = 1 << bit_len
    return lower if (n - lower) < (upper - n) else upper


def analyze_duplicate_names():
    """
    Detect duplicate names that will cause glTF export issues.

    Checks both:
    1. Exact duplicates in Blender
    2. Names that collide after glTF sanitization (e.g., 'Cube.155' and 'Cube_155')

    Returns list of duplicates grouped by type.
    """
    from collections import Counter, defaultdict

    duplicates = []

    def check_collection(items, type_name):
        """Check a collection for exact and sanitized duplicates."""
        names = [item.name for item in items]

        # 1. Exact duplicates
        for name, count in Counter(names).items():
            if count > 1:
                duplicates.append({
                    "type": type_name,
                    "name": name,
                    "count": count,
                    "issue": "EXACT_DUPLICATE",
                })

        # 2. Sanitization collisions
        sanitized_map = defaultdict(list)
        for name in names:
            sanitized = sanitize_gltf_name(name)
            sanitized_map[sanitized].append(name)

        for sanitized, originals in sanitized_map.items():
            if len(originals) > 1:
                # Only report if they're different names that collide
                unique_originals = set(originals)
                if len(unique_originals) > 1:
                    duplicates.append({
                        "type": type_name,
                        "name": f"{sanitized} <- {list(unique_originals)}",
                        "count": len(originals),
                        "issue": "SANITIZATION_COLLISION",
                    })

    # Check all relevant collections
    check_collection(bpy.data.objects, "OBJECT")
    check_collection(bpy.data.meshes, "MESH")
    check_collection(bpy.data.materials, "MATERIAL")
    check_collection(bpy.data.actions, "ACTION")

    # Special handling for bones (per armature)
    for arm in bpy.data.armatures:
        bone_names = [bone.name for bone in arm.bones]
        for name, count in Counter(bone_names).items():
            if count > 1:
                duplicates.append({
                    "type": "BONE",
                    "name": f"{arm.name}/{name}",
                    "count": count,
                    "issue": "EXACT_DUPLICATE",
                })

    return duplicates


def auto_fix_duplicate_names(duplicates):
    """
    Automatically rename duplicates by appending memory pointer suffix.

    Uses as_pointer() for deterministic, session-stable unique IDs.
    Handles both exact duplicates and sanitization collisions.
    Returns list of renames performed.
    """
    import re

    renames = []
    processed = set()  # Track already-renamed items

    def get_collection(dtype):
        """Get the appropriate bpy.data collection."""
        if dtype == "OBJECT":
            return bpy.data.objects
        elif dtype == "MESH":
            return bpy.data.meshes
        elif dtype == "MATERIAL":
            return bpy.data.materials
        elif dtype == "ACTION":
            return bpy.data.actions
        return None

    def get_ptr_suffix(item):
        """Get short unique suffix from memory pointer (last 4 hex digits)."""
        return format(item.as_pointer() & 0xFFFF, "04x")

    def rename_item(collection, old_name, new_name, dtype):
        """Rename an item and track it."""
        item = collection.get(old_name)
        if item and old_name not in processed:
            item.name = new_name
            processed.add(new_name)
            renames.append({"type": dtype, "old": old_name, "new": new_name})
            return True
        return False

    for dup in duplicates:
        dtype = dup["type"]
        issue = dup.get("issue", "EXACT_DUPLICATE")

        if dtype == "BONE":
            continue  # Skip bones for now (complex to rename)

        collection = get_collection(dtype)
        if not collection:
            continue

        if issue == "EXACT_DUPLICATE":
            name = dup["name"]
            matching = [item for item in collection if item.name == name]
            # Keep first, rename rest with pointer suffix
            for item in matching[1:]:
                suffix = get_ptr_suffix(item)
                new_name = f"{name}_{suffix}"
                rename_item(collection, item.name, new_name, dtype)

        elif issue == "SANITIZATION_COLLISION":
            # Parse the collision info: "sanitized <- ['name1', 'name2']"
            # Rename all but the first to have unique sanitized form
            match = re.search(r"\[([^\]]+)\]", dup["name"])
            if match:
                names_str = match.group(1)
                # Parse the list of names
                colliding_names = [n.strip().strip("'\"") for n in names_str.split(",")]

                # Keep first, rename rest with pointer suffix
                for name in colliding_names[1:]:
                    item = collection.get(name)
                    if item and name not in processed:
                        # Replace dots with underscores and add pointer suffix
                        base = re.sub(r"\.", "_", name)
                        suffix = get_ptr_suffix(item)
                        new_name = f"{base}_{suffix}"
                        rename_item(collection, name, new_name, dtype)

    return renames


def analyze_mesh_bloat():
    """
    Detect unreasonably complex meshes for web delivery.

    Returns list of warnings with severity levels:
    - CRITICAL: Must fix before web deployment
    - WARNING: Should review, likely bloated
    - INFO: Notable but may be intentional
    """
    warnings = []

    total_verts = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        mesh = obj.data
        verts = len(mesh.vertices)
        total_verts += verts

        if verts < 100:
            continue

        # Check if skinned (character mesh vs prop)
        is_skinned = any(mod.type == "ARMATURE" for mod in obj.modifiers)

        # Count islands for non-skinned meshes (expensive operation)
        islands = 1
        if not is_skinned and verts < 20000:
            islands = count_mesh_islands(obj)

        verts_per_island = verts / max(islands, 1)

        # Bloat detection rules
        if not is_skinned:
            if verts > BLOAT_THRESHOLDS["prop_critical"]:
                warnings.append({
                    "severity": "CRITICAL",
                    "object": obj.name,
                    "issue": "BLOATED_PROP",
                    "detail": f"{verts:,} verts (limit: {BLOAT_THRESHOLDS['prop_critical']:,})",
                    "suggestion": "Decimate or replace with baked texture",
                })
            elif verts > BLOAT_THRESHOLDS["prop_warning"]:
                warnings.append({
                    "severity": "WARNING",
                    "object": obj.name,
                    "issue": "HIGH_VERT_PROP",
                    "detail": f"{verts:,} verts",
                    "suggestion": "Consider simplifying",
                })

            if (
                islands > BLOAT_THRESHOLDS["repetitive_islands"]
                and verts_per_island > BLOAT_THRESHOLDS["repetitive_verts"]
            ):
                warnings.append({
                    "severity": "CRITICAL",
                    "object": obj.name,
                    "issue": "REPETITIVE_DETAIL",
                    "detail": f"{islands} islands x {verts_per_island:.0f} verts each",
                    "suggestion": "Merge islands or use instancing/texture",
                })

    # Scene-level check
    if total_verts > BLOAT_THRESHOLDS["scene_total"]:
        warnings.append({
            "severity": "WARNING",
            "object": "SCENE",
            "issue": "HIGH_TOTAL_VERTS",
            "detail": f"{total_verts:,} verts (target: <{BLOAT_THRESHOLDS['scene_total']:,})",
            "suggestion": "Review all meshes for optimization opportunities",
        })

    # Sort by severity
    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    warnings.sort(key=lambda w: severity_order.get(w["severity"], 99))

    return warnings


def optimize_and_export(
    output_path=None,
    export_format="GLB",
    use_draco=True,
    use_webp=True,
    max_texture_size=1024,
    force_pot_textures=False,
    analyze_animations=True,
    check_bloat=True,
    experimental_autofix=False,
):
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

    # Step 0: Analyze mesh bloat (early warning)
    if check_bloat:
        print("\n[0/6] Analyzing mesh complexity...")
        bloat_warnings = analyze_mesh_bloat()
    else:
        print("\n[0/6] Skipping bloat check")
        bloat_warnings = []

    if bloat_warnings:
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

        # Experimental auto-fix
        if experimental_autofix:
            print("\n  [EXPERIMENTAL] Running auto-fix pipeline...")

            results = auto_fix_bloat(bloat_warnings)

            # Report cleanup phase
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
                        f"    {c['object']}: {', '.join(details)} "
                        f"(-{c['verts_saved']} verts)"
                    )
                    total_saved += c["verts_saved"]
                print(f"  Cleanup total: {total_saved:,} verts removed")
            else:
                print("\n  Phase 1: No cleanup needed")

            # Report decimation phase
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
        else:
            print("  Fix these in Blender before export for optimal web delivery.")
            print("  Or use --experimental-autofix to auto-decimate props.")

        print(f"{'!' * 60}\n")
    else:
        print("      No bloat issues detected")

    # Step 0b: Check for duplicate names
    print("\n[0b/6] Checking for duplicate names...")
    duplicates = analyze_duplicate_names()

    if duplicates:
        print(f"\n{'#' * 60}")
        print(f"  DUPLICATE NAME WARNINGS: {len(duplicates)} found")
        print(f"{'#' * 60}")

        for dup in duplicates:
            issue = dup.get("issue", "DUPLICATE")
            if issue == "SANITIZATION_COLLISION":
                print(f"  [{dup['type']}] COLLISION: {dup['name']}")
            else:
                print(f"  [{dup['type']}] '{dup['name']}' x{dup['count']}")

        if experimental_autofix:
            print("\n  [EXPERIMENTAL] Auto-fixing duplicate names...")
            renames = auto_fix_duplicate_names(duplicates)
            for r in renames:
                print(f"    [{r['type']}] {r['old']} -> {r['new']}")
            if renames:
                print(f"  Renamed {len(renames)} item(s)")
            else:
                print("  No renames needed")
        else:
            print(
                "\n  These will cause JS identifier collisions in generated components."
            )
            print("  Fix in Blender or use --experimental-autofix to auto-rename.")

        print(f"{'#' * 60}\n")
    else:
        print("      No duplicate names found")

    # Step 0c: Check for skinned mesh parenting issues
    print("\n[0c/6] Checking skinned mesh hierarchy...")
    skinned_warnings = analyze_skinned_mesh_parents()

    if skinned_warnings:
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
            transform_note = (
                " (has non-identity transform!)" if w["has_transform"] else ""
            )
            print(f"  {icon} {w['mesh']} -> parent: {w['parent']}{transform_note}")

        print(f"{'~' * 60}")
        print("  To fix: Apply parent transforms or reparent to scene root")
        print("")
    else:
        print("      All skinned meshes at root or have identity-transform parents")

    # Step 0d: Check for unused UV maps
    print("\n[0d/6] Checking for unused UV maps...")
    unused_uv_warnings = analyze_unused_uv_maps()

    if unused_uv_warnings:
        total_unused = sum(len(w["unused_uvs"]) for w in unused_uv_warnings)
        print(f"\n{'-' * 60}")
        print(
            f"  UNUSED UV MAPS: {total_unused} found in {len(unused_uv_warnings)} mesh(es)"
        )
        print(f"{'-' * 60}")

        for w in unused_uv_warnings:
            print(
                f"  {w['mesh']}: {w['unused_uvs']} (keeping {w['total_uvs'] - len(w['unused_uvs'])})"
            )

        if experimental_autofix:
            print("\n  [EXPERIMENTAL] Removing unused UV maps...")
            removed = remove_unused_uv_maps(unused_uv_warnings)
            print(f"  Removed {removed} unused UV map(s)")
        else:
            print("\n  These cause UNUSED_OBJECT warnings in glTF validation.")
            print("  Use --experimental-autofix to auto-remove them.")

        print(f"{'-' * 60}\n")
    else:
        print("      No unused UV maps found")

    # Step 1: Clean bone shapes
    print("\n[1/6] Cleaning bone shape objects...")
    deleted = delete_bone_shape_objects()
    print(f"      Deleted {deleted} objects")

    # Step 2: Clean vertex groups
    print("\n[2/6] Cleaning unused vertex groups...")
    removed_vg = clean_vertex_groups()
    print(f"      Removed {removed_vg} empty vertex groups")

    # Step 3: Analyze and mark static bones
    if analyze_animations:
        print("\n[3/6] Analyzing bone animations (may take 1-2 minutes)...")
        static_bones = analyze_bone_animation()
        marked, skipped = mark_static_bones_non_deform(static_bones)
        print(f"      Found {len(static_bones)} static bones")
        print(f"      Marked {marked} as non-deform, kept {skipped} for skinning")
    else:
        print("\n[3/6] Skipping animation analysis")

    # Step 4: Resize textures
    if max_texture_size > 0 or force_pot_textures:
        pot_msg = " (forcing POT)" if force_pot_textures else ""
        print(f"\n[4/6] Resizing textures > {max_texture_size}px{pot_msg}...")
        resized = resize_textures(max_texture_size, force_pot=force_pot_textures)
        print(f"      Resized {resized} textures")
    else:
        print("\n[4/6] Skipping texture resize")

    # Step 5: Determine output path
    if output_path is None:
        blend_path = bpy.data.filepath
        if blend_path:
            base = os.path.splitext(blend_path)[0]
            output_path = f"{base}_optimized.glb"
        else:
            output_path = os.path.join(os.getcwd(), "optimized_export.glb")

    output_path = bpy.path.abspath(output_path)

    print(f"\n[5/6] Exporting to: {output_path}")
    print(f"      Format: {export_format}, Draco: {use_draco}, WebP: {use_webp}")

    # Step 6: Export
    try:
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format=export_format,
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
            export_image_format="WEBP" if use_webp else "AUTO",
            # Standard settings
            export_yup=True,
            export_texcoords=True,
            export_normals=True,
            export_materials="EXPORT",
            export_shared_accessors=True,
        )
    except Exception as e:
        print(f"\n[ERROR] Export failed: {e}")
        return None

    # Report results
    print("\n[6/6] Export complete!")

    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        print(f"\n{'=' * 60}")
        print(f"  OUTPUT: {os.path.basename(output_path)}")
        print(f"  SIZE:   {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
        print(f"{'=' * 60}")
    else:
        print("\n[WARNING] Output file not found")

    return output_path


# =============================================================================
# CONFIGURATION - Edit these values as needed (used when running from Blender UI)
# =============================================================================
CONFIG = {
    "output_path": None,  # None = auto (same folder as input)
    "use_draco": True,  # Mesh compression
    "use_webp": True,  # WebP textures (smaller than PNG)
    "max_texture_size": 1024,  # Resize textures (0 = no resize)
    "force_pot_textures": False,  # Force power-of-two dimensions
    "analyze_animations": True,  # Find static bones (slow but saves MB)
    "check_bloat": True,  # Detect unreasonable mesh complexity
    "experimental_autofix": False,  # [EXPERIMENTAL] Auto-decimate props
}


def parse_cli_args():
    """Parse CLI arguments - works both via direct execution and blender --python"""
    import sys

    # Detect execution mode:
    # 1. Direct: ./script.py input.glb (args in sys.argv[1:])
    # 2. Blender: blender --python script.py -- input.glb (args after --)
    try:
        idx = sys.argv.index("--")
        script_args = sys.argv[idx + 1 :]
    except ValueError:
        # No '--' found - check if running directly (not from Blender UI)
        # If argv[0] ends with .py and there are more args, we're running directly
        if len(sys.argv) > 1 and sys.argv[0].endswith(".py"):
            script_args = sys.argv[1:]
        else:
            return None  # Running from Blender UI

    if not script_args:
        return None

    import argparse

    parser = argparse.ArgumentParser(
        description="Optimize GLB/glTF/blend files for web delivery",
        prog="glb_export_optimizer.py",
    )
    parser.add_argument("input", help="Input file (.blend, .glb, or .gltf)")
    parser.add_argument(
        "-o", "--output", help="Output path (default: input_optimized.[glb|gltf])"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["glb", "gltf", "gltf-embedded"],
        default="glb",
        help="Output format (default: glb)",
    )
    parser.add_argument(
        "--no-draco", action="store_true", help="Disable Draco compression"
    )
    parser.add_argument(
        "--no-webp", action="store_true", help="Keep original texture format"
    )
    parser.add_argument(
        "--max-texture", type=int, default=1024, help="Max texture size (0=no resize)"
    )
    parser.add_argument(
        "--force-pot",
        action="store_true",
        help="Force power-of-two texture dimensions (better GPU compat)",
    )
    parser.add_argument(
        "--skip-animation-analysis",
        action="store_true",
        help="Skip static bone detection",
    )
    parser.add_argument(
        "--skip-bloat-check", action="store_true", help="Skip mesh complexity analysis"
    )
    parser.add_argument(
        "--experimental-autofix",
        action="store_true",
        help="[EXPERIMENTAL] Auto-decimate bloated props, remove unused UVs",
    )

    return parser.parse_args(script_args)


def import_gltf(filepath):
    """Import GLB/glTF file into Blender scene"""
    # Clear existing scene
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    # Import
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".glb", ".gltf"):
        raise ValueError(f"Unsupported format: {ext}")

    bpy.ops.import_scene.gltf(filepath=filepath)
    print(f"Imported: {filepath}")


def main():
    """Entry point - handles both CLI and Blender UI execution"""
    args = parse_cli_args()

    if args is None:
        # Running from Blender UI or without CLI args
        optimize_and_export(**CONFIG)
        return

    # CLI mode
    input_path = os.path.abspath(args.input)
    ext = os.path.splitext(input_path)[1].lower()

    # Check file exists
    if not os.path.isfile(input_path):
        print(f"[ERROR] File not found: {input_path}")
        return

    # Import if GLB/glTF (blend files are already loaded by Blender)
    if ext in (".glb", ".gltf"):
        import_gltf(input_path)
    elif ext != ".blend":
        print(f"[ERROR] Unsupported format: {ext}")
        print("        Supported: .blend, .glb, .gltf")
        return

    # Map CLI format to Blender format
    format_map = {
        "glb": "GLB",
        "gltf": "GLTF_SEPARATE",
        "gltf-embedded": "GLTF_EMBEDDED",
    }
    export_format = format_map[args.format]
    out_ext = ".gltf" if args.format.startswith("gltf") else ".glb"

    # Determine output path
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        base = os.path.splitext(input_path)[0]
        output_path = f"{base}_optimized{out_ext}"

    # Run optimization
    optimize_and_export(
        output_path=output_path,
        export_format=export_format,
        use_draco=not args.no_draco,
        use_webp=not args.no_webp,
        max_texture_size=args.max_texture,
        force_pot_textures=args.force_pot,
        analyze_animations=not args.skip_animation_analysis,
        check_bloat=not args.skip_bloat_check,
        experimental_autofix=args.experimental_autofix,
    )


if __name__ == "__main__":
    main()
