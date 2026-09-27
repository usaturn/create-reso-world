# slum03 Cyberpunk Slum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 中央で遊べる120×120 mのスラム街と方向別の背景景観を、新規slum03プロジェクトから別の空Resoniteワールドへ生成・反映する。

**Architecture:** slum02の幾何・UV・出力の有用部分をslum03内へ移し、独立した固定シードのレイアウトから区画別のBlenderアセットとネイティブ宣言を作る。中央・建築・市場・AR・道路河川・森林・背景を分け、共通レイアウトと出力インターフェースだけを共有する。全体が一つの所有ルートと導線を共有するため計画は一本とし、成果物を独立に検証できる12タスクへ分割する。

**Tech Stack:** Python >=3.12（uv）、pytest、Blender 5.0.1（確認時の導入版）、Geometry Nodes、ResoLoop fork `0.1.0-preview.14.pr1.20260925`、ResoniteLinkと実機Reflection。

**Spec:** `docs/superpowers/specs/2026-09-27-slum03-cyberpunk-slum-design.md`（書面承認済み）。必ず計画と併読する。

**Status:** 計画承認済み。ユーザーはSubagent-driven（B）を選択し、中間承認なしの継続実行を指示した。必須のsubagent能力一覧呼出しがツールスキーマに拒否され、実装開始前に環境側の起動規約整合が必要。コード、テスト、雛形、生成物はまだ作成していない。

## Global Constraints

- 街区は東西120 m × 南北120 m。道路と背景は外側。Resoniteは東=+X、上=+Y、北=+Z、地表ローカルY=0。
- 工場跡地40×30 m、中央32×22 m（X=-16〜16、Z=-11〜11）と上方3 mを空ける。主導線と出入口は幅3 m以上。
- 北壁の基準: X=0、Z=14.5、幅36 m、厚さ0.8 m、高さ10 m。南向きに `稲垣は絶対マカぶる`。東壁に戻さない。
- 東側車道24 m（X=66〜90）、歩道各6 m（60〜66、90〜96）、森の前縁X>=100。川はZ=78〜112、橋はX=60〜96/Z=72〜118。
- Yarolは北東の道路沿い、外観のみ。橋・検問まで歩行可能。森・周辺都市の内部探索なし。
- 高層群80〜200 m級と最低3棟のアーコロジー500〜900 m級は北側。西・南は低中層の背景街区。
- 既定シードは `260927`。変更したシードは明示した別案とし、同じシード・入力は再現可能にする。
- 所有キー `slum03`、ルート名 `Slum03_Slum`、root slot key `root`、state `.resoloop/slum03/state/slum03.json`。
- slum02のファイル・state・ライブ内容、Rootの既存設定、既定床、空・全体照明、ResoLoop lockは変更しない。
- ライブ変更はresoloopだけ。現接続先と対象を確認し、diffレビュー→apply→同一宣言再applyで無変更。削除/pruneは自動実行しない。
- ローカルPythonはuv経由。Blender処理は `resoloop blender run`。編集可能なソースと出力コピーを分け、独立物ごとに1メッシュ。
- 指定9スキルに加え、新プロジェクトのresonite-build/resonite-blenderを読む。API・ノード・素材・駆動メンバーを推測しない。
- 大面積の透明層、高速点滅、全広告同期の明滅を避ける。ポリゴン数の丸い上限に合わせて品質を落とさない。
- Blenderプレビューを実機QAと呼ばない。キャプチャ、歩行、保存再読込を確認できなければ該当項目はpending。
- 時間の計測は各タスクの開始/終了と検証待ちを分けて `artifacts/slum03/timing.md` に残す。長時間待機はmonitoring-long-tasksに従う。

## Review Focus

- **RF-1 / Task 3, 11:** 散布点は外でも、回転・スケール・鉄筋の突出で瓦礫が中央や出入口へ侵入する入力。点だけでなく評価後の形状で拒否する。
- **RF-2 / Task 2, 3:** 非対称の面、複数UV、反転軸、日本語の不足グリフ。法線・UV0・追加UV・文字向きを保持し、失敗を省略で隠さない。
- **RF-3 / Task 10:** 別セクタで同じキーなのに違う資源/素材を持つ入力。衝突を解消し、完全一致だけ共有し、参照とサブメッシュ順を壊さない。
- **RF-4 / Task 8, 9, 12:** 実行時に回転中の広告を再applyする条件。固定配置と駆動スロットを分け、駆動中フィールドを宣言で巻き戻さない。
- **RF-5 / Task 6, 9, 12:** 空ワールドに既定床が残り、ローカル地表より低い川を覆う条件。所有ルート全体を持ち上げ、既定床は変更しない。

---

## 作業場所・参照・実行規約

- リポジトリは `usaturn/create-reso-world`。現ブランチは `feat/slum03-slum`。実装開始前にusing-git-worktreesで隔離を確保する。既存の未コミット変更があれば保全し、同時書き込みをしない。
- 以下はリポジトリルート基準のファイルパス。Task 1の雛形作成後、各Run/Commitは特記がなければ `slum03/` をcwdにする。ルートの配置検査は `bash ../scripts/check-layout.sh`。
- `uv run pytest <対象> -q` は記載したテストがPASSすることが合格。REDは新しい期待動作の不足でFAILすることを確認し、環境破損をREDとして扱わない。
- `--report NEW_FILE.json` とBlender export先は既存を上書きしない。実行ごとに `RUN=$(date -u +%Y%m%dT%H%M%S)-$$` を採番する。
- resoloopの `--brief` はグローバルオプション。接続先は実行時に確認したURLを `$URL` に設定し、ライブコマンドへ明示する。旧slum02のURL/IDを計画へ埋め込まない。
- 出力検査用の `--parent Root` はオフラインの記述値であり実機確認ではない。早期ブロックアウト確認またはTask 12の前に現ワールドのRootと所有範囲を確認するまで、エクスポートした宣言を適用しない。
- 各commit前にFiles欄の対象と明示した成果物だけを `git add -- <対象パス>` でstageし、`git diff --cached --check` と差分を確認する。無関係な変更・ローカルstateを含めない。
- 参考実装: `slum02/modeling/slum02/{geometry,uv,vcolor,blender_io,build,sectors,pipeline,postprocess}.py` と対応テスト。現在の `layout.py` は約977行で全方位遮蔽に密結合しているためコピーしない。
- ResoLoopはContext7で該当資料なし。導入版のCLI helpと同梱スキルを確認済み。Blender評価メッシュAPIはContext7の `/websites/blender_api_current` を参照したが、5.0.1のRNAで再確認する。

## ファイルと共通インターフェース

`modeling/slum03/` 以下で役割を分ける。細部を隣接タスクで勝手に改名しない。

| ファイル群 | 責務 |
| --- | --- |
| `types.py`, `config.py`, `layout.py`, `layout_district.py`, `layout_environment.py`, `layout_ads.py`, `spatial.py` | 純粋データ型、固定寸法、決定論配置、占有範囲・導線 |
| `geometry.py`, `uv.py`, `vcolor.py`, `materials.py`, `blender_io.py`, `sectors.py` | 再利用部品、座標/UV/色、素材、区画登録 |
| `ground.py`, `plaza.py`, `gn_scatter.py`, `graffiti.py` | 中央と地盤、散布、北壁の文字 |
| `ruins.py`, `shacks.py`, `overhead.py`, `stalls.py`, `nightlife.py`, `yarol.py` | 街区内建築と生活小物 |
| `road_river.py`, `forest.py`, `backdrop.py`, `sightlines.py` | 周辺環境と方向別の可視性 |
| `ads.py` | 広告の3系統と独立ピボット |
| `native/{__init__,common,materials,colliders,lighting,drivers,text}.py`, `postprocess.py` | Reflection確認後の素材・衝突・照明・駆動の宣言 |
| `pipeline.py`, `build.py`, `preview.py`, `verify_assets.py`, `delivery.py` | 統合、Blender生成、検証、納品結果 |

Task 1で次の型を定義する（すべてローカルResonite座標、JSON化は明示的に行う）。

- `RectXZ(x_min, x_max, z_min, z_max)`、`.bounds -> tuple[float,float,float,float]`、`.size -> tuple[float,float]`。
- `Bounds3(minimum: Vec3, maximum: Vec3)`。`Vec3 = tuple[float,float,float]`。
- `Placement(key: str, sector: str, kind: str, origin: Vec3, size: Vec3, yaw_deg: float, domain: str, params: dict)`。domainはdistrict/road/water/background。originは足元/設置面の中央、X/Zはsizeの半分ずつ広がる。ローカルY範囲は `params.get("local_y_min", 0.0)` からその値+size[1]まで。床/橋床版は負のlocal_y_minで上面Y=0を表し、中心点扱いして半分埋めない。正面は+Z、yawは上向きY軸回りの度数。Yarolはyaw=90で東を向く。
- `Viewpoint(key: str, eye: Vec3, target_group: str)`。主要視点はplaza-north=(0,1.6,-6)、east-forest=(63,1.6,0)、bridge-checkpoint=(63,1.6,50)、west-city=(-54,1.6,0)、south-market=(0,1.6,-52)、ar-hero=(0,1.6,-28)。それぞれnorth_arcologies/east_forest/checkpoint/west_city/south_city/adsをtarget_groupとする。
- `LabelSpec(key: str, text: str, parent_name: str, offset: Vec3, yaw_deg: float, height: float, color: tuple[float,float,float,float])`。parent_nameは固定されたBlenderオブジェクト/配置親の一意な名前。offset/yawはその親ローカル。graffiti以外の店名・AR主コピーに使う。
- `Layout(seed: int, district: RectXZ, plaza: RectXZ, clear: RectXZ, routes: tuple[RectXZ,...], placements: tuple[Placement,...], viewpoints: tuple[Viewpoint,...], labels: tuple[LabelSpec,...])`。`.select(kind: str) -> tuple[Placement,...]`。
- `Issue(code: str, object_key: str, message: str)`。`Report = dict[str, Any]`、`Manifest = dict[str, Any]`。

Task 2は旧geometryの `MeshData(name, vertices, faces, material)`、`Assembly(kind, name, sector, origin, parts, meta)`、`MergedMesh(name, vertices, faces, face_materials, materials)` を同じ意味で移植する。`Assembly.meta` の共通キーは `placement_key`、`uv_exempt`、`parent_name`、`motion`。parent_nameはBlender内の親の安定名。親なしのoriginはワールドローカル、親ありのoriginは親ローカルとし、変換を二重に加えない。motionは `None` または `{"kind":"spin"|"scan", "driven_name":str, "axis":Vec3, "rate":float}`。driven_nameはBlenderオブジェクト名であり、ネイティブ宣言ではslot_key_by_nameで解決する。単位はspinが度/秒、scanが模様の周期/秒。主文字はLabelSpecで固定親へ付け、motionを持たない。

SECTORSは `ground, plaza, ruins-west, ruins-north, ruins-east, market, shacks, nightlife, yarol, overhead, ads, road-river, forest, backdrop-north, backdrop-west-south`。各生成器は `build_assemblies(layout: Layout, sector: str) -> list[Assembly]` を公開し、registryの `sector_assemblies(layout, sector)` から呼ぶ。未登録・未知セクタはエラーにし、黙って空出力にしない。Blender追加処理は `register_blender_hook(sector: str)` デコレーターで登録し、呼出署名を `hook(bpy, layout, materials, source_collection, export_collection) -> tuple[list[Any],Report]` に固定する。plaza hookはadd_scatterとadd_graffitiを合成し、オブジェクトとIssueを欠落させず返す。

共通の `BuildReport` はReport形式で `sector: str, export_collection: str, objects: list[{key,kind,mesh}], evaluated_bounds: dict[key,{minimum:Vec3,maximum:Vec3}], materials: list[str], triangles: int, vertices: int, submeshes: int, uv_issues: list[Issue], errors: list[Issue]` を必須にする。JSONではIssueをcode/object_key/messageのobject、Vec3を3数値のarrayへ変換する。ファイル名は出力blendと同じディレクトリの `<sector>-report.json`。mesh/UV/法線が壊れた場合はerrorsを残して非ゼロ終了する。AO等の追加処理の失敗も記録し、見た目に影響する場合は次段階へ進めない。

### Task 1: 新規プロジェクトと検証可能なレイアウト

**Files:** Create `slum03/`（正規雛形）、`slum03/modeling/{__init__.py,slum03/__init__.py}`、上表の型/配置7ファイル、`slum03/tests/slum03/{test_scaffold,test_layout,test_spatial}.py`。Modify 新規`slum03/AGENTS.md`のみ。
**Interfaces:** Produces `build_layout(seed: int = 260927) -> Layout`, `validate_layout(layout: Layout) -> list[Issue]`, `write_layout(layout: Layout, path: Path) -> None`, `read_layout(path: Path) -> Layout`。`spatial.placement_bounds(p: Placement) -> Bounds3`, `validate_clearance(layout: Layout, bounds: Mapping[str,Bounds3]) -> list[Issue]`。

- [ ] Step 1: 隔離先ルートで `bash scripts/new-world.sh slum03`。生成されたAGENTS.mdを読み、所有キー/ルート/stateを追記。`cd slum03 && resoloop skills sync --check`。初期化途中失敗なら再initせず残存状態を確認する。
- [ ] Step 2: scaffoldの存在と旧namespaceの不在、および次のREDテストを書く。
```python
def test_layout_dimensions_and_repeatability():
    a = build_layout()
    assert a == build_layout(260927)
    assert a.district.size == (120.0, 120.0)
    assert a.plaza.size == (40.0, 30.0)
    assert a.clear.bounds == (-16.0, 16.0, -11.0, 11.0)
    assert validate_layout(a) == []
```
  JSON往復一致、別プロセスで2回生成したJSONの一致、別シード7/91でも寸法・出入口不変、道路/背景を街区寸法へ混入しない、非有限値/負寸法を拒否するテストも追加する。以降の例は各Testファイルの最小assertionであり、同じStepに列挙した追加条件も個別テストにする。
- [ ] Step 3: `uv run pytest tests/slum03/test_scaffold.py tests/slum03/test_layout.py tests/slum03/test_spatial.py -q` でREDを確認。
- [ ] Step 4: 型と固定値、用途付きPlacement、主導線、視点を実装。north-wall、yarol、bridge、checkpoint、forest、3 arcology、west-city、south-cityの安定キーを定義する。道路の歩行領域はZ=-100〜130とし、北端は橋詰の折り返しと境界を持たせる。工場の東壁Placementは作らない。入口・動線と回転後の占有範囲を検査する。
- [ ] Step 5: 同じテストをGREENにし、`uv run python -m modeling.slum03.layout --output content/slum03/layout.json` で生成/再読込一致を確認。
- [ ] Step 6: `git add AGENTS.md pyproject.toml uv.lock .resoloop/.gitignore .resoloop.json modeling tests content/main.json content/slum03/layout.json flux .agents .claude .pi CLAUDE.md` の候補をstatusで確認し、ローカルstate/cacheを含めず `git commit -m "feat: scaffold slum03 with validated deterministic layout"`。

### Task 2: 幾何・UV・素材とBlenderへの最小往復

**Files:** Create 上表の幾何/UV/色/素材/Blender橋渡し/区画登録6ファイル、`slum03/modeling/slum03/{probe_blender,probe_manifest,build}.py`、`slum03/tests/slum03/{test_geometry,test_uv,test_materials,test_blender_io,test_probe_manifest}.py`。
**Interfaces:** Produces `merge_assembly(assembly: Assembly) -> MergedMesh`、`create_object(bpy, bmesh, merged: MergedMesh, origin: Vec3, material_lookup: dict, *, uv_exempt: bool=False) -> tuple[Any,list[Issue]]`、`write_colors(obj, colors, name="Col") -> None`、`make_blender_materials() -> dict[str,Any]`、registryの共通署名。`write_scene(sector: str, output: Path) -> Report` の基礎をここで作り、登録済み区画を個別に生成できるようにする。`prepare_probe_manifest(source: Path, output: Path, root_position: Vec3) -> Manifest` はsource bundleをslum03所有ルート配下の `blockout-preview` に包み、assetパスをoutput基準へ付け替える。元bundle rootの明示parentは除き、旧rootへのslot参照を一時子keyへ再配線して所有ルートの外へ出さない。

- [ ] Step 1: 旧test_geometry/test_vcolorから意味のある幾何検査を移植。RF-2として非対称三角形の法線、XZY変換、逆巻き、render-active UVを第2レイヤーにした2チャンネル、色属性を持つfixtureを用意する。`test_uv_degenerate_face_rejected` と `test_material_order_matches_submeshes` も書く。probe manifestは所有キーslum03/root名Slum03_Slum/一時子名ResoLoop_Test_Slum03_Blockout、他のrootへの変更なし、相対asset参照の維持を検査する。
```python
def test_axis_swap_is_not_a_second_scale():
    assert resonite_to_blender((1.0, 2.0, 3.0)) == (1.0, 3.0, 2.0)
```
  `blender_io.resonite_to_blender(p: Vec3) -> Vec3` は旧helperと同じ署名で移植する。実際の法線/UVは非対称fixtureのexportで併せて確認。
- [ ] Step 2: `uv run pytest tests/slum03/test_geometry.py tests/slum03/test_uv.py tests/slum03/test_materials.py tests/slum03/test_blender_io.py tests/slum03/test_probe_manifest.py -q` のREDを確認。
- [ ] Step 3: 必要な幾何・UV/色の処理だけ移植し、Slum02名・importを除去。Blender依存は関数内importに隔離。バージョン・RNA・実体化に必要なノード/ソケットを `probe_blender.py` で実測し、GNの名前を推測しない。builderは登録済み生成器とBlender hookを受け取り、未実装の別区画はその区画を要求した時だけ失敗させる。probeの `--mode blockout` は全Placementの簡略形と登録済み区画の実メッシュを専用collectionへ組み合わせる。
- [ ] Step 4: 単体テストGREEN後、`resoloop blender run modeling/slum03/probe_blender.py --arg=--output --arg=artifacts/slum03/probes --json`。非対称fixtureを専用Export collectionに保存・再読込し、実測結果と `.blend` を出す。
- [ ] Step 5: fixtureを新規bundleへ `resoloop blender export artifacts/slum03/probes/fixture.blend --output content/slum03/probes/fixture-$RUN --parent Root --name Slum03_Probe --collection Slum03ProbeExport --preserve-hierarchy --json`。mesh.jsonのUV順、追加UV、色、法線を照合し、実機適用はしない。
- [ ] Step 6: `uv run pytest tests/slum03/test_probe_manifest.py -q` もRED→GREENを確認。対象ソース/テストとprobeの検証記録だけを選んで `git commit -m "feat: add slum03 mesh UV and Blender bridge"`。追加UVを旧helperのUV0作成で上書きしない。

### Task 3: 中央跡地・北壁・スプレーアート・安全な瓦礫

**Files:** Create `slum03/modeling/slum03/{ground,plaza,gn_scatter,graffiti}.py`、`slum03/assets/fonts/{DelaGothicOne-Regular.ttf,OFL.txt}`（slum02からライセンス付きで再利用）、`slum03/tests/slum03/{test_ground,test_plaza,test_scatter,test_graffiti}.py`。Modify registry。
**Interfaces:** Uses Task 1/2。Produces ground/plazaの `build_assemblies`。`scatter_samples(layout: Layout, *, seed: int, count: int, max_extent: Vec3) -> tuple[Vec3,...]`、Blender内 `add_scatter(bpy, layout, materials, source_collection, export_collection) -> tuple[list[Any],Report]`、`add_graffiti(bpy, layout, materials, export_collection) -> tuple[list[Any],Report]`。

- [ ] Step 1: 中央床、北壁、正確な文字列、南向き法線、旧東壁なしのテストを書く。RF-1で点は外だが回転した鉄筋付き瓦礫が中央に入るboundsを与え、`validate_clearance` が `CLEARANCE_INTRUSION` を返すことを確認。count=0/複数seedと出入口の除外もテストする。
```python
def test_protruding_rubble_is_rejected():
    base = build_layout()
    p = Placement("rubble-probe", "plaza", "rubble", (16.5, 0.0, 0.0), (2.0, 1.0, 2.0), 45.0, "district", {})
    layout = dataclasses.replace(base, placements=base.placements + (p,))
    issues = validate_clearance(layout, {p.key: Bounds3((15.5, 0.0, -1.0), (17.5, 1.0, 1.0))})
    assert any(i.code == "CLEARANCE_INTRUSION" for i in issues)
```
- [ ] Step 2: `uv run pytest tests/slum03/test_ground.py tests/slum03/test_plaza.py tests/slum03/test_scatter.py tests/slum03/test_graffiti.py -q` のREDを確認。
- [ ] Step 3: 工場床と北壁を実装し、散布の最大形状半径で禁止領域を拡張する。GNで元部品の選択・インスタンス・変種を保持し、出力コピーだけ実体化。瓦礫は編集可能な小さな山単位へ分ける。壁・文字は独立メッシュ。
- [ ] Step 4: 文字全グリフの存在をBlender fontで確認し、不足グリフは明示エラーにする。赤塗り・黒縁・垂れを非発光で生成し、UV/法線/文字向きと中央上方3 mの無障害を検査。
- [ ] Step 5: 上記テストをGREENにし、Task 11で評価メッシュboundsを再検査するためのReportを出力。`git commit -m "feat: build clear factory plaza north graffiti wall and rubble"`。

### Task 4: 廃ビル・小屋・頭上の構造

**Files:** Create `slum03/modeling/slum03/{ruins,shacks,overhead}.py`、`slum03/tests/slum03/{test_ruins,test_shacks,test_overhead}.py`。Modify registry。
**Interfaces:** 各モジュールの `build_assemblies(layout, sector)`。ルート配置はPlacement.origin、部品はローカル座標。`Assembly.meta.placement_key` を必ず設定する。

- [ ] Step 1: `test_ruin_has_recessed_openings_and_broken_slab` で窓開口が単なる塗り面でなく奥行きを持つこと、`test_each_building_has_independent_assembly`、`test_overhead_avoids_activity_volume`、`test_cable_endpoints_have_supports` を書く。
```python
def test_each_building_has_independent_assembly():
    objects = build_assemblies(build_layout(), "ruins-west")
    assert len(objects) > 1
    assert len({a.name for a in objects}) == len(objects)
    assert all(a.meta["placement_key"] and a.parts for a in objects)
```
- [ ] Step 2: `uv run pytest tests/slum03/test_ruins.py tests/slum03/test_shacks.py tests/slum03/test_overhead.py -q` のREDを確認。
- [ ] Step 3: 旧towers/shacks/overheadの有用形状を局所移植し、深い窓・厚いスラブ・崩落断面・増築の構造を作る。東側は低めで、東向きの通路と森林への視線を残す。配線端点は壁面/柱に接続させる。
- [ ] Step 4: 同テストGREEN。seed変更でも通路侵入なし、パレット未定義素材なし、全建物を一つに結合していないことを確認。`git commit -m "feat: add modular ruins shacks and supported overhead details"`。
- [ ] Step 5: 小物を密に配置する前に、下記「早期実機ブロックアウト確認」をcontrollerが行い、配置図・主要建築との比較結果を記録する。

#### 早期実機ブロックアウト確認（Task 4後、controllerのみ）

- [ ] 別の空ワールドをTask 12 Step 3と同じdoctor/status/hierarchyで確認。既定床上面に対して `max(0, floor_top - (-4.0) + 0.5)` をroot-yの初期値とする。既定床がなければ0。これを宣言へ保存し、Task 9の検査で照合する。
- [ ] `resoloop blender run modeling/slum03/probe_blender.py --arg=--mode --arg=blockout --arg=--output --arg=artifacts/slum03/probes --json`。実装済み中央/建物と、道路・森・背景の簡略形を同じスケールで出す。
- [ ] `resoloop blender export artifacts/slum03/probes/blockout.blend --output content/slum03/probes/blockout-$RUN --parent Root --name Slum03_Blockout --collection Slum03ProbeExport --preserve-hierarchy --json`。`uv run python -m modeling.slum03.probe_manifest --source content/slum03/probes/blockout-$RUN/model.apply.json --output content/slum03/blockout.json --root-y "$Y"` で包む。Yは上で確認した値。
- [ ] root key/name/ownership/stateは本体と同じ。Task 12 Step 4/6のvalidate/diff/apply/再applyをこのblockout.jsonへ実行し、所有配下の `ResoLoop_Test_Slum03_Blockout` だけを追加する。未承認の生成子やRoot設定変更があれば適用しない。
- [ ] 中央の余白・北壁・森・巨大都市の見かけの大きさを実機で配置図と比較する。キャプチャ到達不可ならユーザーの目視を依頼し、未確認のまま小物を詰め込まない。接続不可なら未完了として、オフライン制作を続けるかユーザーに確認する。
- [ ] 確認後は所有rootだけを残す `content/slum03/blockout-retire.json` を作る。現在のpreview subtree IDをinspectし、`diff --deletes-only` の全候補がその検証済み一時subtree内であることを確認してから、controllerがこの退役宣言にだけ `apply --prune --yes` を実行する。rootとstateは保ち、通常の生成/適用スクリプトに自動pruneを追加しない。

### Task 5: 屋台・ネオン横丁・Yarolの外観

**Files:** Create `slum03/modeling/slum03/{stalls,nightlife,yarol}.py`、`slum03/tests/slum03/{test_stalls,test_nightlife,test_yarol}.py`。Modify registry。
**Interfaces:** 各モジュールの `build_assemblies(layout, sector)`。商品・看板・入口の必要寸法はPlacement.paramsから取得する。

- [ ] Step 1: `test_market_lane_remains_three_metres_clear`、`test_stall_has_frame_shelves_and_distinct_junk`、`test_yarol_is_northeast_and_east_facing`、`test_yarol_has_no_enterable_interior` を書く。ネオン横丁の店名/外観と路地への張り出しを検査する。
```python
def test_yarol_is_northeast_and_east_facing():
    layout = build_layout()
    bar, = layout.select("yarol")
    assert 43.0 <= bar.origin[0] <= 59.0
    assert 40.0 <= bar.origin[2] <= 54.0
    assert bar.yaw_deg == 90.0
    assert any(s.text == "Yarol" for s in layout.labels)
```
- [ ] Step 2: `uv run pytest tests/slum03/test_stalls.py tests/slum03/test_nightlife.py tests/slum03/test_yarol.py -q` のREDを確認。
- [ ] Step 3: 屋台のパイプ・天幕・棚・基板/工具/義肢/部品箱、風俗店のシャッター・看板、Yarolの店名と暖色入口・窓越しの浅い造形を実装。各店/屋台を独立Assemblyにし、通路へ商品を散布しない。
- [ ] Step 4: 同テストGREEN。露骨な性的図像やNPC/取引/入店機能が増えていないことをレビュー。`git commit -m "feat: add junk market nightlife facades and Yarol frontage"`。

### Task 6: 東側道路・川・橋・検問

**Files:** Create `slum03/modeling/slum03/road_river.py`、`slum03/tests/slum03/test_road_river.py`。Modify registry。
**Interfaces:** `build_assemblies(layout, "road-river")`。路面/橋の上面Y=0、川の水面Y=-4.0をこの区画の既定値とし、最低可視面YをReportへ含める。

- [ ] Step 1: 幅と位置のテストを書く。`test_bridge_walkway_connects_both_banks` は歩道と橋の接続、`test_checkpoint_has_three_metre_opening` は装飾フレームを除いた開口、`test_railings_keep_avatar_out_of_water` は欄干/端部を対象にする。
```python
def test_bridge_matches_road_and_bank_span():
    bridge, = build_layout().select("bridge")
    assert bridge.size[0] == 36.0
    assert bridge.origin[2] - bridge.size[2] / 2 == 72.0
    assert bridge.origin[2] + bridge.size[2] / 2 == 118.0
```
- [ ] Step 2: `uv run pytest tests/slum03/test_road_river.py -q` のREDを確認。
- [ ] Step 3: 車道24 m＋歩道各6 m、護岸、水面、橋の支持構造と欄干、検問の屋根/機器/開口を生成する。川は背景に続く長さとし、道路南端/橋北端の歩行範囲もレイアウトへ明示する。
- [ ] Step 4: 同テストGREEN。RF-5向けに最低可視面Y=-4.0の証跡を残す。既定床の削除・地形編集を行わない。`git commit -m "feat: add eastern road river bridge and passable checkpoint"`。

### Task 7: 森と方向別の背景都市

**Files:** Create `slum03/modeling/slum03/{forest,backdrop,sightlines}.py`、`slum03/tests/slum03/{test_forest,test_backdrop,test_sightlines}.py`。Modify registryとGN共有処理。
**Interfaces:** forest/backdropの `build_assemblies(layout, sector)`、`sightline_report(layout: Layout, bounds_by_key: Mapping[str,Bounds3]) -> dict[str,bool]`。結果キーは `north_arcologies, east_forest, west_city, south_city`。

- [ ] Step 1: 森は道路東側・非歩行、北に80〜200 m高層群と3種類/3棟以上の500〜900 mアーコロジー、西南の低中層背景の存在をテスト。`test_north_wall_does_not_hide_all_arcologies` と `test_east_route_sees_forest` を追加する。
```python
def test_multiple_arcologies_are_north_of_river():
    towers = build_layout().select("arcology")
    assert len(towers) >= 3
    assert all(p.origin[2] - p.size[2] / 2 > 112.0 for p in towers)
    assert all(500.0 <= p.size[1] <= 900.0 for p in towers)
```
- [ ] Step 2: `uv run pytest tests/slum03/test_forest.py tests/slum03/test_backdrop.py tests/slum03/test_sightlines.py -q` のREDを確認。
- [ ] Step 3: 近景の独立樹木と奥の樹冠パッチ、GNによる変種、段状巨壁/門型/連結塔、低中層の西南街区を作る。背景に不要な内部・小物・全樹木のコライダーを生成しない。
- [ ] Step 4: 指定視点からの見かけの大きさを調整。中央の少なくとも1視点で2棟以上のアーコロジーが読み取れ、東向き路地と歩道で森林が見えることをproxy boundsでテストする。西南に背景の切れ目を作るケースはFAILさせる。
- [ ] Step 5: 同テストGREEN。実メッシュの可視性確認はTask 11/12にも残す。`git commit -m "feat: add forest and directional city backgrounds"`。

### Task 8: 立体ARと固定/駆動階層

**Files:** Create `slum03/modeling/slum03/ads.py`、`slum03/tests/slum03/test_ads.py`。Modify registry、materials、必要なgeometry部品。
**Interfaces:** `build_assemblies(layout, "ads")`。広告キーごとに固定placement、独立driven、固定labelを区別するmetaを出力する。動く部品は独立メッシュ/原点を持つ。

- [ ] Step 1: `test_three_hologram_families_have_depth` は立体商品/層状広告/曲面帯が単一平面でないことを検査。`test_primary_copy_is_not_driven`、`test_motion_envelope_avoids_routes`、`test_projector_has_physical_mount` を書く。
```python
def test_primary_copy_is_not_driven():
    layout = build_layout()
    objects = build_assemblies(layout, "ads")
    moving_names = {a.name for a in objects if a.meta.get("motion")}
    assert moving_names
    assert all(label.parent_name not in moving_names for label in layout.labels)
```
- [ ] Step 2: `uv run pytest tests/slum03/test_ads.py -q` のREDを確認。
- [ ] Step 3: 商品、分割リング、離れた情報層、曲面帯、投影装置を作る。固定placementは安定名のEmpty親、回転部は独立した子メッシュとし、placement transformを一度だけ適用する。主コピーはLayout.labelsの固定親を参照し、Task 9のnative TextRendererで生成する。大きな透明四角形の積層で代替せず、発光輪郭と形状を主体にする。
- [ ] Step 4: RF-4としてplacementとdrivenが別キーであること、主文字がdrivenの子にならないことをGREENにする。`--preserve-hierarchy` でピボットが保持される設計を確認。`git commit -m "feat: create volumetric layered and ribbon AR ads"`。

### Task 9: Reflection確認とネイティブ素材・衝突・照明・駆動

**Files:** Create `slum03/modeling/slum03/native/{__init__,common,materials,colliders,lighting,drivers,text}.py`、`slum03/modeling/slum03/postprocess.py`、`slum03/tests/slum03/{test_native_materials,test_colliders,test_lighting,test_drivers,test_signs,test_root_anchor}.py`。Reflection記録は`.resoloop/slum03/reflection/`。
**Interfaces:** `postprocess.py` に `postprocess(manifest: Manifest, layout: Layout, reports: Mapping[str,Report], root_position: Vec3) -> Manifest` と `choose_root_y(existing_floor_top: float | None, lowest_visible_local_y: float, margin: float = 0.5) -> float`。`native/common.py` の `slot_key_by_name(manifest: Manifest, name: str) -> str` は一致が一つでなければ失敗する。native各モジュールはpostprocess内部の独立処理で、LabelSpec.parent_nameと駆動対象名をこの関数で実際のkeyへ解決する。

- [ ] Step 1: 選択した別の空ワールドへ読み取り専用で接続する。`resoloop discover --json` → 候補確認 → `resoloop doctor --url "$URL" --json`。`resoloop type describe <型> --url "$URL" --json` で素材・Light・BoxCollider・Spinner・TextRenderer等と必要メンバー/enumを確認する。接続できなければ純粋処理までに留め、未知の型を創作しない。
- [ ] Step 2: 確認済み型に対する生成テストと、次のRF-4/RF-5テストを書く。
```python
def test_anchor_clears_existing_floor_without_editing_it():
    assert choose_root_y(0.0, -4.0) == 4.5
    assert choose_root_y(None, -4.0) == 0.0

def test_live_rotation_is_not_managed_by_reapply():
    m, layout = native_ad_fixture()  # 同一ad-probeを含む最小宣言と対応するLayout
    out = postprocess(m, layout, {}, (0.0, 0.0, 0.0))
    assert "rotation" not in driven_slot(out)["slot"]
    assert driver_target(out) == "$slot-member:ad-probe-driven.Rotation"
```
  fixture/lookup関数はテスト内で定義する。driver_targetはReflectionで確認した実際の対象メンバーから取り出す。床だけがclear volumeに接すること、背景コライダーなし、全宣言が所有配下であること、root-y入力の非有限値と負marginを拒否することも検査。test_signsはYarol文字列、日本語主コピー、固定親ローカル座標、親名の曖昧/欠落時の失敗を確認する。
- [ ] Step 3: `uv run pytest tests/slum03/test_native_materials.py tests/slum03/test_colliders.py tests/slum03/test_lighting.py tests/slum03/test_drivers.py tests/slum03/test_signs.py tests/slum03/test_root_anchor.py -q` のREDを確認。
- [ ] Step 4: 頂点色を使う素材、ホロ用素材、限定したローカル光源、床/欄干/建物/検問の単純コライダー、確認済みnative driver、LabelSpecからのTextRendererを宣言へ追加。旧sign_slotsの考え方は再利用できるが旧spray fallbackを持ち込まない。Slotの駆動先にComponent用 `$member:` を使わず、確認済み `$slot-member:` を使う。
- [ ] Step 5: 同テストGREEN。同じpostprocessを2回行っても重複component/slotなし、root_positionは所有ルートだけに作用することを確認。`git commit -m "feat: add owned native materials colliders lights and AR drivers"`。

### Task 10: バンドル統合と移植境界の検証

**Files:** Create `slum03/modeling/slum03/pipeline.py`、`slum03/tests/slum03/{test_pipeline,test_ownership}.py`。
**Interfaces:** `merge_bundles(bundle_dir: Path) -> Manifest`、`build_unified_manifest(bundle_dir: Path, layout: Layout, reports: Mapping[str,Report], root_position: Vec3) -> Manifest`、`write_unified_manifest(manifest: Manifest, output: Path) -> None`。bundle_dir直下のディレクトリ名はSECTORSと一致。mergeのasset.sourceはbundle_dir基準の相対パス。build_unified_manifestでbundle_dirから絶対パスへ解決し、write_unified_manifestは入力を変更せずoutput.parent基準の相対パスへ戻して保存する。これにより深いbundles/REV配下でも参照を壊さない。

- [ ] Step 1: 旧test_pipelineのsynthetic bundleをtmp_pathで再利用しRF-3を固定。違う内容の同名asset/materialは別キー、完全一致は共有、 `$asset/$component/$slot/$slot-member` 参照をすべて再配線、material順を維持することをassertする。
```python
def test_conflicting_asset_names_are_rewritten(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SECTORS", ("ground", "plaza"))
    _bundle(tmp_path / "ground", "Ground")
    _bundle(tmp_path / "plaza", "Plaza")
    m = pipeline.merge_bundles(tmp_path)
    assert m["assets"]["mesh_a"]["source"] == "ground/mesh_a.mesh.json"
    assert m["assets"]["plaza-mesh_a"]["source"] == "plaza/mesh_a.mesh.json"
```
  `_bundle` は旧test_pipeline.pyの同名テストhelperを移植し、衝突する異なるmesh内容もtmp_pathへ書く。完全一致を共有するケースは別テストにする。`test_nested_bundle_paths_survive_final_write` で最終宣言のsourceが `bundles/rev/ground/mesh_a.mesh.json` になることと実ファイルに解決することをassertする。
- [ ] Step 2: `test_missing_sector_fails_closed`、`test_material_provider_has_unique_slot`、`test_foreign_ownership_references_rejected`、`test_same_manifest_is_deterministic` も書き、`uv run pytest tests/slum03/test_pipeline.py tests/slum03/test_ownership.py -q` のREDを確認。
- [ ] Step 3: 旧mergeの必要部分を移植し、root ownership/name/state依存をslum03へ限定。出力宣言から見た相対assetパスを正しく付け替え、expandedNodes等の量は最終宣言から再計算。providerは独立した安定名のスロットに置く。
- [ ] Step 4: 同テストGREEN。`uv run python -m modeling.slum03.pipeline --bundles content/slum03/bundles/<REV> --layout content/slum03/layout.json --root-y <Y> --output content/slum03/slum03.json` のCLIを定義し、tmp_path fixtureで入出力を試験する。REV/Yは実際の検証済み出力・設置高さを与える。
- [ ] Step 5: `git commit -m "feat: merge slum03 bundles with stable ownership and references"`。

### Task 11: 区画ビルド・実体化・出力・プレビュー改善

**Files:** Modify `slum03/modeling/slum03/build.py`。Create `slum03/modeling/slum03/{preview,verify_assets}.py`、`slum03/tests/slum03/{helpers,test_build,test_asset_verification}.py`。Generate `slum03/artifacts/slum03/`、`slum03/content/slum03/bundles/`。
**Interfaces:** `write_scene(sector: str, output: Path) -> Report`、`verify_assets(layout: Layout, reports: Mapping[str,Report]) -> list[Issue]`、`compare_geometry_exports(first: Path, second: Path) -> list[Issue]`、`preview(output_dir: Path, *, sector: str | None = None) -> Report`。

- [ ] Step 1: 生成Reportを使い、壊れたUV/欠落材/不足セクタ/RF-1の評価後侵入を拒否するREDテストを書く。exportコピーだけが出力collectionにあり、GN source/graphが編集元へ残ることもBlender probeで検査する。
```python
def test_build_error_blocks_asset_verification():
    layout = build_layout()
    reports = minimal_reports(layout)
    reports["plaza"]["errors"] = [{"code": "UV_MISSING", "object_key": "north-wall", "message": "missing UV0"}]
    assert any(i.code == "BUILD_ERROR" for i in verify_assets(layout, reports))
```
  `tests/slum03/helpers.py` に `minimal_reports(layout)` を定義し、全SECTORSの合成Reportを同じスキーマで返す。実生成の証拠としては使わない。
- [ ] Step 2: `uv run pytest tests/slum03/test_build.py tests/slum03/test_asset_verification.py -q` のREDを確認。
- [ ] Step 3: Task 2のbuilderへ全区画のhookと評価後検査を統合。fresh Blenderシーンだけを初期化する。先にground/plaza、次に建物・屋台、道路・背景、最後にARの順でbuild。`resoloop blender run modeling/slum03/build.py --arg=--sector --arg=plaza --arg=--output --arg=artifacts/slum03/plaza.blend --json` を各区画へ展開する。
- [ ] Step 4: 既存の生成ソースblendを変更する前に `.resoloop/slum03/backups/$RUN/` へ保全。編集元と実体化した出力を分け、`.blend`保存・再読込後にUV、色、GN graph、独立メッシュを再確認。評価メッシュ取得はdepsgraphと全データ層を指定し、使用後にtemporary meshを解放する。
- [ ] Step 5: `resoloop blender export artifacts/slum03/plaza.blend --output content/slum03/bundles/$RUN/plaza --parent Root --name Slum03_Plaza --collection Slum03PlazaExport --preserve-hierarchy --json` を各区画へ展開。collection名はbuild Reportのexport_collectionを使う。不完全な出力は統合しない。
- [ ] Step 6: `resoloop blender run modeling/slum03/preview.py --arg=--output --arg=artifacts/slum03/previews --json`。512〜768 px程度の反復用プレビューで近/中/遠を見て修正。全景視点はplaza-north、east-forest、bridge-checkpoint、west-city、south-market、ar-hero。実メッシュでも北の複数アーコロジーと東の森林を確認する。
- [ ] Step 7: `uv run python -m modeling.slum03.verify_assets --reports artifacts/slum03 --layout content/slum03/layout.json` と全 `uv run pytest -q` をGREEN。再生成した別bundleのmesh/UV/tangent/colorの内容hashを比較し、パス/時刻以外の差を丸めて隠さない。
- [ ] Step 8: 全体/区画のtriangles、expanded vertices、materials、draw sections、textures、lights、colliders、透明層を記録し、無意味なコストのみ整理。`git commit -m "feat: build and verify slum03 sector assets and previews"`。

### Task 12: 安全なライブ反映・収束・実機QA・納品

**Files:** Create `slum03/modeling/slum03/delivery.py`、`slum03/tests/slum03/test_delivery.py`。Generate `content/slum03/slum03.json`、`artifacts/slum03/{delivery-report.json,timing.md,apply-log.md}`。セッション情報は`.resoloop/slum03/`のみ。
**Interfaces:** `summarize_delivery(layout: Layout, build_reports: Mapping[str,Report], live_results: Mapping[str,Any]) -> Report`。live_resultsはapply/reapply/structure/visual/walk/portability/resourcesの各キーに `{status:"pass"|"fail"|"pending", evidence:list[str], details:dict}` を持つ。必須キー欠落、未実施、passなのに根拠なしの項目はpendingとし、全体完了へ繰り上げない。根拠は実際のCLI全文report・画像・ユーザー確認記録へのパス/識別子を使う。

- [ ] Step 1: `test_missing_live_visual_check_remains_pending`、`test_import_success_is_not_visual_success`、`test_portability_warning_is_not_pass`、`test_elapsed_and_task_times_are_distinct` を書き、`uv run pytest tests/slum03/test_delivery.py -q` でREDを確認。
```python
def test_import_success_is_not_visual_success():
    r = summarize_delivery(build_layout(), {}, {"apply": {"status": "pass", "evidence": ["apply-report.json"], "details": {}}})
    assert r["status"] == "pending"
    assert r["checks"]["visual"]["status"] == "pending"
```
  出力Reportは `status` と入力各項目を正規化した `checks` を持ち、一つでもfailならfail、failがなく未確認があればpending、全必須項目と資源/ビルド検査がpassの場合だけpassとする。
- [ ] Step 2: summarizerを実装し同テストGREEN。宣言に上記6視点のcamera bookmarkと構造assertionを登録。カメラの世界座標は所有ルートの設置高さを反映する。
- [ ] Step 3: controllerが現接続先を再確認する。`resoloop doctor --url "$URL" --json`、`resoloop status --url "$URL" --json`、`resoloop hierarchy --under Root --depth 2 --include-components --url "$URL" --json`。別の空ワールドか確認し、既定床上面と最低可視面からroot-yを固定して統合宣言を生成する。既存slum02や所有権不明のrootがあれば停止する。
- [ ] Step 4: 次を順に実行し、strict validationとdiffの対象/理由をレビューする。REPORTは毎回未使用名。
```bash
STATE=.resoloop/slum03/state/slum03.json
MANIFEST=content/slum03/slum03.json
RUN=$(date -u +%Y%m%dT%H%M%S)-$$
resoloop validate "$MANIFEST" --strict --url "$URL" --json
resoloop diff "$MANIFEST" --state "$STATE" --brief --report ".resoloop/slum03/diff-$RUN.json" --url "$URL" --json
resoloop apply "$MANIFEST" --state "$STATE" --report ".resoloop/slum03/apply-$RUN.json" --url "$URL" --json
```
  apply失敗はcheckpointを保存し、観測と再diffまで止める。Rootの設定変更、adopt、prune、削除を付け足さない。
- [ ] Step 5: 生成rootと参照をinspect。ARの駆動先を確認し、時間差のある2回の `resoloop inspect '$slot:<driven-key>' --state "$STATE" --url "$URL" --json` で値の変化と固定文字を確認。driven-keyはmanifestに実在するkeyを使う。
- [ ] Step 6: 同じmanifest/stateを変更せず、別report名でapplyを再実行。書き込み/再importがゼロであることを全文reportで確認する。RF-4の回転が止まる・巻き戻る場合は宣言の管理フィールドを修正し、再検証。
- [ ] Step 7: `resoloop test "$MANIFEST" --state "$STATE" --url "$URL" --json`、`resoloop item audit '$slot:root' --state "$STATE" --strict --url "$URL" --json`。外部参照候補を見て必要な正確な型/メンバーだけ許可し、未使用の許可や広い_shader許可で回避しない。
- [ ] Step 8: `resoloop capture "$MANIFEST" --camera plaza-north --output "artifacts/slum03/live-plaza-north-$RUN.jpg" --width 768 --height 512 --url "$URL"` 等で実機確認。ホスト保存先へ到達できなければエラーを記録し、ユーザーの実機目視/歩行確認を依頼。中央→市場→東歩道→Yarol前→検問→橋を確認する。実機QA未実施ならpendingのまま納品報告する。
- [ ] Step 9: ユーザーの許可・協力のもと保存/再読込後の資源保持を確認する。実施できなければportabilityをpending。セッションFPSを個別モデルの性能証明にせず、構造的資源量と実測できた事実だけを記録する。
- [ ] Step 10: `uv run pytest -q`、`bash ../scripts/check-layout.sh`、`git diff --check`。最終レビューとtiming/delivery/apply-logを更新し、source/spec/plan/resultsの対応を確認。秘密情報やstateはstageしない。`git commit -m "feat: deliver verified slum03 world and validation reports"` は実際に確認できた範囲に合わせて文言を選ぶ。

## 依存関係・停止点・レビュー

- Task 1→2が共通基盤。3〜8はTask 1/2のインターフェースに依存し、独立したレビュー単位にする。
- Task 9はAR階層と完成した配置を使う。Task 10は資源参照を統合。Task 11は全区画の評価結果と見た目を統合する。ライブ書き込みはcontrollerが早期実機ブロックアウト確認とTask 12でのみ行う。
- Task 3後、Task 8後、Task 11後はagent-handoffを作り、完了範囲、未確認事項、次の実行コマンド、実際のworktree/branchを記録する。長い生成・検証を起動したままターンを終えない。
- 各タスクでspec対応とコード品質を確認し、Task 11では芸術的な方向の照合、Task 12では所有・再適用・実機の最終確認を重視する。
- すべての編集元・出力・stateのパスはslum03内に閉じる。再利用元は読み取り専用。PR/予約ref/Issue操作は本計画の対象外。

## 計画レビューと実行方法の選択

2026-09-28 JSTにユーザーが本計画と **Subagent-driven（B）** を承認し、途中の承認待ちなしで最後まで実行するよう指示した。起動規約を整合した後は、この承認を再取得せずTask 1から継続する。Nativeへ勝手に切り替えない。

1. **Subagent-driven:** タスクごとに新しい実装担当とレビュー担当を使う。12の境界で見落としを減らせる一方、コンテキストとレビューの費用が増える。
2. **Native:** controllerがタスク順に実装し、節目で引継ぎを保存し、最後に独立したレビューを受ける。共有レイアウト/Blender環境を一貫して扱いやすい。

起動前検査の実測: 規約どおり `subagent({action:"list", capabilities:true})` を呼んだが、`action: schema is false`、`capabilities: schema is false`、`must not have additional properties` で拒否された。現toolは同期Superpowers role APIで、必須の `async:false` も定義されていない。規約元は `.pi/APPEND_SYSTEM.md:12-18`。エージェントは一件も起動していない。現在のセッションに適用されている起動規約を無視・変更して迂回せず、環境側で現行APIと整合し再読込された後にBを再開する。起動規約の整合以外に、計画や実行方法の再承認は不要。

## 自己レビューの確認先

- Spec 1〜6 → Tasks 1,3〜8。Spec 7 → Tasks 1,2,9〜11。Spec 8 → Tasks 9,10,12。Spec 9〜10 → 全テストとTasks 11,12。Spec 11 → 本計画の承認ゲート。
- RF-1 → Tasks 3,11。RF-2 → Tasks 2,3。RF-3 → Task 10。RF-4 → Tasks 8,9,12。RF-5 → Tasks 6,9,12。
- すべての生成器、共通型、Reportキー、root-yと描画座標の責務は上記の定義を使う。参照される関数を未定義のまま残さない。
