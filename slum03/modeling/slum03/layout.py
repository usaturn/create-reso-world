"""Deterministic offline plan, validation and explicit JSON wire format."""
import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path

from . import config
from .layout_ads import ad_labels, ad_placements
from .layout_district import district_labels, district_placements
from .layout_environment import environment_placements
from .spatial import placement_bounds, validate_clearance
from .types import Issue, LabelSpec, Layout, Placement, RectXZ, Viewpoint


VIEWPOINTS = (
    Viewpoint('plaza-north', (0, 1.6, -6), 'north_arcologies'),
    Viewpoint('east-forest', (63, 1.6, 0), 'east_forest'),
    Viewpoint('bridge-checkpoint', (63, 1.6, 50), 'checkpoint'),
    Viewpoint('west-city', (-54, 1.6, 0), 'west_city'),
    Viewpoint('south-market', (0, 1.6, -52), 'south_city'),
    Viewpoint('ar-hero', (0, 1.6, -28), 'ads'),
)
REQUIRED = ('north-wall', 'yarol', 'bridge', 'checkpoint', 'forest',
            'arcology-terraces', 'arcology-gate', 'arcology-towers',
            'west-city', 'south-city', 'west-sidewalk', 'roadway', 'east-sidewalk',
            'north-turnback')
DOMAINS = {'district', 'road', 'water', 'background'}


def build_layout(seed: int = config.DEFAULT_SEED) -> Layout:
    """Fixed anchors do not drift when changing seed; variation belongs in sectors."""
    if type(seed) is not int:
        raise ValueError('seed must be an integer')
    layout = Layout(seed, config.DISTRICT, config.PLAZA, config.CLEAR,
                    config.ROUTES,
                    district_placements() + ad_placements() + environment_placements(),
                    VIEWPOINTS, district_labels() + ad_labels())
    issues = validate_layout(layout)
    if issues:
        raise ValueError(f'invalid built layout: {issues}')
    return layout


def _finite(values) -> bool:
    return all(isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(v) for v in values)


def _rect_valid(rect: RectXZ) -> bool:
    return (_finite(rect.bounds) and rect.x_min < rect.x_max and
            rect.z_min < rect.z_max)


def _params_finite(value) -> bool:
    if isinstance(value, dict):
        return all(_params_finite(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return all(_params_finite(v) for v in value)
    return not isinstance(value, float) or math.isfinite(value)


def validate_layout(layout: Layout) -> list[Issue]:
    issues = []
    if type(layout.seed) is not int:
        issues.append(Issue('SEED', 'layout', 'seed must be an integer'))
    for key, rect, expected in (('district', layout.district, config.DISTRICT),
                                ('plaza', layout.plaza, config.PLAZA),
                                ('clear', layout.clear, config.CLEAR)):
        if not _rect_valid(rect) or rect != expected:
            issues.append(Issue('DIMENSIONS', key, 'invalid or changed footprint'))
    if len(layout.routes) != len(config.ROUTES) or any(
            not _rect_valid(r) or min(r.size) < 3 for r in layout.routes):
        issues.append(Issue('ROUTES', 'routes', '3m continuous route is missing'))
    elif layout.routes != config.ROUTES:
        issues.append(Issue('ROUTES', 'routes', 'entrance/bridge route has moved'))

    seen = set()
    valid_placements = {}
    for p in layout.placements:
        if not p.key or p.key in seen:
            issues.append(Issue('KEY', p.key, 'missing or duplicate placement key'))
        seen.add(p.key)
        if (p.domain not in DOMAINS or not p.sector or not p.kind or
                not _finite((*p.origin, *p.size, p.yaw_deg)) or
                any(s <= 0 for s in p.size) or not _params_finite(p.params) or
                not _finite((p.params.get('local_y_min', 0),))):
            issues.append(Issue('PLACEMENT', p.key, 'invalid domain, size, pose or parameters'))
        else:
            valid_placements[p.key] = p
    for key in REQUIRED:
        if key not in seen:
            issues.append(Issue('MISSING', key, 'required anchor missing'))
    if 'east-wall' in seen:
        issues.append(Issue('WALL', 'east-wall', 'old factory east wall is forbidden'))
    wall = valid_placements.get('north-wall')
    if wall and (wall.origin != (0., 0., 14.5) or wall.size != (36., 10., .8)
                 or wall.params.get('face') != 'south'
                 or wall.params.get('graffiti') != '稲垣は絶対マカぶる'):
        issues.append(Issue('WALL', 'north-wall', 'north wall location/face changed'))
    yarol = valid_placements.get('yarol')
    if yarol and (yarol.yaw_deg != 90 or yarol.params.get('entrance') != 'east'):
        issues.append(Issue('ENTRANCE', 'yarol', 'east-facing entrance required'))
    if yarol:
        b = placement_bounds(yarol)
        if (b.minimum[0] < 43 or b.maximum[0] > 59 or
                b.minimum[2] < 40 or b.maximum[2] > 54 or
                yarol.domain != 'district'):
            issues.append(Issue('ENTRANCE', 'yarol', 'rotated site must fit northeast lot'))
    for key, domain in (('west-sidewalk', 'road'), ('roadway', 'road'),
                        ('east-sidewalk', 'road'), ('bridge', 'road'),
                        ('checkpoint', 'road'), ('north-turnback', 'road'),
                        ('river', 'water'), ('west-city', 'background'),
                        ('south-city', 'background')):
        p = valid_placements.get(key)
        if p and p.domain != domain:
            issues.append(Issue('DOMAIN', key, f'expected {domain} domain'))
    for key, rect in (('west-sidewalk', config.WEST_SIDEWALK),
                      ('roadway', config.ROADWAY), ('east-sidewalk', config.EAST_SIDEWALK),
                      ('bridge', config.BRIDGE), ('river', config.RIVER)):
        p = valid_placements.get(key)
        if p:
            b = placement_bounds(p)
            if (b.minimum[0], b.maximum[0], b.minimum[2], b.maximum[2]) != rect.bounds:
                issues.append(Issue('DIMENSIONS', key, 'road/water bounds changed'))
    forest = valid_placements.get('forest')
    if forest and (forest.domain != 'background' or
                   placement_bounds(forest).minimum[0] < 100):
        issues.append(Issue('FOREST', 'forest', 'forest must begin east of x=100'))
    checkpoint = valid_placements.get('checkpoint')
    if checkpoint and (checkpoint.params.get('open') is not True or
                       not _finite((checkpoint.params.get('opening_width'),)) or
                       checkpoint.params['opening_width'] < 3):
        issues.append(Issue('ENTRANCE', 'checkpoint', 'bridge checkpoint must remain open'))
    for v in VIEWPOINTS:
        if v not in layout.viewpoints:
            issues.append(Issue('VIEWPOINT', v.key, 'required viewpoint missing or moved'))
    for key in ('arcology-terraces', 'arcology-gate', 'arcology-towers'):
        p = valid_placements.get(key)
        if p and (p.domain != 'background' or not 500 <= p.size[1] <= 900
                  or p.origin[2] <= config.RIVER.z_max):
            issues.append(Issue('SKYLINE', key, 'arcology must be beyond north river'))
    if len({v.key for v in layout.viewpoints}) != len(layout.viewpoints):
        issues.append(Issue('KEY', 'viewpoints', 'duplicate viewpoint'))
    for v in layout.viewpoints:
        if not _finite(v.eye):
            issues.append(Issue('VIEWPOINT', v.key, 'invalid eye'))
    if len({l.key for l in layout.labels}) != len(layout.labels):
        issues.append(Issue('KEY', 'labels', 'duplicate label'))
    for l in layout.labels:
        if (l.parent_name not in seen or not l.text or
                not _finite((*l.offset, l.yaw_deg, l.height, *l.color)) or
                l.height <= 0):
            issues.append(Issue('LABEL', l.key, 'invalid or orphaned label'))
    issues.extend(validate_clearance(layout, {key: placement_bounds(p)
                  for key, p in valid_placements.items()}))
    return issues


def write_layout(layout: Layout, path: Path) -> None:
    issues = validate_layout(layout)
    if issues:
        raise ValueError(f'invalid layout: {issues}')
    payload = json.dumps(asdict(layout), ensure_ascii=False, sort_keys=True,
                         allow_nan=False, indent=2) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding='utf-8')


def read_layout(path: Path) -> Layout:
    def reject_constant(value):
        raise ValueError(f'non-finite JSON number: {value}')

    data = json.loads(path.read_text(encoding='utf-8'), parse_constant=reject_constant)
    try:
        rect = lambda r: RectXZ(**r)
        layout = Layout(
            seed=data['seed'], district=rect(data['district']),
            plaza=rect(data['plaza']), clear=rect(data['clear']),
            routes=tuple(rect(r) for r in data['routes']),
            placements=tuple(Placement(p['key'], p['sector'], p['kind'],
                                       tuple(p['origin']), tuple(p['size']),
                                       p['yaw_deg'], p['domain'], p['params'])
                             for p in data['placements']),
            viewpoints=tuple(Viewpoint(v['key'], tuple(v['eye']), v['target_group'])
                             for v in data['viewpoints']),
            labels=tuple(LabelSpec(l['key'], l['text'], l['parent_name'],
                                   tuple(l['offset']), l['yaw_deg'], l['height'],
                                   tuple(l['color'])) for l in data['labels']))
    except (KeyError, TypeError) as e:
        raise ValueError('invalid layout JSON structure') from e
    issues = validate_layout(layout)
    if issues:
        raise ValueError(f'invalid layout JSON: {issues}')
    return layout


def main() -> None:
    parser = argparse.ArgumentParser(description='Write deterministic slum03 layout')
    parser.add_argument('--seed', type=int, default=config.DEFAULT_SEED)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    write_layout(build_layout(args.seed), args.output)
    if read_layout(args.output) != build_layout(args.seed):
        raise ValueError('layout failed readback')


if __name__ == '__main__':
    main()
