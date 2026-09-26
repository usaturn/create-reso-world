"""Owned inner-facing night sky, atmospheric layers and distant city silhouettes."""
from __future__ import annotations

import math
from typing import Any

from modeling.tokyo_nova import geometry as geo
from modeling.tokyo_nova.props import Assembly


def _dome() -> Assembly:
    radius, center_y, segments, rings = 78.0, -18.0, 48, 14
    vertices = [(0.0, center_y + radius, 0.0)]
    for row in range(1, rings + 1):
        theta = (math.pi / 2) * row / rings
        for col in range(segments):
            phi = math.tau * col / segments
            vertices.append((radius * math.sin(theta) * math.cos(phi), center_y + radius * math.cos(theta), radius * math.sin(theta) * math.sin(phi)))
    faces = []
    # Winding faces toward the inhabited interior; the open horizon ring avoids a floor/ground cap.
    for col in range(segments):
        faces.append((0, 1 + col, 1 + (col + 1) % segments))
    for row in range(rings - 1):
        start_a = 1 + row * segments
        start_b = start_a + segments
        for col in range(segments):
            a, b = start_a + col, start_a + (col + 1) % segments
            c, d = start_b + (col + 1) % segments, start_b + col
            # All rows face the inhabited side; the pole fan above is inward-wound too.
            faces.append((a, d, c, b))
    return Assembly("night_sky_dome", "Owned inner-facing rain-night dome", (0, 0, 0), 0.0, [geo.mesh("night_dome_inner_shell", vertices, faces, "glass")])


def _horizon_layers() -> list[Assembly]:
    parts: list[geo.MeshData] = []
    # Split, far-horizon ribbons do not close into a small orange circle over the plaza.
    for band, (radius, base_y, material) in enumerate(((58.0, 2.2, "cool_light"), (62.0, 4.1, "faded_teal"), (65.0, 5.8, "warm_light"))):
        for sector in range(8):
            if band == 2 and sector % 3 != 0:
                continue
            start = math.tau * sector / 8 + 0.11 + band * 0.03
            stop = math.tau * (sector + 1) / 8 - 0.13 - band * 0.02
            count = 7
            verts = []
            faces = []
            for index in range(count + 1):
                phi = start + (stop - start) * index / count
                waviness = math.sin(index * 1.7 + sector * 0.8) * (0.35 + band * 0.1)
                for height in (base_y + waviness, base_y + 1.15 + waviness):
                    verts.append((radius * math.cos(phi), height, radius * math.sin(phi)))
            for index in range(count):
                start_vertex = index * 2
                faces.append((start_vertex, start_vertex + 2, start_vertex + 3, start_vertex + 1))
            parts.append(geo.mesh(f"distant_horizon_glow_band_{band}_sector_{sector}", verts, faces, material))
    # Wispy cloud strips sit beyond the owned blocks and carry no lit ground-facing loop.
    for cloud in range(12):
        phi = cloud * math.tau / 12 + .17
        radius = 54.0 + (cloud % 3) * 2.5
        y = 22.0 + (cloud % 4) * 2.2
        tangent = (-math.sin(phi), 0.0, math.cos(phi))
        center = (radius * math.cos(phi), y, radius * math.sin(phi))
        length = 5.5 + (cloud % 4) * 1.7
        points = (
            (center[0] - tangent[0] * length / 2, y, center[2] - tangent[2] * length / 2),
            (center[0] + tangent[0] * length / 2, y + .48 + (cloud % 2) * .2, center[2] + tangent[2] * length / 2),
            (center[0] + tangent[0] * length / 2, y + .68 + (cloud % 2) * .2, center[2] + tangent[2] * length / 2),
            (center[0] - tangent[0] * length / 2, y + .20, center[2] - tangent[2] * length / 2),
        )
        parts.append(geo.mesh(f"distant_cloud_wisp_{cloud}", points, ((0, 1, 2, 3),), "faded_teal" if cloud % 3 else "cool_light"))
    return [Assembly("night_atmosphere", "Segmented distant glow and separated cloud wisps", (0, 0, 0), 0.0, parts)]


def _far_city() -> Assembly:
    parts: list[geo.MeshData] = []
    # Non-uniform tower groupings at four distant horizons; each silhouette has shoulders,
    # rooftop plant and sparse, emissive window strips rather than repeated neon boxes.
    for index in range(44):
        side = index % 4
        along = -58.0 + (index // 4) * 10.8 + ((index * 7) % 3) * 1.15
        if side == 0:
            x, z = along, 54 + (index % 5) * 2.8
        elif side == 1:
            x, z = 54 + (index % 4) * 3.0, along
        elif side == 2:
            x, z = along, -54 - (index % 5) * 2.6
        else:
            x, z = -54 - (index % 4) * 3.2, along
        width = 4.6 + (index % 4) * 1.7
        depth = 4.0 + (index % 3) * 1.25
        height = 22.0 + ((index * 17) % 11) * 5.7
        material = "faded_teal" if index % 4 else "concrete"
        _box = geo.box(f"far_tower_mass_{index}", (x, height / 2, z), (width, height, depth), material)
        parts.append(_box)
        setback = width * (.10 + (index % 3) * .04)
        upper_h = height * (.18 + (index % 4) * .025)
        parts.append(geo.box(f"far_tower_roof_step_{index}", (x + (width - setback) * .12, height - upper_h / 2, z), (width - setback, upper_h, depth - setback), "concrete"))
        if index % 3 == 0:
            parts.append(geo.pipe(f"far_antenna_{index}", (x, height, z), (x, height + 7 + index % 5, z), .06, "exposed_metal", segments=6))
        # Sparse window bands occupy the visible edge facing the neighborhood.
        window_z = z - depth / 2 - .025 if side in (0, 1) else z + depth / 2 + .025
        for row in range(2 + index % 3):
            y = height * (.24 + row * .15)
            parts.append(geo.box(f"far_window_glow_{index}_{row}", (x, y, window_z), (width * .55, .13, .035), "warm_light" if (row + index) % 4 else "cool_light"))
    return Assembly("far_megacity", "Far megacity silhouette · artistic interpretation", (0, 0, 0), 0.0, parts)


def build_skyline(layout: dict[str, Any] | None = None) -> list[Assembly]:
    """Return a sky dome and layered far-city assemblies entirely inside the owned root."""
    return [_dome(), *_horizon_layers(), _far_city()]


def sky_report(assemblies: list[Assembly]) -> dict[str, Any]:
    dome = next((assembly for assembly in assemblies if assembly.kind == "night_sky_dome"), None)
    inner_facing = dome is not None
    if dome is not None:
        for part in dome.parts:
            for face in part.faces:
                a, b, c = (part.vertices[index] for index in face[:3])
                ab = tuple(b[axis] - a[axis] for axis in range(3))
                ac = tuple(c[axis] - a[axis] for axis in range(3))
                normal = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
                centroid = tuple(sum(part.vertices[index][axis] for index in face) / len(face) for axis in range(3))
                if sum(normal[axis] * (centroid[axis] - (0.0, -18.0, 0.0)[axis]) for axis in range(3)) >= -1e-7:
                    inner_facing = False
                    break
            if not inner_facing:
                break
    return {
        "inner_facing": inner_facing,
        "owned_root_only": True,
        "mutates_global_skybox": False,
        "layer_count": len(assemblies),
        "layers": [{"kind": item.kind, "parts": len(item.parts), "triangles": sum(len(face) - 2 for part in item.parts for face in part.faces)} for item in assemblies],
        "city_extent": "artistic far-city silhouettes begin beyond the 50 m owned ground; cloud wisps and split glow arcs sit beyond 54 m",
        "horizon_glow": "warm accents use separated 65 m arcs; there is no closed near-plaza emissive ring",
        "visual_limit": "global directional lighting may affect owned geometry; no world-wide light/sky component was edited",
    }


def local_lights() -> list[dict[str, Any]]:
    """Small warm/cool native point lights, using Reflection-verified Light members."""
    anchors = (
        (-34.0, 2.6, 12.8, (1.0, .62, .34, 1.0)),
        (-25.0, 2.5, 12.9, (1.0, .68, .42, 1.0)),
        (-15.0, 3.0, 11.9, (.80, .61, .39, 1.0)),
        (15.0, 2.5, -35.0, (1.0, .54, .31, 1.0)),
        (15.0, 2.6, -1.8, (1.0, .67, .42, 1.0)),
        (-35.0, 2.1, -23.0, (.95, .59, .35, 1.0)),
        (-25.0, 2.1, -32.1, (.35, .62, .80, 1.0)),
        (-15.0, -1.6, -35.0, (1.0, .47, .25, 1.0)),
        (-15.0, -1.5, -16.0, (.32, .54, .73, 1.0)),
        (25.0, 2.4, -12.0, (.90, .58, .36, 1.0)),
        (35.0, 2.4, 12.0, (.95, .66, .42, 1.0)),
        (10.5, 2.8, 3.0, (.45, .59, .68, 1.0)),
    )
    return [
        {"key": f"city_light_{index:02d}", "name": f"Owned city point light {index + 1:02d}", "position": [x, y, z], "fields": {
            "Enabled": True, "LightType": "Point", "Intensity": 0.75 if y < 0 else 0.9,
            "Color": color, "Range": 7.0,
        }}
        for index, (x, y, z, color) in enumerate(anchors)
    ]
