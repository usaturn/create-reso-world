---
name: sci-fi-punk-worlds
description: "Sci-fi punk world art direction for an explicitly named project or district. Use when the user selects a lane such as cyberpunk, hard sci-fi, steampunk, dieselpunk, atompunk or solarpunk; generic sci-fi assets alone do not set a world style."
---

# Sci-Fi Punk Worlds

Use only when the user gives an explicit lane or approves one for the named project, district or asset. Choose one dominant visual grammar and carry it through silhouette, construction, signage and palette. A coherent lane is more useful than collecting genre motifs.

- **Cyberpunk:** dense vertical signage, visible cabling, street-to-tower contrast and neon accents; make signs legible at the intended viewing distance.
- **Hard sci-fi / space:** functional panels and readable modules, restrained materials and purposeful wear.
- **Steampunk:** brass, copper, rivets, gauges and steam vents with Victorian-derived silhouettes.
- **Dieselpunk / atompunk:** heavy industrial machinery, or 1950s-future chrome forms and atomic motifs, respectively.
- **Solarpunk:** warm, inhabited architecture with plants integrated into its construction rather than added as decoration.

For a cyberpunk street beside a concrete utility building, keep cyberpunk as the world setting and treat monumental concrete as a deliberate architectural district choice. Do not add brass Victorian gears, space-opera motifs or neon chrome everywhere by default; an intentional cross-lane exception needs a local reason in the brief. Do not infer a new lane merely from isolated words like “chrome” or “architecture,” and do not change global lighting or the whole project from a local asset request.

Save reproducible Python source in the project and execute Blender edits with `resoloop blender run`; prefer bpy data API, bmesh and mathutils, using context-dependent `bpy.ops` only when needed. Preserve existing `model.py` and `.blend` before destructive operations; check installed Blender RNA/API for version-sensitive behavior.

`resonite-blender` owns export, material conversion/packing, UV preservation, resource review and final visual QA in Resonite; a Blender render is not final verification. `resonite-build` owns native runtime lighting, collision, interaction and world changes. Keep standard validate/diff/apply/reapply safety unchanged.
