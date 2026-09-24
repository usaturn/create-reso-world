"""Deterministic Resonite-coordinate mesh primitives used by editable Blender assets.

Mesh vertices use Resonite XYZ (Y is up); ``build.py`` converts once to Blender XZY.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

Vec3 = tuple[float, float, float]
Face = tuple[int, ...]


def _vec(value: Sequence[float], name: str) -> Vec3:
    if len(value) != 3:
        raise ValueError(f"{name} must have three coordinates")
    return tuple(float(component) for component in value)  # type: ignore[return-value]


@dataclass(frozen=True)
class MeshData:
    """Editable polygon mesh in assembly-local Resonite coordinates."""

    name: str
    vertices: tuple[Vec3, ...]
    faces: tuple[Face, ...]
    material: str

    def __post_init__(self) -> None:
        if not self.name or not self.material:
            raise ValueError("mesh name and material are required")
        if not self.vertices or not self.faces:
            raise ValueError("mesh must contain vertices and faces")
        for face in self.faces:
            if len(face) < 3 or any(index < 0 or index >= len(self.vertices) for index in face):
                raise ValueError(f"mesh {self.name} contains an invalid face")


def mesh(name: str, vertices: Sequence[Sequence[float]], faces: Sequence[Sequence[int]], material: str) -> MeshData:
    """Create a validated indexed polygon mesh."""
    return MeshData(name, tuple(_vec(vertex, "vertex") for vertex in vertices), tuple(tuple(int(i) for i in face) for face in faces), material)


def box(name: str, center: Sequence[float], size: Sequence[float], material: str) -> MeshData:
    """Create a deterministic six-sided box centered at ``center``."""
    cx, cy, cz = _vec(center, "center")
    sx, sy, sz = _vec(size, "size")
    if min(sx, sy, sz) <= 0:
        raise ValueError("box dimensions must be positive")
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    vertices = tuple((cx + x * hx, cy + y * hy, cz + z * hz) for x, y, z in (
        (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
        (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
    ))
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    return mesh(name, vertices, faces, material)


def beveled_box(name: str, center: Sequence[float], size: Sequence[float], bevel: float, material: str) -> MeshData:
    """Create a faceted chamfered box; clamp bevels to preserve thin sheet thickness."""
    c = _vec(center, "center")
    s = _vec(size, "size")
    if min(s) <= 0 or bevel <= 0:
        raise ValueError("box dimensions and bevel must be positive")
    bevel = min(float(bevel), min(s) * 0.45)
    half = tuple(value / 2 for value in s)
    vertices: list[Vec3] = []
    index_by_point: dict[Vec3, int] = {}
    faces: list[Face] = []

    def add_face(points: Sequence[Vec3]) -> None:
        indices = []
        for point in points:
            rounded = (round(point[0], 10), round(point[1], 10), round(point[2], 10))
            if rounded not in index_by_point:
                index_by_point[rounded] = len(vertices)
                vertices.append(rounded)  # type: ignore[arg-type]
            indices.append(index_by_point[rounded])
        faces.append(tuple(indices))

    # Eight-sided inset polygons on each of the six original box faces.
    for normal_axis in range(3):
        tangent = [axis for axis in range(3) if axis != normal_axis]
        a, b = tangent
        for sign in (-1, 1):
            aa, bb = half[a], half[b]
            inset_a, inset_b = aa - bevel, bb - bevel
            uv = ((-inset_a, -bb), (inset_a, -bb), (aa, -inset_b), (aa, inset_b),
                  (inset_a, bb), (-inset_a, bb), (-aa, inset_b), (-aa, -inset_b))
            points = []
            for u, v in uv:
                point = [0.0, 0.0, 0.0]
                point[normal_axis] = c[normal_axis] + sign * half[normal_axis]
                point[a] = c[a] + u
                point[b] = c[b] + v
                points.append(_vec(point, "beveled face vertex"))
            if sign < 0:
                points.reverse()
            add_face(points)

    # Beveled edge strips shared by adjacent face insets.
    for axis in range(3):
        others = [value for value in range(3) if value != axis]
        u, v = others
        for sign_u in (-1, 1):
            for sign_v in (-1, 1):
                lo, hi = -half[axis] + bevel, half[axis] - bevel
                p0 = [c[0], c[1], c[2]]
                p1 = list(p0)
                p2 = list(p0)
                p3 = list(p0)
                p0[axis], p1[axis], p2[axis], p3[axis] = c[axis] + lo, c[axis] + hi, c[axis] + hi, c[axis] + lo
                p0[u] = p1[u] = c[u] + sign_u * (half[u] - bevel)
                p2[u] = p3[u] = c[u] + sign_u * half[u]
                p0[v] = p3[v] = c[v] + sign_v * half[v]
                p1[v] = p2[v] = c[v] + sign_v * (half[v] - bevel)
                add_face((_vec(p0, "beveled edge vertex"), _vec(p1, "beveled edge vertex"), _vec(p2, "beveled edge vertex"), _vec(p3, "beveled edge vertex")))

    # Triangular facets at the eight corners close the chamfered edge bands.
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                add_face((
                    (c[0] + sx * half[0], c[1] + sy * (half[1] - bevel), c[2] + sz * (half[2] - bevel)),
                    (c[0] + sx * (half[0] - bevel), c[1] + sy * half[1], c[2] + sz * (half[2] - bevel)),
                    (c[0] + sx * (half[0] - bevel), c[1] + sy * (half[1] - bevel), c[2] + sz * half[2]),
                ))
    return mesh(name, vertices, faces, material)


def cylinder(name: str, center: Sequence[float], radius: float, depth: float, material: str, segments: int = 16) -> MeshData:
    """Create a capped cylinder along local Y, suitable for pots, lids and buttons."""
    cx, cy, cz = _vec(center, "center")
    if radius <= 0 or depth <= 0 or segments < 6:
        raise ValueError("cylinder needs positive radius/depth and at least six segments")
    vertices: list[Vec3] = []
    for y in (cy - depth / 2, cy + depth / 2):
        vertices.extend((cx + radius * math.cos(math.tau * i / segments), y, cz + radius * math.sin(math.tau * i / segments)) for i in range(segments))
    faces: list[Face] = [tuple(reversed(range(segments))), tuple(range(segments, 2 * segments))]
    faces.extend((i, (i + 1) % segments, (i + 1) % segments + segments, i + segments) for i in range(segments))
    return mesh(name, vertices, faces, material)


def pipe(name: str, start: Sequence[float], end: Sequence[float], radius: float, material: str, segments: int = 8) -> MeshData:
    """Create a closed round pipe segment between arbitrary 3D points."""
    a, b = _vec(start, "start"), _vec(end, "end")
    direction = tuple(b[i] - a[i] for i in range(3))
    length = math.sqrt(sum(value * value for value in direction))
    if length <= 1e-9 or radius <= 0 or segments < 5:
        raise ValueError("pipe endpoints must differ; radius and segment count must be positive")
    axis = tuple(value / length for value in direction)
    reference = (0.0, 1.0, 0.0) if abs(axis[1]) < 0.9 else (1.0, 0.0, 0.0)
    side = (axis[1] * reference[2] - axis[2] * reference[1], axis[2] * reference[0] - axis[0] * reference[2], axis[0] * reference[1] - axis[1] * reference[0])
    side_length = math.sqrt(sum(value * value for value in side))
    side = tuple(value / side_length for value in side)
    other = (axis[1] * side[2] - axis[2] * side[1], axis[2] * side[0] - axis[0] * side[2], axis[0] * side[1] - axis[1] * side[0])
    vertices: list[Vec3] = []
    for point in (a, b):
        for i in range(segments):
            angle = math.tau * i / segments
            cosine, sine = math.cos(angle), math.sin(angle)
            vertices.append((
                point[0] + radius * (side[0] * cosine + other[0] * sine),
                point[1] + radius * (side[1] * cosine + other[1] * sine),
                point[2] + radius * (side[2] * cosine + other[2] * sine),
            ))
    faces: list[Face] = [tuple(reversed(range(segments))), tuple(range(segments, 2 * segments))]
    faces.extend((i, (i + 1) % segments, (i + 1) % segments + segments, i + segments) for i in range(segments))
    return mesh(name, vertices, faces, material)
