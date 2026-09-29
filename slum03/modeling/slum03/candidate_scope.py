"""Protect canonical declarations while transplanting evaluated selected placements.

All manifest paths share one parent; never rebase a protected source. No live APIs.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from .types import Layout, Manifest, Issue, Report
from .pipeline import _validate_final, _refs
from .density_model import SCATTER_PREFIXES, SURFACE_PLACEMENT_SLOTS
from .density_layout import NEW_KEY_PREFIXES


def nodes(manifest: Manifest):
    def visit(node, parent):
        yield node['slot']['key'], node, parent
        for child in node.get('children', []):
            yield from visit(child, node['slot']['key'])
    return {key: (node, parent) for key, node, parent in visit(manifest, None)}


def _file(directory: Path, source: str) -> tuple[str, str]:
    if not isinstance(source, str) or '://' in source or Path(source).is_absolute():
        raise ValueError(f'nonlocal asset: {source}')
    target = (directory / source).resolve()
    if not target.is_relative_to(directory.resolve()) or not target.is_file():
        raise ValueError(f'missing or escaped asset: {source}')
    return source, hashlib.sha256(target.read_bytes()).hexdigest()


def _asset_refs(node: dict) -> set[str]:
    found = set()
    def visit(value):
        if isinstance(value, str) and value.startswith('$asset:'):
            found.add(value[7:])
        elif isinstance(value, dict):
            for item in value.values(): visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)
    visit({k: v for k, v in node.items() if k not in ('children', 'assets')})
    return found


def _full(layout: Layout) -> bool:
    return layout.density is not None and layout.density.stage == 'full'


def _scatter_prefix(name, layout: Layout) -> str | None:
    """Full stage only: '<prefix>-<i>-<j>' rubble heap of a *selected* scatter family."""
    if not _full(layout) or not isinstance(name, str):
        return None
    return next((prefix for prefix in SCATTER_PREFIXES
                 if prefix in layout.density.selected_keys and
                 re.fullmatch(re.escape(prefix) + r'-\d+-\d+', name)), None)


def expected_cluster_lights(layout: Layout) -> dict[str, dict]:
    """Full-stage shadowless cluster lights regenerated from the same saved Layout."""
    if not _full(layout):
        return {}
    from .native.lighting import light_slots
    return {n['slot']['key']: n for n in light_slots(layout)
            if n['slot']['key'].startswith('local-light-cluster-')}


def _selected(node: dict, layout: Layout) -> bool:
    name = node['slot'].get('name')
    key = node['slot']['key']
    if not key.startswith('collider-'):
        return name in layout.density.selected_keys or _scatter_prefix(name, layout) is not None
    suffix = key.removeprefix('collider-')
    owner = next((p.key for p in sorted(layout.placements, key=lambda p: len(p.key), reverse=True)
                  if suffix == p.key or suffix.startswith(p.key + '-')), None)
    if _full(layout) and SURFACE_PLACEMENT_SLOTS.get(owner) in layout.density.selected_keys:
        return True  # e.g. collider-district-ground-* belongs to the district-foundation Slot.
    return owner in layout.density.selected_keys


def _subtree(node: dict) -> set[str]:
    return set(nodes(node))


def absent_selected_baseline(baseline_nodes: dict, candidate_nodes: dict, layout: Layout) -> list[dict]:
    """Baseline heaps of a selected scatter family that the regeneration no longer emits."""
    return [{'key': key, 'name': node['slot']['name'], 'parent': parent,
             'reason': f'scatter heap not regenerated under selected prefix {prefix}'}
            for key, (node, parent) in baseline_nodes.items()
            if key not in candidate_nodes and
            (prefix := _scatter_prefix(node['slot'].get('name'), layout)) is not None]


def _selected_roots(baseline_nodes: dict, candidate_nodes: dict, layout: Layout) -> set[str]:
    """Only baseline-confirmed placement Slots may start dependency traversal.

    Full stage adds two classes (Task 8 interface): a new 'density-*' key must be
    generated exactly once below an existing sector, and a selected scatter
    family may keep, add or drop '<prefix>-<i>-<j>' heaps below its baseline parent.
    """
    roots = set()
    for name in layout.density.selected_keys:
        if _full(layout) and name in SCATTER_PREFIXES:
            family = {key: parent for key, (node, parent) in baseline_nodes.items()
                      if _scatter_prefix(node['slot'].get('name'), layout) == name}
            parents = set(family.values())
            for key, parent in family.items():
                current = candidate_nodes.get(key)
                if current is None:
                    continue  # Listed by absent_selected_baseline; never pruned here.
                if current[1] != parent or current[0]['slot'].get('name') != baseline_nodes[key][0]['slot']['name']:
                    raise ValueError(f'selected scatter heap moved or renamed in place: {key}')
                roots.add(key)
            for key, (node, parent) in candidate_nodes.items():
                if key in baseline_nodes or _scatter_prefix(node['slot'].get('name'), layout) != name:
                    continue
                if parent not in (parents or {p for p in baseline_nodes if p.startswith('sector-')}):
                    raise ValueError(f'new scatter heap outside its family parent: {key}')
                roots.update(_subtree(node))
            continue
        matches = [(key, parent) for key, (node, parent) in baseline_nodes.items()
                   if node['slot'].get('name') == name]
        if not matches and _full(layout) and name.startswith(NEW_KEY_PREFIXES):
            generated = [(key, parent) for key, (node, parent) in candidate_nodes.items()
                         if node['slot'].get('name') == name]
            if len(generated) != 1:
                raise ValueError(f'selected new placement not generated or duplicated: {name}')
            key, parent = generated[0]
            if key in baseline_nodes or parent not in baseline_nodes or not parent.startswith('sector-'):
                raise ValueError(f'selected new placement outside a baseline sector: {name}')
            roots.update(_subtree(candidate_nodes[key][0]))
            continue
        if len(matches) != 1:
            raise ValueError(f'selected baseline placement ambiguous or missing: {name}')
        key, parent = matches[0]
        candidate = candidate_nodes.get(key)
        if candidate is None or candidate[1] != parent or candidate[0]['slot'].get('name') != name:
            raise ValueError(f'selected placement identity missing or renamed: {name}')
        roots.add(key)
    return roots


def _draft_run(draft_path: Path, draft: Manifest) -> str:
    """Establish a unique run from every source AND the full draft filename."""
    runs = set()
    for entry in draft.get('assets', {}).values():
        source = entry.get('source')
        parts = source.split('/') if isinstance(source, str) else []
        if len(parts) != 4 or parts[0] != 'bundles' or not all(parts[1:]):
            raise ValueError(f'unrecognized raw draft source/run: {source}')
        runs.add(parts[1])
    if len(runs) != 1:
        raise ValueError('raw draft needs one identifiable export run')
    run = runs.pop()
    prefix = f'{run}-raw-draft'
    stem = draft_path.stem
    revision = stem[len(prefix):] if stem.startswith(prefix) else None
    if revision is None or (revision and (not revision.startswith('-') or
            not revision[1:].replace('-', '').isalnum())):
        raise ValueError(f'raw draft filename cannot identify export run: {draft_path.name}')
    return run


_MATERIAL_TYPES = frozenset({'FrooxEngine.PBS_Metallic', 'FrooxEngine.PBS_VertexColorMetallic'})


def _component_refs(value: object) -> set[str]:
    return {match[2] for match in _refs(value) if match[1] == 'component'}


def _reachable_components(items: dict, components: dict, selected_roots: set[str]) -> set[str]:
    """Follow references only from selected render/mesh components, then their providers."""
    seeds = set()
    for key in selected_roots:
        node = items[key][0]
        for c in node.get('components', []):
            if c['type'] in ('FrooxEngine.MeshRenderer', 'FrooxEngine.StaticMesh'):
                seeds.update(_component_refs(c))
    reached = set(seeds)
    pending = list(seeds)
    while pending:
        key = pending.pop()
        component = components.get(key)
        if component is None:
            continue
        for ref in _component_refs(component[0]) - reached:
            reached.add(ref)
            pending.append(ref)
    return reached


def _index(manifest: Manifest):
    items = nodes(manifest)
    comps = {}
    for key, (node, _) in items.items():
        for component in node.get('components', []):
            ck = component['key']
            if ck in comps:
                raise ValueError(f'duplicate component: {ck}')
            comps[ck] = (component, key)
    return items, comps


def check_candidate_scope(baseline: Manifest, candidate: Manifest, layout: Layout,
                          manifest_dir: Path, *, baseline_dir: Path | None = None) -> list[Issue]:
    """Report protected declaration/source/byte changes; verify complete owned references."""
    issues = []
    if layout.density is None or layout.density.stage not in ('representative', 'full'):
        return [Issue('SCOPE_STAGE', 'layout', 'density candidate needs representative/full stage')]
    manifest_dir = Path(manifest_dir)
    baseline_dir = Path(baseline_dir) if baseline_dir is not None else manifest_dir
    try:
        _validate_final(candidate)
        bnodes, bcomps = _index(baseline)
        cnodes, ccomps = _index(candidate)
    except (ValueError, KeyError, TypeError) as exc:
        return [Issue('SCOPE_INVALID', 'manifest', str(exc))]
    for field in ('schemaVersion', 'ownership', 'slot', 'components', 'cameras', 'tests'):
        if candidate.get(field) != baseline.get(field):
            issues.append(Issue('SCOPE_ROOT', field, 'root declaration changed'))
    absent = {entry['key'] for entry in absent_selected_baseline(bnodes, cnodes, layout)}
    for key, (original, parent) in bnodes.items():
        replacement = cnodes.get(key)
        if key in absent:
            continue  # Selected scatter heap no longer generated: listed, not pruned.
        if replacement is None or replacement[1] != parent:
            issues.append(Issue('SCOPE_NODE', key, 'node removed/moved'))
            continue
        current = replacement[0]
        if _selected(original, layout):
            if current['slot'].get('key') != key or current['slot'].get('name') != original['slot'].get('name'):
                issues.append(Issue('SCOPE_IDENTITY', key, 'selected identity changed'))
        else:
            # Provider containers may gain new nodes, but their existing declarations do not change.
            old = {k: v for k, v in original.items() if k not in ('children', 'assets', 'cameras', 'tests', 'limits')}
            new = {k: v for k, v in current.items() if k not in ('children', 'assets', 'cameras', 'tests', 'limits')}
            if old != new or [c['slot']['key'] for c in original.get('children', []) if c['slot']['key'] not in absent] != [c['slot']['key'] for c in current.get('children', []) if c['slot']['key'] in bnodes]:
                issues.append(Issue('SCOPE_NODE', key, 'protected node/component changed'))
    for key, (component, owner) in bcomps.items():
        if owner in absent:
            continue
        if key not in ccomps:
            issues.append(Issue('SCOPE_COMPONENT', key, 'component removed'))
        elif ccomps[key][1] != owner or (not _selected(bnodes[owner][0], layout) and ccomps[key][0] != component):
            issues.append(Issue('SCOPE_COMPONENT', key, 'protected component changed/moved'))
    selected_asset_keys = set()
    for key, (node, _) in bnodes.items():
        if _selected(node, layout):
            selected_asset_keys.update(_asset_refs(node))
    protected = set(baseline.get('assets', {})) - selected_asset_keys
    for key, (node, _) in bnodes.items():
        if key != 'root' and not _selected(node, layout):
            protected.update(_asset_refs(node))
    for key, asset in candidate.get('assets', {}).items():
        try:
            _file(manifest_dir, asset['source'])
        except (ValueError, KeyError, OSError, TypeError) as exc:
            issues.append(Issue('SCOPE_ASSET_SOURCE', key, str(exc)))
    for key in sorted(protected):
        before = baseline['assets'].get(key)
        after = candidate.get('assets', {}).get(key)
        if before != after:
            issues.append(Issue('SCOPE_ASSET', key, 'protected asset declaration/source changed'))
        try:
            if before is None or after is None or _file(baseline_dir, before['source'])[1] != _file(manifest_dir, after['source'])[1]:
                issues.append(Issue('SCOPE_ASSET_BYTES', key, 'protected asset bytes changed'))
        except (ValueError, KeyError, OSError) as exc:
            issues.append(Issue('SCOPE_ASSET_BYTES', key, str(exc)))
    try:
        roots = _selected_roots(bnodes, cnodes, layout)
    except ValueError as exc:
        issues.append(Issue('SCOPE_IDENTITY', 'layout', str(exc)))
        roots = set()
    reachable = _reachable_components(cnodes, ccomps, roots)
    selected_new = {key for key, (n, parent) in cnodes.items()
                    if key not in bnodes and key.startswith('collider-') and parent in bnodes and
                    _selected(n, layout) and any(c['type'] == 'FrooxEngine.BoxCollider'
                                                   for c in n.get('components', []))}
    lights = expected_cluster_lights(layout)
    for key, (node, parent) in cnodes.items():
        if key in bnodes or key in selected_new or key in roots:
            continue
        if key in lights:
            if parent != 'native-lights' or parent not in bnodes or node != lights[key]:
                issues.append(Issue('SCOPE_NEW_NODE', key, 'cluster light differs from the saved Layout'))
            continue
        if (not key.startswith('provider_') or parent not in bnodes or
                'blender_providers' not in parent or not any(
                    c['key'] in reachable for c in node.get('components', []))):
            issues.append(Issue('SCOPE_NEW_NODE', key, 'new unreferenced node outside selected scope'))
    return issues


def generated_asset_keys(draft: Manifest, keys: set[str]) -> set[str]:
    items = nodes(draft)
    return set().union(*(_asset_refs(items[k][0]) for k in keys if k in items)) if keys else set()


def compose_candidate(baseline_path: Path, draft_path: Path, layout: Layout, output: Path) -> Report:
    """Deep-copy baseline, transfer only named selected nodes and newly required resources."""
    baseline_path, draft_path, output = map(Path, (baseline_path, draft_path, output))
    if len({p.parent.resolve() for p in (baseline_path, draft_path, output)}) != 1:
        raise ValueError('baseline, raw draft and candidate require same parent')
    if output.exists():
        raise FileExistsError(output)
    if layout.density is None or layout.density.stage not in ('representative', 'full'):
        raise ValueError('density stage must be representative or full')
    baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
    draft = json.loads(draft_path.read_text(encoding='utf-8'))
    _validate_final(baseline); _validate_final(draft)
    bnodes, bcomps = _index(baseline)
    dnodes, dcomps = _index(draft)
    if baseline['slot'] != draft['slot'] or baseline['ownership'] != draft['ownership']:
        raise ValueError('root changed in raw regeneration')
    selected_roots = _selected_roots(bnodes, dnodes, layout)
    new_roots = selected_roots - set(bnodes)
    selected_keys = selected_roots & set(bnodes)
    selected_refs = _reachable_components(dnodes, dcomps, selected_roots)
    absent = absent_selected_baseline(bnodes, dnodes, layout)
    absent_keys = {entry['key'] for entry in absent}
    lights = expected_cluster_lights(layout)
    if set(lights) - set(dnodes):
        raise ValueError(f'cluster lights missing from raw draft: {sorted(set(lights) - set(dnodes))}')
    baseline_slot_refs = {m[2] for m in _refs(baseline) if m[1] in ('slot', 'slot-member')}
    retained_stubs = {key: parent for key, (node, parent) in bnodes.items()
                      if _full(layout) and key not in dnodes and not _selected(node, layout) and parent and
                      'blender_providers' in parent and not node.get('components') and
                      not node.get('children') and key not in baseline_slot_refs and
                      key == parent.removesuffix('-blender_providers') + '-provider_' + str(node['slot'].get('name'))}
    relocated = set()
    for key, (node, parent) in bnodes.items():
        if key in dnodes and parent != dnodes[key][1] and key.startswith('provider_') and (
            parent and dnodes[key][1] and 'blender_providers' in parent and
            'blender_providers' in dnodes[key][1] and node == dnodes[key][0] and
            len(node.get('components', [])) == 1 and
            node['components'][0]['type'] in _MATERIAL_TYPES and
            node['components'][0]['key'] in selected_refs):
            relocated.add(key)
    for key, (node, parent) in bnodes.items():
        if key in absent_keys or key in retained_stubs:
            continue  # Absent heap is listed; empty baseline stub is kept verbatim.
        if _selected(node, layout):
            selected_keys.add(key)
            continue
        fresh = dnodes.get(key)
        if fresh is None or (parent != fresh[1] and key not in relocated):
            raise ValueError(f'unselected node/provider moved or missing: {key}')
        if {k: v for k, v in node.items() if k not in ('children', 'assets', 'cameras', 'tests', 'limits')} != {k: v for k, v in fresh[0].items() if k not in ('children', 'assets', 'cameras', 'tests', 'limits')}:
            raise ValueError(f'unselected node/provider changed in raw regeneration: {key}')
        old_children = [c['slot']['key'] for c in node.get('children', []) if c['slot']['key'] not in relocated
                        and c['slot']['key'] not in absent_keys and c['slot']['key'] not in retained_stubs]
        new_children = [c['slot']['key'] for c in fresh[0].get('children', [])
                        if c['slot']['key'] in bnodes and c['slot']['key'] not in relocated]
        if set(old_children) != set(new_children) or len(old_children) != len(new_children):
            raise ValueError(f'unselected children changed in raw regeneration: {key}, {old_children} -> {new_children}')
    empty_provider_stubs = []
    relocation_evidence = []
    for key in sorted(relocated):
        node, parent = bnodes[key]
        relocation_evidence.append({'provider_slot': key, 'component': node['components'][0]['key'],
                                    'type': node['components'][0]['type'],
                                    'from_parent': parent, 'raw_parent': dnodes[key][1],
                                    'reason': 'identical selected-referenced material reused earlier in raw export'})
    for key, (node, parent) in dnodes.items():
        if key in bnodes or key in new_roots or (key.startswith('collider-') and _selected(node, layout)):
            continue
        if key in lights:
            if parent != 'native-lights' or parent not in bnodes or node != lights[key]:
                raise ValueError(f'cluster light differs from the saved Layout: {key}')
            continue
        if (key.startswith('provider_') and parent in bnodes and 'blender_providers' in parent and
                node.get('components') and all(c['key'] in selected_refs for c in node['components'])):
            continue  # Fresh provider needed by a selected Renderer/Mesh dependency.
        comp_key = node['slot'].get('name')
        matched = next((entry for entry in relocation_evidence
                        if entry['component'] == comp_key and entry['from_parent'] == parent), None)
        stub_shape = (isinstance(comp_key, str) and parent and 'blender_providers' in parent and
                      key == parent.removesuffix('-blender_providers') + '-provider_' + comp_key and
                      not node.get('components') and not node.get('children') and
                      not any(match[1] in ('slot', 'slot-member') and match[2] == key
                              for match in _refs(draft)))
        if matched is not None and stub_shape:
            empty_provider_stubs.append({'slot': key, 'material_component': comp_key,
                                         'relocated_provider': matched['provider_slot'],
                                         'from_parent': matched['from_parent'],
                                         'raw_parent': matched['raw_parent'],
                                         'reason': 'unreferenced empty slot left by verified material relocation'})
            continue
        # Full stage: every other sector that reuses a material also receives an
        # empty reuse slot. Only for a material the candidate provides from one
        # verified provider: a relocated baseline provider or a new selected one.
        relocated_to = next((entry for entry in relocation_evidence if entry['component'] == comp_key), None)
        fresh_provider = (comp_key in selected_refs and comp_key in dcomps and comp_key not in bcomps and
                          dcomps[comp_key][0]['type'] in _MATERIAL_TYPES and
                          dcomps[comp_key][1] == 'provider_' + comp_key and
                          'blender_providers' in (dnodes[dcomps[comp_key][1]][1] or ''))
        if _full(layout) and stub_shape and (relocated_to is not None or fresh_provider):
            provider = relocated_to['provider_slot'] if relocated_to else dcomps[comp_key][1]
            empty_provider_stubs.append({'slot': key, 'material_component': comp_key,
                                         'relocated_provider' if relocated_to else 'new_provider': provider,
                                         'raw_parent': parent,
                                         'provider_parent': dnodes[provider][1],
                                         'reason': ('unreferenced empty reuse slot for a verified relocated material'
                                                    if relocated_to else
                                                    'unreferenced empty reuse slot for a new selected material provider')})
            continue
        raise ValueError(f'unrelated or referenced raw draft stub/node: {key}')
    for key in selected_keys:
        if key not in dnodes or bnodes[key][1] != dnodes[key][1] or dnodes[key][0]['slot'].get('name') != bnodes[key][0]['slot'].get('name'):
            raise ValueError(f'selected key removed/moved: {key}')
        old_keys = {c['key'] for c in bnodes[key][0].get('components', [])}
        new_keys = {c['key'] for c in dnodes[key][0].get('components', [])}
        if not old_keys <= new_keys:
            raise ValueError(f'selected component identity lost: {key}')
    # All raw regenerated assets used by protected nodes (and retained providers) must have
    # the same declaration except for run-relative source, and the exact same payload bytes.
    replaced = selected_keys | absent_keys
    selected_assets = set().union(*(_asset_refs(bnodes[k][0]) for k in replaced)) if replaced else set()
    protected_assets = set(baseline['assets']) - selected_assets
    protected_assets.update(*( _asset_refs(n) for k, (n, _) in bnodes.items() if k not in replaced and k != 'root'))
    run = _draft_run(draft_path, draft)
    for key in protected_assets:
        old = baseline['assets'].get(key)
        fresh = draft['assets'].get(key)
        if (old is None or fresh is None or
                {k: v for k, v in old.items() if k != 'source'} !=
                {k: v for k, v in fresh.items() if k != 'source'} or
                (old['source'].startswith('bundles/') and
                 old['source'].split('/')[2:] != fresh['source'].split('/')[2:])):
            raise ValueError(f'unselected regenerated asset source/declaration changed: {key}')
        if _file(baseline_path.parent, old['source'])[1] != _file(draft_path.parent, fresh['source'])[1]:
            raise ValueError(f'unselected regenerated asset changed: {key}')
    generated = selected_keys | new_roots
    allowed_new_assets = set().union(*(_asset_refs(dnodes[k][0]) for k in generated)) if generated else set()
    for comp_key in selected_refs:
        if comp_key in dcomps and dcomps[comp_key][1] not in bnodes:
            allowed_new_assets.update(_asset_refs(dnodes[dcomps[comp_key][1]][0]))
    if set(draft['assets']) - set(baseline['assets']) - allowed_new_assets:
        raise ValueError('unrelated raw draft asset added')
    result = copy.deepcopy(baseline)
    cnodes = nodes(result)
    for key in selected_keys:
        original = cnodes[key][0]
        fresh = dnodes[key][0]
        original['slot'] = copy.deepcopy(fresh['slot'])
        original['components'] = copy.deepcopy(fresh.get('components', []))
        if key in dnodes and [c['slot']['key'] for c in original.get('children', [])] != [c['slot']['key'] for c in fresh.get('children', [])]:
            raise ValueError(f'selected children changed unexpectedly: {key}')
    for key in sorted(new_roots):
        node, parent = dnodes[key]
        if parent in bnodes:  # Descendants travel with their new top-level Slot.
            cnodes[parent][0]['children'].append(copy.deepcopy(node))
    for entry in absent:
        siblings = cnodes[entry['parent']][0]['children']
        siblings[:] = [c for c in siblings if c['slot']['key'] != entry['key']]
    for key in sorted(lights):
        cnodes['native-lights'][0]['children'].append(copy.deepcopy(dnodes[key][0]))
    selected_draft_assets = allowed_new_assets
    for key in sorted(selected_draft_assets):  # Stable bytes across independent runs.
        if key in protected_assets and (key not in baseline['assets'] or _file(baseline_path.parent, baseline['assets'][key]['source'])[1] != _file(draft_path.parent, draft['assets'][key]['source'])[1]):
            raise ValueError(f'shared asset changed: {key}')
        if key not in protected_assets:
            result['assets'][key] = copy.deepcopy(draft['assets'][key])
    # Copy the dependency closure rooted in selected Renderer/Mesh only.
    for component_key in sorted(selected_refs):
        if component_key in bcomps:
            if (component_key in dcomps and dcomps[component_key][0] != bcomps[component_key][0]
                    and bcomps[component_key][1] not in selected_keys):
                raise ValueError(f'shared provider edited: {component_key}')
            continue
        if component_key not in dcomps:
            raise ValueError(f'missing new provider: {component_key}')
        new_node_key = dcomps[component_key][1]
        if new_node_key in new_roots:
            continue  # Declared on a newly generated selected Slot copied above.
        new_node, parent = dnodes[new_node_key]
        if new_node_key in cnodes or parent not in cnodes or 'blender_providers' not in parent:
            raise ValueError(f'new provider cannot be placed safely: {component_key}')
        if not any(child['slot']['key'] == new_node_key for child in cnodes[parent][0]['children']):
            cnodes[parent][0]['children'].append(copy.deepcopy(new_node))
    for key, (node, parent) in dnodes.items():
        if key not in cnodes and key not in new_roots and _selected(node, layout):
            if parent not in cnodes or not key.startswith('collider-'):
                raise ValueError(f'new selected node outside collider group: {key}')
            cnodes[parent][0]['children'].append(copy.deepcopy(node))
    referenced = {m[2] for m in _refs({k: v for k, v in result.items() if k != 'assets'}) if m[1] == 'asset'}
    for key in (selected_assets - referenced) if _full(layout) else ():
        if key not in generated_asset_keys(draft, generated):
            result['assets'].pop(key, None)  # Only declarations of heaps no longer emitted.
    _validate_final(result)
    issues = check_candidate_scope(baseline, result, layout, baseline_path.parent)
    if issues:
        raise ValueError(f'candidate scope: {issues[:5]}')
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'protected_changes': 0, 'selected_nodes': sorted(selected_keys),
            'new_selected_nodes': sorted(new_roots),
            'absent_baseline_slots': absent,
            'cluster_lights': sorted(lights),
            'raw_absent_baseline_empty_provider_stubs': [
                {'slot': key, 'parent': parent,
                 'reason': 'empty unreferenced baseline provider stub not re-emitted by exporter; kept verbatim'}
                for key, parent in sorted(retained_stubs.items())],
            'raw_ignored_empty_provider_nodes': empty_provider_stubs,
            'raw_material_relocations': relocation_evidence,
            'asset_sources': {key: {'source': value['source'], 'sha256': _file(output.parent, value['source'])[1],
                                     'origin': 'baseline' if key in protected_assets else 'draft'}
                              for key, value in result['assets'].items()},
            'object_sources': {key: 'draft' if key in selected_keys or key not in bnodes else 'baseline'
                               for key in nodes(result)}}
