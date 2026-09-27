"""Repeatable full slum03 offline build/export/merge; no Resonite connection or live writes.

Run from slum03/: uv run python scripts/build_offline.py --run task11-UNIQUE
Re-run with a different --run for independent geometry comparison. Each command
runs synchronously with a deadline. Never overwrite existing builds or bundles.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modeling.slum03.sectors import SECTORS
from modeling.slum03.layout import read_layout
from modeling.slum03.verify_assets import verify_assets
from modeling.slum03.postprocess import choose_root_y
from modeling.slum03.pipeline import build_unified_manifest, write_unified_manifest


def command(*args, timeout=240):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{args}: {result.returncode}\n{result.stdout[-3000:]}\n{result.stderr[-3000:]}')
    return result.stdout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True)
    args = p.parse_args()
    if not args.run or '/' in args.run or args.run in ('.', '..'):
        raise ValueError('run must be a unique single directory name')
    artifact = Path('artifacts/slum03') / args.run
    bundles = Path('content/slum03/bundles') / args.run
    if artifact.exists() or bundles.exists():
        raise FileExistsError(f'run output already exists: {artifact} or {bundles}')
    # Preserve any older flat source before generating a new run (without modifying it).
    previous = Path('artifacts/slum03')
    originals = [previous / f'{s}.blend' for s in SECTORS if (previous / f'{s}.blend').exists()]
    if originals:
        backup = Path('.resoloop/slum03/backups') / args.run
        if backup.exists():
            raise FileExistsError(backup)
        backup.mkdir(parents=True)
        for path in originals:
            shutil.copy2(path, backup / path.name)
    artifact.mkdir(parents=True)
    bundles.mkdir(parents=True)
    layout = read_layout(Path('content/slum03/layout.json'))
    reports = {}
    for sector in SECTORS:
        output = artifact / f'{sector}.blend'
        command('resoloop', '--command-timeout', '180', 'blender', 'run', 'modeling/slum03/build.py',
                '--arg=--sector', f'--arg={sector}', '--arg=--output', f'--arg={output}', '--json', timeout=200)
        report = json.loads((artifact / f'{sector}-report.json').read_text(encoding='utf-8'))
        reports[sector] = report
        if report['errors'] or not output.is_file():
            raise ValueError(f'build failed: {sector}')
    issues = verify_assets(layout, reports)
    if issues:
        raise ValueError(f'build verification failed: {[vars(i) for i in issues]}')
    for sector in SECTORS:
        report = reports[sector]
        destination = bundles / sector
        command('resoloop', '--command-timeout', '240', 'blender', 'export',
                str(artifact / f'{sector}.blend'), '--output', str(destination),
                '--parent', 'Root', '--name', f'Slum03_{sector}',
                '--collection', report['export_collection'], '--preserve-hierarchy', '--json', timeout=260)
        if not (destination / 'report.json').is_file() or not list(destination.glob('*.mesh.json')):
            raise ValueError(f'incomplete sector export: {sector}')
    y = choose_root_y(0, reports['road-river']['evaluated_bounds']['river']['minimum'][1])
    manifest = build_unified_manifest(bundles, layout, reports, (0, y, 0))
    output = Path('content/slum03') / f'{args.run}-candidate.json'
    write_unified_manifest(manifest, output)
    provenance = {'status': 'OFFLINE CANDIDATE', 'currentReflectionValidated': False,
                  'liveApplied': False, 'bundles': str(bundles), 'rootPosition': [0, y, 0],
                  'layout': 'content/slum03/layout.json'}
    output.with_name(output.stem + '-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps({'artifacts': str(artifact), 'bundles': str(bundles),
                      'manifest': str(output), 'rootY': y,
                      'triangles': sum(r['triangles'] for r in reports.values()),
                      'vertices': sum(r['vertices'] for r in reports.values()),
                      'submeshes': sum(r['submeshes'] for r in reports.values())}))


if __name__ == '__main__':
    main()
