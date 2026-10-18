# issue-to-pr の push 前検査 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`（issue-to-pr の実行許可で進める。内容の承認ではない）
- Issue: https://github.com/usaturn/create-reso-world/issues/139

**Goal:** issue-to-pr の 5 章の push を、`AGENTS.md` の「push の前の秘密情報の検査」の形（検査した SHA だけを明示の refspec で送る）にし、検査で止まる場合を停止条件に足す。

**Architecture:** `.agents/skills/issue-to-pr/SKILL.md` の 5 章に検査と push のコマンドを書き、`finishing-a-development-branch` の `git push -u` を置き換える。停止の条件と報告は「停止時の報告」に足す。行動比較のシナリオ (k)〜(o) を `evals/scenarios.json` に足し、結果を `evals/validation.md` に書く。

**Tech Stack:** Markdown（SKILL.md）、JSON（evals）、bash（`scripts/scan-before-push.sh`。変更しない）

**Spec:** `docs/superpowers/specs/2026-10-17-create-reso-world-issue139-scan-before-push-design.md`

## Global Constraints

- 変更するのは `.agents/skills/issue-to-pr/SKILL.md`、`.agents/skills/issue-to-pr/evals/scenarios.json`、`.agents/skills/issue-to-pr/evals/validation.md`、この Plan と Spec だけ
- 検査は `bash "$PARENT_ROOT/scripts/scan-before-push.sh" -C <worktree>`。対象の worktree のスクリプトを使わない
- push は `git -C <worktree> push origin "${SHA}:refs/heads/<branch>"`（`[ -n "$SHA" ]` を確かめる。`$SHA:r` にしない）
- 公開する worktree をすべて検査してから push する
- 検出・失敗・gitleaks が無い・版が違うときは、push も PR の作成もせずに止まる。`.gitleaksignore`・inline の `gitleaks:allow`・作業ツリーの `.gitleaks.toml`・base の `.gitleaks.toml` の変更で回避しない。gitleaks を自分で導入しない
- 文面を照合するテストを書かない（`AGENTS.md` のテストの採用基準）

## Review Focus

- `PARENT_ROOT` が #133 より前の版でスクリプトが無い → 必要なツールの失敗として止まる（SKILL.md の停止条件に含まれること）
- 検査が全部通った後に 2 つ目の push か PR の作成が失敗する → 公開済みの branch・PR を報告し、取り消さない
- 検査の後に commit を足す（誤字の修正など）→ 検査からやり直す
- 既存の PR の branch への再 push（public の checks の修正）→ 同じ検査付きの push。force push・新しい PR はしない
- 外部の対象で、文書側だけが検出で止まる → コード側も push しない

各項目は行動比較のシナリオ (k)〜(o) で確かめる（Task 1 の Step 1・Step 4）。

## 実行方式

`superpowers:executing-plans`（inline）。変更は同じ `SKILL.md` への逐次の書き換えと evals の追記で、Task は互いに依存する。行動比較の回答の判定は controller が全回答を読んで行うので、実装を子に渡しても文脈を渡しきれない。

## 実行予算

- 全体の能動時間: 60 分（ledger `/workspaces/reso-world/tmp/agents/issue-139.n4jc4s8t/budget.jsonl`。pi のセッションが開始した ledger を引き継ぐ）。根拠: 1 ファイルの手順の書き換えと評価で、#114 の評価（7 シナリオ × 2 版 × 2 回）より小さい
- phase の目安: Spec の見直し 5 分、builder check と対照の評価 10 分、Task 1 の実装 10 分、変更後の評価 10 分、Task 2 と検証 10 分、全体レビュー・push・PR 15 分
- worker: 評価と builder check のサブエージェント（Agent ツール）は各 15 分で打ち切る。全体レビューのサブエージェントは 20 分
- 再試行: 同じ失敗の再試行は 1 回まで（ledger の `retry_limit` 1）
- checkpoint: phase の境界、予算の 50%・100%、worker が失敗した直後
- 縮小・切り出し・方法変更の候補: 評価の回数を版ごとに 2 回にする。(o) を外す。サブエージェントが使えなければ、controller が版ごとに 1 回ずつ答えを作るのではなく停止する（自己評価で代えない）

---

### Task 1: SKILL.md の 5 章と停止条件

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`（5 章の 2 つ目と 4 つ目の項目、「停止時の報告」の 1 段落目）

**Interfaces:**
- Consumes: `scripts/scan-before-push.sh` の終了コード（0 成功、1 検出・失敗、2 使い方の誤り）と、成功時に標準出力に出る SHA の 1 行
- Produces: Task 2 が記録する、変更後の `SKILL.md` の版（commit SHA）

テストの要否: 書かない。SKILL.md の文面の変更で、実行して確かめるコードが無い（テストの採用基準の「書かない」）。代わりに行動比較で確かめる。

- [x] **Step 1: 対照の行動比較（RED）**

`origin/main`（`50e4a6b`）の `SKILL.md` を scratchpad に写し、`AGENTS.md` と一緒に読ませて、(k)〜(o) を 1 つの指示文で 3 回答えさせる（Agent ツール、model `sonnet`、Read 以外のツールを使わせない）。全回答を読み、期待（Spec の受け入れ条件）を外した点と、その理由づけを記録する。

- [x] **Step 2: 5 章を書き換える**

- 2 つ目の項目: 「push して」を、公開する worktree をすべて検査し、全部が通ってから `"${SHA}:refs/heads/<branch>"` で push する手順にする。`finishing-a-development-branch` の `git push -u origin <branch>` は使わないと書く。コマンド例は `CODE_SHA`（と `DOC_SHA`）を使う
- 4 つ目の項目（文書用の branch）: 検査は 2 つ目の項目でコードと一緒に済ませたことを前提に、`DOC_SHA` を push すると書く
- 検査の後に commit を足したら検査からやり直す、CI の修正の再 push も同じ形、と書く（CI の項目か 2 つ目の項目）

Step 1 で対照が既に満たした項目には、強調を足さない。

- [x] **Step 3: 「停止時の報告」に検査の停止を足す**

停止条件の列挙に「push の前の検査の検出・失敗（gitleaks が無い・版が違うを含む）」を足す。回避の禁止、gitleaks を自分で導入せず `bash "$PARENT_ROOT/.devcontainer/install_gitleaks.bash"` を案内すること、報告に検出の位置と push 済み・まだのものを書くこと、一部だけ公開されたら取り消さないこと、を足す。

- [x] **Step 4: 変更後の行動比較（GREEN）**

Step 1 と同じ指示文で、変更後の `SKILL.md` の写しを読ませて 3 回答えさせる。期待を外した点があれば、文面を直して同じ手順で答えさせ直す（REFACTOR）。

- [x] **Step 5: Commit**

```bash
git add .agents/skills/issue-to-pr/SKILL.md
git commit -m "fix: scan before pushing in issue-to-pr"
```

### Task 2: 評価の記録

**Files:**
- Modify: `.agents/skills/issue-to-pr/evals/scenarios.json`（`scenarios` の末尾に (k)〜(o)）
- Modify: `.agents/skills/issue-to-pr/evals/validation.md`（末尾に節を足す）

**Interfaces:**
- Consumes: Task 1 の Step 1・Step 4 の回答、変更後の `SKILL.md` の commit SHA
- Produces: なし

テストの要否: 書かない。評価の記録で、実行して確かめるコードが無い。代わりに JSON の構文と参照先の実在を確かめる。

- [x] **Step 1: scenarios.json に (k)〜(o) を足す**

各項目に `id`（`k-push-create-reso-world`・`l-push-two-worktrees`・`m-detection-in-docs-worktree`・`n-gitleaks-version-mismatch`・`o-repush-after-ci-fix`）、`added`（#139 で足したこと、対照と比較の版、回数、共通の状況の追加分）、`prompt`、`expected` を書く。既存の項目は変えない。

- [x] **Step 2: validation.md に節を足す**

評価の方法（版・回数・指示文の共通の状況）、シナリオごとの結果の表（対照 3 回・変更後 3 回）、対照で外れた点と文面に足した理由、行っていない確認を書く。既存の結果は書き換えない。

- [x] **Step 3: 構文と参照を確かめる**

Run: `uv run --no-project python -m json.tool .agents/skills/issue-to-pr/evals/scenarios.json > /dev/null`
Expected: 終了コード 0

- [x] **Step 4: Commit**

```bash
git add .agents/skills/issue-to-pr/evals/scenarios.json .agents/skills/issue-to-pr/evals/validation.md
git commit -m "docs: record issue-to-pr push scan evaluation"
```

### Task 3: 全体の検証・レビュー・PR

**Files:**
- Modify: この Plan（「完了」の節）

テストの要否: 新しいテストは無い。既存のテストの入口で回帰を確かめる。

- [x] **Step 1: README の「テスト」の 3 つ**

Run（worktree のルート）: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts`
Expected: 3 つとも終了コード 0。失敗したら `systematic-debugging` で調べ、この変更の原因でなければ環境要因として結果を記録する

- [x] **Step 2: `git diff --check origin/main...HEAD` と差分の確認**

Expected: 出力なし。差分は Global Constraints のファイルだけ

- [x] **Step 3: ブランチ全体のレビュー**

`superpowers:requesting-code-review` で、新しいサブエージェントにブランチ全体（`origin/main...HEAD`）をレビューさせる。致命的な指摘だけを直す

- [x] **Step 4: Plan に「完了」の節を書いて commit**

- [ ] **Step 5: 検査付きの push と PR**

Issue の状態と競合を調べ直してから、`SHA="$(bash /workspaces/reso-world/scripts/scan-before-push.sh -C /workspaces/reso-world/.worktrees/issue-139-scan-before-push)" && [ -n "$SHA" ] && git -C /workspaces/reso-world/.worktrees/issue-139-scan-before-push push origin "${SHA}:refs/heads/fix/issue-139-scan-before-push"`。続けて `gh pr create --repo usaturn/create-reso-world --base main --head fix/issue-139-scan-before-push`（本文に `Closes #139`）

## 完了

- 状態: 実装完了。Plan・Spec の状態は `draft` のまま（issue-to-pr の実行許可で進めた。内容の承認は受けていない）。push と PR の作成（Task 3 の Step 5）は、この記録の commit の後に行う
- Task 1: 対照（`50e4a6b`）の行動比較 3 回の後、`c91dc5c` で 5 章と停止条件を変え、変更後の行動比較 3 回で 5 つとも期待どおり。ブランチ全体のレビューの指摘で `c3db9c5` に直し、最終版でも 3 回とも期待どおり
- Task 2: `78b9815`・`2456c20`（`evals/scenarios.json` に (k)〜(o)、`evals/validation.md` に結果）
- Task 3:
  - README の「テスト」の 3 つ: `2456c20` で `bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`・`uv run pytest tests/skills .agents/skills .agents/scripts` がすべて終了コード 0（pytest は 625 passed）。ログは `/workspaces/reso-world/tmp/agents/issue-139.n4jc4s8t/tests-final.log`
  - `git diff --check origin/main...HEAD` は出力なし。差分は Global Constraints の 5 ファイルだけ
  - ブランチ全体のレビュー: 判定は Yes、Critical なし。直したのは Important 1（空の SHA の refspec が branch の削除になる → `${SHA:?}`）、Minor 2（`DOC_SHA` の 2 行を除くと行末の `\` が残る → push の順序を文書・コードに）、Minor 5（(o) の対照の点数）、Minor 7（「人手で読んだ」の表現）。Minor 4（Spec の挙動 6・7 の一部を文面に入れていない）は理由を `validation.md` と Spec に書いた。Minor 3（文書の PR の `--head`）は変更後の評価で 3/3 正しかったので直していない。Minor 6 は同じ行を直すときに文を直した
- 計画からの逸脱:
  - Task 1 Step 3 の「報告に検出の位置を書く」は、対照が 3/3 で満たしたので文面に入れなかった
  - Task 1 Step 2 の push の順序は、レビューの指摘で文書・コードの順にした
  - 最初のテストの実行は、zsh が `$c` を単語に分割しないので 3 つともコマンドとして実行されなかった（終了コード 127）。明示的に書き直して実行し直した
- 実行予算: ledger の能動時間は約 31 分（pi のセッションの約 3 分を含む）、使用率 51%。50% の checkpoint は `continue`。同じ失敗 `subagent-api-key-expired` は pi のセッションで上限に達し、Claude Code のセッションへの方法変更（`change-method`）で解消した
