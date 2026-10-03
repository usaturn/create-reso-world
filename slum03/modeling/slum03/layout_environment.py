"""Road, river, nonwalkable forest, and direction-specific skyline anchors."""
from . import config
from .types import Placement


def environment_placements() -> tuple[Placement, ...]:
    def place(key, sector, kind, domain, x, y, z, sx, sy, sz, **params):
        return Placement(key, sector, kind, (x, y, z), (sx, sy, sz), 0.,
                         domain, params)

    def rect_place(key, kind, rect, y, height, **params):
        return place(key, 'road-river', kind, 'water' if kind == 'river' else 'road',
                     (rect.x_min+rect.x_max)/2, y, (rect.z_min+rect.z_max)/2,
                     rect.size[0], height, rect.size[1], **params)

    return (
        rect_place('west-sidewalk', 'sidewalk', config.WEST_SIDEWALK, 0, .2,
                   local_y_min=-.2, walkable=True),
        rect_place('roadway', 'roadway', config.ROADWAY, 0, .3,
                   local_y_min=-.3, walkable=True),
        rect_place('east-sidewalk', 'sidewalk', config.EAST_SIDEWALK, 0, .2,
                   local_y_min=-.2, walkable=True),
        rect_place('river', 'river', config.RIVER, -4, .2),
        rect_place('bridge', 'bridge', config.BRIDGE, 0, 6.1,
                   local_y_min=-4, walkable=True),
        place('checkpoint', 'road-river', 'checkpoint', 'road',
              (config.BRIDGE.x_min+config.BRIDGE.x_max)/2, 0, config.BRIDGE.z_min-3,
              config.BRIDGE.size[0], 6, 6,
              opening_width=config.ROADWAY.size[0], open=True),
        place('north-turnback', 'road-river', 'boundary', 'road',
              (config.BRIDGE.x_min+config.BRIDGE.x_max)/2, 0, config.ROAD_NORTH+.5,
              config.BRIDGE.size[0], 3, 1),
        place('south-road-end', 'road-river', 'boundary', 'road',
              (config.BRIDGE.x_min+config.BRIDGE.x_max)/2, 0, config.ROAD_SOUTH-.5,
              config.BRIDGE.size[0], 3, 1),
        place('forest', 'forest', 'forest', 'background', 160, 0, -10,
              120, 36, 155, nonwalkable=True),
        place('north-towers', 'backdrop-north', 'highrises', 'background',
              0, 0, 178, 125, 160, 42, nonwalkable=True),
        place('arcology-terraces', 'backdrop-north', 'arcology', 'background',
              -130, 0, 330, 130, 620, 100, silhouette='terraced'),
        place('arcology-gate', 'backdrop-north', 'arcology', 'background',
              25, 0, 440, 180, 820, 100, silhouette='gate'),
        place('arcology-towers', 'backdrop-north', 'arcology', 'background',
              195, 0, 370, 150, 700, 110, silhouette='linked-towers'),
        place('west-city', 'backdrop-west-south', 'low-city', 'background',
              -115, 0, -15, 65, 42, 180, nonwalkable=True),
        place('south-city', 'backdrop-west-south', 'low-city', 'background',
              0, 0, -122, 115, 38, 65, nonwalkable=True),
    )
