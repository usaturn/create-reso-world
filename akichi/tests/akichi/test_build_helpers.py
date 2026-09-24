"""Task 6: unit tests for the pure-Python build helpers (build.py).

Utilities here cover the vertex-level batching, coordinate conversion and sector
assembly composition. `write_scene` and the Geometry Nodes scatter run inside
Blender (`bpy`) and are exercised by the Task 7 smoke via
``resoloop blender run modeling/akichi/build.py``.
"""
from __future__ import annotations

import math
from collections import Counter

from modeling.akichi import build, geometry
from modeling.akichi.buildings import Assembly
from modeling.akichi.layout import build_layout
from modeling.akichi.materials import MATERIALS


def test_resonite_to_blender_swaps_yz():
    assert build.resonite_to_blender((1, 2, 3)) == (1, 3, 2)


def test_batch_assembly_merges_by_material():
    from modeling.akichi.buildings import Assembly
    a = Assembly(kind="test", name="t1", origin=(0, 0, 0), rotation=0.0)
    a.parts.append(geometry.box("p1", (0, 0, 0), (1, 1, 1), "rust"))
    a.parts.append(geometry.box("p2", (2, 0, 0), (1, 1, 1), "rust"))
    a.parts.append(geometry.box("p3", (4, 0, 0), (1, 1, 1), "dark_metal"))
    batched = build.batch_assembly(a)
    assert set(batched) == {"t1__rust", "t1__dark_metal"}
    assert len(batched["t1__rust"].vertices) == 16
    assert len(batched["t1__rust"].faces) == 12


def test_batch_offset_is_correct():
    from modeling.akichi.buildings import Assembly
    a = Assembly(kind="test", name="t2", origin=(0, 0, 0), rotation=0.0)
    a.parts.append(geometry.box("p1", (0, 0, 0), (1, 1, 1), "rust"))
    a.parts.append(geometry.box("p2", (10, 0, 0), (1, 1, 1), "rust"))
    merged = build.batch_assembly(a)["t2__rust"]
    xs = [v[0] for v in merged.vertices]
    assert min(xs) == -0.5 and max(xs) == 10.5


def test_batch_assembly_bakes_rotation_and_origin():
    """Rotation (radians, Y up) and origin are applied once at batch time."""
    a = Assembly(kind="test", name="t3", origin=(10, 0, 0), rotation=math.radians(90))
    a.parts.append(geometry.box("p1", (0, 0, 0), (1, 1, 1), "rust"))
    merged = build.batch_assembly(a)["t3__rust"]
    xs = sorted({round(v[0], 9) for v in merged.vertices})
    zs = sorted({round(v[2], 9) for v in merged.vertices})
    assert (min(xs), max(xs)) == (9.5, 10.5)  # translated by origin
    assert min(zs) == -0.5 and max(zs) == 0.5  # 90 deg yaw keeps local extents


# --- sector composition -------------------------------------------------------


def test_towers_sector_has_all_ten_towers():
    data = build_layout()
    assemblies = build.build_sector_assemblies(data, "towers")
    assert len(assemblies) == 10
    assert {a.name for a in assemblies} == {t["id"] for t in data["towers"]}
    assert all(a.kind == "tower" for a in assemblies)


def test_market_sector_composition():
    data = build_layout()
    assemblies = build.build_sector_assemblies(data, "market")
    kinds = Counter(a.kind for a in assemblies)
    assert kinds == Counter({"stall": 12, "junk-pile": 12, "stall-pad": 12})


def test_shacks_sector_composition_and_cables():
    data = build_layout()
    assemblies = build.build_sector_assemblies(data, "shacks")
    kinds = Counter(a.kind for a in assemblies)
    assert kinds == Counter({"shack": 10, "junk-pile": 5, "cable": 4})
    cable_names = [a.name for a in assemblies if a.kind == "cable"]
    assert cable_names == [c["id"] for c in data["cables"][0:4]]


def test_nightlife_sector_composition():
    data = build_layout()
    assemblies = build.build_sector_assemblies(data, "nightlife")
    kinds = Counter(a.kind for a in assemblies)
    assert kinds == Counter({"club": 4, "ad": 3, "cable": 4})
    ads = [a for a in assemblies if a.kind == "ad"]
    assert all(a.name in {"ad-01", "ad-02", "ad-03"} for a in ads)
    cable_names = [a.name for a in assemblies if a.kind == "cable"]
    assert cable_names == [c["id"] for c in data["cables"][4:8]]


def test_ads_split_covers_all_ads_exactly_once():
    data = build_layout()
    nightlife_ads = {a.name for a in build.build_sector_assemblies(data, "nightlife") if a.kind == "ad"}
    ads_sector = {a.name for a in build.build_sector_assemblies(data, "ads") if a.kind == "ad"}
    assert nightlife_ads <= {ad["id"] for ad in data["ads"]}
    assert len(nightlife_ads | ads_sector) == len(data["ads"]) == 26
    assert not (nightlife_ads & ads_sector)
    # The nightlife wall ads hang on the north-band towers that host the club strip.
    wall_by_id = {ad["id"]: ad for ad in data["ads"] if ad["kind"] == "wall"}
    assert all(wall_by_id[ad_id]["attach"] in build.NIGHTLIFE_TOWERS for ad_id in nightlife_ads)
    assert all(wall_by_id[ad_id]["face"] == "south" for ad_id in nightlife_ads)


def test_ads_sector_keeps_cables_8_to_12():
    data = build_layout()
    assemblies = build.build_sector_assemblies(data, "ads")
    cable_names = [a.name for a in assemblies if a.kind == "cable"]
    assert cable_names == [c["id"] for c in data["cables"][8:12]]
    assert not ({a.name for a in assemblies if a.kind == "ad"} & build.NIGHTLIFE_TOWERS)


def test_vacant_sector_composition():
    data = build_layout()
    assemblies = build.build_sector_assemblies(data, "vacant")
    kinds = Counter(a.kind for a in assemblies)
    assert kinds == Counter({"vehicle-husk": 2, "junk-pile": 3, "large-chunk": 6, "collapsed-structure": 1})
    collapsed = next(a for a in assemblies if a.kind == "collapsed-structure")
    assert len(collapsed.parts) >= 8
    # Everything sits on the ground inside the vacant rect.
    vmin, vmax = data["vacant"]["min"], data["vacant"]["max"]
    for assembly in assemblies:
        for part in assembly.parts:
            for vertex in part.vertices:
                assert vertex[1] >= -0.2, (assembly.name, part.name)


def test_ground_sector_composition():
    data = build_layout()
    assemblies = build.build_sector_assemblies(data, "ground")
    kinds = Counter(a.kind for a in assemblies)
    assert kinds == Counter({"ground": 1, "street-patches": 1, "vacant-base": 1, "perimeter": 1})
    patches = next(a for a in assemblies if a.kind == "street-patches")
    assert 8 <= len(patches.parts) <= 15
    base = next(a for a in assemblies if a.kind == "vacant-base")
    (lo, hi) = base.bounds
    assert lo[0] <= -13.5 and hi[0] >= 13.5 and lo[2] <= -18.5 and hi[2] >= 18.5


# --- determinism and palette hygiene ------------------------------------------


def test_sector_assemblies_are_deterministic():
    data = build_layout()
    for sector in build.SECTORS:
        first = build.build_sector_assemblies(data, sector)
        second = build.build_sector_assemblies(data, sector)
        assert [(a.name, a.kind, len(a.parts)) for a in first] == [
            (a.name, a.kind, len(a.parts)) for a in second
        ], sector
        tri = lambda a: sum(len(f) - 2 for p in a.parts for f in p.faces)
        assert [tri(a) for a in first] == [tri(a) for a in second], sector


def test_batch_materials_all_exist_in_palette():
    data = build_layout()
    for sector in build.SECTORS:
        for assembly in build.build_sector_assemblies(data, sector):
            for key, merged in build.batch_assembly(assembly).items():
                assert key == f"{assembly.name}__{merged.material}", (sector, key)
                assert merged.material in MATERIALS, (sector, key)
                assert len(merged.vertices) > 0 and len(merged.faces) > 0


def test_sector_triangle_budget():
    data = build_layout()
    total = 0
    for sector in build.SECTORS:
        for assembly in build.build_sector_assemblies(data, sector):
            for merged in build.batch_assembly(assembly).values():
                total += sum(len(face) - 2 for face in merged.faces)
    # GN scatter adds ~15k for the vacant lot; 250k is the advisory ceiling.
    assert total < 220_000, total


# --- resource report -----------------------------------------------------------


def test_resource_report_schema():
    data = build_layout()
    towers = build.build_sector_assemblies(data, "towers")
    report = build.resource_report(towers, "towers")
    assert report["schema_version"] == 1
    assert report["sector"] == "towers"
    assert report["seed"] == 250925
    assert report["assembly_count"] == 10
    assert report["total_parts"] == sum(len(a.parts) for a in towers)
    assert report["blender_object_count"] == sum(len(build.batch_assembly(a)) for a in towers)
    assert report["material_count"] == len({p.material for a in towers for p in a.parts})
    assert report["scatter_method"] == "n/a"
    assert report["uv_issue_count"] == 0
    assert report["blend_path"] is None
    assert report["blender_version"] is None
