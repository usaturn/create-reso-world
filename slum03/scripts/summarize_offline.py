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
            if placement is None:
                raise ValueError(f'unattributed native {kind}: {key}')
            counts[placement.sector][kind] += 1
    return counts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--first', required=True)
    p.add_argument('--second', required=True)
    args = p.parse_args()
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
    native_by_sector = native_sector_counts(manifest, read_layout(Path('content/slum03/layout.json')))
    for sector in SECTORS:
        rows[sector].update(native_by_sector[sector])
        rows[sector]['transparentDrawSections'] = None  # shared native providers; real overdraw unmeasured
    components = Counter(c['type'] for n in walk(manifest) for c in n.get('components', []))
    totals = {key: sum(row[key] for row in rows.values()) for key in
              ('triangles', 'vertices', 'materials', 'drawSections', 'meshes', 'textures', 'lights', 'colliders', 'advisoryWarnings')}
    output = {'status': 'OFFLINE CANDIDATE', 'sourceRuns': [args.first, args.second],
              'comparison': {'status': 'pass', 'separatelyBuiltAndExported': True,
                             'meshCount': totals['meshes'], 'numericRounding': False,
                             'fields': ['position', 'normal', 'tangent', 'uvs', 'color', 'submeshes']},
              'sectors': rows, 'exportTotals': totals, 'nativeComponentCounts': dict(sorted(components.items())),
              'transparentLayers': {'FresnelMaterialProviders': components['FrooxEngine.FresnelMaterial'],
                                    'measuredOverdraw': None},
              'currentReflectionValidated': False, 'liveApplied': False}
    destination = Path('artifacts/slum03') / args.first / 'asset-summary.json'
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'summary': str(destination), 'totals': totals}))


if __name__ == '__main__':
    main()
