"""Safe composition for reviewed Blender sectors under the existing owned root."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from modeling.tokyo_nova.north import (
    asset_catalog,
    collision_manifest_entries,
    sign_manifest_entries,
)


def enrich_layout(layout: dict[str, Any]) -> dict[str, Any]:
    """Return the layout source with its detailed north assets and recognized catalog kinds."""
    result = copy.deepcopy(layout)
    assets = asset_catalog()
    result["north_assets"] = assets
    known = {entry.get("kind") for entry in result.get("prop_catalog", [])}
    for asset in assets:
        kind = asset["kind"]
        if kind not in known:
            result.setdefault("prop_catalog", []).append({"key": kind, "kind": kind})
            known.add(kind)
    return result


def _walk_component_lists(slot: dict[str, Any]):
    yield from slot.get("components", [])
    for child in slot.get("children", []):
        yield from _walk_component_lists(child)


def _walk_slots(slot: dict[str, Any]):
    yield slot
    for child in slot.get("children", []):
        yield from _walk_slots(child)


def _disable_reviewed_placeholder_renderers(children: list[dict[str, Any]]) -> None:
    """Hide replaced north shell pieces and explicitly restore each visible floor.

    The three legacy floor renderers and colliders are set Enabled=true so an
    earlier false field cannot survive manifest composition. Other shell
    renderers and colliders are disabled; matching detail colliders are generated
    from visible counter, wall, glazing and door parts separately.
    """
    targets = {"building_north_yatai", "building_north_terminal_repair", "building_north_machiya"}
    for child in children:
        if child.get("slot", {}).get("key") not in targets:
            continue
        for slot in _walk_slots(child):
            slot_key = slot.get("slot", {}).get("key", "")
            for component in slot.get("components", []):
                component_type = component.get("type")
                if component_type not in {"FrooxEngine.MeshRenderer", "FrooxEngine.BoxCollider"}:
                    continue
                component.setdefault("fields", {})["Enabled"] = slot_key.endswith("_floor")


def _source_for_output(asset: dict[str, Any], export_directory: Path, output_directory: Path) -> str:
    source = str(asset["source"])
    if "://" in source:
        return source
    source_path = Path(source)
    if not source_path.is_absolute():
        source_path = export_directory / source_path
    return Path(os.path.relpath(source_path.resolve(), output_directory.resolve())).as_posix()


def _is_ar_model(slot: dict[str, Any]) -> bool:
    declaration = slot.get("slot", {})
    searchable = f"{declaration.get('key', '')} {declaration.get('name', '')}".casefold()
    return "ar_menu" in searchable or "ar_repair_ad" in searchable


def integrate_north_manifest(base_path: Path, export_path: Path, output_path: Path) -> dict[str, Any]:
    """Merge exported north meshes and matched detail colliders without pruning.

    Existing root pose and state identity are inherited from the Task 1 manifest. Reviewed
    north-shell wall/roof renderers and colliders are disabled, floor fields are explicitly
    restored, and detail colliders come only from selected visible solid parts. Recomposition
    replaces only these exact owned keys.
    """
    base_path, export_path, output_path = base_path.resolve(), export_path.resolve(), output_path.resolve()
    manifest = json.loads(base_path.read_text(encoding="utf-8"))
    exported = json.loads(export_path.read_text(encoding="utf-8"))
    if manifest.get("slot", {}).get("key") != "root" or exported.get("slot", {}).get("key") != "root":
        raise ValueError("both base and Blender export manifests must declare the stable root key")
    if manifest.get("ownership", {}).get("key") != "tokyo-nova-west-slum":
        raise ValueError("base manifest is not the TokyoNova_WestSlum owned root")

    old_owned_keys = {"north_detail", "north_collision_geometry", "north_physical_japanese_signage", "north_ar_displays"}
    children = [child for child in manifest.get("children", []) if child.get("slot", {}).get("key") not in old_owned_keys]
    _disable_reviewed_placeholder_renderers(children)

    assets = manifest.setdefault("assets", {})
    for key, asset in exported.get("assets", {}).items():
        if key in assets and assets[key] != asset:
            raise ValueError(f"Blender export asset key collides with the base manifest: {key}")
        assets[key] = {**asset, "source": _source_for_output(asset, export_path.parent, output_path.parent)}
    components = manifest.setdefault("components", [])
    existing_component_keys = {component.get("key") for slot in [manifest, *children] for component in _walk_component_lists(slot)}
    for component in exported.get("components", []):
        if component.get("key") in existing_component_keys:
            raise ValueError(f"Blender export component key collides with the owned root: {component.get('key')}")
        components.append(component)
        existing_component_keys.add(component.get("key"))

    limits = manifest.setdefault("limits", {})
    limits["expandedNodes"] = max(int(limits.get("expandedNodes", 0)), 20000)

    exported_children = copy.deepcopy(exported.get("children", []))
    ar_models = [child for child in exported_children if _is_ar_model(child)]
    sector_models = [child for child in exported_children if not _is_ar_model(child)]
    manifest["children"] = children
    manifest["children"].append({
        "slot": {"key": "north_detail", "name": "North frontage detailed Blender assemblies"},
        "children": sector_models,
    })
    source_layout = enrich_layout_source(manifest, base_path)
    manifest["children"].append(collision_manifest_entries(source_layout))
    sign_groups = sign_manifest_entries(source_layout)
    physical = sign_groups["physical"]
    manifest["children"].append(physical)
    ar_group = sign_groups["ar"]
    ar_group.setdefault("children", []).extend(ar_models)
    manifest["children"].append(ar_group)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def enrich_layout_source(manifest: dict[str, Any], base_path: Path) -> dict[str, Any]:
    """Reconstruct the same north signage positions from the canonical source layout."""
    layout_path = base_path.parent / "layout.json"
    if layout_path.exists():
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
    else:
        from modeling.tokyo_nova.layout import build_layout

        layout = build_layout()
    return enrich_layout(layout)
