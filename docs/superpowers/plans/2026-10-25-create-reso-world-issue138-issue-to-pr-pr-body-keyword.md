# Issue #138 issue-to-pr の PR 本文の Issue の指定 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** issue-to-pr が、マージの後の確認が残る Issue とボードの子を `Refs #N` にし、残りの確認を記録し、マージ済みの PR で作業が済んだ Issue で作り直さずに止まるようにする。

**Architecture:** 変えるのは `SKILL.md` の文面だけ。5 章の PR 本文の Issue の指定を条件ごとの対応にし、`--merge` の結果の表と 2 章の 6 の停止をそれに合わせる。振る舞いは sonnet のサブエージェントの行動比較（対照で外れることを先に確かめる）で確かめ、`evals/` に記録する。

**Tech Stack:** Markdown、JSON、Claude Code の Agent ツール（model `sonnet`）。

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue138-issue-to-pr-pr-body-keyword-design.md`

状態: draft。実行許可は利用者の `/issue-to-pr #138 --merge --max-cycles 3`。内容の承認を意味しない。

## Global Constraints

- 変えるのは `.agents/skills/issue-to-pr/SKILL.md`・`evals/scenarios.json`・`evals/validation.md` と、この Spec・Plan だけ（Spec の「対象外」、D7）
- pytest のテストは書かない（Spec D8）
- 本物のモデルを起動するのは Task 1 の 3 回と Task 3 の 6 回だけ。Task 3 の contingency で最大 6 回を足す（Spec D9）
- 変更は `/workspaces/reso-world/.worktrees/issue-138-pr-body-keyword`（branch `fix/issue-138-pr-body-keyword`）で行う。ログ・ledger・評価の材料は `/workspaces/reso-world/tmp/agents/issue-138.2he3b_ok/` に置く
- 指示文は簡潔に書く

## Review Focus

| 観点 | Task と検証 |
| --- | --- |
| 別のリポジトリの Issue にマージの後の確認が残っても、`Refs #N`（実装の対象のリポジトリの番号）にせず `Refs <URL>` のままにする | Task 1 と Task 3 の (pe) |
| `.devcontainer/` などを直すが受け入れ条件がこの run で確かめられる Issue を、`Refs` にしない（条件の当てすぎ） | (pc) |
| `--merge` で `finalize.py` が `Refs #N` の Issue を閉じないことを、未完了や失敗と報告しない | (pd) |
| マージ済みの `Refs` の PR が残した Issue で、worktree を作ってから残りを整理しない | Task 3 の (i) |
| 今までの場面（通常の Issue の `Closes`、別のリポジトリの `Refs <URL>`、各停止）が変わらない | Task 3 の (a)〜(h)・(j) |

## 実行方式

`implement_task.py check` の結果は `agents: [self]`、`fallback: []`、`self: true`（Spec D11）。Task は 4 つで、Task 2 は Task 1 の対照の結果を読んでから書き（writing-skills の RED → GREEN）、Task 3 は Task 2 の `SKILL.md` に、Task 4 は全部に依存する。同じファイルの逐次変更で、子に渡す文脈が作業より大きいので、issue-to-pr の 4 章の表のとおり `superpowers:executing-plans` で、このセッションが順に実装する。評価のサブエージェントは評価の方法（Spec D9）で、実装の委譲ではない。最後に、新しいサブエージェント（Claude Code の既定のモデル）にブランチ全体をレビューさせる。SDD の作業領域は `/workspaces/reso-world/tmp/agents/issue-138.2he3b_ok/sdd/2026-10-25-create-reso-world-issue138-issue-to-pr-pr-body-keyword/`。

## 実装前の要件照合

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 受け入れ条件 1（(pa)・(pb)・(pc) の Issue の指定） | Task 2（変更の内容 1〜3）、Task 3 | 比較の版で 3/3 | Task 3 の Step 2 |
| 受け入れ条件 2（(pd) の `--merge` の後） | Task 2（変更の内容 2・4）、Task 3 | 比較の版で 3/3 | Task 3 の Step 2 |
| 受け入れ条件 3（(a)〜(j)） | Task 2（変更の内容 5）、Task 3 | (a)〜(h)・(j) が 3/3、(i) が 3/3 | Task 3 の Step 2・3 |
| D2 の `TARGET_REPO` に限る条件 | Task 2、Task 3 | (pe) で `Refs <URL>` のまま | Task 3 の Step 2 |

共有する条件は、「`Refs #N` で開いたまま残した Issue」の意味である。5 章の Issue のコメント（変更の内容 2）に書く確認の項目と PR の URL を、2 章の 6 の停止（変更の内容 5）が読み、`--merge` の結果の表（変更の内容 4）は `finalize.py` が `closingIssuesReferences` だけを閉じる挙動を前提にする。この 3 か所が同じ前提で読めるかを、統合担当（このセッション）が Task 4 の Step 1 で確かめる。

## 実行予算

1. 全体の能動時間: 330 分。根拠: #137（文面と helper の変更、9 回の行動比較）は PR の作成まで約 2 時間。今回はコードの変更が無く、行動比較は 9 回。`--merge` のループはサイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 20 分）で最大 195 分
2. phase の目安: 準備・Spec・Plan 35 分、RED 15 分、実装 15 分、評価と記録 35 分、検証・全体レビュー 25 分、PR 10 分、ループ 195 分
3. worker: `bash .devcontainer/run-tests.bash` と `uv run pytest tests/skills .agents/skills .agents/scripts tools` は、それぞれ絶対期限 20 分、無進捗の打ち切りは出力が 10 分増えないとき。評価のサブエージェントは 1 回 20 分を期限とする（出力ファイルは完了まで進捗にならないので、無進捗では打ち切らない）。ループは pr-review-fix-loop の期限に従う
4. 再試行: 同じ失敗の再試行は 1 回まで（既定）。評価のサブエージェントがツールの制限を破った回は、その回を捨てて 1 回だけ取り直す
5. checkpoint: phase の境界、予算の 50%（165 分）・100%、worker の失敗の直後
6. 縮小・切り出し・方法変更の候補: 比較の版で (pa)〜(pe) が 3/3 に届かなければ、文面を直して比較の (pa)〜(pe) を 1 回だけ取り直す（方法変更）。(a)〜(h)・(j) で外れたら、対照でも (a)〜(j) を 3 回取って切り分け、今回の変更が原因なら文面を直して比較の (a)〜(j) を 1 回だけ取り直す。それでも届かなければ、結果をそのまま記録し、PR に未達として書く

ledger は `/workspaces/reso-world/tmp/agents/issue-138.2he3b_ok/budget.jsonl`。

---

### Task 1: 評価の場面と材料を作り、対照の版で取る（RED）

**Files:**
- Modify: `.agents/skills/issue-to-pr/evals/scenarios.json`（(pa)〜(pe) を末尾に足す）
- 評価の材料と回答: `/workspaces/reso-world/tmp/agents/issue-138.2he3b_ok/eval/`（コミットしない）

**Interfaces:**
- Produces: `eval/shared/AGENTS.md`、`eval/<対照>/issue-to-pr/SKILL.md`（`git show c1fdc56:.agents/skills/issue-to-pr/SKILL.md`）、指示文 `eval/prompt-p-<版>.md`・`eval/prompt-aj-<版>.md`。`<対照>`・`<比較>` は意味の無い 3 文字の名前。Task 3 が同じ指示文を比較の版で使う

**テスト:** 書かない。行動比較そのものが検証。

- [ ] **Step 1: 材料を作る**

`AGENTS.md` は worktree の版を写す。指示文の書き出しと共通の状況は、PR #266 の評価の `/workspaces/reso-world/tmp/agents/issue-137.p0ogh8cd/eval/prompt-aj-q7m.md` と同じにし、ファイルのパスだけを変える。`prompt-aj-<版>.md` はその (a)〜(j) をそのまま使う。`prompt-p-<版>.md` は、共通の状況に次の 2 文を足し、場面を (pa)〜(pe)、問いを「各場面について、PR 本文に書く Issue の指定（`Closes #N`・`Refs #N`・`Refs <URL>` など）とその理由、PR の作成の後に行うこと（Issue へのコメント・Issue の close を含む）、最終報告に書くことを答えてください」にする。

```text
PARENT_ROOT の review-fix-planning の scripts/finalize.py は、マージの後に、PR の closingIssuesReferences（本文の `Closes #N` などで GitHub が PR に結び付けた Issue）を閉じる。`Refs` は結び付けない。
planning-parallel-issues は、後続の子の着手の条件を、先行の子が state_reason=completed で閉じたことにしている。親の実行マップと公開台帳は調整役が更新する。
```

- [ ] **Step 2: (pa)〜(pe) を scenarios.json に足す**

`added` に「#138 で追加」と方法（Step 1 の指示文、対照は `c1fdc56`、比較は #138 の版、各 3 回）を書く。

- (pa) `pa-post-merge-rebuild-check`: 利用者 `/issue-to-pr #220`。create-reso-world の Issue で、postCreate で shellcheck を導入する。受け入れ条件「コンテナを rebuild すると `shellcheck --version` が出る」、検証「実際の rebuild で導入と再実行を確かめ、結果をこの Issue に記録する」。この run では rebuild できない（導入スクリプトは一時 HOME で確かめた）。README の「テスト」の 3 つは通った。期待: `Refs #220`（`Closes` にしない）。rebuild の後に確かめる項目を PR 本文・最終報告と、run の最後の #220 のコメントに書く。この run では #220 を閉じない
- (pb) `pb-board-child`: 利用者 `/issue-to-pr #46`。#46 はボードの子（親 #40）で、スクリプトの小さな変更。予約 `refs/heads/agent-claims/issue-46` はこのセッションのもの。受け入れ条件はこの run のテストで確かめられ、README の「テスト」の 3 つは通った。期待: `Refs #46`。#46 の close と #40 の更新は、マージの後に調整役が行う（この run では閉じない）。結果を #46 に書いてから予約を解放する
- (pc) `pc-plain-issue-devcontainer-script`: 利用者 `/issue-to-pr #221`。`.devcontainer/install_gitleaks.bash` の版の比較の誤りを直す。受け入れ条件「`bash .devcontainer/run-tests.bash` に再現のテストを足して通る」。rebuild・実機の確認は無い。README の「テスト」の 3 つは通った。期待: `Closes #221`。マージの後の確認を作らない
- (pd) `pd-post-merge-check-with-merge`: 利用者 `/issue-to-pr #222 --merge`。(pa) と同じく受け入れ条件に rebuild の後の確認がある（この run では rebuild できない）。PR https://github.com/usaturn/create-reso-world/pull/99 を作り、ループが `no_fix_needed` で終わり、`finalize.py` がマージした。問いは PR 本文の Issue の指定、ループの後の #222 の状態、最終報告と #222 への書き込み。期待: `Refs #222`。`finalize.py` も run も #222 を閉じず、開いたまま残す。最終報告に、#222 が開いたままであることと確かめる項目を書く。ループの終了の後に、#222 へ、マージ済みの PR と確かめる項目をコメントする
- (pe) `pe-other-repo-post-merge-check`: 利用者 `/issue-to-pr #223`。create-reso-world の Issue で、本文に「実装の対象: usaturn/resoloop（checkout は external/resoloop）」。C# の修正で、受け入れ条件に「PR のマージの後に、fork のビルドを `scripts/resoloop-fork.sh install` で導入し、ワールドのプロジェクトで `resoloop doctor` が pass になる」。`dotnet test` は通った。期待: コードの PR（`--repo usaturn/resoloop`）は `Refs https://github.com/usaturn/create-reso-world/issues/223`（`Refs #223`・`Closes` にしない）、文書の PR も `Refs <URL>`。導入の後に確かめる項目を PR 本文・最終報告と #223 のコメントに書く

- [ ] **Step 3: 対照の版で (pa)〜(pe) を 3 回取る**

Agent ツールで新しいサブエージェント（model `sonnet`、`general-purpose`）を 1 回の起動で 1 回答、3 回並べて起動する。指示文は `prompt-p-<対照>.md` の内容。回答を `eval/answers/p-<対照>-<n>.md` に保存し、全回答を読んで場面ごとに判定する（文言の一致では採点しない）。ツールの呼び出しが Read の 2 回を超えた回は捨てて取り直す。
Expected: (pa)・(pb)・(pd) は外れる（`Closes` にする、確認の項目を Issue に書かない）。外れなければ、外れなかった場面を Task 2 で文面にしない（writing-skills の「対照が失敗しなければ文面を書かない」）

- [ ] **Step 4: commit する**

```bash
git add .agents/skills/issue-to-pr/evals/scenarios.json
git commit -m "docs: add issue-to-pr PR body keyword scenarios (#138)"
```

### Task 2: `SKILL.md` の Issue の指定と、マージ済みの PR での停止を書く（GREEN）

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`（2 章の 6 の一覧、5 章の PR 本文の項・ボードの子の項・`--merge` の結果の表、「停止時の報告」の停止条件）

**Interfaces:**
- Consumes: Task 1 の対照の結果（外れた場面と、その理由づけ）
- Produces: 比較の版の `SKILL.md`。Task 3 がこの版を読む

**テスト:** 書かない（Spec D8）。Task 3 の行動比較で確かめる。

- [ ] **Step 1: 文面を書く**

Spec の「変更の内容」1〜5 のとおり。Task 1 で外れなかった場面に当たる文は書かない。

- 5 章: 今の「PR 本文: Issue が `TARGET_REPO` にあれば `Closes #N`、…」の項を、Issue の指定の対応（変更の内容 1。理由は「`Closes` はマージの時に Issue を completed で閉じ、マージの後の確認や調整役の close を待たない」の 1 文）と、残りの確認を書く場所（変更の内容 2）と、変更概要などを書く項に分ける
- 5 章のボードの子の項: 「子の close と親の更新は、マージの後に調整役が行う」を足す
- 5 章の結果の表の `no_fix_needed`: 「`Refs #N` にした Issue は `finalize.py` が閉じない。開いたままであることと、その理由（残りの確認、ボードの子の調整役の close）を書く」を足す
- 2 章の 6: 「同じ Issue の open PR」の次に、「同じ Issue のマージ済みの PR があり（探し方は open PR と同じ）、本文・コメントから、PR にする作業が残っていないと分かる（残りがマージの後の確認だけ、など）。その PR の URL と残りの確認を報告する」を足す
- 「停止時の報告」の停止条件の「競合」の次に、「マージ済みの PR で PR にする作業が残っていない Issue」を足す

Ruling（実装中）: 対照で外れたのは (pb) だけだった。(pa)・(pd)・(pe) は 3 回とも「文面どおりなら `Closes`。規定が無いので私の判断」と規則から外れて期待どおりにしたが、実際の PR #253 は同じ状況で `Closes` にした。ボードの子だけを足すと例外を並べた表が rebuild の Issue を `Closes` に寄せるので、対応の表はマージの後の確認の条件も含めた。確認の項目を書く場所と `no_fix_needed` の行は書かず、ボードの子の close の担当は対応の行に書いた（3 か所の変更）。

- [ ] **Step 2: 差分を読む**

Run: `git diff -- .agents/skills/issue-to-pr/SKILL.md`
Expected: 上の 5 か所だけ。別のリポジトリの `Refs <URL>`、文書専用の PR の本文、ほかの手順・停止条件の文が変わっていない

- [ ] **Step 3: commit する**

```bash
git add .agents/skills/issue-to-pr/SKILL.md
git commit -m "docs: keep issues with post-merge checks open in issue-to-pr (#138)"
```

### Task 3: 比較の版で取り、評価を記録する

**Files:**
- Modify: `.agents/skills/issue-to-pr/evals/validation.md`（#138 の節を末尾に足す）
- 評価の材料と回答: `/workspaces/reso-world/tmp/agents/issue-138.2he3b_ok/eval/`（コミットしない）

**Interfaces:**
- Consumes: Task 1 の指示文と材料、Task 2 の `SKILL.md`

**テスト:** 書かない。行動比較そのものが検証。

- [ ] **Step 1: 比較の材料を作る**

Task 2 の `SKILL.md` を `eval/<比較>/issue-to-pr/SKILL.md` に写し、`prompt-p-<比較>.md`・`prompt-aj-<比較>.md` を、対照の指示文から SKILL.md のパスだけを変えて作る。

- [ ] **Step 2: 比較の版で (pa)〜(pe) と (a)〜(j) を 3 回ずつ取る**

方法は Task 1 の Step 3 と同じ。6 回を並べて起動し、`eval/answers/p-<比較>-<n>.md`・`aj-<比較>-<n>.md` に保存して判定する。(a)〜(j) の期待は今の scenarios.json のもの。
Expected: (pa)〜(pe) が 3/3。(a)〜(h)・(j) が 3/3。(i) が 3/3

- [ ] **Step 3: 届かなければ実行予算の 6 のとおりにする**

(pa)〜(pe) が外れたら、外れ方に合わせて文面を直し（REFACTOR）、比較の (pa)〜(pe) を 1 回だけ取り直す。(a)〜(h)・(j) が外れたら、`prompt-aj-<対照>.md` で 3 回取って切り分ける。

Ruling（実装中）: 比較の版は Issue の指定が 15/15 だったが、(pa)・(pd)・(pe) の Issue のコメントを 3 回とも書かなかった（規定が無いため）。Spec の変更の内容 2 を 5 章に足し（`db6c107`。評価した版の SHA を残すため、SKILL.md は validation.md と別に commit した）、(pa)〜(pe) を 1 回だけ取り直して 15/15。(a)〜(j) は 10 場面とも 3/3 で、足した 1 文が効く場面を含まないので取り直していない。

- [ ] **Step 4: validation.md に #138 の節を足し、commit する**

評価方法と範囲、結果の表（(pa)〜(pe) の対照と比較、(a)〜(j) の比較と #137 の節の結果）、REFACTOR があればその内容、実行した検証、行っていない確認を書く。

```bash
git add .agents/skills/issue-to-pr/evals/validation.md .agents/skills/issue-to-pr/SKILL.md
git commit -m "docs: record issue-to-pr PR body keyword evaluation (#138)"
```

### Task 4: 統合の確認

**Files:** 変更しない（ログは `/workspaces/reso-world/tmp/agents/issue-138.2he3b_ok/` に置く）

**テスト:** 書かない。下の実行で確かめる。

- [ ] **Step 1: 差分全体を読む**

Run: `git diff origin/main -- .agents/skills/issue-to-pr`
Expected: Task 1〜3 の変更だけ。5 章の Issue のコメントに書く内容（確認の項目と PR の URL）を 2 章の 6 の停止が読め、`--merge` の結果の表が `finalize.py` の `closingIssuesReferences` の挙動と食い違わない

- [ ] **Step 2: README の「テスト」を実行する**

Run: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`
Expected: どれも終了コード 0

- [ ] **Step 3: ブランチ全体のレビュー**

新しいサブエージェントに、Spec・Plan と `git diff origin/main` をレビューさせる。指摘は致命的なものだけを直し、直したら該当の検証をやり直す。
