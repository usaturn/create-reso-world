# usaturn/create-reso-world PR #63: Cursor CLI の認証情報のマウントのレビュー修正要否

- 対象リポジトリ・PR: https://github.com/usaturn/create-reso-world/pull/63（`feat/cursor-auth-mount` → `main`）
- 関連 Issue: 無い（`closingIssuesReferences` は空。本文は usaturn/maatlog-poc#585 を手法の参照として挙げるだけ）
- 新しい文書にした理由: PR #63 とこのテーマ（Cursor CLI の認証情報のマウント）の Spec・Plan は `docs/superpowers/` に無かった
- 検証したコード HEAD: `a7f438963c5c02cb7b488c8128104e8b30f3a94f`（base `main` = `a44fee02b85acdb4ccfe21620249997d27ac14c0` は head の親）
- 状態: completed
- 実行許可: 利用者が `/review-fix-planning #63` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要としてマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/cursor-auth-mount`（PR head を checkout 済みの既存の worktree を、未コミットの変更なし・HEAD 一致の条件で再利用。このセッションの片付けの対象ではない）

## 入力

`reviews/#63-feat-cursor-auth-mount/` の 3 ファイル。対象 HEAD はすべて `a7f438963c5c` で、現行の `pull/63/head` と同じである。

| ファイル | 対象 HEAD | 判定 | 指摘 |
| --- | --- | --- | --- |
| `Grok-4.7.md` | `a7f438963c5c` | Approve | 0（Unverified candidates なし） |
| `claude-opus-5-5.md` | `a7f438963c5c` | Approve | 0（Unverified candidates なし） |
| `opencode-go-deepseek-v4.1-flash.md` | `a7f438963c5c` | Approve | 0（Unverified candidates なし） |

## 分類

指摘は 0 件。分類: **解消済み 0 / 対応する 0 / 対応しない 0**。

確認中に自分で見つけた PR の致命的な欠陥も無い（下の「確認の範囲」）。

## 確認の範囲

- 変更ファイルの全文: `.devcontainer/devcontainer.json`・`initialize.bash`・`install_beforehand.bash`・`test-initialize-mounts.bash`、`.devcontainer/README.md` のツール表
- 関連処理: `mounts.bash` の突き合わせ（`mounts_from_devcontainer`・`mounts_from_initialize`・`mounts_compare`）、`test-readme.bash`（ツール表と mount・`initialize.bash` の突き合わせ）、`scripts/check-layout.sh` の `check_mounts`、`install_beforehand.bash` の `ensure_user_writable_dir` と書き込み可能化の一覧、`zshrc.txt`・`cleanup-workspace.bash`（`~/.config` 配下を触る処理と `XDG_CONFIG_HOME` の有無）、設計 Spec `2026-09-26-create-reso-world-redesign-design.md` の 7.1 節
- 自己確認（PR が持ち込んだ致命的な欠陥は見つからなかった）
  - 導入済みの Cursor CLI（`2026.10.01-e373342` の `index.js`）で、Linux の認証ファイルは `${XDG_CONFIG_HOME:-~/.config}/cursor/auth.json`、ログアウト（認証情報の消去）は `auth.json` を unlink する。ファイル単体の bind mount ではログアウトが失敗するため、ディレクトリの mount は実装と一致する。`XDG_CONFIG_HOME` は `.devcontainer` のどこでも設定しておらず、このコンテナでも未設定
  - 秘密情報の露出: `initialize.bash` はホスト側の `~/.config/cursor` を `mkdir -p`（umask どおり、通常 755）で作るが、Cursor CLI は認証情報を書くたびにディレクトリを `chmod 700`、`auth.json` を mode 600 で書いて `chmod 600` する。bind mount 越しの chmod はホスト側に効くので、認証情報は本人以外に読めない。`~/.codex`・`~/.claude` と同じ扱いである
  - 書き込み可能化: 一覧の `~/.config` が `~/.config/cursor` より前にあり、`ensure_user_writable_dir` は再帰しない。ホスト側に先にディレクトリがあるので、Docker が root 所有で作る経路は通らない
  - 4 か所の集合の一致: `devcontainer.json` の mounts、`initialize.bash`、postCreate の書き込み可能化、README のツール表が同じ 14 個で、固定値の一覧（`test-initialize-mounts.bash`）とも一致する
  - 設計 Spec 7.1 節の表には `~/.config/cursor` が無い。PR #62 で足した写真フォルダも同じく載っておらず、mount の集合は `test-initialize-mounts.bash` の固定値が守っている。記録の差で、手順・挙動に影響しないため直さない

## 検証

全テストは専用の worktree（PR head、未コミットの変更なし）で実行した。指摘が無いので、隔離 worktree での再現は行っていない。

| 確認 | 結果 |
| --- | --- |
| `bash .devcontainer/run-tests.bash` | 28 本 PASS（exit 0、159 秒） |
| `bash scripts/check-layout.sh` | PASS（exit 0。`mounts match .devcontainer/initialize.bash` を含む） |

base `main` は head の親なので、base を merge した一時ツリーでの再検証は不要。create-reso-world は private のため、ルート `AGENTS.md` の「GitHub Actions」により CI は確認の対象外。

## 自己レビュー

未実施。結論 2 で修正が無いため、修正後の自己レビューの対象が無い。

## PR 本文に書き足すこと

無い。「対応しない」の指摘が無く、PR 本文の保証（rebuild 後もログインが保持される、初回だけ再ログインが要る）と食い違う実在の制約も無い。

## 作業時間

- 着手 2026-10-09T09:49Z ごろ、Spec の完成 2026-10-09T09:58Z（約 9 分）。内訳: レビューの読込と PR の状態・境界・worktree の確認（約 3 分）、変更ファイルと関連処理の精読、Cursor CLI の認証処理の確認（約 4 分）、全テストと `check-layout.sh`（約 3 分。精読と並行）、Spec の作成（約 3 分）
