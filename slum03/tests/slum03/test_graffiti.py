from modeling.slum03.graffiti import GRAFFITI_TEXT, FONT_PATH
from modeling.slum03.layout import build_layout


def test_graffiti_is_exactly_the_north_wall_south_face_copy():
    wall = next(p for p in build_layout().placements if p.key == 'north-wall')
    assert GRAFFITI_TEXT == wall.params['graffiti'] == '稲垣は絶対マカぶる'
    assert wall.origin == (0, 0, 14.5)
    assert wall.params['face'] == 'south'
    assert FONT_PATH.is_file()


def test_missing_font_glyph_is_explicit_error():
    import pytest
    from modeling.slum03.graffiti import require_glyphs
    require_glyphs('稲垣は絶対マカぶる')
    with pytest.raises(ValueError, match='missing glyph'):
        require_glyphs('稲\U0010ffff')
