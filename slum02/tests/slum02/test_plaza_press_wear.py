"""N-7 follow-up: the press wear must grey both paints, never push the yellow towards saturated orange."""
from modeling.slum02 import SEED
from modeling.slum02 import geometry as g
from modeling.slum02 import plaza
from modeling.slum02 import vcolor
from modeling.slum02.layout import build_layout
from modeling.slum02.materials import MATERIALS


def _press():
    return next(a for a in plaza.plaza_assemblies(build_layout()) if a.name == "plaza-press")


def _final_colors(material):
    """Mean saturation and red/green ratio of base colour x vertex colour over one material's vertices."""
    press = _press()
    merged = g.merge_assembly(press)
    cols = vcolor.vertex_colors(merged, press.origin, SEED + 5, press.meta["sprays"])
    mi = merged.materials.index(material)
    ids = {i for f, m in zip(merged.faces, merged.face_materials) if m == mi for i in f}
    base = MATERIALS[material].base_color
    sats, ratios = [], []
    for i in ids:
        rgb = [b * c for b, c in zip(base, cols[i][:3])]
        sats.append((max(rgb) - min(rgb)) / max(rgb))
        ratios.append(rgb[0] / rgb[1])
    return sum(sats) / len(sats), sum(ratios) / len(ratios)


def _saturation(rgb):
    return (max(rgb) - min(rgb)) / max(rgb)


def test_yellow_paint_fades_towards_grey_brown_not_orange():
    base = MATERIALS["paint_yellow_faded"].base_color
    sat, red_green = _final_colors("paint_yellow_faded")
    assert sat <= _saturation(base) - 0.08, sat             # duller than the fresh ochre, not more saturated
    assert red_green <= base[0] / base[1] + 0.1, red_green  # hue stays ochre/khaki, not orange


def test_teal_paint_stays_weathered():
    base = MATERIALS["paint_teal_faded"].base_color
    sat, red_green = _final_colors("paint_teal_faded")
    assert sat <= _saturation(base) - 0.2, sat
    assert red_green >= 0.55, red_green                     # green no longer dominates red by ~4x


def test_yellow_panels_are_tessellated_for_in_face_wear():
    parts = {p.name: p for p in _press().parts}
    for name in ("press-guard", "press-control-box", "press-control-door", "press-fallen-guard"):
        assert len(parts[name].vertices) >= 40, (name, len(parts[name].vertices))
    rails = [p for n, p in parts.items() if n.startswith("press-rail")]
    assert rails and all(len(p.vertices) >= 24 for p in rails)
    assert sum(1 for n, p in parts.items() if n.startswith("press-flake") and p.material.startswith("rust")
               and any(abs(v[0] - (plaza.BASES[0][0] + 1.99)) < 0.01 for v in p.vertices)) >= 3   # flakes on the guard


def test_spray_material_filter():
    m = g.merge_assembly(g.Assembly("t", "t", "plaza", (0.0, 0.0, 0.0),
                                    [g.box("a", (0.0, 5.0, 0.0), (1.0, 1.0, 1.0), "paint_teal_faded"),
                                     g.box("b", (0.0, 5.0, 2.0), (1.0, 1.0, 1.0), "paint_yellow_faded")]))
    plain = vcolor.vertex_colors(m, (0.0, 0.0, 0.0), 7)
    sp = vcolor.Spray((0.0, 5.0, 1.0), 10.0, (1.3, 0.45, 0.4), 0.9, ("paint_teal_faded",))
    tinted = vcolor.vertex_colors(m, (0.0, 0.0, 0.0), 7, [sp])
    assert tinted[:8] != plain[:8]      # teal box vertices are tinted
    assert tinted[8:] == plain[8:]      # yellow box vertices are untouched
