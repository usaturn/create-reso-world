"""Inject a real evaluated-mesh defect into the ground export copy before reporting."""
import bpy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from modeling.slum03 import build

mode, output = sys.argv[sys.argv.index('--')+1:]
original = build.add_assembly

def corrupt(*args, **kwargs):
    copy, issues = original(*args, **kwargs)
    if mode == 'uv':
        for layer in tuple(copy.data.uv_layers):
            copy.data.uv_layers.remove(layer)
    elif mode == 'material':
        copy.data.materials.clear()
    else:
        raise ValueError(mode)
    return copy, issues

build.add_assembly = corrupt
build.write_scene('ground', Path(output))
