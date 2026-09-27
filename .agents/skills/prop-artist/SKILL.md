---
name: prop-artist
description: "Blender modeling for grounded everyday and hero props, furniture, workshop tools, containers and reusable kitbash parts. Use when props need believable scale, silhouette, purposeful wear or pivot design."
---

# Prop Artist

1. Establish a reference scale and the object's use before detailing. Block primary volumes and check the silhouette from the intended viewing distance. Make contact points, openings, handles and load-bearing parts legible; distinguish hero props that invite close inspection from standard and background props without treating tier labels as polygon quotas.
2. Add secondary construction details that explain how the object is made or used. Everyday objects should retain familiar design language rather than accumulating arbitrary sci-fi panels. Wear should follow cause: polish or dirt at touch points, edge chips at exposed corners, dust on protected upward faces, and cleaner protected undersides. Keep pristine regions where maintenance or protection makes sense.
3. Build kit parts around chosen attachment faces and a documented project grid. Preserve meaningful origins at floor contact, grip, hinge or wall mount; use linked geometry for repeated instances and unique meshes only for deliberate variation. A door's pivot can be authored at the hinge, but runtime movement and collision need a separate Resonite handoff.
4. For sets of modular props, define compatible corner, edge, fill, trim and opening dimensions in [modular environment design](../references/modular-environment-design.md). Place narrative prop groups with [set-dressing patterns](../references/set-dressing-patterns.md); do not confuse modeling a prop with deciding a whole world's layout.
5. Preserve editable modifier stacks and source objects. Before destructive operations preserve the existing `model.py` and `.blend`. Save reproducible Python source in the project; execute with `resoloop blender run`, preferring bpy data API, bmesh and mathutils to context-dependent `bpy.ops`. Check installed Blender RNA/API for version-sensitive operations.
6. `resonite-blender` owns export, material conversion/packing, UV preservation, resource review and final actual-Resonite visual QA; a Blender render is not final verification. `resonite-build` owns native collider, lighting, interaction and world changes. Keep standard validate/diff/apply/reapply safety intact.
