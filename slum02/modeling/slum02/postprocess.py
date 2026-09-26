"""Postprocess the merged slum02 manifest (Task 14).

Runs after ``pipeline.merge_bundles`` on the unified apply document:

* ``FrooxEngine.PBS_Metallic`` providers (``mat_material_Slum02_<name>_<8hex>``)
  become ``PBS_VertexColorMetallic`` (``vc``/``neon`` kinds) or
  ``FresnelMaterial`` (``holo`` kinds) following ``materials.MATERIALS``.
* A ``textures`` Slot carries one ``NoiseTexture`` per ``materials.NOISES``
  entry; vertex-colour materials point at ``tex-noise-<noise>`` and every holo
  points at ``tex-noise-holo``.
* Each ``*_scroll`` holo material gets two ``Panner2D`` drivers (near/far
  texture offsets) on the ``textures`` Slot; each ``ad-NN-panel`` Slot gets a
  ``Spinner`` on its ``Rotation``.
* One ``Light`` per ``layout["lights"]`` entry (Spot adds ``SpotAngle``),
  ``BoxCollider`` slots for the brief's collider list, and ``TextRenderer``
  slots for ``layout["signs"]``. When ``reports["plaza"]["spray_art"]
  ["method"] == "text-renderer"`` the east wall gets two extra TextRenderers
  (black outline behind, red fill 0.01 m in front) in place of the font mesh.

Everything added by this module uses stable keys and is skipped when already
present, so ``postprocess`` is idempotent.
"""
from __future__ import annotations

import math
import re
from typing import Any

from modeling.slum02.materials import MATERIALS, NOISES

# Measured on 2026-09-26 (artifacts/slum02/probe-vertex-color.json): the exporter
# copies FLOAT_COLOR/POINT values verbatim - no sRGB encode, no clamp.
VERTEX_COLOR_SPACE = "Linear"

_MATERIAL_KEY = re.compile(r"mat_material_Slum02_(.+)_[0-9a-f]{8}$")
_AD_PANEL_NAME = re.compile(r"ad-\d{2}-panel")

PBS_METALLIC = "FrooxEngine.PBS_Metallic"
VC_METALLIC = "FrooxEngine.PBS_VertexColorMetallic"
FRESNEL = "FrooxEngine.FresnelMaterial"

# The four PBS_Metallic fields carried over verbatim into the converted material.
_CARRIED_FIELDS = ("AlbedoColor", "Metallic", "Smoothness", "EmissiveColor")

_QUATERNION_DECIMALS = 8
_POSITION_DECIMALS = 3

# Group slots appended to the root children, in order.
GROUP_SLOTS = ("textures", "lights", "colliders", "signs")


def material_name(component_key: str) -> str | None:
    """Parse ``mat_material_Slum02_<name>_<8hex>`` back into the palette name."""
    match = _MATERIAL_KEY.fullmatch(component_key)
    return match.group(1) if match else None


def convert_material(component: dict[str, Any], name: str) -> dict[str, Any]:
    """Convert one exported PBS_Metallic component into its runtime material."""
    spec = MATERIALS[name]
    if spec.kind == "holo":
        emission = list(spec.emission)
        return {
            "key": component["key"],
            "type": FRESNEL,
            "fields": {
                "NearColor": [c * 0.35 for c in emission] + [0.25],
                "FarColor": [min(1.0, c * 1.2) for c in emission] + [0.85],
                "Exponent": 1.6,
                "GammaCurve": 1.0,
                "BlendMode": "Additive",
                "Sidedness": "Double",
                "ZWrite": "Off",
                "UseVertexColors": False,
                "NearTexture": "$component:tex-noise-holo",
                "FarTexture": "$component:tex-noise-holo",
                "NearTextureScale": list(spec.texture_scale),
                "FarTextureScale": list(spec.texture_scale),
            },
        }
    fields = {k: component.get("fields", {})[k] for k in _CARRIED_FIELDS if k in component.get("fields", {})}
    fields.update(
        {
            "VertexColorTarget": "Albedo",
            "VertexColorInterpolationSpace": VERTEX_COLOR_SPACE,
            "AlphaHandling": "Opaque",
            "Culling": "Back",
            "TextureScale": list(spec.texture_scale),
        }
    )
    if spec.noise:
        fields["AlbedoTexture"] = f"$component:tex-noise-{spec.noise}"
    return {"key": component["key"], "type": VC_METALLIC, "fields": fields}


def _noise_component(name: str) -> dict[str, Any]:
    n = NOISES[name]
    return {
        "key": f"tex-noise-{name}",
        "type": "FrooxEngine.NoiseTexture",
        # Six same-type components share the textures Slot; the seed is the
        # immutable per-noise distinction the validator asks for.
        "identityFields": ["Seed"],
        "fields": {
            "Size": [n.size, n.size],
            "Seed": n.seed,
            "Monochrome": True,
            "MonochromeMin": [n.low, n.low, n.low, 1.0],
            "MonochromeMax": [n.high, n.high, n.high, 1.0],
            "Bias": n.bias,
            "Gain": n.gain,
            "FilterMode": "Anisotropic",
            "WrapModeU": "Repeat",
            "WrapModeV": "Repeat",
            "Mipmaps": True,
        },
    }


def texture_slot() -> dict[str, Any]:
    """The ``textures`` Slot carrying every engine-side NoiseTexture."""
    return {
        "slot": {"key": "textures", "name": "Slum02_Textures",
                 "position": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]},
        "components": [_noise_component(name) for name in NOISES],
    }


def _yaw_quaternion(degrees: float) -> list[float]:
    """Y-axis quaternion for a yaw in degrees (layout's convention)."""
    half = math.radians(degrees) / 2.0
    return [0.0, round(math.sin(half), _QUATERNION_DECIMALS), 0.0,
            round(math.cos(half), _QUATERNION_DECIMALS)]


def _yaw(x: float, z: float, degrees: float) -> tuple[float, float]:
    """Rotate a local XZ offset into world by a yaw in degrees (layout._yaw)."""
    a = math.radians(degrees)
    return x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)


def _direction_quaternion(d: tuple[float, float, float]) -> list[float]:
    """Quaternion rotating local +Y onto the normalised direction ``d``."""
    x, y, z = d
    cos_a = max(-1.0, min(1.0, y))
    if cos_a > 1.0 - 1e-9:
        return [0.0, 0.0, 0.0, 1.0]
    ax, ay, az = z, 0.0, -x  # +Y x d
    norm = math.sqrt(ax * ax + ay * ay + az * az)
    if norm < 1e-9:  # d ~ -Y: flip about X
        return [1.0, 0.0, 0.0, 0.0]
    s = math.sqrt((1.0 - cos_a) / 2.0) / norm
    return [round(ax * s, _QUATERNION_DECIMALS), round(ay * s, _QUATERNION_DECIMALS),
            round(az * s, _QUATERNION_DECIMALS), round(math.sqrt((1.0 + cos_a) / 2.0), _QUATERNION_DECIMALS)]


def _box_collider(key: str, size: list[float]) -> dict[str, Any]:
    return {
        "key": key,
        "type": "FrooxEngine.BoxCollider",
        "fields": {"Enabled": True, "Type": "Static", "CharacterCollider": True,
                   "Offset": [0.0, 0.0, 0.0], "Size": size},
    }


def light_slots(layout: dict[str, Any]) -> list[dict[str, Any]]:
    """One ``FrooxEngine.Light`` Slot per ``layout["lights"]`` entry."""
    slots: list[dict[str, Any]] = []
    for l in layout["lights"]:
        fields: dict[str, Any] = {
            "LightType": l["type"],
            "Intensity": l["intensity"],
            "Color": list(l["color"]),
            "Range": l["range"],
            "ShadowType": l["shadow"],
        }
        if l["type"] == "Spot":
            fields["SpotAngle"] = l["spot_angle"]
        number = l["id"].removeprefix("light-")
        slots.append({
            "slot": {"key": l["id"], "name": f"Light {number}",
                     "position": list(l["position"]), "rotation": list(l["rotation"]),
                     "scale": [1, 1, 1]},
            "components": [{"key": f"{l['id']}-light", "type": "FrooxEngine.Light", "fields": fields}],
        })
    return slots


def _static_box(key: str, name: str, center: list[float], size: list[float],
                rotation_deg: float = 0.0) -> dict[str, Any]:
    return {
        "slot": {"key": key, "name": name,
                 "position": [round(c, _POSITION_DECIMALS) for c in center],
                 "rotation": _yaw_quaternion(rotation_deg), "scale": [1, 1, 1]},
        "components": [_box_collider(f"{key}-box", size)],
    }


# Plaza machinery collider boxes in machine-local coordinates
# (centre offset from the machine origin on the floor, box extents).
MACHINE_COLLIDERS: dict[str, tuple[list[float], list[float]]] = {
    # press: bed/uprights/crown +-1.55 x, flywheel to x 2.53, hoses to z -1.6, ~5.9 m tall
    "press": ([0.5, 3.0, -0.2], [4.2, 6.0, 2.9]),
    # conveyor: rails x -3..3.3, motor/gearbox to z 1.4, belt low over collapsed end
    "conveyor": ([0.15, 0.55, 0.4], [6.3, 1.15, 2.0]),
    # tank: shell +-0.78 x / +-2.5 z, leaning ladder and fallen manway cover on -x
    "tank": ([-0.55, 1.0, 0.2], [2.7, 2.0, 4.6]),
}

# Burnt car: body 4.2 x 1.8 plus bumper/plate and wheel hubs.
CAR_COLLIDER = ([0.0, 0.75, 0.0], [4.4, 1.5, 2.0])

# Stall counter: plywood top at 0.9 m on stacked crates, on the lane side.
STALL_COUNTER_HEIGHT = 0.9


def collider_slots(layout: dict[str, Any]) -> list[dict[str, Any]]:
    """Static CharacterCollider boxes for the brief's collider list."""
    slots: list[dict[str, Any]] = [
        _static_box("collider-ground", "Ground Collider", [0.0, 0.0, 0.0], [80.0, 0.2, 80.0]),
    ]
    for t in layout["towers"]:
        slots.append(_static_box(
            f"collider-{t['id']}", f"{t['id']} Collider",
            [t["center"][0], t["height"] / 2.0, t["center"][1]],
            [t["footprint"][0], t["height"], t["footprint"][1]], t["rotation"]))
    wall = layout["east_wall"]
    slots.append(_static_box(
        "collider-east-wall", "East Wall Collider",
        [wall["center"][0], wall["size"][1] / 2.0, wall["center"][2]], list(wall["size"])))
    for c in layout["clubs"]:
        slots.append(_static_box(
            f"collider-{c['id']}", f"{c['id']} Collider",
            [c["center"][0], c["height"] / 2.0, c["center"][1]],
            [c["size"][0], c["height"], c["size"][1]], c["rotation"]))
    for s in layout["stalls"]:
        # Counter box in stall-local coords: plywood top + crates on the lane side.
        w, d = s["size"]
        local = (0.0, STALL_COUNTER_HEIGHT / 2.0, d / 2 - 0.2 - 0.26)
        ox, oz = _yaw(local[0], local[2], s["rotation"])
        slots.append(_static_box(
            f"collider-{s['id']}", f"{s['id']} Counter Collider",
            [s["center"][0] + ox, local[1], s["center"][1] + oz],
            [w - 0.55, STALL_COUNTER_HEIGHT, 0.6], s["rotation"]))
    for s in layout["shacks"]:
        slots.append(_static_box(
            f"collider-{s['id']}", f"{s['id']} Collider",
            [s["center"][0], s["height"] / 2.0, s["center"][1]],
            [s["size"][0], s["height"], s["size"][1]], s["rotation"]))
    feats = layout["plaza_features"]
    for x, z, yaw, kind in feats["machines"]:
        (lx, ly, lz), size = MACHINE_COLLIDERS[kind]
        ox, oz = _yaw(lx, lz, yaw)
        slots.append(_static_box(
            f"collider-plaza-{kind}", f"Plaza {kind.capitalize()} Collider",
            [x + ox, ly, z + oz], size, yaw))
    cx, cz, cyaw = feats["car"]
    (lx, ly, lz), size = CAR_COLLIDER
    ox, oz = _yaw(lx, lz, cyaw)
    slots.append(_static_box(
        "collider-plaza-car", "Plaza Car Collider", [cx + ox, ly, cz + oz], size, cyaw))
    # Columns lean toward the plaza centre by up to 25 deg; the box follows the shaft.
    base_y = 0.185  # plaza FLOOR_TOP + grout/baseplate
    for k, (x, z, tilt_deg, height) in enumerate(feats["columns"]):
        broken = k == 4
        shaft = height * 0.5 if broken else height - base_y
        t = math.radians(tilt_deg)
        tn = math.sqrt(x * x + 0.09 * z * z)
        tilt = (-x / tn, -0.3 * z / tn) if tn > 1e-9 else (0.0, 0.0)
        d = (tilt[0] * math.sin(t), math.cos(t), tilt[1] * math.sin(t))
        mid = (x + d[0] * shaft / 2.0, base_y + d[1] * shaft / 2.0, z + d[2] * shaft / 2.0)
        slots.append({
            "slot": {"key": f"collider-column-{k + 1:02d}", "name": f"Column {k + 1:02d} Collider",
                     "position": [round(c, _POSITION_DECIMALS) for c in mid],
                     "rotation": _direction_quaternion(d), "scale": [1, 1, 1]},
            "components": [_box_collider(f"collider-column-{k + 1:02d}-box", [0.55, shaft + 0.3, 0.55])],
        })
    return slots


def sign_slots(layout: dict[str, Any], spray_method: str | None = None) -> list[dict[str, Any]]:
    """TextRenderer slots for ``layout["signs"]`` (+ east-wall fallback)."""
    slots: list[dict[str, Any]] = []
    for s in layout["signs"]:
        number = s["id"].removeprefix("sign-")
        slots.append({
            "slot": {"key": s["id"], "name": f"Sign {number}",
                     "position": list(s["position"]), "rotation": _yaw_quaternion(s["rotation"]),
                     "scale": [1, 1, 1]},
            "components": [{
                "key": f"sign-text-{number}",
                "type": "FrooxEngine.TextRenderer",
                "fields": {
                    "Text": s["text"],
                    "Size": s["size"],
                    "Color": list(s["color"]),
                    "HorizontalAlign": "Center",
                    "VerticalAlign": "Middle",
                },
            }],
        })
    if spray_method == "text-renderer":
        # The font could not be meshed in Task 7: the ring glyph is geometry but
        # the lettering needs an engine-side fallback. Black outline behind, red
        # fill 0.01 m in front, both facing -X toward the plaza (yaw 270).
        text = "トーキョー\nN◎VA"
        for layer, size, color, x in (
            ("black", 3.0, list(MATERIALS["spray_black"].base_color) + [1.0], 9.19),
            ("red", 2.9, list(MATERIALS["spray_red"].base_color) + [1.0], 9.18),
        ):
            slots.append({
                "slot": {"key": f"spray-text-{layer}", "name": f"Spray Text {layer.capitalize()}",
                         "position": [x, 5.3, 0.0], "rotation": _yaw_quaternion(270.0),
                         "scale": [1, 1, 1]},
                "components": [{
                    "key": f"spray-text-{layer}-renderer",
                    "type": "FrooxEngine.TextRenderer",
                    "fields": {
                        "Text": text,
                        "Size": size,
                        "Color": color,
                        "HorizontalAlign": "Center",
                        "VerticalAlign": "Middle",
                    },
                }],
            })
    return slots


def _walk(node: dict[str, Any]):
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def _find_node(manifest: dict[str, Any], slot_key: str) -> dict[str, Any] | None:
    for node in _walk(manifest):
        if node.get("slot", {}).get("key") == slot_key:
            return node
    return None


def _ensure_group(manifest: dict[str, Any], key: str, name: str) -> dict[str, Any]:
    """Return the root-level group Slot ``key``, creating it once."""
    for child in manifest.get("children", []):
        if child.get("slot", {}).get("key") == key:
            return child
    node = {"slot": {"key": key, "name": name,
                     "position": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]},
            "children": []}
    manifest.setdefault("children", []).append(node)
    return node


def _ensure_child(group: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    key = node["slot"]["key"]
    for child in group.setdefault("children", []):
        if child.get("slot", {}).get("key") == key:
            return child
    group["children"].append(node)
    return node


def _ensure_component(node: dict[str, Any], component: dict[str, Any]) -> None:
    components = node.setdefault("components", [])
    if not any(c.get("key") == component["key"] for c in components):
        components.append(component)


def _convert_materials(manifest: dict[str, Any]) -> None:
    for node in _walk(manifest):
        components = node.get("components")
        if not components:
            continue
        for i, component in enumerate(components):
            if component.get("type") != PBS_METALLIC:
                continue
            name = material_name(str(component.get("key", "")))
            if name is None:
                continue
            components[i] = convert_material(component, name)


def drive_components(manifest: dict[str, Any], layout: dict[str, Any]) -> None:
    """Add Panner2D drivers for scroll holo materials and Spinners on ad panels.

    Mutates ``manifest`` in place. Panners live on the ``textures`` Slot (two
    per scroll material: ``NearTextureOffset`` at [0, 0.35] and
    ``FarTextureOffset`` at [0, 0.2]); spinners are added to each exporter
    child Slot named ``ad-NN-panel`` driving ``Rotation`` at [0, 30, 0].
    """
    scroll_keys: list[str] = []
    panel_slots: list[dict[str, Any]] = []
    for node in _walk(manifest):
        if _AD_PANEL_NAME.fullmatch(str(node.get("slot", {}).get("name", ""))):
            panel_slots.append(node)
        for component in node.get("components", []):
            name = material_name(str(component.get("key", "")))
            if name and name.endswith("_scroll") and name in MATERIALS:
                key = component["key"]
                if key not in scroll_keys:
                    scroll_keys.append(key)
    textures = _find_node(manifest, "textures")
    if textures is None:
        textures = texture_slot()
        manifest.setdefault("children", []).append(textures)
    for key in scroll_keys:
        for suffix, member, speed in (("near", "NearTextureOffset", [0.0, 0.35]),
                                       ("far", "FarTextureOffset", [0.0, 0.2])):
            _ensure_component(textures, {
                "key": f"panner-{key}-{suffix}",
                "type": "FrooxEngine.Panner2D",
                # Same-type drivers share the textures Slot; the driven member is
                # the immutable distinction the validator asks for.
                "identityFields": ["_target"],
                "fields": {"_target": f"$member:{key}.{member}", "_speed": speed, "_repeat": [1.0, 1.0]},
            })
    for node in panel_slots:
        slot_key = node["slot"]["key"]
        _ensure_component(node, {
            "key": f"spinner-{slot_key}",
            "type": "FrooxEngine.Spinner",
            "fields": {"_target": f"$slot-member:{slot_key}.Rotation", "_speed": [0.0, 30.0, 0.0]},
        })


def postprocess(manifest: dict[str, Any], layout: dict[str, Any],
                reports: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convert materials and add textures, drives, lights, colliders and signs."""
    _convert_materials(manifest)
    textures = _ensure_group(manifest, "textures", "Slum02_Textures")
    for name in NOISES:
        _ensure_component(textures, _noise_component(name))
    drive_components(manifest, layout)
    lights = _ensure_group(manifest, "lights", "Slum02_Lights")
    for node in light_slots(layout):
        _ensure_child(lights, node)
    colliders = _ensure_group(manifest, "colliders", "Slum02_Colliders")
    for node in collider_slots(layout):
        _ensure_child(colliders, node)
    spray_method = ((reports or {}).get("plaza") or {}).get("spray_art", {}).get("method")
    signs = _ensure_group(manifest, "signs", "Slum02_Signs")
    for node in sign_slots(layout, spray_method):
        _ensure_child(signs, node)
    return manifest
