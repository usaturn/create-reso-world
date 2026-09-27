"""Merge offline ResoLoop exports below one slum03-owned root; never touch live state.

CLI: uv run python -m modeling.slum03.pipeline --bundles content/slum03/bundles/REV
     --layout content/slum03/layout.json --root-y Y --output content/slum03/slum03.json
Bundle reports: <bundles>/<sector>/report.json (export), or
<bundles>/<sector>/<sector>-report.json (Blender build); the latter is preferred.
CLI writes <output.stem>-provenance.json beside output: OFFLINE CANDIDATE only.
Current Reflection, runtime type validation and live QA are *not* performed here.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Mapping

from .layout import read_layout
from .postprocess import postprocess
from .sectors import SECTORS
from .types import Layout, Manifest, Report, Vec3

_REF = re.compile(r'^\$(asset|component|slot|member|slot-member):([^.$\s]+)(?:\.([^.$\s]+))?$')


def _claim(key: str, sector: str, used: set[str]) -> str:
    candidate = key
    while candidate in used:
        candidate = f'{sector}-{candidate}'
    used.add(candidate)
    return candidate


def _walk(node: dict):
    yield node
    for child in node.get('children', []):
        yield from _walk(child)


def _refs(value: Any):
    if isinstance(value, str):
        if value.startswith('$'):
            match = _REF.fullmatch(value)
            if not match or ((match[1] in ('member', 'slot-member')) != (match[3] is not None)):
                raise ValueError(f'malformed reference: {value}')
            yield match
    elif isinstance(value, list):
        for item in value:
            yield from _refs(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _refs(item)


def _rewrite(value: Any, maps: dict[str, dict[str, str]]) -> Any:
    if isinstance(value, str) and value.startswith('$'):
        match = next(_refs(value))
        kind, key, member = match.groups()
        mapped = maps[kind][key]  # already checked against local bundle declarations
        return f'${kind}:{mapped}' + (f'.{member}' if member else '')
    if isinstance(value, list):
        return [_rewrite(item, maps) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite(item, maps) for key, item in value.items()}
    return value


def _asset_file(directory: Path, source: Any) -> Path:
    if not isinstance(source, str) or not source or '://' in source or '\\' in source:
        raise ValueError(f'invalid asset source: {source}')
    path = Path(source)
    if path.is_absolute() or any(part in ('..', '.') for part in path.parts):
        raise ValueError(f'asset source escapes bundle: {source}')
    resolved = (directory / path).resolve()
    if not resolved.is_relative_to(directory.resolve()) or not resolved.is_file():
        raise ValueError(f'missing or external asset source: {source}')
    return resolved


def _validate_local(bundle: dict, directory: Path) -> tuple[list[dict], dict[str, Path]]:
    if not isinstance(bundle, dict) or set(bundle) != {
            'schemaVersion', 'ownership', 'slot', 'assets', 'components', 'children'}:
        raise ValueError(f'unexpected bundle document keys: {directory}')
    if (bundle.get('schemaVersion') != '1' or bundle.get('slot', {}).get('key') != 'root' or
            bundle['slot'].get('parent') != 'Root' or
            not isinstance(bundle.get('ownership', {}).get('key'), str) or
            not bundle['ownership']['key'].startswith('blender_') or bundle.get('components')):
        raise ValueError(f'unexpected bundle ownership/root structure: {directory}')
    nodes = list(_walk(bundle))
    slots: set[str] = set()
    components: set[str] = set()
    for node in nodes:
        if node is not bundle and (not isinstance(node, dict) or not set(node) <= {'slot', 'components', 'children'}):
            raise ValueError(f'unexpected bundle node keys: {directory}')
        slot = node.get('slot', {})
        key = slot.get('key')
        if not isinstance(key, str) or not key or key in slots or (node is not bundle and key == 'root'):
            raise ValueError(f'duplicate or invalid slot key: {key}')
        slots.add(key)
        for component in node.get('components', []):
            ck = component.get('key')
            if not isinstance(ck, str) or not ck or ck in components or ck in slots:
                raise ValueError(f'duplicate or invalid component key: {ck}')
            components.add(ck)
    if slots & components:
        raise ValueError(f'slot/component key conflict: {slots & components}')
    assets = bundle.get('assets', {})
    if not isinstance(assets, dict):
        raise ValueError('invalid assets')
    files = {key: _asset_file(directory, entry.get('source')) for key, entry in assets.items()}
    for node in nodes:
        parent = node.get('slot', {}).get('parent')
        if node is not bundle and parent is not None and parent != '$slot:root':
            # Explicit local parent pointers are allowed, but never external/root literal.
            if not isinstance(parent, str) or not parent.startswith('$slot:') or parent[6:] not in slots:
                raise ValueError(f'foreign parent: {parent}')
        for ref in _refs(node):
            kind, key, _ = ref.groups()
            declared = {'asset': assets, 'slot': slots, 'slot-member': slots,
                        'component': components, 'member': components}[kind]
            if key not in declared:
                raise ValueError(f'foreign or unresolved reference: {ref.group()}')
    for entry in assets.values():
        for ref in _refs(entry):
            kind, key, _ = ref.groups()
            declared = {'asset': assets, 'slot': slots, 'slot-member': slots,
                        'component': components, 'member': components}[kind]
            if key not in declared:
                raise ValueError(f'foreign or unresolved reference: {ref.group()}')
    return nodes, files


def merge_bundles(bundle_dir: Path) -> Manifest:
    """Merge every canonical sector; source paths remain relative to bundle_dir."""
    bundle_dir = Path(bundle_dir).resolve()
    used = {'root'}
    used_assets: set[str] = set()
    assets: dict[str, dict] = {}
    asset_signatures: dict[str, dict[tuple[str, str], str]] = {}
    material_signatures: dict[str, dict[str, str]] = {}
    children = []
    for sector in SECTORS:
        directory = bundle_dir / sector
        source = directory / 'model.apply.json'
        if not source.is_file() or not directory.resolve().is_relative_to(bundle_dir):
            raise ValueError(f'missing sector bundle: {source}')
        bundle = json.loads(source.read_text(encoding='utf-8'))
        nodes, files = _validate_local(bundle, directory)
        asset_keys = {}
        for key, asset in bundle['assets'].items():
            if not isinstance(key, str) or not key or not isinstance(asset, dict):
                raise ValueError(f'invalid asset key or entry: {key}')
            signature = (json.dumps({k: v for k, v in asset.items() if k != 'source'}, sort_keys=True),
                         hashlib.sha256(files[key].read_bytes()).hexdigest())
            reused = asset_signatures.get(key, {}).get(signature)
            if reused is not None:
                asset_keys[key] = reused
                continue
            final = _claim(key, sector, used_assets)
            asset_keys[key] = final
            asset_signatures.setdefault(key, {})[signature] = final
            assets[final] = {**asset, 'source': files[key].relative_to(bundle_dir).as_posix()}
        sector_key = _claim(f'sector-{sector}', sector, used)
        slot_keys = {'root': sector_key}
        for node in nodes[1:]:
            original = node['slot']['key']
            slot_keys[original] = _claim(original, sector, used)
        # Claim all non-provider component keys first. Identity of a renderer
        # depends on its mesh and materials; it is never safe to reuse by key.
        component_keys = {}
        for node in nodes[1:]:
            for component in node.get('components', []):
                key = component['key']
                if component.get('type') != 'FrooxEngine.PBS_Metallic':
                    component_keys[key] = _claim(key, sector, used)
        for node in nodes[1:]:
            for component in node.get('components', []):
                key = component['key']
                if component.get('type') != 'FrooxEngine.PBS_Metallic':
                    continue
                # Local references can spell the same but point to different
                # sector components/assets. Do not share reference-bearing
                # material declarations without proving target identity.
                identity = json.dumps(component, sort_keys=True, ensure_ascii=False)
                has_refs = any(_refs(component.get('fields', {})))
                reused = None if has_refs else material_signatures.get(key, {}).get(identity)
                if reused is not None:
                    component_keys[key] = reused
                else:
                    final = _claim(key, sector, used)
                    component_keys[key] = final
                    if not has_refs:
                        material_signatures.setdefault(key, {})[identity] = final
        maps = {'asset': asset_keys, 'slot': slot_keys, 'slot-member': slot_keys,
                'component': component_keys, 'member': component_keys}
        emitted = []
        def emit(node):
            original = node['slot']['key']
            result = copy.deepcopy(node)
            result['slot']['key'] = slot_keys[original]
            if 'parent' in result['slot']:
                result['slot']['parent'] = _rewrite(result['slot']['parent'], maps)
            result['components'] = []
            for component in node.get('components', []):
                final = component_keys[component['key']]
                if final in declared_components:
                    continue  # identical material provider; keep its unique slot
                clone = _rewrite(component, maps)
                clone['key'] = final
                result['components'].append(clone)
                declared_components.add(final)
            result['children'] = [emit(child) for child in node.get('children', [])]
            return result
        # The sector root itself is replaced by a dedicated stable slot.
        declared_components = {c['key'] for n in children for sub in _walk(n) for c in sub.get('components', [])}
        emitted = [emit(node) for node in bundle.get('children', [])]
        children.append({'slot': {'key': sector_key, 'name': 'Slum03_' + ''.join(
            word.capitalize() for word in sector.split('-')),
            'position': [0, 0, 0], 'rotation': [0, 0, 0, 1], 'scale': [1, 1, 1]},
            'components': [], 'children': emitted})
    return {'schemaVersion': '1', 'ownership': {'key': 'slum03'},
            'slot': {'key': 'root', 'name': 'Slum03_Slum', 'parent': 'Root',
                     'position': [0, 0, 0], 'rotation': [0, 0, 0, 1], 'scale': [1, 1, 1]},
            'assets': assets, 'components': [], 'children': children}


def _validate_final(manifest: Manifest) -> None:
    """Every owned reference must resolve inside this document, not in Root/elsewhere."""
    nodes = list(_walk(manifest))
    slots = [n['slot']['key'] for n in nodes]
    components = [c['key'] for n in nodes for c in n.get('components', [])]
    if (manifest.get('ownership') != {'key': 'slum03'} or
            manifest['slot'].get('key') != 'root' or
            manifest['slot'].get('name') != 'Slum03_Slum' or
            manifest['slot'].get('parent') != 'Root' or
            len(slots + components) != len(set(slots + components))):
        raise ValueError('foreign ownership or duplicate stable key')
    targets = {'asset': manifest['assets'], 'slot': slots, 'slot-member': slots,
               'component': components, 'member': components}
    for ref in _refs(manifest):
        kind, key, _ = ref.groups()
        if key not in targets[kind]:
            raise ValueError(f'foreign or unresolved reference: {ref.group()}')


def _count(value: Any) -> int:
    return 1 + (sum(_count(v) for v in value.values()) if isinstance(value, dict)
                else sum(_count(v) for v in value) if isinstance(value, list) else 0)


def build_unified_manifest(bundle_dir: Path, layout: Layout,
                           reports: Mapping[str, Report], root_position: Vec3) -> Manifest:
    """Resolve asset paths, then invoke Task 9 native postprocess exactly once."""
    base = Path(bundle_dir).resolve()
    merged = merge_bundles(base)
    for asset in merged['assets'].values():
        asset['source'] = str((base / asset['source']).resolve())
    result = postprocess(merged, layout, reports, root_position)
    _validate_final(result)
    result['limits'] = {'expandedNodes': math.ceil(_count(result) * 1.2)}
    return result


def write_unified_manifest(manifest: Manifest, output: Path) -> None:
    """Write output-relative assets without mutating manifest or accessing live content."""
    output = Path(output)
    if 'slot' in manifest:
        _validate_final(manifest)
    result = copy.deepcopy(manifest)
    for asset in result.get('assets', {}).values():
        source = asset.get('source')
        if not isinstance(source, str) or not Path(source).is_absolute():
            raise ValueError(f'invalid absolute asset source: {source}')
        path = Path(source).resolve()
        if not path.is_file():
            raise ValueError(f'external or missing asset source: {source}')
        asset['source'] = os.path.relpath(path, output.parent.resolve())
    result.pop('limits', None)
    result['limits'] = {'expandedNodes': math.ceil(_count(result) * 1.2)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _reports(directory: Path) -> dict[str, Report]:
    result = {}
    for sector in SECTORS:
        paths = (directory / sector / f'{sector}-report.json', directory / sector / 'report.json')
        path = next((p for p in paths if p.is_file()), None)
        if path is None:
            raise ValueError(f'missing sector report: {sector}; expected {paths[0]} or {paths[1]}')
        report = json.loads(path.read_text(encoding='utf-8'))
        if report.get('errors') or report.get('sector', sector) != sector:
            raise ValueError(f'invalid sector report: {path}')
        result[sector] = report
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundles', type=Path, required=True)
    parser.add_argument('--layout', type=Path, required=True)
    parser.add_argument('--root-y', type=float, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = build_unified_manifest(args.bundles, read_layout(args.layout),
                                      _reports(args.bundles), (0, args.root_y, 0))
    write_unified_manifest(manifest, args.output)
    report = {'status': 'OFFLINE CANDIDATE', 'currentReflectionValidated': False,
              'liveApplied': False, 'typeProvenance': 'modeling/slum03/native/* (ported slum02 templates)',
              'bundles': str(args.bundles), 'layout': str(args.layout),
              'rootPosition': [0, args.root_y, 0]}
    args.output.with_name(args.output.stem + '-provenance.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
