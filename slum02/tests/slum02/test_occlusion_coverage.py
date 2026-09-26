from modeling.slum02 import geometry as g
from modeling.slum02.layout import build_layout
from modeling.slum02.sectors import SECTORS, sector_assemblies


def test_every_occluder_is_backed_by_geometry():
    data = build_layout()
    owners = {}
    for sector in SECTORS:
        for a in sector_assemblies(data, sector):
            for oid in a.meta.get("occludes", []):
                owners.setdefault(oid, []).append(a)
    for o in data["occluders"]:
        assert o["id"] in owners, o["id"]
        parts = [g.transformed(p, 0.0, a.origin) for a in owners[o["id"]] for p in a.parts]
        lo, hi = g.bounds(parts)
        assert all(lo[i] <= o["min"][i] + 0.05 for i in range(3)), o["id"]
        assert all(hi[i] >= o["max"][i] - 0.05 for i in range(3)), o["id"]
