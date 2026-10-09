# usaturn/create-reso-world PR #62: Resonite の写真フォルダのマウントのレビュー修正要否

- 対象リポジトリ・PR: https://github.com/usaturn/create-reso-world/pull/62（`feat/resoloop-13-screenshot-mount` → `main`）
- 関連 Issue: usaturn/resoloop#13（PR 本文で Refs。`closingIssuesReferences` は無い。実機での撮影の確認が残る）
- 関連文書: `docs/superpowers/specs/2026-10-09-usaturn-resoloop-issue-13-capture-export-dir-design.md`、`docs/superpowers/plans/2026-10-09-usaturn-resoloop-issue-13-capture-export-dir.md`、`docs/superpowers/specs/2026-10-09-usaturn-resoloop-pr15-capture-export-dir-review-fixes-design.md`（resoloop PR #15 の修正要否。PR #62 とは別の PR）
- 新しい文書にした理由: 同じテーマの既存のレビュー修正の Spec は resoloop PR #15 が対象で、create-reso-world PR #62 のレビュー修正の Spec は無かった
- 検証したコード HEAD: `4669e4ab638469cd1b53153019417659768fa9fb`（base `main` = `2b260b69fea36e0f2fc2616cf4d8bcf1a9e93b83` は head の祖先）
- 状態: completed
- 実行許可: 利用者が `/review-fix-planning https://github.com/usaturn/create-reso-world/pull/62` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要としてマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/resoloop-13-screenshots`（PR head を checkout 済みの既存の worktree を、未コミットの変更なし・HEAD 一致の条件で再利用。このセッションの片付けの対象ではない）

## 入力

`reviews/#62-feat-resoloop-13-screenshot-mount/` の 4 ファイル。対象 HEAD は `ec9fbfc4ff70` と `4669e4ab6384` の 2 世代で、どちらも `pull/62/head` の祖先である。2 つの間の差分は resoloop PR #15 の修正要否の Spec 1 件だけで、`.devcontainer/` と `.gitignore` は同一である。

| ファイル | 対象 HEAD | 判定 | 指摘 |
| --- | --- | --- | --- |
| `Grok-4.7.md` | `4669e4ab6384` | Approve | Low 2、Info 1 |
| `SWE-2-High.md` | `ec9fbfc4ff70` | Needs manual verification | Info 1 |
| `claude-fable-5-1.md` | `ec9fbfc4ff70` | Approve | Info 1（Test suggestions 1） |
| `deepseek-v4.1-flash.md` | `4669e4ab6384` | Needs manual verification | Low 1、Info 2、Unverified candidates 1 |

## 分類

| ID | 出どころ | 指摘 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | Grok L-1、Fable I-1、DeepSeek I-2 | README は、リンクが無いと `CAPTURE_EXPORT_DIR_UNREACHABLE` で止まると書くが、NuGet の公開版はタイムアウトまで待つ | 対応しない。現行 HEAD で確認した（`.devcontainer/README.md:151-152`。NuGet の最新は `0.1.0-preview.17` で、rebuild で公開版に戻る）。README の手順（リンクを作って rebuild）のとおりに進めた結果は正しく、違うのはリンクが無いときのエラーコードと待ち時間だけである。データ・権限・操作対象に影響しない。PR 本文は「修正版の resoloop では」と条件を付けて書いている |
| R2 | Grok L-2、SWE I-1（前半）、DeepSeek I-1（前半）、Fable の Test suggestions 1 | `initialize.bash` の分岐（空・1 行・リンク削除・リンク先なし）と `CDPATH` の回帰がテストで固定されていない | 対応しない。現行 HEAD で確認した（`test-initialize-mounts.bash` に env ファイルの検査は無い）。テストの欠落で、挙動の誤りではない（下の検証で全分岐が仕様どおり）。Plan の「実行中の変更」に、ユーザーの指示（AGENTS.md「テストの採用基準」、設定を確かめるテストは不要）で検査 3c をやめたと記録されている |
| R3 | Grok I-1 | Plan Task 5 Step 3 のコード片が、`CDPATH` で壊れる `cd` の式のまま | 対応しない。完了した Plan の手順の記録で、実行する処理ではない。実施結果に `d3050ed` で `cd` をやめたことが記録されている。完了した Plan の手順を再実行する使い方は無い |
| R4 | DeepSeek L-1、SWE I-1（後半） | 検査 4 が、読み取り専用のマウントを書き込み可能化の一覧に入れていないことを検査しない。`install_beforehand.bash` の注釈は「ディレクトリの mount はすべてここに並べる」のまま | 対応しない。現行 HEAD で確認した（一覧に入れた変異でも検査 4 は PASS）。現行の一覧には入っておらず、今の構成で誤動作は起きない。将来の変更に対する保険である。誤って足した場合も、postCreate が `Failed to prepare writable directory` で止まり、すぐに分かる |
| R5 | DeepSeek I-1（後半）、Grok L-2（後半） | 設計 Spec のテスト節と Plan Task 5 Step 1（`[x]`）が、省略した検査 3c・検査 4 の否定検査を載せたままで、実装と食い違って読める | 対応しない。記録の書き方の問題で、Plan の「実行中の変更」に省略とその理由が記録されている。挙動・手順の結果に影響しない |
| R6 | DeepSeek の Unverified candidates | シンボリックリンクを source にした読み取り専用の bind mount を、Docker が解決できない可能性 | 対応しない。指摘ではなく未検証の候補である。bind mount の mount(2) は source のシンボリックリンクを解決し、リンク先が無いときは `initialize.bash` が先に止まる。このコンテナに Docker が無く実機では確かめられないが、PR 本文の「未実施」と引き継ぎで、リンク作成と rebuild 後の実機確認として扱っている。失敗してもリンクを作った利用者のコンテナ作成のエラーで、README のとおりリンクを消せば戻る |

分類: **解消済み 0 / 対応する 0 / 対応しない 6**。

仕様の論点として残すもの:

- R2・R5: `initialize.bash` の分岐をテストで固定するか、設計 Spec のテスト節から外すか（ユーザーの指示で省略済み。実際に起きた `CDPATH` の不具合の再発防止として足す余地はある）
- R1: 修正版の resoloop が NuGet に公開されたら README の記述が当てはまる。公開されるまでの追随は resoloop の公開の作業で扱う

## 確認の範囲

- 変更ファイルの全文: `.devcontainer/initialize.bash`・`devcontainer.json`・`test-initialize-mounts.bash`、README の写真フォルダの節とツール表、`.gitignore`。設計 Spec の全文、Plan の Task 5 と実施結果、resoloop PR #15 の修正要否の Spec の全文
- 関連処理: `install_beforehand.bash` の `ensure_user_writable_dir` と書き込み可能化の一覧、`mounts.bash` と `check-layout.sh` のマウントの突き合わせ、`run-tests.bash` のテストの集め方、`install_resoloop.bash`（rebuild で公開版へ戻す `dotnet tool update`）、`git status` を読む `scripts/superpowers_context.py`・`.devcontainer/herdr-git-status.bash`
- 自己確認（PR が持ち込んだ致命的な欠陥は見つからなかった）
  - Docker はマウント先の中間ディレクトリ `~/.local/share/create-reso-world` を root 所有で作り得るが、コンテナの中でここへ書く処理は無い（`.devcontainer`・`scripts`・`templates` を検索）
  - ホストで `initialize.bash` が書く env ファイルは、bind mount でコンテナの作業ツリーにも見える。`.gitignore` で除外され、`git status --porcelain=v1 --untracked-files=all` に出ない。env ファイルがある状態でも `check-layout.sh`・`test-file-modes.bash`・`test-initialize-mounts.bash`・`test-readme.bash` は PASS
  - `initializeCommand` と同じ相対パスの起動（`/bin/bash .devcontainer/initialize.bash`）で、`CDPATH=.:` でも exit 0 で、env ファイルは `.devcontainer/` にできる

## 検証

再現は、レビュー対象の HEAD `4669e4a` を `mktemp` の隔離 worktree に展開して行い、終了後に外した。全テストは専用の worktree（PR head、未コミットの変更なし）で実行し、実行後も `git status --porcelain` は空だった。

| 確認 | 結果 |
| --- | --- |
| `initialize.bash` のコピーを一時 HOME で実行: 空のディレクトリ | exit 0、env ファイル 0 バイト、プレースホルダーのディレクトリを作成 |
| リンク先があるリンク（cwd `/`、`CDPATH=.:`） | exit 0、`RESOLOOP_SCREENSHOTS_DIR=/home/vscode/.local/share/create-reso-world/resonite-screenshots` の 1 行、リンクはそのまま |
| リンクを消して再実行 | exit 0、env ファイル 0 バイト |
| リンク先が無いリンク | exit 1、`links to a missing folder` とリンク先のパス |
| 対照: Plan の `cd` の式を `CDPATH=.:` で評価 | パスが改行で 2 行に割れる（R3 の事実を確認） |
| 変異: 書き込み可能化の一覧に写真フォルダを足して `test-initialize-mounts.bash` | PASS（R4 の事実を確認） |
| `curl https://api.nuget.org/v3-flatcontainer/resoloop/index.json` | 公開版の最新は `0.1.0-preview.17`（R1 の事実を確認） |
| `bash .devcontainer/run-tests.bash` | 28 本 PASS（exit 0、167 秒） |
| `bash scripts/check-layout.sh` | PASS（exit 0） |

base `main` は head の祖先なので、base を merge した一時ツリーでの再検証は不要。create-reso-world は private のため、ルート `AGENTS.md` の「GitHub Actions」により CI は確認の対象外。

PR 本文の「`run-tests.bash` 29 本 PASS」は、`d3050ed`・`4669e4a` とも追跡しているテストが 28 本（`.devcontainer/test-*.bash` 17、`tests/scripts/*.bash` 11）で、記録の数え違いである。致命的ではないため直さない。

## 自己レビュー

未実施。結論 2 で修正が無いため、修正後の自己レビューの対象が無い。

## PR 本文に書き足すこと

無い。「対応しない」のうち実在する制約（R1: 公開版ではリンクが無いとタイムアウトまで待つ）は、PR 本文の「修正版の resoloop では `CAPTURE_EXPORT_DIR_UNREACHABLE` ですぐに止まります」と食い違わない。

## 作業時間

- 着手 2026-10-09T09:05Z ごろ、Spec の完成 2026-10-09T09:20Z（約 15 分）。内訳: レビューの読込と PR の状態・境界・worktree の確認（約 4 分）、変更ファイルと関連処理の精読（約 3 分）、隔離 worktree での再現と自己確認（約 3 分）、全テスト（約 3 分）、Spec の作成（約 2 分）
