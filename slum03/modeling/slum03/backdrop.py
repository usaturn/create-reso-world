"""Directional city masses: inhabited monumental north, layered low western/southern streets."""
from __future__ import annotations
import random
from .geometry import Assembly, box
from .types import Layout


def _mass(parts, name, center, size, material='backdrop_mass'):
    parts.append(box(name, center, size, material))


def _terraces(p):
    w, h, d = p.size
    parts = []
    for i, (base, tall, fraction) in enumerate(((0, 155, 1.), (155, 150, .9),
                                                 (305, 145, .73), (450, 115, .56),
                                                 (565, h-565, .39))):
        _mass(parts, f'habitation-terrace-{i}', (0, base+tall/2, 0),
              (w*fraction, tall, d*(.88 if i%2 else 1.)),
              'concrete_stained' if i%2 else 'backdrop_mass')
        _mass(parts, f'slab-overhang-{i}', (0, base+tall-3, -d*.06),
              (min(w, w*fraction+7), 6, d*.96), 'concrete_dark')
    for side in (-1, 1):
        for i in range(4):
            _mass(parts, f'balcony-{side}-{i}', (side*(w*.18+i*2), 140+i*125, -d*.48),
                  (w*.29, 11, d*.12), 'steel_dark')
    return parts


def _gate(p):
    w, h, d = p.size
    parts = []
    # Real open gap: two broad inhabited piers and a high occupied lintel.
    for side in (-1, 1):
        _mass(parts, f'pier-{side}', (side*(w*.33), 220, 0), (w*.34, 440, d), 'backdrop_mass')
        _mass(parts, f'buttress-{side}', (side*(w*.425), 160, -d*.18),
              (w*.13, 320, d*.62), 'concrete_dark')
        _mass(parts, f'upper-dwelling-{side}', (side*w*.31, 605, 0),
              (w*.39, 335, d*.8), 'concrete_stained')
        for level in range(3):
            _mass(parts, f'housing-deck-{side}-{level}',
                  (side*w*.33, 130+level*112, -d*.43),
                  (w*.38, 9, d*.2), 'steel_dark')
    _mass(parts, 'gate-habitation-bridge', (0, 477, 0), (w*.98, 74, d), 'backdrop_mass')
    _mass(parts, 'gate-crown', (0, h-12, 0), (w*.94, 24, d*.88), 'concrete_dark')
    return parts


def _linked(p):
    w, h, d = p.size
    parts = []
    for side in (-1, 1):
        _mass(parts, f'tower-{side}', (side*w*.29, h*.48, 0),
              (w*.39, h*.96, d*.81), 'backdrop_mass')
        for i in range(4):
            level = (i+1)*h/5
            _mass(parts, f'floorplate-{side}-{i}', (side*w*.29, level, -d*.09),
                  (w*.45, 12, d*.93), 'concrete_stained')
        _mass(parts, f'head-{side}', (side*w*.29, h*.98, 0),
              (w*.45, h*.04, d*.8), 'concrete_dark')
    for level in (h*.3, h*.53, h*.76):
        _mass(parts, f'habitation-link-{int(level)}', (0, level, -d*.08),
              (w*.32, 25, d*.67), 'concrete_stained')
        _mass(parts, f'link-keel-{int(level)}', (0, level-16, -d*.08),
              (w*.36, 7, d*.36), 'steel_dark')
    return parts


def _highrises(site, seed):
    rng = random.Random(seed + 81)
    result = []
    for i in range(12):
        x = -55 + (i%6)*22 + rng.uniform(-2, 2)
        z = (-13 if i < 6 else 12) + rng.uniform(-4, 4)
        h = rng.uniform(84, 191)
        width = rng.uniform(14, 19)
        parts = []
        _mass(parts, 'tower-shaft', (0, h/2, 0), (width, h, 18), 'backdrop_mass')
        for floor in range(2, int(h//22)):
            _mass(parts, f'deep-floor-{floor}', (0, floor*22, -10),
                  (width+2, 3, 4), 'concrete_stained')
        _mass(parts, 'roof-services', (-2, h+3, 1), (width*.45, 6, 12), 'steel_dark')
        key = f'north-highrise-{i}'
        result.append(Assembly('highrise', key, 'backdrop-north',
                               (site.origin[0]+x, 0, site.origin[2]+z), parts,
                               {'placement_key': key}))
    return result


def _low_city(site, seed, direction):
    rng = random.Random(seed + (91 if direction == 'west' else 92))
    result = []
    for row in range(2):
        for col in range(9):
            if direction == 'west':
                x = site.origin[0] - 11 + row*23 + rng.uniform(-2, 2)
                z = site.origin[2] - 78 + col*19 + rng.uniform(-2, 2)
            else:
                x = site.origin[0] - 51 + col*13 + rng.uniform(-1, 1)
                z = site.origin[2] - 14 + row*27 + rng.uniform(-2, 2)
            h = rng.uniform(14, 39) if row else rng.uniform(23, 53)
            width = 15 if direction == 'west' else 12
            depth = 17 if direction == 'west' else 15
            parts = []
            _mass(parts, 'shell', (0, h/2, 0), (width, h, depth), 'backdrop_mass')
            _mass(parts, 'roof-layer', (.8, h+.8, -1), (width+2, 1.6, depth+2),
                  'concrete_stained')
            _mass(parts, 'lean-annex', (width*.43, h*.24, -depth*.38),
                  (width*.38, h*.48, depth*.53), 'concrete_dark')
            # A few weathered, non-emissive projecting signs anchor the far streets;
            # no inaccessible interiors, no background collision geometry.
            if col % 3 == 0:
                sign_center = ((width*.53, h*.71, -1) if direction == 'west'
                               else (-1, h*.71, depth*.53))
                sign_size = ((.45, 4.5, 6) if direction == 'west'
                             else (6, 4.5, .45))
                _mass(parts, 'distant-sign', sign_center, sign_size, 'paint_yellow_faded')
            for level in range(1, max(2, int(h//8))):
                face_center = ((width*.505, level*8, 0) if direction == 'west'
                               else (0, level*8, depth*.505))
                face_size = ((.65, 1.3, depth*.66) if direction == 'west'
                             else (width*.66, 1.3, .65))
                _mass(parts, f'facade-recess-{level}', face_center,
                      face_size, 'steel_dark')
            key = f'{direction}-city-{row}-{col}'
            result.append(Assembly('low-city', key, 'backdrop-west-south',
                                   (round(x, 4), 0, round(z, 4)), parts,
                                   {'placement_key': key}))
    return result


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    placements = {p.key: p for p in layout.placements}
    if sector == 'backdrop-north':
        result = _highrises(placements['north-towers'], layout.seed)
        for key, builder in (('arcology-terraces', _terraces), ('arcology-gate', _gate),
                             ('arcology-towers', _linked)):
            p = placements[key]
            result.append(Assembly('arcology', key, sector, p.origin, builder(p),
                                   {'placement_key': key, 'silhouette': p.params['silhouette']}))
        return result
    if sector == 'backdrop-west-south':
        return (_low_city(placements['west-city'], layout.seed, 'west') +
                _low_city(placements['south-city'], layout.seed, 'south'))
    raise ValueError(sector)
