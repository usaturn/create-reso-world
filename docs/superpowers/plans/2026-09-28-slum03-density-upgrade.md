# slum03 Density Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 中央活動床と導線を維持し、slum02を下回らない街区密度・近景品質を持つslum03へ段階的に改善する。

**Architecture:** 既存Layout／区画Assembly／Blender評価／bundle統合を拡張する。全域ブロックアウトと代表3単位の高品質化を分離し、既存manifestを基準に対象外を保護した完全な候補を作る。代表区画の実機確認後に全域へ展開し、数量・評価後形状・実機目視の証跡を別々に保持する。

**Tech Stack:** Python >=3.12、uv、pytest、導入済みBlender、pinned ResoLoop。追加のPython依存は不要。Blender/API/CLIの新規利用部分は該当スキル・導入済みメタデータで確認する。

**Spec:** `/workspaces/create-reso-world/docs/superpowers/specs/2026-09-28-slum03-density-upgrade-design.md`（2026-09-28ユーザー承認済み）。原仕様は実装worktreeの `docs/superpowers/specs/2026-09-27-slum03-cyberpunk-slum-design.md`。

**Status:** 2026-09-28、ユーザーが「途中で止めずに推奨案で進めてください」と計画実行と継続判断を承認。以下のチェックボックスはcontrollerが実証・レビュー後に更新する。中間のユーザー回答待ちは挟まず、目視・歩行・保存再読込の未確認状態は別に保持する。

## Global Constraints

- 文書の正本は親worktree `/workspaces/create-reso-world/docs/superpowers/`。実装worktreeは `/workspaces/create-reso-world/.worktrees/slum03`、既存ブランチは `feat/slum03-slum`、着手前HEADは `93bca2f`。親worktreeはdetached HEADのままで、ここへ実装しない。
- 以下のFilesは特記がなければ実装worktree内の **`slum03/` 基準**。Python／テスト／Blender／liveコマンドも同ディレクトリをcwdにする。Pythonは `uv run python`、テストは `uv run pytest`。
- 仕様ファイルはユーザー指示で親worktreeへ移動済み。実装worktreeの旧仕様パスの未stage削除は意図した状態。勝手に復元・stageしない。親にある仕様と計画を子へ絶対パスで渡す。仕様の書き戻しや文書移転はこの計画の実装タスクに含めない。
- root/project両方のAGENTS.mdを守る。slum02、Root、既定床・空・全体照明、avatar/spawn、依存lockを変更しない。新root/state、無断adopt・prune・削除、push・merge・PRは禁止。
- 街区120×120 m、工場跡地40×30 m、中央32×22 mとその上方3 m、既存の幅3 m以上の主導線、Yarol敷地と東向き入口を維持する。工場跡地の周縁まで空白にする必要はない。
- `稲垣は絶対マカぶる`、北壁の位置・寸法、北の巨大都市／東の森林への視線、既存AR3系統と主文字固定を維持する。全方位高層リングを作らない。
- 初期合計は廃墟32・小屋28・屋台28・ネオン店先8・Yarol1＝97主要用途。市場20＋枝道8、東横丁6＋南東2。背景や部品数を加算しない。数を減らす必要が出たら理由と代案をユーザーへ提示する。
- 新規建物の幅・奥行8〜14 m、北・西の高さ10〜30 m、東の視線帯4〜12 m、小屋の幅・奥行4〜7 m／高さ3〜6 m、新規屋台幅2.5〜4 m／奥行3〜5 mを基準とする。既存大型物は無理に縮小しない。
- 廃墟6系統以上、小屋4系統以上、屋台4用途以上。屋台は各2段以上・商品12点以上。頭上設備12まとまり以上。数は幾何と用途の証拠で検査し、見た目の代用にしない。
- `slum03`／`Slum03_Slum`／`.resoloop/slum03/state/slum03.json`、root位置 `[0,4.5,0]`、seed `260927` を維持する。旧run `finalfix-m-20260928T0511` と全untracked生成物を保持する。
- 原版の150 meshes／339 Slots／400 Components／34 collidersを新版の期待値に固定しない。背景の資源を街区密度へ数えない。FPS保証や全域の固定三角形上限は設けない。
- strict auditの `ITEM_GRABBABLE_MISSING` と森林奥の旧FINAL-I1は別件のまま。改善受入と完全納品を分け、Grabbable追加や広い外部参照許可で通さない。
- 最新の継続指示によりGate Bはcontrollerの検査・レビューで継続判断し、ユーザー回答待ちでTask8を止めない。実機目視・歩行・新版の保存再読込の人間確認は別項目としてpendingを維持し、構造テストやBlender画像で代用しない。

## Review Focus

1. **代表更新の共有資源:** 共通素材・source相対パス・新規キー衝突による対象外変更を許さない（Task6 `test_shared_provider_edit_rejected`、`test_protected_asset_sources_and_bytes_unchanged`）。
2. **旧Layoutと不正メタデータ:** 旧JSONは読めるが、新しい密度条件を満たした扱いにしない。未知stage・NaN・boolを数値として受理しない（Task1 `test_legacy_layout_not_full_density`、`test_invalid_density_metadata`）。
3. **数量の水増しと空間の誤認:** 重複・背景・空アンカー・小物・広範囲除外で密度を通せず、天幕のAABBを通路閉塞と誤認しない（Task2密度ケース、Task5開口ケース）。
4. **追加順と縮小変種:** 配置順変更で既存形状が変わらず、奥行3 mの屋台から商品や支柱がはみ出さない（Task3安定seed、Task4小型屋台、Task9独立export）。
5. **証跡の取り違え:** 部分更新・capture timeout・旧版の保存成功を全域／新版のpassにしない。被写体が写らないカメラも成功証拠ではない（Task7受入記録、Task10集計テスト）。

## 作業構成と実行順

新規の `density_*` はslum03専用であり、汎用都市生成基盤にはしない。

| 責務 | 主なファイル | 担当 |
| --- | --- | --- |
| 密度型・互換読込・seed／部品証拠 | `types.py`, `density_model.py`, `detail_evidence.py`, `layout.py` | 1 |
| 配置・分布・枝道・ブロックアウト | `density_layout.py`, `density_metrics.py`, `density_blockout.py` | 2 |
| 廃墟／小屋の近景 | `architecture_detail.py`, `ruins.py`, `shacks.py` | 3 |
| 屋台・商品 | `market_detail.py`, `merchandise.py`, `stalls.py` | 4 |
| 評価・色・コライダー | `build.py`, `evaluated_detail.py`, `native/colliders.py`, `verify_assets.py` | 5 |
| 完全候補の限定更新と資源保護 | `density_candidate.py`, `candidate_scope.py`, `scripts/build_density.py` | 6 |
| 比較視点・証跡・代表受入 | `density_views.py`, `density_acceptance.py`, `preview.py`, `delivery.py` | 7 |
| 全域の生活・設備・横丁・散布 | `utilities.py`, `nightlife.py`, `overhead.py`, `gn_scatter.py`等 | 8 |
| 全域exportと統合 | 既存pipeline／検査／新runの生成物 | 9 |
| 実機受入と報告 | 新版manifest／delivery／live証跡／回帰 | 10 |

依存波は **1 → 2 → {3,4} → 5 → 6 → 7 → Gate B（controller）→ 8 → 9 → Gate D（controller）→ 10**。並列化できるのは3と4だけで、共通APIはTask1で固定する。Taskは全Stepsを含めて委譲し、Step単位でdispatch/reviewしない。

選択済み方式はSDD、TDD、per-task review、lineage-only。子の起動は現行role APIを使い、通常はmodelを指定しない。リポジトリの同期直列dispatch規約を優先し、同じworktreeへの同時writerを作らない。並列Task worktreeを使う場合も上流SDD／using-git-worktreesの手順を正とし、controllerが承認済みコミットをTask番号順に統合する。失敗Taskは統合せず、競合時はcherry-pickを中止して更新済み親HEADから該当Taskを再実行する。新たなroot作業ブランチは作らない。

各Taskは全Stepsの実装→検証を同期完了→task reviewの順。Gate B/Dのliveと人間確認はレビュー済みTaskの間に置くcontroller作業であり、未完了TaskのStepだけを先にレビューしない。レビュー子はread-only。レビュー対応はreceiving-code-reviewを通し、review scopeはtask／re-review／branchの所定区分を使う。最終SDD cleanupは全承認後に新しい計画のworkspaceだけを対象とし、旧SDD資料は削除しない。

## データと証跡の共通仕様

- `Layout.density: DensityConfig | None = None` を末尾へ追加。旧8引数の生成と旧JSON読込を維持する。`DensityConfig(stage: str, zones: tuple[DensityZone,...], routes: tuple[DensityRoute,...], branch_clearances: tuple[RectXZ,...], selected_keys: tuple[str,...])`、`DensityZone(key: str, bounds: RectXZ)`、`DensityRoute(key: str, purpose: str, corridor: RectXZ, openings: tuple[DensityOpening,...])`、`DensityOpening(bounds: RectXZ, reason: str)`を `types.py` に置く。stageは `blockout | representative | full`、purposeは `residential | market | alley`。
- 追加のPlacement.paramsは `detail_profile='v2'`, `variant`, `density_zone`, `cluster`。別配置の付属設備には `attachment={parent_key, contact_min, contact_max, reason}`。contactはrootローカル座標。親不在・自己参照・循環・非有限値・範囲外接触を拒否する。旧paramsには変更を強制しない。
- Assembly.metaの `detail_groups` は `{id, category, part_indices}` の列。categoryは `architecture | shelf | merchandise | utility | lived_in`。実在するMeshDataの非空faces／verticesから境界を算出する。同一商品部品を別商品へ重複登録せず、metadataの自己申告件数を信用しない。
- 新評価レポートには `layout_sha256` とobjectごとの `detail_groups`、`evaluated_bounds`、`placement_key`、変種／用途、実体化後の幾何証拠を持つ。sourceから求めた部品証拠と実体化後の境界は区別する。旧レポートを新評価の証拠へ昇格させない。
- `density-report.json` はstage、`geometry_basis=blockout|evaluated`、counts/by_zone/variants、占有矩形のunion、frontage_gaps、attachment関係、issues、参照するLayout／build／exportのpath・hashを記録する。評価後の各オブジェクト占有矩形のunionは保守的な範囲であると明記し、開口の通行可否と分ける。離れた建物群を先に1つのAABBへ結合して空地を埋めない。
- 代表の対象は **`ruin-west`, `shack-row`, `market-west`** と、その内部に結合する付随設備・生活道具。最初は別配置を増やさず、対象外変更を最小化する。原版manifestの名前→安定キーを実際に照合する。
- baseline manifestはTask1で `content/slum03/density-baseline.json` に一度だけ保存する（元canonicalと同じ親ディレクトリなのでasset sourceが有効）。元canonicalとhashが同じことを検査し、以後は上書きしない。baseline Layoutは保持済みrunの `layout.json` を使う。生stateはコピー・追跡しない。
- 各タスクの新しい出力は `artifacts/slum03/<unique-run>/`、`content/slum03/bundles/<unique-run>/`、`content/slum03/<unique-run>-candidate.json`。実行時に未使用run名を決め、既存への上書きは失敗させる。

### 実行時のパスとコマンド変数

次は計画承認後、実装projectをcwdにして設定する。再開時はledgerに記録したrun名を復元し、未使用名を取り直して同じ処理を重複実行しない。新CLIはそれを実装するTaskのGREEN後に限り実行する。

```bash
BASE_LAYOUT=artifacts/slum03/finalfix-m-20260928T0511/layout.json
BASE_MANIFEST=content/slum03/density-baseline.json
LAYOUT_BLOCK=content/slum03/density-blockout-layout.json
LAYOUT_REP=content/slum03/density-representative-layout.json
LAYOUT_FULL=content/slum03/density-full-layout.json
STAMP=$(date -u +%Y%m%dT%H%M%SZ)-$$
RUN_BLOCK=density-block-$STAMP
RUN_PROBE=density-probe-$STAMP
RUN_REP_A=density-rep-a-$STAMP
RUN_REP_B=density-rep-b-$STAMP
RUN_FULL_C=density-full-c-$STAMP
RUN_FULL_D=density-full-d-$STAMP
```

代表buildの検証コマンドは次のとおり。full時はstage／Layout／runをfull/C/Dへ置換する。`asset-summary.json`の比較pass、scope-reportの対象外変更0、各buildのerrors/uv_issues空が期待値。目視合格ではない。

```bash
uv run python scripts/build_density.py --stage representative --base-manifest "$BASE_MANIFEST" --layout "$LAYOUT_REP" --run "$RUN_REP_A" --root-y 4.5
uv run python scripts/build_density.py --stage representative --base-manifest "$BASE_MANIFEST" --layout "$LAYOUT_REP" --run "$RUN_REP_B" --root-y 4.5
uv run python scripts/summarize_offline.py --first "$RUN_REP_A" --second "$RUN_REP_B" --layout "artifacts/slum03/$RUN_REP_A/layout.json"
uv run python -m modeling.slum03.verify_assets --reports "artifacts/slum03/$RUN_REP_A" --layout "artifacts/slum03/$RUN_REP_A/layout.json"
```

---

### Task 1: 密度データ・互換読込・安定した部品証拠

**Files:** Modify `modeling/slum03/{types.py,layout.py}`; Create `modeling/slum03/{density_model.py,detail_evidence.py}`, `content/slum03/density-baseline.json`, `tests/slum03/{conftest.py,test_density_model.py,test_detail_evidence.py}`。

**Interfaces:** `stable_seed(seed: int, key: str, channel: str) -> int`; `detail_groups(assembly: Assembly) -> list[dict]`; `validate_density_config(layout: Layout) -> list[Issue]`。`TARGET_COUNTS={'ruin':32,'shack':28,'stall':28,'nightlife':8,'yarol':1}` と `REPRESENTATIVE_KEYS` はdensity_modelだけが定義する。conftestは `legacy_layout`、`legacy_manifest`、`legacy_reports` を既存run／保存baselineから読むfixtureを提供する。

- [x] **1. REDを定義:** `test_legacy_layout_not_full_density` は旧Layoutが読めて `.density is None` のままでありfull stageを付与されないことを確認。`validate_density_config` はNoneを互換形式として受理し、密度達成の判定はTask2の別APIに任せる。round-tripでDensityConfigが一致し、未知stage、NaN、bool、duplicate route／zone、空理由のopening、循環attachmentを拒否するparametrizeを追加。`stable_seed(260927,'a','wear')` は別プロセスでも同値、keyかchannel変更で異なることを検査する。空のpart_indices／存在しないindex／重複商品登録を拒否する。
- [x] **2. RED実行:** `uv run pytest tests/slum03/test_density_model.py tests/slum03/test_detail_evidence.py -q`。新API未実装で失敗することを確認する。
- [x] **3. 実装:** 上記型・読込・検査を追加。既存 `validate_layout` の主導線一致条件は維持し、追加枝道はdensity側で検査する。stable_seedはseed/key/channelのUTF-8をSHA-256化して整数化し、Pythonのhashや共通RNGを使わない。部品証拠はMeshDataから計算。baselineをコピーしhash照合する。
- [x] **4. GREEN／回帰:** 上記に `tests/slum03/test_layout.py tests/slum03/test_spatial.py tests/slum03/test_pipeline.py` を加えて実行。旧Layout読み書き／既存8引数生成が通ることを確認する。
- [x] **5. Commit:** 上記Filesだけをstageし `feat: add backward-compatible density metadata and detail evidence`。実装worktreeで消えている仕様ファイルはstageしない。

### Task 2: 全域ブロックアウトと空間密度検査 — Gate A

**Files:** Create `modeling/slum03/{density_layout.py,density_metrics.py,density_blockout.py}`, `tests/slum03/{test_density_layout.py,test_density_metrics.py}`; Modify `modeling/slum03/spatial.py`（追加枝道の検査を小関数として再利用）。

**Interfaces:** `build_density_layout(baseline: Layout, stage: str, seed: int=260927) -> Layout`; `union_area(rects: Sequence[RectXZ]) -> float`; `density_report(layout: Layout, reports: Mapping[str,Report], geometry_basis: str) -> Report`; `validate_density(layout: Layout, reports: Mapping[str,Report], geometry_basis: str) -> list[Issue]`。CLI: `uv run python -m modeling.slum03.density_layout --base "$BASE_LAYOUT" --stage blockout --output "$LAYOUT_BLOCK"`（representative／fullもそれぞれのLayoutパスに保存）。blockoutはexport/live候補を作らず、専用Blenderシーンと画像・レポートだけを出す。

- [x] **1. REDを定義:** `assert Counter(p.kind for p in full.placements if p.kind in TARGET_COUNTS)==TARGET_COUNTS`。代表Layoutは既存placementのpose/keyを全て保ち3つだけv2。旧4/2/2候補、全物を1区画へ集中、同じ位置の重複、背景増量、空メッシュのcounts水増しを不合格にする。`union_area([RectXZ(0,2,0,2),RectXZ(1,3,0,2)])==6`。frontage gap20 mは許容、20.01 mは検出、小物／背景／無承認openingでは隠せない。中央・枝道・Yarol入口侵入と支持先のないattachmentを検出する。
- [x] **2. RED実行:** `uv run pytest tests/slum03/test_density_layout.py tests/slum03/test_density_metrics.py -q`。
- [x] **3. 実装:** 既存重要アンカー・主導線を保持して追加座標を固定。北西・南西・市場・東の非重複zone境界と枝道、意図したopeningをこのモジュールへ明記。新規yawは当初0/90/180/270度を使い、旧poseを変更しない。countsを減らして衝突を避けず、不成立なら停止して修正案を報告する。unionは矩形のsweep、frontageは帯内の評価後範囲を長手方向へ投影してinterval unionを取る。左右各10 m、Y=0〜8 m、幅・高さがそれぞれ1 m以上、20 m超を規則とする。attachmentの許可は接触範囲内のみ。
- [x] **4. GREENと実ブロックアウト:** testsに既存layout/spatial回帰を加えて通す。CLIでblockout／representative／fullをそれぞれ `$LAYOUT_BLOCK`／`$LAYOUT_REP`／`$LAYOUT_FULL` に保存する。blockoutとfullのplacement poseは同一とし、代表は旧配置を保持する。`resoloop blender run modeling/slum03/density_blockout.py --arg=--layout --arg="$LAYOUT_BLOCK" --arg=--output --arg="artifacts/slum03/$RUN_BLOCK" --json` で真上・北西・南西・市場・東の1.6 m視点を作る。97用途、clearance、4地区の密度をcontrollerが画像でも確認し、Gate Aの結果を保存する。これはBlender検証でありlive合格ではない。
- [x] **5. Commit:** 対象ソース／テストと承認したblockout Layout・レポート・画像だけをstageし `feat: define dense district layout and spatial quality gates`。

### Task 3: 廃墟・小屋の近景変種

**Files:** Create `modeling/slum03/architecture_detail.py`, `tests/slum03/test_architecture_detail.py`; Modify `modeling/slum03/{ruins.py,shacks.py}`, `tests/slum03/{test_ruins.py,test_shacks.py}`。

**Interfaces:** `detailed_ruin(p: Placement, seed: int) -> Assembly`; `detailed_shack(p: Placement, seed: int) -> Assembly`。既存 `build_assemblies(layout,sector)` は `detail_profile=='v2'` のplacementだけ新処理へ渡す。Task1のseed／detail_groupsを使用する。Task4と共有ファイルを変更しない。

- [x] **1. REDを定義:** 6廃墟系統 `slab_bay, broken_corner, service_core, stepped_shell, exposed_frame, patched_facade` と4小屋系統 `corrugated, plywood, tarp, pallet` の幾何差を確認する。同じ形の色／回転違いを変種にしない。poseの0/90度、追加順変更、seed変更のテストを追加。`assert old_unselected_assembly == new_unselected_assembly`、`assert v2.meta['placement_key']==p.key`。凹んだ開口、梁スラブ、支持された増築、生活道具の実部品と境界を検査する。
- [x] **2. RED実行:** `uv run pytest tests/slum03/test_architecture_detail.py tests/slum03/test_ruins.py tests/slum03/test_shacks.py -q`。
- [x] **3. 実装:** 既存のbox/tube/wall_with_openings/meshを再利用し、MeshDataを部品単位で造形する。yawを頂点へ適用し、origin・export名・既存キーを保持。v2部品はgroup参照用indexが確定する順に構築する。旧generatorと既存palette値は変更しない。歩ける内装や新しい階段ルートは作らない。
- [x] **4. GREEN:** 上記と `test_geometry.py test_materials.py` を実行。v2の1棟＝1 Assembly、全partのfaces/材料の有効性、図面上の占有内への収まりを確認。旧2件固定テストはlegacy fixtureの試験として維持し、新版試験を別に置く。
- [x] **5. Commit:** Filesを限定して `feat: add detailed ruin and shack variants`。

### Task 4: 小型屋台と12点の商品・設備

**Files:** Create `modeling/slum03/{market_detail.py,merchandise.py}`, `tests/slum03/{test_market_detail.py,test_merchandise.py}`; Modify `modeling/slum03/stalls.py`, `tests/slum03/test_stalls.py`。

**Interfaces:** `stock_items(p: Placement, seed: int) -> list[Assembly]` は商品ごとのローカル形状を返す（exportオブジェクトにはしない）。商品originは屋台ローカルで、結合時に各頂点へ加算してから屋台のyawを適用する。`detailed_stall(p: Placement, seed: int) -> Assembly` は商品を屋台へまとめ、各商品のpart_indicesを記録する。外部向けgenerator署名は変更しない。

- [x] **1. REDを定義:** 4用途 `electronics,tools,prosthetics,reclaimed_equipment` と幅2.5/4・奥行3/5の組合せを試験。`assert merchandise_count >= 12`、`assert shelf_count >= 2`。商品groupは実partに結びつき、同じ箱12個・chipを独立商品として二重計上するケースは不合格。全商品／支柱／留め具が実寸の棚・屋台内に収まること、表から商品形状が読める配置、未選択market-eastの変更ゼロを確認する。
- [x] **2. RED実行:** `uv run pytest tests/slum03/test_market_detail.py tests/slum03/test_merchandise.py tests/slum03/test_stalls.py -q`。
- [x] **3. 実装:** 現行のz=±3.5や商品z=-3.8等をv2へ持ち込まず、棚長から展示cellと支持点を決める。厚い天幕・留め具・筋交い・収納、基板／工具／モニター／義肢の形状差を作る。各商品を一時Assemblyとして構築後に親1メッシュへ結合し、商品用Slotを量産しない。旧paletteと未選択generator結果は保持する。
- [x] **4. GREEN:** 上記とgeometry回帰を通す。商品カテゴリ別のparts/bounds、2棚、欠損・床への張り出しゼロを確認。旧2基固定試験はlegacyとして維持する。
- [x] **5. Commit:** Filesを限定して `feat: build stocked compact market stalls`。

### Task 5: 評価後の証拠・色・コライダーを生成器へ接続

**Files:** Create `modeling/slum03/evaluated_detail.py`, `tests/slum03/{test_evaluated_detail.py,blender_density_probe.py}`; Modify `modeling/slum03/{build.py,sectors.py,verify_assets.py,vcolor.py,native/colliders.py}`, `tests/slum03/{test_build.py,test_colliders.py,test_asset_verification.py}`。Create `tests/slum03/test_density_dispatch.py`（R6: 同一sector内の異種kindを各generatorへ振り分ける統合回帰）。

**Interfaces:** `observe_detail(assembly: Assembly, evaluated_geometry: Mapping[str,Any]) -> Report`; `validate_evaluated_density(layout: Layout,reports: Mapping[str,Report]) -> list[Issue]`。evaluated_geometryの必須キーは `vertices`（評価後のResonite rootローカルVec3列）、`faces`（頂点index列の列）。sourceの部品indexと評価後幾何の対応・境界を照合できない場合は失敗にする。`write_scene(sector,output,layout)` と `collider_slots(layout,reports)` は外向き署名を維持する。

- [x] **1. REDを定義:** full Layout由来の明示した部分fixtureで、同一sector内に混在する実装済みruin/shack/stallをkind別に振り分け、欠落・重複なくAssembly/buildへ到達すること、legacy単一kindの出力が不変であることを検査する。新nightlifeのv2はTask8で実装するため、未実装full入力は黙って欠落させず失敗とし、この部分fixtureを全97用途の生成成功には数えない。全97の実生成はTask8/9で確認する（R7）。偽のdetail group、評価で消えた／潰れた形状、sourceだけ存在してexportにない商品、Layout hash違いを検出する。open canopyの通路は空いたまま、counter/脚のみ衝突し、閉鎖建物の外殻にはcolliderがある。既存の橋・検問・床34個のbaseline collider定義が無関係に変わらないことを確認。branch corridor侵入とattachmentの許可範囲外貫通を試験する。
- [x] **2. RED実行:** `uv run pytest tests/slum03/test_evaluated_detail.py tests/slum03/test_build.py tests/slum03/test_colliders.py tests/slum03/test_asset_verification.py -q`。
- [x] **3. 実装:** sectors.pyの密度Layout用dispatchで同じsectorにある異種kindを各generatorへ渡し、legacy経路は保持する。buildのobject entryへ所有key・変種・検証済みgroupを渡し、評価済みmesh/境界と照合する。group対応が消えるmodifierは黙って成功にせず拒否する。v2だけ安定seedと接合・雨だれ・摩耗の位置情報を色処理へ渡し、既存のvertex_colors出力は保持する。colliderは新しいplacement種も処理し、旧キーを維持。屋台・開口は実際の脚／counter／壁の部分形状から作り、囲いAABBで塞がない。背景にcolliderを増やさない。
- [x] **4. GREEN／Blender評価:** 上記を通し、`resoloop blender run tests/slum03/blender_density_probe.py --arg=--output --arg="artifacts/slum03/$RUN_PROBE" --json` で代表3単位と小型屋台、開口、UV0／追加UV／頂点カラー／法線の保持を評価する。レポートの空オブジェクト・shape消失を意図的に入れたfixtureが失敗することも確認する。
- [x] **5. Commit:** 対象のみstageし `feat: verify evaluated detail and density-aware collision`。

### Task 6: 対象外を保護した代表候補と再現可能な出力

**Files:** Create `modeling/slum03/{candidate_scope.py,density_candidate.py}`, `scripts/build_density.py`, `tests/slum03/{test_candidate_scope.py,test_density_candidate.py}`; Modify `modeling/slum03/{pipeline.py,postprocess.py}`, `scripts/build_offline.py`（必要な共通呼出しを小関数として公開、既存CLIを保持）、`scripts/summarize_offline.py`（明示 `--layout` と両runのLayout hash一致検査を追加）。

**Interfaces:** `compose_candidate(baseline_path:Path,draft_path:Path,layout:Layout,output:Path) -> Report`; `check_candidate_scope(baseline:Manifest,candidate:Manifest,layout:Layout,manifest_dir:Path) -> list[Issue]`。CLIは上記の実行コマンドに合わせ、`--stage` はrepresentative/full、`--base-manifest`／`--layout`／`--run`／`--root-y` を必須とする。stage blockoutは拒否。raw draft／protected candidate／scope-report／provenanceを区別する。

- [x] **1. REDを定義:** `test_shared_provider_edit_rejected` は対象外にも使われる素材の編集を失敗させる。`test_protected_asset_sources_and_bytes_unchanged` は文字列とhashの両方を比較。別root位置、欠落node、改名、key衝突、state自動生成、代表stageで全域Layoutを渡すケースを拒否する。出力先変更による相対sourceの解釈変更も拒否する。fixtureの対象3つ以外のnode/component/asset宣言が正規化後も完全一致することを検査する。
- [x] **2. RED実行:** `uv run pytest tests/slum03/test_candidate_scope.py tests/slum03/test_density_candidate.py tests/slum03/test_pipeline.py -q`。
- [x] **3. 実装:** canonical全manifestのdeep copyを土台に、選択placement名から確認した安定Slot、StaticMesh／Renderer、直接付随するcollider等だけを置換する。必要な新providerは新keyで追加し、共有旧providerは変更しない。範囲外の再生成差分を無視して新候補へ混ぜず、保護検査で止める。未変更assetsは旧source文字列とbytesを保持する。同じ親 `content/slum03/` にbaseline/draft/candidateを置く制約とし、path rebasingを曖昧にしない。raw draftは従来pipelineで全区画・同じ保存Layoutから作る。raw draftの対象外sourceは出力runのパス差だけを許し、bytesが旧資源と一致しない場合は停止する。R8/R9: exporterの素材共有処理に伴う、定義が完全一致するproviderのraw内移動と空・未参照provider Slotは、素材型・参照不存在・元providerとの対応を検証し、全キーと根拠を記録して除外できる。元providerが移動せず以前の場所で再利用される場合の空Slotも、同じ型・完全一致・未参照・対応条件を満たす場合に限り、移動とは別に記録する。候補では旧providerの親・定義・キーを保持し、その他のraw差分や参照される空Slotをこの例外へ含めない。最終候補の全資源を同じ保存Layoutの新しい評価・export報告と照合し、旧sourceを維持した資源も新exportとbytesが一致する証拠を残す。古い評価報告へ差し替えて再生成の意図しない差分を隠さない。provenanceに各object/assetの実際の参照先を記録する。summarize_offlineは新しい保存Layoutを `--layout` から受け、旧 `content/slum03/layout.json` を密度runの集計に使わない。camera/testは旧項目を維持した追加だけ許可。候補をcanonicalへ昇格する処理やlive呼出しはこのscriptに入れない。
- [x] **4. GREEN／独立export:** 上記とfull pytestを通し、代表Layoutから上記のA/Bコマンドを実行。`compare_geometry_exports`で新生成payloadを丸めず比較、scope-reportで対象外更新／削除／asset変更0を確認。実際の件数を数え、旧150等は比較元としてだけ記録する。sourceのprovenanceを検査して取り違えを失敗させる。
- [x] **5. Commit:** コードとレビュー済み代表runのLayout／候補／report／編集元を必要な範囲だけstageし `feat: preserve unrelated content in density candidates`。生成物の一括stage禁止。

### Task 7: 代表比較・実機確認の証跡 — Gate B

**Files:** Create `modeling/slum03/{density_views.py,density_acceptance.py}`, `tests/slum03/{test_density_views.py,test_density_acceptance.py}`; Modify `modeling/slum03/{preview.py,delivery.py}`, `scripts/build_density.py`, `tests/slum03/test_delivery.py`; Create `artifacts/slum03/<representative-run>/representative-review.json` と比較画像／timing。

**Interfaces:** `density_cameras(layout:Layout,root_position:Vec3) -> dict[str,dict]`; `add_density_checks(manifest:Manifest,layout:Layout) -> None`;  `validate_acceptance(record:Report,manifest_sha256:str,stage:str) -> list[Issue]`; `summarize_density_delivery(layout:Layout,build_reports:Mapping[str,Report],live_results:Mapping[str,Any],acceptance:Report) -> Report`。後者2つはdensity_acceptanceに置く。recordは `{stage,manifest_sha256,status,evidence,confirmed_by,confirmed_at,scope}`。ユーザーの明示確認なしには `status='pass'` を作らない。旧deliveryの7 checksとstrict結果を維持し、密度の部分受入とワールド全体のoverallを分ける。previewは既存署名を保ち、任意の共有cameraデータを渡せるようにする。offlineはRoot offsetを戻し、二重加算しない。

- [x] **1. REDを定義:** eye localY=1.6がRoot Y=6.1になること、市場比較カメラは市場へ向き背景だけを向かないこと、baseline/new比較の同一pose/FOV=60を検査。狙う対象が視錐台外／手前に遮蔽物／暗すぎて判別不能なら「画像生成成功」を視覚passに使えない。画像の確認結果 `subject_visible`／`exposure_usable` と人間の確認を分け、未確認を自動trueにしない。別manifest hashの承認、capture timeout、代表承認をfullへ流用する記録を拒否する。user visual受入だけでwalk/resourcesがpassにならず、旧版の保存確認・監査失敗・森林残件がoverall成功へ変わらないことも検査する。旧固定件数試験はbaseline fixtureへ分離し、新版の試験は実証跡とmanifestの件数/hashを比較する。
- [x] **2. RED実行:** `uv run pytest tests/slum03/test_density_views.py tests/slum03/test_density_acceptance.py tests/slum03/test_delivery.py tests/slum03/test_preview.py -q`。
- [x] **3. 実装とGREEN:** 旧cameraは保持し `density-ruin-near, density-shack-near, density-market-inward, density-west-street, density-east-lane` の明示target付き視点を追加。近景1〜3 m／中景を別視点にし、画像の確認とpure testを区別する。上記testsとfull suiteを通す。acceptanceとdeliveryの集計は代表／fullの両stageで試験する。
- [x] **4. 比較画像と最終QA候補:** baselineと代表candidateを同じcamera／診断用照明で描画し、実際に画像を開いて被写体を確認する。`add_density_checks`をbuild_densityへ接続し、Task6候補にも新camera/testを追加した `content/slum03/${RUN_REP_A}-review-candidate.json` を別名保存する。幾何・Slot・Component・asset変更0を再照合し、追加後のhashでscope-report／provenance／acceptanceを揃える。Gate Bはこのreview候補を使う。実機user受入のstatusはpendingにし、画像・recordのpathを保存する。
- [x] **5. Commit／Task review:** 対象コード・テスト・offline比較をcommitする（`feat: record representative visual acceptance separately`）。Task7全体のレビュー後、controllerが以下のGate Bへ進む。

### Gate B — Task7承認後のcontrollerチェックポイント

2026-09-28 controller実行結果: **反映前のdiffで停止**。Task1〜7はレビュー済み（HEAD `4d7fa5a`、controller再実行435 tests pass）。唯一の「スラム街03」へ再接続し、doctorと所有rootの観測は成功したが、通常diffと `--cache off` のdiffがともに exit 6 / `APPLY_TARGET_AMBIGUOUS`。1件だけ存在する既存土台Slotの同じIDを2回候補へ数えている。導入済みResoLoopの再接続時snapshot結合処理に重複排除不足があるという診断。apply/adopt/prune/state編集は未実行、state hash不変。依存版・ロック変更は本計画の対象外なので、ResoLoop側の限定修正と版更新の承認が必要。Task8以降は未着手。詳細はSDDの `gate-b-debug-output.md` と `gate-b-report.md`、生証跡はprojectの `.resoloop/slum03/density-gateb-20260928T214904Z/`。これは通常の中間承認待ちではなく、安全な所有解決を妨げる実行阻害要因である。

2026-09-29 追記: 承認を受けて ResoLoop の修正を 2 件（usaturn/resoloop#3 の Slot 重複の排除、#4 の保存後の asset URL の移行）ロックに反映した（`d6e5222`、`e270d44`、0.1.0-preview.14.pr3.20260929）。3 回目の Gate B では、diff で対象外の変更が版の刻印の 1 件だけ、apply は成功、再 apply は書き込み 0、test は 2/2、対象外の子は不変、strict audit はレビュー済みの 4 ロールで既知の `ITEM_GRABBABLE_MISSING` だけが残った。capture は出力フォルダが未マウントのため実行していない。controller は Task8 への継続を判断した。人間の受入は pending。詳細は SDD の `gate-b3-report.md`。

- [x] 全子の終了を確認してLive手順で代表候補を反映し、構造・駆動・対象外不変・同一入力再applyのゼロ書込を確認する。既存stateとliveの所有境界を一元管理するため、ここはcontrollerが直接実行し、子へmutationを委譲しない。
- [x] 廃墟・小屋・屋台の代表比較と取得できた実機証拠をcontrollerが検査する。品質不良は該当Taskのfix/re-reviewで直し、候補を再作成する。自動captureが利用できなくても、最新の継続指示に基づき確認できた証拠と制限を記録してTask8へ進む。人間の実機受入はpendingのままにする。
- [x] controllerの継続判断と、人間の受入を別フィールドに記録する。後日ユーザーの明示承認が得られたときだけ対象hash・発言・時刻を人間受入へ記録する。未確認の歩行・保存を補完しない。

### Task 8: 全域の生活設備・横丁・瓦礫へ展開

**Files:** Create `modeling/slum03/utilities.py`, `tests/slum03/test_utilities.py`; Modify `modeling/slum03/{nightlife.py,overhead.py,plaza.py,gn_scatter.py,ground.py,native/lighting.py}`, `tests/slum03/{test_nightlife.py,test_overhead.py,test_scatter.py,test_ground.py,test_lighting.py}`。Task2のfull Layoutに追加設備・具体的support routeを確定する変更は `density_layout.py` だけに置く。

**Interfaces:** `utility_parts(p:Placement,seed:int) -> list[MeshData]` は所有Assemblyへ結合する設備部品。generator署名は既存のまま。独立の頭上経路はoverhead placementごとに1 Assemblyとし、支持点・経路・clusterをparamsで持つ。full selected_keysは変更対象の街区内97用途、頭上設備、中央周縁と表面表現だけを明記する。

- [ ] **1. REDを定義:** 各建物群に実際のutilityとlived_in group、32/28/28/8/1と変種数、12以上の支持された頭上経路が存在することを検査。線分分割だけの水増し、空のgroup、無支持endpoint、3 m空間への侵入を拒否する。東の6店／南東2店、市場20/枝道8、Yarol不変を確認する。scatterを増やしても中央床／全枝道への評価後侵入が0であることを試験する。
- [ ] **2. RED実行:** `uv run pytest tests/slum03/test_utilities.py tests/slum03/test_nightlife.py tests/slum03/test_overhead.py tests/slum03/test_scatter.py tests/slum03/test_ground.py tests/slum03/test_lighting.py -q`。
- [ ] **3. 実装:** 全域のv2を有効にし、壁の設備群・小屋の生活道具・店先の庇／入口／表示を用途に合わせる。散布は塊・機械残骸・鉄骨・小瓦礫を混ぜ、実体化後の形状を検査する。床の油染み等は表面だけ。既存palette／既存6lightsは保持し、必要な新しい局所光はcluster単位・影なしで追加して資源数を記録する。北壁／graffiti／AR／Yarol、森林と背景は触らない。
- [ ] **4. GREEN／幾何検証:** 上記とTask1〜7の回帰を通す。R6のkind別dispatchを実際のfull Layoutと全generatorで検査し、97主要用途が欠落・重複なく生成されることを確認する。full Layoutのblockoutとの差分をレビューし、主要poseや通路がずれたらGate Aの画像と密度検査を再実行する。独立背景を触らずに生活圏全域が改善していることを区画別に確認する。
- [ ] **5. Commit:** 対象のみstageし `feat: populate district utilities nightlife and lived-in detail`。

### Task 9: 全域export・再現性・資源検査 — Gate C

**Files:** Modify `modeling/slum03/{verify_assets.py,density_metrics.py,density_candidate.py}`, `scripts/summarize_offline.py`（新stageの集計のみ）; Create `tests/slum03/test_density_integration.py`, `artifacts/slum03/<full-runs>/`, `content/slum03/bundles/<full-runs>/`, `<full-run>-candidate.json`。

**Interfaces:** Task6のbuild_density CLI／scope検査をfullで再利用する。保護対象はRoot設定、既存背景・森林・道路・橋・検問・北壁文字・AR等。既存node/keyは保持し、差分対象が消える場合は自動pruneせず停止する。

- [ ] **1. REDを定義:** full candidateのcounts／hashは実際の出力に一致すること、selected metadataだけ変えて生成しなかった物をfailにすること、full Layoutへrepresentative reportsを混ぜた場合にfailになることを試験。レイアウト順を変えても同じkeyのgeometryが変わらず、mesh減少・UV層消失・正規化丸めで差を隠せないことを試験する。
- [ ] **2. RED実行:** `uv run pytest tests/slum03/test_density_integration.py tests/slum03/test_asset_verification.py tests/slum03/test_pipeline.py -q`。
- [ ] **3. 実装とGREEN:** 実際のbuild/exportのgroup・hash・資源を集計へ接続する。full密度／形状条件と構造条件の双方を満たした候補だけを採用可能とし、目視／歩行はpendingのまま保つ。full suite、`bash ../scripts/check-layout.sh`、`git diff --check` を実行する。
- [ ] **4. 独立生成と画像:** 上記の代表buildコマンドを `--stage full`、`$LAYOUT_FULL`、`$RUN_FULL_C`／`$RUN_FULL_D` に置換して2回同期実行。summarize_offlineもC/DとCの保存Layoutを渡す。decoded mesh JSONの完全一致、density-report、`uv run python -m modeling.slum03.verify_assets --reports "artifacts/slum03/$RUN_FULL_C" --layout "artifacts/slum03/$RUN_FULL_C/layout.json"` のissues空を確認。真上と少なくとも中央北西／南西／市場入口／市場内部／東横丁／Yarol前の比較を開き、暗さや遮蔽で未確認になった画像は撮り直す。triangles/vertices/mesh/material/draw sections/透明重なり/light/shadow/collider/driverを区画別に保存する。
- [ ] **5. Commit:** コードと採用runの必要成果物を明示stageし `test: verify full density exports and resource provenance`。独立runと旧生成物は保持し、まとめて削除・stageしない。

### Gate D — Task9承認後のcontrollerチェックポイント

- [ ] Live手順でfull候補を反映し、再apply、構造・駆動・文字・対象外保持を確認する。live mutationはcontroller限定。失敗時は診断までで止め、Task10へ成功証跡を渡さない。
- [ ] 中央→市場→東歩道→Yarol→検問→橋の目視・歩行確認を依頼し、街区全域のslum02対比の受入を記録する。新版の保存・再読込はユーザーに実施してもらい、その後にread-onlyで保持を確認する。できない項目はpending。既知監査失敗も残す。
- [ ] controllerが秘匿済みの実証跡と状態をTask10へ渡す。手動ゲートが未完でも事実を記録することはできるが、ワールド完全納品やSDD cleanupの条件は満たさない。

### 改訂 1 — Gate D の目視結果（2026-09-29）

Gate D で全域候補（`density-full-c-20260929T054230Z-541218-review-candidate-fix1.json`）を反映し、収束を確認した（ResoLoop の修正 #3/#4/#5 をロックに反映。詳細は SDD の `gate-d-report.md`）。ユーザーの目視結果は不合格で、指摘は「路面がノッペリ」「工場跡の床がノッペリ」「slum02 のような小さい瓦礫を中央床にも」。歩行は問題なし。保存と再読込は未確認。仕様の「改訂 1」に従い、Task 10 の前に次の Task 11〜13 と Gate D2 を行う。

### Task 11: 路面の作り込み

**Files:** Modify `modeling/slum03/ground.py`、`tests/slum03/test_ground.py`（必要なら `modeling/slum03/surface_detail.py` を新規作成）。slum02 の `slum02/modeling/slum02/ground.py`（ひび、補修パッチ、覆工板、縁石、側溝の格子、マンホール、水たまり、ごみ）を参照するが、slum02 のコードは変更しない。

- [ ] **1. RED:** full stage の街路・枝道に、ひび、補修パッチと覆工板、縁石（壊れた区間を含む）、側溝の格子、マンホール、水たまり、染みと汚れ、小さなごみが、評価後の形状として存在することを検査する。覆工板とパッチの段差は 0.01 m 未満。縁石と追加のコライダーは主導線の有効幅を横切らない。小さなごみは高さ 0.10 m 以下でコライダーを持たない。blockout と representative の地面は変えない（golden hash を維持する）。
- [ ] **2. 実装とGREEN:** Layout の街路の矩形と主導線から配置を決め、seed で再現できるようにする。1 オブジェクト 1 メッシュの規約に従い、区画ごとのまとまりにする。資源（三角形数、材質数）を記録する。
- [ ] **3. Commit:** `feat: add weathered street surface detail`

### Task 12: 工場跡の床と中央の小瓦礫

**Files:** Modify `modeling/slum03/plaza.py`、`modeling/slum03/gn_scatter.py`、`modeling/slum03/density_model.py`（中央床の小瓦礫の許可）、関係するテスト。slum02 の `slum02/modeling/slum02/plaza.py`（`_floor`、`_crack`、`_pit_depth`、`rubble_prototypes` の小さいもの、散布面）を参照する。

- [ ] **1. RED:** 工場跡の床に、ひび、浅い窪み、機械の基礎の跡、外周の湿った汚れがあることを検査する。中央 32×22 m に小瓦礫があり、そのすべてが高さ 0.10 m 以下でコライダーを持たないこと。中以上の瓦礫とコライダーが中央床と上方 3 m に 0 件であること。出入口と主導線の有効幅に小瓦礫が 0 件であること。これまでの「中央床の散布 0 件」の検査は、この新しい規則に置き換える。
- [ ] **2. 実装とGREEN:** 小瓦礫は既存の散布（`gn_scatter.py`）の仕組みを使い、seed で再現できるようにする。評価後の形状で規則を検査する。
- [ ] **3. Commit:** `feat: weather the factory floor and scatter walkable debris`

### Task 13: 改訂後の全域 export と候補（Task 9 の手順を再実行）

- [ ] Task 9 の手順（C/D の独立生成、decoded mesh の一致、verify_assets、density-report、scope-report で保護対象の変更 0、区画別の資源表、画像の確認）を新しい run 名で実行する。limits は候補自身の内容から計算する（Task 9 fix1）。既存の run と候補は上書きしない。
- [ ] Commit: `test: verify revised full density exports`

### Gate D2 — Task 13 承認後の controller チェックポイント

- [ ] Live 手順で改訂後の候補を反映し、再 apply が書き込み 0 になること、構造、対象外の保持、strict audit を確認する。
- [ ] 路面と工場跡の床について、目視、歩行、新版の保存と再読込をユーザーに依頼する。結果は controller の判断と分けて記録する。

### Task 10: 実証跡の反映と納品レポート回帰

**Files:** Create `tests/slum03/test_density_live_evidence.py`; Modify `content/slum03/slum03.json`, `artifacts/slum03/{delivery-report.json,live-verification.json,apply-log.md,timing.md}`（反映・実証後のみ）。生のlive報告は `.resoloop/slum03/` の新しいパス。

**Interfaces:** Task7の `summarize_density_delivery` と `validate_acceptance` を使用する。live命令は実行しない。controllerが渡した実証跡のhash・件数・状態を読むだけで、未確認項目の値を推測しない。

- [ ] **1. REDを定義:** controllerの秘匿済み証跡をfixtureとして、採用候補のhashとcanonicalが一致し、exportの実数・live数・レポートが対応することを検査する。現行wire形式の `live['reapply']['counts']` のslotsCreated/slotsUpdated/componentsAdded/componentsUpdated/slotsDeleted/componentsDeletedを合算して `assert writes == 0`、同じdictの `assert counts['assetsImported'] == 0` を実証に対して検査する。未知の場合はpassを要求しない。`ITEM_GRABBABLE_MISSING`が残るfixtureで `assert overall != 'pass'`。旧報告が新manifestの結果として残っていれば失敗する。
- [ ] **2. RED実行:** `uv run pytest tests/slum03/test_density_live_evidence.py -q`。記録の未更新による失敗を確認し、actual live失敗を期待値変更で隠さない。
- [ ] **3. 記録更新:** 反映成功した候補だけをcanonicalへコピーし、参照baseが同じこととhashを照合。対応する密度／構造／視覚／歩行／保存の結果を独立して更新する。旧証跡は履歴として保持する。報告コードの不具合が見つかったらsystematic-debuggingと別の限定fix/re-reviewを行い、文書更新に混ぜて迂回しない。
- [ ] **4. GREEN／最終検証:** 上記、full suite、`bash ../scripts/check-layout.sh`、`git diff --check`、生ID／URL／秘密情報の混入検査を実行。controllerも差分・件数・hash・未確認状態を独立確認する。
- [ ] **5. Commit／最終レビュー:** 実証跡・テストだけを明示stageして `docs: record density upgrade acceptance and remaining gates`。Task review後にbranch scope最終レビュー。未達ゲートがあればworkspaceと証跡を保持し、完全納品やcleanupを宣言しない。

## ControllerのLive手順（Gate B／D共通）

liveは実装計画承認と該当Taskのコード／候補レビュー後に限る。実装・レビュー子を止めた状態で、controllerが最新の同梱resonite-buildとmonitoring-long-tasksに従う。

1. 現在の接続先を `resoloop discover --json` で再探索。候補が複数なら選択を確認し、古いURL・IDを再利用しない。doctor/status/hierarchy/inspectで保存world・所有root・保持stateの再解決を確認。欠落・曖昧さをadoptや再importで隠さない。
2. `STATE=.resoloop/slum03/state/slum03.json`、`CANDIDATE=レビュー済み候補`、現在選択した `URL`、新しい `RUN` を設定。stateと対象外のsnapshotを記録する。未知のComponent/memberがあればReflectionで確認する。
3. `resoloop diff "$CANDIDATE" --state "$STATE" --brief --report ".resoloop/slum03/density-$RUN-diff.json" --url "$URL" --json`。完全レポートとscope-reportを照合し、全対象・理由を確認する。代表時の対象外更新、想定外削除／改名、global変更があれば停止する。
4. `resoloop apply "$CANDIDATE" --state "$STATE" --report ".resoloop/slum03/density-$RUN-apply.json" --url "$URL" --json`。失敗時は観測・診断までで止める。成功後に同じ入力・stateで再applyして書き込み/importゼロを確認する。
5. `resoloop test "$CANDIDATE" --state "$STATE" --url "$URL" --json`、対象のinspect／observeで構造・文字・動きを確認。対象外snapshotを比較する。source fileが同じでもliveの表示成功とはみなさない。
6. captureを使う場合はユーザーが用意したコンテナから読める写真exportフォルダを `--screenshots-dir` へ渡す。無断のmount設定変更をしない。timeoutなら記録してユーザー画像／目視を依頼する。
7. strict auditは既存で調べたexact4rolesと現在の参照先を再確認し、許可を広げず実行する。`ITEM_GRABBABLE_MISSING`だけが残ってもstrict passにしない。生URL／ID／stateはcommitしない。

## Controller checklist・自己点検

- [x] 計画のユーザーレビュー・承認を得る。2026-09-28の継続実行指示により承認済み。選択済みSDD方式を保持する。
- [x] Task1 → Task2をレビュー・統合し、Gate Aの配置を確認する。
- [x] Task3とTask4を担当分離し、レビュー後Task番号順に統合する。
- [ ] Task5 → Task6 → Task7を全Stepsレビュー・統合し、Gate Bでcontrollerが証拠と制限を確認する。
- [ ] 継続承認に従ってTask8 → Task9へ進み、Gate Dの結果をTask10へ渡す。人間確認がない項目はpendingのままにする。
- [ ] 最終レビューと未達ゲートを確認し、上流SDDの最終手順を実施可能か判断する。push／mergeは別途指示が必要。

計画自己点検: 仕様1〜4→Task1/2/6、仕様5→Task3/4/5/8、仕様6→Task1/5/6、仕様7→Task2/7/9/10、仕様8〜9→Task6/7/9/10へ対応する。Review Focusの5項目は各TaskのREDへ割り当てた。代表候補はfull密度のpassにはならず、Gate Bのcontroller検査なしにTask8は開始できない。共有palette・主導線・既存キーの変更を避ける順序になっている。

計画は承認済み。文書保存やテスト案の記述自体を、コードの実装・テスト成功・world改善として報告しない。
