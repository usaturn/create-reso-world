"""Sector .blend builder. Run: resoloop blender run modeling/slum02/build.py --arg=--sector --arg=ground --arg=--output --arg=artifacts/slum02/ground.blend --json"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modeling.slum02 import SEED  # noqa: E402
from modeling.slum02 import sectors as S  # noqa: E402
from modeling.slum02.geometry import merge_assembly  # noqa: E402
from modeling.slum02.layout import build_layout, validate_layout  # noqa: E402
from modeling.slum02.materials import make_blender_materials  # noqa: E402
from modeling.slum02.sectors import SECTORS, resource_report, sector_assemblies  # noqa: E402
from modeling.slum02.vcolor import vertex_colors  # noqa: E402


def _title(sector: str) -> str:
    return "".join(part.capitalize() for part in sector.split("-"))


def _reset(bpy) -> None:
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for m in [m for m in bpy.data.meshes if m.users == 0]:
        bpy.data.meshes.remove(m)


def write_scene(sector: str, output: Path, *, ao: bool = True, ao_samples: int = 16) -> dict:
    import bmesh
    import bpy
    from modeling.slum02 import blender_io as io

    if sector not in SECTORS or output.suffix != ".blend":
        raise ValueError("bad sector or output")
    data = build_layout()
    if issues := validate_layout(data):
        raise RuntimeError(f"layout invalid: {issues[:4]}")
    _reset(bpy)
    title = _title(sector)
    export = bpy.data.collections.new(f"Slum02{title}Export")
    bpy.context.scene.collection.children.link(export)
    lookup = make_blender_materials()
    assemblies = sector_assemblies(data, sector)
    report = resource_report(assemblies, sector)
    objects, uv_issues = [], 0
    for a in assemblies:
        merged = merge_assembly(a)
        obj, issues = io.create_object(bpy, bmesh, merged, a.origin, lookup, uv_exempt=a.meta.get("uv_exempt", False))
        io.write_colors(obj, vertex_colors(merged, a.origin, SEED + len(objects), a.meta.get("sprays", ())))
        obj["slum02_kind"] = a.kind
        obj["slum02_sector"] = sector
        export.objects.link(obj)
        objects.append(obj)
        uv_issues += issues
    # Optional sector hook (plaza GN scatter etc.) may add baked objects; sectors without one skip this.
    hook = S.BLENDER_HOOKS.get(sector)
    if hook:
        extra_objects, extra_report = hook(bpy, bmesh, data, lookup, export)
        objects += extra_objects
        report.update(extra_report)
    report["ao"] = io.bake_ao(bpy, objects, samples=ao_samples) if ao else {"baked": 0, "skipped": True}
    for obj in objects:
        io.combine_ao(obj)
    report["uv_issue_count"] = uv_issues
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(output.resolve()))
    col = bpy.data.collections.get(f"Slum02{title}Export")
    meshes = [o for o in col.objects if o.type == "MESH"]
    if len(meshes) != len(objects):
        raise RuntimeError(f"expected {len(objects)} meshes after reopen, got {len(meshes)}")
    for o in meshes:
        if not o.data.uv_layers or o.data.color_attributes.get("Col") is None or o.data.color_attributes.get("AO") is not None:
            raise RuntimeError(f"{o.name}: missing UV0/Col or leftover AO after reopen")
    report.update({"blend_path": str(output.resolve()), "blender_version": bpy.app.version_string,
                   "export_collection": col.name,
                   "triangles_blender": sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons)})
    (output.parent / f"{sector}-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sector", choices=SECTORS, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--no-ao", action="store_true")
    p.add_argument("--ao-samples", type=int, default=16, help="Cycles samples for the AO vertex bake (raise for large flats)")
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    print("SLUM02_SECTOR_REPORT=" + json.dumps(write_scene(args.sector, args.output, ao=not args.no_ao, ao_samples=args.ao_samples), ensure_ascii=False))


if __name__ == "__main__":
    main()
