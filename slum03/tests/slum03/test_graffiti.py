from modeling.slum03.graffiti import GRAFFITI_TEXT, FONT_PATH
from modeling.slum03.layout import build_layout


def test_graffiti_is_exactly_the_north_wall_south_face_copy():
    # 固定値の理由: 承認済みの設計仕様（2026-09-27-slum03-cyberpunk-slum-design.md の D-05・4.3・9.1「工場壁」）が
    # 北壁の位置と、南向きの面の文字列の完全一致を受入条件として定める。
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
