from modeling.slum02 import FONT_PATH, PROJECT_ROOT, SEED


def test_project_root_is_slum02():
    assert PROJECT_ROOT.name == "slum02"
    assert SEED == 260926


def test_font_present_with_license():
    assert FONT_PATH.is_file() and FONT_PATH.stat().st_size > 100_000
    assert (FONT_PATH.parent / "OFL.txt").is_file()
