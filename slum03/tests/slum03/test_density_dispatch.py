"""Breaks caught: sector-only dispatch drops mixed new kinds or changes old builds."""
from dataclasses import replace
import pytest
from modeling.slum03.layout import build_layout, read_layout
from modeling.slum03.sectors import sector_assemblies
from pathlib import Path


def test_full_derived_partial_fixture_dispatches_mixed_implemented_kinds_once():
    full = read_layout(Path('content/slum03/density-full-layout.json'))
    # Honest partial fixture: select three implemented kinds in ONE real full sector.
    chosen = tuple(next(p for p in full.placements if p.sector == 'nightlife' and p.kind == kind)
                   for kind in ('ruin', 'shack', 'stall'))
    partial = replace(full, placements=chosen)
    result = sector_assemblies(partial, 'nightlife')
    assert [(a.name, a.kind) for a in result] == [(p.key, p.kind) for p in chosen]
    assert all(a.meta['detail_groups'] for a in result)


def test_legacy_single_kind_meshes_remain_identical():
    layout = build_layout()
    from modeling.slum03.ruins import build_assemblies
    assert sector_assemblies(layout, 'ruins-west') == build_assemblies(layout, 'ruins-west')


def test_full_layout_dispatches_every_use_sector_including_v2_nightlife():
    # Task 8: the fail-closed nightlife guard is replaced by real v2 storefronts;
    # every sector returns exactly its own placements, once, in Layout order.
    full = read_layout(Path('content/slum03/density-full-layout.json'))
    for sector in ('ruins-west', 'ruins-north', 'ruins-east', 'shacks', 'market', 'nightlife'):
        targets = [p for p in full.placements if p.sector == sector]
        result = sector_assemblies(full, sector)
        assert [(a.name, a.kind) for a in result] == [(p.key, p.kind) for p in targets]
        assert all(a.meta['detail_groups'] for a in result)


def test_unsupported_mixed_kind_still_fails_closed():
    full = read_layout(Path('content/slum03/density-full-layout.json'))
    p = next(p for p in full.placements if p.sector == 'nightlife' and p.kind == 'shack')
    bogus = replace(full, placements=(replace(p, kind='kiosk'),))
    with pytest.raises(NotImplementedError, match='unsupported'):
        sector_assemblies(bogus, 'nightlife')
