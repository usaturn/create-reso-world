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
    # Walkable surfaces must face +Y by winding alone (Blender's recalc cannot decide an open sheet).
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


def test_puddles_and_manholes():
    a = _by_name(ground.ground_assemblies(build_layout()))
    assert sum(1 for p in a["ground-puddles"].parts if p.material == "asphalt_wet") == 14
    assert sum(1 for p in a["ground-details"].parts if p.name.startswith("manhole")) == 6


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
