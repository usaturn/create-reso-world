"""Build all sectors from a saved density Layout, compose a protected offline candidate."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_offline import build_raw_run
from modeling.slum03.density_candidate import prepare, finalize
from modeling.slum03.density_views import write_review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('representative', 'full', 'blockout'), required=True)
    parser.add_argument('--base-manifest', type=Path, required=True)
    parser.add_argument('--layout', type=Path, required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--root-y', type=float, required=True)
    args = parser.parse_args()
    prepare(args.stage, args.base_manifest, args.layout, args.run, args.root_y)
    artifact, bundles, reports, manifest, y = build_raw_run(args.run, args.layout, root_y=args.root_y)
    result = finalize(args.stage, args.base_manifest, args.layout, args.run, y,
                      artifact, bundles, manifest)
    source = Path(result['candidate'])
    review = source.with_name(f'{args.run}-review-candidate.json')
    scope = write_review(source, artifact / 'layout.json', review, artifact / f'{args.stage}-review')
    result['review_candidate'] = str(review)
    result['review_sha256'] = scope['candidate_sha256']
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
