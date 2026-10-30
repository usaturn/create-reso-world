# #100 プラグイン UIX レシピ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** プロジェクト別の検証済みレシピ API と、主入力に固定した `$recipe` 展開を実装する。

**Architecture:** instance resolver が F の OpenVerified lease とテキストsnapshotを所有する。UixRecipes は既存 Catalog を変更せず合成 API を提供する。Compile は主入力から遅延作成し finally で resolver を解放する。

**Tech Stack:** .NET 10 / C# / System.Text.Json / xUnit、既存 PluginRegistry/PluginInstaller。

**Spec:** `docs/superpowers/specs/2026-10-30-create-reso-world-issue100-plugin-recipes-design.md`（draft、利用者の issue-to-pr 実行許可。内容承認なし）。

## Global Constraints

- コード: usaturn/resoloop `origin / refs/heads/feat/plugin-v2`、捕捉 SHA `dd0b40fb216b0c9fbd82da44903195a885104015`。
- 文書: create-reso-world `origin / refs/heads/main`、捕捉 SHA `acd288c3e81a6c108136e37815e718a0fe088195`。
- 非default baseをmainへ読み替えない。捕捉後の移動は停止し、新SHAを採用しない。
- 変更は resolver新規、UixRecipes（Catalog除外）、ApplyDocumentCompiler、PluginRecipeTests、recipes fixture のみ。ApplyWorkflow/Program/CommandLine/既存Plugins/他子所有は変更禁止。
- 名前 `<plugin-name>:<recipe-name>`、生成キー `uix-plugin--<plugin-name>--<recipe-name>--<caller-key>`、組み込みは不変。bare plugin名の探索は禁止。
- recipe消費は OpenVerified lease 下。Compile成功/失敗の両方で解放する。static可変状態を作らない。
- Pythonはuv。テスト/fixtureは一時所有領域、live接続/実認証/global導入なし。シェル削除変数は引用と`${VAR:?}`。
- 実行は self/inline。2 Task が同じテストとresolverのAPIを逐次変更するため。実装担当と最終レビュー担当は同じ受け入れ基準・Spec/Planを読む。レビュー子は読み取りのみ。

## 受け入れ基準

動作環境: 本 Linux Dev Container と global.json の .NET 10。公開Windows CIはコードPR後に区別して確認。実機Resonite/Blenderは使わない。

実入力: 一時プロジェクト「主 ワールド」「別 ワールド」。主入力が別ワールド内JSONをinclude、cwdも別ワールド。複数行/日本語JSON、`aa-plugin:sample-card`・`bb-plugin:sample-card`、caller key `panel_1`。プラグイン生成キーの期待値は仕様から直接記す。

防御範囲: namespace/key/main projectの取り違え、bare fallback、未導入/不整合の無視、既存export破壊、lease漏れによる後続処理不能、組み込み回帰。Fのpath/hash/lock機構を重複実装/網羅しない。悪意ある同一ユーザの完全防御・runtime UIX検証・CLI結線は対象外。

## Review Focus

- レシピ利用失敗後に lease が残って次の利用を拒否しないこと（Task2の代表テスト）。
- 組み込みのみの入力がproject無し/壊れたpluginでも従来どおり展開すること（Task2）。
- 同じローカルレシピ名の別pluginを一覧から説明/読取/exportまで取り違えないこと（Task1）。
- 修飾名にresolverを渡さないAPIがcwdのpluginへfallbackしないこと（Task1）。
- CLI entry versionとCore既定versionを取り違えないこと（Task2の実CLI offline validate、非CLIは明示版）。

## 実行予算

- 全体360分（開始前の調査時間は別途報告）。準備/設計45、実装70、検証/全体レビュー40、公開25、ループ最大3×60=180分。公開CI/レビュー待ちも能動時間。
- ledger: `/workspaces/reso-world/tmp/agents/issue-100.yvd477qx/budget.jsonl`。SDD: 同sessionの `sdd/2026-10-30-create-reso-world-issue100-plugin-recipes/`。消さず引き継ぐ場合は完全パスを報告する。
- 読み取り専用設計/全体レビューは同期subagent。共有実装/検証はkillしない。将来ループのレビュー期限45分、fix担当90分はrunner定義どおり。追加の実モデル実験は行わない。
- 同じ信頼性失敗の再試行1回、権限/外部送信等の安全失敗は即停止。checkpointはphase境界・50%/100%・worker失敗直後。100%で延長せず停止する。
- 範囲拡大が必要なら親裁定を待つ。CLI結線を早める・builtinを削る・検証前mergeで縮小しない。仕様の意味を変えないAPI/テストfixtureの最小修正だけledgerに残して継続する。

## contingency（代替策）

- 初回REDが想定APIと異なるときは実出力を記録し、仕様の意味を保つ最小修正で継続。意味/所有境界が変われば停止。
- `ApplyDocument.cs`は存在しない。Compile内文脈で足りなければApplyWorkflowへ無断変更せず停止し、親のscope rulingを求める。
- Coreのversionは実CLI版でない。default Compileのplugin利用はentry名resoloopのみ対応し、非CLIは明示版overload。version不明を固定0.2.0やCore1.0.0で代用しない。
- base移動/競合/公開検査/必要API失敗はスキルの停止条件。捕捉値の差替え・既存作業再利用・force pushで回避しない。

## 要件・原因・検証の対応

| 条件 | Task/統合担当 | 観測/独立した根拠 |
| --- | --- | --- |
| project別list/describe/read/export | 1 | 別plugin同ローカル名を明示fixtureで読み分け、既存export sentinel不変 |
| 主入力/include/cwdの固定 | 2 / controller | 同名pluginが異なる値を返す2worldを独立構成し主入力の結果に一致 |
| namespace/deterministic key | 2 | 仕様から直接記した `uix-plugin--aa-plugin--sample-card--panel_1` と一致、反復結果同一 |
| 照合と利用の順序/lease | 1,2 / controller | modified拒否と正常対照、失敗後再利用成功。FのOpenVerifiedを使用するコード経路も確認 |
| builtin不変 | 2 | 既存UixRecipeTestsとプロジェクト無し/壊れたpluginでのcompile成功 |
| CLI版/接続前停止 | 2 / controller | 実CLI offline `validate`、ワールド接続なし。Program.csは変更しない |
| 公開・統合条件 | controller | final HEAD clean、build/test logs、全体レビュー、scan、base/head実PR照合 |

### Task 1: 検証済み resolver と UixRecipes 合成 API

**Files:** 新規 `src/RLoop.Core/Plugins/PluginRecipeResolver.cs`、変更 `src/RLoop.Core/UixRecipes.cs`（Catalog以外）、新規 `tests/RLoop.Tests/PluginRecipeTests.cs`。fixtureが必要なら許可recipes directoryだけ。

**Interfaces:** Specの `PluginRecipeResolver(PluginRegistry)` / `ProjectRoot` / plugin-only `Catalog` / `Describe(name)` / `Read(name)` / `ForDocument(path,version,reservations)` / `Dispose()` と UixRecipes `List(resolver=null)`、`Describe/Read/Export` resolver付きoverload。既存overloadは維持。

テスト要否: S の名前取り違え、export破壊、無検証read、lease漏れのみ恒久化。単なるコード文言・argparse・構文エラー等F/Lは追加しない。

- [ ] `CatalogRoundTripIsNamespacedAndExportNeverOverwrites` を先に書く。別plugin同ローカル名/日本語内容、一覧のNameをDescribe/Read/Exportへ戻し同じ内容が得られる。既存出力へexportを拒否しsentinelを保持。resolver無し修飾名/bare plugin名は暗黙探索せず拒否する。
- [ ] `ModifiedPackageIsRejectedBeforeRecipeRead` を先に書く。正常read→破棄→packageのJSONを変更→新resolverは拒否。復元後read成功。ここはresolverが検証APIを実際に使う境界の代表1件で、Fのhash/pathバリエーションを増やさない。
- [ ] RED: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter FullyQualifiedName~PluginRecipeTests --nologo`。新API未実装で失敗を確認。
- [ ] 最小実装: lazy OpenVerified、ordinal修飾名catalog、検証中raw UTF-8 text cache、readonly公開、失敗/Disposeでlease解放。F API/manifestを変更しない。
- [ ] GREEN: 同じfocused test。`git diff --check`。Expected: 全成功、既存Catalog差分なし。
- [ ] 明示stage、commit `feat: add project-scoped verified plugin recipe resolver`。

### Task 2: 主入力固定の compiler と統合検証

**Files:** 変更 `src/RLoop.Core/ApplyDocumentCompiler.cs`、`tests/RLoop.Tests/PluginRecipeTests.cs`。Task1のinterfacesを消費。ApplyWorkflowを変更しない。

**Produces:** 既存 `Compile(string path)` と追加 `Compile(string path, string resoloopVersion, PluginNameReservations reservations)`。Contextがmain path/factoryを保持してDispose。レシピ展開はUixRecipes overloadでmetadata/textを解決し、修飾名だけplugin key baseを生成する。

テスト要否: S のproject/key取り違え・誤成功・lease漏れ・既存利用破損の代表例。CLIのversion仕様は実コマンドで確かめ固定値テストを追加しない。

- [ ] `MainInputWinsOverIncludeAndWorkingDirectory` を先に書く。2worldの同名pluginのJSON内容を別値とし、mainが他worldのincludeを使用、cwdも他world。明示版Compileはmainの値/固定仕様keyに一致し、再Compileも同一結果。cwd変更が必要なら既存非並列test collectionを使用し必ずfinallyで復旧する。
- [ ] `MissingPluginAndFailedExpansionReleaseLease` を先に書く。正しく使える例の後に未導入名/parameter不正を拒否し、同プロジェクトの次の正常Compile成功。未導入をbuiltin/bare名で代用しない。
- [ ] `BuiltinsDoNotRequireAProjectOrHealthyPlugins` を先に書く。組み込みbuttonの既存キーがproject無しとmodified plugin projectで一致する。既存UixRecipeTestsの大半と重複させず、遅延resolver境界だけ確認。
- [ ] RED: focused PluginRecipeTests実行、既存compilerの名前解決/キーが期待と異なり失敗することを観測。
- [ ] 最小実装: `CompileCore`で固定main path、using Contextとfactory。default host版はCLI entry assembly名resoloopから取得し、不明ならfail closed。明示版overloadはtest/library用。組み込み時はversion/projectを解決しない。
- [ ] GREEN: focused testsと既存UixRecipeTests、`git diff --check`。実CLI offline validate用fixtureをsession内に独立構成して成功とmodified/missing拒否を確かめる。ライブopt-in/URLはchild環境から除去する。
- [ ] 明示stage、commit `feat: compile plugin recipes in the main input project`。
- [ ] controllerが `dotnet build ResoLoop.slnx --nologo`、`dotnet test ResoLoop.slnx --nologo` を同期実行し全ログ/終了コードを確認。最後のcommit後のHEAD/clean status/argv/exit/log/code baseをchecks記録に保存する。public Windows CIはPR後のfinalizeが確認する。
- [ ] 捕捉baseからの全差分、Spec/Plan/同じ受け入れ基準/ledgerを独立全体レビューへ渡す。Review scope branch、upstream reviewer templateを必ず含める。Important/Criticalは1回のfix passでRED→GREEN、minorは記録する。
- [ ] draft文書に実測の記録を追記しcommit。所有/Issue競合/baseを再確認し全worktreeをscan、検査したSHAだけpush、コード/文書PRを作成・相互リンク・実base/head照合。
- [ ] 指定inspect4担当・既定3cycleでloopを回す。ループ中はfeature worktreeを独断変更しない。handoff pair/manifestを公開し遠隔復元検証、Issueへ実状態・PR・残るCLI結線を記録後、自分のclaimだけ解放する。親ボードや子のcloseは調整役に残す。

## 停止・未実行の記録（2026-10-30）

状態 `draft` / planning: blocked / implementation: not-started。Spec builder checkを反映してPlanを書き終えた後、実装前のbase再確認がexit2。捕捉 `dd0b40fb216b0c9fbd82da44903195a885104015` → 観測 `454b54cd961e078dac2a71fe1270529ebff11cd2`（resoloop#27 merge）。Task1/2の実装・新テスト・CLI smoke・全体レビュー・scan/push/PR/loopはすべて未実行。SDD ledgerは未作成（作成ブロックはbase再確認で止まった）。

旧baseのbaseline `dotnet test ResoLoop.slnx --nologo` は終了0、573unit+22offline成功。ログ `/workspaces/reso-world/tmp/agents/issue-100.yvd477qx/baseline-tests.log`。新baseのテスト成功を意味しない。移動差分は同sessionの `base-movement.diff` / `base-movement-stat.txt`。計画のTask完了は一つも記録しない。

再開時は利用者の明示継続許可後に現在のref/競合/新規claimを確認し、既存文書・未変更code worktreeを再利用する手順と新baseを確定する。旧runの捕捉JSONを書き換えて再開しない。新base全体のbaseline、共有資源との整合確認、必要なSpec/Plan再照合を行ってからTask1へ進む。

## 自己照合

Spec全条件は上記表に対応。型名/シグネチャを照合しTask2はTask1のAPIのみ利用。共有条件はmain path・package snapshot・lease lifetime・host versionでcontrollerが統合確認する。恒久テストはSのみ。F/Lはbuild/既存検査/実CLI/差分で代える。現時点で実装・新テスト・公開・マージは未実行。
