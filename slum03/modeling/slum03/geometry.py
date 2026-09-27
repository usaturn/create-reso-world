"""Deterministic local primitives in Resonite XYZ (Y up, metres)."""
from __future__ import annotations
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

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


def rotate_y(point: Sequence[float], radians: float) -> Vec3:
    c, s = math.cos(radians), math.sin(radians)
    x, y, z = point
    return (x * c + z * s, y, -x * s + z * c)


def bounds(meshes: Iterable[MeshData]) -> tuple[Vec3, Vec3]:
    pts = [v for m in meshes for v in m.vertices]
    if not pts:
        raise ValueError("bounds of nothing")
    return (tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3)))  # type: ignore[return-value]


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


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


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
