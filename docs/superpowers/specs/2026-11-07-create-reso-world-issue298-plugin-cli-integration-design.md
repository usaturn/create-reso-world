# Issue #298 プラグイン 4 機能の CLI 統合 設計

## 管理・実行許可

- 状態: `draft`（コミットしただけで `approved` にしない）
- 対象 Issue: usaturn/create-reso-world#298（実装対象 `usaturn/resoloop`、base `feat/plugin-v2`）
- 親: create-reso-world#95。設計の定義元は `2026-10-29-create-reso-world-issue95-plugin-replan-design.md` の D-1〜D-6
- 実行許可: 利用者の指示 `/issue-to-pr #298 --base feat/plugin-v2 --merge`（実装・push・PR 作成・PR 修正ループ・`finalize.py` によるマージ）。内容の承認ではない
- 先行の取り込み: #98（resoloop PR #29）、#99（PR #27）、#100（PR #28）がいずれも `feat/plugin-v2`（`d76c7baa`）に取り込み済み
- コード base: `usaturn/resoloop` `feat/plugin-v2` @ `d76c7baabac6441ecbb67fcbc8d4027515accfc5`

## 1. 目的と現状

プラグインの管理 API（F）、コマンド実行・doctor・名前 catalog（#98）、スキル配布（#99）、UIX レシピ resolver（#100）は Core と CLI の補助クラスに実装済みだが、`Program.cs` から呼ばれていない。この Issue で次を結線し、4 機能を一時プロジェクトで通す。

| 機能 | 結線前の状態 |
| --- | --- |
| install / list / remove | `plugin` コマンドが無い（`BuiltinCommandCatalog` には予約済み） |
| 外部コマンド | `PluginCommandDispatch.Parse/RunAsync` が未接続。未知名は ResoniteLink へ接続してから `UNKNOWN_COMMAND` |
| init / skills sync | 引数なしの旧オーバーロードを使い、プラグインのスキルを配らない |
| UIX レシピ | `uix recipe` が組み込みの `UixRecipes.Catalog` だけを見る |
| doctor | `PluginDoctorChecks` が未接続 |

`$recipe` を含む宣言ファイル（`apply` / `plan` / `validate` / `test` など）は、`ApplyDocumentCompiler.Compile(path)` の既定オーバーロードが CLI ホストでプロジェクトの resolver を選ぶため、この Issue での変更は不要である（確認は検証で行う）。

## 2. 範囲と禁止

変えてよいもの（Issue 本文の所有範囲）: `src/RLoop.Cli/Program.cs`、`src/RLoop.Cli/CommandLine.cs`（必要な場合のみ）、`src/RLoop.Cli/PluginManagementCommands.cs`（新設）、`tests/RLoop.Tests/PluginCliIntegrationTests.cs`、`tests/fixtures/plugins/integration/`。

変えないもの: 先行の API（`RLoop.Core/Plugins/*`、`PluginCommandDispatch`、`PluginDoctorChecks`、`BuiltinCommandCatalog`、`UixRecipes`、`BundledSkillManager`、`ProjectInitializer`）の無断変更、F・#98・#99・#100 の所有ファイル、旧 fork 専用機能、fork `main` の reset・force push・削除。記載外の編集が必要になったら停止して報告する。

## 3. 決定記録

| # | 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任・停止条件 |
| --- | --- | --- | --- | --- | --- |
| 1 | プラグイン呼び出しの分離位置 | `Main` の先頭で、`ParsedArguments.Parse` より前に `PluginCommandDispatch.Parse(args)` を呼ぶ。非 null ならプラグインの経路だけで終了する | パース後の `Positionals` から復元する | 既存パーサは `--`・空文字・未知オプションの値を壊すため、生 argv を保てない（D-4） | 仕様変更になる場合は停止 |
| 2 | プラグイン経路の出力 | ホストのエラーは `OutputWriter(json: false)` で stderr に出す。子の stdout/stderr は転送のまま、終了コードは子のものを返す | `--json` をホストが解釈する | コマンド名より後ろの `--json` はプラグインのもの（D-4）。コマンド前の `--project` だけがホストの指定 | なし |
| 3 | `plugin` 管理コマンド | `PluginManagementCommands`（新設）に `install SOURCE [--ref REF]`・`list`・`remove NAME --yes` を置き、`init`・`skills` と同じく ResoniteLink 設定の解決より前に処理する。対象は `--project DIR` か cwd からの探索 | `Program.cs` に直接書く | Program.cs の肥大を避け、所有範囲（新設ファイル）に合う | 既存の `CONFIRMATION_REQUIRED` を迂回する暗黙の確認はしない |
| 4 | 予約名の共有 | 導入・実行・doctor・init/sync・`uix recipe` のすべてで `ProductVersion()` と `BuiltinCommandCatalog.Reservations` を渡す | 各所で独自の予約を作る | 導入時と実行時で判定が食い違うのを防ぐ（D-4） | なし |
| 5 | init / skills sync | 版と予約を取る既存オーバーロードに切り替える | 旧オーバーロードのまま | プラグイン無しの結果は同一であることを #99 が保証する | プラグイン無しの出力が変わるなら停止 |
| 6 | `uix recipe` | `list` と `プラグイン名:レシピ名` の `describe`/`export` だけ resolver を開く。組み込み名の `describe`/`export` は resolver を開かない。プロジェクトが見つからず `--project` 未指定のときは組み込みだけで動く | 常に resolver を開く | 壊れたプラグインがあっても組み込みレシピの利用を止めない（D-6「プロジェクトを参照しない既存の組み込みレシピ利用は維持」） | なし |
| 7 | doctor | 既存のチェックの後ろに `PluginDoctorChecks.RunAsync` の結果を足す。必須判定（`Ready`）は既存の式のまま | プラグイン用の別コマンド | プラグイン無しなら結果が空で、doctor は変わらない（D-4） | なし |
| 8 | `$recipe` の経路 | 変更しない | `ApplyDocument.Load` に予約を渡す | Core の変更は所有範囲外。CLI ホストでは既定オーバーロードが正しく解決することを統合テストで確かめる | 解決できないと分かったら停止して親へ報告 |
| 9 | ヘルプ | `PrintHelp` に `plugin` の節とプラグイン呼び出しの構文を足す | 文書だけ | 組み込みの構文・出力を維持しつつ利用者が到達できるようにする | なし |
| 10 | ループ・担当 | `--merge` のループ用オプションは利用者の指定なし（既定: サイクル上限 3、レビューと修正の担当は agent-runner 設定）。Plan の実装担当は `self`（雛形の既定の適用） | — | `check-options`・`implement_task.py check` の出力どおり | — |

## 4. 受け入れ条件

D-1〜D-6 と 4 機能を一時プロジェクト・偽の外部プログラムで統合確認する。

- **動作環境:** 本 Dev Container（Linux、`global.json` の .NET 10 SDK）。Windows は対象だが未実行であり、確認済みと報告しない。Resonite・Blender・認証情報は使わない。
- **実入力:** 実際の CLI（`dotnet resoloop.dll`）の子プロセスに、日本語・空白を含むプロジェクトパス、`--json`・`--help`・`--`・空文字・非 ASCII を含む引数を渡す。
- **防御範囲:**
  - コマンド前の `--project` は cwd より優先され、別プロジェクトの同名コマンドを選ばない。コマンド名より後ろの全トークンは順序・値を変えずにプラグインへ渡り、子の終了コードが保たれる。
  - 未登録名は ResoniteLink へ接続する前に `UNKNOWN_COMMAND`（終了コード `InvalidArguments`）で止まる（待ち受けているソケットへ接続が来ない）。
  - `plugin remove` は `--yes` が無ければ何も消さない。`--yes` 付きでは対象だけが消える。
  - 対象外: 組み込みコマンドの構文・出力の変更、悪意ある同一ユーザへの完全な防御、署名・サンドボックス、実 Resonite・実 Blender、Windows の実行確認。
- **重複しない守り:** #98 の生 argv・失敗判定、#99 の記録・競合、#100 の主入力解決は各モジュールのテストの責任である。結線のテストはそれを繰り返さず、結線の取り違え（別の経路・別の予約・別のプロジェクト）が起きないことだけを確かめる。

## 5. 検証

`external/resoloop/.worktrees/create-reso-world-issue-298-cli-integration` で `dotnet build ResoLoop.slnx` と `dotnet test ResoLoop.slnx --no-build`。結線の確認として `dotnet run --project src/RLoop.Cli -- help` と、一時プロジェクトでの手動の通し（Plan の Task 4）を行う。

## 6. 持ち越し

マージの後でなければ確かめられない項目: 上流の公開版への取り込み、Windows の実行、親 #95 のボード更新と #110〜#112 の close 判断（親の調整役が行う）。
