"""Schema-complete synthetic reports; never evidence of generated geometry."""
from modeling.slum03.sectors import SECTORS
from modeling.slum03.spatial import placement_bounds


def minimal_reports(layout):
    reports = {}
    for sector in SECTORS:
        objects, bounds = [], {}
        for p in layout.placements:
            if p.sector != sector:
                continue
            objects.append({'key': p.key, 'kind': p.kind, 'mesh': p.key})
            b = placement_bounds(p)
            bounds[p.key] = {'minimum': list(b.minimum), 'maximum': list(b.maximum)}
        reports[sector] = {'sector': sector, 'export_collection': f'Slum03{sector}Export',
                           'objects': objects, 'evaluated_bounds': bounds,
                           'materials': ['synthetic'], 'triangles': 1, 'vertices': 3,
                           'submeshes': 1, 'uv_issues': [], 'errors': []}
    return reports
