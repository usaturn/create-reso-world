# slum03 apply log — pre-live handoff (UTC 2026-09-28)

**No apply, test, capture, walk, audit, or save/reload performed by Task12 implementer.** This is a handoff, not an apply record. `content/slum03/slum03.json` is a portable *offline* candidate; `artifacts/slum03/delivery-report.json` is pending. Never paste a previously observed session URL/ID from local discovery into version control.

## Evidence and prerequisite

- The controller's earlier read-only observation is local `.resoloop/slum03/discovery/task12-20260928T040849-361157-{doctor,status,hierarchy}.json`: one separate slum03 session; default/avatar only, no slum02 or slum03; default floor top Y=0, lowest visible river Y=-4; requested owned root Y=4.5. These are time-specific observations; confirm again before applying. Later implementer read-only query of Fresnel offset members via discovery returned `RESONITE_DISCOVERY_NOT_FOUND` (2026-09-28 ~04:16 UTC). Reconnect and check `NearTextureOffset` and `FarTextureOffset` on `FrooxEngine.FresnelMaterial` **before strict validate/diff/apply**. The previous Reflection result `.resoloop/slum03/discovery/task12-reflection-current.json` verified 10 actual types / 56 queried members but did not request these two *drive targets*. Do not infer them from source templates.
- Candidate comes **only** from `task11-fix2-20260928T0356` portable bundles, with 15 real build reports under matching artifacts. Never apply C/D/fix1 or substitute an unrelated candidate. Slot owner `slum03`, key `root`, name `Slum03_Slum`; no Root settings, adopt, prune or delete. Four Panner2D instances each now live on a dedicated owned child Slot with a stable key and a reference to a cloned Fresnel provider; runtime-driven spin Rotation stays unmanaged. Static labels remain on undriven parents. Installed ResoLoop source `ComponentIdentityDiagnostics.cs` ignores `$member:` reference selectors for `identityFields`, even when strings differ; separate Slots remove the same-Slot ambiguity without changing targets. No prior apply/checkpoint exists to migrate.
- `resoloop validate content/slum03/slum03.json --json`: offline `valid:true`, `strict:false`, `issues:[]` (326 Slots, 379 Components, 878 refs). **Not current strict runtime validation.** Candidate's six Root-space camera bookmarks and owned structural tests are declarations, not executed checks.

## Controller-only live sequence (do not skip gates)

First recover the target session and URL by `resoloop discover --json`; set `URL` to the unique **current** slum03 endpoint, or stop/ask if ambiguous. Use `resoloop doctor --url "$URL" --json`, `resoloop status --url "$URL" --json`, `resoloop hierarchy --under Root --depth 2 --include-components --url "$URL" --json` to confirm the intended separate world, no foreign owned root, default floor top and lowest visible surface before using Y=4.5. If session restarted, reobserve session-scoped IDs; do not mutate Root. Query actual Fresnel drive-target members through Reflection on the current endpoint and resolve unsupported targets before proceeding. All live output/state paths go under `.resoloop/slum03/` and report names must not exist already.

```bash
STATE=.resoloop/slum03/state/slum03.json
MANIFEST=content/slum03/slum03.json
RUN=$(date -u +%Y%m%dT%H%M%S)-$$
resoloop validate "$MANIFEST" --strict --url "$URL" --json
resoloop diff "$MANIFEST" --state "$STATE" --brief --report ".resoloop/slum03/diff-$RUN.json" --url "$URL" --json
# Inspect FULL diff report: only slum03 owned new root/children/components/assets; no Root changes or foreign targets.
resoloop apply "$MANIFEST" --state "$STATE" --report ".resoloop/slum03/apply-$RUN.json" --url "$URL" --json
```

If apply fails, retain the checkpoint, observe and re-diff; **stop before retries**. Inspect generated root, component targets and AR copy. Spin-driven key in manifest: `object_market-product-holo-driven_99eaadfa` (confirm against same manifest); inspect twice with a time gap to confirm rotation changes while fixed product text does not move:

```bash
resoloop inspect '$slot:root' --state "$STATE" --url "$URL" --json
resoloop inspect '$slot:object_market-product-holo-driven_99eaadfa' --state "$STATE" --url "$URL" --json
# wait briefly; repeat inspect and compare rotation, plus inspect fixed label under its parent
resoloop inspect '$slot:object_market-product-holo-driven_99eaadfa' --state "$STATE" --url "$URL" --json
resoloop apply "$MANIFEST" --state "$STATE" --report ".resoloop/slum03/reapply-$RUN.json" --url "$URL" --json
# Full reapply report MUST show zero writes and zero reimports, without changing manifest/state between applies.
resoloop test "$MANIFEST" --state "$STATE" --url "$URL" --json
resoloop item audit '$slot:root' --state "$STATE" --strict --url "$URL" --json
```

Inspect external reference candidates; add only exact necessary type/member exemptions after verifying them, never blanket `_shader`, unrelated external permissions, adopt, prune or deletion. Capture six declared cameras (e.g. `resoloop capture "$MANIFEST" --camera plaza-north --output "artifacts/slum03/live-plaza-north-$RUN.jpg" --width 768 --height 512 --url "$URL"`; repeat for `east-forest`, `bridge-checkpoint`, `west-city`, `south-market`, `ar-hero`). If host capture path inaccessible, retain error and request user's own real-device visual/walking confirmation. Inspect central plaza → market → east sidewalk → Yarol entrance → checkpoint → bridge and material/text visibility including rotating AR vs fixed copy. Only with user permission verify saved/reloaded asset retention; otherwise `portability` stays pending. No performance claim from session FPS: record only measured runtime facts and structural costs. Add CLI full-report/screenshot/user-confirmation evidence to `delivery-report.json` check entries; never turn pending into pass from import or Blender preview alone.
