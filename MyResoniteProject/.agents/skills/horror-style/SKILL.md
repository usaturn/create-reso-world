---
name: horror-style
description: "Horror art direction for Blender assets or a named world zone. Use when the user explicitly requests horror treatment, such as institutional dread, uncanny repetition or environmental tension; ordinary words like dark or architecture alone do not trigger it."
---

# Horror Style

Apply only to the project or zone explicitly named in the art direction. Keep the rest of the world and global lighting unchanged unless the user separately authorizes a broader direction. Build tension through familiar forms made subtly wrong, purposeful absence, asymmetrical evidence of past use, restrained focal objects and transitions between readable and obscured space. Do not require a fixed prop count or leave important geometry unfinished because a zone is sparse.

## Workflow

1. Translate the requested fear or narrative beat into form, contrast, material, sound/interaction handoff and density choices. Modern technology is acceptable when the direction calls for it; analog objects are options, not rules.
2. Shape a readable route and a clear hierarchy of approach, pause and reveal. Narrow passages, low ceilings, blind corners and distorted proportions are optional examples, not fixed dimensions. Keep openings and stairs usable; ask `resonite-build` to handle world layout, traversal and native collider checks where needed.
3. Concentrate story objects and wear where they explain a specific event. Leave deliberate negative space between narrative clusters; see [set-dressing patterns](../references/set-dressing-patterns.md). Fog and volumetric effects are optional; use them only when explicitly useful and supported by the target environment. Flicker, strong contrast and low-detail geometry are also optional choices, not universal requirements.
4. Treat Blender geometry and materials as authored asset inputs, not proof of runtime presentation. Static mesh export does not transfer volumetrics, shader effects, light animation, sound or interactivity. Keep such effects as clearly described runtime requests for the appropriate Resonite workflow. Verify actual look, visibility and route readability in Resonite; a Blender render is not final verification.
5. Save reproducible Python source in the project and execute with `resoloop blender run`; prefer bpy data API, bmesh and mathutils, with context-dependent `bpy.ops` only when needed. Preserve existing `model.py` and `.blend` before destructive operations; check installed Blender RNA/API when version-sensitive behavior matters.
6. `resonite-blender` owns export, material conversion/packing, UV preservation, resource review and final visual QA. `resonite-build` owns native lighting, collision, interaction and world changes. Keep standard validate/diff/apply/reapply safety unchanged.
