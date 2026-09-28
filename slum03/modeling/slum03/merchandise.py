"""Small, recognizable merchandise, authored at the origin of each display cell.

Origins are local to the stall (shelf contact, not world coordinates). A stock
Assembly is temporary: the stall builder folds its parts into one export mesh.
"""
from __future__ import annotations

from .density_model import stable_seed
from .geometry import Assembly, MeshData, box, tube
from .types import Placement

VARIANTS = ('electronics', 'tools', 'prosthetics', 'reclaimed_equipment')


def _electronic(motif: int) -> list[MeshData]:
    if motif % 3 == 0:  # horizontal PCB with a raised chip and bus traces
        return [box('circuit-board', (0, .035, 0), (.26, .07, .25), 'electronics'),
                box('chip', (0, .092, -.02), (.1, .045, .08), 'steel_dark'),
                *[box('contact', (x, .073, .085), (.022, .012, .07), 'steel_bare')
                  for x in (-.09, -.04, .04, .09)]]
    if motif % 3 == 1:  # standing display, actual separate +Z screen and foot
        return [box('monitor-foot', (0, .02, 0), (.23, .04, .19), 'steel_bare'),
                box('monitor', (0, .235, -.01), (.25, .38, .095), 'steel_dark'),
                box('monitor-screen', (0, .24, .044), (.205, .29, .012), 'glass_dark'),
                box('monitor-neck', (0, .09, -.01), (.04, .12, .04), 'steel_bare')]
    return [box('radio-base', (0, .09, 0), (.25, .18, .23), 'steel_dark'),
            box('radio-dial', (-.065, .13, .122), (.07, .07, .02), 'glass_dark'),
            tube('antenna', [(-.085, .18, -.07), (-.055, .45, -.09)], .013, 6, 'steel_bare')]


def _tool(motif: int) -> list[MeshData]:
    if motif % 3 == 0:  # hammer laid across the shelf
        return [tube('hammer-grip', [(0, .029, -.11), (0, .029, .11)], .029, 6, 'pallet_wood'),
                box('hammer-head', (0, .075, .115), (.23, .1, .06), 'steel_bare')]
    if motif % 3 == 1:  # spanner jaws leave a visible central gap
        return [box('spanner-shaft', (0, .047, 0), (.05, .094, .24), 'steel_bare'),
                box('spanner-jaw', (-.09, .048, .115), (.065, .09, .065), 'steel_bare'),
                box('spanner-jaw', (.09, .048, .115), (.065, .09, .065), 'steel_bare'),
                box('spanner-neck', (0, .048, .083), (.16, .09, .03), 'rust_dark')]
    return [box('driver-handle', (0, .055, -.055), (.12, .11, .16), 'rubber'),
            tube('driver-shaft', [(0, .055, .03), (0, .055, .16)], .021, 8, 'steel_bare'),
            box('driver-tip', (0, .055, .17), (.06, .043, .04), 'rust')]


def _limb(motif: int) -> list[MeshData]:
    # Three articulated types: forearm, hand, and knee brace; none is a plain cuboid.
    if motif % 3 == 0:
        return [box('socket', (0, .045, -.09), (.23, .09, .105), 'rubber'),
                tube('forearm', [(0, .06, -.07), (0, .19, .05), (0, .06, .13)],
                     .036, 8, 'steel_bare'),
                box('elbow', (0, .19, .05), (.11, .1, .095), 'rust_dark')]
    if motif % 3 == 1:
        return [box('palm', (0, .035, -.035), (.17, .07, .15), 'steel_bare'),
                *[tube('finger', [(x, .05, .025), (x, .11, .13)], .018, 6, 'steel_dark')
                  for x in (-.065, 0, .065)],
                box('cuff', (0, .045, -.125), (.21, .09, .07), 'rubber')]
    return [tube('knee-rail', [(-.08, .045, -.11), (-.08, .13, 0), (-.08, .045, .12)],
                 .024, 6, 'steel_bare'),
            tube('knee-rail', [(.08, .045, -.11), (.08, .13, 0), (.08, .045, .12)],
                 .024, 6, 'steel_bare'),
            box('knee-hinge', (0, .13, 0), (.21, .08, .08), 'rust_dark'),
            box('cuff', (0, .045, -.1), (.23, .09, .055), 'rubber')]


def _reclaimed(motif: int) -> list[MeshData]:
    if motif % 3 == 0:  # open crate: rim + rails, no lid covering the mouth
        return [box('crate-floor', (0, .025, 0), (.26, .05, .24), 'plastic_crate'),
                *[box('crate-wall', (x, .105, 0), (.025, .16, .24), 'rust_dark')
                  for x in (-.115, .115)],
                *[box('crate-wall', (0, .105, z), (.21, .16, .026), 'rust_dark')
                  for z in (-.105, .105)]]
    if motif % 3 == 1:  # salvaged motor with shaft and cooling fins
        return [box('motor', (0, .105, -.015), (.21, .21, .21), 'steel_dark'),
                tube('drive-shaft', [(0, .12, .08), (0, .12, .17)], .026, 8, 'steel_bare'),
                *[box('cooling-fin', (x, .215, -.015), (.025, .04, .19), 'rust')
                  for x in (-.065, 0, .065)]]
    return [box('pump-foot', (0, .025, 0), (.25, .05, .22), 'steel_dark'),
            box('pump-case', (0, .125, -.02), (.18, .18, .17), 'paint_yellow_faded'),
            tube('pump-elbow', [(0, .16, .04), (0, .26, .04), (.09, .26, .04)],
                 .024, 8, 'steel_bare', ref=(0., 0., 1.))]


_BUILDERS = {'electronics': _electronic, 'tools': _tool,
             'prosthetics': _limb, 'reclaimed_equipment': _reclaimed}


def stock_items(p: Placement, seed: int) -> list[Assembly]:
    """Twelve local display-cell assemblies, never separately exported."""
    variant = p.params['variant']
    if variant not in VARIANTS:
        raise ValueError(f'unknown stall variant: {variant}')
    w, _, d = p.size
    step = (w - .6) / 6
    items = []
    for row, top in enumerate((.99, 1.72)):
        for column in range(6):
            index = row*6 + column
            jitter = (stable_seed(seed, p.key, f'stock-{index}') / (2**256-1) - .5)*.024
            x = -w/2 + .3 + step*(column+.5) + jitter
            z = -d/2 + .82
            items.append(Assembly('merchandise', f'{p.key}-stock-{index:02d}', p.sector,
                                  (x, top, z), _BUILDERS[variant](index),
                                  {'variant': variant}))
    return items
