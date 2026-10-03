"""Evidence from source assembly parts, never from claimed metadata counts."""
import math

from .geometry import Assembly

CATEGORIES = frozenset(('architecture', 'shelf', 'merchandise', 'utility', 'lived_in'))


def detail_groups(assembly: Assembly) -> list[dict]:
    """Measure each declared group from the face-referenced vertices of its parts."""
    result = []
    seen_ids: set[str] = set()
    merchandise_parts: set[int] = set()
    groups = assembly.meta.get('detail_groups', ())
    if not isinstance(groups, (list, tuple)):
        raise ValueError('detail_groups must be a sequence')
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError('detail group must be an object')
        identifier, category, indices = (group.get('id'), group.get('category'),
                                         group.get('part_indices'))
        if (type(identifier) is not str or not identifier.strip() or identifier in seen_ids
                or type(category) is not str or category not in CATEGORIES
                or not isinstance(indices, (list, tuple)) or not indices
                or any(type(i) is not int or i < 0 or i >= len(assembly.parts) for i in indices)
                or len(set(indices)) != len(indices)):
            raise ValueError('invalid detail group id, category or part indices')
        seen_ids.add(identifier)
        if category == 'merchandise':
            if merchandise_parts.intersection(indices):
                raise ValueError('part registered as multiple merchandise items')
            merchandise_parts.update(indices)
        points = []
        faces = 0
        for index in indices:
            part = assembly.parts[index]
            if not part.faces or not part.vertices:
                raise ValueError('detail part has no faces or vertices')
            faces += len(part.faces)
            points.extend(part.vertices[i] for face in part.faces for i in face)
        if not points or any(len(v) != 3 or any(type(c) not in (int, float) or not math.isfinite(c)
                                               for c in v) for v in points):
            raise ValueError('invalid face vertices')
        result.append({'id': identifier, 'category': category, 'part_indices': list(indices),
                       'bounds': {'minimum': [min(v[axis] for v in points) for axis in range(3)],
                                  'maximum': [max(v[axis] for v in points) for axis in range(3)]},
                       'vertex_count': len(set(points)), 'face_count': faces})
    return result
