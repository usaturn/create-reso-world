"""Write measured offline metrics and independent export comparison evidence.

uv run python scripts/summarize_offline.py --first task11-c-... --second task11-d-...
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modeling.slum03.sectors import SECTORS
from modeling.slum03.layout import read_layout
from modeling.slum03.density_metrics import layout_digest
from modeling.slum03.native.common import walk
from modeling.slum03.verify_assets import compare_geometry_exports


def native_sector_counts(manifest, layout):
    """Attribute native lights/colliders to the longest owned placement prefix."""
    counts = {sector: {'lights': 0, 'colliders': 0} for sector in SECTORS}
    placements = sorted(layout.placements, key=lambda p: len(p.key), reverse=True)
    for node in walk(manifest):
        key = node.get('slot', {}).get('key', '')
        for component in node.get('components', []):
            kind = {'FrooxEngine.Light': 'lights', 'FrooxEngine.BoxCollider': 'colliders'}.get(component['type'])
            if kind is None:
                continue
            prefix = 'local-light-' if kind == 'lights' else 'collider-'
            owner = key.removeprefix(prefix)
            placement = next((p for p in placements if owner == p.key or owner.startswith(p.key + '-')), None)
            if placement is None and kind == 'lights' and owner.startswith('cluster-'):
                placement = _cluster_member(layout, owner)
            if placement is None:
                raise ValueError(f'unattributed native {kind}: {key}')
            counts[placement.sector][kind] += 1
    return counts


def _cluster_member(layout, owner):
    """Full-stage cluster light 'cluster-<kind>-<cluster>' -> first member placement."""
    members = sorted((p for p in layout.placements
                      if owner == f"cluster-{p.kind}-{p.params.get('cluster')}"), key=lambda p: p.key)
    return members[0] if members else None


def full_gate(layout, runs, first_bundles):
    """Full stage only: per-zone resources, export/candidate provenance and Gate C status."""
    from modeling.slum03.density_metrics import zone_resources
    from modeling.slum03.density_candidate import (gate_c_status, inventory_issues,
                                                   regeneration_issues)
    from modeling.slum03.verify_assets import export_count_issues
    density_issues, structural = [], []
    evidence = {}
    for run in runs:
        artifact = Path('artifacts/slum03') / run
        bundles = Path('content/slum03/bundles') / run
        candidate = Path('content/slum03') / f'{run}-candidate.json'
        reports = {sector: json.loads((artifact / f'{sector}-report.json').read_text()) for sector in SECTORS}
        density = json.loads((artifact / 'density-report.json').read_text())
        scope = json.loads((artifact / 'scope-report.json').read_text())
        manifest = json.loads(candidate.read_text())
        density_issues += [{**i, 'run': run} for i in density['issues']]
        if density.get('stage') != 'full' or density.get('layout_sha256') != layout_digest(layout):
            density_issues.append({'code': 'DENSITY_STAGE', 'object_key': run, 'message': 'not a full report of this Layout'})
        structural += [{'code': i.code, 'object_key': i.object_key, 'message': i.message, 'run': run}
                       for i in (export_count_issues(reports, bundles) +
                                 inventory_issues(scope.get('candidate_inventory', {}), candidate) +
                                 regeneration_issues(manifest, layout, run))]
        structural += [{**i, 'run': run} for i in scope['issues']]
        if scope.get('protected_changes') != 0:
            structural.append({'code': 'SCOPE', 'object_key': run, 'message': 'protected changes recorded'})
        evidence[run] = {'candidate': str(candidate), 'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
                         'absent_baseline_slots': scope.get('absent_baseline_slots'),
                         'density_counts': density.get('counts')}
    manifest = json.loads((Path('content/slum03') / f'{runs[0]}-candidate.json').read_text())
    exports = {sector: json.loads((first_bundles / sector / 'report.json').read_text()) for sector in SECTORS}
    zones = zone_resources(layout, manifest, exports)
    if any(zones['unattributed'][f] for f in ('meshes', 'lights', 'colliders', 'drivers')):
        structural.append({'code': 'RESOURCE_UNATTRIBUTED', 'object_key': 'zones',
                           'message': json.dumps(zones['unattributed'])})
    return {'zones': zones, 'runs': evidence,
            'gate_c': gate_c_status(density_issues=density_issues, structural_issues=structural)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--first', required=True)
    p.add_argument('--second', required=True)
    p.add_argument('--layout', type=Path, required=True)
    args = p.parse_args()
    saved = args.layout.read_bytes()
    layout = read_layout(args.layout)
    for run in (args.first, args.second):
        copy = Path('artifacts/slum03') / run / 'layout.json'
        if copy.read_bytes() != saved or layout_digest(read_layout(copy)) != layout_digest(layout):
            raise ValueError(f'Layout bytes/digest differ: {copy}')
    first = Path('content/slum03/bundles') / args.first
    second = Path('content/slum03/bundles') / args.second
    issues = compare_geometry_exports(first, second)
    if issues:
        raise ValueError(f'independent exports differ: {[vars(i) for i in issues[:10]]}')
    rows = {}
    for sector in SECTORS:
        report = json.loads((first / sector / 'report.json').read_text())
        rows[sector] = {key: report[key] for key in ('triangles', 'vertices', 'materials', 'drawSections')}
        rows[sector].update(meshes=len(report['meshes']), textures=len(report['textures']),
                            advisoryWarnings=len(report['warnings']))
        digest = hashlib.sha256()
        for path in sorted((first / sector).glob('*.mesh.json')):
            # Compare decoded JSON (not timestamps/formatting), without rounding floats.
            mesh = json.loads(path.read_text())
            digest.update(path.name.encode())
            digest.update(json.dumps(mesh, sort_keys=True, separators=(',', ':')).encode())
        rows[sector]['geometrySha256'] = digest.hexdigest()
    manifest = json.loads((Path('content/slum03') / f'{args.first}-candidate.json').read_text())
    native_by_sector = native_sector_counts(manifest, layout)
    for sector in SECTORS:
        rows[sector].update(native_by_sector[sector])
        rows[sector]['transparentDrawSections'] = None  # shared native providers; real overdraw unmeasured
    components = Counter(c['type'] for n in walk(manifest) for c in n.get('components', []))
    totals = {key: sum(row[key] for row in rows.values()) for key in
              ('triangles', 'vertices', 'materials', 'drawSections', 'meshes', 'textures', 'lights', 'colliders', 'advisoryWarnings')}
    output = {'status': 'OFFLINE CANDIDATE', 'sourceRuns': [args.first, args.second], 'layout': {'path': str(args.layout), 'sha256': hashlib.sha256(saved).hexdigest(), 'semantic_sha256': layout_digest(layout)},
              'comparison': {'status': 'pass', 'separatelyBuiltAndExported': True,
                             'meshCount': totals['meshes'], 'numericRounding': False,
                             'fields': ['position', 'normal', 'tangent', 'uvs', 'color', 'submeshes']},
              'sectors': rows, 'exportTotals': totals, 'nativeComponentCounts': dict(sorted(components.items())),
              'transparentLayers': {'FresnelMaterialProviders': components['FrooxEngine.FresnelMaterial'],
                                    'measuredOverdraw': None},
              'currentReflectionValidated': False, 'liveApplied': False}
    if layout.density is not None and layout.density.stage == 'full':
        output.update(full_gate(layout, (args.first, args.second), first))
    destination = Path('artifacts/slum03') / args.first / 'asset-summary.json'
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'summary': str(destination), 'totals': totals,
                      **({'gate_c': output['gate_c']['status']} if 'gate_c' in output else {})}))


if __name__ == '__main__':
    main()
