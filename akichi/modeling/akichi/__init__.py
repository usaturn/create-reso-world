"""Akichi cyberpunk slum generator: layout -> Blender sectors -> Resonite bundles.

pytest covers the pure Python layers only (``cd akichi && uv run pytest
tests/akichi/ -q``); the Blender side is smoke-checked by hand, e.g. after a
Blender version change. Rebuild one sector into a scratch directory, compare the
geometry digests of ``tmp/smoke/ground-report.json`` (``total_vertices`` /
``total_triangles`` / ``uv_issue_count``) against the committed
``artifacts/akichi/ground-report.json``, then re-export and validate offline::

    resoloop blender run modeling/akichi/build.py --arg=--sector --arg=ground \
      --arg=--output --arg=tmp/smoke/ground.blend --json
    resoloop blender export tmp/smoke/ground.blend \
      --output tmp/smoke/ground-v1 --name Ground --collection AkichiGroundExport --json
    resoloop validate tmp/smoke/ground-v1/model.apply.json --json

Outputs stay under the gitignored ``tmp/`` so the committed ``artifacts/`` and
``content/`` files are never overwritten; only the geometry digests are
comparable (the .blend bytes embed Blender-internal pointers and are not
byte-stable).
"""
