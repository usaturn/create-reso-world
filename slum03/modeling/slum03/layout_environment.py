"""Road, river, nonwalkable forest, and direction-specific skyline anchors."""
from .types import Placement


def environment_placements() -> tuple[Placement, ...]:
    def place(key, sector, kind, domain, x, y, z, sx, sy, sz, **params):
        return Placement(key, sector, kind, (x, y, z), (sx, sy, sz), 0.,
                         domain, params)

    return (
        place('west-sidewalk', 'road-river', 'sidewalk', 'road', 63, 0, 15,
              6, .2, 230, local_y_min=-.2, walkable=True),
        place('roadway', 'road-river', 'roadway', 'road', 78, 0, 15,
              24, .3, 230, local_y_min=-.3, walkable=True),
        place('east-sidewalk', 'road-river', 'sidewalk', 'road', 93, 0, 15,
              6, .2, 230, local_y_min=-.2, walkable=True),
        place('river', 'road-river', 'river', 'water', 15, -2, 95,
              430, .2, 34),
        place('bridge', 'road-river', 'bridge', 'road', 78, 0, 95,
              36, .4, 46, local_y_min=-.4, walkable=True),
        place('checkpoint', 'road-river', 'checkpoint', 'road', 98, 0, 69,
              3, 6, 4, opening_width=24, open=True),
        place('bridge-rail-west', 'road-river', 'guardrail', 'road', 59.5, 0, 95,
              1, 1.4, 46),
        place('bridge-rail-east', 'road-river', 'guardrail', 'road', 96.5, 0, 95,
              1, 1.4, 46),
        place('north-turnback', 'road-river', 'boundary', 'road', 78, 0, 130.5,
              36, 3, 1),
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
