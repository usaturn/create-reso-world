"""The new world stays self-contained and ready for later generation tasks."""
from pathlib import Path

from modeling.slum03.layout import build_layout

ROOT = Path(__file__).resolve().parents[2]


def test_project_scaffold_is_standalone():
    for name in ('pyproject.toml', 'uv.lock', 'AGENTS.md', '.resoloop.json',
                 'content/main.json', 'modeling/__init__.py', 'modeling/slum03/__init__.py'):
        assert (ROOT / name).exists(), name
    assert not (ROOT / 'modeling/slum02').exists()
    assert not (ROOT / '.resoloop/slum02').exists()
    assert build_layout().seed == 260927


def test_project_guide_names_ownership_and_state():
    text = (ROOT / 'AGENTS.md').read_text()
    assert 'Slum03_Slum' in text
    assert '.resoloop/slum03/state/slum03.json' in text
    assert 'slum03' in text


def test_scaffold_manifest_and_flux_use_the_approved_world_identity():
    import json
    manifest = json.loads((ROOT / 'content/main.json').read_text())
    assert manifest['ownership']['key'] == 'slum03'
    assert manifest['slot']['key'] == 'root'
    assert manifest['slot']['name'] == 'Slum03_Slum'
    assert manifest['slot']['parent'] == 'Root'
    assert not any(c['type'].endswith('.Grabbable') for c in manifest.get('components', []))
    flux = json.loads((ROOT / 'flux/resoloop.flux.json').read_text())
    assert flux['worldState'] == '../.resoloop/slum03/state/slum03.json'
