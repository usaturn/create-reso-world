# Issue #83: 移行元参照ガードの見直し

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- 対象 Issue: [#83](https://github.com/usaturn/create-reso-world/issues/83)
- 基準コード HEAD: `8f7594a85636c26c719abe51eb932e8516abf398`（#84 マージ後）
- 状態: draft
- 関連 Plan: `../plans/2026-10-11-create-reso-world-issue83-legacy-reference-guard.md`
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-83-legacy-reference-guard`
- 実行許可: ユーザーの「#83 に以下条件で着手してください。 - 途中で止めずに推奨案で完了する」に基づき、推奨案の選択・ローカル実装・検証を進める。文書内容の個別承認ではない。push・PR 作成・マージ・Issue close は行わない。

## 目的と原因

`tests/skills/test_legacy_references.py` の追跡ファイル検査が、`.devcontainer/test-initialize-mounts.bash:20` の Cursor 認証 mount の由来を記録したコメント（`usaturn/maatlog-poc#585`）を検出する。

このコメントは導入の経緯であり、移植元で操作するよう促す手順ではない。検査は文字列の有無だけで、両者を区別できない。変更前の隔離 worktree で `uv run pytest -q` を実行し、同じ 1 件の失敗、481 件成功、1 件 skip を再現した。

Issue #51 の分類表は誤対象操作を防ぐ固定値としてこの検査を維持した。しかし現行の検査対象は文言・旧参照の不在であり、実際の操作先検証ではない。今回、この検査の扱いのみを見直す。#51 の完了記録や #68 の Spec・Plan は改変しない。

## 推奨案（今回の判断）

`tests/skills/test_legacy_references.py` 全体を削除する。追跡ファイル検査にしか使われない定数・正規表現と、専用のパターンテストも同時に不要になる。

- 由来コメントを消す案: 正しい記録を失い、誤検出する検査を残すため採らない。
- 個別 allowlist: 今回だけを回避し、例外の継続追加が必要になるため採らない。
- 文章分類器への変更: 実際の作業先検証にはならず、今回の範囲では過剰なため採らない。
- 実際のリポジトリ境界は、既存 resolver/context の実行テストと root・remote 検証を維持する。
- 移植元で操作するような誤った手順は引き続きレビュー対象とする。参照語句があるだけで一律に禁じない。

## Global Constraints

- 変更対象は `tests/skills/test_legacy_references.py` の削除と、本 Issue の Spec・Plan だけ。
- `.devcontainer/test-initialize-mounts.bash` の由来コメント・mount 一覧・実行検査は変更しない。
- resolver/context の実装・実行テスト、`AGENTS.md`、既存の履歴文書、ローカルワールドは変更しない。
- 文書の文言・削除済みファイルの不在だけを照合する代替テスト、allowlist、文章分類器は追加しない。
- Python の実行には `uv` を使う。公開操作は行わない。親 checkout は `origin/main` のまま維持する。

## 検証と完了条件

新しい実装のロジックはないため、新規テストは作らない。TDD 設定にかかわらず `AGENTS.md` の採用基準を優先する。既存失敗の再現、既存の境界実行テスト、全体 pytest、mount 検査、Shell 全体、配置、差分の検査で確かめる。

- `uv run pytest -q` が本 Issue の失敗を出さず、他の失敗もない。
- 既存の repository resolver/context 検査を実行し、誤った root・remote の拒否を維持する。
- mount コメントと安全範囲は変更せず、既存 mount 検査が通る。
- Issue #68 の実装や他のテストを変更しない。
- タスクレビューと全体レビューを行い、公開未実施で成果を保持する。
