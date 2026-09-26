"""Deterministic mesh primitives for the slum02 cyberpunk slum, in Resonite coordinates.

Mesh vertices use Resonite XYZ (Y is up, metres); the build step converts once to Blender XZY.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

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


def rotate_y(point: Sequence[float], radians: float) -> Vec3:
    c, s = math.cos(radians), math.sin(radians)
    x, y, z = point
    return (x * c + z * s, y, -x * s + z * c)


def transformed(m: MeshData, radians: float, offset: Sequence[float], name: str | None = None) -> MeshData:
    ox, oy, oz = offset
    verts = tuple((p[0] + ox, p[1] + oy, p[2] + oz) for p in (rotate_y(v, radians) for v in m.vertices))
    return MeshData(name or m.name, verts, m.faces, m.material)


def rotate_xyz(point: Sequence[float], rx: float, ry: float, rz: float) -> Vec3:
    x, y, z = point
    c, s = math.cos(rx), math.sin(rx)
    y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(ry), math.sin(ry)
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(rz), math.sin(rz)
    x, y = x * c - y * s, x * s + y * c
    return (x, y, z)


def transformed_xyz(m: MeshData, rx: float, ry: float, rz: float, offset: Sequence[float], name: str | None = None) -> MeshData:
    verts = tuple(tuple(p[i] + offset[i] for i in range(3)) for p in (rotate_xyz(v, rx, ry, rz) for v in m.vertices))
    return MeshData(name or m.name, verts, m.faces, m.material)  # type: ignore[arg-type]


def bounds(meshes: Iterable[MeshData]) -> tuple[Vec3, Vec3]:
    pts = [v for m in meshes for v in m.vertices]
    if not pts:
        raise ValueError("bounds of nothing")
    return (tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3)))  # type: ignore[return-value]


def triangle_count(m: MeshData) -> int:
    return sum(len(f) - 2 for f in m.faces)


def _splits(lo: float, hi: float, max_edge: float, cuts: Iterable[float] = ()) -> list[float]:
    """Sorted breakpoints from lo to hi including forced cuts, no span above max_edge."""
    points = sorted({lo, hi, *(c for c in cuts if lo < c < hi)})
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        n = max(1, math.ceil((b - a) / max_edge - 1e-9))
        out.extend(a + (b - a) * k / n for k in range(1, n + 1))
    return out


class GridBuilder:
    """Vertex-interning polygon builder shared by the subdivided primitives."""

    def __init__(self) -> None:
        self.vertices: list[Vec3] = []
        self.faces: list[Face] = []
        self._index: dict[tuple[float, float, float], int] = {}

    def v(self, p: Sequence[float]) -> int:
        key = (round(p[0], 9), round(p[1], 9), round(p[2], 9))
        if key not in self._index:
            self._index[key] = len(self.vertices)
            self.vertices.append(key)
        return self._index[key]

    def quad(self, a, b, c, d) -> None:
        self.faces.append((self.v(a), self.v(b), self.v(c), self.v(d)))

    def grid(self, origin: Vec3, u: Vec3, w: Vec3, us: list[float], ws: list[float], skip=lambda i, j: False) -> None:
        """Quads over origin + u*us[i] + w*ws[j]; winding u x w is the face normal."""
        def at(a: float, b: float) -> Vec3:
            return tuple(origin[k] + u[k] * a + w[k] * b for k in range(3))  # type: ignore[return-value]
        for i in range(len(us) - 1):
            for j in range(len(ws) - 1):
                if not skip(i, j):
                    self.quad(at(us[i], ws[j]), at(us[i + 1], ws[j]), at(us[i + 1], ws[j + 1]), at(us[i], ws[j + 1]))

    def build(self, name: str, material: str) -> MeshData:
        return mesh(name, self.vertices, self.faces, material)


def subdivided_box(name: str, center: Sequence[float], size: Sequence[float], max_edge: float, material: str) -> MeshData:
    cx, cy, cz = center
    sx, sy, sz = size
    if min(sx, sy, sz) <= 0 or max_edge <= 0:
        raise ValueError("subdivided box needs positive size and max_edge")
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    xs, ys, zs = (_splits(-h, h, max_edge) for h in (hx, hy, hz))
    b = GridBuilder()
    # +X / -X
    b.grid((cx + hx, cy, cz), (0, 1, 0), (0, 0, 1), ys, zs)
    b.grid((cx - hx, cy, cz), (0, 0, 1), (0, 1, 0), zs, ys)
    # +Y / -Y
    b.grid((cx, cy + hy, cz), (0, 0, 1), (1, 0, 0), zs, xs)
    b.grid((cx, cy - hy, cz), (1, 0, 0), (0, 0, 1), xs, zs)
    # +Z / -Z
    b.grid((cx, cy, cz + hz), (1, 0, 0), (0, 1, 0), xs, ys)
    b.grid((cx, cy, cz - hz), (0, 1, 0), (1, 0, 0), ys, xs)
    return b.build(name, material)


def wall_with_openings(name: str, width: float, height: float, thickness: float,
                       openings: Sequence[Sequence[float]], recess: float, max_edge: float, material: str,
                       closed: bool = True) -> MeshData:
    hw, ht = width / 2, thickness / 2
    if width <= 0 or height <= 0 or thickness <= 0 or max_edge <= 0:
        raise ValueError("wall needs positive dimensions")
    if not 0 < recess < thickness:
        raise ValueError("recess must be positive and thinner than the wall")
    rects = []
    for x0, y0, x1, y1 in openings:
        if not (-hw < x0 < x1 < hw and 0 < y0 < y1 < height):
            raise ValueError(f"opening {(x0, y0, x1, y1)} must lie strictly inside the wall")
        rects.append((x0, y0, x1, y1))
    xs = _splits(-hw, hw, max_edge, [c for r in rects for c in (r[0], r[2])])
    ys = _splits(0.0, height, max_edge, [c for r in rects for c in (r[1], r[3])])

    def inside(i: int, j: int) -> bool:
        mx, my = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
        return any(r[0] < mx < r[2] and r[1] < my < r[3] for r in rects)

    b = GridBuilder()
    b.grid((0, 0, ht), (1, 0, 0), (0, 1, 0), xs, ys, skip=inside)            # front (+Z) minus openings
    if closed:
        b.grid((0, 0, -ht), (0, 1, 0), (1, 0, 0), ys, xs)                      # back
        zs = [-ht, ht]
        b.grid((hw, 0, 0), (0, 1, 0), (0, 0, 1), ys, zs)                       # +X end
        b.grid((-hw, 0, 0), (0, 0, 1), (0, 1, 0), zs, ys)                      # -X end
        b.grid((0, height, 0), (0, 0, 1), (1, 0, 0), zs, xs)                   # top
        b.grid((0, 0, 0), (1, 0, 0), (0, 0, 1), xs, zs)                        # bottom
    back = ht - recess
    for x0, y0, x1, y1 in rects:
        rx = [x for x in xs if x0 - 1e-9 <= x <= x1 + 1e-9]
        ry = [y for y in ys if y0 - 1e-9 <= y <= y1 + 1e-9]
        b.grid((0, 0, back), (1, 0, 0), (0, 1, 0), rx, ry)                     # recess back (+Z facing)
        dz = [back, ht]
        b.grid((0, y0, 0), (0, 0, 1), (1, 0, 0), dz, rx)                       # sill, faces +Y
        b.grid((0, y1, 0), (1, 0, 0), (0, 0, 1), rx, dz)                       # head, faces -Y
        b.grid((x0, 0, 0), (0, 1, 0), (0, 0, 1), ry, dz)                       # left jamb, faces +X
        b.grid((x1, 0, 0), (0, 0, 1), (0, 1, 0), dz, ry)                       # right jamb, faces -X
    return b.build(name, material)


def catenary(a: Sequence[float], b: Sequence[float], sag: float, segments: int) -> list[Vec3]:
    if segments < 2 or sag < 0:
        raise ValueError("catenary needs >=2 segments and non-negative sag")
    pts = []
    for k in range(segments + 1):
        t = k / segments
        drop = sag * 4 * t * (1 - t)
        pts.append(tuple(a[i] + (b[i] - a[i]) * t - (drop if i == 1 else 0.0) for i in range(3)))
    return pts  # type: ignore[return-value]


def tube(name: str, points: Sequence[Sequence[float]], radius: float, sides: int, material: str,
         ref: Vec3 | None = None) -> MeshData:
    if len(points) < 2 or radius <= 0 or sides < 3:
        raise ValueError("tube needs >=2 points, positive radius and >=3 sides")
    verts: list[Vec3] = []
    n = len(points)
    for k, p in enumerate(points):
        prev_p, next_p = points[max(k - 1, 0)], points[min(k + 1, n - 1)]
        d = [next_p[i] - prev_p[i] for i in range(3)]
        length = math.sqrt(sum(x * x for x in d)) or 1.0
        d = [x / length for x in d]
        # ref pins the ring basis for every span (planar bends need one roll reference; the
        # default heuristic flips axis near vertical and twists the quads into bowties).
        base = ref if ref is not None else ((0.0, 1.0, 0.0) if abs(d[1]) < 0.9 else (1.0, 0.0, 0.0))
        s = [d[1] * base[2] - d[2] * base[1], d[2] * base[0] - d[0] * base[2], d[0] * base[1] - d[1] * base[0]]
        sl = math.sqrt(sum(x * x for x in s))
        if sl <= 1e-9:
            base = (0.0, 1.0, 0.0) if abs(d[1]) < 0.9 else (1.0, 0.0, 0.0)
            s = [d[1] * base[2] - d[2] * base[1], d[2] * base[0] - d[0] * base[2], d[0] * base[1] - d[1] * base[0]]
            sl = math.sqrt(sum(x * x for x in s))
        s = [x / sl for x in s]
        o = [d[1] * s[2] - d[2] * s[1], d[2] * s[0] - d[0] * s[2], d[0] * s[1] - d[1] * s[0]]
        for j in range(sides):
            ang = math.tau * j / sides
            verts.append(tuple(p[i] + radius * (s[i] * math.cos(ang) + o[i] * math.sin(ang)) for i in range(3)))  # type: ignore[arg-type]
    faces: list[Face] = []
    for k in range(n - 1):
        for j in range(sides):
            a, b2 = k * sides + j, k * sides + (j + 1) % sides
            faces.append((a, b2, b2 + sides, a + sides))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(range((n - 1) * sides, n * sides)))
    return mesh(name, verts, faces, material)


@dataclass
class Assembly:
    kind: str
    name: str
    sector: str
    origin: Vec3
    parts: list[MeshData]
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MergedMesh:
    name: str
    vertices: tuple[Vec3, ...]
    faces: tuple[Face, ...]
    face_materials: tuple[int, ...]
    materials: tuple[str, ...]


def merge_assembly(assembly: Assembly) -> MergedMesh:
    materials: list[str] = []
    verts: list[Vec3] = []
    faces: list[Face] = []
    face_mats: list[int] = []
    for part in assembly.parts:
        if part.material not in materials:
            materials.append(part.material)
        slot = materials.index(part.material)
        offset = len(verts)
        verts.extend(part.vertices)
        for f in part.faces:
            faces.append(tuple(offset + i for i in f))
            face_mats.append(slot)
    return MergedMesh(assembly.name, tuple(verts), tuple(faces), tuple(face_mats), tuple(materials))


# --------------------------------------------------------------------------- shared mesh ops
#
# Vector + shell helpers shared by the sector generators (plaza.py, towers.py)
# and vcolor.py. They used to be copied verbatim into each generator; keep the
# single implementation here so R11 (outward/CCW, positive signed volume) is
# enforced the same way everywhere.


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def norm(a: Vec3) -> Vec3:
    """Unit vector along ``a``. Contract: a zero vector returns ``(0, 0, 0)``
    instead of raising (the tolerant behaviour the former towers.py copy had;
    plaza.py's copy used to raise ZeroDivisionError). Callers only ever pass
    non-zero vectors — endpoints/offsets are separated by construction — so
    both contracts agree on every real input."""
    length = math.sqrt(dot(a, a)) or 1.0
    return mul(a, 1.0 / length)


def face_normal(pts: Sequence[Vec3]) -> Vec3:
    """Normalized Newell normal of a polygon (direction *does not* depend on size)."""
    nx = ny = nz = 0.0
    for a, b in zip(pts, (*pts[1:], pts[0])):
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / length, ny / length, nz / length)


def signed_volume(m: MeshData) -> float:
    total = 0.0
    for face in m.faces:
        p0 = m.vertices[face[0]]
        for i in range(1, len(face) - 1):
            total += dot(p0, cross(m.vertices[face[i]], m.vertices[face[i + 1]])) / 6
    return total


def outward(m: MeshData) -> MeshData:
    """Flip a consistently wound closed shell if it came out inside-out (R11)."""
    if signed_volume(m) > 0:
        return m
    return MeshData(m.name, m.vertices, tuple(tuple(reversed(f)) for f in m.faces), m.material)


def planarize(m: MeshData, tol: float = 1e-6) -> MeshData:
    """Split non-planar polygons (bent tubes, torn plates) into triangles so metric UVs stay exact."""
    faces: list[Face] = []
    changed = False
    for f in m.faces:
        if len(f) > 3:
            pts = [m.vertices[i] for i in f]
            n = face_normal(pts)
            c = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
            if max(abs(dot(sub(p, c), n)) for p in pts) > tol:
                faces.extend((f[0], f[k], f[k + 1]) for k in range(1, len(f) - 1))
                changed = True
                continue
        faces.append(f)
    return MeshData(m.name, m.vertices, tuple(faces), m.material) if changed else m


def combine(name: str, meshes: Sequence[MeshData], material: str | None = None) -> MeshData:
    """Concatenate meshes into one part (flat face list, re-indexed)."""
    verts: list[Vec3] = []
    faces: list[Face] = []
    for m in meshes:
        off = len(verts)
        verts.extend(m.vertices)
        faces.extend(tuple(off + i for i in f) for f in m.faces)
    return mesh(name, verts, faces, material or meshes[0].material)


def fan_prism(name: str, ring: Sequence[tuple[float, float]], y0: float, y1: float,
              material: str) -> MeshData:
    """Closed prism over a star-shaped (x, z) outline; caps are fans around the centroid."""
    n = len(ring)
    cx, cz = sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n
    verts = [(x, y0, z) for x, z in ring] + [(x, y1, z) for x, z in ring] + [(cx, y0, cz), (cx, y1, cz)]
    bc, tc = 2 * n, 2 * n + 1
    faces = []
    for i in range(n):
        k = (i + 1) % n
        faces.append((bc, i, k))
        faces.append((tc, n + k, n + i))
        faces.append((i, n + i, n + k, k))
    return outward(mesh(name, verts, faces, material))


def basis(d: Vec3, hint: Vec3) -> tuple[Vec3, Vec3, Vec3]:
    """Right-handed frame (u, d, w) with ``d`` normalized and ``u`` built from ``hint``."""
    d = norm(d)
    u = sub(hint, mul(d, dot(hint, d)))
    if dot(u, u) < 1e-10:
        alt = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 0.0, 1.0)
        u = sub(alt, mul(d, dot(alt, d)))
    u = norm(u)
    return u, d, cross(u, d)   # right-handed: identity when u=X, d=Y


def frame(m: MeshData, origin: Sequence[float], d: Vec3, hint: Vec3,
          name: str | None = None) -> MeshData:
    """Map local (x, y, z) to origin + x*u + y*d + z*w (a proper rotation, so winding survives)."""
    u, dd, w = basis(d, hint)
    verts = tuple(tuple(origin[k] + p[0] * u[k] + p[1] * dd[k] + p[2] * w[k] for k in range(3))
                  for p in m.vertices)
    return MeshData(name or m.name, verts, m.faces, m.material)  # type: ignore[arg-type]


def beam(name: str, p0: Vec3, p1: Vec3, su: float, sw: float, material: str,
         hint: Vec3 = (0.0, 1.0, 0.0)) -> MeshData:
    """Box beam between two points; ``su``/``sw`` are the section sizes, axis along p0->p1."""
    d = sub(p1, p0)
    length = math.sqrt(dot(d, d))
    return frame(box(name, (0, length / 2, 0), (su, length, sw), material), p0, d, hint)


def torus(name: str, center: Sequence[float], major: float, minor: float, segments: int, sides: int,
          material: str) -> MeshData:
    """Closed outward torus around the Y axis through ``center`` (tyres, cable rings)."""
    c = _vec(center, "center")
    if major <= minor or minor <= 0 or segments < 3 or sides < 3:
        raise ValueError("torus needs 0 < minor < major and at least three segments/sides")
    verts: list[Vec3] = []
    for i in range(segments):
        a = math.tau * i / segments
        for j in range(sides):
            b = math.tau * j / sides
            r = major + minor * math.cos(b)
            verts.append((c[0] + r * math.cos(a), c[1] + minor * math.sin(b), c[2] + r * math.sin(a)))
    faces = [(i * sides + j, ((i + 1) % segments) * sides + j, ((i + 1) % segments) * sides + (j + 1) % sides,
              i * sides + (j + 1) % sides) for i in range(segments) for j in range(sides)]
    return outward(mesh(name, verts, faces, material))


def thick_sheet(name: str, grid: Sequence[Sequence[Sequence[float]]], offset: Sequence[float],
                material: str) -> MeshData:
    """Closed thin shell over a (rows x cols) point grid and the same grid moved by ``offset``.

    Used for sagging tarps, corrugated sheets and sign boards: a single-sided card would be
    culled from one side (R11 forbids relying on Blender normal recalculation), a thin closed
    shell reads from both. Non-planar grid cells are triangulated for metric UVs.
    """
    rows, cols = len(grid), len(grid[0])
    if rows < 2 or cols < 2 or any(len(r) != cols for r in grid):
        raise ValueError("thick_sheet needs a rectangular grid of at least 2 x 2 points")
    o = _vec(offset, "offset")
    top = [_vec(p, "grid point") for r in grid for p in r]
    verts = top + [(p[0] + o[0], p[1] + o[1], p[2] + o[2]) for p in top]
    n = rows * cols

    def t(i: int, j: int) -> int:
        return i * cols + j

    faces: list[Face] = []
    for i in range(rows - 1):
        for j in range(cols - 1):
            a, b, c_, d = t(i, j), t(i + 1, j), t(i + 1, j + 1), t(i, j + 1)
            faces.append((a, b, c_, d))
            faces.append((a + n, d + n, c_ + n, b + n))
    # boundary loop of the top grid in the same direction as its quads' boundary edges
    loop = ([t(i, 0) for i in range(rows)] + [t(rows - 1, j) for j in range(1, cols)]
            + [t(i, cols - 1) for i in range(rows - 2, -1, -1)] + [t(0, j) for j in range(cols - 2, 0, -1)])
    for p, q in zip(loop, (*loop[1:], loop[0])):
        faces.append((q, p, p + n, q + n))
    return outward(planarize(mesh(name, verts, faces, material)))


def corrugation(x0: float, x1: float, pitch: float = 0.19, amp: float = 0.028) -> list[tuple[float, float]]:
    """Trapezoidal corrugation profile over [x0, x1]: ``(x, height above the valley)`` breakpoints.

    Four breakpoints per pitch (valley, rise, ridge, fall), so a sheet built on these columns
    has planar strips. Shared by the stall roofs and the shack roofs.
    """
    steps = max(2, round((x1 - x0) / pitch)) * 4
    return [(x0 + (x1 - x0) * c / steps, (0.0, amp, amp, 0.0)[c % 4]) for c in range(steps + 1)]


def seat(m: MeshData, top: Callable[[float, float], float]) -> MeshData:
    """Drop (or lift) ``m`` vertically until its lowest point rests on the surface ``top(x, z)``.

    ``top`` is usually a ridge envelope of a corrugated sheet, so the weight touches the ridges
    and never sinks into the sheet (Task 9 roof-tyre lesson). Orient the mesh before seating.
    """
    dy = max(top(v[0], v[2]) - v[1] for v in m.vertices)
    return transformed(m, 0.0, (0.0, dy, 0.0))
