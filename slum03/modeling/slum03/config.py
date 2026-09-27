"""Single source of fixed world dimensions for all sectors (metres)."""
from .types import RectXZ

DEFAULT_SEED = 260927
DISTRICT = RectXZ(-60.0, 60.0, -60.0, 60.0)
PLAZA = RectXZ(-20.0, 20.0, -15.0, 15.0)
CLEAR = RectXZ(-16.0, 16.0, -11.0, 11.0)
ROAD_SOUTH, ROAD_NORTH = -100.0, 130.0
WEST_SIDEWALK = RectXZ(60.0, 66.0, ROAD_SOUTH, ROAD_NORTH)
ROADWAY = RectXZ(66.0, 90.0, ROAD_SOUTH, ROAD_NORTH)
EAST_SIDEWALK = RectXZ(90.0, 96.0, ROAD_SOUTH, ROAD_NORTH)
RIVER = RectXZ(-200.0, 230.0, 78.0, 112.0)
BRIDGE = RectXZ(60.0, 96.0, 72.0, 118.0)
# Continuous 3m-wide activity paths; include overlap with the central floor.
ROUTES = (
    RectXZ(-60.0, 16.0, -1.5, 1.5),          # west entrance
    RectXZ(-1.5, 1.5, -60.0, 11.0),          # south entrance / market
    RectXZ(-16.0, 66.0, -1.5, 1.5),          # east entrance to west sidewalk
    WEST_SIDEWALK, EAST_SIDEWALK,           # bridge and north turnback
    RectXZ(66.0, 90.0, 66.0, 72.0),         # open checkpoint / vehicle access
    RectXZ(66.0, 90.0, 112.0, 130.0),       # north turnback
)
