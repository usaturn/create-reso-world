"""Build the unified ResoLoop manifest for the akichi cyberpunk slum (Task 9).

Merges the seven validated sector bundles
(``content/akichi/<sector>-v1/model.apply.json``) into one owned root
(``Akichi_Slum``, ownership key ``akichi``) with one child Slot per sector
(``sector-<name>``). On top of the bundle contents the manifest adds:

* Sign TextRenderers from ``layout.build_layout()["signs"]`` at absolute world
  coordinates. The exporter bakes world transforms into mesh vertices and the
  bundle hierarchy is flat, so the texts are placed directly under the sector
  Slot that owns their ``attach_to`` target (nightlife clubs -> sector-nightlife,
  stalls -> sector-market, holo ads -> sector-ads). The position is the
  attachment assembly origin plus its offset rotated by the assembly's Y yaw
  (the same ``_rotate`` the geometry build uses), and the rotation is the Y-axis
  quaternion for that yaw.
* Collision boxes: one ground box (100 x 0.2 x 100, centred [0, -0.1, 0]) under
  ``sector-ground`` and one per tower (footprint x height, centred on the tower
  centre) under ``sector-towers``. Field names follow the tokyo_nova manifests
  verbatim; Resonite reflection is unavailable offline and stays a Task 10 check.
* The four brief camera bookmarks and the existence test list.

Stable keys (slot keys and component keys) share one uniqueness namespace in an
apply document (the validator rejects duplicates with
``APPLY_EXPANDED_KEY_CONFLICT``). The seven bundles repeat keys such as
``blender_providers`` and the junk-pile mesh keys, so any incoming slot or
component key that is already taken is renamed to ``<sector>-<key>`` and the
``$component:``/``$asset:`` references inside that sector's subtree are
rewritten to follow. An incoming component whose key is already taken is reused
as-is when its type and (asset-rewritten) fields are identical, which keeps one
material provider per distinct material in the merged world; provider slots
that become empty through reuse are pruned.

Determinism: sector iteration follows the fixed ``SECTORS`` tuple, and children,
components and assets keep the bundle file order plus the deterministic layout
order. No hash-, set- or dict-iteration ordering is used anywhere.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from modeling.akichi.buildings import _rotate
from modeling.akichi.layout import build_layout

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = PROJECT_ROOT / "content" / "akichi"

# Keep in sync with modeling.akichi.build.SECTORS.
SECTORS: tuple[str, ...] = ("ground", "vacant", "towers", "market", "shacks", "nightlife", "ads")
BUNDLE_SUBDIR_SUFFIX = "-v1"
BUNDLE_APPLY_NAME = "model.apply.json"
UNIFIED_NAME = "akichi-slum.json"
OWNERSHIP_KEY = "akichi"
ROOT_SLOT_KEY = "root"

SIGN_SECTOR_BY_PREFIX = ("club-", "nightlife"), ("stall-", "market"), ("ad-", "ads")

# Brief camera bookmarks, verbatim.
CAMERAS: dict[str, dict[str, Any]] = {
    "overview-north": {"position": [0, 45, -75], "target": [0, 5, 10], "fieldOfView": 60, "width": 1280, "height": 720, "representative": True},
    "vacant-street": {"position": [0, 1.7, -30], "target": [0, 3, 15], "fieldOfView": 70, "width": 1280, "height": 720},
    "market-close": {"position": [26, 1.7, -4], "target": [22, 1.5, 4], "fieldOfView": 70, "width": 1280, "height": 720},
    "nightlife-alley": {"position": [-4, 1.7, 32], "target": [6, 3, 28], "fieldOfView": 70, "width": 1280, "height": 720},
}

GROUND_COLLIDER_POSITION: list[float] = [0.0, -0.1, 0.0]
GROUND_COLLIDER_SIZE: list[float] = [100.0, 0.2, 100.0]

_POSITION_DECIMALS = 3
_QUATERNION_DECIMALS = 8


def _yaw_quaternion(radians: float) -> list[float]:
    """Y-axis quaternion for an assembly yaw, the tokyo_nova convention."""
    half = radians / 2.0
    return [
        0.0,
        round(math.sin(half), _QUATERNION_DECIMALS),
        0.0,
        round(math.cos(half), _QUATERNION_DECIMALS),
    ]


def _claim_key(key: str, sector: str, used: set[str]) -> str:
    """Return a globally unique stable key for ``key``, prefixing on conflict."""
    candidate = key
    while candidate in used:
        candidate = f"{sector}-{candidate}"
    used.add(candidate)
    return candidate


def _rewrite_references(value: Any, asset_renames: dict[str, str], component_renames: dict[str, str]) -> Any:
    """Rewrite ``$asset:``/``$component:`` strings within a plain JSON value."""
    if isinstance(value, str):
        if value.startswith("$asset:"):
            key = value[len("$asset:"):]
            renamed = asset_renames.get(key)
            return f"$asset:{renamed}" if renamed else value
        if value.startswith("$component:"):
            key = value[len("$component:"):]
            renamed = component_renames.get(key)
            return f"$component:{renamed}" if renamed else value
        return value
    if isinstance(value, list):
        return [_rewrite_references(item, asset_renames, component_renames) for item in value]
    if isinstance(value, dict):
        return {k: _rewrite_references(v, asset_renames, component_renames) for k, v in value.items()}
    return value


def _merge_bundle_slots(
    bundle_children: list[dict[str, Any]],
    sector: str,
    used: set[str],
    components_by_key: dict[str, tuple[str, dict[str, Any]]],
    asset_renames: dict[str, str],
) -> list[dict[str, Any]]:
    """Merge one bundle's child slots into uniquely keyed slots of the sector.

    Pass 1 walks the subtree in source order and fixes every key: slot keys are
    renamed on any conflict; component keys are reused when the existing
    component is identical (type + asset-rewritten fields) and renamed
    otherwise. Slot keys and component keys share one stable-key namespace,
    which the validator enforces, so every claim goes through ``used``. Pass 2
    emits the subtree with the final keys, mutes reused component declarations
    and prunes providers that became empty.
    """
    slot_renames: dict[str, str] = {}
    component_renames: dict[str, str] = {}

    def decide(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for node in slots:
            slot = node.get("slot", {})
            orig = str(slot.get("key", ""))
            if not orig:
                raise ValueError(f"{sector} bundle contains a slot without a key")
            slot_renames[orig] = _claim_key(orig, sector, used)
            for component in node.get("components", []):
                orig_component = str(component.get("key", ""))
                if not orig_component:
                    raise ValueError(f"{sector} slot {orig!r} contains a component without a key")
                resolved = dict(component)
                # Identity is compared after rewriting the references whose
                # renames are already decided: a renderer whose Mesh points at a
                # renamed key must never look identical to an earlier sector's
                # renderer, or its declaration would be muted and the mesh stay
                # invisible.
                resolved["fields"] = _rewrite_references(resolved.get("fields", {}), asset_renames, component_renames)
                identity = (resolved.get("type"), resolved.get("fields"))
                if components_by_key.get(orig_component) == identity:
                    component_renames[orig_component] = ""  # reuse: declaration is muted
                elif orig_component in components_by_key or orig_component in used:
                    renamed = _claim_key(orig_component, sector, used)
                    component_renames[orig_component] = renamed
                    components_by_key[renamed] = identity
                else:
                    components_by_key[orig_component] = identity
                    used.add(orig_component)
            for child in node.get("children", []):
                decide([child])
        return slots

    decide(bundle_children)

    def emit(nodes: list[dict[str, Any]], is_root: bool = True) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for node in nodes:
            orig = str(node.get("slot", {}).get("key", ""))
            slot = dict(node.get("slot", {}))
            slot["key"] = slot_renames[orig]
            entry: dict[str, Any] = {"slot": slot}
            components = []
            for component in node.get("components", []):
                key = str(component.get("key", ""))
                if component_renames.get(key) == "":
                    continue  # reused elsewhere: no duplicate declaration
                copy = dict(component)
                final = component_renames.get(key)
                if final:
                    copy["key"] = final
                copy["fields"] = _rewrite_references(copy.get("fields", {}), asset_renames, component_renames)
                components.append(copy)
            if components or not node.get("components"):
                entry["components"] = components
            children = emit(node.get("children", []))
            if children:
                entry["children"] = children
            # A provider slot whose contents were all reused has no components
            # left and no children: it contributes nothing to the world.
            if node.get("components") and not components and not children:
                continue
            result.append(entry)
        return result

    return emit(bundle_children)


def _sign_slots_by_sector(layout: dict[str, Any], used: set[str]) -> dict[str, list[dict[str, Any]]]:
    """Absolute-coordinate TextRenderer slots per sector for the layout signs."""
    by_id: dict[str, dict[str, Any]] = {}
    for group in (layout["nightlife"], layout["stalls"], layout["ads"]):
        for item in group:
            by_id[item["id"]] = item
    slots: dict[str, list[dict[str, Any]]] = {sector: [] for sector in SECTORS}
    for sign in layout["signs"]:
        attach = by_id.get(sign["attach_to"])
        if attach is None:
            raise ValueError(f"sign {sign['id']!r} attaches to unknown {sign['attach_to']!r}")
        sector = next((name for prefix, name in SIGN_SECTOR_BY_PREFIX if sign["attach_to"].startswith(prefix)), None)
        if sector is None:
            raise ValueError(f"sign {sign['id']!r} attaches outside the sign sectors: {sign['attach_to']!r}")
        if "position" in attach:  # holo ads carry their world position (including y)
            origin = [float(value) for value in attach["position"]]
        else:  # clubs and stalls are anchored on the ground at their centre
            origin = [float(attach["center"][0]), 0.0, float(attach["center"][1])]
        yaw = math.radians(float(attach["rotation"]))
        offset = _rotate((float(sign["offset"][0]), float(sign["offset"][1]), float(sign["offset"][2])), yaw)
        position = [round(origin[axis] + offset[axis], _POSITION_DECIMALS) for axis in range(3)]
        number = sign["id"].removeprefix("sign-")
        sign_key = _claim_key(sign["id"], sector, used)
        text_key = _claim_key(f"sign-text-{number}", sector, used)
        slots[sector].append(
            {
                "slot": {"key": sign_key, "name": f"Sign_{number}", "position": position, "rotation": _yaw_quaternion(yaw)},
                "components": [
                    {
                        "key": text_key,
                        "type": "FrooxEngine.TextRenderer",
                        "fields": {
                            "Text": sign["text"],
                            "Size": sign["size"],
                            "Color": list(sign["color"]),
                            "Alignment": "Center",
                        },
                    }
                ],
            }
        )
    return slots


def _tower_collider_slots(layout: dict[str, Any], used: set[str]) -> list[dict[str, Any]]:
    """One footprint x height BoxCollider per tower, centred on the tower centre."""
    slots: list[dict[str, Any]] = []
    for tower in layout["towers"]:
        key = _claim_key(f"{tower['id']}-collider", "towers", used)
        box_key = _claim_key(f"{key}-box", "towers", used)
        radial = math.radians(float(tower["rotation"]))
        centre = [float(tower["center"][0]), float(tower["height"]) / 2.0, float(tower["center"][1])]
        size = [float(tower["footprint"][0]), float(tower["height"]), float(tower["footprint"][1])]
        slots.append(
            {
                "slot": {"key": key, "name": f"Tower {tower['id'].removeprefix('tower-')} Collider", "position": centre, "rotation": _yaw_quaternion(radial)},
                "components": [
                    {
                        "key": box_key,
                        "type": "FrooxEngine.BoxCollider",
                        "fields": {"Enabled": True, "Type": "Static", "CharacterCollider": True, "Offset": [0.0, 0.0, 0.0], "Size": size},
                    }
                ],
            }
        )
    return slots


def _ground_collider_slot(used: set[str]) -> dict[str, Any]:
    """Single flat BoxCollider under ``sector-ground``."""
    key = _claim_key("ground-collider", "ground", used)
    box_key = _claim_key(f"{key}-box", "ground", used)
    return {
        "slot": {"key": key, "name": "Ground Collider", "position": list(GROUND_COLLIDER_POSITION), "rotation": [0.0, 0.0, 0.0, 1.0]},
        "components": [
            {
                "key": box_key,
                "type": "FrooxEngine.BoxCollider",
                "fields": {"Enabled": True, "Type": "Static", "CharacterCollider": True, "Offset": [0.0, 0.0, 0.0], "Size": list(GROUND_COLLIDER_SIZE)},
            }
        ],
    }


def _sector_manifest_tests(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Existence tests: the owned root, every sector slot, one emissive material."""
    tests: list[dict[str, Any]] = [{"name": "root-exists", "assertions": [{"target": "$slot:root", "exists": True}]}]
    for sector in SECTORS:
        tests.append(
            {"name": f"sector-{sector}-exists", "assertions": [{"target": f"$slot:sector-{sector}", "exists": True}]}
        )
    emissive_slot = _first_emissive_slot(manifest)
    if emissive_slot:
        tests.append(
            {"name": "emissive-material-exists", "assertions": [{"target": f"$slot:{emissive_slot}", "exists": True}]}
        )
    return tests


def _first_emissive_slot(manifest: dict[str, Any]) -> str | None:
    """First (deterministic traversal order) slot hosting an emissive material."""
    for node in manifest.get("children", []):
        found = _find_emissive(node)
        if found:
            return found
    return None


def _find_emissive(node: dict[str, Any]) -> str | None:
    slot_key = str(node.get("slot", {}).get("key", ""))
    for component in node.get("components", []):
        if component.get("type") != "FrooxEngine.PBS_Metallic":
            continue
        emissive = component.get("fields", {}).get("EmissiveColor")
        if isinstance(emissive, list) and any(float(value) > 0.0 for value in emissive[:3]):
            return slot_key
    for child in node.get("children", []):
        found = _find_emissive(child)
        if found:
            return found
    return None


def build_unified_manifest(bundle_dir: Path) -> dict[str, Any]:
    """Merge the seven sector bundles into the owned ``Akichi_Slum`` manifest."""
    bundle_dir = Path(bundle_dir)
    layout = build_layout()

    used: set[str] = {ROOT_SLOT_KEY}
    components_by_key: dict[str, tuple[str, dict[str, Any]]] = {}
    used_assets: set[str] = set()
    assets: dict[str, Any] = {}
    children: list[dict[str, Any]] = []
    sign_slots = _sign_slots_by_sector(layout, used)
    tower_colliders = _tower_collider_slots(layout, used)

    for sector in SECTORS:
        bundle_path = bundle_dir / f"{sector}{BUNDLE_SUBDIR_SUFFIX}" / BUNDLE_APPLY_NAME
        if not bundle_path.is_file():
            raise ValueError(f"missing sector bundle {bundle_path}")
        bundle: dict[str, Any] = json.loads(bundle_path.read_text(encoding="utf-8"))
        if bundle.get("schemaVersion") != "1" or bundle.get("slot", {}).get("key") != "root":
            raise ValueError(f"unexpected bundle structure in {bundle_path}")

        asset_renames: dict[str, str] = {}
        for key, asset in bundle.get("assets", {}).items():
            entry = dict(asset)
            source = str(entry.get("source", ""))
            if source and "://" not in source:
                entry["source"] = f"{sector}{BUNDLE_SUBDIR_SUFFIX}/{source}"
            final_key = _claim_key(key, sector, used_assets)
            if final_key != key:
                asset_renames[key] = final_key
            assets[final_key] = entry

        sector_slot_key = _claim_key(f"sector-{sector}", sector, used)
        children.append(
            {
                "slot": {"key": sector_slot_key, "name": f"Akichi_{sector.capitalize()}"},
                "children": _merge_bundle_slots(
                    list(bundle.get("children", [])), sector, used, components_by_key, asset_renames
                )
                + ([_ground_collider_slot(used)] if sector == "ground" else [])
                + (tower_colliders if sector == "towers" else [])
                + sign_slots[sector],
            }
        )

    manifest: dict[str, Any] = {
        "schemaVersion": "1",
        "ownership": {"key": OWNERSHIP_KEY},
        # The validator expands the whole document into JSON nodes and enforces
        # a default budget of 10000; the merged manifest measures 10034 nodes,
        # so declare ~20% headroom (following the tokyo_nova recipe of sizing
        # the limit from the measured value). Stay far below the 250000 cap.
        "limits": {"expandedNodes": 12000},
        "slot": {
            "key": ROOT_SLOT_KEY,
            "name": "Akichi_Slum",
            "parent": "Root",
            "position": [0, 0, 0],
            "rotation": [0, 0, 0, 1],
            "scale": [1, 1, 1],
        },
        "assets": assets,
        "components": [],
        "children": children,
        "cameras": {name: dict(camera) for name, camera in CAMERAS.items()},
    }
    manifest["tests"] = _sector_manifest_tests(manifest)
    return manifest


def write_unified_manifest(bundle_dir: Path, output_path: Path) -> dict[str, Any]:
    """Build the unified manifest and write it byte-stably to ``output_path``."""
    manifest = build_unified_manifest(bundle_dir)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    """Write ``content/akichi/akichi-slum.json`` from the sector bundles."""
    write_unified_manifest(CONTENT_DIR, CONTENT_DIR / UNIFIED_NAME)


if __name__ == "__main__":
    main()