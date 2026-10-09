# usaturn/resoloop PR #16: hostPathMap のレビュー修正要否

- 文書管理リポジトリ: `usaturn/create-reso-world`（文書用ブランチ `docs/resoloop-12-host-path-map`。同じテーマの文書 PR #64 はマージ済みで、open の文書専用 PR は無い）
- 対象リポジトリ・PR: https://github.com/usaturn/resoloop/pull/16（`fix/issue-12-host-path-map` → `main`）
- 関連 Issue: usaturn/resoloop#12（PR 本文の `Fixes #12`。`closingIssuesReferences` に含まれる）
- 関連文書: `docs/superpowers/specs/2026-10-09-usaturn-resoloop-issue-12-host-path-map-design.md`、`docs/superpowers/plans/2026-10-09-usaturn-resoloop-issue-12-host-path-map.md`
- 検証したコード HEAD: `709d57d1bab799fce42595cf83df4ceaf592a517`（base `main` = `4c703659b0f20096faa5f8e85189a1feaceb9bf1` は head の祖先）
- 状態: completed
- 実行許可: 利用者が `/review-fix-planning https://github.com/usaturn/resoloop/pull/16` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要としてマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/resoloop-12-host-path-map-docs`（同じテーマの既存の文書用ブランチの worktree を、clean の条件で再利用）
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-12-host-path-map`（PR head を checkout 済みの既存 worktree を、clean・HEAD 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`external/resoloop/reviews/#16-fix-issue-12-host-path-map/` の 3 ファイル。対象 HEAD はすべて `709d57d1bab7` で、`pull/16/head` の取得結果と一致する。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `claude-opus-5-5.md` | Approve | Low 1 |
| `Grok-4.7.md` | Approve | なし |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | Approve | Low 2、Info 3 |

## 分類

| ID | 出どころ | 指摘 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | Opus L-1、DeepSeek L-2（両者の Test suggestions を含む） | `WorldService` 側の新しい分岐（置き換えたパスをアダプターへ渡すこと、`ASSET_HOST_PATH_UNREACHABLE` への変換、`REQUEST_TIMEOUT` への context とヒントの追加、plan の `ASSET_HOST_PATH_UNMAPPED`）にオフラインテストが無い | 対応しない。現行 HEAD で確認した（`tests/` で `ASSET_HOST_PATH`・`HostSource`・`HostPathMap` を参照するのは `HostPathMapTests.cs` だけ。`FakeResoniteClient.ImportAssetAsync`（`tests/RLoop.Tests/ApplyWorkflowTests.cs:1623-1627`）は渡されたパスを記録しない）。テストの欠落で、挙動の誤りではない。各分岐は下の「確認の範囲」のコード精読で確かめた。PR 本文の実機検証（置き換えありの apply の成功と、次の plan で asset が `no-op`、置き換えなしの `REQUEST_TIMEOUT` と context、`--timeout 90` での `ASSET_HOST_PATH_UNREACHABLE`、plan の警告）にも記録がある |
| R2 | DeepSeek L-1 | `FROM` の検証と照合が CLI の OS に依存する。Windows の CLI では POSIX の `FROM` が `INVALID_HOST_PATH_MAP` になり接続コマンドが止まる。`C:/...` と書いた `FROM` は一致せず、置き換えも警告も無い | 対応しない。`src/RLoop.Core/HostPathMap.cs:23`（`Path.IsPathFullyQualified`）と `:44-51`（`StartsWith`）で記載どおりの挙動を確認した。どちらも PR 本文の既知の制限（1・2 件目）に、条件と回避方法（機械ごとの値は `RESOLOOP_HOST_PATH_MAP` か user 設定に置く）が書かれている。前者は接続前に止まり、エラーが設定元（`source`）を示すので、誤った結果は残らない。後者は置き換えが無い従来の挙動と同じで、失敗すると `context.hostPath` に置き換え前のパスが出る。CLI と Resonite が同じ Windows の PC にあるなら置き換え自体が不要である。どこで正規化・検証するかは設計の選択 |
| R3 | DeepSeek I-1 | `HostPathMap.Source` を読む箇所が無い | 対応しない。確認した（`src/` に `HostPathMap` の `Source` を読む箇所は無い）。未使用のプロパティで、挙動に影響しない |
| R4 | DeepSeek I-2 | 同梱の `resonite-blender` の `SKILL.md` が、apply のエラー `ASSET_HOST_PATH_UNREACHABLE` を plan の警告と並べて書いている | 対応しない。確認した（`skills/codex/resonite-blender/SKILL.md:90`）。指示される行動（同じ apply を繰り返さず、利用者に対応付けを尋ねる）は 2 つのコードで同じで、読み違えても誤った操作にならない |
| R5 | DeepSeek I-3 | CLI の help の `--host-path-map` の例がシェル向けに引用されていない | 対応しない。確認した（`src/RLoop.Cli/Program.cs:1162-1163`。bash で引用せずに渡すと `\\wsl.localhost\Gentoo\...` が `\wsl.localhostGentoo...` になる）。PR 本文の既知の制限（3 件目）に挙がっている。help の例は `DISTRO`・`USER` を含む書式の例で、README-DETAILS の JSON の例は正しい。崩れた値で apply すると、Slot・Component を作る・変える処理（`WorldService.cs:443` 以降）より前の asset の import で `REQUEST_TIMEOUT` か `ASSET_HOST_PATH_UNREACHABLE` になり、`context.hostPath`・`hostPathMap` に崩れた値が出る。world に誤った変更を残さずに原因が分かる |

Grok は指摘なし。Opus が「既出のため指摘しなかった事項」とした 4 件（PR 本文の既知の制限）は指摘として扱わない。R2・R5 はそのうち 2 件を DeepSeek が指摘として挙げたもの。

分類: **解消済み 0 / 対応する 0 / 対応しない 5**。

仕様の論点として残すもの:

- R1: resoloop の `AGENTS.md`「Tests and Skills」は error codes のオフラインテストの維持を求めている。`WorldService` の新しい分岐のテストを足すかは、致命的な指摘の修正とは別の作業として扱う
- R2: `FROM` を正規化するか、その OS で解釈できない `FROM` を接続コマンド全体で止めずに扱うか

## 確認の範囲

- 変更ファイル: `HostPathMap.cs`・`HostPathMapTests.cs`・`Configuration.cs` は全文。`WorldService.cs` は変更した hunk のすべてと、`PlanApplyAsync`・`ApplyAsync`（外側の catch を含む 386〜708 行）・`BuildAssetPlans`・新設の `UnmappedHostPathWarnings`・`ImportAssetAsync`・`HostPathSuggestions`・`AssetRuntime`。`Program.cs` は設定の解決から接続まで（95〜235 行）、plan/diff・apply の分岐（527〜563 行）、flux の `WorldService` の生成箇所（875・960 行）、help。README-DETAILS・`docs/BLENDER.md`・`docs/DECLARATIVE.md`・`resonite-blender` の `SKILL.md` は差分。`WorldService.cs`・`Program.cs` のうち、上に挙げていない部分（PR の変更と呼出関係の無い処理）は読んでいない
- import の経路: `client.ImportAssetAsync` の呼出しは `WorldService.cs:1318` の 1 か所だけ。アダプター（`ResoniteLinkClientAdapter.cs:292-305`）が Resonite 側でファイルを開く kind（`texture`・`texture2d`・`audio`・`audioclip`）は `HostPathMap.AppliesTo` と一致し、`mesh` は CLI がファイルを読むので `HostSource` が null になり、置き換えない
- 置き換えが無いとき: `HostSource` は `ResolvedSource` と同じになり、アダプターへ渡るパスは変更前と同じ
- hash と state: hash は CLI 側のパス（`resolved`）から計算し、state に保存するのは kind・hash・URL だけ（`WorldService.cs:435`）。置き換え後のパスは保存しない
- 例外: `RLoopException.Context` は null にならない（`Errors.cs:17`）。`ImportAssetAsync` はアダプターの context（`kind`・`source`）を引き継いで `asset`・`kind`・`source`・`hostPath`・`hostPathMap` を上書き・追加し、`ApplyAsync` の外側の catch がさらに引き継ぐ。`RLoopException` 以外（取消しなど）はそのまま外へ出る
- plan の警告: 表示されるだけで、strict でも apply でも止めない（`Program.cs:537-561`。`PlanApplyAsync` の呼出元は CLI の plan/diff と統合テストだけ）
- 設定と引数: `ConfigResolver.Pick` の `sources` のキーは `hostPathMap` で、`Program.cs:229` の参照と一致する。`--name=value` は最初の `=` で分かれ、`host-path-map` は真偽のオプションではないので次の引数を値に取る。`HostPathMap.Parse` は接続コマンドの入口（`Program.cs:229`）にあり、offline のコマンドと capture・flux・doctor の分岐はそれより前に戻る。flux の `WorldService`（875・960 行）は import を呼ばない
- 自己確認で、PR が持ち込んだ致命的な欠陥は見つからなかった

## 検証

PR head を checkout した専用の worktree（CODE_ROOT。HEAD `709d57d`、未コミットの変更なし）で実行した。ビルド出力（`bin/`・`obj/`）は ignore の対象で、実行後も `git status --porcelain` は空だった。

| コマンド | 結果 |
| --- | --- |
| `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` | 456 passed、skip 0（exit 0、85 秒）。ビルドの警告 0 |
| `dotnet test tests/RLoop.IntegrationTests/RLoop.IntegrationTests.csproj`（live の設定なし） | 19 passed、skip 0（exit 0）。`WorldService` を生成する統合テストのビルドも通る |
| bash で `printf '%s\n' /workspaces/repo=\\wsl.localhost\Gentoo\home\usaturn\repo` を引用あり・なしで実行（R5） | 引用なしは `\wsl.localhostGentoohomeusaturnrepo`、引用ありは元の値 |

公開 CI: run 37923742478 がこの head で `linux-offline-python`（49 秒）・`windows`（4 分 37 秒）とも成功（`gh pr checks 16 --repo usaturn/resoloop`）。base `main` は head の祖先なので、base を merge した一時ツリーでの再検証は不要。

## 自己レビュー

未実施。結論 2 で修正が無いため、修正後の自己レビューの対象が無い。

## PR 本文に書き足すこと

無い。「対応しない」のうち実在する制約（R2・R5）は、PR 本文の既知の制限に条件と回避方法が書かれており、本文の保証と食い違わない。

## 作業時間

- 着手 2026-10-09T12:12Z 頃、Spec の完成 2026-10-09T12:27Z 頃（約 15 分）。内訳: レビューの読込と PR の状態・境界の確認・worktree の選定（約 3 分）、差分と関連処理の精読（約 6 分）、テスト（約 2 分）、Spec の作成（約 4 分）
