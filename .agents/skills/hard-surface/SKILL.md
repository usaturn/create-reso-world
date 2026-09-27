---
name: hard-surface
description: "Hard-surface Blender modeling for industrial equipment, machinery, vehicles, consoles, doors and mechanical props. Use for manufacturing seams, Boolean cuts, bevels and layered mechanical forms."
---

# Hard-Surface Modeling

1. Block the silhouette and large primary masses first; add secondary panels, access covers and structural transitions only where construction logic supports them. Reserve tertiary seams, fasteners and greebles for focal zones. Every feature should explain assembly, access, protection, cooling or connection.
2. Plan panel breaks around plausible manufactured parts: bends, joints, service access, material changes and removable covers. Use a separate, organized cutter collection for repeated Boolean work. Keep cuts live while iterating, make sure cutters cross the target cleanly, and inspect intersection shading and topology. Boolean operations generally precede beveling; apply scale when the operation depends on it, not as a blanket command to destroy transforms.
3. Choose bevel width by the asset's physical scale and edge role. Keep widths consistent within a form tier, use selective bevels for complex parts, and add weighted normals only after checking the result. Avoid blanket bevels and unsupported exact numbers; a readable highlight is the goal, not uniform rounding.
4. Repeat vents, bolts and brackets from reusable linked meshes or instances. Keep micro-detail as geometry when it affects silhouette, parallax, contact shadow or close focal readability; use a baked surface treatment when it is only a distant flat mark. Do not invent fixed polygon budgets or remove focal structure to hit a target.
5. For moving parts, create separate objects with pivots at the functional hinge or attachment point; preserve authored hierarchy and pivots. Blender static-mesh output does not imply runtime motion—handoff behavior separately for native Resonite implementation.
6. Keep modifier stacks editable; preserve `model.py` and `.blend` before destructive operations. Save reproducible Python source in the project and run it with `resoloop blender run`; prefer bpy data API, bmesh and mathutils over context-dependent `bpy.ops`. Check installed Blender RNA/API for version-sensitive operations.
7. Handoff export, materials, packing, UV preservation, resource review and final Resonite visual QA to `resonite-blender`; a Blender render is not final QA. Handoff runtime collision, lighting, interaction and world changes to `resonite-build`. Do not alter standard validate/diff/apply/reapply safety.

For repeatable architectural modules, align component roles and connection dimensions with [modular environment design](../references/modular-environment-design.md).