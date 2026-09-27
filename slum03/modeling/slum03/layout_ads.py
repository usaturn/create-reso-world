"""Three separated AR anchor styles with fixed readable copy."""
from .types import LabelSpec, Placement


def ad_placements() -> tuple[Placement, ...]:
    return (
        Placement('market-product-holo', 'ads', 'product-holo', (-9, 4, -46),
                  (3, 3, 3), 0., 'district', {'motion': 'slow-spin'}),
        Placement('nightlife-info-ad', 'ads', 'info-ad', (37, 12, -16.55),
                  (5, 4, 2), 0., 'district', {'motion': 'slow-scan'}),
        Placement('east-lane-ribbon', 'ads', 'ribbon-ad', (26, 6, 10),
                  (7, 2, 2), 0., 'district', {'motion': 'slow-flow'}),
    )


def ad_labels() -> tuple[LabelSpec, ...]:
    return (
        LabelSpec('product-copy', 'AUGMENT', 'market-product-holo',
                  (0, -1, 1.35), 0., .9, (.3, 1., 1., 1.)),
        LabelSpec('info-copy', 'NIGHT SHIFT', 'nightlife-info-ad',
                  (0, 1, -0.9), 180., 1., (1., .3, .8, 1.)),
        LabelSpec('ribbon-copy', 'LIVE', 'east-lane-ribbon',
                  (0, 0, 1.0), 0., .7, (.8, 1., .25, 1.)),
    )
