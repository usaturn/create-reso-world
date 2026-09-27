"""Breaks caught: market products or unsupported canopies blocking the pedestrian lane."""
from modeling.slum03.geometry import bounds
from modeling.slum03.layout import build_layout
from modeling.slum03.materials import MATERIALS
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.spatial import placement_bounds, validate_clearance
from modeling.slum03.types import Bounds3


def _world_bounds(a):
    lo, hi = bounds(a.parts)
    return Bounds3(tuple(lo[i]+a.origin[i] for i in range(3)),
                   tuple(hi[i]+a.origin[i] for i in range(3)))


def _touches(a, b, tolerance=.025):
    lo, hi = bounds([a]); l2, h2 = bounds([b])
    return all(lo[i] <= h2[i]+tolerance and l2[i] <= hi[i]+tolerance for i in range(3))


def test_market_lane_remains_three_metres_clear():
    layout = build_layout()
    stalls = sector_assemblies(layout, 'market')
    assert len(stalls) == 2
    for stall in stalls:
        p = next(p for p in layout.placements if p.key == stall.name)
        real, site = _world_bounds(stall), placement_bounds(p)
        assert all(site.minimum[i]-1e-6 <= real.minimum[i] <= real.maximum[i] <= site.maximum[i]+1e-6
                   for i in range(3))
        assert not validate_clearance(layout, {stall.name: real})
        assert {part.material for part in stall.parts} <= MATERIALS.keys()
    west = _world_bounds(next(s for s in stalls if s.origin[0] < 0))
    east = _world_bounds(next(s for s in stalls if s.origin[0] > 0))
    assert east.minimum[0]-west.maximum[0] >= 3


def test_stall_has_frame_shelves_and_distinct_junk():
    for stall in sector_assemblies(build_layout(), 'market'):
        assert stall.meta['placement_key'] == stall.name
        parts = stall.parts
        for feature in ('post', 'beam', 'awning', 'shelf', 'circuit-board',
                        'monitor', 'tool', 'prosthetic', 'parts-crate'):
            assert any(part.name == feature for part in parts), feature
        posts = [p for p in parts if p.name == 'post']
        awnings = [p for p in parts if p.name == 'awning']
        shelves = [p for p in parts if p.name == 'shelf']
        assert len(posts) >= 4 and len(shelves) >= 2
        assert all(any(_touches(post, awning) for post in posts) for awning in awnings)
        assert all(any(_touches(shelf, post) for post in posts) for shelf in shelves)
        for name in ('circuit-board', 'monitor', 'tool', 'prosthetic', 'parts-crate'):
            assert any(_touches(item, shelf) for item in parts if item.name == name for shelf in shelves), name
        # Products must read as shapes, not a set of plain anonymous cuboids.
        assert any(len(part.vertices) > 8 for part in parts if part.name in ('monitor', 'prosthetic', 'parts-crate'))


def test_task5_sectors_build_uv_clean_and_reopen(tmp_path):
    import json
    import subprocess
    for sector, count in (("market", 2), ("nightlife", 2), ("yarol", 1)):
        blend = tmp_path / f"{sector}.blend"
        subprocess.run(["resoloop", "blender", "run", "modeling/slum03/build.py",
                        "--arg=--sector", f"--arg={sector}", "--arg=--output",
                        f"--arg={blend}", "--json"], check=True, capture_output=True, text=True)
        report = json.loads((tmp_path / f"{sector}-report.json").read_text())
        assert report["errors"] == report["uv_issues"] == []
        assert len(report["objects"]) == len(report["evaluated_bounds"]) == count
        probe = tmp_path / f"{sector}-reopen.py"
        probe.write_text(
            'import bpy, json, sys\nfrom pathlib import Path\n'
            'export=bpy.data.collections["Slum03'+sector+'Export"]\n'
            'source=bpy.data.collections["Slum03'+sector+'Source"]\n'
            'Path(sys.argv[sys.argv.index("--")+1]).write_text(json.dumps({'
            '"count":len(export.objects), "source_hidden":source.hide_render, '
            '"uv":[[u.name for u in o.data.uv_layers if u.active_render] for o in export.objects], '
            '"colors":["Col" in o.data.color_attributes for o in export.objects]}))\n')
        result = tmp_path / f"{sector}-reopen.json"
        subprocess.run(["resoloop", "blender", "run", str(probe), "--blend", str(blend),
                        f"--arg={result}", "--json"], check=True, capture_output=True, text=True)
        data = json.loads(result.read_text())
        assert data == {"count": count, "source_hidden": True,
                        "uv": [["UV0"]]*count, "colors": [True]*count}


def test_shelf_brace_ends_are_carried_by_vertical_uprights():
    for stall in sector_assemblies(build_layout(), 'market'):
        uprights = [part for part in stall.parts if part.name == 'shelf-upright']
        braces = [part for part in stall.parts if part.name == 'shelf-brace']
        assert len(uprights) == 2 and len(braces) == 4
        for brace in braces:
            # Last ring is the wall-side fixing: its actual XYZ location must
            # overlap a ground-to-beam vertical pipe, not merely lie in the stall.
            end = brace.vertices[-6:]
            x = sum(v[0] for v in end)/len(end)
            y = sum(v[1] for v in end)/len(end)
            z = sum(v[2] for v in end)/len(end)
            assert any(_touches(brace, post) and
                       abs((bounds([post])[0][0]+bounds([post])[1][0])/2-x) < .12 and
                       abs((bounds([post])[0][2]+bounds([post])[1][2])/2-z) < .12 and
                       bounds([post])[0][1] <= y <= bounds([post])[1][1]
                       for post in uprights), (stall.name,x,y,z)


def test_task5_preview_renders_without_deprecation_warning(tmp_path):
    import subprocess
    from pathlib import Path
    scene = Path('artifacts/slum03/task5-20260927T184805-2248710')
    image = tmp_path / 'market.png'
    result = subprocess.run(['resoloop', 'blender', 'run', str(scene/'reopen-preview.py'),
                             '--blend', str(scene/'market.blend'), f'--arg={image}', '--json'],
                            check=True, capture_output=True, text=True)
    assert image.stat().st_size > 1000
    assert 'DeprecationWarning' not in result.stdout + result.stderr
