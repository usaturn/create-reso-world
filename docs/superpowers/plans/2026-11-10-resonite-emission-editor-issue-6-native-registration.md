# Emission Editor — native 多段ドロップ登録の実装計画（Issue #6）

- 状態: draft
- 対象: `usaturn/resonite-emission-editor#6`
- Spec: `../specs/2026-11-10-resonite-emission-editor-issue-6-native-registration-design.md`
- 文書管理: `usaturn/create-reso-world`
- 実装先: `external/emission-editor/.worktrees/issue-6-native-registration`、`feat/issue-6-native-registration`、基準 `fca8e25cb34707a7ebb7b805183b77a262a00bd7`
- 実行許可: 利用者の `/issue-to-pr`（`--merge` は対象が手動マージのため外し、利用者が「`--merge` を外して進める」を選択）。登録方式は、調査結果に対する利用者の「native 多段ドロップへ変更（推奨）」で確定した。内容の承認はない（`draft`）。
- 実行方式: `self`（agent-runner の雛形の既定）。同じ生成処理と native モジュールを逐次変更するため、`superpowers:executing-plans` としてこのセッションで実装する。Task ごとに検証し、最後にブランチ全体をレビューする。

## ゴール

未登録の初期パネルを生成・配備する入口を追加し、保存して取り出したパネルで、Resonite 内の多段ドロップ（アバター Root + 材質の `EmissionColor` フィールド）だけで登録し、既存の RGB ライブ編集・元に戻す・キャンセル・OK を使えるようにする。PC 側 ResoLoop は生成・配備時だけ使う。

## 受け入れ基準・環境・防御範囲

- 動作環境: 現在の Dev Container、uv/Python 3.14、ResoLoop 0.2.0、Flux-SDK 1.9.0、Resonite managed data 2026.11.6.1136。実機の接続・前面・対象の確認はマージ後に利用者の操作で行う。
- 実入力: 13 材質を持つ実アバター（利用者が画面上の名前で指定する。過去に確認した ID2300 のプラムを含む）と、新規の試験用対象。材質フィールドは `colorX` の `EmissionColor`。HDR RGB（1 を超える値）、Alpha 非 1、複数行、日本語の表示名を使う。行数は 16 まで。
- 防御範囲: 誤ったフィールドへの書き込み、元値の喪失、重複参照の二重編集、行間の結線取り違え、別パネルへの誤接続、失敗を成功と表示する経路を守る。`colorX` 以外の参照、`Root` という名前の Slot、17 行目は拒否または表示で明示する。対象外は、自動列挙・材質名・影響メッシュ・外部共有先・参照 ID 単位の重複排除、多人数同時編集、編集中の保存復旧、全材質型の保証。

## Task 1: native モジュールを追加する

**担当ファイル:**

- `flux/emission-editor/registrable/RootGuard.pg`（新規）
- `flux/emission-editor/registrable/RowGuard.pg`（新規）
- `flux/emission-editor/registrable/BeginRow.pg`（新規、`current/BeginRow.pg` を基に `CapturedField` を追加）
- `flux/emission-editor/registrable/RowPreview.pg`（新規、`current/RowPreview.pg` を基に、既知の利用先ガードを `CapturedField` の参照一致へ置き換える）
- `flux/emission-editor/registrable/RowCommand.pg`（新規、`current/RowCommand.pg` を基に同じ置き換えを行う）
- 再利用: `staged-s6/Session.pg`、`staged-s6/RowPresentation.pg`、`RowValue.pg`、`current/Commit.pg`

**内容:**

- `RootGuard`: アバター Root の参照を監視し、表示名と `RootReady` を出す。`Root` という名前の Slot を拒否する。
- `RowGuard`: 行のドロップ参照を `IValue<colorX>` にキャストし、`Registered`・`ValidField`・`Duplicate`・`Selected`・`CanSelect`・`CanEdit`・`DropEnabled`・`Visible`・表示文字列を出す。重複は同じ `IWorldElement` 参照の一致で判定し、自分自身のポートには null を渡す。選択時は `SelectedRow`・`SelectedRoot`（アバター Root）・`EditEpoch` を書く。16 行は常に表示し、記録のある行は `DropEnabled=false` でドロップ受付を止める。
- `BeginRow`: 選択時と、記録のない状態で参照が変わったときに、`CapturedField`・元値・入力欄を捕捉する。記録がある間は `CapturedField` を保持する。
- `RowPreview`／`RowCommand`: 入力の `SourceField` を `CapturedField` として扱い、書き込み・復元の直前に `CapturedField` が非 null で、登録参照と一致することを確かめる。既存の書き込み前記録、読み戻し、競合検出、失敗表示を保つ。
- `Commit`・`Session`・`RowPresentation`・`RowValue` は変更せず、結線だけを新しい行構成に合わせる。

**テスト:** 不要（.pg の動作はオフラインで実行できない。コンパイル失敗は L、実機の挙動はマージ後に確認する）。代わりの検証は、Task 2 の manifest 結線テストと、`flux-sdk build` の全ファイル成功。

**検証:**

```bash
cd external/emission-editor/.worktrees/issue-6-native-registration
for f in flux/emission-editor/registrable/*.pg; do
  flux-sdk build -L "$RESONITE_MANAGED_DATA_PATH" "$f"
done
```

## Task 2: 初期パネル生成と manifest 生成を追加する

**担当ファイル:**

- `scripts/emission_editor/registrable.py`（新規）
- `tests/test_emission_registrable.py`（新規）

**内容:**

- `POOL_ROWS = 16`。
- `build_panel(token, rows=POOL_ROWS)` は、UIX の shell と 16 行のプールを持つ宣言を返す。各行に `ReferenceField<FrooxEngine.IWorldElement>`（ドロップ参照）と `ReferenceField<FrooxEngine.IWorldElement>`（捕捉参照）、RGB 入力、元値／現在値、行の状態、選択ボタン、ドロップ領域、`ReferenceReceiver<FrooxEngine.IWorldElement>` を置く。全体に Root の `ReferenceReceiver<Slot>`、開始／OK／元に戻す／キャンセル、状態表示を置く。`ReferenceField` の初期値は空、外部参照・fixture・材質参照を含めない。
- `session_manifest(...)` は、Session 1 件、RootGuard 1 件、行ごとに RowGuard／BeginRow／RowValue／RowPreview／RowCommand／RowPresentation、Commit 1 件の manifest を作る。行のモジュールはその行のキーだけを参照し、他行のフィールドへ結線しない。RowGuard の `Other0..15` には全行の参照を渡し、自分の位置は `ui-null-element` にする。
- `create_panel(...)` は新しいディレクトリで `apply` し、所有キーを照合してからモジュールを validate／deploy し、最後に `registry-ready` と `ui-runtime-ready` を有効にする。材質・アバター・fixture へは書き込まない。

**テスト:** S に当たるものだけを `tests/test_emission_registrable.py` に置く。

- 生成した全行の Source／Captured／Provider 相当の参照が空で、外部参照を含まない（初期保存版が実アバターや fixture へ誤接続しない。データ消失・誤対象の防止）。
- 行 i の BeginRow／RowPreview／RowCommand の結線が行 i の `dropped`／`captured` キーを指し、他の行のキーを指さない（誤対象への書き込み防止）。
- `Other` ポートの自分の位置が null で、重複判定が自分自身と一致しない（全行が常に重複扱いになる誤判定の防止）。
- 16 行を超える指定を拒否する（上限の黙殺防止）。正しく 16 行が作れる例も残す。
- 初期パネルに `ui-operator` の参照値とプレビュー記録がなく、`SelectedRoot` も空である（初期保存版の要件）。

**検証:** `uv run pytest tests/test_emission_registrable.py`、`uv run pytest`、生成した panel JSON の `resoloop validate`、manifest の `resoloop flux validate-manifest`。

## Task 3: 生成・配備 CLI を追加する

**担当ファイル:** `scripts/emission_editor/registrable.py`

**内容:** `python -m scripts.emission_editor.registrable create --directory ... --url ... --library-path ... --position ...` を追加する。出力先は checkout の外に限り、`slim_demo.Demo` と同じ doctor／discover／apply／validate／deploy の手順を使う。成功時の summary に panelName、root ID、行数、ready を書く。既存パネルの再適用や同名 Root の再利用はしない。

**テスト:** 生成処理の安全条件（外部参照なし、行の分離、上書き禁止）は Task 2 のテストで代表を 1 件ずつ確かめる。CLI の引数解析・エラー終了は L としてテストしない。代わりに `--help` と、出力先が checkout 内なら停止することの実行確認を行う。

## Task 4: 使い方と制限を README に書く

**担当ファイル:** `README.md`（対象リポジトリ）

**内容:** 新しい入口、初期パネルの保存手順（操作者を取得する前に保存する）、Root と材質フィールドのドロップ、16 行上限、自動列挙・材質名・影響メッシュ・外部共有先・参照 ID 重複排除ができないこと、`EmissionColor` 以外の `colorX` を選ばない責任、別ワールドでは再登録が必要なことを書く。既存の PC 登録入口は残し、どちらを使うか明記する。

**テスト:** 不要（F/L）。代わりの検証は `git diff` と README の記述と実装の照合。

## Task 5: 全体を検証する

- `uv run pytest`（全 suite）を実行し、終了コードと件数を記録する。
- 全 .pg を `flux-sdk build` でコンパイルする。
- 生成した panel JSON を `resoloop validate` し、manifest bundle を `resoloop flux validate-manifest` で検査する。
- `git diff` で意図しない変更（fixture の追加、外部参照、既存モジュールの変更）がないことを確認する。
- 実機でのドロップ・編集・復元・保存再読込・複製・最終配備はマージ後の確認として残す。

## 実行予算・contingency

- 利用者は時間上限を設けていない。目安は、Task 1 に 30 分、Task 2 に 40 分、Task 3 に 20 分、Task 4 に 15 分、Task 5 に 15 分。各 Task の完了時に ledger へ記録し、30 分ごとに進捗を確認する。時間経過だけを理由に停止しない。
- コンパイルの失敗は同じ修正を 3 回まで試す。それでも通らない場合は、次の順に縮小し、Spec と Plan に記録する。
  1. `CapturedField` の参照一致を、`SourceField` の非 null 検査だけに縮小する。
  2. 行数を 16 から 8 へ減らす。
  3. `ReferenceReceiver<IWorldElement>` を非ジェネリックの `ReferenceReceiver`（`ISyncRef`）へ替える。
- 方式の意味（多段ドロップ、材質を書き換えない登録、既存の編集意味）を変える必要が出た場合は、実装を続けずに利用者へ確認する。
- 実機の接続・対象確認・操作は、マージ後に利用者が行う。この run では成功を装わない。
- 出力先の変更・既存パネルの再利用・PC 登録への切り替えは行わない。

## コミットと公開

- 文書は `docs/resonite-emission-editor-issue-6-native-registration` にコミットし、コードは `feat/issue-6-native-registration` にコミットする。
- push の前に `scripts/scan-before-push.sh` で未 push commit を検査する。
- コードの PR は `usaturn/resonite-emission-editor` の `main` 向け、文書の PR は `usaturn/create-reso-world` の `main` 向けに分ける。文書の PR は Spec・Plan だけを含め、コードの PR と相互参照する。マージはしない。
