# Emission Editor の共通基盤への登録・公開ソース移行 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 共通基盤の登録先として、独立した公開 repo に Emission の開発ソースとポータブルなSテストを置き、既存実機資料を保持したまま今後のコード開発を移す。

**Architecture:** 先行Planの採用済み台帳から常設checkoutを決める。元コードは動かさず、ファイル単位の権利・依存・公開範囲の監査結果からコピーし、新コピーだけの最小分離でオフライン検査を独立させる。現在worldのstateや実機試験は移行せず、native切替は別の計画にする。

**Tech Stack:** Python >=3.14、uv / pytest、既存 ResoLoop / Flux-SDK / managed DLL による隔離したオフラインbuild、Git/GitHub CLI。Actionsは無効。

**Spec:** `docs/superpowers/specs/2026-11-06-emission-editor-repository-management-design.md`、現行保存版 `c654fafaa9eb7cdb6d2136c31f8239f44bb5c7a9`。承認の参照版は `b8c9b4253a5cd3431c9e2e6320649c2de14c15d8` と利用者の最低Python3.14への明示変更。

- 状態: completed
- 内容の事前承認は無い。実行は利用者の個別指示による。この状態は移行作業が終わった記録であり、設計を事後に承認したという意味ではない。
- 草稿の確認状態: writing-plans の最終自己点検を実施し、下記に記録。型・Sの対応・最小context分離・offline build呼出しを具体化した。作成時点では Plan は未承認・全 Task 未実施で、その自己点検は実行許可ではなかった。
- 先行Plan: `docs/superpowers/plans/2026-11-06-external-tools-framework.md`。共通基盤と台帳は #317 で親へ採用済み。
- 文書作業先: 作成時 `/workspaces/reso-world/.worktrees/emission-repo-management`。結果追記は `/workspaces/reso-world/.worktrees/emission-onboarding-record`。親の追跡ファイルは直接編集しない。
- 元コード: `/workspaces/reso-world/worlds/tools`（Git追跡外、移動・変更しない）。
- 新repo: `usaturn/resonite-emission-editor`。常設 root は `/workspaces/reso-world/external/emission-editor` で、detached HEAD は merge commit `a8d7d4068b681de82cb79feb6215bc39743faccd`。
- Issue / PR: create-reso-world #318。コード PR は usaturn/resonite-emission-editor#1 で MERGED。実機切替と、未公開のツール機能 Spec/Plan の公開は未実施。

## Global Constraints

- 共通基盤と新しい Emission Editor リポジトリの Python は最低 3.14（`requires-python = ">=3.14"`）とする。
- 正式な Spec・Plan は引き続き create-reso-world の `docs/superpowers/` に置く。
- 元のディレクトリを移動せず、選別したソースを新しい作業領域へコピーする。
- `.resoloop/` の実 state、deploy checkpoint、接続・登録 capture、実機 session / ID の対応資料を公開しない。
- 旧 `/workspaces/reso-world/worlds/tools` と既存証拠は変更・削除しない。sealed source/hash/manifest/state、G0、SourceMap を移行のために書き換えない。
- 登録だけでrepo作成・push・PR・マージ・release・実機操作を許可しない。今回のコード整備はオフライン、world呼出し0。
- 初期repoのActionsを無効化する。ライセンス未選択/権利不明/公開候補未精査ならソースをpushしない。

## Review Focus

1. 古い59125/33046の実行用入口が公開コードの現在の利用手順にならないこと — Task3のcontext必須/CLI非実行のS。
2. 安全な汎用関数まで履歴依存ごと消して守りを失わないこと — Task1の対応表とTask3–4の既存S。
3. `current/` と root PG、未反映のTask5/S6候補を取り違えないこと — Task1/4のsource選択と隔離compilerのS。
4. 新コピーのbuildが作者側や凍結 `.brson` を上書きしないこと — Task3–4のfake compilerと元の保全検査。
5. README bootstrapやsecret scanのPASSを、コード公開/実機成功と誤報告しないこと — Task2/5の段階別actual receiptとレビュー。文書文字列テストにはしない。

---

## 受け入れ基準

- **環境:** 先行共通基盤の採用commitを読める親checkout。新repoの常設rootはdetached、コード変更はそのlinked worktree。Python>=3.14、uv、GitHub認証は既存のものを使い、値を記録しない。旧worldのpyprojectやSDK/DLLを更新しない。
- **実入力:** 現在の作者ソース、汎用registry template、選択済みPG、fake登録対象2件（同名/日本語/複数行）、完全RGBA/profile、無効RGB文字列、途中失敗するfake compiler。
- **防御範囲:** 認証情報・素材・state/raw/log等を含まない明示一覧。旧hash/source選択と同じ意味のSを維持する。URL/state/baselineを旧sessionから自動で補わず、新コピーの操作用contextも明示必須にする。
- **対象外の反例:** 古いrunを再生するCLI、private referenceのコード、実アバター、native拒否/解除/復元、実UI・二人・save/reloadは今回の成功条件ではない。
- **完了:** 新repo自身のrootだけでオフラインtests/必要PG buildを実行でき、旧world/tmpに依存しない。コードcommitとreview、push/PR、mergeの各状態を別に報告。PR公開まで進むにはその許可も必要。

## 実行予算・作業領域・監視

時間上限なしを維持する。目安は監査60–90分、GitHub bootstrap15–30分、抽出/最小分離90–180分、検証/公開準備60–120分で、許可上限ではない。各Task/外部操作の境界、失敗直後、能動60分ごとにcheckpoint。利用者待ちは除外して `SESSION/timing.md` に記録する方式を提案する。有限値しか扱わないissue_budget.pyへinfや架空の上限を渡さず、拡張も今回行わない。JSONL helperに代わる今回限定の記録例外は先行Planと合わせて確認し、未確認なら実装開始をblockedとする。

`agent_tmp.py mkdir emission-onboarding` の一意SESSIONに `audit.json`、権利判断、raw receipts、SDD `sdd/2026-11-06-emission-editor-onboarding/` を置く。worktreeに未コミットの証拠を作らない。公開しない資料はGit追跡外で保持する。Task2/5の不可逆な外部操作はcontrollerが集中管理するためinline、コード実装はsp-implementer、Taskレビューはreadonly sp-review。レビュー子はテストしない。

Taskは1→2→3→4→5。Task1監査とTask2/5の外部操作は依存とcontrollerの許可確認を要し、並列writerへ分割しない。同じ受け入れ基準を実装担当・レビュー担当双方へ渡す。チェックはcontrollerが更新する。

worker絶対期限/外側timeoutはなし。監視・同期待ち・10分進捗/2回無変化stall報告はmonitoring-long-tasksに従う。信頼性失敗の同条件retryは1回まで、安全の失敗は全体停止。通信断でrepo作成/push結果が不明なら再実行せず読み取り照合する。

## ファイルと公開範囲

新repoでは `scripts/emission_editor` の名前とroot相対配置を維持する。`src/` への再配置は行わない。新 `pyproject.toml` は project名 `resonite-emission-editor`、`requires-python=">=3.14"`、runtime依存なし、dev `pytest>=8`、testpaths=`tests`、pythonpath=`["."]`、uv package=false。`uv.lock` は新しく生成する。

最初に監査するPython候補は `scripts/__init__.py` と `scripts/emission_editor/{__init__,__main__,model,resoloop_io,ui,recovery,guard_supplement,claim_recovery}.py`。`runtime_59125.py` / `recovery_33046.py` は実行用履歴として残し、初期公開packageに含めない。

templateは `content/emission-editor/registry.json`。生成済み `panel.json`、runtime-*、primary-*、旧fixtures、全 `.resoloop` / artifacts / tmp / `.brson` は公開しない。

PGの最小active-ui集合はrootの `Session,Generation,DropGuard,BeginRow,RowValue,RowPresentation.pg` と `current/Selection.pg`, `current/RowView.pg`。別bootstrapの `SessionIdentity.pg`、開発途中の `current/{RowPreview,RowCommand,Commit,BeginRow,CommitProofProbe}.pg` と `staged-s6/{Session,Selection,RowPresentation}.pg` も監査候補に含め、採用する場合は `bootstrap|candidate|proof` と分類し、active-uiに昇格しない。これらの未完了な開発ソースを黙って落として移行完了にしない。`current/{ConflictProof,GuardProof,InputDriverProbe,ReadbackProof,RequestProof}.pg` もproof候補としてauditに必ず採否を記録する。影になったroot Selection/RowViewやその他の実験PGは、依存/権利監査で必要性が確定しない限り除外する。全PGを列挙して分類し、名前を列挙したことだけでincludeにしない。

監査結果 `audit.json` の項目は `sourceRelative,destinationRelative,sha256,kind,decision,reason,provenance,transform`。kind=`python|test|template|pg-active|pg-bootstrap|pg-candidate|pg-proof`、decision=`include|exclude|hold`。絶対path/実session/個人情報は非公開の別記録へ分け、公開版source一覧に入れない。未知の必要依存はhold、採用manifestを変更するなら理由を記録してレビューする。

### Task 1: 移行前監査と公開前の判断ゲート

**Files:** Read only 上記作者ソース・関連tests。Create SESSION内 `audit.json`, `safety-map.md`, `license-review.md`（すべて非公開）。既存コードは変更しない。

**Interfaces:** Produces file-level auditとSの移行対応、source snapshot hashes、ライセンス候補/未確認事項。Task3はinclude項目だけを消費し、コピー前後にhashを再照合する。

**テスト:** 新規永続テストなし。人による一回の公開選別・権利判断（F/Lをテスト化しない）。元コードの既存保全検査はツールで実行する。

- [ ] **Step 1:** 先行Planの共通package/台帳が親に採用されたcommitと、登録repo/path/CI/baseを確認する。機能branchにファイルがあるだけなら停止する。
- [ ] **Step 2:** 候補のimport・resource・PG選択を読み、auditを作る。`ui.native_source_path` と既存CURRENT_NATIVE_SOURCESを基準にactive-uiを特定する。Task5候補のsource群は既存pinを読み取り照合し、実験物と区別する。コードをimport/生成して実機を調べない。
- [ ] **Step 3:** testsのS/F∩Sを新実装に対応付ける。少なくともcompiler隔離、WriteBack=false/私有Target、元値/入力/epoch保持、途中claim/記録失敗、競合拒否を列挙する。旧runtime_59125/recovery_33046専用テストは元に保持し、新APIの対象外か代替Sが必要かを明示する。
- [ ] **Step 4:** 元cwdで `uv run python -m scripts.emission_editor.runtime_59125 offline-check`。新nativeがまだ無い場合だけ旧prestart verifierを実行し、pinを変えない。holdの必要依存・権利不明・秘密候補があれば止める。
- [ ] **Step 5:** 利用者へライセンス候補と由来を提示して選択を得る。public/作成/README説明/初回source push/PRの許可を個別に記録する。計画承認だけで補わない。このTaskだけでは公開もコードcommitも行わない。

### Task 2: controllerによるGitHub bootstrapと共通経路での取得

**Files:** Create SESSION内 `bootstrap-receipts/`。新GitHub repoの生成READMEのみ。新常設checkoutはまだ作者ソースを含まない。

**Interfaces:** Consumes Task1の権利/許可と採用済み共通経路。Produces `repositoryId,repository,url,visibility,actionsEnabled,baseRef,baseSha,checkout,commonDir` を含む確認記録。baseShaを以後固定する。

**テスト:** 自動テストは書かない。本物の外部操作をテストに使わない。controllerが実応答とreadonly設定取得を確認する。実装のない外部操作を集中管理するTaskなのでinlineとする。

- [ ] **Step 1:** `gh repo view usaturn/resonite-emission-editor` 相当の読み取りで存在/権限を確認する。既存なら再利用・上書きせず停止。404だけで権限エラーを「空き」と決めない。
- [ ] **Step 2:** 実行許可後だけ `gh repo create usaturn/resonite-emission-editor --public --add-readme --disable-wiki --description 'Experimental source code for a Resonite avatar emission editor.'`。`--source` / `--push` は使わない。descriptionも事前確認する。
- [ ] **Step 3:** 直後に `gh api -X PUT repos/usaturn/resonite-emission-editor/actions/permissions -F enabled=false`、続くGETでfalseを確認する。owner/repo/ID/PUBLIC/mainを読んで固定する。失敗/不明ならsource push禁止。既存親のActionsは変えない。
- [ ] **Step 4:** 採用済み共通CLIの `clone emission-editor` で取得し、detached/main基準SHA/common-dirを記録する。既存物・未完了stagingは勝手に修復しない。bootstrap SHAの変更を観測したら止める。
- [ ] **Step 5:** Taskレビューへ実応答を渡す。READMEのみのrepoを「source移行済み」と報告しない。コード担当へ渡す前に、通常worktree `feat/initial-source-import` を作成して絶対CODE_ROOTを記録する。

### Task 3: 公開コピーの最小分離と同等のSをRED/GREEN

**Files:** 新CODE_ROOTに上記Python/template/PGのinclude項目、`scripts/emission_editor/context.py`、`pyproject.toml`, `uv.lock`, `.gitignore`, `README.md`, `AGENTS.md`, 選択済みLICENSE/必要な帰属文書。Testsは `test_emission_{registry,publish,retention,guard_supplement,claim_recovery,claim_journal,position}.py` と選別した `test_emission_recovery.py`、新 `test_emission_context.py` と共通fakeを置く `tests/conftest.py`。保全baselineは一時fixture内だけで生成し、旧41件のbaselineや空baselineを公開用の既定値にしない。

**Interfaces:** `context.py` の frozen dataclass `ProjectContext` は `project_root, source_root, registry_template, world_state, flux_state, preservation_baseline: Path` と `url, owner, root_name: str`（いずれもdefaultなし）。`validate_context(context: ProjectContext) -> None` は既存root、source/template/baselineの存在とroot内配置、world/flux stateの別pathと既存祖先のroot内配置、明示ws/wss URLを検査する。所有値は既存の `tools-emission-editor` / `ResoLoop_Test_EmissionEditor` だけを許可し、今回一般化しない。baselineは明示された非空のpath→SHA-256 mappingで、対象も新root内に限る。現在sessionの承認やlive readinessを証明するAPIではない。

- `ResoloopReadPort(context: ProjectContext, *, evidence: Path)` は上の検査とevidenceのroot内・未使用確認後にだけ記録領域を作る。state/flux_state/baselineはcontextから設定し、旧URL/stateをdefaultで補わない。`.context` を保持する。
- `ResoloopPanelPort(read: ReadPort, capture: RegistrationCapture, retained_declaration: dict | None = None)` と `UIPanelPort` のconstructorは維持する。実装が利用するreadには `.context` が必須で、同じcontextを引き継ぐ。fakesも `.context` を持たせる。
- `render_registry(plan: RegistryPlan, *, template: Path) -> dict`、`render_panel(registry: RegistryPlan, *, template: Path) -> dict`、`native_source_path(name: str, *, source_root: Path) -> Path`、`session_manifest(registry: RegistryPlan, *, world_state: Path, deploy_state: Path, source_directory: Path, source_root: Path) -> dict`。呼出し元すべてへ明示引数を通す。`render` CLI は `--template PATH` を必須にする。
- `publish_registry(plan: RegistryPlan, port: PanelPort) -> PublishResult` は変更しない。結果fieldは `success, ready: bool` と `generation, error: str`。capture/planの `.complete` は事前観測の完全性で、登録成功とは別。

algorithm/PGの振る舞いは変更しない。managed DLLは既存どおり `RESONITE_MANAGED_DATA_PATH` を明示し、fakeのstageテストでは一時libraryディレクトリをsetenvする。新live runnerやcontextの永続保存・自動採取は作らない。

**テスト:** S。省略したcontextから旧sessionへの書込や、resource/baselineの取り違え、凍結sourceの上書き、移行時の元値消失を防ぐ。単なるimport失敗はLなのでsmokeで代える。

- [ ] **Step 1:** includeファイルを新worktreeへ非置換コピーし、hashを監査値と照合する。live入口・旧captureをコピーしない。全変更は新コピー内だけ。
- [ ] **Step 2:** `test_live_cli_refuses_before_transport` と `test_context_refuses_resources_outside_new_root` をREDにする。live registerは既存CLIの必須引数を揃えてもtransport/evidence作成前に拒否し、contextが範囲外baselineを指す場合も通信・書込0。有効な一時contextではfake登録の正例を既存Sと共有する。
  ```python
  assert live_exit != 0
  assert transport_calls == [] and not rejected_evidence.exists()
  with pytest.raises(ValueError):
      validate_context(outside_baseline_context)
  validate_context(fake_context)  # 新root内の非空baselineと作者作成resource
  result = publish_registry(plan, fake_panel_port)
  assert result.success and result.ready
  assert fake_panel_port.avatar_writes == []
  assert fake_panel_port.old_recovery == {"baseline": "preserve", "candidate": "preserve"}
  ```
  `fake_context` は新root内にsource/template、作者作成の保全対象1件以上とその実hashを持つbaseline、専用world/flux state、明示URL/所有値を準備する。拒否だけで何でも止める実装を合格にしない。
- [ ] **Step 3:** 上記署名のcontext/resource注入だけを新コピーに実装する。旧59125のURL・state・絶対baselineをdefaultとして補わない。`__main__` の `load_capture` 等の純粋処理は保持するが、live register入口は公開版で有効化せず、native切替計画が未承認と示してconstructor/transport前に停止する。`ResoloopPanelPort.render_declaration` / `UIPanelPort.stage` はread.contextを使う。直接のrender呼出し・`port.render_declaration = render_panel` の旧monkeypatch・session_manifest呼出しとfake Readにも引数を通し、cwdへfallbackしない。
- [ ] **Step 4:** 既存 `test_compiler_sibling_output_stays_in_isolated_tree`、`test_main_registration_isolates_compiler_and_keeps_failed_ui_closed`、`test_native_current_reader_cannot_write_back_to_registered_material`、claimの拒否/正例・journal、`test_stage_retains_existing_records_without_replaying_values_or_foreign_scope` を新contextのfakeでGREENにする。実値由来のfixture文字列は同じ意味の作者作成データへ置換する。`test_recovery_generator_keeps_one_driver_and_is_idempotent` と `test_guarded_transport_stops_cleanup_writes_after_disconnect` は旧artifact内の実行scriptに依存するため元に保持し、対応する守りが新コピーにも必要ならsafety-mapに代替を記す。59125固定を検査する `test_main_transport_rejects_legacy_checkpoint_before_recording` は新contextの境界拒否/正例へ対応付ける。既存Sを黙って削除して移行完了にしない。
- [ ] **Step 5:** `uv lock` / `uv sync --locked` 後、新rootで `uv run pytest`、構文/import、`git diff --check`。source選択の意味、失敗後停止と保全を維持したことを確認しcommit・Taskレビュー。実機確認済みとは表示しない。

### Task 4: 独立したオフライン検証と公開treeの確定

**Files:** 新repo README/AGENTSの検証手順、必要なら `source-status.json`（相対path・hash・active/candidate/proofの区別のみ）。SESSIONに非公開の検査ログ/元資料の保全結果を保存する。

**Interfaces:** Consumes auditとTask3のcommit。Produces source tree SHA、S対応表、offline test/build結果、元の保全結果。候補をactiveへ昇格する機能は提供しない。

**テスト:** 既存Sを再実行。新しい文書/固定PG一覧のFテストは書かない。作者と生成物の分離はTask3のSで代表し、別層に重複させない。

- [ ] **Step 1:** 新Git treeからSESSION内の一意な一時領域へ展開し、元world/tmpを渡さず、`uv sync --locked` の後 `unshare -rn uv run --no-sync pytest`。PYTHONPATH/PYTHONHOMEを渡さず、全project moduleの `__file__` が展開root配下であることを一時smokeで確認する。ユーザHOMEはexportで変更せず、必要ならワンショット隔離。依存取得時のネットワークとテスト中のworld呼出し0を区別する。
- [ ] **Step 2:** `RESONITE_MANAGED_DATA_PATH` の既存ディレクトリを明示した MANAGED_DATA として使い、不明/不在ならbuildをblockedとする（doctor/discoverを代用しない）。auditのinclude PGを相対配置ごと一意なcompiler作業領域へコピーする。SOURCEはそのコピーの絶対path、BUILD_ROOTは同領域、OUTPUTは同領域内の未使用な `<相対source>.brson` とし、親を作ってから次を各sourceで実行する。
  ```bash
  resoloop flux check "$SOURCE" --project "$BUILD_ROOT" --library-path "$MANAGED_DATA" --json
  resoloop flux build "$SOURCE" --project "$BUILD_ROOT" --out "$OUTPUT" --library-path "$MANAGED_DATA" --json
  ```
  各exit0と診断/出力path・実ファイルを確認する。sourceを別領域へ置くのでcompilerがsource隣へ出力しても作者側を変更しない。2026-11-06の導入版0.2.0のhelpで positional FILE.pg / --project / --out / --library-path / --json を確認済み。版は固定せず、実行時もhelpと版を記録する。採用したschema-v1 manifestがある場合だけコピーに `resoloop flux validate-manifest "$MANIFEST" --json` を行う。doctor/discover/deploy/watchは実行しない。
- [ ] **Step 3:** auditとgit tree/全commitを人が照合し、除外対象・権利・日本語fixture・未反映candidate表示を再確認する。旧worldで保全検査を再実行。元資料/新tree/PG出力が変わったらTask3へ戻り、scan済みSHAは破棄する。
- [ ] **Step 4:** READMEに開発中・live入口非対応・正式文書は親・実機切替別gateを記載する。AGENTSは親安全規則、Python>=3.14、uv、clone/コード/文書/レビューの境界を定義する。永続する絶対個人パスや実sessionを記載しない。
- [ ] **Step 5:** 最終code commitを固定してTaskレビューを受ける。Task1–4で採用した全変更がtask review済みか確認し、未解決Importantを黙って残さず、native未実施とソース移行の検証を分ける。SDDの最終全体レビューはTask5の外部操作と記録を含む全Task終了後に行う。

### Task 5: controllerによる秘密情報検査・初回source push・PR

**Files:** SESSIONにscan/push/PRの実応答。正式Planの結果はcreate-reso-world側のDOC_ROOTへ追記する。新repoに正式Spec/Planを複写しない。

**Interfaces:** Consumes レビュー済みcode SHA / bootstrap base SHA / licenseと公開の許可。Produces 公開した正確なSHA、code PR URL、CI/Actionsの実設定と未実施事項。merge許可は含めない。

**テスト:** 新規テストなし。既存scan helperと実応答を使う。public操作のためcontrollerがinline管理する。

- [ ] **Step 1:** repo ID/remote全送信先/base SHA/Actions=false/レビュー済みHEAD/権利/許可を別々に再確認する。新repo作成時のREADME commitをbaseとして実在させ、空remoteを理由にscanを迂回しない。
- [ ] **Step 2:** 親の `scan-before-push.sh -C CODE_ROOT --base origin/main --expected-base-sha BOOTSTRAP_SHA` を実行し、成功時の非空SHAとレビュー済みSHAを照合する。検出/未知の失敗ならpushしない。除外設定で回避せず、偽値の修正は共通規約の条件をすべて満たす場合だけ。
- [ ] **Step 3:** 許可された場合だけ、そのSHAを `origin` の `refs/heads/feat/initial-source-import` へpushする。`${SHA:?}` で空値を拒否する。結果不明ならGET/ls-remoteで照合し、同じpushを盲目的に繰り返さない。
- [ ] **Step 4:** PR作成の許可がある場合だけ、対象repo/base/headを明示してcode PRを作成し、実head SHAとbaseを確認する。Actions無効・CI未使用・native未実施を記す。自動マージしない。
- [ ] **Step 5:** コード/文書の所在、レビュー・ローカル検査・公開・PR・merge・実機切替を別状態で記録する。全Task終了後のSDD全体レビューを `Review scope: branch` で依頼し、Task1–5の証跡とcode diffを対象にする。指摘でcode SHAが変われば再検証・再scanと更新pushの許可確認が必要。文書側のpush/PRも別許可/scanが必要。全体レビューと所定cleanup後のみfinishingへ進み、handoffを残す。

## contingency（代替策）

- sourceの権利や依存が未解決なら公開せずTask1で停止する。非公開化へ勝手に方針変更せず、保留内容を利用者へ提示する。
- generic部分の切り出しが広範なAPI/PG変更を必要としたら、scopeを広げず設計へ戻す。旧worldコードを書き換える回避は禁止。
- GitHub repoが既存/作成結果不明/Actions設定不明/base移動なら停止。repo削除・force push・旧state再生で直さない。
- buildのCLI形状が前提と違えば、意味を保った出力隔離の呼出しだけを修正して記録する。旧sourceや判定・受け入れ基準は緩めない。
- オフライン移行が通ってもnativeは開始しない。現在のS4/r3失敗・短いDrivegate未実施・S5以降の未完了を保持する。

## Plan 自己点検と完了記録

controllerがSpecと作者ソース/既存Sを照合し、子には不足する署名・呼出し元・PG選択の事実調査だけを依頼した。CLIはcontrollerがContext7のResoLoop一次資料と導入版helpを照合した。build/tests/実機確認ではない。

1. 仕様網羅: Spec4→Task1/3/4、6→Task2/5、7→旧資料保持とnative別gate、8→各Taskの検証。Spec5の共通基盤は先行Planへ分離した。
2. 手順: source採否を監査で決め、未反映PGをactiveにしない。旧baselineを持ち込まず一時fakeでSを検証する。buildの入力・出力をともに隔離し、必要なmanaged DLL不在はblockedとした。
3. 型: 存在しなかった `.completed` を `PublishResult.success/ready` に訂正。context/renderer/manifestの署名とcall-site、fake Readのcontext/library、非空baselineの用意を具体化した。owner/rootの一般化・新live runnerは行わない。
4. Review Focus: 1→Task3のtransport前拒否、2→Task1のS対応とTask3の既存S、3→Task1の分類とTask3–4のsource検証、4→Task3のcompiler隔離SとTask4の旧保全、5→Task2/5のactual receiptと段階別記録。外部操作にfakeの成功を代用せず、F/Lの恒久テストを増やさない。
5. 分量: 最小分離のインターフェースと代表assertに限定し、実装本体は書いていない。sourceの実採否・由来・ライセンスはTask1、外部操作は別許可で決める。

上の自己点検は、作成時点の記録である。実行結果は次のとおりで、各状態は別である。

## 実行記録

- ライセンス: BSD 2-Clause。表示は `Copyright (c) 2026 usaturn`。
- 公開 repo: `usaturn/resonite-emission-editor`、id `R_kgDOVl5t4g`、PUBLIC。Actions は `enabled=false`。`main` の branch protection は無く、ruleset は 0 件。
- コード: `696995a249c316dea809873b64c88a60b4791dc8` のあと、レビューで直した `b4b4ff0f9b964787cb0f9142563ffd991eebaea8`。merge commit `a8d7d4068b681de82cb79feb6215bc39743faccd` の tree は `b4b4ff0` と同じ `dd03ed492c19a59948d3e98f4f9be91c54da238c`。
- レビュー: `f8136f76..696995a` の branch review で Critical は無く、Important が 2 件。保全ハッシュの root 解決と、root 外 state / 同一 state パスのテストを `b4b4ff0` で直した。その差分の再レビューでは 2 件とも解消し、新しい Critical / Important は無かった。Minor は保留。`isolate_manifest` は削除していない。
- push: scan の印字 SHA だけを `feat/initial-source-import` へ送った。`696995a` と `b4b4ff0` は別々の scan と push。検出はどちらも無し。
- PR: https://github.com/usaturn/resonite-emission-editor/pull/1 は利用者が merge した。merge commit は `a8d7d4068b681de82cb79feb6215bc39743faccd`。
- 常設 checkout: detached の `a8d7d4068b681de82cb79feb6215bc39743faccd`。登録照合は `ready`。
- 検証: 2026-11-07 に、その checkout で `uv sync --locked` のあと `uv run --offline pytest` は 40 passed。同じ commit の archive から隔離したコピーで、ProtoFlux 22 件の check と build はすべて exit 0 で、出力 `.brson` は作業領域だけ。checkout の追跡ファイルは変わっていない。doctor、discover、deploy、watch はしていない。
- 未実施: 実機切替。未公開のツール機能 Spec/Plan の公開。この文書の merge は、この記録の PR を作っただけでは行わない。
