# Issue #169 Trusted Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 上流 PR でも明示した利用者自身の判断記録を継続して読めるようにする。

**Architecture:** association による既存の信頼判定へ、空でない単一 login の完全一致を加える。API はキーワード専用の既定引数、CLI は明示オプションで伝え、認証済み login の取得は呼び出し側に残す。

**Tech Stack:** Python 標準ライブラリ、uv、pytest、Markdown。

**Spec:** `docs/superpowers/specs/2026-10-18-create-reso-world-issue169-trusted-login-design.md`（Spec commit: `2b9e2cd`）

## 管理・実行許可

- 文書管理・対象: `usaturn/create-reso-world`、Issue https://github.com/usaturn/create-reso-world/issues/169
- 状態: `draft`。利用者の `/skill:issue-to-pr #169` に基づく実行許可であり内容の承認は未取得。
- 開始 HEAD: `1335f410e624355cd558029bdcdad65eaa944ed8`
- `PARENT_ROOT`: `/workspaces/reso-world`
- `DOC_ROOT` / `CODE_ROOT`: `/workspaces/reso-world/.worktrees/issue-169-trusted-login`
- 実行方式: `executing-plans`。一つの関数群・テスト・説明を順に直す小変更のため inline を選択。最後に read-only の `sp-review` でブランチ全体を確認する。

## Global Constraints

- `trusted_login: str = ""`。空でない完全一致だけを追加で信頼する。`TRUSTED_ASSOCIATIONS` は `OWNER`・`MEMBER`・`COLLABORATOR` のまま。
- モジュールは gh を実行しない。コメントの本文や PR author で信頼先を決めない。
- 既存の schema・PR 一致検査・除外処理・エラー終了コードを維持する。
- #155 の upsert/run_roles、スキル、他 Issue の状態・予約は変更しない。
- 未コミットのログ・ledger は `/workspaces/reso-world/tmp/agents/issue-169.5aokzp_x/` に置く。SDD 標準の worktree 内スクラッチの代わりに、この場所へ brief・結果を記録する（AGENTS.md の配置規則を優先）。
- 指定パスだけ stage する。公開は秘密情報検査を通した SHA の push と PR 作成まで。マージしない。

## Review Focus

- 空 login と空/欠落 author の一致で信頼を付与しない（Task 1 のパラメーター化テスト）。
- 明示 login があっても他の CONTRIBUTOR は読まない（Task 1 の負例）。
- 明示 login でも壊れた記録・異なる PR・除外 ID を迂回しない（Task 1）。
- validate の過去コメント照合と fold の JSON 出力で同じ信頼指定を使う（Task 1 の CLI テスト）。
- #155 に接続したと誤認させない。現行の API 対応と後続の接続予定を区別する（Task 1 の文書差分確認）。

## 実行予算

小変更として着手から能動時間 30 分（準備・設計 8、実装 8、回帰・レビュー 10、公開 4 分）を目安とし、予算 ledger は省略する。工程境界・15 分・30 分と worker 失敗時に確認する。独立レビューは同期で終了まで待ち、停止できる監視手段がないため強制停止しない。レビュー目安 5 分、末尾 1 分を報告用に取り、進捗が無ければ最小の結論を報告させる。実モデルは builder check 1 件（起動条件不備の再試行 1 回を含む）と最終レビュー 1 件のみ。信頼性の同じ失敗は再試行 1 回まで、安全の失敗は即停止。範囲が膨らめば upsert/run_roles は引き続き #155 に残し、予算 100% では残作業・対策を報告して停止する。

---

### Task 1: 明示 login の信頼判定と利用手順

**Files:**
- Modify: `.agents/scripts/review_records.py`（collect_records / read_state / CLI）
- Test: `.agents/scripts/tests/test_review_records.py`
- Modify: `.agents/review-records.md`（7.4、7.6、8.1）

**Interfaces:**
- Consumes: 整形済みコメントの `author` / `author_association`、既存の round_one/round_two の正常な記録 fixture。
- Produces: `collect_records(comments, *, exclude_comment_ids=(), trusted_login: str = "")`、`read_state(comments, *, expected_pr=None, exclude_comment_ids=(), trusted_login: str = "")`、fold と validate の `--trusted-login LOGIN`。戻り値は変更しない。

**テストの要否:** 必要。信頼する投稿者の安全条件・引数の伝播・過去記録からの継続が実行時の挙動である。文書自体の文字列照合テストは不要。

- [ ] **Step 1: 失敗する回帰テストを書く。**
  - `test_collect_records_accepts_explicit_trusted_login`：CONTRIBUTOR / NONE の自分の記録が一件、ignored は空。
  - `test_collect_records_does_not_trust_other_or_empty_logins`：別 login / 空の信頼指定 / 空 author / 欠落 author の正常な記録は records が空、ignored に ID がある。負例は正常入力から不一致条件一つだけを作る。
  - `test_trusted_login_keeps_association_trust`：従来の三区分は異なる明示 login でも読める。
  - `test_read_state_trusted_login_continues_next_round`：自分の CONTRIBUTOR の round 1 を読んだ状態で round 2 の check_against は成功、round 1 の重複は拒否。
  - `test_trusted_login_does_not_bypass_record_checks`：PR 違い・壊れた記録・除外 ID の既存条件をそれぞれ検査。
  - CLI fold の有/無指定で rounds が `[1]` / `[]`、別人の投稿は無視。validate は自分の round 1 から round 2 が終了 0、無指定なら 65。
- [ ] **Step 2: RED を確認。** `uv run pytest .agents/scripts/tests/test_review_records.py -q`。新しい引数・オプション未実装による新テストの失敗で、既存 187 件は成功すること。
- [ ] **Step 3: 最小実装。** キーワード専用引数、空でない login の一致分岐、read_state と二つの CLI からの伝播を加える。
- [ ] **Step 4: GREEN を確認。** `uv run pytest .agents/scripts/tests/test_review_records.py -q` と `uv run pytest .agents/scripts -q`。全件成功、終了コード 0。
- [ ] **Step 5: 文書更新。** 7.4 の照合対象と同じ認証 login の利用、7.6 の API 引数、8.1 の取得失敗時停止と fold オプションを記す。validate の同オプションも説明する。`git diff --check` と差分閲覧で文書・参照を確認。
- [ ] **Step 6: commit。** 上記の三つのパスだけ stage、`fix: trust explicit login when reading review records`。

### Task 2: 全体の検証・独立レビュー・PR 公開

**Files:** Spec・Plan の実施記録。新たな機能ファイルは追加しない。

**Interfaces:** Task 1 の API と CLI、開始 HEAD からのブランチ全差分。

**テストの要否:** 新規テスト不要。既存の回帰入口とレビューで統合を確かめる。

- [ ] **Step 1: README の入口を worktree で同期実行。** `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。ログは親 checkout の上記 session に保存し、各終了コード 0 を確認する。失敗は systematic-debugging で切り分け、解消しなければ停止する。
- [ ] **Step 2: sp-review にブランチ全体を read-only で依頼。** Spec・Plan・実施記録・開始 HEAD と Review Focus を渡す。テストは子に実行させない。重要な問題があれば一度の修正で RED→GREEN と全回帰を行う。
- [ ] **Step 3: 結果を文書に追記して commit。** 状態は draft のまま実行結果・検証・時間を追記し、`git diff --check`、clean な git status を確認する。
- [ ] **Step 4: 競合を再確認し秘密情報検査→push。** Issue の open・全ページの PR/コメント・claim ref・同番号 branch/worktree を確認し、この run の所有物以外があれば停止。`SHA="$(bash /workspaces/reso-world/scripts/scan-before-push.sh -C /workspaces/reso-world/.worktrees/issue-169-trusted-login)" && [ -n "$SHA" ] && git push origin "${SHA:?}:refs/heads/fix/issue-169-trusted-login"`。検査の失敗時は何も push しない。
- [ ] **Step 5: 再度重複 PR を確認し main 向けに PR 作成。** 本文へ Closes #169、設計判断、inline の理由、検証、所要時間を記載する。private のため CI 確認不要。作業中の worktree と branch を残し、Herdr を completed にする。

## Plan 自己確認

Spec の受け入れ 1〜5 は Task 1、6 と公開規則は Task 2 に対応する。関数名・引数は Spec と一致。文書だけのテストは追加しない。builder check は「nothing important left」であり、未解決の利用者判断は無い。
