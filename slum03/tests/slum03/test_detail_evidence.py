"""Mesh-backed details and root-local attachment references."""
from dataclasses import replace

import pytest

from modeling.slum03.detail_evidence import detail_groups
from modeling.slum03.density_model import validate_density_config
from modeling.slum03.geometry import Assembly, box, mesh


def _assembly(groups):
    # The second part is separate physical merchandise; indices refer to real parts.
    parts = [box('counter', (0, 1, 0), (2, 2, 1), 'steel'),
             box('jar', (3, 1, 0), (1, 2, 1), 'steel')]
    return Assembly('stall', 'market-west', 'market', (0, 0, 0), parts,
                    {'detail_groups': groups, 'claimed_count': 900})


def test_detail_groups_are_measured_from_referenced_faces_not_self_report():
    actual = detail_groups(_assembly([
        {'id': 'shelf-1', 'category': 'shelf', 'part_indices': [0]},
        {'id': 'good-1', 'category': 'merchandise', 'part_indices': [1]},
    ]))
    assert actual == [
        {'id': 'shelf-1', 'category': 'shelf', 'part_indices': [0],
         'bounds': {'minimum': [-1.0, 0.0, -0.5], 'maximum': [1.0, 2.0, 0.5]},
         'vertex_count': 8, 'face_count': 6},
        {'id': 'good-1', 'category': 'merchandise', 'part_indices': [1],
         'bounds': {'minimum': [2.5, 0.0, -0.5], 'maximum': [3.5, 2.0, 0.5]},
         'vertex_count': 8, 'face_count': 6},
    ]


def test_unused_vertices_cannot_expand_measured_bounds():
    part = mesh('triangle', [(0, 0, 0), (1, 0, 0), (0, 1, 0), (999, 999, 999)],
                [(0, 1, 2)], 'steel')
    assembly = Assembly('stall', 'one', 'market', (0, 0, 0), [part],
                        {'detail_groups': [{'id': 'shelf', 'category': 'shelf', 'part_indices': [0]}]})
    assert detail_groups(assembly)[0]['bounds']['maximum'] == [1.0, 1.0, 0.0]
    assert detail_groups(assembly)[0]['vertex_count'] == 3


@pytest.mark.parametrize('groups', [
    [{'id': 'empty', 'category': 'shelf', 'part_indices': []}],
    [{'id': 'absent', 'category': 'shelf', 'part_indices': [2]}],
    [{'id': 'bool', 'category': 'shelf', 'part_indices': [True]}],
    [{'id': 'invalid', 'category': 'other', 'part_indices': [0]}],
    [{'id': 'same', 'category': 'shelf', 'part_indices': [0]},
     {'id': 'same', 'category': 'utility', 'part_indices': [1]}],
    [{'id': 'good1', 'category': 'merchandise', 'part_indices': [1]},
     {'id': 'good2', 'category': 'merchandise', 'part_indices': [1]}],
])
def test_invalid_groups_cannot_claim_detail(groups):
    with pytest.raises(ValueError):
        detail_groups(_assembly(groups))


def _attach(parent_key, lo, hi, reason='fastened'):
    return {'parent_key': parent_key, 'contact_min': lo, 'contact_max': hi, 'reason': reason}


def test_valid_attachment_uses_root_local_contact(legacy_layout):
    parent = next(p for p in legacy_layout.placements if p.key == 'market-west')
    child = replace(parent, key='attached-jar', kind='prop', size=(1, 1, 1),
                    origin=(-9, 1, -34), params={'attachment': _attach('market-west',
                        [-9, 1, -34], [-9, 1.5, -34])})
    assert validate_density_config(replace(legacy_layout, placements=legacy_layout.placements + (child,))) == []


@pytest.mark.parametrize('attach', [
    _attach('not-here', [-9, 1, -34], [-9, 1, -34]),
    _attach('attached-jar', [-9, 1, -34], [-9, 1, -34]),
    _attach('market-west', [float('inf'), 1, -34], [-9, 1, -34]),
    _attach('market-west', [True, 1, -34], [-9, 1, -34]),
    _attach('market-west', [-9, 2, -34], [-9, 1, -34]),
    _attach('market-west', [30, 1, 30], [30, 2, 30]),
    _attach('market-west', [-9, 1, -34], [-9, 1, -34], ''),
])
def test_invalid_attachment_rejected(legacy_layout, attach):
    original = next(p for p in legacy_layout.placements if p.key == 'market-west')
    child = replace(original, key='attached-jar', kind='prop', size=(1, 1, 1),
                    origin=(-9, 1, -34), params={'attachment': attach})
    assert validate_density_config(replace(legacy_layout, placements=legacy_layout.placements + (child,)))


def test_attachment_cycles_rejected(legacy_layout):
    base = next(p for p in legacy_layout.placements if p.key == 'market-west')
    a = replace(base, key='a', origin=(-9, 1, -34), size=(1, 1, 1),
                params={'attachment': _attach('b', [-9, 1, -34], [-9, 1, -34])})
    b = replace(a, key='b', params={'attachment': _attach('a', [-9, 1, -34], [-9, 1, -34])})
    assert validate_density_config(replace(legacy_layout, placements=legacy_layout.placements + (a, b)))


def test_new_detail_profile_rejects_unknown_version(legacy_layout):
    original = next(p for p in legacy_layout.placements if p.key == 'market-west')
    changed = replace(original, params={**original.params, 'detail_profile': 'v3'})
    layout = replace(legacy_layout, placements=tuple(changed if p.key == changed.key else p
                                                     for p in legacy_layout.placements))
    assert validate_density_config(layout)
