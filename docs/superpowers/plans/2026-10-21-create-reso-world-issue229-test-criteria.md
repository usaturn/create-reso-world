# Issue #229: テストの採用基準を改める Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `AGENTS.md` の「テストの採用基準」を、#228 の「削除と採用の基準」に沿った新しい節（F・F∩S・L・S・D の分類と、書くとき・書かないときの手順）に置き換える。

**Architecture:** `AGENTS.md:18-33` の節だけを、Spec の設計 1 の文で置き換える。テストは足さず、節と Spec の照合、節の外が変わっていないことの確認、参照の実在の検査、README の「テスト」の入口で検証する。スキルの食い違いの候補は変えずに #228 に報告する。

**Tech Stack:** Markdown（`AGENTS.md`）、bash（`tests/scripts/test-instructions.bash` の参照の検査、`scripts/check-layout.sh`）、pytest

**Spec:** `docs/superpowers/specs/2026-10-21-create-reso-world-issue229-test-criteria-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/229（親 #228、子のキー `criteria`）
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-229-test-criteria`（branch `feat/issue-229-test-criteria`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: Spec の「管理・実行許可」と同じ（`/issue-to-pr https://github.com/usaturn/create-reso-world/issues/229 --merge`。PR の作成後に PR 修正ループを回し、修正不要ならループの `finalize.py` がマージする）
- 実行方式: inline（`superpowers:executing-plans`）。`implement_task.py check` の `self` が true で、変更は `AGENTS.md` の 1 節と、それを照合する統合確認の 2 Task である。同じファイルを順に扱うので委譲しても並行できず、文脈を渡す手間が上回る。独立したレビューは Task 2 の最後のブランチ全体のレビュー（新しいコンテキストのサブエージェント 1 回）で受ける
- 検証のログ・実行の記録（ledger `budget.jsonl` を含む）: `/workspaces/reso-world/tmp/agents/issue-229.6ce3napi/`（commit しない。worktree の中には置かない）。以下 `$SESSION`
- 基準: `origin/main` の `7d44355`。最後のレビューの間に PR #237 がマージされたので、2026-10-21 16:58 JST に未 push の branch を `d643cda` に rebase した（「検証の記録」）

## Global Constraints

- 変えるのは `AGENTS.md` の「テストの採用基準」の節（`AGENTS.md:18-33`）だけ。節の名前「テストの採用基準」は変えない（スキルの本文と過去の Spec が名前で参照している）
- 節の本文は Spec の設計 1 のコードブロックの中身をそのまま使う。文を変えるときは、先に Spec を直して commit する
- 節の中の backtick には、実在するパス（`scripts/check-layout.sh`）と、`tests/scripts/test-docs.bash` の `check_refs` が対象にしないもの（`GIT_*`・`HOME`・`git diff`）だけを書く。SKILL.md は backtick で囲まない（ルートに無いので参照の検査が失敗する）
- テストのファイル、スキルの本文（SKILL.md・`references/`）、`.pi/APPEND_SYSTEM.md`、`CLAUDE.md`、`AGENTS.md` のほかの節は変えない
- テストは足さない（文書だけの変更。今の基準でも新しい基準でも書かない）
- `AGENTS.md` の「日本語表現」で避ける語（契約・原子的・製品・着地・正本・巡・席・実行器）を使わない

## Review Focus

- 領域ごとの子が、権限を決める frontmatter などの守りの固定値を、F の「SKILL.md の本文と frontmatter」に当たるとして消す → Task 2 の Step 2 のレビューで、F∩S の項が今の基準の文（安全な操作範囲・権限・凍結した履歴・利用者所有部分）と例で、これらを F から外していることを確かめる
- パスの脱出の拒否のような S のテストを、L の「誤った入力で例外を投げることだけを確かめるテスト」に当たるとして消す → Task 2 の Step 2 で、L のただし書き（拒否が壊れると危険な操作がエラーなしに進むものは S）を確かめる
- TDD の担当が、一時的なテストを worktree に残す → Task 2 の Step 2 で、TDD の項が「コミットしないファイルの置き場所」を指していることを確かめる
- 節の backtick が `test-docs.bash --refs AGENTS.md` を落とす → Task 1 の Step 4 で `bash tests/scripts/test-instructions.bash` を実行する
- 節の名前で参照するスキル（issue-to-pr・review-fix-planning）が参照先を失う → Task 1 の Step 4 で見出しが 1 つだけ残っていることを確かめる

## 要件と Task・検証の対応

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1. 節に Issue の 1〜7 がある | Task 1、統合は Task 2 | 節の文が Spec の設計 1 と同じで、設計 2 の表の各行が節の文を指す | Task 1 の Step 2（Spec と節の diff が空）、Task 2 の Step 2（レビューで 1〜7 を照合） |
| 2. `AGENTS.md` の変更が節の中だけ | Task 1 | 節を除いた `AGENTS.md` が merge-base と同じ | Task 1 の Step 3 |
| 3. テストを足していない | Task 1・Task 2 | ブランチの変更が `AGENTS.md`・Spec・Plan の 3 ファイルだけ | Task 2 の Step 1 |
| 4. `git diff --check` が空、`check-layout.sh` が 0、README の入口で失敗が無い | Task 1・Task 2 | 各コマンドの終了コード 0 | Task 1 の Step 4、Task 2 の Step 4 |
| 5. 食い違いの候補を #228 に報告 | PR の作成の後（下の「PR と PR 修正ループ」） | #228 のコメントの URL | コメントを読み戻す |

共有する前提: 節の文（Spec の設計 1）を Task 1 が写し、統合担当の Task 2 が Spec の受け入れ条件・#228 の基準と照合する。ほかに共有する入力・状態は無い。

## 実行予算

- Issue 全体の能動時間の予算: 360 分（ledger: `$SESSION/budget.jsonl`、2026-10-21 16:26 JST に開始）。根拠は #221（300 分の予算で、コードと文書 3 つ、ループを含む）。この Issue は文書 1 節だけだが、PR 修正ループ（最大 3 サイクル）を含む
- phase の目安: 準備・調査 25 分（済）、Spec 25 分（済。builder check の 7 分を含む）、Plan 15 分、Task 1 10 分、Task 2 60 分（README の入口の約 20 分、レビューの待ち約 15 分、記録）、PR 15 分（検査・push・PR・#228 への報告）、PR 修正ループは残り（最大 3 サイクル ×（レビューの期限 45 分＋計画・修正 30 分）のうち、予算に収まる範囲）
- worker は使わない（inline）。最後のレビューのサブエージェントは 1 回だけ起動する。長時間の実行（`run-tests.bash`・pytest 全体）はバックグラウンドで実行し、終了コードで確かめる。1 回の期限は 30 分。README の入口は並行させず順に実行する
- 再試行の上限: 同じ signature の信頼性の失敗（テストの時間切れ・環境の I/O の停止）は 1 回まで。安全の失敗（想定外の外部への書き込み、親の checkout や他の worktree の書き換えの疑い、本物の担当の想定外の起動）は再試行せず止まる
- checkpoint: Task 1 の後、Task 2 の後、PR の作成の後、ループの各サイクルの後、予算の 50%・100%（100% では停止して報告する）
- 縮小・方法変更の候補: README の入口が負荷で落ちたら（#218）、落ちたテストだけを単独で再実行し、基準（`7d44355`）の同じテストと比べて、この変更による失敗かを判定する。レビューの指摘で節が長くなりすぎるときは、例を削る前に Spec の決定記録（D-229-3）と照合する

## Task 1: 「テストの採用基準」の節を置き換える

**Files:**
- Modify: `AGENTS.md:18-33`

**Interfaces:**
- Consumes: Spec の設計 1 のコードブロック（見出し `## テストの採用基準` から最後の項まで）
- Produces: 新しい節。見出しは `## テストの採用基準` のまま

**テストの要否:** 書かない。文書だけの変更で、今の基準でも新しい基準でもテストを書かない。代わりに、Spec との照合、節の外の不変、参照の実在の検査、`git diff --check` で確かめる。

- [x] **Step 1: 節を置き換える**

`AGENTS.md` の `## テストの採用基準` の行から、`## resoloop 注意` の前の空行の手前まで（今の 18〜33 行目）を、Spec の設計 1 のコードブロックの中身で置き換える。`## resoloop 注意` の前の空行 1 行は残す。

- [x] **Step 2: 節が Spec と同じことを確かめる**

~~~bash
diff <(sed -n '/^## テストの採用基準$/,/^## resoloop 注意$/p' AGENTS.md | sed '$d' | sed '$d') \
     <(sed -n '/^```markdown$/,/^```$/p' docs/superpowers/specs/2026-10-21-create-reso-world-issue229-test-criteria-design.md | sed '1d;$d')
~~~

Expected: 出力なし、終了コード 0

- [x] **Step 3: 節の外が変わっていないことを確かめる**

~~~bash
strip_section() { sed '/^## テストの採用基準$/,/^## resoloop 注意$/{/^## resoloop 注意$/!d;}'; }
diff <(git show "$(git merge-base origin/main HEAD)":AGENTS.md | strip_section) <(strip_section < AGENTS.md)
~~~

Expected: 出力なし、終了コード 0（節の見出しから次の見出しの前までを除くと、merge-base の `AGENTS.md` と同じ）

- [x] **Step 4: 参照の実在、見出し、空白の誤りを確かめる**

Run: `bash tests/scripts/test-instructions.bash`
Expected: `PASS: root instruction imports, references and persona SHA`、終了コード 0

Run: `grep -c '^## テストの採用基準$' AGENTS.md`
Expected: `1`

Run: `git diff --check`
Expected: 出力なし、終了コード 0

- [x] **Step 5: Commit**

```bash
git add AGENTS.md
git commit -m "docs(agents): rewrite the test adoption criteria for the #228 board (#229)"
```

## Task 2: 統合確認と最後のレビュー

**Files:**
- Modify: `docs/superpowers/plans/2026-10-21-create-reso-world-issue229-test-criteria.md`（チェックと「検証の記録」）

**Interfaces:**
- Consumes: Task 1 の commit

**テストの要否:** 書かない。ここではブランチの範囲、ブランチ全体のレビュー、README の入口で、条件単位の証拠をそろえる。

- [x] **Step 1: ブランチの範囲を確かめる**

Run: `git diff --name-only origin/main...HEAD`
Expected: `AGENTS.md`、Spec、Plan の 3 ファイルだけ（テストのファイルが無い）

- [x] **Step 2: ブランチ全体のレビュー**（新しいコンテキストのサブエージェント 1 回）

Spec・Plan・Issue #229 の本文・#228 の「利用者の決定」と「削除と採用の基準」・`git diff origin/main...HEAD` を渡し、次を見てもらう。(1) Issue の「書く内容」1〜7 と受け入れ条件を満たすか、(2) #228 の決定と基準を変えていないか（決定済みの方針を議論し直していないか）、(3) S のテストを消しうる書き方（F∩S・L の境界）が無いか、Review Focus の 3 行、(4) `AGENTS.md` の「日本語表現」と、ほかの節（「コミットしないファイルの置き場所」など）との食い違い、(5) 変更が節の中だけか。致命的な指摘だけを直す。節の文を直すときは、先に Spec の設計 1 を直して commit し、Task 1 の Step 2〜4 をやり直す

- [x] **Step 3: Plan の「検証の記録」を書いて commit する**（これが最後の commit）

各 Step のチェック、Task 別の所要時間、Task 1 の Step 2〜4 と Task 2 の Step 1 の結果、レビューの結果と対応を「検証の記録」に書き、`git commit -m "docs: record the Issue #229 verification and final review in the plan"`

- [ ] **Step 4: 最後の commit で README の「テスト」の入口を実行し、検証の記録を作る**（`--merge` のループで再利用する）

最後の commit の上で `git status --porcelain` が空であることを確かめてから、worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` をバックグラウンドで順に実行する（各 30 分まで。並行させない）
Expected: 3 つとも終了コード 0。落ちたら、落ちたテストを単独で再実行し、基準（`7d44355`）の同じテストと比べて、この変更による失敗かを判定する。検証した HEAD・`git status --porcelain` が空だったこと・各コマンドの argv・終了コード・ログの完全パスを `$SESSION/verify/record.md` に、`finalize.py --checks-file` の形（`{"head", "base", "commands"}`。`base` は検証したツリーが含む `origin/main` の SHA）を `$SESSION/verify/checks.json` に書く。結果は Plan に書かず（HEAD が変わるので）、PR 本文に書く

## PR と PR 修正ループ（issue-to-pr の 5 章）

- push の前に、Issue の状態と競合、予約 ref が自分の SHA（`5df1a4c`）のままであることを確かめ直す。`PARENT_ROOT` の `scripts/scan-before-push.sh` で検査し、検査した SHA を `refs/heads/feat/issue-229-test-criteria` に push する
- `gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-229-test-criteria`（draft にしない）。本文は `Closes #229`、変更概要、Spec の決定と理由、実行方式と理由、検証と結果、作業時間と Task 別の内訳
- PR の作成の後、#228 に、スキルの食い違いの候補と F∩S の申し送り（Spec の D-229-7）をコメントし、読み戻す。#229 に状態（`planning: ready / implementation: in-progress`、PR の URL）をコメントする
- `PARENT_ROOT` の `loop.py start` でループを回す（`--controller-model claude-opus-5-5 --controller-runtime claude-code`。ループ用のオプションは利用者が書いていないので渡さない）。1 サイクル目で修正不要かつサイクルの HEAD が Task 2 の Step 4 の HEAD と同じなら、`$SESSION/verify/checks.json` を `finalize.py` の `--checks-file` に使う
- ループの `finish` の後に、結果と再開の方法を #229 に書いてから、予約を `--force-with-lease=refs/heads/agent-claims/issue-229:5df1a4c2b86be52ee6a31be98d712098a33fe548` で解放し、ref が無いことを確かめる

## 検証の記録

ログはどれも `/workspaces/reso-world/tmp/agents/issue-229.6ce3napi/` にある（commit しない）。SDD の ledger は `sdd/progress.md`（判定は `Ruling:` の行）、予算の ledger は `budget.jsonl`。

### Task 1（`98f4310`。rebase の前は `10d8ff7`）

- Step 1: 節を Spec の設計 1 のコードブロックから差し込んだ（`AGENTS.md` の 18〜33 行目が 18〜30 行目になった）
- Step 2: Spec と節の diff は空（終了コード 0）
- Step 3: 節を除いた `AGENTS.md` と merge-base の diff は空（終了コード 0）
- Step 4: `bash tests/scripts/test-instructions.bash` は `PASS: root instruction imports, references and persona SHA`（終了コード 0）、見出しは 1 つ、`git diff --check` は空。`AGENTS.md` の「日本語表現」で避ける語は節に無い

### Task 2

- Step 1: `git diff --name-only origin/main...HEAD` は `AGENTS.md`・Spec・Plan の 3 ファイル（テストのファイルは無い）
- Step 2（ブランチ全体のレビュー。新しいコンテキストの Opus のサブエージェント 1 回、約 13 分）: With fixes。Critical 0、Important 1、Minor 4。レビュアーは `test-instructions.bash`・`check-layout.sh`・`git diff --check`・Spec との diff・節の外の diff を自分で実行し、どれも期待どおりだった
  - I-1（L のただし書きが危険な操作に限られ、ほかの S の損害を防ぐ拒否・停止のテストを L と読める）: 直した（Spec `d02f713`、`AGENTS.md` `d436ae7`。D-229-4）
  - M-1（「既存の検査」にほかのテストを含めて読める）・M-3（F∩S の「使ってよい」が消してよいとも読める）: どちらも #228 の決定 6 が禁じる S のテストの削除につながるので、効果で Important に上げて同じ修正で直した（D-229-11・D-229-12）
  - M-2（冒頭の 2 文目が L・S の軸だけを書いている）・M-4（「迷うもの」が節に無い）: S のテストの削除にはつながらないので直さない（持ち越し）
  - 直した後に Task 1 の Step 2〜4 をやり直し、すべて期待どおりだった
  - レビュアーが判断しなかった 9 項目への判定は ledger の `Final: Ruling:` の行に書いた。`AGENTS.md:154` が参照する `tests/scripts/test-scan-before-push.bash` の件は #228 に報告する（Spec の「確認した事実」）
- rebase: レビューの間に PR #237 が `main` にマージされた（`d643cda`）。#237 はこの branch のファイルを変えないので、未 push の branch を `d643cda` に rebase した。commit の対応は `9f75b67`→`e5f0b29`（Spec）、`c5d6638`→`964410a`（Plan）、`10d8ff7`→`98f4310`（Task 1）、`b694c10`→`d02f713`（Spec の修正）、`064a6c9`→`d436ae7`（`AGENTS.md` の修正）。rebase の後に Task 1 の Step 2〜4 と Task 2 の Step 1 をやり直し、すべて期待どおりだった
- Step 4（README の「テスト」の入口）の結果は、HEAD が変わるので PR 本文に書く

### 所要時間（Task 2 の Step 3 の commit まで）

- 着手は 2026-10-21 16:15（JST）頃（予約の作成は 16:20）
- 準備・調査（入力の検査、予約、worktree、規約と関連箇所の確認）約 12 分、Spec 約 11 分（builder check の待ち 7 分を含む）、Plan 約 2 分、Task 1 約 1 分、Task 2（レビューの待ち 13 分、修正、rebase、記録）約 20 分
