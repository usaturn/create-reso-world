"""Read-only fixtures from the preserved pre-density run."""
import json
from pathlib import Path

import pytest

from modeling.slum03.layout import read_layout


RUN = Path('artifacts/slum03/finalfix-m-20260928T0511')


@pytest.fixture
def legacy_layout():
    return read_layout(RUN / 'layout.json')


@pytest.fixture
def legacy_manifest():
    return json.loads(Path('content/slum03/slum03.json').read_text(encoding='utf-8'))


@pytest.fixture
def legacy_reports():
    return {path.stem.removesuffix('-report'): json.loads(path.read_text(encoding='utf-8'))
            for path in sorted(RUN.glob('*-report.json'))}
