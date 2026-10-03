"""Inspect saved/reopened full preview scene, not a single isolated sector."""
import bpy
from pathlib import Path
import json
import sys

report = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text())
assert all(report['visibility']['pass'].values())
assert len([o for o in bpy.context.scene.objects if o.type == 'MESH']) == report['visibility']['meshCount']
assert len([o for o in bpy.context.scene.objects if o.type == 'CAMERA']) == len(report['cameras'])
assert len([o for o in bpy.context.scene.objects if o.type == 'FONT' and o.name.endswith('-preview')]) == report['labels']
assert not any(o.name.endswith('_Source') for o in bpy.context.scene.objects)
print(json.dumps({'savedScene': bpy.data.filepath, 'cameras': len(report['cameras']), 'meshes': report['visibility']['meshCount'], 'labels': report['labels']}))
