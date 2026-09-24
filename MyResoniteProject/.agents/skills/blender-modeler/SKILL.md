---
name: blender-modeler
description: "General Blender mesh modeling, blockout, modifier stacks, cleanup, scene organization, precise dimensions and pivots. Use for reusable static assets when no narrower modeling discipline is requested."
---

# Blender Modeler

## Workflow

1. Establish a scale reference, dimensions, origin/pivot intent and collections before detail. Keep temporary blockout distinct from approved geometry; organize reference, source and export-copy objects so cleanup does not erase the editable source.
2. Block primary forms with primitives and edit-mode operations. Use snapping and numeric input for repeatable dimensions. Prefer linked duplicates or collection instances for identical repeated parts; reserve unique meshes for meaningful variation.
3. Keep the modifier stack editable. Combine Mirror or Array for repetition with Solidify for thickness, Boolean for cuts and Bevel for edge highlights in a deliberate order. Boolean cuts generally precede beveling; inspect intersections and shading rather than applying every modifier as a default. Check the installed Blender RNA/API when an operation or socket may vary by version.
4. Clean only intended geometry: merge duplicates where appropriate, remove loose/interior geometry, check normals and manifold boundaries, and preserve intentional openings. Check silhouette and close-up surfaces before simplifying. Do not force a triangle target or destroy useful focal geometry to meet a round number.
5. Save a reproducible Python source in the project and execute it with `resoloop blender run`; prefer bpy data API, bmesh and mathutils, using context-dependent `bpy.ops` only when needed. Before destructive operations, preserve existing `model.py` and `.blend` sources.
6. Handoff: `resonite-blender` owns export, material conversion/packing, UV preservation, resource review and final visual QA in Resonite; a Blender render is not final verification. `resonite-build` owns native runtime collision, lighting, interaction and world changes. Keep its standard validate/diff/apply/reapply workflow unchanged.

For modular wall, floor and opening compatibility, consult [modular environment design](../references/modular-environment-design.md).