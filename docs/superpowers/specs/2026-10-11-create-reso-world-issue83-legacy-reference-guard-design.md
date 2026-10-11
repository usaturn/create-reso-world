# Issue #83: 移行元参照ガードの見直し

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- 対象 Issue: [#83](https://github.com/usaturn/create-reso-world/issues/83)
- 対象 PR: [#86](https://github.com/usaturn/create-reso-world/pull/86)
- レビュー指摘の検証 HEAD: `6db6b9deab7b0767b9529a4041bbd465e4437a8f`
- 今回の実行許可: ユーザーが `review-fix-planning` を `#86` に対して指定した。計画のみの指定はなく、同スキルの完遂経路として、検証・Spec 更新・既存 PR への push・状況投稿・修正不要の場合のマージと関連 Issue 更新を許可された。以下の初回実装・PR 作成段階の許可制限は、その時点の記録であり、今回の実行許可を制限しない。
- 基準コード HEAD: `8f7594a85636c26c719abe51eb932e8516abf398`（#84 マージ後）
- 状態: completed
- 関連 Plan: `../plans/2026-10-11-create-reso-world-issue83-legacy-reference-guard.md`
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-83-legacy-reference-guard`
- 実行許可: ユーザーの「#83 に以下条件で着手してください。 - 途中で止めずに推奨案で完了する」に基づき、推奨案の選択・ローカル実装・検証を進める。文書内容の個別承認ではない。完了後の追加指示「PRをしてください」により push・PR 作成を許可された。マージと Issue の直接 close は行わない。

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
- Python の実行には `uv` を使う。追加の明示指示により既存ブランチの push・PR 作成のみ許可する。マージと Issue の直接 close は行わない。親 checkout は `origin/main` のまま維持する。

## 検証と完了条件

新しい実装のロジックはないため、新規テストは作らない。TDD 設定にかかわらず `AGENTS.md` の採用基準を優先する。既存失敗の再現、既存の境界実行テスト、全体 pytest、mount 検査、Shell 全体、配置、差分の検査で確かめる。

- `uv run pytest -q` が本 Issue の失敗を出さず、他の失敗もない。
- 既存の repository resolver/context 検査を実行し、誤った root・remote の拒否を維持する。
- mount コメントと安全範囲は変更せず、既存 mount 検査が通る。
- Issue #68 の実装や他のテストを変更しない。
- タスクレビューと全体レビューを行い、成果を保持する。公開は追加の明示許可に従う。

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
- タスクの通常実装は完了。通常実装を再実行しない。公開操作は以下の追加許可にのみ従う。

## 追加の公開許可（2026-10-11）

- ユーザーの「PRをしてください」により、`fix/issue-83-legacy-reference-guard` の push と `main` 向けの PR 作成を許可された。
- 設計・実装修正・テスト採用の判断は変更しない。公開許可の記録追記であり、個別の文書内容承認を得たとは扱わない。
- マージ・Issue の直接 close は未依頼のため行わない。PR 本文の `Closes #83` でマージ後の close を関連付ける。
- 「完了記録」の公開未実施は、この追加指示前の時点の記録。公開結果・PR URL は GitHub と更新した handoff で確認する。
- PR 作成前の再検証（2026-10-11 23:06–23:10 JST）: `uv run pytest -q -rs` は 474 passed、skip・失敗なし。配置・差分検査も成功。ログ: `tmp/issue83-verification/pr-20261011-230652-2190883.log`（`EXIT=0`）。

## PR #86 のレビュー指摘の選別（2026-10-11）

### 入力と確認範囲

`reviews/#86-fix-issue-83-legacy-reference-guard/` 配下の全4ファイルを読み、全ファイルの対象 HEAD `6db6b9deab7b` が現在の PR head と一致し、その祖先であることを確認した。

| レビューファイル | 対象 HEAD | 指摘数 |
| --- | --- | --- |
| `openai-codex-gpt-6.1-sol.md` | `6db6b9deab7b` | 0 |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `6db6b9deab7b` | 0 |
| `SWE-2-High.md` | `6db6b9deab7b` | 1 |
| `Claude-Opus-5.5.md` | `6db6b9deab7b` | 1 |

変更ファイル3件の全文を確認した。削除されたテスト68行は committed blob/diff で確認し、本 Spec と関連 Plan は clean かつ HEAD が一致する専用 worktree で読んだ。削除対象の参照先、pytest 設定、CI、Shell runner、配置検査、mount 検査、repository context の root・remote 検証と関連テストを確認した。独立した読み取り専用調査を `sp-recon` に委譲し、`scripts/superpowers_context.py`、その呼出経路、および維持する境界テスト3ファイルの全文確認を担当させた。検証コマンドと GitHub 操作は controller が実行した。

### 全指摘の分類

分類は **解消済み 0 / 対応する 0 / 対応しない 2**。同じ `I-1` が別レビューにあるため、ここでは出典付きの ID を使う。

| ID | 出典 | 指摘 | 分類と根拠 |
| --- | --- | --- | --- |
| S-I-1 | SWE-2-High `I-1` | 移植比較表が削除済みテストの `EXCLUDED` を参照している | 対応しない。`docs/maatlog-poc-porting.md:140` の参照は実在するが、冒頭で移植時の記録と明示し、現在の手順を README に分けている。実行上の参照ではなく、履歴の保存方針と整合する。 |
| C-I-1 | Claude-Opus-5.5 `I-1` | #51 で撤去した検査と #53 の R3 がこのガードを前提にした経緯が Spec に列挙されていない | 対応しない。#51 の分類表65・94・100・182・204・256行と #53 のレビュー修正 Spec 30行で前提を確認した。文書は当時の判断記録であり、現在の実行手順ではない。記録の網羅性の指摘であって致命的な誤動作ではなく、撤去した検査も現在の採用基準の作らない型2に該当する。 |

解消済みに分類した指摘はない。確認中に見つけた PR 由来の致命的な欠陥もない。移行元の語句を自動検出する保証を維持するかという論点は、現行 `AGENTS.md` のテスト採用基準と、この Spec の撤去判断で決着している。

### 判断と設計

- 結論: **2 修正不要としてマージする**。Info の補足を目的とする変更や代替テストは追加しない。
- 新しい Spec は作らず、リポジトリ・Issue・テーマ・PR 本文の文書リンクが一致する本 Spec を更新する。既存 Plan の実装手順は再実行しない。
- 「対応する」は0件のため、修正対象の守る条件・影響経路の表、設計の見直し、失敗時のガード対照検証は不要。
- 旧テストは追跡ファイルの文字列検索だけで resolver や操作を実行していない。削除に伴い実行時の境界保証は変わらず、root・remote の拒否と mount の安全範囲検査を維持する。
- 履歴参照は実在するが、PR 本文も既存履歴を変更しないと明記しており、説明の保証との不一致はない。PR 本文の変更は不要。
- open・非 draft の `usaturn/create-reso-world` PR で、操作権限は ADMIN。private の停止中 CI は `AGENTS.md` に従って確認不要。

### 今回実行した検証

| 検証 | 結果 |
| --- | --- |
| 隔離した base `8f7594a` の旧テストを `uv run --frozen pytest -q tests/skills/test_legacy_references.py` で実行 | 期待どおり exit 1、1 failed / 8 passed。唯一の検出は mount の由来コメント20行目。 |
| 専用 worktree で `uv run --frozen pytest -q -rs tests/skills .agents/skills` | 最終実行は exit 0、474 passed、skip なし（208.22秒）。 |
| `uv run --frozen pytest -q -rs tests/scripts/test_superpowers_context.py .agents/skills/pr-review/tests/test_pr_review_skill_contract.py .agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py` | exit 0、172 passed / 109 subtests passed（141.85秒）。 |
| `bash .devcontainer/run-tests.bash` | exit 0、29件成功（426秒）。mount 検査も成功。 |
| `bash scripts/check-layout.sh`、`git diff --check`、`git diff origin/main...HEAD --check` | すべて exit 0。 |
| base 再取得と祖先確認 | 検証後に再取得した `origin/main` は `8f7594a85636c26c719abe51eb932e8516abf398` で、検証 head の祖先。先行変更がないため一時 merge は不要。 |

スキルスイート初回は `test_killed_create_reports_its_last_phase_and_leftovers` の `running` / `vanished` 判定で1回失敗し、473件成功した。同じテスト・実装は base と head で完全に同じで、個別再実行は双方5回ずつ成功した。全スイートの再実行も474件成功したため、PR の回帰として扱わない。一過性失敗のタイミング原因は特定しておらず、原因が解消したとは主張しない。無関係な既存コードは変更しない。

結論2では修正後の自己レビューは行わない（未実施）。代わりに全入力・全変更・関連処理とテストの確認、および上記の実行検証を完了した。今回の変更は判断記録のみで実行する新しい挙動がないため、新規テストは不要。文書の構造・参照先と差分で検証する。

検証のログ・venv・一時ファイルは `mktemp` が返した `/tmp/review-fix-planning.BUIi6n` 配下に閉じ込めた。隔離 worktree を Git から外してから親ディレクトリを削除し、Spec 更新前に teardown を完了した。既存の clean な `.worktrees/issue-83-legacy-reference-guard` を専用 worktree として再利用したため、この checkout と既存ブランチは片付けの対象にしない。

### 作業管理と所要

- [x] 全レビューと対象 HEAD の固定、PR/context 照合
- [x] 全指摘・変更全文・関連処理とテストの確認、分類
- [x] 既存 Spec の特定、推奨結論と実行許可の記録
- [x] 種類別検証、base 確認、一時 worktree の teardown
- 状態は completed。結論2の公開前の確認は完了。push・投稿・マージ・Issue 更新の結果は、この文書には追加コミットせず、PR の状況コメントと完了報告に記録する。
- controller の主な区間（UTC）: 14:24–14:30 入力・context・全文と関連処理の確認、14:30–14:35 旧ガード再現と初回失敗の調査、14:35–14:48 最終 pytest・境界・Shell・配置検証、14:48–14:49 head/base 再確認と teardown。公開操作を除く所要は約25分。
