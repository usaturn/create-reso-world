"""Deterministic mesh primitives for the akichi cyberpunk slum, in Resonite coordinates.

Mesh vertices use Resonite XYZ (Y is up, metres); the build step converts once to Blender XZY.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

Vec3 = tuple[float, float, float]
Face = tuple[int, ...]

_AXIS_DIRECTIONS: dict[str, Vec3] = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}


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
    """Create a closed chamfered box with shared vertices and outward face winding."""
    c = _vec(center, "center")
    s = _vec(size, "size")
    if min(s) <= 0 or bevel <= 0:
        raise ValueError("box dimensions and bevel must be positive")
    bevel = min(float(bevel), min(s) * 0.45)
    half = tuple(value / 2 for value in s)
    vertices: list[Vec3] = []
    vertex_indices: dict[Vec3, int] = {}
    faces: list[Face] = []

    def intern(point: Vec3) -> int:
        key = (round(point[0], 12), round(point[1], 12), round(point[2], 12))
        if key not in vertex_indices:
            vertex_indices[key] = len(vertices)
            vertices.append(key)
        return vertex_indices[key]

    def add_outward_face(points: Sequence[Vec3]) -> None:
        normal = (
            (points[1][1] - points[0][1]) * (points[2][2] - points[0][2]) - (points[1][2] - points[0][2]) * (points[2][1] - points[0][1]),
            (points[1][2] - points[0][2]) * (points[2][0] - points[0][0]) - (points[1][0] - points[0][0]) * (points[2][2] - points[0][2]),
            (points[1][0] - points[0][0]) * (points[2][1] - points[0][1]) - (points[1][1] - points[0][1]) * (points[2][0] - points[0][0]),
        )
        centroid = tuple(sum(point[axis] for point in points) / len(points) for axis in range(3))
        outward = tuple(centroid[axis] - c[axis] for axis in range(3))
        if sum(normal[axis] * outward[axis] for axis in range(3)) < 0:
            points = tuple(reversed(points))
        face = tuple(intern(point) for point in points)
        if len(set(face)) != len(face):
            raise ValueError(f"beveled box {name} has a collapsed face")
        faces.append(face)

    # The six original planes are inset rectangles; edge strips and corner
    # triangles share their exact boundary vertices with these rectangles.
    for normal_axis in range(3):
        tangents = tuple(axis for axis in range(3) if axis != normal_axis)
        a, b = tangents
        inset_a, inset_b = half[a] - bevel, half[b] - bevel
        for sign in (-1, 1):
            points = []
            for sign_a, sign_b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                point = [c[0], c[1], c[2]]
                point[normal_axis] = c[normal_axis] + sign * half[normal_axis]
                point[a] = c[a] + sign_a * inset_a
                point[b] = c[b] + sign_b * inset_b
                points.append(_vec(point, "beveled face vertex"))
            add_outward_face(points)

    # Twelve longitudinal strips fill each original box edge.
    for edge_axis in range(3):
        u, v = tuple(axis for axis in range(3) if axis != edge_axis)
        for sign_u in (-1, 1):
            for sign_v in (-1, 1):
                lo, hi = -half[edge_axis] + bevel, half[edge_axis] - bevel
                points = []
                for edge_value, inset_u in ((lo, False), (hi, False), (hi, True), (lo, True)):
                    point = [c[0], c[1], c[2]]
                    point[edge_axis] = c[edge_axis] + edge_value
                    point[u] = c[u] + sign_u * (half[u] - (bevel if inset_u else 0.0))
                    point[v] = c[v] + sign_v * (half[v] - (0.0 if inset_u else bevel))
                    points.append(_vec(point, "beveled edge vertex"))
                add_outward_face(points)

    # Eight triangular chamfer planes close the three face corners at every box vertex.
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                add_outward_face((
                    (c[0] + sx * half[0], c[1] + sy * (half[1] - bevel), c[2] + sz * (half[2] - bevel)),
                    (c[0] + sx * (half[0] - bevel), c[1] + sy * half[1], c[2] + sz * (half[2] - bevel)),
                    (c[0] + sx * (half[0] - bevel), c[1] + sy * (half[1] - bevel), c[2] + sz * half[2]),
                ))

    return MeshData(name, tuple(vertices), tuple(faces), material)


def cylinder(name: str, center: Sequence[float], radius: float, height: float, segments: int, material: str, axis: str = "Y") -> MeshData:
    """Create a closed cylinder along a world axis, capped at both ends.

    ``axis`` is one of ``"X"``, ``"Y"`` or ``"Z"`` (case-insensitive); ``height``
    spans that axis, centred on ``center``. The two caps are n-gons and the side
    is one quad per segment.
    """
    c = _vec(center, "center")
    if radius <= 0 or height <= 0 or segments < 3:
        raise ValueError("cylinder needs a positive radius and height, and at least three segments")
    if not isinstance(axis, str) or axis.upper() not in _AXIS_DIRECTIONS:
        raise ValueError("cylinder axis must be one of 'X', 'Y' or 'Z'")
    n = _AXIS_DIRECTIONS[axis.upper()]
    reference = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 1.0, 0.0)
    u_raw = (n[1] * reference[2] - n[2] * reference[1], n[2] * reference[0] - n[0] * reference[2], n[0] * reference[1] - n[1] * reference[0])
    u_length = math.sqrt(sum(value * value for value in u_raw))
    u = tuple(value / u_length for value in u_raw)
    v = (n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0])
    vertices: list[Vec3] = []
    for end_sign in (-1.0, 1.0):
        for index in range(segments):
            angle = math.tau * index / segments
            cosine, sine = math.cos(angle), math.sin(angle)
            vertices.append(_vec(tuple(
                c[axis_index] + end_sign * n[axis_index] * height / 2
                + radius * (u[axis_index] * cosine + v[axis_index] * sine)
                for axis_index in range(3)
            ), "cylinder vertex"))
    faces: list[Face] = [tuple(reversed(range(segments))), tuple(range(segments, 2 * segments))]
    faces.extend((index, (index + 1) % segments, (index + 1) % segments + segments, index + segments) for index in range(segments))
    return mesh(name, vertices, faces, material)


def prism(name: str, center: Sequence[float], size: Sequence[float], material: str) -> MeshData:
    """Create a closed gable-roof triangular prism centred on ``center``.

    ``size`` is ``(width, height, depth)``; ``height`` reaches the ridge, which
    runs along the depth (local Z) axis at ``height / 2`` above ``center``. The
    triangular gable ends therefore face -Z and +Z, the base sits at
    ``center - height / 2`` and the two roof planes slope in ±X.
    """
    c = _vec(center, "center")
    width, height, depth = _vec(size, "size")
    if min(width, height, depth) <= 0:
        raise ValueError("prism dimensions must be positive")
    half_w, half_h, half_d = width / 2, height / 2, depth / 2
    vertices = (
        (c[0] - half_w, c[1] - half_h, c[2] - half_d),
        (c[0] + half_w, c[1] - half_h, c[2] - half_d),
        (c[0] + half_w, c[1] - half_h, c[2] + half_d),
        (c[0] - half_w, c[1] - half_h, c[2] + half_d),
        (c[0], c[1] + half_h, c[2] - half_d),
        (c[0], c[1] + half_h, c[2] + half_d),
    )
    faces = ((0, 1, 2, 3), (0, 4, 1), (3, 2, 5), (0, 3, 5, 4), (1, 4, 5, 2))
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
