"""AR holo ad panels (sector ``ads``).

Every layout ad becomes one object; spin floats become two — the panel must pivot on
its own slot for the Spinner the manifest adds later (the ``ad-NN-mount`` /
``ad-NN-panel`` name convention and the panel-centre origin are load-bearing):

* ``wall`` / ``vertical``: object ``ad-NN`` — a ``steel_dark`` border frame, brackets
  that reach back to the wall face (the layout parks the panel centre 0.12 m off it)
  and a single ``holo_*`` face 0.03 in front of the frame (Fresnel Sidedness=Double
  shows both sides, so one thin shell is enough).
* ``float`` (anim ``none``): object ``ad-NN`` — a thin mast on a ballast foot or a
  hanging cable pair, a projector box under the panel (``steel_dark`` body,
  ``neon_cyan`` lens), short struts up to the frame, a thin frame and the holo face.
* ``float`` (anim ``spin``): ``ad-NN-mount`` (mast, ballast, projector, lens) plus
  ``ad-NN-panel`` (thin frame + holo face, parts in panel-centre local coordinates).

Local frame: +Z is the panel's facing direction (the spec yaw), X runs across the
canvas, Y is up. Parts carry the yaw (baked) and every assembly's origin is the spec
position (the panel centre). ``kind`` is ``"ad"`` everywhere. Wall ads get
``meta["occludes"] = ["occ-ad-NN"]`` and their panel+frame AABB contains the layout
occluder box. Everything is deterministic — ad specs carry no seed, so all geometry
derives from the spec itself (the cable-hung mounts are picked by ad number).
R11: every part is a closed outward shell, including the holo face (a thin box).
"""
from __future__ import annotations

import math
from typing import Any

from modeling.slum02 import geometry as g
from modeling.slum02.sectors import register
from modeling.slum02.vcolor import Spray

WALL_OFF = 0.12          # layout parks wall/vertical panel centres this far off the wall face
FRAME_W, FRAME_D = 0.06, 0.08      # wall-panel frame bar width / depth
THIN_W, THIN_D = 0.04, 0.05        # float-panel thin frame bar width / depth
HOLO_GAP = 0.03                    # holo face this far in front of the frame front (brief)
HOLO_T = 0.006
PROJ_GAP = 0.15                    # projection gap between the lens and the panel bottom edge
PROJ_W, PROJ_H, PROJ_D = 0.34, 0.18, 0.30
LENS_R, LENS_T = 0.07, 0.016
POLE_R = 0.035
CABLE_R = 0.006
CABLE_DROP = 4.5                   # the drop line vanishes this far above the panel
RUST = (1.05, 0.6, 0.38)


def _ring(name: str, w: float, h: float, bar: float, depth: float, material: str) -> g.MeshData:
    """4-bar border around a w x h opening (holo canvas = spec size), centred on z=0."""
    bw = w + 2 * bar
    return g.combine(name, [
        g.box("top", (0.0, h / 2 + bar / 2, 0.0), (bw, bar, depth), material),
        g.box("bot", (0.0, -h / 2 - bar / 2, 0.0), (bw, bar, depth), material),
        g.box("left", (-w / 2 - bar / 2, 0.0, 0.0), (bar, h, depth), material),
        g.box("right", (w / 2 + bar / 2, 0.0, 0.0), (bar, h, depth), material),
    ], material)


def _holo(spec: dict[str, Any], z_back: float) -> g.MeshData:
    """The single holo face: a thin closed shell just in front of the frame."""
    w, h = spec["size"]
    return g.box("holo", (0.0, 0.0, z_back + HOLO_T / 2), (w, h, HOLO_T), spec["material"])


def _brackets(w: float, h: float) -> tuple[list[g.MeshData], tuple[float, float]]:
    """Anchor plates (1.5 cm buried in the wall) + arms reaching the frame back
    (-FRAME_D/2). Returns the meshes plus the lowest bracket's centre for the spray."""
    if w >= h:
        us = (-w * 0.3, w * 0.3) if w <= 5 else (-w * 0.34, 0.0, w * 0.34)
        pts = [(u, h * 0.15) for u in us]
        low = min(pts, key=lambda p: p[1])
    else:
        vs = (-h * 0.3, h * 0.3) if h <= 5 else (-h * 0.34, 0.0, h * 0.34)
        pts = [(0.0, v) for v in vs]
        low = min(pts, key=lambda p: p[1])
    out = []
    for k, (bx, by) in enumerate(pts):
        out += [g.box(f"plate-{k}", (bx, by, -WALL_OFF - 0.0025), (0.16, 0.1, 0.025), "steel_dark"),
                g.box(f"arm-{k}", (bx, by, -0.075), (0.05, 0.05, 0.07), "steel_dark")]
    return out, low


def _projector(y_top: float, with_struts: bool) -> tuple[list[g.MeshData], g.MeshData]:
    """Projector box + lens centred on local z=0; box top at ``y_top`` (a ``PROJ_GAP``
    under the canvas bottom edge). Struts tie it to the frame bottom bar."""
    housing = [g.beveled_box("box", (0.0, y_top - PROJ_H / 2, 0.0), (PROJ_W, PROJ_H, PROJ_D), 0.02,
                           "steel_dark")]
    if with_struts:
        for k, sx in enumerate((-1, 1)):
            housing.append(g.box(f"strut-{k}", (sx * 0.12, y_top + 0.045, 0.0), (0.03, 0.09, 0.03),
                                 "steel_dark"))
    lens = g.cylinder("lens", (0.0, y_top + LENS_T / 2, 0.0), LENS_R, LENS_T, 10, "neon_cyan", "Y")
    return housing, lens


def _mast(y_top: float, py: float) -> list[g.MeshData]:
    """Thin mast: ballast block + foot plate at the ground (-py), pole up to the box bottom."""
    return [
        g.pipe("pole", (0.0, -py + 0.02, 0.0), (0.0, y_top - PROJ_H, 0.0), POLE_R, "steel_bare", 8),
        g.box("foot", (0.0, -py + 0.01, 0.0), (0.22, 0.02, 0.22), "steel_dark"),
        g.box("ballast", (0.0, -py + 0.09, 0.0), (0.3, 0.14, 0.3), "concrete_stained"),
        g.box("svc", (0.06, -py + 1.35, 0.0), (0.07, 0.16, 0.1), "electronics"),
    ]


def _hanger(w: float, h: float) -> g.MeshData:
    """Hanging cables: a V from the frame top corners to a point, one drop line up."""
    x_c, y_c = w / 2 + THIN_W - 0.01, h / 2 + THIN_W - 0.01
    conv = (0.0, y_c + 0.6, 0.0)
    return g.combine("cables", [
        g.pipe("v-l", (-x_c, y_c, 0.0), conv, CABLE_R, "rubber", 5),
        g.pipe("v-r", (x_c, y_c, 0.0), conv, CABLE_R, "rubber", 5),
        g.pipe("drop", conv, (0.0, y_c + CABLE_DROP, 0.0), CABLE_R, "rubber", 5),
    ], "rubber")


def _bake(parts: list[g.MeshData], yaw: float) -> list[g.MeshData]:
    return [g.planarize(g.transformed(p, yaw, (0.0, 0.0, 0.0))) for p in parts]


def _mounted(spec: dict[str, Any]) -> g.Assembly:
    """One wall/vertical ad: border frame + brackets into the facade + holo face."""
    w, h = spec["size"]
    px, py, pz = spec["position"]
    yaw = math.radians(spec["rotation"])
    brackets, low = _brackets(w, h)
    steel = [_ring("ring", w, h, FRAME_W, FRAME_D, "steel_dark"), *brackets]
    local = [g.combine("frame", steel, "steel_dark"), _holo(spec, FRAME_D / 2 + HOLO_GAP)]
    meta: dict[str, Any] = {"anim": spec["anim"], "mount": spec.get("mount")}
    if spec["kind"] == "wall":
        meta["occludes"] = [f"occ-{spec['id']}"]
    # rust streak running down from the lowest bracket (tints only this ad's steel)
    wx, _, wz = g.rotate_y((low[0], low[1] - 0.1, -WALL_OFF), yaw)
    meta["sprays"] = [Spray((px + wx, py + low[1] - 0.1, pz + wz), 0.5, RUST, 0.5,
                            materials=("steel_dark",))]
    return g.Assembly("ad", spec["id"], "ads", (float(px), float(py), float(pz)), _bake(local, yaw), meta)


def _float_none(spec: dict[str, Any]) -> g.Assembly:
    """One static float ad: mast or hanger + projector under the thin-framed panel."""
    w, h = spec["size"]
    px, py, pz = spec["position"]
    yaw = math.radians(spec["rotation"])
    hung = int(spec["id"].rsplit("-", 1)[1]) % 3 == 0     # ad-15/21 hang (ad-18 spins anyway)
    y_top = -(h / 2) - PROJ_GAP
    housing, lens = _projector(y_top, with_struts=True)
    local = [_ring("frame", w, h, THIN_W, THIN_D, "steel_dark"), _holo(spec, THIN_D / 2 + HOLO_GAP),
             g.combine("housing", housing, "steel_dark"), lens]
    sprays = []
    if hung:
        local.append(_hanger(w, h))
    else:
        local += _mast(y_top, py)
        sprays.append(Spray((px, 0.05, pz), 0.55, RUST, 0.55,
                            materials=("steel_bare", "steel_dark", "concrete_stained")))
    meta: dict[str, Any] = {"anim": "none", "support": "cable" if hung else "pole"}
    if sprays:
        meta["sprays"] = sprays
    return g.Assembly("ad", spec["id"], "ads", (float(px), float(py), float(pz)), _bake(local, yaw), meta)


def _float_spin(spec: dict[str, Any]) -> tuple[g.Assembly, g.Assembly]:
    """Spin float: mast+projector mount, then the free holo panel on its own pivot."""
    w, h = spec["size"]
    px, py, pz = spec["position"]
    yaw = math.radians(spec["rotation"])
    y_top = -(h / 2) - PROJ_GAP
    housing, lens = _projector(y_top, with_struts=False)
    mount_local = [*_mast(y_top, py), g.combine("housing", housing, "steel_dark"), lens]
    panel_local = [_ring("frame", w, h, THIN_W, THIN_D, "steel_dark"), _holo(spec, THIN_D / 2 + HOLO_GAP)]
    origin = (float(px), float(py), float(pz))
    mount = g.Assembly("ad", f"{spec['id']}-mount", "ads", origin, _bake(mount_local, yaw),
                       {"anim": "spin", "for_panel": f"{spec['id']}-panel",
                        "sprays": [Spray((px, 0.05, pz), 0.55, RUST, 0.55,
                                         materials=("steel_bare", "steel_dark", "concrete_stained"))]})
    panel = g.Assembly("ad", f"{spec['id']}-panel", "ads", origin, _bake(panel_local, yaw),
                       {"anim": "spin", "spin": True})
    return mount, panel


def build_ad(spec: dict[str, Any]) -> list[g.Assembly]:
    """Assemblies for one layout ad spec: 1 object, or mount + panel when it spins."""
    if spec["kind"] in ("wall", "vertical"):
        return [_mounted(spec)]
    if spec["anim"] == "spin":
        return list(_float_spin(spec))
    return [_float_none(spec)]


@register("ads")
def ads_assemblies(data: dict[str, Any]) -> list[g.Assembly]:
    return [a for spec in data["ads"] for a in build_ad(spec)]
