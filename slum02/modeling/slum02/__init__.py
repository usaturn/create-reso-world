"""slum02 high-quality cyberpunk slum: layout -> Blender sectors -> Resonite bundles.

pytest covers the pure Python layers (``uv run pytest tests/slum02 -q``). Blender
runs through ``resoloop blender run modeling/slum02/build.py``.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FONT_PATH = PROJECT_ROOT / "assets" / "fonts" / "DelaGothicOne-Regular.ttf"
SEED = 260926
