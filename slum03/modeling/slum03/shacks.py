"""Individually editable occupied shack shells with a load path and rainwater outlet."""
from .geometry import Assembly, box, mesh, tube
from .types import Layout


def _roof(w: float, h: float, d: float):
    """Folded sheet: actual alternating crests/troughs and a continuous fall to +Z."""
    n = max(10, round(w / .36))
    stations = (-d/2+.35, 0, d/2-.35)
    vertices = []
    for side in (0, 1):
        for z in stations:
            for i in range(n+1):
                x = (-w/2+.25) + (w-.5)*i/n
                # Folded sections, not color stripes on a flat roof.
                fold = .11 if i % 2 else 0
                y = h-.55 - (z+d/2)/d*.95 + fold - side*.075
                vertices.append((x, y, z))
    row = n+1
    sheet = len(stations)*row
    faces = []
    for j in range(2):
        for i in range(n):
            a = j*row+i
            faces.append((a, a+row, a+row+1, a+1))
            a += sheet
            faces.append((a+1, a+row+1, a+row, a))
    for i in range(n):
        faces.extend(((i, i+1, sheet+i+1, sheet+i),
                      (2*row+i+1, 2*row+i, sheet+2*row+i, sheet+2*row+i+1)))
    for j in range(2):
        k = j*row
        faces.append((k, sheet+k, sheet+k+row, k+row))
        k += n
        faces.append((k+row, sheet+k+row, sheet+k, k))
    return mesh('corrugated-roof', vertices, faces, 'corrugated_rust')


def _shack(p):
    w, h, d = p.size
    # Timber platform, four posts, tied header/joists, and walls with an actual
    # central entrance gap. Cladding and roof are carried by the timber frame.
    parts = [box('pallet-floor', (0, .14, 0), (w-.45, .28, d-.5), 'pallet_wood')]
    for x in (-w/2+.4, w/2-.4):
        for z in (-d/2+.45, d/2-.45):
            top = h-.62 - (z+d/2)/d*.95
            parts.append(box('post', (x, top/2, z), (.22, top, .22), 'pallet_wood'))
        parts.append(box('roof-joist', (x, h-1.1, 0), (.2, .23, d-.7), 'steel_dark'))
    for z in (-d/2+.48, 0, d/2-.48):
        top = h-.65 - (z+d/2)/d*.95
        parts.append(box('roof-joist', (0, top-.2, z), (w-.55, .22, .18), 'pallet_wood'))
    parts.append(box('back-cladding', (0, (h-1.65)/2, -d/2+.49),
                     (w-.8, h-1.65, .09), 'plywood'))
    for x in (-(w/4-.8), w/4-.8):
        parts.append(box('door-side-cladding', (x, (h-1.85)/2, d/2-.48),
                         (w/2-1.6, h-1.85, .08), 'corrugated'))
    parts.append(box('door-header', (0, h-1.85, d/2-.48),
                     (2.1, .24, .17), 'pallet_wood'))
    for x in (-w/2+.48, w/2-.48):
        parts.append(box('side-cladding', (x, (h-1.9)/2, 0),
                         (.07, h-1.9, d-1.1), 'plywood'))
    parts.append(_roof(w, h, d))
    # Supported at the front eave; outlet turns down one post and stops above grade.
    front = d/2-.4
    y = h-1.54
    parts.append(tube('gutter', [(-w/2+.4, y, front), (w/2-.4, y, front)],
                      .085, 6, 'rust_dark'))
    parts.append(tube('downpipe', [(w/2-.4, y, front), (w/2-.4, .24, front)], .065, 6, 'steel_dark'))
    # Protected ventilation beneath the eave; rain marks end below a drip edge.
    parts.append(box('vent-flashing', (-w*.23, h-1.9, -d/2+.55),
                     (.65, .16, .13), 'rust'))
    return Assembly('shack', p.key, p.sector, p.origin, parts, {'placement_key': p.key})


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    return [_shack(p) for p in layout.placements if p.sector == sector and p.kind == 'shack']
