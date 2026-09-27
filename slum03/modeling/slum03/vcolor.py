"""Pure-Python vertex-colour wear masks (multiplicative RGBA, Blender linear)."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from modeling.slum03.geometry import MergedMesh, Vec3, face_normal as _face_normal
from modeling.slum03.materials import MATERIALS


@dataclass(frozen=True)
class WearProfile:
    variation: float
    ground_grime: float
    streaks: float
    edge_wear: float
    rust: float
    edge_color: tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass(frozen=True)
class Spray:
    center: Vec3
    radius: float
    color: tuple[float, float, float]
    strength: float
    # Optional palette names: when set, only vertices of those materials are tinted (a tint that
    # greys one paint can push another towards a saturated hue, e.g. teal fade vs. yellow paint).
    materials: tuple[str, ...] = ()


WEAR: dict[str, WearProfile] = {
    "concrete": WearProfile(0.18, 0.45, 0.55, 0.30, 0.0, (1.12, 1.10, 1.05)),
    "asphalt": WearProfile(0.25, 0.0, 0.0, 0.0, 0.0, (1.0, 1.0, 1.0)),
    "wet": WearProfile(0.05, 0.0, 0.0, 0.0, 0.0, (1.0, 1.0, 1.0)),
    "ground": WearProfile(0.3, 0.0, 0.0, 0.0, 0.0, (1.0, 1.0, 1.0)),
    "rust": WearProfile(0.25, 0.3, 0.2, 0.2, 0.0, (0.8, 0.55, 0.4)),
    "metal": WearProfile(0.12, 0.35, 0.35, 0.35, 0.45, (1.25, 1.2, 1.15)),
    "painted": WearProfile(0.15, 0.35, 0.3, 0.55, 0.35, (0.75, 0.72, 0.70)),
    "wood": WearProfile(0.2, 0.4, 0.25, 0.2, 0.0, (0.8, 0.75, 0.7)),
    "fabric": WearProfile(0.15, 0.3, 0.15, 0.0, 0.0, (1.0, 1.0, 1.0)),
    "plastic": WearProfile(0.1, 0.3, 0.1, 0.2, 0.0, (1.1, 1.1, 1.1)),
    "glass": WearProfile(0.05, 0.2, 0.4, 0.0, 0.0, (1.0, 1.0, 1.0)),
    "paint": WearProfile(0.12, 0.0, 0.2, 0.0, 0.0, (1.0, 1.0, 1.0)),
    "backdrop": WearProfile(0.35, 0.0, 0.0, 0.0, 0.0, (1.0, 1.0, 1.0)),
    "neon": WearProfile(0.0, 0.0, 0.0, 0.0, 0.0, (1.0, 1.0, 1.0)),
    "holo": WearProfile(0.0, 0.0, 0.0, 0.0, 0.0, (1.0, 1.0, 1.0)),
}


def _hash(ix: int, iy: int, iz: int, seed: int) -> float:
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 144665) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def value_noise3(x: float, y: float, z: float, seed: int) -> float:
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    sx, sy, sz = (t * t * (3 - 2 * t) for t in (fx, fy, fz))

    def lerp(a, b, t):
        return a + (b - a) * t

    c = [[[_hash(ix + dx, iy + dy, iz + dz, seed) for dz in (0, 1)] for dy in (0, 1)] for dx in (0, 1)]
    x00 = lerp(c[0][0][0], c[1][0][0], sx)
    x10 = lerp(c[0][1][0], c[1][1][0], sx)
    x01 = lerp(c[0][0][1], c[1][0][1], sx)
    x11 = lerp(c[0][1][1], c[1][1][1], sx)
    return lerp(lerp(x00, x10, sy), lerp(x01, x11, sy), sz)


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _smooth(a, b, x):
    t = _clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def vertex_colors(merged: MergedMesh, origin: Sequence[float], seed: int,
                   sprays: Sequence[Spray] = ()) -> list[tuple[float, float, float, float]]:
    n = len(merged.vertices)
    normals: list[list[Vec3]] = [[] for _ in range(n)]
    family: list[str | None] = [None] * n
    material: list[str | None] = [None] * n
    for face, mat in zip(merged.faces, merged.face_materials):
        fn = _face_normal([merged.vertices[i] for i in face])
        fam = MATERIALS[merged.materials[mat]].family
        for i in face:
            normals[i].append(fn)
            if family[i] is None:
                family[i] = fam
                material[i] = merged.materials[mat]
    top = max(v[1] for v in merged.vertices) + origin[1]
    out = []
    for idx, v in enumerate(merged.vertices):
        prof = WEAR[family[idx] or "concrete"]
        P = (v[0] + origin[0], v[1] + origin[1], v[2] + origin[2])
        base = 1 + prof.variation * (value_noise3(P[0] * 0.35, P[1] * 0.35, P[2] * 0.35, seed) - 0.5) * 2 * 0.5
        rgb = [base, base, base]
        g_raw = _clamp(1 - P[1] / 1.4)
        rgb = [c * (1 - 0.55 * prof.ground_grime * g_raw) for c in rgb]
        ns = normals[idx] or [(0.0, 1.0, 0.0)]
        avg_ny = sum(n_[1] for n_ in ns) / len(ns)
        if abs(avg_ny) < 0.35 and prof.streaks > 0:
            col = value_noise3(P[0] * 2.3 + P[2] * 2.3, 0.0, 0.0, seed + 7)
            s = prof.streaks * _smooth(0.55, 0.8, col) * _clamp((top - P[1]) / 6)
            rgb = [c * (1 - 0.45 * s) for c in rgb]
        if prof.edge_wear > 0 and len(ns) > 1:
            min_dot = min(sum(a[k] * b[k] for k in range(3)) for i, a in enumerate(ns) for b in ns[i + 1:])
            e = prof.edge_wear * _smooth(0.3, 1.0, _clamp(1 - min_dot)) * value_noise3(P[0] * 1.7, P[1] * 1.7, P[2] * 1.7, seed + 3)
            rgb = [c + (c * ec - c) * e for c, ec in zip(rgb, prof.edge_color)]
        if prof.rust > 0:
            r = prof.rust * _smooth(0.55, 0.85, value_noise3(P[0] * 0.9, P[1] * 0.9, P[2] * 0.9, seed + 5)) * (0.5 + 0.5 * _clamp(1 - P[1] / 2.5))
            rgb = [c + (c * t - c) * r for c, t in zip(rgb, (1.1, 0.55, 0.3))]
        for sp in sprays:
            if sp.materials and material[idx] not in sp.materials:
                continue
            d = math.dist(P, sp.center) / sp.radius
            k = sp.strength * (1 - _smooth(0.4, 1.0, d))
            if k > 0:
                rgb = [c + (c * t - c) * k for c, t in zip(rgb, sp.color)]
        out.append((*(round(_clamp(c, 0.05, 1.3), 6) for c in rgb), 1.0))
    return out  # type: ignore[return-value]
