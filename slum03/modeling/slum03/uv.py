"""Metric, face-local UV projections for slum03 meshes (ported from akichi)."""
from __future__ import annotations

import math
from collections.abc import Sequence

Vec3 = tuple[float, float, float]
Vec2 = tuple[float, float]


def uv_triangle_issues(
    points: Sequence[Sequence[float]],
    uvs: Sequence[Sequence[float]],
    normal: Sequence[float],
    uv_per_meter: float = 0.5,
    handedness: int = 1,
) -> list[str]:
    """Audit one triangle's UV area, orientation and metre-based edge scale.

    Pass handedness=-1 after an XZY coordinate conversion; do not use this
    metric-tiling check for a deliberately spherical or unique texture atlas.
    """
    if (len(points) != 3 or len(uvs) != 3 or len(normal) != 3
            or any(len(p) != 3 for p in points) or any(len(uv) != 2 for uv in uvs)
            or not math.isfinite(uv_per_meter) or uv_per_meter <= 0 or handedness not in (-1, 1)):
        raise ValueError("UV audit needs three XYZ/UV corners, a normal, positive scale and valid handedness")
    try:
        xyz = [tuple(float(value) for value in point) for point in points]
        uv = [tuple(float(value) for value in corner) for corner in uvs]
        surface_normal = tuple(float(value) for value in normal)
    except (TypeError, ValueError) as exc:
        raise ValueError("UV audit coordinates must be numeric") from exc
    ab = tuple(xyz[1][axis] - xyz[0][axis] for axis in range(3))
    ac = tuple(xyz[2][axis] - xyz[0][axis] for axis in range(3))
    cross = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
    if math.sqrt(sum(value * value for value in cross)) <= 2e-9:
        return []  # A geometric zero-area triangle has no meaningful UV density.
    uv_ab = (uv[1][0] - uv[0][0], uv[1][1] - uv[0][1])
    uv_ac = (uv[2][0] - uv[0][0], uv[2][1] - uv[0][1])
    signed_uv_area = (uv_ab[0] * uv_ac[1] - uv_ab[1] * uv_ac[0]) / 2
    if not math.isfinite(signed_uv_area) or abs(signed_uv_area) <= 1e-10:
        return ["zero UV area"]
    issues = []
    if signed_uv_area * sum(cross[axis] * surface_normal[axis] for axis in range(3)) * handedness < 0:
        issues.append("reversed orientation")
    for first, second in ((0, 1), (1, 2), (2, 0)):
        world_length = math.dist(xyz[first], xyz[second])
        if world_length <= 1e-9:
            continue
        scale = math.dist(uv[first], uv[second]) / world_length
        if not math.isfinite(scale) or abs(scale / uv_per_meter - 1) > 0.02:
            issues.append("metric distortion")
            break
    return issues


def metric_face_uvs(points: Sequence[Sequence[float]], normal: Sequence[float], uv_per_meter: float = 0.5) -> list[Vec2]:
    """Project one planar face to an aspect-preserving, metre-scaled local UV island."""
    if (len(points) < 3 or len(normal) != 3 or any(len(point) != 3 for point in points)
            or not math.isfinite(uv_per_meter) or uv_per_meter <= 0):
        raise ValueError("a UV face needs XYZ points, a normal and positive texel density")
    try:
        coordinates: list[Vec3] = [(float(point[0]), float(point[1]), float(point[2])) for point in points]
        surface_normal: Vec3 = (float(normal[0]), float(normal[1]), float(normal[2]))
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError("UV points and normal must contain numeric XYZ coordinates") from exc
    center: Vec3 = (
        sum(point[0] for point in coordinates) / len(coordinates),
        sum(point[1] for point in coordinates) / len(coordinates),
        sum(point[2] for point in coordinates) / len(coordinates),
    )
    normal_length = math.sqrt(sum(value * value for value in surface_normal))
    if normal_length <= 1e-12:
        raise ValueError("a UV face needs a nonzero surface normal")
    unit_normal: Vec3 = (surface_normal[0] / normal_length, surface_normal[1] / normal_length, surface_normal[2] / normal_length)
    edges: list[tuple[float, Vec3]] = []
    for point, following in zip(coordinates, (*coordinates[1:], coordinates[0])):
        edge: Vec3 = (following[0] - point[0], following[1] - point[1], following[2] - point[2])
        length = math.sqrt(sum(value * value for value in edge))
        if length > 1e-12:
            edges.append((length, edge))
    if not edges:
        raise ValueError("a UV face cannot have zero-length boundary edges")
    # A collinear face has no valid UV island even if its longest edge exists.
    for _, edge in edges[1:]:
        a, b = edges[0][1], edge
        area = ((a[1] * b[2] - a[2] * b[1]) ** 2 +
                (a[2] * b[0] - a[0] * b[2]) ** 2 +
                (a[0] * b[1] - a[1] * b[0]) ** 2)
        if area > 1e-20:
            break
    else:
        raise ValueError("zero-area UV face")
    _length, longest = max(edges, key=lambda item: item[0])
    projection = sum(longest[axis] * unit_normal[axis] for axis in range(3))
    tangent_raw: Vec3 = tuple(longest[axis] - projection * unit_normal[axis] for axis in range(3))  # type: ignore[assignment]
    tangent_length = math.sqrt(sum(value * value for value in tangent_raw))
    if tangent_length <= 1e-12:
        raise ValueError("the longest UV boundary edge is parallel to its normal")
    tangent: Vec3 = (tangent_raw[0] / tangent_length, tangent_raw[1] / tangent_length, tangent_raw[2] / tangent_length)
    bitangent: Vec3 = (
        unit_normal[1] * tangent[2] - unit_normal[2] * tangent[1],
        unit_normal[2] * tangent[0] - unit_normal[0] * tangent[2],
        unit_normal[0] * tangent[1] - unit_normal[1] * tangent[0],
    )
    return [
        (
            sum((point[axis] - center[axis]) * tangent[axis] for axis in range(3)) * uv_per_meter,
            sum((point[axis] - center[axis]) * bitangent[axis] for axis in range(3)) * uv_per_meter,
        )
        for point in coordinates
    ]
