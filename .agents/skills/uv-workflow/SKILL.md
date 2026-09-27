---
name: uv-workflow
description: "Blender UV layout and unwrapping for asset seams, texel density, intentional overlap, atlas packing and bake-ready surfaces. Use when creating or revising UV maps, not for unrelated scene edits."
---

# UV Workflow

1. Identify unique hero surfaces, repeated parts, material boundaries and intended bake details before marking seams. Place seams along hidden sides, underside edges or real construction boundaries where possible; inspect likely views rather than forbidding all visible seams.
2. Unwrap for the shape and surface role. Use manual seams for important forms; use quick projections as a blockout aid, not an automatic final choice. Inspect stretch and distortions on visible lettering, long strips, curved forms and focal areas.
3. Set texel density by asset role and viewing distance. Keep adjacent parts that share a map visually consistent, but allocate extra resolution to focal surfaces when useful. Intentional mirrored overlap saves space when unique surface variation is unnecessary; keep mirrored islands separate when they need different wear or bake detail. Do not allow accidental overlap to hide unique details.
4. Pack islands with margins appropriate to image resolution and filtering, leaving enough padding to prevent edge bleeding. Choose a shared atlas for reusable modular surfaces or separate images when unique detail/material requirements justify them. A 4K image alone is not a reason to use UDIM; extra tiles are a deliberate authoring choice, not a default export solution. Do not require a lightmap UV channel.
5. The render-active UV map is UV0. Keep other UV maps intact for the standard `resonite-blender` workflow to preserve; do not rename, overwrite or drop them as a side effect of editing the active map. Check the asset after unwrap and after any modifier/topology changes that affect UVs.
6. For normal and auxiliary map creation, consult [texture baking](../references/texture-baking.md). For shared environment pieces, coordinate atlas regions and modular seams with [modular environment design](../references/modular-environment-design.md).
7. Save reproducible Python source in the project and execute edits with `resoloop blender run`; prefer bpy data API, bmesh and mathutils, using context-dependent `bpy.ops` only when needed. Check installed Blender RNA/API for version-sensitive operators. Preserve existing `model.py` and `.blend` before destructive operations.
8. `resonite-blender` owns texture/material conversion and packing, UV preservation review, export, resource checks and final Resonite visual QA; a Blender render is not final verification. `resonite-build` owns native runtime lighting, collision, interaction and world edits. Do not weaken standard validate/diff/apply/reapply safety.
