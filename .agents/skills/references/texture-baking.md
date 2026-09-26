# Texture Baking

This reference covers authoring bakes only. It does not prescribe target-engine channel packing or material conversion.

## High-to-low normal bake

1. Finish the low-poly mesh and its intended UV map. Check for accidental overlaps and leave appropriate space between islands.
2. Align and name the high- and low-poly sources clearly. Match their scale and orientation. A cage can extend the low surface toward the high surface; edit it where rays would hit an adjacent part or miss a recessed form. Do not assume one cage extrusion distance works for every asset.
3. Configure the bake through the installed Blender version's UI/API and confirm source, active target image and bake type before running. Test a representative region first. Tune cage shape or ray distances when projection artifacts appear rather than hiding them with unrelated texture edits.
4. Inspect the normal result under a neutral preview. Check seams, skewing, missed protrusions, intersecting source surfaces and reversed shading. Preserve the high-resolution source until the bake is reviewed.

## AO and curvature

Bake AO to describe local occlusion and contact; use curvature-like data to locate convex wear or recessed accumulation when the bake method supports it. Treat both as masks or supporting maps, not universal albedo color. Inspect for excessive darkening, noise and projection leaks. Keep causes and wear placement art-directed rather than multiplying every map into the surface.

## Atlas and margins

Plan atlas regions around the intended set of meshes and their relative visual importance. Keep shared modular surfaces aligned to compatible regions; reserve unique regions for surfaces that need distinct detail. Leave padding for texture filtering and bake dilation. Margin depends on output resolution, mip use and island scale, so inspect the baked edges at reduced sizes and increase it when colors bleed. Do not pack islands so tightly that dilation crosses a neighboring unique region.

Retain the editable high/low sources and bake setup until the result is validated. Material adaptation, packing and final runtime appearance belong to the project's standard Resonite workflow.
