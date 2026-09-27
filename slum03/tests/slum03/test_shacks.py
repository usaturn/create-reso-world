"""Failures caught: unsupported roofs, flat fake corrugation, merged dwellings or path blockage."""
from modeling.slum03.geometry import bounds
from modeling.slum03.layout import build_layout
from modeling.slum03.materials import MATERIALS
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.spatial import placement_bounds, validate_clearance
from modeling.slum03.types import Bounds3


def test_shacks_have_separate_supported_roofs_and_rainwater_outlets():
    layout = build_layout()
    buildings = sector_assemblies(layout, 'shacks')
    assert len(buildings) >= 2
    assert len({a.name for a in buildings}) == len(buildings)
    assert len({a.meta['placement_key'] for a in buildings}) == len(buildings)
    for a in buildings:
        assert {p.name for p in a.parts} >= {'post', 'roof-joist', 'corrugated-roof', 'gutter', 'downpipe'}
        roof = next(p for p in a.parts if p.name == 'corrugated-roof')
        # Genuine folds along the fall line; peak and trough vertices at same longitudinal station.
        heights = {round(v[1], 3) for v in roof.vertices if abs(v[2]) < 1e-5}
        assert len(heights) > 2
        lo, hi = bounds(a.parts)
        assert lo[1] == 0 and hi[1] <= 6
        p = next(p for p in layout.placements if p.key == a.meta['placement_key'])
        canonical = placement_bounds(p)
        real = Bounds3(tuple(lo[i] + a.origin[i] for i in range(3)),
                       tuple(hi[i] + a.origin[i] for i in range(3)))
        assert all(canonical.minimum[i] - 1e-6 <= real.minimum[i] <= real.maximum[i] <= canonical.maximum[i] + 1e-6
                   for i in range(3))
        assert not validate_clearance(layout, {a.name: real})
        assert {part.material for part in a.parts} <= MATERIALS.keys()


def test_folded_roof_exports_without_uv_metric_distortion_and_reopens(tmp_path):
    import json
    import subprocess
    blend = tmp_path / 'shacks.blend'
    subprocess.run(['resoloop', 'blender', 'run', 'modeling/slum03/build.py',
                    '--arg=--sector', '--arg=shacks', '--arg=--output',
                    f'--arg={blend}', '--json'], check=True, capture_output=True, text=True)
    report = json.loads((tmp_path / 'shacks-report.json').read_text())
    assert report['errors'] == report['uv_issues'] == []
    probe = tmp_path / 'reopen.py'
    probe.write_text(
        'import bpy, json, sys\nfrom pathlib import Path\n'
        'src=bpy.data.collections["Slum03shacksSource"]\n'
        'out=bpy.data.collections["Slum03shacksExport"]\n'
        'Path(sys.argv[sys.argv.index("--")+1]).write_text(json.dumps({'
        '"source":len(src.objects),"export":len(out.objects),"hidden":src.hide_render,'
        '"uv":[[u.name for u in o.data.uv_layers if u.active_render] for o in out.objects],'
        '"colors":["Col" in o.data.color_attributes for o in out.objects]}))\n')
    evidence = tmp_path / 'reopen.json'
    subprocess.run(['resoloop', 'blender', 'run', str(probe), '--blend', str(blend),
                    f'--arg={evidence}', '--json'], check=True, capture_output=True, text=True)
    data = json.loads(evidence.read_text())
    assert data == {'source': 2, 'export': 2, 'hidden': True,
                    'uv': [['UV0'], ['UV0']], 'colors': [True, True]}
