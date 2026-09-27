import copy
import math
import pytest

from dataclasses import replace
from modeling.slum03.layout import build_layout
from modeling.slum03.postprocess import choose_root_y, postprocess


def test_anchor_clears_existing_floor_without_editing_it():
    assert choose_root_y(0.0, -4.0) == 4.5
    assert choose_root_y(None, -4.0) == 0.0


@pytest.mark.parametrize('floor,lowest,margin', [(math.nan, -4, .5), (0, math.inf, .5),
                                                (0, -4, -1), (0, -4, math.nan)])
def test_anchor_rejects_invalid_inputs(floor, lowest, margin):
    with pytest.raises(ValueError):
        choose_root_y(floor, lowest, margin)


def test_root_position_changes_only_owned_root():
    source = {'schemaVersion': '1', 'ownership': {'key': 'slum03'},
              'slot': {'key': 'root', 'name': 'Slum03_Slum', 'parent': 'Root'},
              'components': [], 'children': []}
    original = copy.deepcopy(source)
    result = postprocess(source, replace(build_layout(), labels=()), {}, (0, 4.5, 0))
    assert result['slot']['position'] == [0, 4.5, 0]
    assert result['slot']['parent'] == 'Root'
    assert source == original
    assert all(node['slot']['key'] != 'Root' for node in result['children'])
