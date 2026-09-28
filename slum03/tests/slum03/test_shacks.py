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


def test_front_entrance_is_open_from_ground_to_header():
    # A 2.1m doorway under the header, not two solid panels meeting at X=0.
    for building in sector_assemblies(build_layout(), 'shacks'):
        width = next(p.size[0] for p in build_layout().placements if p.key == building.name)
        front_z = max(v[2] for part in building.parts if part.name == 'door-side-cladding'
                      for v in part.vertices)
        for x in (-.95, 0, .95):
            for part in building.parts:
                for face in part.faces:
                    pts = [part.vertices[i] for i in face]
                    assert not (min(v[0] for v in pts) <= x <= max(v[0] for v in pts)
                                and min(v[1] for v in pts) <= 1.5 <= max(v[1] for v in pts)
                                and min(v[2] for v in pts) <= front_z <= max(v[2] for v in pts))
        assert width > 2.1


def test_long_roof_joists_touch_both_end_posts_and_sheet_underside():
    for building in sector_assemblies(build_layout(), 'shacks'):
        roof = next(p for p in building.parts if p.name == 'corrugated-roof')
        posts = [p for p in building.parts if p.name == 'post']
        joists = [p for p in building.parts if p.name == 'roof-joist'
                  and max(v[2] for v in p.vertices)-min(v[2] for v in p.vertices) > 4]
        assert len(posts) == 4 and len(joists) == 2
        for joist in joists:
            cx = sum(v[0] for v in joist.vertices)/len(joist.vertices)
            post_pair = [p for p in posts if abs(sum(v[0] for v in p.vertices)/len(p.vertices)-cx) < .01]
            assert len(post_pair) == 2
            for post in post_pair:
                z = sum(v[2] for v in post.vertices)/len(post.vertices)
                section = [v for v in joist.vertices if abs(v[2]-z) < .001]
                assert section, 'joist must reach the post at the eave station'
                low, high = min(v[1] for v in section), max(v[1] for v in section)
                post_top = max(v[1] for v in post.vertices)
                assert low < post_top < high, 'the upright actually intersects the beam'
                # Interpolate roof undersurface at the joist centre X from the
                # nearest corrugation crests/troughs at either roof station.
                zs = sorted({v[2] for v in roof.vertices})
                sheet_z = min(zs, key=lambda station: abs(station-z))
                row = sorted((v[0], v[1]) for v in roof.vertices if abs(v[2]-sheet_z) < 1e-6)
                # Two layers share each X; lower one is the roof underside.
                row = sorted({x:min(y for px,y in row if abs(px-x)<1e-6) for x,_ in row}.items())
                pair = next(((x0,y0,x1,y1) for (x0,y0),(x1,y1) in zip(row,row[1:])
                             if x0 <= cx <= x1), None)
                assert pair is not None
                x0,y0,x1,y1 = pair
                roof_under = y0+(y1-y0)*(cx-x0)/(x1-x0)
                assert abs(high-roof_under) < .04, 'sloped beam top must touch the sheet'


def test_last_corrugation_station_matches_final_fold_height():
    from modeling.slum03.shacks import _roof, _eave_height
    for building in sector_assemblies(build_layout(), 'shacks'):
        p = next(p for p in build_layout().placements if p.key == building.name)
        w, h, d = p.size
        n = max(10, round(w/.36))
        roof = _roof(w, h, d)
        z = -d/2+.35
        edge = max(v[0] for v in roof.vertices)
        top = max(v[1] for v in roof.vertices if abs(v[0]-edge)<1e-6 and abs(v[2]-z)<1e-6)
        assert abs(top - (_eave_height(h,d,z) + (.11 if n % 2 else 0))) < 1e-6


def test_v2_roofs_touch_their_corner_posts_at_both_eaves():
    # Shortening any post or flattening the pitch leaves the roof unsupported.
    from modeling.slum03.architecture_detail import detailed_shack
    from modeling.slum03.types import Placement
    for variant in ('corrugated', 'plywood', 'tarp', 'pallet'):
        p = Placement('roof-test', 'shacks', 'shack', (0.,0.,0.), (4.,4.,4.),
                      0., 'district', {'detail_profile':'v2', 'variant':variant})
        a = detailed_shack(p, 260927)
        posts = [part for part in a.parts if part.name == 'support-post']
        assert len(posts) == 4
        roof_names = {'folded-sheet', 'staggered-board-roof',
                      'tensioned-canopy', 'spaced-pallet-roof'}
        roof = [part for part in a.parts if part.name in roof_names]
        for post in posts:
            center_x = sum(v[0] for v in post.vertices)/len(post.vertices)
            center_z = sum(v[2] for v in post.vertices)/len(post.vertices)
            post_top = max(v[1] for v in post.vertices)
            # At the adjacent eave the underside must reach the post head.
            edge = [v for part in roof for v in part.vertices
                    if abs(v[0]-center_x)<.22 and abs(v[2]-center_z)<.23]
            assert edge, (variant, center_x, center_z)
            assert min(v[1] for v in edge)-.14 <= post_top <= max(v[1] for v in edge)+.14, variant
