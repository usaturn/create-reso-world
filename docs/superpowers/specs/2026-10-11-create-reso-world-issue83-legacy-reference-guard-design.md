# Issue #83: 移行元参照ガードの見直し

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- 対象 Issue: [#83](https://github.com/usaturn/create-reso-world/issues/83)
- 基準コード HEAD: `8f7594a85636c26c719abe51eb932e8516abf398`（#84 マージ後）
- 状態: completed
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

## 完了記録

- 実行対象の文書版: `510711b0485d71eeaae0665806d61f73b3601832`。個別の内容承認はなく、ユーザーの推奨案での継続指示に従って実行した。
- 実装コミット: `33f99d9f43325e361958ccdc1d824c1fadbc33d0`（専用テストファイル 68 行の削除のみ）。
- タスクレビュー: Spec compliant / Task quality Approved。Critical・Important・Minor の指摘なし。変更していない領域・親 checkout・検証結果の確認項目は controller が差分・状態・再実行で解消した。
- 実装子: 既存失敗 1 failed / 8 passed を再現。撤去後 pytest 474 passed、境界検査 172 passed / 109 subtests passed、mount 検査・Shell 29 件・配置・差分検査成功。
- controller 再検証（2026-10-11 22:45–22:52 JST）: `uv run pytest -q -rs` は 473 passed / 1 skipped、失敗なし。skip は stale-git-lock-recovery の安全検査が別の Git プロセスを検出したため（cwd が読めない PID）。`bash .devcontainer/run-tests.bash` は 29 件成功。配置と差分検査も成功。
- controller ログ: `tmp/issue83-verification/controller-20261011-224526-1974982.log`（worktree 内、追跡対象外、`EXIT=0`）。
- mount の由来コメント、境界検査・実装、過去の文書、親 checkout は変更していない。親 checkout は `8f7594a` の detached HEAD = `origin/main`。worktree にはローカルワールドがない。
- 初回の uv 環境作成のみ cross-filesystem hardlink の警告があった。以降は `UV_LINK_MODE=copy` で実行し、テスト失敗として扱わない。
- 実装子の所要: 11 分（境界検査 102 秒、全体 pytest 163 秒、Shell 199 秒）。調査子 7 分31秒、タスクレビュー約3分。controller 基準 pytest 212 秒、再検証約7分。
- 公開未実施。成果は `fix/issue-83-legacy-reference-guard` と `.worktrees/issue-83-legacy-reference-guard` に保持し、push・PR・マージ・Issue close はしていない。

## 最終レビューと裁定

- 全体レビュー対象: `8f7594a..ff4aea3`。`Review scope: branch` の読み取り専用レビューで Ready to merge: Yes。Critical・Important・Minor の指摘なし。レビュー所要約2分。
- レビューが評価対象外とした項目は以下のとおり確認し、別の成功主張には含めない。
- G1: Ruling: 新しい操作指示分類器は追加しない — 文言分類では操作先の安全性を保証できず、Issue #83 の最小修正に不要 — 誤っていれば別途分類機能の設計が必要。
- G2: Ruling: 未変更 resolver/context の全面監査と Issue #68 の再修正は行わない — 既存実行検査を維持して成功を確認し、別 Issue の範囲を混ぜない — 誤っていれば既存実装の問題を別途調査・修正する必要がある。
- G3: Ruling: 他の Git プロセスによる stale-lock 検査の skip を成功とは扱わず、今回の停止条件にもしない — 安全のための既存 skip で対象は未変更、実装子の全件成功記録もある — 誤っていれば静かな環境で追加検証が必要。
- G4: Ruling: ローカルワールドの動作検証は行わない — 隔離 worktree にワールドはなく、変更は文言ガードの撤去だけ — 誤っていればワールドの実環境検証が必要。
- タスクの通常実装は完了。本 Plan の再実行や公開操作には使わない。
