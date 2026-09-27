"""Offline-only wrapper for an exported bundle under the slum03 test subtree."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
from .types import Manifest, Vec3


def _rewire(value, old_key: str):
    if isinstance(value, str):
        if value == f'$slot:{old_key}':
            return '$slot:blockout-preview-bundle'
        if value.startswith(f'$slot-member:{old_key}.'):
            return value.replace(f'$slot-member:{old_key}.', '$slot-member:blockout-preview-bundle.', 1)
        return value
    if isinstance(value, dict):
        return {key: _rewire(item, old_key) for key, item in value.items()}
    if isinstance(value, list):
        return [_rewire(item, old_key) for item in value]
    return value


def prepare_probe_manifest(source: Path, output: Path, root_position: Vec3) -> Manifest:
    """Write isolated test declaration; never change or apply the original bundle."""
    source, output = Path(source), Path(output)
    bundle = json.loads((source / 'model.apply.json').read_text(encoding='utf-8'))
    old_key = bundle['slot']['key']
    if not old_key or old_key == 'blockout-preview-bundle':
        raise ValueError('invalid bundle root key')
    inner = _rewire(copy.deepcopy(bundle), old_key)
    inner_slot = inner['slot']
    inner_slot.pop('parent', None)
    inner_slot['key'] = 'blockout-preview-bundle'
    def check_parents(node):
        for child in node.get('children', []):
            parent = child['slot'].get('parent')
            if parent is not None and parent != '$slot:blockout-preview-bundle' and not parent.startswith('$slot:'):
                raise ValueError(f'external parent in bundle: {parent}')
            check_parents(child)
    check_parents(inner)
    # Bundle root transforms/components/children belong to its own nested slot.
    inner = {k: inner[k] for k in ('slot', 'components', 'children') if k in inner}
    assets = copy.deepcopy(bundle.get('assets', {}))
    for asset in assets.values():
        name = asset.get('source')
        if not isinstance(name, str) or not name or Path(name).is_absolute() or not (source.resolve() / name).resolve().is_relative_to(source.resolve()):
            raise ValueError(f'asset path escapes source bundle: {name}')
        if not (source / name).is_file():
            raise ValueError(f'asset missing: {name}')
        asset['source'] = os.path.relpath((source / name).resolve(), output.parent.resolve())
    result: Manifest = {
        'schemaVersion': bundle['schemaVersion'], 'ownership': {'key': 'slum03'},
        'slot': {'key': 'root', 'name': 'Slum03_Slum', 'parent': 'Root', 'position': list(root_position)},
        'assets': assets, 'components': [],
        'children': [{'slot': {'key': 'blockout-preview', 'name': 'ResoLoop_Test_Slum03_Blockout'},
                      'components': [], 'children': [inner]}],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result
