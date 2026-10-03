"""Limited local Light candidates based on slum02/postprocess.py fields."""
from modeling.slum03.types import Layout
from .common import node


def _light(key, position, color, radius, intensity):
    n = node(f'local-light-{key}', f'Local light {key}', position)
    n['components'].append({'key': f'local-light-{key}-component', 'type': 'FrooxEngine.Light',
                            'fields': {'LightType': 'Point', 'Intensity': intensity,
                                       'Color': list(color), 'Range': radius,
                                       'ShadowType': 'None'}})
    return n


def _cluster_lights(layout: Layout) -> list[dict]:
    """Full stage only: one shadowless accent per new storefront / market stall cluster."""
    groups: dict[tuple[str, str], list] = {}
    for p in layout.placements:
        if not p.key.startswith('density-') or p.params.get('detail_profile') != 'v2':
            continue
        if p.kind == 'nightlife' or (p.kind == 'stall' and p.params.get('density_zone') == 'market'):
            groups.setdefault((p.kind, p.params['cluster']), []).append(p)
    result = []
    for (kind, cluster), items in sorted(groups.items()):
        x = sum(p.origin[0] for p in items)/len(items)
        z = sum(p.origin[2] for p in items)/len(items)
        y = sum(p.origin[1] for p in items)/len(items) + (4.2 if kind == 'nightlife' else 3.2)
        color, radius = (((1., .16, .55, 1.), 10.) if kind == 'nightlife' else
                         ((1., .55, .25, 1.), 11.))
        result.append(_light(f'cluster-{kind}-{cluster}', (x, y, z), color, radius, .9))
    return result


def light_slots(layout: Layout) -> list[dict]:
    placements = {p.key: p for p in layout.placements}
    choices = (('market-west', (1., .55, .25, 1.), 11., 1.4),
               ('market-east', (1., .55, .25, 1.), 11., 1.4),
               ('yarol', (1., .52, .26, 1.), 12., 1.7),
               ('nightlife-east', (1., .16, .55, 1.), 10., 1.1),
               ('nightlife-velvet', (1., .16, .55, 1.), 10., 1.1),
               ('market-product-holo', (.15, .8, 1., 1.), 9., .8))
    result = []
    for key, color, radius, intensity in choices:
        x, y, z = placements[key].origin
        result.append(_light(key, (x, y+2.5, z), color, radius, intensity))
    if layout.density is not None and layout.density.stage == 'full':
        result += _cluster_lights(layout)
    return result
