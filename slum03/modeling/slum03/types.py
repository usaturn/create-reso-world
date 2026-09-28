"""Offline Resonite-local plan data. X east, Y up, Z north (metres)."""
from dataclasses import dataclass, field
from typing import Any

Vec3 = tuple[float, float, float]


@dataclass(frozen=True)
class RectXZ:
    x_min: float
    x_max: float
    z_min: float
    z_max: float

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return self.x_min, self.x_max, self.z_min, self.z_max

    @property
    def size(self) -> tuple[float, float]:
        return self.x_max - self.x_min, self.z_max - self.z_min


@dataclass(frozen=True)
class Bounds3:
    minimum: Vec3
    maximum: Vec3


@dataclass(frozen=True)
class Placement:
    key: str
    sector: str
    kind: str
    origin: Vec3
    size: Vec3
    yaw_deg: float
    domain: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Viewpoint:
    key: str
    eye: Vec3
    target_group: str


@dataclass(frozen=True)
class LabelSpec:
    key: str
    text: str
    parent_name: str
    offset: Vec3
    yaw_deg: float
    height: float
    color: tuple[float, float, float, float]


@dataclass(frozen=True)
class DensityZone:
    key: str
    bounds: RectXZ


@dataclass(frozen=True)
class DensityOpening:
    bounds: RectXZ
    reason: str


@dataclass(frozen=True)
class DensityRoute:
    key: str
    purpose: str
    corridor: RectXZ
    openings: tuple[DensityOpening, ...]


@dataclass(frozen=True)
class DensityConfig:
    stage: str
    zones: tuple[DensityZone, ...]
    routes: tuple[DensityRoute, ...]
    branch_clearances: tuple[RectXZ, ...]
    selected_keys: tuple[str, ...]


@dataclass(frozen=True)
class Layout:
    seed: int
    district: RectXZ
    plaza: RectXZ
    clear: RectXZ
    routes: tuple[RectXZ, ...]
    placements: tuple[Placement, ...]
    viewpoints: tuple[Viewpoint, ...]
    labels: tuple[LabelSpec, ...]
    density: DensityConfig | None = None

    def select(self, kind: str) -> tuple[Placement, ...]:
        return tuple(p for p in self.placements if p.kind == kind)


@dataclass(frozen=True)
class Issue:
    code: str
    object_key: str
    message: str


Report = dict[str, Any]
Manifest = dict[str, Any]
