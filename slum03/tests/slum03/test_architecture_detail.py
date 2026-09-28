"""Regression targets: fake variants, unsupported attachments, paint-only openings, pose/seed drift."""
from dataclasses import replace
import hashlib
import math
from pathlib import Path

import pytest

from modeling.slum03.geometry import bounds, rotate_y
from modeling.slum03.layout import read_layout
from modeling.slum03.materials import MATERIALS
from modeling.slum03.spatial import placement_bounds
from modeling.slum03.types import Placement


FULL = Path('content/slum03/density-full-layout.json')
REP = Path('content/slum03/density-representative-layout.json')


def _sample(kind, variant, yaw=0):
    size = (8., 12., 8.) if kind == 'ruin' else (4., 4., 4.)
    return Placement(f'example-{kind}', 'ruins-west' if kind == 'ruin' else 'shacks',
                     kind, (0., 0., 0.), size, yaw, 'district',
                     {'detail_profile': 'v2', 'variant': variant})


def _names(a):
    return {p.name for p in a.parts}


def _assert_assembly(a, p):
    assert a.kind == p.kind and a.name == a.meta['placement_key'] == p.key
    assert a.origin == p.origin and a.sector == p.sector
    allowed = placement_bounds(p)
    lo, hi = bounds(a.parts)
    for i in range(3):
        assert allowed.minimum[i] - 1e-6 <= lo[i] + p.origin[i] <= hi[i] + p.origin[i] <= allowed.maximum[i] + 1e-6
    assert a.parts and all(part.vertices and part.faces and part.material in MATERIALS for part in a.parts)
    assert all(len(f) >= 3 and all(0 <= n < len(part.vertices) for n in f)
               for part in a.parts for f in part.faces)
    groups = a.meta['detail_groups']
    assert {g['category'] for g in groups} >= {'architecture', 'utility', 'lived_in'}
    assert len({g['id'] for g in groups}) == len(groups)
    for g in groups:
        assert g['part_indices'] and all(type(i) is int and 0 <= i < len(a.parts)
                                         for i in g['part_indices'])


def test_ruin_variants_have_different_load_paths_and_nonpainted_apertures():
    # Removing a variant's signature piece, recess or slab makes this fail.
    from modeling.slum03.architecture_detail import detailed_ruin
    signatures = {
        'slab_bay': 'projecting-slab', 'broken_corner': 'sheared-corner-slab',
        'service_core': 'external-service-core', 'stepped_shell': 'setback-slab',
        'exposed_frame': 'open-frame-girder', 'patched_facade': 'bolted-patch',
    }
    for variant, characteristic in signatures.items():
        p = _sample('ruin', variant)
        a = detailed_ruin(p, 260927)
        _assert_assembly(a, p)
        assert characteristic in _names(a)
        assert 'recessed-window' in _names(a) and 'front-spandrel' in _names(a)
        window = next(part for part in a.parts if part.name == 'recessed-window')
        # Real depth and void in the +Z face at the center of the window.
        z_front = max(v[2] for v in window.vertices)
        assert min(v[2] for v in window.vertices) < z_front - .3
        assert not any(all(abs(window.vertices[i][2] - z_front) < 1e-6 for i in face)
                       and min(window.vertices[i][0] for i in face) < 0 < max(window.vertices[i][0] for i in face)
                       and min(window.vertices[i][1] for i in face) < 3 < max(window.vertices[i][1] for i in face)
                       for face in window.faces)
        assert 'joint-anchor' in _names(a) and 'work-crate' in _names(a)
    # Geometry/silhouette families, not a palette or rotation change.
    assert len({tuple(sorted(_names(detailed_ruin(_sample('ruin', v), 260927))))
                for v in signatures}) == 6


def test_shack_variants_have_distinct_roofs_and_supported_occupied_shells():
    # Deleting a family roof, door clearance, gutter or lived-in cluster breaks this.
    from modeling.slum03.architecture_detail import detailed_shack
    signatures = {'corrugated': 'folded-sheet', 'plywood': 'staggered-board-roof',
                  'tarp': 'tensioned-canopy', 'pallet': 'spaced-pallet-roof'}
    for variant, characteristic in signatures.items():
        p = _sample('shack', variant)
        a = detailed_shack(p, 260927)
        _assert_assembly(a, p)
        assert {characteristic, 'door-jamb', 'vent-grille', 'drip-gutter',
                'downspout', 'wash-basin', 'support-post'} <= _names(a)
        roof = next(part for part in a.parts if part.name == characteristic)
        assert max(v[1] for v in roof.vertices) - min(v[1] for v in roof.vertices) > .08
        # Through-door from ground to header: no cladding panel crosses front center.
        for part in a.parts:
            if 'cladding' in part.name:
                lo, hi = bounds([part])
                assert not (lo[0] < 0 < hi[0] and lo[1] < 1.5 < hi[1] and lo[2] < p.size[2]/2-.3 < hi[2])
    assert len({tuple(sorted(_names(detailed_shack(_sample('shack', v), 260927))))
                for v in signatures}) == 4


@pytest.mark.parametrize('kind,variant', [('ruin', 'broken_corner'), ('shack', 'tarp')])
def test_yaw_rotates_actual_vertices_without_moving_origin(kind, variant):
    # A pose used only in metadata, or applied twice, must fail.
    from modeling.slum03.architecture_detail import detailed_ruin, detailed_shack
    builder = detailed_ruin if kind == 'ruin' else detailed_shack
    a = builder(_sample(kind, variant), 260927)
    turned = builder(_sample(kind, variant, 90), 260927)
    assert a.origin == turned.origin == (0., 0., 0.)
    assert [p.name for p in a.parts] == [p.name for p in turned.parts]
    for part, rotated in zip(a.parts, turned.parts):
        for original, actual in zip(part.vertices, rotated.vertices):
            assert actual == pytest.approx(rotate_y(original, math.pi/2), abs=1e-7)


@pytest.mark.parametrize('kind,variant', [('ruin', 'slab_bay'), ('shack', 'corrugated')])
def test_seed_changes_small_details_not_structure_and_key_is_stable(kind, variant):
    from modeling.slum03.architecture_detail import detailed_ruin, detailed_shack
    builder = detailed_ruin if kind == 'ruin' else detailed_shack
    p = _sample(kind, variant)
    a, b = builder(p, 260927), builder(p, 260928)
    assert a != b
    assert _names(a) == _names(b)
    assert builder(p, 260927) == a
    assert builder(replace(p, key='other'), 260927) != a


def test_authored_layouts_fit_their_footprints_with_no_missing_variant():
    from modeling.slum03.architecture_detail import detailed_ruin, detailed_shack
    for path in (REP, FULL):
        layout = read_layout(path)
        for p in layout.placements:
            if p.kind in ('ruin', 'shack') and p.params.get('detail_profile') == 'v2':
                _assert_assembly((detailed_ruin if p.kind == 'ruin' else detailed_shack)(p, layout.seed), p)


def test_legacy_unselected_builds_unchanged_and_representative_selected():
    from modeling.slum03.ruins import build_assemblies as ruins, _shell
    from modeling.slum03.shacks import build_assemblies as shacks, _shack
    rep = read_layout(REP)
    for generator, legacy, sector, key, old_digest in (
        (ruins, _shell, 'ruins-west', 'ruin-west-annex', '29cc4c04a6401bdf331a29d82de556cc329475eceb82d65bbae77ec3b32d86f3'),
        (shacks, _shack, 'shacks', 'shack-west', 'd25fd07274b285e2579020b01d7008b8d452e6ebfd0de91a99468aef73f24336'),
    ):
        p = next(p for p in rep.placements if p.key == key)
        actual = next(a for a in generator(rep, sector) if a.name == key)
        assert actual == legacy(p)
        assert hashlib.sha256(repr(actual).encode()).hexdigest() == old_digest
    for gen, sector, key in ((ruins, 'ruins-west', 'ruin-west'), (shacks, 'shacks', 'shack-row')):
        got = {a.name: a for a in gen(rep, sector)}[key]
        assert got.meta['placement_key'] == key and got.meta['detail_groups']
        assert got != ( _shell if key == 'ruin-west' else _shack)(next(p for p in rep.placements if p.key == key))


def test_reordering_placements_does_not_reseed_existing_buildings():
    from modeling.slum03.ruins import build_assemblies
    full = read_layout(FULL)
    first = {a.name: a for a in build_assemblies(full, 'ruins-west')}
    reverse = replace(full, placements=tuple(reversed(full.placements)))
    second = {a.name: a for a in build_assemblies(reverse, 'ruins-west')}
    assert first == second
    assert len(first) > 2
