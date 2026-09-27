---
name: dark-gritty-mood
description: "Localized dark, gritty or decayed art direction for surfaces and assets in a named project or location. Use when the user explicitly requests a wear or mood treatment; the words dark, material or architecture alone do not trigger it."
---

# Dark-Gritty Mood

Scope wear to the project, location, asset or surface named in the brief. Keep untreated areas and overall world lighting intact unless a broader change is explicitly requested. Wear should tell a plausible history, not appear as uniform noise.

Choose marks by cause and placement: rust accumulates around persistent moisture, damaged coatings, seams or exposed edges; oil gathers near lubricated joints, machinery and service points; touch wear polishes or dirties handles and frequently contacted controls; chipped paint follows impact, abrasion or maintenance access. Protected faces, recently serviced parts and clean paths may remain clear. Vary age and intensity locally, while keeping labels, edges, silhouettes and route cues readable.

Use restrained value and color shifts to support the requested mood, but do not independently prescribe a shader graph, channel packing or universal lighting change. Distinguish authored surface wear from world-level illumination. Where the surface is a Resonite material, follow the project-standard material conversion and packing rules instead of treating a Blender preview as authoritative. Confirm the actual appearance in Resonite when integrated; a Blender render is not final visual QA.

Save reproducible Python source in the project and run it with `resoloop blender run`; prefer bpy data API, bmesh and mathutils, using context-dependent `bpy.ops` only when needed. Check installed Blender RNA/API for version-sensitive operations. Preserve existing `model.py` and `.blend` before destructive operations.

`resonite-blender` owns export, material conversion/packing, UV preservation, resource review and final visual QA. `resonite-build` owns native runtime lighting, collision, interaction and world changes. Keep standard validate/diff/apply/reapply safety unchanged.
