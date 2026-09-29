"""Fail-closed offline density candidate build; no state, promotion or live calls."""
from __future__ import annotations

import hashlib
import json
import math
import copy
import os
from pathlib import Path

from .candidate_scope import (compose_candidate, check_candidate_scope, _file, _index,
                              _reachable_components, _selected_roots, _MATERIAL_TYPES)
from .density_metrics import density_report, layout_digest
from .layout import read_layout
from .pipeline import _reports, _count, merge_bundles, _refs
from .verify_assets import verify_assets
from .types import Issue


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_export_sources(assets: dict, bundles: Path, manifest_dir: Path) -> dict:
    """Use exporter declarations and inventory, not the draft's self-reported sources."""
    bundles = Path(bundles).resolve()
    manifest_dir = Path(manifest_dir).resolve()
    if not bundles.is_relative_to(manifest_dir / 'bundles'):
        raise ValueError(f'export directory outside manifest bundles: {bundles}')
    merged = merge_bundles(bundles)
    if set(assets) != set(merged['assets']):
        raise ValueError('draft asset keys differ from current export declarations')
    inventory = {}
    for sector_dir in bundles.iterdir():
        if not sector_dir.is_dir():
            continue
        path = sector_dir / 'report.json'
        report = json.loads(path.read_text(encoding='utf-8'))
        inventory[sector_dir.name] = {item['file'] for item in report['meshes']}
    result = {}
    for key, declared in merged['assets'].items():
        file = bundles / declared['source']
        source = file.relative_to(manifest_dir).as_posix()
        actual = assets[key]
        if actual != {**declared, 'source': source}:
            raise ValueError(f'draft source/declaration differs from current export: {key}: {actual.get("source")} != {source}')
        sector, filename = Path(declared['source']).parts[0], Path(declared['source']).name
        if declared['kind'] == 'mesh' and filename not in inventory.get(sector, set()):
            raise ValueError(f'export mesh file absent from inventory: {sector}/{filename}')
        result[key] = {'source': source, 'file': str(file), 'sha256': sha(file),
                       'export_declaration': str(bundles / sector / 'model.apply.json'),
                       'export_inventory': str(bundles / sector / 'report.json')}
    return result


def prune_unmoved_reuse_stubs(raw: dict, baseline: dict, layout) -> tuple[dict, list[dict]]:
    """Remove only exporter-empty reuse slots for *unmoved* identical old materials.

    Relocated providers and their empty slots remain for R8's separate strict audit.
    The original regenerated manifest and bundle declarations are never modified.
    """
    result = copy.deepcopy(raw)
    old_nodes, old_comps = _index(baseline)
    new_nodes, new_comps = _index(result)
    selected_roots = _selected_roots(old_nodes, new_nodes, layout)
    selected_refs = _reachable_components(new_nodes, new_comps, selected_roots)
    evidence = []
    for key, (node, parent) in list(new_nodes.items()):
        if key in old_nodes or not parent or 'blender_providers' not in parent:
            continue
        comp_key = node['slot'].get('name')
        if key != parent.removesuffix('-blender_providers') + '-provider_' + str(comp_key):
            continue
        provider_key = 'provider_' + str(comp_key)
        provider = old_nodes.get(provider_key)
        current = new_nodes.get(provider_key)
        if (not provider or not current or provider[1] != current[1] or
                provider[0] != current[0] or
                len(provider[0].get('components', [])) != 1 or
                provider[0]['components'][0]['key'] != comp_key or
                provider[0]['components'][0]['type'] not in _MATERIAL_TYPES or
                comp_key not in selected_refs or node.get('components') or node.get('children')):
            continue
        if any(ref[1] in ('slot', 'slot-member') and ref[2] == key for ref in _refs(raw)):
            raise ValueError(f'referenced empty provider stub cannot be removed: {key}')
        new_nodes[parent][0]['children'].remove(node)
        evidence.append({'slot': key, 'unchanged_provider': provider_key,
                         'material_component': comp_key, 'parent': parent,
                         'unchanged_provider_parent': provider[1],
                         'reason': 'exporter emitted an unreferenced empty reuse slot; identical material did not relocate'})
    return result, evidence


def prepare(stage: str, baseline: Path, source: Path, run: str, root_y: float):
    if stage not in ('representative', 'full'):
        raise ValueError('blockout is not a density candidate stage')
    if not run or run in ('.', '..') or '/' in run or '\\' in run:
        raise ValueError('run must be a unique single directory name')
    if not math.isfinite(root_y) or root_y != 4.5:
        raise ValueError('root position must remain [0, 4.5, 0]')
    layout = read_layout(source)
    if not layout.density or layout.density.stage != stage:
        raise ValueError('stage does not match saved Layout')
    if stage == 'representative' and set(layout.density.selected_keys) != {'ruin-west', 'shack-row', 'market-west'}:
        raise ValueError('representative layout must select precisely the three protected placements')
    if baseline.parent.resolve() != Path('content/slum03').resolve():
        raise ValueError('baseline must remain beside canonical manifest')
    if not baseline.is_file():
        raise FileNotFoundError(baseline)
    if any(p.exists() for p in (Path('artifacts/slum03') / run,
                                 Path('content/slum03/bundles') / run,
                                 Path('content/slum03') / f'{run}-candidate.json',
                                 Path('content/slum03') / f'{run}-raw-draft.json')):
        raise FileExistsError(f'run already exists: {run}')
    return layout


def finalize(stage: str, baseline: Path, source: Path, run: str, root_y: float,
             artifact: Path, bundles: Path, manifest: dict, *, suffix: str = '') -> dict:
    """Write raw draft, independently validate evaluated assets and protect baseline."""
    from .pipeline import write_unified_manifest
    layout_path = artifact / 'layout.json'
    layout = read_layout(layout_path)
    if layout.density is None or layout.density.stage != stage:
        raise ValueError('copied Layout changed stage')
    reports = _reports(artifact, layout, bundles)
    if verify_assets(layout, reports):
        raise ValueError('evaluated assets invalid')
    if stage == 'full':
        from .verify_assets import export_count_issues
        exported = export_count_issues(reports, bundles)
        if exported:
            raise ValueError(f'export inventory differs from evaluated build: {exported[:5]}')
    report = density_report(layout, reports, 'evaluated')
    if report['issues']:
        raise ValueError(f'evaluated density failed: {report["issues"][:5]}')
    if suffix and (not suffix.startswith('-') or not suffix[1:].replace('-', '').isalnum()):
        raise ValueError('invalid fresh evidence suffix')
    draft = Path('content/slum03') / f'{run}-raw-draft{suffix}.json'
    candidate = Path('content/slum03') / f'{run}-candidate{suffix}.json'
    density_path = artifact / f'density-report{suffix}.json'
    scope_path = artifact / f'scope-report{suffix}.json'
    provenance_path = candidate.with_name(candidate.stem + '-provenance.json')
    if any(p.exists() for p in (candidate, density_path, scope_path, provenance_path)):
        raise FileExistsError('candidate/evidence already exists')
    manifest, removed_stubs = prune_unmoved_reuse_stubs(manifest, json.loads(baseline.read_text()), layout)
    if draft.exists():
        expected = copy.deepcopy(manifest)
        for asset in expected['assets'].values():
            asset['source'] = os.path.relpath(asset['source'], draft.parent.resolve())
        expected.pop('limits', None)
        expected['limits'] = {'expandedNodes': math.ceil(_count(expected) * 1.2)}
        if json.loads(draft.read_text()) != expected:
            raise ValueError('existing raw draft differs from current regenerated manifest')
    else:
        write_unified_manifest(manifest, draft)
    draft_data = json.loads(draft.read_text())
    export_sources = verify_export_sources(draft_data['assets'], bundles, draft.parent)
    scope = compose_candidate(baseline, draft, layout, candidate)
    result = json.loads(candidate.read_text())
    # Every resource must match the freshly exported run, including retained old sources.
    comparison = {}
    for key, asset in result['assets'].items():
        fresh = draft_data['assets'].get(key)
        if not fresh or {k: v for k, v in asset.items() if k != 'source'} != {k: v for k, v in fresh.items() if k != 'source'}:
            raise ValueError(f'no current export for candidate asset: {key}')
        old_source, old_hash = _file(candidate.parent, asset['source'])
        new_source, new_hash = _file(draft.parent, fresh['source'])
        if old_hash != new_hash or old_hash != export_sources[key]['sha256']:
            raise ValueError(f'candidate resource differs from new export: {key}')
        comparison[key] = {'candidate_source': old_source, 'draft_source': new_source,
                           'sha256': old_hash, 'origin': scope['asset_sources'][key]['origin'],
                           'export': export_sources[key]}
    issues = check_candidate_scope(json.loads(baseline.read_text()), result, layout, candidate.parent)
    if issues:
        raise ValueError(f'scope changed: {issues[:5]}')
    full_evidence = {}
    if stage == 'full':
        stale = regeneration_issues(result, layout, run)
        if stale:
            raise ValueError(f'selected content not regenerated by this run: {stale[:5]}')
        full_evidence = {'new_selected_nodes': scope['new_selected_nodes'],
                         'absent_baseline_slots': scope['absent_baseline_slots'],
                         'cluster_lights': scope['cluster_lights'],
                         'raw_absent_baseline_empty_provider_stubs': scope['raw_absent_baseline_empty_provider_stubs'],
                         'regeneration_issues': [],
                         'candidate_inventory': candidate_inventory(candidate)}
    report['references'] = {'layout': {'path': str(layout_path), 'sha256': sha(layout_path),
                                        'hash_basis': 'saved-file-bytes', 'semantic_sha256': layout_digest(layout)},
                            'build': {sector: {'path': str(artifact / f'{sector}-report.json'),
                                               'sha256': sha(artifact / f'{sector}-report.json')} for sector in reports},
                            'export': {sector: {'path': str(bundles / sector / 'report.json'),
                                                'sha256': sha(bundles / sector / 'report.json')} for sector in reports}}
    density_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    scope_path.write_text(json.dumps({'protected_changes': 0, 'protected_updates': 0, 'protected_deletes': 0, 'protected_asset_changes': 0, 'issues': [],
        'selected_nodes': scope['selected_nodes'],
        'raw_ignored_empty_provider_nodes': scope['raw_ignored_empty_provider_nodes'],
        'raw_material_relocations': scope['raw_material_relocations'],
        'raw_removed_unmoved_empty_provider_nodes': removed_stubs,
        **full_evidence,
        'asset_matches_new_export': comparison}, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    provenance = {'status': 'OFFLINE PROTECTED CANDIDATE', 'liveApplied': False,
                  'currentReflectionValidated': False, 'baseline': {'path': str(baseline), 'sha256': sha(baseline)},
                  'draft': {'path': str(draft), 'sha256': sha(draft)},
                  'candidate': {'path': str(candidate), 'sha256': sha(candidate)},
                  'layout': report['references']['layout'], 'rootPosition': [0, root_y, 0],
                  'object_sources': scope['object_sources'], 'asset_sources': comparison,
                  'raw_removed_unmoved_empty_provider_nodes': removed_stubs,
                  **({'candidate_inventory': full_evidence['candidate_inventory'],
                      'absent_baseline_slots': full_evidence['absent_baseline_slots']} if full_evidence else {})}
    provenance_path.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    return {'run': run, 'candidate': str(candidate), 'draft': str(draft), 'scope': str(scope_path),
            'assets': len(comparison), 'protected_changes': 0}


_INVENTORY_TYPES = {'mesh_renderers': 'FrooxEngine.MeshRenderer', 'static_meshes': 'FrooxEngine.StaticMesh',
                    'colliders': 'FrooxEngine.BoxCollider', 'lights': 'FrooxEngine.Light'}


def candidate_inventory(path: Path) -> dict:
    """Counts and hash measured from the written candidate bytes, never self-reported."""
    from collections import Counter
    from .candidate_scope import nodes
    path = Path(path)
    data = path.read_bytes()
    manifest = json.loads(data)
    items = nodes(manifest)
    types = Counter(c['type'] for node, _ in items.values() for c in node.get('components', []))
    result = {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
              'slots': len(items), 'components': sum(types.values()),
              'component_types': dict(sorted(types.items())),
              'assets': len(manifest.get('assets', {})),
              'mesh_assets': sum(1 for a in manifest.get('assets', {}).values() if a.get('kind') == 'mesh'),
              'cameras': len(manifest.get('cameras', {})), 'tests': len(manifest.get('tests', []))}
    result.update({name: types[kind] for name, kind in _INVENTORY_TYPES.items()})
    return result


def inventory_issues(recorded: dict, path: Path) -> list[Issue]:
    actual = candidate_inventory(path)
    return [Issue('INVENTORY_MISMATCH', key, f'recorded {recorded.get(key)!r} != actual {value!r}')
            for key, value in actual.items() if key != 'path' and recorded.get(key) != value]


def regeneration_issues(candidate: dict, layout, run: str) -> list[Issue]:
    """Every selected Slot must exist and render a mesh exported by *this* run."""
    from .candidate_scope import nodes, _asset_refs, _scatter_prefix
    from .density_model import SCATTER_PREFIXES
    items = nodes(candidate)
    assets = candidate.get('assets', {})
    issues = []
    def fresh(node):
        meshes = [assets.get(ref) for ref in _asset_refs(node)]
        meshes = [a for a in meshes if a is not None and a.get('kind') == 'mesh']
        return bool(meshes) and all(str(a.get('source', '')).startswith(f'bundles/{run}/') for a in meshes)
    for name in layout.density.selected_keys:
        if layout.density.stage == 'full' and name in SCATTER_PREFIXES:
            heaps = [n for n, _ in items.values() if _scatter_prefix(n['slot'].get('name'), layout) == name]
            if not heaps or not all(fresh(n) for n in heaps):
                issues.append(Issue('SELECTED_NOT_REGENERATED', name, 'scatter family missing or stale'))
            continue
        matches = [n for key, (n, _) in items.items()
                   if n['slot'].get('name') == name and not key.startswith('collider-')]
        if len(matches) != 1 or not fresh(matches[0]):
            issues.append(Issue('SELECTED_NOT_REGENERATED', name,
                                f'expected one Slot with a mesh from bundles/{run}/, found {len(matches)}'))
    return issues


def gate_c_status(*, density_issues: list, structural_issues: list) -> dict:
    """Offline adoption needs density/shape AND structure; human checks stay pending."""
    adoptable = not density_issues and not structural_issues
    return {'status': 'offline-adoptable-human-pending' if adoptable else 'offline-rejected',
            'adoptable': adoptable,
            'density': 'pass' if not density_issues else 'fail',
            'structure': 'pass' if not structural_issues else 'fail',
            'density_issues': list(density_issues), 'structural_issues': list(structural_issues),
            'visual': 'pending', 'walk': 'pending', 'save_reload': 'pending',
            'live_applied': False,
            'note': 'Offline evidence only; Blender images and structure do not replace in-world checks.'}
