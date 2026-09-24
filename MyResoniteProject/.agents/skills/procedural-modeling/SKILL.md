---
name: procedural-modeling
description: "Repeatable Blender procedural modeling for parametrically generated pipes, cables, buildings, roads, panels, rocks and repeated structure. Use when exposed parameters and controlled variation improve iteration or reuse."
---

# Procedural Modeling

1. Choose procedural construction when repeated structure, controlled variants or revisions benefit from it; hand-author focal forms when procedural uniformity weakens the design. Define named parameters with useful bounds, physical units where relevant, stable random seeds and deterministic iteration order. Changing a seed should be an intentional variation, not uncontrolled noise.
2. Build the simplest parameterized system that expresses the shape. Expose only meaningful controls such as dimensions, spacing, density or seed. Test boundary values and representative seeds; inspect the silhouette, intersections, openings and surface continuity, not just generated counts.
3. Preserve the editable source graph/modifiers and source objects in the `.blend`. Document meaningful parameter defaults and the chosen variant so the asset can be rebuilt. Different seeds are variations, not LODs; choose lower-detail versions only when viewing distance and asset role justify them.
4. For architectural repetition, align modules and openings with [modular environment design](../references/modular-environment-design.md). Before static export, evaluate the chosen result, realize instances and convert curves or evaluated forms into an explicit static mesh where required. Keep authoring geometry separate from export copies; do not destructively collapse the only source.
5. Save reproducible Python source in the project and run it with `resoloop blender run`. Prefer bpy data API, bmesh and mathutils; use context-dependent `bpy.ops` only when needed. Preserve existing `model.py` and `.blend` before destructive work, and check installed Blender RNA/API for version-sensitive operations.
6. `resonite-blender` owns export, material conversion/packing, UV preservation, resource review and final visual QA in Resonite; a Blender render is not final verification. `resonite-build` owns native runtime collision, lighting, interaction and world changes. Leave standard validate/diff/apply/reapply checks unchanged.
