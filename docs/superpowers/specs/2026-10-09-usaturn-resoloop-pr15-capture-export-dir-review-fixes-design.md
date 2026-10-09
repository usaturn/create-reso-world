# usaturn/resoloop PR #15: capture の書き出し先の早期停止のレビュー修正要否

- 文書管理リポジトリ: `usaturn/create-reso-world`（文書用ブランチ `feat/resoloop-13-screenshot-mount`、PR #62。同じテーマの Spec・Plan を載せている PR）
- 対象リポジトリ・PR: https://github.com/usaturn/resoloop/pull/15（`fix/issue-13-capture-export-dir` → `main`）
- 関連 Issue: usaturn/resoloop#13（PR 本文で Refs。実機での撮影の確認が残るため自動 close なし）。関連: #12（ホストのパスの対応付け）
- 関連文書: `docs/superpowers/specs/2026-10-09-usaturn-resoloop-issue-13-capture-export-dir-design.md`、`docs/superpowers/plans/2026-10-09-usaturn-resoloop-issue-13-capture-export-dir.md`
- 検証したコード HEAD: `9e43c95c5ed83455ef02c43d8dc5abd810b524fa`（base `main` = `9cf7178f02a696cd91ae5fb092b9078e98f25beb` は head の祖先）
- 状態: completed
- 実行許可: 利用者が `/review-fix-planning https://github.com/usaturn/resoloop/pull/15` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要としてマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/resoloop-13-screenshots`（設計 Spec が DOC_ROOT として指定した既存の worktree を、clean・origin 一致の条件で再利用）
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-13-capture-export-dir`（PR head を checkout 済みの既存 worktree を、clean・HEAD 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`external/resoloop/reviews/#15-fix-issue-13-capture-export-dir/` の 4 ファイル。対象 HEAD はすべて `9e43c95c5ed8` で、`pull/15/head` の取得結果と一致する。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `Grok-4.7.md` | Approve | なし（Summary に範囲外の付記 1） |
| `SWE-2-High.md` | Approve | Info 1（Test suggestions 2） |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | Approve | Low 1 |
| `openai-codex-gpt-6.1-sol.md` | Approve | なし |

## 分類

| ID | 出どころ | 指摘 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | SWE I-1 | `LiveCaptureService.CaptureAsync` に追加した省略可能引数 `screenshotDirectorySource` が `cancellationToken` の後ろにある | 対応しない。現行 HEAD で確認した（`src/RLoop.Core/LiveCaptureService.cs:14`）。引数の並びの慣例の問題で、唯一の CLI の呼出元（`src/RLoop.Cli/Program.cs:220-221`）は位置引数で正しく渡している。他の呼出元（`LiveCaptureWorkflowTests`、統合テスト 6 件）は named 引数か既定値で、ビルドが通る（下の検証） |
| R2 | DeepSeek L-1、SWE の Test suggestions 1・2 | Plan の Task 2 の 3 テスト（`TimeoutReports*`・`MissingParentReports*`）と、Task 1 のテストの `context` の検査が無い | 対応しない。現行 HEAD で確認した（`tests/` に該当のテスト名・キーの検査は無い）。テストの欠落で、挙動の誤りではない（`context` の各値は DeepSeek・Codex が最小再現で確かめ、下の CLI の再現でも確かめた）。加えて、Plan の「実行中の変更」に、ユーザーの指示（AGENTS.md「テストの採用基準」）で Task 1 の `context` の検査と Task 2 の 3 本をやめたと記録され、該当の Step も「ユーザー指示で省略」になっている。レビューの「承認済み Plan が定めた」は、この省略の記録を見落としている |
| R3 | Grok（Summary の付記。指摘としては挙げていない） | `~/Pictures` はあるが Resonite の書き出し先ではない環境では、従来どおり `~/Pictures/Resonite` を監視し、接続後に `CAPTURE_EXPORT_TIMEOUT` になり得る | 対応しない。PR が止めるのは「保存先の指定が無く、Pictures 既知フォルダも取得できない」場合だけで、PR 本文と `README-DETAILS.md` の追記もこの条件で書いている。別の PC・コンテナ外の Resonite では、写真フォルダをマウントして保存先を指定するよう同じ段落で案内している。CLI からはそのフォルダが Resonite の書き出し先かを判定できず、ホストのパスの対応付けは PR 本文で #12 に残している |

Codex は指摘なし。

分類: **解消済み 0 / 対応する 0 / 対応しない 3**。

仕様の論点として残すもの: R3（`~/Pictures` があっても Resonite が別のホストで動くことを検出するか。#12 のパスの対応付けと合わせて扱う）。

## 確認の範囲

- 変更ファイル 7 件の全文: `ScreenshotDirectoryResolver.cs`・`ScreenshotExport.cs`・`LiveCaptureService.cs`、`Program.cs` の capture の分岐（179〜224 行）、`CaptureTests.cs`、`README-DETAILS.md` の段落、同梱の `resonite-build` の `SKILL.md` の手順 9
- 関連処理: `ScreenshotDirectoryResolver.ResolveDefault` の全呼出元（CLI の capture と、live の統合テスト 5 件。`doctor` などからは呼ばれない）、`ScreenshotExport` の生成元（`LiveCaptureService`・`CaptureTests`）、`CaptureAsync` の全呼出元、`ConfigResolver.Pick` と `Sources` のキー（`screenshotsDirectory`）、`RLoopException` の引数と `ExitCodes`（`ConfigurationError` = 3）
- 接続前に止まること: `Program.cs` で `ResolveDefault` が `ConnectAsync` より前にあり、保存先の指定があるときは `ResolveDefault` を呼ばない
- Windows: Pictures 既知フォルダは通常取得できるため、`primary` と OneDrive の候補の選び方は変更前と同じになる
- 自己確認で、PR が持ち込んだ致命的な欠陥は見つからなかった

## 検証

PR head を checkout した専用の worktree（CODE_ROOT。HEAD `9e43c95`、未コミットの変更なし）で実行した。ビルド出力（`bin/`・`obj/`）は `.gitignore` の対象で、実行後も `git status --porcelain` は空だった。

| コマンド | 結果 |
| --- | --- |
| `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` | 454 passed、skip 0（exit 0） |
| `dotnet test tests/RLoop.IntegrationTests/RLoop.IntegrationTests.csproj`（live の設定なし） | 19 passed、skip 0（exit 0）。`CaptureAsync`・`ResolveDefault` を呼ぶ統合テストのビルドも通る |
| ビルド済みの CLI で `capture examples/capture.json --camera main --output out.png --url ws://localhost:1/ --json`（`~/Pictures` 無し、`RESOLOOP_SCREENSHOTS_DIR` 無し、user・project の設定なし、空の一時 cwd） | `CAPTURE_EXPORT_DIR_UNREACHABLE`、exit 3、279 ms。`context` は `picturesFolder: ""`・`candidates: []`・`oneDriveCandidatesChecked: false`、`suggestions` 2 件。cwd に `Resonite` も出力も作らない |
| 上と同じコマンドに `RESOLOOP_SCREENSHOTS_DIR=<一時 cwd>` | 既定の解決を通らず `CONNECTION_FAILED`（接続先が無いため） |

`dotnet test` の 1 回目は `--artifacts-path` を worktree 外に置いたため、`ApplyWorkflowTests` の 2 件（`HouseFixtureHasBoundedRequestsAndZeroWriteSecondRun`・`HouseMirrorFixtureVerifiesWiringAndReportsUnavailableProbeAsStructuralOnly`）が失敗した（452 passed）。2 件は `AppContext.BaseDirectory` の 5 階層上を repository のルートとして `examples/house-world.json` を読むため、出力先を移すと `/tmp/examples/...` を探す。検証方法の問題で、PR の変更とは関係しない。上の表は出力先を既定に戻した再実行の結果である。

公開 CI: run 37904204687 がこの head で `linux-offline-python`（45 秒）・`windows`（3 分 50 秒）とも成功（`gh pr checks 15 --repo usaturn/resoloop`）。base `main` は head の祖先なので、base を merge した一時ツリーでの再検証は不要。

## 自己レビュー

未実施。結論 2 で修正が無いため、修正後の自己レビューの対象が無い。

## PR 本文に書き足すこと

無い。「対応しない」のうち実在する制約（R3）は、PR 本文の保証（Pictures 既知フォルダが取得できないときに接続前に止まる）と食い違わない。

## 作業時間

- 着手 2026-10-09T08:40Z、Spec の完成 2026-10-09T08:47Z（約 7 分）。内訳: レビューの読込と PR の状態・境界の確認・worktree の選定（約 2 分）、変更ファイルと呼出元の精読・Plan の記録の確認（約 2 分）、テストと CLI の再現（約 3 分、出力先の誤りによる再実行を含む。Spec の作成と並行）
