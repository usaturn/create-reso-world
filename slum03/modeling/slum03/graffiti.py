"""South-facing non-emissive spray paint; exact glyphs checked in bundled OFL font."""
from __future__ import annotations
import math
from pathlib import Path
from struct import unpack_from
from typing import Any

from .types import Layout, Report

GRAFFITI_TEXT = '稲垣は絶対マカぶる'
FONT_PATH = Path(__file__).resolve().parents[2] / 'assets/fonts/DelaGothicOne-Regular.ttf'


def require_glyphs(text: str, font_path: Path = FONT_PATH) -> None:
    """Read the Unicode cmap of the *actual* font; reject missing glyphs before conversion.

    OpenType format 12 and TrueType format 4 are supported; do not treat .notdef
    or Blender's fallback glyph as a successful font rendering.
    """
    data = font_path.read_bytes()
    u16 = lambda p: unpack_from('>H', data, p)[0]
    u32 = lambda p: unpack_from('>I', data, p)[0]
    table_count = u16(4)
    cmap = None
    for i in range(table_count):
        start = 12 + i * 16
        if data[start:start+4] == b'cmap':
            cmap = u32(start+8)
            break
    if cmap is None:
        raise ValueError(f'font has no cmap: {font_path}')
    candidates = []
    for i in range(u16(cmap+2)):
        entry = cmap + 4 + i*8
        platform, encoding = u16(entry), u16(entry+2)
        off = cmap + u32(entry+4)
        fmt = u16(off)
        if platform in (0, 3) and fmt in (4, 12):
            candidates.append((fmt == 12, platform == 3 and encoding == 10, off))
    if not candidates:
        raise ValueError(f'font has no Unicode cmap: {font_path}')
    offset = max(candidates)[2]
    fmt = u16(offset)

    def present(codepoint):
        if fmt == 12:
            n = u32(offset+12)
            return any(u32(offset+16+j*12) <= codepoint <= u32(offset+20+j*12)
                       and u32(offset+24+j*12) + codepoint - u32(offset+16+j*12) != 0
                       for j in range(n))
        if codepoint > 65535:
            return False
        n = u16(offset+6)//2
        ends = offset+14
        starts = ends + 2*n + 2
        deltas = starts + 2*n
        ranges = deltas + 2*n
        for j in range(n):
            if u16(starts+2*j) <= codepoint <= u16(ends+2*j):
                distance = u16(ranges+2*j)
                glyph = (codepoint + u16(deltas+2*j)) & 65535 if distance == 0 else u16(ranges+2*j+distance+2*(codepoint-u16(starts+2*j)))
                return glyph != 0
        return False

    missing = sorted({c for c in text if not present(ord(c))})
    if missing:
        raise ValueError(f'missing glyph in {font_path.name}: {missing!r}')


def _text_mesh(bpy, font, text, name, size, offset, material, source, export, wall, *, front):
    curve = bpy.data.curves.new(f'{name}_editable', 'FONT')
    curve.body = text
    curve.font = font
    curve.size = size
    curve.offset = offset
    curve.align_x = 'CENTER'
    curve.extrude = .001
    author = bpy.data.objects.new(name+'_Source', curve)
    # Local +Z normal rotated to Blender -Y, exactly the Resonite south face.
    author.rotation_euler[0] = math.pi/2
    author.location = (wall.origin[0], wall.origin[2] - wall.size[2]/2 - front, 3.7)
    source.objects.link(author)
    bpy.context.view_layer.update()
    evaluation = author.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = bpy.data.meshes.new_from_object(evaluation, preserve_all_data_layers=True,
                                           depsgraph=bpy.context.evaluated_depsgraph_get())
    if not mesh.vertices or not mesh.polygons:
        raise ValueError(f'font generated empty mesh: {text!r}')
    mesh.materials.append(material)
    uv = mesh.uv_layers.get('UV0') or mesh.uv_layers.new(name='UV0')
    uv.active_render = True
    for polygon in mesh.polygons:
        for li in polygon.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv = (co.x * .25, co.y * .25)
    copy = bpy.data.objects.new(name, mesh)
    copy.matrix_world = author.matrix_world.copy()
    copy['graffiti_text'] = text
    copy['face_normal_blender'] = [0, -1, 0]
    copy['slum03_kind'] = 'graffiti'
    export.objects.link(copy)
    return copy


def add_graffiti(bpy, layout: Layout, materials: dict, export_collection) -> tuple[list[Any], Report]:
    """Keep source curves in a separate collection; export individually editable static meshes."""
    wall = next(p for p in layout.placements if p.key == 'north-wall')
    text = wall.params['graffiti']
    if text != GRAFFITI_TEXT or wall.params['face'] != 'south':
        raise ValueError('north wall graffiti text or face changed')
    require_glyphs(text)
    font = bpy.data.fonts.load(str(FONT_PATH), check_existing=True)
    font.pack()
    font.use_fake_user = True
    # Export collection's sibling is the editable authoring collection.
    source = bpy.data.collections[export_collection.name.replace('Export', 'Source')]
    black = _text_mesh(bpy, font, text, 'north-wall-graffiti-black', 1.84, .07,
                       materials['spray_black'], source, export_collection, wall, front=.019)
    red = _text_mesh(bpy, font, text, 'north-wall-graffiti-red', 1.80, .0,
                     materials['spray_red'], source, export_collection, wall, front=.047)
    # Gravity streaks and off-target mist remain paint, not light emitters or obstacles.
    from .geometry import Assembly, box, merge_assembly
    from . import blender_io
    from .vcolor import vertex_colors
    import bmesh
    strokes = []
    # Select the lower edge from the *evaluated, transformed* red glyph mesh.
    # No wall-coordinate guesses: a change to font, kerning, or size moves the
    # streaks and nearby overspray with the rendered letters.
    glyph = [red.matrix_world @ vertex.co for vertex in red.data.vertices]
    lo_x, hi_x = min(v.x for v in glyph), max(v.x for v in glyph)
    lo_y, hi_y = min(v.z for v in glyph), max(v.z for v in glyph)
    for fraction, height in ((.10,.42),(.26,.3),(.42,.55),(.58,.36),(.74,.49),(.90,.28)):
        target = lo_x + (hi_x-lo_x)*fraction
        nearby = [v for v in glyph if abs(v.x-target) <= .1]
        if not nearby:
            nearby = [min(glyph, key=lambda v: abs(v.x-target))]
        anchor = min(nearby, key=lambda v: v.z)
        # Follow lower vertices along adjacent strokes until the local lower
        # edge stops descending; this keeps the drip attached to actual paint.
        for _ in range(32):
            lower = min((v for v in glyph if abs(v.x-anchor.x) <= .08), key=lambda v: v.z)
            if lower.z >= anchor.z - 1e-6:
                break
            anchor = lower
        top = anchor.z + .04
        strokes.append(box('spray-drip', (anchor.x-wall.origin[0], top-height/2-wall.origin[1], 0),
                           (.09, height, .008), 'spray_red'))
    for x, y in ((lo_x-.2,hi_y+.12),(lo_x-.36,lo_y+.11),
                 (hi_x+.2,hi_y+.12),(hi_x+.36,lo_y+.11)):
        strokes.append(box('spray-overshoot', (x-wall.origin[0], y-wall.origin[1], 0),
                           (.15, .055, .008), 'spray_black'))
    merged = merge_assembly(Assembly('graffiti', 'north-wall-graffiti-drips', 'plaza',
                                     (0,0,0), strokes))
    # Blender Y coordinate = Resonite north Z; this lies just south of all paint.
    drips, issues = blender_io.create_object(bpy, bmesh, merged,
                                              (0,0,wall.origin[2] - wall.size[2]/2 - .077), materials)
    blender_io.write_colors(drips, vertex_colors(merged, (0,0,0), layout.seed))
    drips['slum03_kind'] = 'graffiti'
    export_collection.objects.link(drips)
    objects = [black, red, drips]
    return objects, {'objects': [{'key':obj.name, 'kind':'graffiti', 'mesh':obj.name} for obj in objects],
                     'uv_issues': issues, 'errors': []}
