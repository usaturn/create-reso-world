# issue-to-pr: レビュー runner 実行中の対象 checkout 書き込み禁止の明示 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** issue-to-pr SKILL.md に、レビュー runner・実装 Task 依頼の実行中は対象 checkout へ書き込まないことの明示を追加し、並行書き込みによる `outside_changes` 拒否・有料レビューの損失を防ぐ。

**Architecture:** `.agents/skills/issue-to-pr/SKILL.md` への 2 段落の追加のみ（追加 A: 「Spec・設計レビュー」節、追加 B: 「Task の実装を runner の担当に依頼する」節）。監査実装・helper・他スキルは変更しない。

**Tech Stack:** Markdown（日本語）。検証は bash（check-layout.sh）・uv（pytest）・git。

**Spec:** `docs/superpowers/specs/2026-11-13-issue-417-review-runner-write-guard-design.md`（commit `6e1247fc2cd153038fd5e9a1958ba89b75dee370` の版。Spec レビュー 1 回目の S1 採用済み）

## Global Constraints

- 編集対象は `.agents/skills/issue-to-pr/SKILL.md` のみ（Spec・Plan の文書を除く）。frontmatter・既存段落の文言は変更しない（追加のみ）
- `tools/agent_runner/`・`.agents/skills/issue-to-pr/scripts/`・monitoring-long-tasks・review-verify・review-fix-planning・pr-review-fix-loop は変更しない
- テストは追加しない（AGENTS.md の採用基準 F。F∩S に当たる固定値を守らない）。検証はツールの実行と文面の照合で代える
- 日本語表現は AGENTS.md の規則に従う（「正本」「着地」「契約」などの禁止語を使わない）
- 作業 worktree: `/workspaces/reso-world/.worktrees/issue-417-runner-write-guard`（branch `fix/issue-417-runner-write-guard`、base `main` @ `bce027ba003a4090fee3f4a2e9c85a6383009e51`）。main checkout では編集しない
- コミットしないファイル（ledger・検証ログ）は `SESSION`（`/workspaces/reso-world/tmp/agents/issue-417.usgohlf8`）に置く。worktree 内に作らない

## Review Focus

文書変更でありテストは追加しない（F）。各項目は Task 2 の照合で確認する。

1. 追加文面と監査仕様（interfaces.rst「期限と保持」）の語義一致: 比較時点は「開始前に登録された checkout」と「終了後の状態」。S1 採用済みの文面が保たれていること
2. 配置の到達範囲: 追加 A が設計レビュー・Spec レビュー・再レビューのすべてに適用される位置（節の共通部）にあること。追加 B が待機の指示（項目 3）に結び付いていること
3. 既存記述との整合: 「未 commit の変更を残さない」（起動前）と実行中禁止の関係が明示され、矛盾しないこと。`outside_changes` の失敗扱い・開始時 HEAD 照合の既存記述と重複・矛盾しないこと
4. 編集範囲の限定: `git diff` の対象が SKILL.md の 2 段落の追加のみであること（frontmatter・marked block・他ファイルの変更なし）
5. 受け取り後の書き込み再開: レビューは `submit` 成功後、実装は verdict 処理（`accept` を含む）完了後であること。項目 4 の「取り込んだ後」のテスト実行と矛盾しないこと

## 受け入れ基準

- 動作環境: Ubuntu 26.04 LTS の Dev Container。uv・git・jq・gh が使えること。検証は worktree のルートで実行する
- 実入力: `.agents/skills/issue-to-pr/SKILL.md`（692 行・日本語の複数行 Markdown）。追加 A の挿入位置は「Spec・設計レビュー」節の依頼 JSON の例（```json ブロック）の直後、「**設計レビュー（`--design-review` があるときだけ）。**」の直前。追加 B の挿入位置は「Task の実装を runner の担当に依頼する」節の項目 3 の段落末尾
- 防御範囲:
  - 対象: レビュー runner（設計レビュー・Spec レビュー・再レビュー）実行中の `CODE_ROOT`（同一なら `DOC_ROOT`）への書き込み・コミット禁止の明示。実装 Task 依頼（`implement_task.py run`）実行中の feature worktree 変更禁止の明示。準備は `SESSION`（実装側は `SESSION` / `IMPLEMENT_SESSION`）、コミットは受け取り後
  - 対象外（反例）: runner の監査実装・helper の変更、他スキルの変更、frontmatter・既存段落の文言変更、gitignored キャッシュの扱いの変更、テストの追加

## Task 1: SKILL.md への 2 段落の追加

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`（追加 A: 401 行目の ```json ブロック終了直後・403 行目の直前。追加 B: 492 行目の項目 3 段落末尾。行番号は base 版の目安で、実際の挿入位置は下の文脈で特定する）

**Interfaces:**
- Consumes: Spec の「設計（推奨案）」の追加 A・追加 B の文面（S1 採用済み）
- Produces: 追加済みの SKILL.md（Task 2 の照合対象）

**テストの要否:** 不要（F: SKILL.md 本文の固定文言）。代わりの検証: `git diff` で追加が 2 段落のみ・既存行の変更が無いことを確認する。

- [ ] **Step 1: 追加 A を挿入する**

「Spec・設計レビュー」節で、次の文脈の間に挿入する（前: 依頼 JSON の例の閉じ ```、後: `**設計レビュー（`--design-review` があるときだけ）。**`）:

```markdown
**レビュー runner の実行中は対象 checkout を変更しない。** `review` の起動から結果の受け取り（`submit` 成功）まで、レビュー対象 checkout（`CODE_ROOT`。`DOC_ROOT` が同一の checkout ならその `DOC_ROOT`）への書き込み・コミットをしない。runner の checkout 監査は実行の開始前に登録されていた checkout の HEAD・index・tracked ファイル・非 ignored untracked ファイルを終了後の状態と比較する（`tools/agent_runner/interfaces.rst`「期限と保持」）ため、Plan 草案のような untracked ファイル 1 件でも `outside_changes` の拒否になり、完了した有料レビューが失われて再実行が必要になる。待機中の準備（Plan 草案・調査メモなど）は `SESSION` の下で行い、並行作業は対象 checkout の読み取りと `SESSION` への書き込みに限る。対象 checkout への書き込み・コミットはレビュー結果の受け取り後に行う。これは設計レビュー・Spec レビュー・再レビューのいずれでも同じである。
```

- [ ] **Step 2: 追加 B を挿入する**

「Task の実装を runner の担当に依頼する」節の項目 3 の段落（`3. **依頼:** 終わるまで待つ（…）。`）の末尾に、続けて追加する:

```markdown
依頼の実行中は feature worktree（`CODE_ROOT`）への書き込み・コミットをしない。runner はレビューと同じ checkout 監査を行うため、実行中の書き込み（untracked ファイルを含む）は `outside_changes` の拒否（`rejected`）になる。これは項目 2 の起動前の「未 commit の変更を残さない」に加えて、実行中の条件である。次の依頼の準備・ledger への記録は `SESSION` / `IMPLEMENT_SESSION` の下で行い、feature worktree への書き込み・コミットは依頼が終わって verdict の処理（`accept` を含む）が済んでから行う。
```

- [ ] **Step 3: diff を確認する**

Run: `git -C "$CODE_ROOT" diff -- .agents/skills/issue-to-pr/SKILL.md`
Expected: 追加は上記 2 段落のみ。既存行の削除・変更なし（diff は追加行のみ）。frontmatter・`<!-- base-workflow:* -->` の marked block に変更なし。

- [ ] **Step 4: Commit**

```bash
git -C "$CODE_ROOT" add .agents/skills/issue-to-pr/SKILL.md
git -C "$CODE_ROOT" commit -m "docs(issue-to-pr): forbid checkout writes while runner reviews/tasks run

Refs #417

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

## Task 2: 統合確認（条件単位の照合と回帰）

**Files:**
- なし（検証のみ。記録は `SESSION` に置く）

**Interfaces:**
- Consumes: Task 1 の追加済み SKILL.md、Spec の受け入れ条件、ベースライン pytest の結果（1483 passed・exit 0・`SESSION/baseline-pytest.log`）
- Produces: 検証の記録（`SESSION`。`--merge` のループで再利用する `--checks-file` の形を含む）

**テストの要否:** 不要（同上）。代わりの検証: 下の必須検証コマンドと条件単位の照合。

- [ ] **Step 1: 必須検証コマンドを実行する**

worktree のルートで実行する（monitoring-long-tasks に従い、長時間はバックグラウンド＋完了通知で待つ）:

1. `bash scripts/check-layout.sh` → 終了コード 0
2. `uv run pytest` → 終了コード 0・ベースライン（1483 passed）と比較して新規の失敗なし

- [ ] **Step 2: 受け入れ条件を条件単位で照合する**

`git diff bce027ba...HEAD -- .agents/skills/issue-to-pr/SKILL.md` と SKILL.md の該当節を読み、Review Focus の 1〜5 と受け入れ条件 1〜4 を確認する。結果を `SESSION/sdd/2026-11-13-issue-417-review-runner-write-guard/progress.md` に記録する。

- [ ] **Step 3: 検証の記録を作る**

`SESSION` に、検証した HEAD・そのときの `git status --porcelain` が空だったこと・各コマンドの argv と終了コード・ログの完全パス・base（`CODE_BASE_SHA` = `bce027ba003a4090fee3f4a2e9c85a6383009e51`）を記録する。`finalize.py` の `--checks-file` の形（`{"head": …, "base": …, "commands": [{"argv": …, "exit_code": 0}]}`）のファイルも作る。

## 実行予算

- Issue 全体の能動時間の予算: 90 分（controller の能動時間。runner・テストの待機時間は含まない）。内訳の目安: Spec・Plan 作成 30 分、実装・統合確認 20 分、検証・PR 作成 20 分、ループの計画・修正 20 分
- phase の目安: Spec レビュー 1 回（role 期限 1800 秒）＋再レビュー最大 1 回（実施済み: 1 回・再レビューなし）。実装 1 Task。ループは最大 3 サイクル（`--merge` の既定。各サイクルの inspect 期限 2700 秒＋計画・修正）
- worker の期限・予約枠: Spec レビューは runner の role 期限（1800 秒）に従う。controller 側の追加の予約枠は設けない。無進捗の打ち切りは runner の期限に委ねる（monitoring-long-tasks の stall 報告は行う）
- 失敗の種類ごとの再試行の上限: Spec レビューの再レビューは helper の許す 1 回のみ。runner の失敗（`state: failed`・`response_failed` など）は再試行せず停止して報告する（暗黙の担当切り替えなし）。検証の失敗は systematic-debugging で調べ、解消できなければ停止
- checkpoint の時点: Spec レビューの採否確定時（済み）、Task 1 完了時、PR 作成前、ループの各サイクル終了時
- 縮小・切り出し・方法変更の候補: ループがサイクル上限に達したら `fixes_pushed` で終える（継続は利用者が判断）。Spec レビューの指摘が編集範囲を超える場合は停止して確認する
- ループの段階の予算: 3 サイクル ×（レビュー 45 分＋計画・修正 30 分）を目安の上限とする

## contingency（代替策）

- Spec レビューの runner が失敗した場合: 成功扱いせず停止し、`review_dir`・理由・再依頼の選択肢を利用者に報告する。builder check で代えない（実施済みの 1 回目は completed）
- 最初の RED（検証の失敗）で実出力・API の前提が異なると判明した場合: 仕様の意味を保つ最小修正を ledger に残して継続する。意味が変わる場合は利用者の裁定を待つ
- 追加文面が監査仕様と矛盾すると判明した場合: 監査仕様を基準に文面を修正する（Spec の意味＝実行中の書き込み禁止は保つ）。受け入れ条件の意味が変わる場合は停止する
- 既存テストの回帰で新規の失敗が出た場合: systematic-debugging で原因を調べ、追加文面に起因するなら文面を修正、ベースライン由来なら記録して報告する
- 実行予算の縮小: ループのサイクル上限（3）は変更しない。controller の能動時間が予算を超えたら、checkpoint で状況を記録して続行の判断を行う

## 要件照合メモ（実装前の要件照合）

| Spec の条件 | Task | 観測結果 | 検証 |
| --- | --- | --- | --- |
| 受け入れ条件 1（レビュー側 3 要素＋3 種類への適用） | Task 1 追加 A | 追加段落の文面 | Task 2 照合・`git diff` |
| 受け入れ条件 2（実装側・既存記述との整合） | Task 1 追加 B | 追加段落の文面 | Task 2 照合・`git diff` |
| 受け入れ条件 3（テスト不要・検証で代える） | Task 2 | check-layout・pytest の終了コード | 必須検証コマンド 1・2 |
| 受け入れ条件 4（編集対象の限定） | Task 1・2 | `git diff --stat` の対象ファイル | Task 2 照合・`git diff` |
| 除外範囲（監査実装・他スキル・frontmatter 不変更） | Task 1・2 | `git diff` に該当パスの変更なし | Task 2 照合・`git diff` |

共有する入力・状態・順序・外部仕様の確認（監査仕様の語義・挿入位置の既存文脈）は統合担当の Task 2 で条件単位に確認する。

## 実行方式

`self`（このセッション）が `superpowers:executing-plans` で実装する。理由: 同一ファイルへの 2 箇所の追加という 1 Task の逐次変更で、SDD の委譲条件に当たらないため（Spec D5）。`--merge` 適用のため、最終のブランチ全体レビューはループの 1 サイクル目で代える（Task ごとのレビューは残す）。

## 検証の入口

リポジトリルートの AGENTS.md・README.md より: `scripts/check-layout.sh`（配置・symlink の検査）、`uv run pytest`（tests/skills・.agents/skills・.agents/scripts・tools の既存テスト）。GitHub Actions は無効（CI 確認不要・ローカルで実行）。

## 記録

- ledger: `SESSION/sdd/2026-11-13-issue-417-review-runner-write-guard/progress.md`
- 検証の記録（`--merge` のループで再利用）: Task 2 Step 3 のとおり `SESSION` に作る