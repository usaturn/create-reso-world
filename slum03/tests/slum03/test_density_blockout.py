"""Gate A offline camera framing contracts, not a claim of in-world visibility."""
from modeling.slum03.density_blockout import CAMERAS


def test_four_walk_camera_eyes_are_at_1_6m_in_requested_districts():
    assert {key: eye[1] for key, (eye, target) in CAMERAS.items() if key != 'top'} == {
        'northwest': 1.6, 'southwest': 1.6, 'market': 1.6, 'east': 1.6}
    assert CAMERAS['northwest'][0][0] < -20 and CAMERAS['northwest'][0][2] > 0
    assert CAMERAS['southwest'][0][0] < -20 and CAMERAS['southwest'][0][2] < -20
    assert abs(CAMERAS['market'][0][0]) < 20 and CAMERAS['market'][0][2] < -20
    assert CAMERAS['east'][0][0] > 20
