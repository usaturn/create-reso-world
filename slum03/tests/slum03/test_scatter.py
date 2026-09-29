from dataclasses import replace
from modeling.slum03.layout import build_layout
from modeling.slum03.spatial import validate_clearance
from modeling.slum03.types import Bounds3, Placement
from modeling.slum03.gn_scatter import scatter_samples


def test_protruding_rebar_bounds_are_rejected_even_if_centre_is_outside():
    base = build_layout()
    p = Placement('rubble-probe', 'plaza', 'rubble', (16.5, 0, 0), (2, 1, 2), 45, 'district', {})
    layout = replace(base, placements=base.placements + (p,))
    issues = validate_clearance(layout, {p.key: Bounds3((15.5, 0, -1), (17.5, 1, 1))})
    assert any(i.code == 'CLEARANCE_INTRUSION' for i in issues)


def test_sampled_rubble_uses_full_maximum_extent_for_clear_and_three_entries():
    layout = build_layout()
    assert scatter_samples(layout, seed=1, count=0, max_extent=(2, 1, 2)) == ()
    first = scatter_samples(layout, seed=1, count=36, max_extent=(2, 1, 2))
    assert first == scatter_samples(layout, seed=1, count=36, max_extent=(2, 1, 2))
    assert first != scatter_samples(layout, seed=2, count=36, max_extent=(2, 1, 2))
    assert len(first) == 36
    for x, y, z in first:
        assert y == 0
        b = Bounds3((x-1, 0, z-1), (x+1, 1, z+1))
        assert not validate_clearance(layout, {'sample': b})
        assert layout.plaza.x_min <= x-1 and x+1 <= layout.plaza.x_max
        assert layout.plaza.z_min <= z-1 and z+1 <= layout.plaza.z_max


def test_scatter_rejects_extent_larger_than_factory_perimeter():
    import pytest
    with pytest.raises(ValueError, match='maximum extent exceeds plaza'):
        scatter_samples(build_layout(), seed=1, count=1, max_extent=(100, 1, 2))


def test_scatter_has_dense_perimeter_piles_and_sparser_gaps():
    import math
    points = scatter_samples(build_layout(), seed=260927, count=72,
                             max_extent=(1.8, 1.3, 1.8))
    landmarks = [(-18, -8), (-18, 8), (18, -8), (18, 8),
                 (-11, -13), (11, -13), (-11, 12.6), (11, 12.6)]
    near = [min(math.dist((x, z), c) for c in landmarks) < 1.6
            for x, _, z in points]
    assert sum(near) >= 43  # designed accumulations, not uniform scatter
    assert sum(not is_near for is_near in near) >= 7  # unfilled breathing room
    assert sum(sum(math.dist((x,z), c) < 1.6 for x, _, z in points) >= 5
               for c in landmarks) >= 4


# --- Task 8: mixed perimeter rubble, checked after instancing/realization ---

def _full():
    from pathlib import Path
    from modeling.slum03.layout import read_layout
    return read_layout(Path('content/slum03/density-full-layout.json'))


def test_legacy_scatter_plan_is_unchanged_for_existing_candidates():
    from modeling.slum03.gn_scatter import scatter_plan
    heaps = scatter_plan(build_layout())
    instances = [item for items in heaps.values() for item in items]
    assert len(instances) == 72
    assert {item['variant'] for item in instances} == {0, 1, 2}
    # Golden hashes: the legacy samples were verified byte-identical against
    # e270d44 (before Task 8), so a change here means the legacy scatter moved.
    import hashlib
    for seed, samples_hash, plan_hash in (
            (260927, '96c517010df62c6c7cbd5e5d63471715973bbadbf42173f0d5328f9161f4fc89',
             'e7085b32eb81f2867d396fed13ad707c9776962cc5cc5aa04cb7b2bb148cba57'),
            (8195, 'b52ceee16b51aaf3d87d63f43d13bf34a7f577acba04d8dfe5bb9e57e803623a',
             '67db37028ae2d402c4a34f82410b39c0398248f02f0aad514c7cb69ce8f19c23')):
        layout = build_layout(seed)
        samples = scatter_samples(layout, seed=seed, count=72, max_extent=(1.8, 1.3, 1.8))
        assert hashlib.sha256(repr(samples).encode()).hexdigest() == samples_hash
        assert hashlib.sha256(repr(scatter_plan(layout)).encode()).hexdigest() == plan_hash
    # Legacy variant sequence: round-robin in sampling order.
    for seed_layout in (build_layout(),):
        again = scatter_plan(seed_layout)
        assert again == heaps


def _is_floor(name):
    from modeling.slum03.density_model import FLOOR_DEBRIS_PREFIX
    return name.startswith(FLOOR_DEBRIS_PREFIX + '-') or name.startswith('floor-')


def test_full_scatter_mixes_chunks_machines_steel_and_small_debris():
    from collections import Counter
    from modeling.slum03.gn_scatter import VARIANT_KINDS, scatter_plan, variant_parts
    heaps = scatter_plan(_full())
    # Perimeter heaps (every family except the central floor debris).
    instances = [item for name, items in heaps.items() if not _is_floor(name) for item in items]
    legacy = sum(len(v) for v in scatter_plan(build_layout()).values())
    assert len(instances) > legacy
    kinds = Counter(VARIANT_KINDS[item['variant']] for item in instances)
    assert set(kinds) == {'concrete', 'steel', 'machine', 'debris'}
    assert all(count >= 8 for count in kinds.values())
    tiers = Counter(item['tier'] for item in instances)
    assert tiers[0] > tiers[1] > tiers[2] > 0  # many small, fewer large
    materials = {kind: {p.material for p in variant_parts(i)} for i, kind in VARIANT_KINDS.items()}
    assert 'steel_dark' in materials['steel'] and 'electronics' in materials['machine']
    assert 'concrete_stained' in materials['concrete'] | materials['debris']
    assert len(variant_parts(3)) >= 5  # a pile of small pieces, not one box


def test_full_perimeter_scatter_is_unchanged_by_the_floor_debris():
    import hashlib
    from modeling.slum03.gn_scatter import scatter_plan
    heaps = scatter_plan(_full())
    perimeter = {name: items for name, items in heaps.items() if not _is_floor(name)}
    # Task 8 full plan hash, before Task 12 added the central floor debris.
    assert hashlib.sha256(repr(perimeter).encode()).hexdigest() == (
        '9d7f744649dd02a176cbde43dd7877dc1a4fd854fb624f164727da1e2baf1583')


def _walk_keepouts(layout):
    """Main-route effective widths (they include every plaza entrance) and authored branches."""
    rects = [r for r in layout.routes]
    for route in layout.density.routes:
        rects.append(route.corridor)
        rects.extend(o.bounds for o in route.openings)
    rects.extend(layout.density.branch_clearances)
    return rects


def _touches(lo, hi, r, pad=0.):
    return (lo[0] < r.x_max + pad and hi[0] > r.x_min - pad and
            lo[2] < r.z_max + pad and hi[2] > r.z_min - pad)


def _realized(item):
    from modeling.slum03.gn_scatter import realize_instance
    parts = realize_instance(item)
    boxes = []
    for part in parts:
        lo = tuple(min(v[i] for v in part.vertices) for i in range(3))
        hi = tuple(max(v[i] for v in part.vertices) for i in range(3))
        boxes.append((part.name, lo, hi))
    return boxes


def test_realized_full_scatter_keeps_central_floor_and_air_to_walkable_debris_only():
    """Revision 1: only small (<=0.10 m), collider-free debris on the central floor."""
    from modeling.slum03.density_model import FLOOR_DEBRIS_MAX, FLOOR_DEBRIS_PREFIX
    from modeling.slum03.gn_scatter import SIZE_CLASS, scatter_plan
    layout = _full()
    heaps = scatter_plan(layout)
    assert heaps
    clear = layout.clear
    floor_items = floor_pieces = 0
    for name, items in heaps.items():
        floor = name.startswith('floor-')
        points = []
        for item in items:
            x, _, z = item['point']
            ex, ey, ez = item['extent']
            if floor:
                floor_items += 1
                assert SIZE_CLASS[item['variant']] == 'small', (name, item['variant'])
            for part, lo, hi in _realized(item):
                # The realized, scaled and rotated shape stays in the sampled envelope.
                assert x-ex/2-1e-6 <= lo[0] and hi[0] <= x+ex/2+1e-6
                assert z-ez/2-1e-6 <= lo[2] and hi[2] <= z+ez/2+1e-6
                assert -.01 <= lo[1] and hi[1] <= ey+1e-6
                assert layout.plaza.x_min <= lo[0] and hi[0] <= layout.plaza.x_max
                assert layout.plaza.z_min <= lo[2] and hi[2] <= layout.plaza.z_max
                if floor:
                    floor_pieces += 1
                    assert hi[1] <= FLOOR_DEBRIS_MAX, (name, part, hi[1])
                    assert clear.x_min <= lo[0] and hi[0] <= clear.x_max
                    assert clear.z_min <= lo[2] and hi[2] <= clear.z_max
                    # No debris at all on a main-route effective width or entrance.
                    assert not any(_touches(lo, hi, r) for r in _walk_keepouts(layout)), (name, part)
                else:
                    # Medium and larger rubble never enters the central floor or its 3 m air.
                    assert not _touches(lo, hi, clear), (name, part)
                    assert not validate_clearance(layout, {'rubble': Bounds3(lo, hi)})
                points.append((lo, hi))
        heap = Bounds3(tuple(min(p[0][i] for p in points) for i in range(3)),
                       tuple(max(p[1][i] for p in points) for i in range(3)))
        key = f'plaza-rubble-{name}'
        assert not validate_clearance(layout, {key: heap}), name
        if floor:
            assert key.startswith(FLOOR_DEBRIS_PREFIX + '-')
            assert not any(_touches(heap.minimum, heap.maximum, r) for r in _walk_keepouts(layout))
    # A scattered carpet of small pieces, not a token handful (slum02 plaza floor).
    assert floor_items >= 120 and floor_pieces >= 450
    floor_heaps = [n for n in heaps if n.startswith('floor-')]
    assert 8 <= len(floor_heaps) <= 16
    # All four quadrants between the crossing main routes carry debris.
    quads = {(item['point'][0] > 0, item['point'][2] > 0)
             for n in floor_heaps for item in heaps[n]}
    assert len(quads) == 4


def test_floor_debris_is_seeded_and_absent_before_full_stage():
    from dataclasses import replace
    from modeling.slum03.gn_scatter import scatter_plan
    layout = _full()
    first = {n: v for n, v in scatter_plan(layout).items() if n.startswith('floor-')}
    assert first == {n: v for n, v in scatter_plan(_full()).items() if n.startswith('floor-')}
    other = {n: v for n, v in scatter_plan(replace(layout, seed=layout.seed + 1)).items()
             if n.startswith('floor-')}
    assert other and other != first
    for staged in (build_layout(),):
        assert not [n for n in scatter_plan(staged) if n.startswith('floor-')]


def test_floor_debris_variants_are_small_and_varied():
    from modeling.slum03.density_model import FLOOR_DEBRIS_MAX
    from modeling.slum03.gn_scatter import (FLOOR_SCALE, FLOOR_VARIANTS, SIZE_CLASS,
                                            VARIANT_KINDS, variant_parts)
    assert len(FLOOR_VARIANTS) >= 3
    materials = set()
    for index in FLOOR_VARIANTS:
        parts = variant_parts(index)
        assert SIZE_CLASS[index] == 'small' and len(parts) >= 3, VARIANT_KINDS[index]
        top = max(v[1] for p in parts for v in p.vertices)
        assert top * FLOOR_SCALE[1] <= FLOOR_DEBRIS_MAX
        assert min(v[1] for p in parts for v in p.vertices) >= -.01
        materials |= {p.material for p in parts}
    assert {'concrete_raw', 'rust'} <= materials and len(materials) >= 5
    # Perimeter variants stay medium or larger except the legacy mixed pile.
    assert all(SIZE_CLASS[i] != 'small' for i in (0, 1, 2))
