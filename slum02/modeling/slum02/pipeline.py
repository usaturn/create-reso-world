"""Build the unified ResoLoop manifest for the slum02 cyberpunk slum (Task 14).

Merges the eleven sector bundles (``content/slum02/<sector>-v1/model.apply.json``)
into one owned root (``Slum02_Slum``, ownership key ``slum02``) with one child
Slot per sector (``sector-<name>``, display name ``Slum02_<Title>``), then runs
``postprocess`` which converts the exported PBS_Metallic materials into
vertex-colour / Fresnel materials and adds the NoiseTexture slot, holo
Panner2D drivers, ad-panel Spinners, lights, colliders and sign TextRenderers.

Stable keys (slot keys and component keys) share one uniqueness namespace in an
apply document. The bundles repeat keys such as ``providers`` and shared
material keys, so any incoming slot or component key that is already taken is
renamed to ``<sector>-<key>`` and the ``$component:``/``$asset:`` references
inside that sector's subtree are rewritten to follow. An incoming component
whose key is already taken is reused as-is when its type and (asset-rewritten)
fields are identical, which keeps one material provider per distinct material;
provider slots that become empty through reuse are pruned.

``limits.expandedNodes`` is set to ``ceil(measured * 1.2)`` where ``measured``
is the JSON-node count the validator reports (every object/array/primitive
value, root included, ``limits`` itself excluded).

Determinism: sector iteration follows the fixed ``SECTORS`` tuple, and children,
components and assets keep the bundle file order plus the deterministic layout
order. No hash-, set- or dict-iteration ordering is used anywhere.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from modeling.slum02 import PROJECT_ROOT
from modeling.slum02.layout import build_layout
from modeling.slum02.postprocess import postprocess
from modeling.slum02.sectors import SECTORS  # re-exported for tests/monkeypatch

CONTENT_DIR = PROJECT_ROOT / "content" / "slum02"

BUNDLE_SUBDIR_SUFFIX = "-v1"
BUNDLE_APPLY_NAME = "model.apply.json"
UNIFIED_NAME = "slum02.json"
OWNERSHIP_KEY = "slum02"
ROOT_SLOT_KEY = "root"

# Brief camera bookmarks.
CAMERAS: dict[str, dict[str, Any]] = {
    "overview": {"position": [0, 55, -80], "target": [0, 8, 0], "fieldOfView": 60,
                 "width": 1280, "height": 720, "representative": True},
    "plaza-east-wall": {"position": [-2.0, 2.5, 0.0], "target": [9.2, 5.0, 0.0],
                        "fieldOfView": 65, "width": 1280, "height": 720},
    "market": {"position": [-24.0, 2.0, -18.0], "target": [10.0, 1.5, -18.0],
               "fieldOfView": 70, "width": 1280, "height": 720},
    "nightlife": {"position": [12.0, 2.2, -1.0], "target": [20.0, 3.5, 0.0],
                  "fieldOfView": 70, "width": 1280, "height": 720},
}


def _sector_title(sector: str) -> str:
    return "".join(part.capitalize() for part in sector.split("-"))


def _claim_key(key: str, sector: str, used: set[str]) -> str:
    """Return a globally unique stable key for ``key``, prefixing on conflict."""
    candidate = key
    while candidate in used:
        candidate = f"{sector}-{candidate}"
    used.add(candidate)
    return candidate


def _rewrite_references(value: Any, asset_renames: dict[str, str], component_renames: dict[str, str]) -> Any:
    """Rewrite ``$asset:``/``$component:``/``$member:`` strings in a JSON value."""
    if isinstance(value, str):
        if value.startswith("$asset:"):
            key = value[len("$asset:"):]
            renamed = asset_renames.get(key)
            return f"$asset:{renamed}" if renamed else value
        for prefix in ("$component:", "$member:"):
            if value.startswith(prefix):
                key = value[len(prefix):].split(".", 1)[0]
                renamed = component_renames.get(key)
                return value.replace(key, renamed, 1) if renamed else value
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

    def decide(slots: list[dict[str, Any]]) -> None:
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

    decide(bundle_children)

    def emit(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def merge_bundles(bundle_dir: Path) -> dict[str, Any]:
    """Merge the sector bundles into the owned ``Slum02_Slum`` manifest.

    Merging only: key uniquification, reference rewrites, asset source repaths
    and the ``sector-<name>`` / ``Slum02_<Title>`` sector slots. Postprocessing,
    cameras, tests and ``limits`` are added by ``build_unified_manifest``.
    """
    bundle_dir = Path(bundle_dir)
    used: set[str] = {ROOT_SLOT_KEY}
    components_by_key: dict[str, tuple[str, dict[str, Any]]] = {}
    used_assets: set[str] = set()
    assets: dict[str, Any] = {}
    children: list[dict[str, Any]] = []

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
                "slot": {"key": sector_slot_key, "name": f"Slum02_{_sector_title(sector)}",
                         "position": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]},
                "children": _merge_bundle_slots(
                    list(bundle.get("children", [])), sector, used, components_by_key, asset_renames
                ),
            }
        )

    return {
        "schemaVersion": "1",
        "ownership": {"key": OWNERSHIP_KEY},
        "slot": {
            "key": ROOT_SLOT_KEY,
            "name": "Slum02_Slum",
            "parent": "Root",
            "position": [0, 0, 0],
            "rotation": [0, 0, 0, 1],
            "scale": [1, 1, 1],
        },
        "assets": assets,
        "components": [],
        "children": children,
    }


def _count_json_nodes(value: Any) -> int:
    """JSON nodes as the validator counts them: every value, root included."""
    n = 1
    if isinstance(value, dict):
        n += sum(_count_json_nodes(v) for v in value.values())
    elif isinstance(value, list):
        n += sum(_count_json_nodes(v) for v in value)
    return n


def _load_reports(bundle_dir: Path) -> dict[str, Any]:
    """Sector build reports (``<bundle_dir>/../artifacts/slum02/<s>-report.json``)."""
    reports_dir = Path(bundle_dir).resolve().parents[1] / "artifacts" / "slum02"
    reports: dict[str, Any] = {}
    for sector in SECTORS:
        path = reports_dir / f"{sector}-report.json"
        if path.is_file():
            reports[sector] = json.loads(path.read_text(encoding="utf-8"))
    return reports


def _manifest_tests() -> list[dict[str, Any]]:
    """Existence tests: the owned root, every sector slot, the textures slot."""
    tests: list[dict[str, Any]] = [{"name": "root-exists", "assertions": [{"target": "$slot:root", "exists": True}]}]
    for sector in SECTORS:
        tests.append(
            {"name": f"sector-{sector}-exists", "assertions": [{"target": f"$slot:sector-{sector}", "exists": True}]}
        )
    tests.append({"name": "textures-exists", "assertions": [{"target": "$slot:textures", "exists": True}]})
    return tests


def build_unified_manifest(bundle_dir: Path) -> dict[str, Any]:
    """Merge the sector bundles and postprocess into the final manifest."""
    bundle_dir = Path(bundle_dir)
    manifest = merge_bundles(bundle_dir)
    postprocess(manifest, build_layout(), _load_reports(bundle_dir))
    manifest["cameras"] = {name: dict(camera) for name, camera in CAMERAS.items()}
    manifest["tests"] = _manifest_tests()
    # The validator expands the whole document into JSON nodes and enforces a
    # default budget of 10000; declare ~20% headroom over the measured count.
    measured = _count_json_nodes(manifest)
    manifest["limits"] = {"expandedNodes": math.ceil(measured * 1.2)}
    return manifest


def write_unified_manifest(bundle_dir: Path, output_path: Path) -> dict[str, Any]:
    """Build the unified manifest and write it byte-stably to ``output_path``."""
    manifest = build_unified_manifest(bundle_dir)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    """Write ``content/slum02/slum02.json`` from the sector bundles."""
    write_unified_manifest(CONTENT_DIR, CONTENT_DIR / UNIFIED_NAME)


if __name__ == "__main__":
    main()
