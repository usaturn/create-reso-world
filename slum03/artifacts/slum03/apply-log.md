# slum03 apply log — controller live verification (UTC 2026-09-28 / 2026-09-29)

## Current result — Gate D2, 2026-09-29 09:42 UTC (full density, manifest `4f759b666356dde9684964340e22afde03bdb4125b45c1f5749b1fd1af6166bd`)

The controller applied the revised full-density candidate `content/slum03/density-full-c-20260929T092822Z-23504-review-candidate.json` (Task 13 reviewed) to the saved world that held the previous Gate D version. Task 10 copied the same bytes to `content/slum03/slum03.json`; its base is `content/slum03/density-baseline.json` (`2a048a15…`, the superseded canonical). Redacted facts are in `live-verification.json`; the controller's redacted evidence is committed as `tests/slum03/fixtures/density-gate-d2-evidence-redacted.json`. Raw live reports stay in ignored `.resoloop/`.

- Strict runtime validation: exit 0, zero issues.
- Reviewed diff: 92 creates / 50 updates / 0 renames / 0 deletes, 3549 no-ops, nothing outside `Slum03_Slum`. Targets: `Slum03_Ground/district-foundation`, `Slum03_Plaza/factory-floor`, `Slum03_Plaza/plaza-rubble-*` (including 16 new `plaza-rubble-floor-*`), new material `concrete_patch`; four renderers recreated because their Materials list shrinks.
- Apply: exit 0 (incremental over the Gate D version). Slots created 17; Components added 37 / updated 48 / deleted 4 (recreates); 42 imports; unchanged 228 assets, 1603 Slots, 1716 Components.
- Same manifest/state reapply: exit 0; **zero writes and imports** (1620 Slots, 1801 Components, 270 assets unchanged). Diff afterwards: 0 changes, 3691 no-ops; diff did not change state.
- Structure: `resoloop test` 2/2 passed (structural only, verification partial). Motion was not re-observed at Gate D2.
- Out-of-scope preservation: compared with the saved world's post-reload hierarchy before this apply (depth 2, IDs stripped). Root components, Clipboard Importer, Controllers, Ground, Light, Roles, Skybox, SpawnArea, Undo Manager and `__TEMP` are equal; `Assets` differs only by VR-device visual assets and shader cache; the avatar was excluded.
- Strict audit: **failed** (exit 6, `ITEM_NOT_PORTABLE`). All 61 external references matched the four reviewed exact roles (PBS_VertexColorMetallic:_regular 41, TextRenderer:Font 7, TextRenderer:Materials[0] 7, FresnelMaterial:_shader 6); no unmatched roles. The remaining failure is `ITEM_GRABBABLE_MISSING`. No Grabbable was added to bypass it.
- Capture: not run (screenshot directory not mounted).
- Human checks (recorded independently):
  - Visual: **pass** — user message 2026-09-29: 「上書き保存した。ＯＫである。」
  - Walk: **pass** — the user confirmed explicitly on 2026-09-29, when asked whether the revised (Gate D2) version was walked: 「歩いて問題なかった」.
  - Save: **done** — the user overwrote the saved world. Read-only diff after save (09:54 UTC): 0 changes, 3691 no-ops, state unchanged.
  - Reload: **pending** — not reported after Gate D2. Save/reload retention of this version is therefore pending.

`delivery-report.json` is overall **fail** (strict audit). Density acceptance stays **pending** because resources/runtime performance are not measured; save/reload retention and the forest far-edge item (final review I1) also remain open. Do not change these to pass without new evidence.

### Regenerating the delivered density version (full stage)

`content/slum03/slum03.json` is the Gate D2 review candidate of the full density build. Reproduce it from `slum03/` (all commands synchronous; use a unique `RUN` name per attempt):

```bash
RUN=density-full-c-$(date -u +%Y%m%dT%H%M%SZ)-$$
uv run python scripts/build_density.py --stage full \
  --base-manifest content/slum03/density-baseline.json \
  --layout content/slum03/density-full-layout.json --run "$RUN" --root-y 4.5
# Build a second independent run with the same command and another unique name, then compare:
RUN_D=density-full-d-$(date -u +%Y%m%dT%H%M%SZ)-$$
uv run python scripts/build_density.py --stage full \
  --base-manifest content/slum03/density-baseline.json \
  --layout content/slum03/density-full-layout.json --run "$RUN_D" --root-y 4.5
uv run python scripts/summarize_offline.py --first "$RUN" --second "$RUN_D" \
  --layout artifacts/slum03/"$RUN"/layout.json     # expect gate_c: offline-adoptable-human-pending
uv run python -m modeling.slum03.verify_assets --reports artifacts/slum03/"$RUN" \
  --layout artifacts/slum03/"$RUN"/layout.json     # expect {"status": "pass", "issues": []}
```

`build_density.py` also writes the review candidate `content/slum03/"$RUN"-review-candidate.json` (the full candidate plus QA cameras and a structural test) and its provenance. The delivered manifest is that review candidate copied byte for byte:

```bash
cp content/slum03/"$RUN"-review-candidate.json content/slum03/slum03.json
sha256sum content/slum03/"$RUN"-review-candidate.json content/slum03/slum03.json   # must match
```

The adopted run was `density-full-c-20260929T092822Z-23504` (review candidate SHA-256 `4f759b666356dde9684964340e22afde03bdb4125b45c1f5749b1fd1af6166bd`). A regenerated run only reproduces the same geometry, not the same run-name-bearing files; live acceptance (Gate D2) must be redone for a new manifest.

## History: Gate D, 2026-09-29 06:16–06:45 UTC (rejected version, manifest `a1cb4f39b3f53afa1eeb2156b493daaa23ee254e3eedd8ea75261f8f2204afc7`)

The previous full candidate `content/slum03/density-full-c-20260929T054230Z-541218-review-candidate-fix1.json` first stopped at `APPLY_REFERENCE_NOT_RETAINED` (a shrinking Materials list); after the ResoLoop fork fix it applied and converged (zero-write reapply, 2/2 tests, strict audit left only `ITEM_GRABBABLE_MISSING`). The user **rejected** the visual (flat road and factory floor; asked for small debris like slum02). That version's save/reload retention later passed (read-only, 2026-09-29 07:37 UTC); this applies only to that version, not to the current manifest.

## History: Task 12 original result — 2026-09-28 05:42 UTC (superseded manifest `2a048a15fd41de680964590c9182868e85bfd175e5fb12044b4824236c0e2bec`)

This section describes the pre-density canonical manifest, now frozen as `content/slum03/density-baseline.json`. It is kept as history and is not the result for the current manifest.

User approved the rediscovered separate empty world. Controller reconfirmed default ground at Y=0, preserved Root settings/default floor/sky/light, and applied only the `Slum03_Slum` ownership tree at Y=4.5. See `live-verification.json` for the redacted results and exact ignored local evidence paths.

- Strict runtime validation: pass, zero issues.
- Reviewed diff: 150 new assets, 339 owned Slots, 400 owned Components; no updates/renames/deletes or warnings.
- Initial apply: exit 0; 150 imports, 339 Slots and 400 Components created.
- Same manifest/state reapply: exit 0; **zero writes, imports, deletes and renames**. Manifest SHA-256 unchanged.
- Structure: one test group / 23 assertions passed. Spinner rotation and all four Panner offsets changed between observations; fixed `AUGMENT` text/transform remained unchanged.
- Default Ground/Skybox/Light snapshots unchanged. Root transform and configuration remained unchanged except that the engine-resolved shader reference appeared on its default TextUnlitMaterial. No declarative operation targeted Root settings. Capture left no temporary Slots.
- Strict audit: **failed**. All 55 external references match four explicitly inspected shader/font/text-material roles; no unused allowances. The sole remaining warning is `ITEM_GRABBABLE_MISSING`. Installed CLI strict mode has no static-world exception. The city was not made Grabbable merely to bypass the check. This needs an explicit static-world acceptance decision, not a false strict pass.
- Capture: **CAPTURE_EXPORT_TIMEOUT**. Link triggers a Windows screenshot but this client then waits for a locally accessible export folder; no screenshot folder is mounted into the container. Supply an accessible folder using `--screenshots-dir` or perform manual visual QA. No six-view or walk success is claimed.
- Manual visual/walk/save-reload/resource-performance checks remain pending. The final review also retains the lower forest silhouette/far-edge sky openings as an unresolved appearance issue.

`delivery-report.json` therefore has overall **fail** for the failed strict audit, with separate pass/pending checks. This does not mean the live apply failed. Do not silently change it to pass.

## Historical pre-live implementer handoff

The following was recorded before controller live work. **The Task12 implementer itself performed no live mutation.** Statements about pending apply below describe that earlier stage, not the current result. Never commit a session URL/ID or raw state.

## Evidence and prerequisite

- The controller's earlier read-only observation is local `.resoloop/slum03/discovery/task12-20260928T040849-361157-{doctor,status,hierarchy}.json`: one separate slum03 session; default/avatar only, no slum02 or slum03; default floor top Y=0, lowest visible river Y=-4; requested owned root Y=4.5. These are time-specific observations; confirm again before applying. The first offset-member query timed out during discovery at ~04:16 UTC; controller subsequently recovered **read-only** connectivity and confirmed `FrooxEngine.FresnelMaterial` float2 `NearTextureOffset` / `FarTextureOffset` in `.resoloop/slum03/discovery/task12-20260928T043954-382348-offsets.json`. That observation is time/session-specific; controller must repeat strict runtime validation and target review after selecting the current session. No apply occurred.
- Canonical candidate comes **only** from `finalfix-m-20260928T0511` portable bundles and its 15 actual Blender build reports from the saved snapshot `artifacts/slum03/finalfix-m-20260928T0511/layout.json`. Independent `finalfix-n-20260928T0512` bundle comparison is exact for all 150 mesh JSON payloads. Older C/D/fix1/fix2/e/f/g/h are not delivery sources. **Pre-density procedure (superseded; see "Regenerating the delivered density version" above for the delivered manifest).** Rebuild with `uv run python scripts/build_offline.py --run UNIQUE`, then `uv run python scripts/summarize_offline.py --first UNIQUE --second SECOND_UNIQUE`, and regenerate canonical declaration with `uv run python -m modeling.slum03.pipeline --bundles content/slum03/bundles/UNIQUE --layout artifacts/slum03/UNIQUE/layout.json --reports artifacts/slum03/UNIQUE --root-y 4.5 --delivery-checks --output content/slum03/slum03.json` (only after reviewed canonical replacement; use another output for trials). Never use exporter `report.json` as evaluated bounds. Slot owner `slum03`, key `root`, name `Slum03_Slum`; no Root settings, adopt, prune or delete. Four Panner2D instances each now live on a dedicated owned child Slot with a stable key and a reference to a cloned Fresnel provider; runtime-driven spin Rotation stays unmanaged. Static labels remain on undriven parents. Installed ResoLoop source `ComponentIdentityDiagnostics.cs` ignores `$member:` reference selectors for `identityFields`, even when strings differ; separate Slots remove the same-Slot ambiguity without changing targets. No prior apply/checkpoint exists to migrate.
- `resoloop validate content/slum03/slum03.json --json`: offline `valid:true`, `strict:false`, `issues:[]` (339 Slots, 399 Components, 907 refs). **Not current strict runtime validation.** Candidate's six Root-space camera bookmarks and owned structural tests are declarations, not executed checks.

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
