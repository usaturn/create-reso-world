---
name: geometry-nodes
description: "Blender Geometry Nodes authoring for seeded scatter, curves, reusable node groups, modular repetition and parametric assets. Use when node-based geometry generation is requested; not for native runtime graphs."
---

# Geometry Nodes

1. Treat Geometry Nodes as Blender authoring tools, not runtime logic. Define the intended output, named controls, meaningful ranges, stable seed and deterministic source order before building. Keep node groups reusable and expose only controls that an artist needs to direct the result.
2. Verify version-sensitive node types, sockets and modifier APIs against the installed Blender RNA/API or local metadata; never invent exact runtime names or socket identifiers. Build a minimal graph, inspect its evaluated result and then extend it. Test parameter extremes and multiple fixed seeds for silhouette, clipping, scale, density and instance count.
3. Prefer instances for repeated authoring geometry while comparing the evaluated output cost and visual quality. For curves, check profile and endpoints; for scatter, check surface alignment, density distribution and travel/readability around the target surface. Counts help explain cost but do not replace reviewing the asset's visible contribution.
4. Preserve the editable node graph, input values, source meshes and curves in the `.blend`. When static export requires explicit geometry, make an export copy, realize instances and convert curves/evaluated results to a static mesh. Do not treat an unevaluated graph or instance as a transferable Resonite runtime feature. Different seeds are variants, not LODs.
5. Align modular generators to their intended connection dimensions; see [modular environment design](../references/modular-environment-design.md). Do not destructively replace the sole authoring source with an evaluated mesh.
6. Save reproducible Python source in the project and execute with `resoloop blender run`; prefer bpy data API, bmesh and mathutils, with context-dependent `bpy.ops` only when needed. Preserve existing `model.py` and `.blend` before destructive operations.
7. `resonite-blender` owns export, material conversion/packing, UV preservation, resource review and final Resonite visual QA; a Blender render is not final verification. `resonite-build` owns runtime lighting, native collision, interaction and world changes. Keep standard validate/diff/apply/reapply safety unchanged.
