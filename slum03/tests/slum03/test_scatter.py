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


def test_full_scatter_mixes_chunks_machines_steel_and_small_debris():
    from collections import Counter
    from modeling.slum03.gn_scatter import VARIANT_KINDS, scatter_plan, variant_parts
    heaps = scatter_plan(_full())
    instances = [item for items in heaps.values() for item in items]
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


def test_realized_full_scatter_never_enters_clear_floor_or_any_branch():
    from modeling.slum03.gn_scatter import realize_instance, scatter_plan
    layout = _full()
    heaps = scatter_plan(layout)
    assert heaps
    for name, items in heaps.items():
        points = []
        for item in items:
            parts = realize_instance(item)
            verts = [v for part in parts for v in part.vertices]
            lo = tuple(min(v[i] for v in verts) for i in range(3))
            hi = tuple(max(v[i] for v in verts) for i in range(3))
            x, _, z = item['point']
            ex, ey, ez = item['extent']
            # The realized, scaled and rotated shape stays in the sampled envelope.
            assert x-ex/2-1e-6 <= lo[0] and hi[0] <= x+ex/2+1e-6
            assert z-ez/2-1e-6 <= lo[2] and hi[2] <= z+ez/2+1e-6
            assert -1e-6 <= lo[1] and hi[1] <= ey+1e-6
            assert not validate_clearance(layout, {'rubble': Bounds3(lo, hi)})
            assert layout.plaza.x_min <= lo[0] and hi[0] <= layout.plaza.x_max
            assert layout.plaza.z_min <= lo[2] and hi[2] <= layout.plaza.z_max
            points.extend(verts)
        heap = Bounds3(tuple(min(v[i] for v in points) for i in range(3)),
                       tuple(max(v[i] for v in points) for i in range(3)))
        assert not validate_clearance(layout, {name: heap}), name
