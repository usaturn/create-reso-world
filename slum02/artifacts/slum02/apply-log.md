# Task 15 apply log — Slum02_Slum

対象: `content/slum02/slum02.json` → `Root/Slum02_Slum`（Resonite 2026.9.18.82, `ws://localhost:53724`）
state: `.resoloop/slum02/state/slum02.json`（gitignored）、root slot ID `Reso_6B34`
時刻は JST（+09:00）。

## Step 1: 接続と対象確認（~15:47）

```bash
resoloop doctor --url ws://localhost:53724 --json
resoloop find --name Slum02_Slum --exact --url ws://localhost:53724 --json
resoloop find --name ResoLoop_Test_Slum02 --url ws://localhost:53724 --json
```

- doctor: ready（ResoniteLink 0.13.1.0）。flux-sdk / managed-data / log の warning は任意項目のみ。
- `Slum02_Slum` → `[]`（未作成）、`ResoLoop_Test_Slum02*` → `[]`。create-only apply が期待どおり。

## Step 2: 駆動の実機確認（15:50–15:53）

- `content/slum02/test-drives.json` を作成（ownership `slum02-test`、`ResoLoop_Test_Slum02Drives` @ [0,1.5,-45]、probe メッシュ + Task 14 変換済み `PBS_VertexColorMetallic`、`FresnelMaterial`+`Panner2D`、子 Slot+`Spinner`）。変換フィールドは `postprocess.convert_material` / `_noise_component` をそのまま呼んで生成。
- `validate --strict` → valid（5 slots / 13 components / issues 0）
- `apply --state tmp/test-drives-state.json` → 5 slots / 13 components 作成（root `Reso_5BC2`）
- `observe '$member:test-fresnel.NearTextureOffset'` ×2 + `inspect '$slot:test-spin'` ×2 で変化を確認。判定は `live-drive-check.json` 参照。
  - Panner2D: offset が増分（wrap mod 1.0）。`_speed` 単位 = UV/s と推定（0.35/s と整合）。
  - Spinner: yaw が ~26°/s で変化（設定 30、読み取り遅延分の誤差）。`_speed` 単位 = deg/s、30 deg/s ≈ 0.08 rev/s で過速ではない → **速度修正不要**。
- `find --name ResoLoop_Test_Slum02Drives --exact` → `Reso_5BC2` を確認のうえ `slot delete Reso_5BC2 --yes`。再 find → `[]`。残骸なし。

## Step 3: strict validate と diff（15:53）

```bash
resoloop validate content/slum02/slum02.json --strict --url ws://localhost:53724 --json > tmp/strict.json
resoloop diff content/slum02/slum02.json --state .resoloop/slum02/state/slum02.json --summary --url ws://localhost:53724 --json > tmp/diff-summary.json
```

- strict: valid（332 slots / 479 components / 1372 references）。warning 1 件 `APPLY_COMPONENT_IDENTITY_RISK`（textures Slot 上の Panner2D×4。`identityFields:["_target"]` 宣言済みだが参照型のため保守的警告。設計どおり）。
- diff（`--changes-only` と `--summary` はこのバージョンで同時指定不可のため `--summary` に分割）: **creates 970 / updates 0 / deletes 0 / renames 0**。create のみ確認して apply へ。

## Step 4: apply（15:54:09 → 15:55:05、約 56 秒）

```bash
resoloop apply content/slum02/slum02.json --state .resoloop/slum02/state/slum02.json --ndjson-progress --command-timeout 1800 --url ws://localhost:53724 --json > tmp/apply.ndjson 2> tmp/apply.err
```

- exit 0。進捗は stderr（`tmp/apply.err`、1450 イベント）。結果（`tmp/apply.ndjson`）:
  - `slotId Reso_6B34`、`created:true`
  - slotsCreated **332**、componentsAdded **479**、assetsImported **159**
  - 作成後の fields 段で 117 コンポーネントにフィールド書き込み（マテリアル/レンダラ等の作成後設定。内訳は apply.err の `fields` ステージ、updated N field(s) 計 117 件、残り no field changes）
  - updated/deleted 系 0。

## Step 5: 再 apply 収束と test（15:55–15:58）

- 1 回目の再 apply（15:55:27 → 15:55:41、約 14s）: `slotsUpdated:4` — Spinner が駆動する ad-14/16/18/20-panel の Rotation が runtime で変化し、マニフェストの rotation と不一致 → 書き戻しが発生。**収束しない**ため修正:
  - `modeling/slum02/postprocess.py` の `drive_components` で、Spinner を付ける panel Slot に `managedFields: ["position","scale"]` を宣言（Rotation は runtime 所有に）。
  - `uv run python -m modeling.slum02.pipeline` で `content/slum02/slum02.json` 再生成（diff は 4 Slot に `managedFields` 追加のみ）。
- 2 回目の再 apply（15:57:58 → 15:58:08、約 10s）: **slotsUpdated 0 / componentsAdded 0 / componentsUpdated 0 / deleted 0、slotsUnchanged 332 / componentsUnchanged 479 / assetsUnchanged 159 → 書き込み 0 件で収束**。
- `resoloop test`（15:58:17、約 9s）: **13/13 pass**（root + 11 セクタ + textures の存在確認、structuralOnly）。

## まとめ

| 項目 | 結果 |
|---|---|
| 初回 apply | 332 slots / 479 components / 159 assets 作成、約 56 秒 |
| 再 apply（修正前） | 4 slot 更新（Spinner 駆動 Rotation の書き戻し）→ 修正 |
| 再 apply（`managedFields` 修正後） | **writes 0、収束確認** |
| resoloop test | 13/13 pass |
| 速度修正 | 不要（Spinner 30 deg/s ≈ 0.08 rev/s、Panner2D 0.35 UV/s） |
| 副産物の修正 | postprocess.py に `managedFields:["position","scale"]`（駆動される panel Slot のみ）+ slum02.json 再生成 |
