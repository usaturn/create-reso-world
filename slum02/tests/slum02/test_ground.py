import math

from modeling.slum02 import geometry as g
from modeling.slum02 import ground
from modeling.slum02.layout import build_layout
from modeling.slum02.vcolor import _face_normal


def _by_name(assemblies):
    return {a.name: a for a in assemblies}


def test_ground_slab_extent_and_top():
    a = _by_name(ground.ground_assemblies(build_layout()))
    base = a["ground-base"]
    lo, hi = g.bounds(base.parts)
    assert lo[0] == -40 and lo[2] == -40 and hi[0] == 40 and hi[2] == 40
    assert abs(hi[1] - ground.GROUND_TOP) < 0.03
    mats = {p.material for p in base.parts}
    assert {"asphalt", "concrete_stained"} <= mats
    # Walkable surfaces must face +Y by winding alone (R11: create_object never recalculates normals).
    merged = g.merge_assembly(g.Assembly("walk", "walk", "ground", (0.0, 0.0, 0.0),
                                         [p for p in base.parts if p.material in ("asphalt", "concrete_stained")
                                          and max(v[1] for v in p.vertices) - min(v[1] for v in p.vertices) < 0.03
                                          and len(p.faces) > 100]))
    horizontal = 0
    for face in merged.faces:
        n = _face_normal([merged.vertices[i] for i in face])
        if abs(n[1]) > 0.5:
            horizontal += 1
            assert n[1] > 0, face
    assert horizontal > 1600


def test_every_puddle_is_placed():
    a = _by_name(ground.ground_assemblies(build_layout()))
    assert sum(1 for p in a["ground-puddles"].parts if p.material == "asphalt_wet") == 14


def test_backdrop_budget_and_extent():
    data = build_layout()
    parts = ground.backdrop_assemblies(data)
    tris = sum(g.triangle_count(p) for a in parts for p in a.parts)
    assert tris <= 20000
    ring = _by_name(parts)["backdrop-ground"]
    radius = max(math.hypot(v[0], v[2]) for p in ring.parts for v in p.vertices)
    assert 215 <= radius <= 221
    inner = min(max(abs(v[0]), abs(v[2])) for p in ring.parts for v in p.vertices)
    assert abs(inner - 40) < 1e-6
    assert sum(1 for a in parts if a.name.startswith("backdrop-mass-")) == len(data["backdrop"]["masses"])


def test_backdrop_has_lit_windows_and_aviation_lights():
    mats = {p.material for a in ground.backdrop_assemblies(build_layout()) for p in a.parts}
    assert {"window_lit", "neon_red", "backdrop_mass"} <= mats


def test_ground_budget_and_determinism():
    data = build_layout()
    first = ground.ground_assemblies(data)
    tris = sum(g.triangle_count(p) for a in first for p in a.parts)
    assert tris <= 40000
    second = ground.ground_assemblies(build_layout())
    assert [(p.name, p.vertices) for a in first for p in a.parts] == [(p.name, p.vertices) for a in second for p in a.parts]


def test_backdrop_ring_faces_up():
    ring = _by_name(ground.backdrop_assemblies(build_layout()))["backdrop-ground"]
    tops = 0
    for p in ring.parts:
        for face in p.faces:
            pts = [p.vertices[i] for i in face]
            if min(v[1] for v in pts) >= ground.BACKDROP_TOP - 1e-9:
                assert _face_normal(pts)[1] > 0.99
                tops += 1
    assert tops == ground.RING_SEGMENTS


def _closed_consistent(mesh):
    directed = set()
    for face in mesh.faces:
        for a, b in zip(face, (*face[1:], face[0])):
            if (a, b) in directed:
                return False
            directed.add((a, b))
    return all((b, a) in directed for a, b in directed)


def _signed_volume(mesh):
    total = 0.0
    for face in mesh.faces:
        p0 = mesh.vertices[face[0]]
        for i in range(1, len(face) - 1):
            p1, p2 = mesh.vertices[face[i]], mesh.vertices[face[i + 1]]
            total += (p0[0] * (p1[1] * p2[2] - p1[2] * p2[1])
                      - p0[1] * (p1[0] * p2[2] - p1[2] * p2[0])
                      + p0[2] * (p1[0] * p2[1] - p1[1] * p2[0])) / 6
    return total


def test_all_closed_parts_wound_outward():
    """R11: Blender no longer recalculates normals, so every closed part must be outward/CCW."""
    data = build_layout()
    open_sheets = {"base-asphalt", "base-blocks"}  # up-facing sheets, checked in the slab test
    for assembly in [*ground.ground_assemblies(data), *ground.backdrop_assemblies(data)]:
        for part in assembly.parts:
            if part.name in open_sheets:
                continue
            assert _closed_consistent(part), (assembly.name, part.name)
            assert _signed_volume(part) > 0, (assembly.name, part.name)


def test_ground_is_open_under_plaza_pits():
    """The plaza's machine pits go below grade, so no ground sheet or slab may cover them."""
    data = build_layout()
    base = _by_name(ground.ground_assemblies(data))["ground-base"]
    for x0, z0, x1, z1 in data["plaza_features"]["pits"]:
        probes = [(x0 + (x1 - x0) * fx, z0 + (z1 - z0) * fz) for fx in (0.1, 0.5, 0.9) for fz in (0.1, 0.5, 0.9)]
        for part in base.parts:
            for face in part.faces:
                pts = [part.vertices[i] for i in face]
                if max(p[1] for p in pts) - min(p[1] for p in pts) > 1e-6:
                    continue  # only horizontal (axis-aligned rectangle) faces can cover a pit
                lx, hx = min(p[0] for p in pts), max(p[0] for p in pts)
                lz, hz = min(p[2] for p in pts), max(p[2] for p in pts)
                assert not any(lx < px < hx and lz < pz < hz for px, pz in probes), part.name
