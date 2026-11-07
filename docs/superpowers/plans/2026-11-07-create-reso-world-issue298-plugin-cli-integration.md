# Issue #298 プラグイン 4 機能の CLI 統合 Plan

- 状態: `draft`（実行許可: `/issue-to-pr #298 --base feat/plugin-v2 --merge`。内容の承認ではない）
- Spec: `docs/superpowers/specs/2026-11-07-create-reso-world-issue298-plugin-cli-integration-design.md`
- コード対象: `usaturn/resoloop` の `feat/create-reso-world-issue-298-cli-integration`（base `feat/plugin-v2` @ `d76c7baa`）。パスは `external/resoloop/.worktrees/create-reso-world-issue-298-cli-integration`（以下 root）
- 実行方式: inline（`superpowers:executing-plans`）。理由: 変更の中心が `Program.cs` 1 ファイルの逐次変更で、Task が同じファイルを触り、並列・委譲の利点が無い。担当は agent-runner 設定の既定 `self`
- 検証の入口: root で `dotnet build ResoLoop.slnx` → `dotnet test ResoLoop.slnx --no-build`（`AGENTS.md` の Commands）。Linux の Dev Container、`global.json` の .NET を使う

## 受け入れ基準

Spec の「4. 受け入れ条件」と同じ内容を再掲する。

- **動作環境:** 本 Dev Container（Linux、.NET 10）。Windows は未実行で、確認済みと報告しない。Resonite・Blender・認証情報は使わない。
- **実入力:** 実 CLI（`dotnet resoloop.dll`）の子プロセスに、`作業 ワールド` のような日本語・空白を含むプロジェクトパスと、`--json`・`--help`・`--`・空文字・`日本語 引数` を含む引数を渡す。
- **防御範囲:** (1) コマンド前の `--project` が cwd より優先され、別プロジェクトの同名コマンドを選ばない。コマンド名より後ろのトークンは順序・値を変えずプラグインへ渡り、子の終了コードが保たれる。(2) 未登録名は ResoniteLink へ接続する前に `UNKNOWN_COMMAND`（`ExitCodes.InvalidArguments`）で止まる。(3) `plugin remove` は `--yes` が無ければ何も消さず、`--yes` 付きで対象だけが消える。対象外: 組み込みコマンドの構文・出力の変更、悪意ある同一ユーザへの防御、実 Resonite・実 Blender、Windows の実行。

## 実行予算

- Issue 全体の能動時間: 3 時間。phase の目安: 実装 60 分、テスト 45 分、検証 30 分、PR 作成 15 分、ループ（サイクル上限 3 ×（レビュー 45 分＋計画・修正））
- worker の期限: なし（inline）。`dotnet build`/`test` は 1 回 20 分を上限にし、無出力が 10 分続けば打ち切る
- 再試行の上限: ビルド・テストの失敗は原因調査を挟んで 2 回まで。2 回で解消しなければ止まる
- checkpoint: Task 2 の後（Program.cs の結線完了）と Task 3 の後（統合テスト通過）。超過時は縮小（テストを 2 本へ）または文書更新の切り出しを候補にする

## contingency（代替策）

- 最初の RED で実出力・API の前提が異なれば、Spec の意味を保つ最小修正を ledger に残して継続する。意味が変わる場合は停止して報告する
- 実 CLI の子プロセス起動が使えない（`resoloop.dll` がテスト出力に無い）場合は、`Program.Main` をプロセス内で呼ぶ形に切り替える。ただしその場合 `$recipe` の解決（ホストが `resoloop` でない）は確認できないので、Task 4 の手動の通しで補う
- `Program.cs` 以外の編集が必要と分かったら、所有範囲外のため停止して親 #95 に報告する

## Task 1: プラグイン呼び出しの分離と `plugin` 管理コマンド

- 担当ファイル: `src/RLoop.Cli/Program.cs`、`src/RLoop.Cli/PluginManagementCommands.cs`（新設）
- 内容: `Main` の先頭で `PluginCommandDispatch.Parse(args)`。非 null なら `PluginCommandDispatch.RunAsync(invocation, PluginDispatchContext.Current(ProductVersion()), token)` を実行し、`RLoopException` は `OutputWriter(false)` で stderr へ出して `ExitCode` を返し、キャンセルは `CANCELLED`、その他は `UNEXPECTED_ERROR`。`init`・`skills` と同じ位置に `plugin` を追加し、`PluginManagementCommands.Run` が `install SOURCE [--ref REF]`・`list`・`remove NAME --yes` を処理する（`--project DIR` か cwd 探索、`ProductVersion()` と `BuiltinCommandCatalog.Reservations`）。`UnknownCommand` を `internal` にして共有する
- テスト: Task 3 の統合テストで確かめる。単独のテストは書かない（オプション解析・メッセージは L）
- 代わりの検証: `dotnet build` が通ること

## Task 2: init・skills sync・uix recipe・doctor・help の結線

- 担当ファイル: `src/RLoop.Cli/Program.cs`
- 内容: `ProjectInitializer.Initialize(target, ProductVersion(), BuiltinCommandCatalog.Reservations)`、`BundledSkillManager.Sync(target, update, ProductVersion(), reservations)`。`RunUixRecipe` は、`list` と `:` を含む名前の `describe`/`export` のときだけ `PluginRecipeResolver` を開く（`--project` 指定か cwd 探索。見つからず未指定なら組み込みのみ）。`RunDoctor` の末尾（`report` の前）で `PluginDoctorChecks.RunAsync(args.Option("project"), Environment.CurrentDirectory, ProductVersion(), env, ct)` の結果を `checks` に足す。`PrintHelp` に `plugin` の節とプラグイン呼び出しの構文を足す
- テスト: Task 3 で確かめる（プラグイン無しの出力は #99/#98 が保証済みなので重複して書かない）
- 代わりの検証: `dotnet build`、`dotnet run --project src/RLoop.Cli -- help`、プラグイン無しの一時ディレクトリで `init` と `skills sync --check` の出力が変わらないことを手動で比較

## Task 3: 統合テスト（S のみ）

- 担当ファイル: `tests/RLoop.Tests/PluginCliIntegrationTests.cs`、`tests/fixtures/plugins/integration/`
- テスト要否: 必要（S）。壊れてもエラーにならず、別プロジェクトのコマンド・別経路の実行や、確認なしの削除、接続の先行が起きうる。次の 3 件だけを書く
  1. 4 機能の通し（実 CLI）: `plugin install` → `plugin list` → コマンドの生 argv と子の終了コード → `init`/`skills sync --update` でスキル配布 → `uix recipe describe プラグイン名:レシピ名` → `doctor` のツール検査（偽の必須ツール欠落で必須判定が落ちる）→ `plugin remove`（`--yes` 無しは削除されず、あり は削除）
  2. `--project` が cwd のプロジェクトより優先される（別プロジェクトの同名コマンドは実行されない）。正しく通る例も同じテストに含める
  3. 未登録名は待ち受けソケットへ接続せず `UNKNOWN_COMMAND` で終わる（`RESONITE_LINK_URL` に待ち受け中のポートを指定し、接続数 0 を確かめる）
- フィクスチャ: `tests/fixtures/plugins/integration/` に manifest・スキル・レシピのひな形。偽の外部プログラムは既存の `CommandProbe`（`CommandProbeFixture`）を再利用する
- 実装前に RED を確認する（Task 1・2 が未実装の状態では 3 件とも失敗する）。変異確認: 結線を 1 つ外すと対応するテストが落ちること

## Task 4: 統合確認と検証の記録

- `dotnet build ResoLoop.slnx` と `dotnet test ResoLoop.slnx --no-build` の全体、一時プロジェクトでの手動の通し（`$recipe` を含む宣言ファイルを `validate` する経路は ResoniteLink 接続が要るため、`ApplyDocumentCompiler` の解決は統合テスト 1 の `uix` と #100 のテストで代える。未実行の確認は成功と書かない）
- `git status --porcelain` が空であること、検証した HEAD・argv・終了コード・ログのパスを `tmp/agents/issue-298.*/` に記録し、`finalize.py` の `--checks-file` 形式のファイルも作る
- Spec の各条件と Task・実行証拠を条件単位で照合する

## 持ち越し

README/README-DETAILS の更新は所有範囲外のため含めない。Windows の実行、上流公開版への取り込み、親 #95 のボード更新は PR 本文に残す。
