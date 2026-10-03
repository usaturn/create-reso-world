"""Canonical editable anchors inside the district; shapes belong to later tasks."""
from .types import Placement, LabelSpec


def district_placements() -> tuple[Placement, ...]:
    def place(key, sector, kind, x, y, z, sx, sy, sz, yaw=0, **params):
        return Placement(key, sector, kind, (x, y, z), (sx, sy, sz),
                         float(yaw), 'district', params)

    return (
        place('district-ground', 'ground', 'ground', 0, 0, 0, 120, .3, 120,
              local_y_min=-.3, walkable=True),
        place('factory-floor', 'plaza', 'floor', 0, 0, 0, 40, .2, 30,
              local_y_min=-.2, walkable=True),
        place('north-wall', 'plaza', 'north-wall', 0, 0, 14.5, 36, 10, .8,
              face='south', graffiti='稲垣は絶対マカぶる'),
        place('plaza-rubble-west', 'plaza', 'rubble', -18.5, 0, -7, 2, 1.5, 4),
        place('plaza-rubble-east', 'plaza', 'rubble', 18.5, 0, -7, 2, 1.5, 4),
        place('ruin-west', 'ruins-west', 'ruin', -38, 0, 12, 17, 24, 18),
        # A separately editable shell beyond the western building, clear of paths.
        place('ruin-west-annex', 'ruins-west', 'ruin', -49, 0, 29, 10, 14, 12),
        place('ruin-north', 'ruins-north', 'ruin', -26, 0, 39, 16, 29, 18),
        place('ruin-east', 'ruins-east', 'ruin', 32, 0, 20, 13, 17, 14),
        place('shack-row', 'shacks', 'shack', -36, 0, -28, 15, 6, 12),
        place('shack-west', 'shacks', 'shack', -49, 0, -28, 8, 5, 9),
        place('market-west', 'market', 'stall', -9, 0, -34, 6, 3, 12,
              shelf_depth=.8, shelf_height=1.25, awning_height=2.7),
        place('market-east', 'market', 'stall', 9, 0, -34, 6, 3, 12,
              shelf_depth=.8, shelf_height=1.25, awning_height=2.7),
        place('nightlife-east', 'nightlife', 'nightlife', 34, 0, -23, 6, 11, 16,
              sign_height=3.5, shutter_width=3.4, storefront_name='LANTERN'),
        place('nightlife-velvet', 'nightlife', 'nightlife', 40, 0, -23, 6, 11, 16,
              sign_height=3.5, shutter_width=3.4, storefront_name='VELVET'),
        place('yarol', 'yarol', 'yarol', 51, 0, 47, 14, 11, 12, 90,
              entrance='east', exterior_only=True, door_width=2.2,
              window_width=2.3, reveal_depth=.3, sign_height=4),
        place('overhead-west', 'overhead', 'overhead', -32, 12, -10, 12, 13, 2,
              local_y_min=-12),
    )


def district_labels() -> tuple[LabelSpec, ...]:
    return (
        LabelSpec('yarol-sign', 'Yarol', 'yarol', (5.9, 4, 0), 90, 1.2,
                  (1.0, .54, .2, 1.0)),
        LabelSpec('nightlife-lantern-sign', 'LANTERN', 'nightlife-east',
                  (0, 3.5, 7.6), 0, .7, (1, .15, .48, 1)),
        LabelSpec('nightlife-velvet-sign', 'VELVET', 'nightlife-velvet',
                  (0, 3.5, 7.6), 0, .7, (.92, .15, .68, 1)),
        LabelSpec('market-sign', 'JUNK MARKET', 'market-west', (0, 3, -5.5),
                  180, .8, (.2, .95, 1.0, 1.0)),
    )
