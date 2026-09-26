---
name: brutalist-mood
description: "Brutalist architecture and monumental concrete art direction for a named project, district or building. Use when the user explicitly requests this architectural direction; generic architecture or concrete assets alone do not trigger it."
---

# Brutalist Mood

Apply the direction only to the named project, district or building. Start with clear massing: broad structural volumes, deep recesses, shadowed entrances, narrow window openings and a small number of material families. Let human scale emerge from doors, landings, handrails and repeated structural bays rather than scattered decorative props. Concrete formwork seams, pour breaks, tie marks and subtle variation should explain construction; avoid arbitrary surface noise.

Use monumental proportions as visual direction, not as automatic circulation design. Oversized stair flights and narrow slits may convey scale, but required stairs, openings, sightlines and usable routes must be checked separately for the actual world. `resonite-build` owns layout and native collider changes; do not silently resize or redesign runtime paths. Avoid changing global lighting from a localized architecture request.

Preserve the requested massing and important recessed forms through asset revisions. Save reproducible Python source in the project and execute Blender edits with `resoloop blender run`; prefer bpy data API, bmesh and mathutils, using context-dependent `bpy.ops` only when needed. Check installed Blender RNA/API for version-sensitive operations and preserve existing `model.py` and `.blend` before destructive changes.

`resonite-blender` owns export, material conversion/packing, UV preservation, resource review and final visual QA in Resonite; Blender renders are not final verification. `resonite-build` owns native runtime lighting, collision, interaction and world changes. Keep standard validate/diff/apply/reapply safety unchanged.
