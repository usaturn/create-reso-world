"""Limited local Light candidates based on slum02/postprocess.py fields."""
from modeling.slum03.types import Layout
from .common import node


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
        p = placements[key]
        x, y, z = p.origin
        n = node(f'local-light-{key}', f'Local light {key}', (x, y+2.5, z))
        n['components'].append({'key': f'local-light-{key}-component', 'type': 'FrooxEngine.Light',
                                'fields': {'LightType': 'Point', 'Intensity': intensity,
                                           'Color': list(color), 'Range': radius,
                                           'ShadowType': 'None'}})
        result.append(n)
    return result
