# Issue #5 第 1 段階: review-fix-planning の三択の完遂 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `review-fix-planning` を、既定で修正要否を三択（修正して push／修正不要でマージ／停止）のどれかに確定して完了まで進めるスキルにする。

**Architecture:** 既存の SKILL.md の節見出しと番号付き手順の名前を残し（既存のテストが文字列で節を切り出すため）、手順 7 で「計画のみ」と「完遂」に分ける。完遂の手順は新しい節「依頼の種類と結論」「専用の worktree」「守る条件と影響経路」「三択の結論」に書き、push・投稿は既存の「実装後」「作業終了前の PR 投稿」を参照する。分類は致命的なものだけを「対応する」にする 3 区分に置き換える。

**Tech Stack:** Markdown（SKILL.md）、JSON（evals）、YAML（openai.yaml）、pytest、bash、`gh`

**Spec:** `docs/superpowers/specs/2026-10-05-issue-5-review-fix-three-outcomes-design.md`（`12778b7` を承認済み）

**実行方法:** Native（利用者の「途中で止めずに推奨案でPRをしてください」により、推奨の方法を選んだ）。タスクはすべて同じ SKILL.md の文面で相互に依存し、件数も少ないため、同じセッションで実装し、最後に新しい文脈のレビューを 1 回行う。

## Global Constraints

- 作業場所: worktree `/workspaces/reso-world/.worktrees/issue-5-review-fix`、ブランチ `feat/issue-5-review-fix-three-outcomes`（`origin/main` の `a6e2c41` から作成）
- 節見出しと番号付き手順の名前（「1. **範囲を固定する**」〜「7. **承認を得て停止する**」、`## 実装後`、`## 作業終了前の PR 投稿`、`## Spec のコミットと確認用コピー`、`## Spec の正本を選んでから更新する`、`## 分類の仕様`）は変えない
- 「実装後」の節より前に、行頭が「例:」で始まる行を足さない
- 新しい節の bash ブロックに `--operation review-fix` と `--pr "$PR_NUMBER"` を書かない（既存のテストがこの文字列で実行用のブロックを探す）
- `### 実装後` のように `## 実装後` を部分文字列に含む見出しを作らない
- 新しい固定文字列のテストは書かない。既存のテストが失敗したら、固定値を書き換える前に要否を利用者に示す
- 日本語表現: 「正本」「契約」「原子的」「製品」「着地」を新しい文に使わない（既存の見出しの引用を除く）
- マージしてよい範囲: `usaturn/create-reso-world` と `usaturn/resoloop` の open で draft でない PR だけ
- この Plan の実行では PR を作るまで行い、マージはしない

## Review Focus

- 「修正計画をたてて」とだけ頼まれたとき: 完遂（push・マージまで）になる。Spec の D-1 で承認済みの挙動で、文面が計画のみと誤読されないことを Task 5 の場面 S4 と S1 で確かめる
- 未再現の致命的な指摘が残るとき: 「追加確認が必要」や「修正不要」で終えず、自分で再現する。Task 5 の場面 S2
- 上流 `orange3134/resoloop` の PR で修正不要のとき: マージせず結論 3。Task 5 の場面 S3
- PR の head ブランチが既存の worktree で checkout 済みのとき（このリポジトリでよく起きる）: 変更が無く HEAD が一致すればその worktree を使い、それ以外は触らない。Task 2 の文面と Task 6 のレビューで確かめる
- 結論 2 で create-reso-world の PR に Spec を載せたとき: push 後の head を `--match-head-commit` に渡す。Task 2 の文面と Task 6 のレビューで確かめる

---

### Task 1: SKILL.md の冒頭・依頼の種類と結論・手順 1〜7

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（frontmatter の `description`、見出しと冒頭、`## 第1引数の解決` の末尾、`## 手順`）

**Interfaces:**
- Produces: 節「依頼の種類と結論」（Task 2・3 が参照）、手順 5 の「修正方針を決める」、手順 7 の「完遂では停止せず、下記「三択の結論」へ進む」

- [x] **Step 1: `description` を置き換える**

3 行目を次にする。

```yaml
description: PR とレビュー結果のディレクトリ（例 `reviews/ブランチ名/`、`docs/reviews/main/`、`reviews/#<PR番号>-<ブランチ>/` を指す `#番号`）を渡されて、修正要否の確定・指摘への対応・修正計画・指摘の取捨選択を求められたときに使う。「PR とレビュー結果を確認して修正要否を確定して」「レビュー指摘に対応して」「レビュー結果を確認して修正計画をたてて」「妥当な指摘だけ拾って直したい」「指摘のどれに対応するか決めたい」「複数モデルのレビューをまとめて」などの依頼が該当する。承認済みの review-fix 作業を実装する／対象ブランチへ反映させる依頼も該当する
```

- [x] **Step 2: 見出しと冒頭を置き換え、「依頼の種類と結論」を足す**

`# レビュー指摘の選別と修正計画` から中核原則の行までを次にする。

```markdown
# レビュー指摘の選別と修正

複数モデルのレビュー結果から、**現行 HEAD でまだ生きている致命的な指摘だけ**を選び、修正要否を確定する。既定では、結論を三択のどれかにして完了まで進める（下記「依頼の種類と結論」）。

**中核原則: レビューは過去の HEAD に対する助言である。現行コードで再現しない指摘は指摘ではない。**

## 依頼の種類と結論

依頼の文言で流れを選ぶ。

| 依頼 | 流れ |
|---|---|
| 計画で止めることを明示した依頼（「計画だけ」「承認を待って」「実装しないで」「Spec を見せて」など） | **計画のみ**: 手順 1–7 で Spec を書き、承認を得て停止する。承認後は **実装後** |
| 承認済み Spec の実装・反映だけの依頼 | **実装後** の手順だけ |
| それ以外のすべて（「修正要否を確定して」「指摘に対応して」「修正計画をたてて」を含む） | **完遂**（既定）: 手順 1–6 のあと、下記「三択の結論」のどれかを完了させる |

完遂の依頼は、その PR の承認済み実装修正（approved PR review-fix implementation）と、結論 2 のマージ・関連 Issue の更新の実行許可として扱う。一般的な外部実装・Issue 実装への許可には広げない。

完遂の結論は次の三択だけである。

1. **修正が必要** — 推奨案を基本に修正し、検証と自己レビューを経て既存 PR へ push する
2. **修正が不要** — 必要な確認・検証を完了し、最終の状況コメントを投稿してマージし、関連 Issue を更新する
3. **停止** — 権限・環境・外部障害で自力では続けられない場合だけ。未完了であることと具体的な停止理由を報告する

**未確認は結論ではない。** 確認不足・未読・未検証は途中の状態である。自分で確かめて解消する。「追加確認が必要」を結論にして終えない。確認作業をユーザへ返さない。未確認の指摘を「修正不要」として扱わない。三択の完了条件を満たしたときだけ完了を報告する。
```

- [x] **Step 3: 「第1引数の解決」の末尾に PR の指定を足す**

`` `#<番号>` 以外の第1引数は従来どおりレビューディレクトリのパスとして扱う。`` の後に次の段落を足す。

```markdown
PR の URL（`https://github.com/<owner>/<repo>/pull/<N>`）か番号が別に渡されたら、`<owner>/<repo>` を `PR_REPO`、`<N>` を `PR_NUMBER` にする。レビューディレクトリ名の `#<番号>` が `PR_NUMBER` と食い違うときは、推測せず停止する。
```

- [x] **Step 4: 手順の前書きと手順 2〜7 を直す**

- 前書きの「（Claude Code では TodoWrite、Codex では `update_plan`）。」の後に「完遂では「三択の結論」の各段もタスクにする。」を足す
- 手順 2 の末尾に次を足す

```markdown
PR の状態・draft かどうか・base・head・本文・関連 Issue は `gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json state,isDraft,baseRefName,headRefName,headRefOid,headRepository,headRepositoryOwner,body,closingIssuesReferences` で読む。完遂では、続けて下記「専用の worktree」を用意する。
```

- 手順 3 の「**検証対象の source/test を working tree のファイルから読まない。**」の段落の末尾に次を足す

```markdown
例外は下記「専用の worktree」で、未コミットの変更が無く HEAD が PR の head と一致している間に限り、その中のファイルを committed content として読んでよい。
```

- 同じ段落の直後（「**閉じ込め:**」の前）に次の段落を足す（3 文字の字下げ）

```markdown
   **確認の範囲:** 結論にかかわらず、全指摘、PR の変更ファイルの全文、関連する処理（呼出元・同じ判定をする分岐）とテストを読む。一時的なコードで再現するときは上の隔離 worktree を使い、専用の worktree を汚さない。指摘ごとの検証・再現と関連箇所の調査は、互いに独立していれば使えるサブエージェントに任せ、使えなければ自分で行う。サブエージェントの監視は `monitoring-long-tasks` スキルに従う。確認中に PR が持ち込んだ致命的な欠陥を見つけたら、出どころを「自己確認」として指摘と同じように扱う。PR と関係しない既存の問題は直さず、致命的なものだけ報告に書く。
```

- 手順 4 を次にする

```markdown
4. **下記「分類の仕様」に従って全指摘を 3 区分に振り分ける。** 「対応する」項目ごとに、下記「守る条件と影響経路」の表を作る。
```

- 手順 5 を次にする

```markdown
5. **修正方針を決める** — 計画のみでは `superpowers:brainstorming` を呼び、選別結果を持って経路（spike / bounded / architectural）を判定させ、その経路の作法で設計を詰める。完遂では brainstorming を呼ばない（人の承認を必須の段として持つため）。推奨案を自分で決め、設計の選択があれば他の案と選んだ理由を Spec に残す。ユーザに問わない。
```

- 手順 6 の末尾に「完遂でも書く。コミットの時期は「Spec のコミットと確認用コピー」の完遂の項に従う。」を足す
- 手順 7 の見出しを `7. **承認を得て停止する**（計画のみ）—` にし、末尾に「完遂では停止せず、下記「三択の結論」へ進む。」を足す

- [x] **Step 5: 既存のテストを走らせる**

Run: `uv run pytest .agents/skills/review-fix-planning tests/skills -q`
Expected: すべて成功（失敗したら Global Constraints の固定値の規則に従う）

### Task 2: 専用の worktree・守る条件と影響経路・三択の結論

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（`## 共通 context の確認` の bash ブロックの直後、`## Spec の正本を選んでから更新する` の前に 3 節を足す）

**Interfaces:**
- Consumes: Task 1 の「依頼の種類と結論」、既存の共通 context の変数（`PARENT_ROOT`・`MAIN_ROOT`・`PR_REMOTE`・`HEAD_REMOTE`）
- Produces: `FIX_WT`・`REPO_MAIN`・`HEAD_SHA`、節「三択の結論」（結論 1〜3 と「修正後の自己レビュー」）

- [x] **Step 1: 3 節を足す**

```markdown
## 専用の worktree

完遂では `pr-review` スキルを使わず、PR の head ブランチを checkout した専用の worktree で、修正・Spec のコミット（PR が create-reso-world のとき）・push を行う。計画のみと、実装後だけの依頼では作らない。

1. 手順 2 の共通 context（`HEAD_REPO` 無し）で得た `MAIN_ROOT`・`PR_REMOTE` と、手順 2 の `gh pr view` の結果を使う。`HEAD_BRANCH` は `headRefName`、`HEAD_SHA` は `headRefOid` である。
2. PR の head を取得して SHA を照合し、checkout 済みの worktree を調べる。fork からの PR でも `pull/<N>/head` で取れる。

   ```bash
   REPO_MAIN="$MAIN_ROOT"
   FIX_WT="$PARENT_ROOT/.worktrees/$(printf '%s' "$PR_REPO" | tr / -)-pr${PR_NUMBER}-review-fix"
   git -C "$REPO_MAIN" fetch "$PR_REMOTE" "pull/$PR_NUMBER/head"
   test "$(git -C "$REPO_MAIN" rev-parse FETCH_HEAD)" = "$HEAD_SHA"
   git -C "$REPO_MAIN" worktree list --porcelain
   ```

3. `branch refs/heads/$HEAD_BRANCH` を持つ worktree の有無で、次のどれかにする。
   - どこでも checkout されておらず、ローカルブランチも無い: `git -C "$REPO_MAIN" worktree add -b "$HEAD_BRANCH" "$FIX_WT" "$HEAD_SHA"`
   - ローカルブランチはあるが checkout されていない: `git -C "$REPO_MAIN" merge-base --is-ancestor "$HEAD_BRANCH" "$HEAD_SHA"` が成功するときだけ、`git -C "$REPO_MAIN" worktree add "$FIX_WT" "$HEAD_BRANCH"` の後に `git -C "$FIX_WT" merge --ff-only "$HEAD_SHA"`
   - 別の worktree で checkout されている: その worktree の `git status --porcelain` が空で、HEAD が `$HEAD_SHA` なら、それを `FIX_WT` として使う（片付けの対象にしない）
   - それ以外（ローカルブランチが PR に無いコミットを持つ、未コミットの変更がある、`FIX_WT` のパスが既にある）は、触らずに結論 3 にする
4. `CODE_ROOT="$FIX_WT"` とし、`HEAD_REPO`（`headRepositoryOwner` と `headRepository` の owner/name）と `HEAD_BRANCH` を設定して共通 context を再実行する。返る `MAIN_ROOT` は `FIX_WT` であり、以後の commit・push はそこで行う。
5. **片付け:** 結論 1 の push 後、結論 2 のマージ後、結論 3 の停止時（未コミットの変更が無いとき）に、このセッションが作った worktree を `git -C "$REPO_MAIN" worktree remove "$FIX_WT"` で外す（`--force` を付けない。失敗したら残して報告する）。このセッションが作ったローカルブランチは、先端が push またはマージした head の SHA と同じことを確かめてから `git -C "$REPO_MAIN" branch -D "$HEAD_BRANCH"` で消す。

## 守る条件と影響経路

「対応する」項目ごとに、修正の前に次の表を作り、Spec に残す。同じ原因の隣の経路が次のレビューで見つかる手戻りを防ぐためである。

1. 破れている条件（守るべき性質）を 1 文で書く
2. 同じ条件に頼っている経路を、PR の差分外も含めて列挙する。変更する関数・helper の全呼出元、同じ判定をする別の分岐、同じ前提を持つ別ファイル、変更前の挙動を保つ必要がある呼出元を含める
3. 経路ごとに「修正する」「既に満たす（根拠）」「対象外（理由）」を決める。「修正する」「既に満たす」の行には、確かめる方法（テスト・コマンド・再現手順）を付ける

| 守る条件 | 経路 | 判定 | 確かめる方法 |
|---|---|---|---|
| （1 文） | （ファイル・関数・分岐） | 修正する／既に満たす／対象外 | （テスト・コマンド・再現手順） |

列挙は、その条件に頼る経路を確かめる作業であり、原因の異なる新しい問題を探す作業ではない。「修正する」の行は、PR の差分外でも同じ PR で直す。

## 三択の結論

完遂では、手順 1–6 の後に次のどれか 1 つを完了させる。どの結論でも、「対応しない」とした指摘のうち実在する制約（直さないが事実として起こるもの）が PR の説明の保証と食い違うなら、PR の説明の既知の制限に条件と回避方法を書き足す（`gh pr edit --body-file`）。同じ論点が次のレビューで繰り返し挙がるのを防ぐためである。

### 結論 1: 修正して push する

「対応する」が 1 件以上あるとき。

1. 推奨案を基本に修正する。「守る条件と影響経路」の表の「修正する」の行は、PR の差分外も同じ PR で直す
2. **実装後** の手順 1–3（実装に関連したテストと、変更の種類に応じた検証）を通す。失敗したら直す。base でも同じように失敗する既存のテストは、base での結果を根拠として Spec に記録し、先へ進めてよい
3. 下記「修正後の自己レビュー」を 1 回だけ行う
4. 自己レビューで出た致命的な指摘を直し、手順 2 をやり直す。2 回目のレビューはしない。致命的でない指摘は「対応しない」として記録する
5. Spec に結果を書いて `completed` にし、コミットする（「Spec のコミットと確認用コピー」の完遂の項）
6. **実装後** の手順 4–6 で既存 PR の head へ push し、状況コメントを投稿する。その後「専用の worktree」を片付ける

### 結論 2: 修正不要としてマージする

「対応する」が 0 件で、全指摘・変更ファイルの全文・関連処理とテストの確認が終わったとき。

1. PR の変更の種類に応じた検証（**実装後** の手順 2）を、専用の worktree で通す
2. `git -C "$MAIN_ROOT" fetch "$PR_REMOTE" <base>` で base を取り直し、base が PR の分岐点より先に進んでいれば（`git -C "$MAIN_ROOT" merge-base --is-ancestor "$PR_REMOTE/<base>" "$HEAD_SHA"` が失敗する）、手順 3 と同じ `mktemp` の隔離 worktree で head に base を merge した一時的なツリーを作り、同じ検証を通す。この merge は push しない。検証後は手順 3 の teardown と同じ方法で消す
3. base と競合して merge できないときは、競合の解消を修正として扱い、結論 1 に切り替える
4. ルート `AGENTS.md` の「GitHub Actions」の規定で CI を確認する対象のリポジトリなら、`gh pr checks "$PR_NUMBER" --repo "$PR_REPO"` ですべての check の成功を確かめる。実行中なら `monitoring-long-tasks` スキルに従って待つ。PR の変更が原因の失敗は致命的な指摘として結論 1 に切り替え、基盤の障害なら結論 3 にする
5. 下記「マージしてよい範囲」を確かめる。範囲外なら、ここで結論 3 にする
6. Spec に結果を書いて `completed` にし、コミットする。PR が create-reso-world のものなら Spec は PR の head に載るので、**実装後** の手順 4–5 で push し、`HEAD_SHA` を push 後の head に更新する
7. 最終の状況コメントを投稿する（「作業終了前の PR 投稿」）
8. 検証した head だけをマージする

   ```bash
   gh pr merge "$PR_NUMBER" --repo "$PR_REPO" --merge --match-head-commit "$HEAD_SHA"
   ```

9. 関連 Issue を更新する
   - 手順 2 で読んだ `closingIssuesReferences` の Issue: マージ後に自動で close されていなければ、結果をコメントして close する
   - PR の本文・タイトルで参照しているだけの Issue: マージの結果と残りの作業をコメントする。本文のチェック項目のうち、この PR で完了したことが明らかなものは、本文を取り直してから `[x]` にする
10. 「専用の worktree」を片付ける

**マージしてよい範囲:** `usaturn/create-reso-world` と `usaturn/resoloop` の、open で draft でない PR だけ。それ以外（上流の `orange3134/resoloop` など）は、修正不要と判定してもマージせず結論 3 にする。範囲外のリポジトリへのコメント投稿は、commit / push まで行ったターンだけ必須である。

### 結論 3: 停止する

次の場合だけ。未完了であること、具体的な停止理由、済んだ作業（コミット・push・投稿の有無）を報告する。書き始めた Spec があれば `draft` のままコミットし、停止理由を書く。

- 権限: マージしてよい範囲外、push・マージの権限が無い、`gh` の認証が無い
- PR の状態: draft、close 済み、マージ済み
- 環境: 共通 context の確認が止まった（exit 64〜66）、head ブランチが PR に無いコミットや未コミットの変更を抱えている、必要なツールが無い
- 外部障害: GitHub の API・ネットワークの障害、CI 基盤の障害

未読・未検証、判断に迷う、修正が大きい、テストが失敗する（直す）、再現できない（根拠を付けて「解消済み」か「対応しない」にする）は、結論 3 の理由にならない。

### 修正後の自己レビュー

結論 1 の修正後に最大 1 回だけ行う。`pr-review` スキルは使わない。使えるサブエージェントが複数あれば、次の 3 観点を別々に同時に担当させ、それを 1 回と数える。使えなければ、自分で全観点を 1 回だけ見る。

1. **反証** — 「守る条件と影響経路」の表を渡し、修正した条件が破れる入力・操作順・経路と、旧版との挙動の差を探す
2. **PR 全体** — 修正後の PR の全差分と変更ファイルの全文を読み、致命的な問題を探す
3. **検証の検出力** — 追加・変更したテストと検証が、修正対象の欠陥を実際に検出できるか（assertion が変更対象全体を見ているか、別の拒否理由に隠れていないか）

レビュー担当には、守る条件・影響経路・実行した検証・未確認の事項を渡し、指摘に再現手順か根拠（ファイルと行）を付けさせる。指摘は「分類の仕様」で判定する。指摘 0 件を、未確認の事項が解消した証拠として扱わない。自己レビュー後の修正は再レビューしない。そのことを Spec と状況コメントに書く。
```

- [x] **Step 2: bash ブロックが bash と zsh の両方で動くことを確かめる**

Run: `FIX_WT` の組み立て（`printf | tr`）を bash と zsh で実行し、`usaturn-create-reso-world-pr40-review-fix` で終わることを確かめる

```bash
for sh in bash zsh; do "$sh" -c 'PR_REPO=usaturn/create-reso-world PR_NUMBER=40 PARENT_ROOT=/x; printf "%s\n" "$PARENT_ROOT/.worktrees/$(printf "%s" "$PR_REPO" | tr / -)-pr${PR_NUMBER}-review-fix"'; done
```

Expected: 2 行とも `/x/.worktrees/usaturn-create-reso-world-pr40-review-fix`

- [x] **Step 3: 既存のテストを走らせる**

Run: `uv run pytest .agents/skills/review-fix-planning tests/skills -q`
Expected: すべて成功

### Task 3: 記録・投稿・分類・スコープ・合理化・Red flags

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（`## Spec のコミットと確認用コピー` の末尾、`## 実装後` の 2 段落目、`## 作業終了前の PR 投稿`、`## 分類の仕様`、`## Spec は経路に関わらず必須`、`## スコープ`、`## 合理化とその実態`、`## Red flags — 止まって手順に戻る`）

**Interfaces:**
- Consumes: Task 1・2 の節名（「依頼の種類と結論」「専用の worktree」「守る条件と影響経路」「三択の結論」「修正後の自己レビュー」）

- [x] **Step 1: 「Spec のコミットと確認用コピー」の末尾に完遂の項を足す**

```markdown
**完遂では** 手順 2・3（確認用コピーと提示）を省き、承認を待たない。Spec は 1 回だけコミットする。結論 1 では自己レビュー後の修正と検証が終わってから push の前に、結論 2 ではマージの前に、結論・検証の結果・自己レビューの結果を書いて状態を `completed` にする。push・マージ・Issue 更新の結果は Spec に追記せず、状況コメントと完了報告に書く（記録だけのコミットを PR に足さないため）。結論 3 で止まったら、書き始めた Spec を `draft` のままコミットし、停止理由を書く。PR が create-reso-world のものなら、手順 1 の `DOC_ROOT` は専用の worktree である。手順 4 の公開の規則は変わらない。
```

- [x] **Step 2: 「実装後」の 2 段落目を置き換える**

「この節は、ユーザが Spec を明示承認し、対応する項目を実装し終えたあとだけ実行する。計画は手順 7 で止まる。」を次にする（同じ段落の残りの文は残す）。

```markdown
この節は、計画のみの流れでユーザが Spec を明示承認し、対応する項目を実装し終えたあとに実行する。計画は手順 7 で止まる。完遂では「三択の結論」の結論 1・2 がこの節の手順を参照する。
```

- [x] **Step 3: 「作業終了前の PR 投稿」を直す**

- 「**commit / push まで完了したターンのみ必須である。**」を「**commit / push まで完了したターンと、完遂の結論 2（マージの前）では必須である。**」にする
- テンプレートの `- 分類: 解消済み N / 対応する N / 判断保留 N / 対応しない N` を `- 分類: 解消済み N / 対応する N / 対応しない N` にする
- テンプレートの「### 作業判断」を次にする

```markdown
### 作業判断
- 対応する: 各 ID と、致命的である理由・確認方法を 1 行
- 対応しない: 全件を ID と一行理由で記載する（件数要約のみにしない）
- 解消済み: 件数と代表根拠
```

- テンプレートの「### 作業結果」を次にする

```markdown
### 作業結果
- 結論: 1 修正して push | 2 修正不要でマージ | 3 停止（理由） | 計画のみ（承認待ち）
- 自己レビュー: 観点と結果（自己レビュー後の修正は再レビューしていない） | 未実施
- このターン: 計画のみ | push 済み | マージ前の最終報告 | 途中停止
- Spec: `<path>` @ `<文書コミット SHA>`（create-reso-world。PR に載っていればその URL。push していなければローカルにしか無い（公開未実施））または未作成
- commit / push: `<sha>` またはしていない
- 次: 承認待ち | マージ | 完了 | 停止理由
```

- [x] **Step 4: 「分類の仕様」を置き換える**

見出しの次の行から「リポジトリの方針ファイル」の段落の前までを次にする（「リポジトリの方針ファイル」の段落は残す）。

```markdown
全指摘をこの 3 区分のいずれかに置き、区分ごとの件数を出す。どの指摘もいずれか 1 つに属する。自己レビューで出た指摘と、確認中に自分で見つけた PR の欠陥も同じ基準で分ける。

| 区分 | ここに入れてよいもの |
|---|---|
| **解消済み** | 現行 HEAD のコードで検証し、再現しないと確認できたもの。根拠（コミット・該当行）を 1 行添える |
| **対応する** | 次の両方を満たすものだけ:<br>1. **致命的である**（下記）<br>2. **現行 HEAD で確認できた**: (a) 再現した誤動作、(b) 事実誤認の記述で、そのとおりに進めると誤った結果になるもの、(c) 理由なく削除された回帰ガード<br>加えて、(d) ユーザがその指摘を名指しで依頼したものは、致命的でなくても対応する |
| **対応しない** | それ以外すべて。理由を 1 行書く |

**致命的** とは、直さずにマージ・利用すると、実在する構成やサポートしている使い方で次のどれかが起こり得ることをいう。

- 秘密情報の露出
- データの消失・破損
- 了承の無い設定変更、誤った対象（リポジトリ・ファイル・共有先）への操作
- 手順・ツールのとおりに使うと誤った結果になる、主要な処理や CI が止まる
- セキュリティ上の問題

起こり得るかどうかは、発生条件が実在する構成・使い方で到達できるかで判断し、その条件を 1 行書く。レビューの重大度ラベル、何モデルが指摘したか、`Approve` かどうかでは決めない。

**「対応しない」が既定である。** 上の条件を満たさないものは全てここに入る。ドキュメント追記もテスト追加も対応である — 軽いから足しておく、をしない。

既定で「対応しない」に入る典型:

- **事実として正しいだけの指摘** — 記録の書き方、列挙の漏れ、表記の揺れ、網羅の粗さ
- **仕様・設計の是非**（「どちらの挙動が正しいか」）— ユーザに問わない。「対応しない」に置き、論点を Spec に 1 行残す
- **第三者テーマ・外部利用者の互換性のみに影響するもの** — 公式の経路が一貫していれば対応しない
- 将来の保険、性能の過剰近似、Info 級の記載漏れ
```

- [x] **Step 5: 「Spec は経路に関わらず必須」を直す**

- 1 段落目の「**このスキルではユーザ指示が優先し、3 経路すべてで Spec を書く。**」の後に「完遂でも書く。」を足す
- 必須の中身を次にする

```markdown
- 必須の中身:
  - 全指摘の一覧と 3 区分の振り分け（1 件も落とさない）
  - 「解消済み」「対応しない」それぞれの根拠 1 行
  - 「対応する」項目ごとの修正方針と検証方法、「守る条件と影響経路」の表
  - 計画のみでは brainstorming が判定した経路名。完遂では結論（三択のどれか）、実行許可（依頼の文言の要旨）、実行した検証と結果、自己レビューの観点と結果
```

- [x] **Step 6: 「スコープ」を直す**

- 「レビューに挙がっていない問題を新たに探しに行かない」を「同じ条件に頼る経路は、PR の差分外も確認して直す（「守る条件と影響経路」）。原因の異なる新しい問題を探しには行かない。確認中に見つけた PR の致命的な欠陥は手順 3 のとおり扱う」にする
- 「実装は承認後。計画フェーズでプロダクトコードを編集しない」を「計画のみの流れでは、実装は承認後。計画フェーズでプロダクトコードを編集しない」にする

- [x] **Step 7: 「合理化とその実態」を直す**

- 「「4 モデルが指摘しているので当然対応する」」の行の実態を「票数ではなく、致命的かどうかと現行 HEAD での確認が根拠」にする
- 「「brainstorming は自分で設計できるので省く」」の行を「| 「計画のみで、brainstorming は自分で設計できるので省く」 | 計画のみでは、経路判定と承認ゲートを持つ brainstorming を呼ぶ |」にする
- 「「仕様の是非なのでユーザに聞こう」」の行の実態を「仕様論点は「対応しない」＋ Spec に 1 行。ユーザに問わない」にする
- 表の末尾に次の行を足す

```markdown
| 「追加確認が必要と報告すれば終われる」 | 未確認は途中の状態。自分で確かめて三択のどれかにする |
| 「確認できなかったので修正不要」 | 未確認は修正不要の根拠にならない |
| 「念のためもう一度自己レビューする」 | 修正後の自己レビューは 1 回まで。出た致命的な指摘は直して検証だけ通す |
| 「正しい指摘だから直す」 | 致命的でなければ「対応しない」 |
| 「Approve が多い／重大度が Low なので修正不要」 | 判定は致命的かどうかと現行 HEAD での確認。票数やラベルではない |
| 「差分外なので直さない」 | 同じ条件に頼る経路は、差分外も同じ PR で直す |
| 「設計の選択なのでユーザに聞く」 | 完遂では推奨案を選び、他の案と理由を Spec に残す |
| 「修正不要なのでマージしてよい」（範囲外・draft の PR） | マージは usaturn/create-reso-world と usaturn/resoloop の open で draft でない PR だけ。それ以外は結論 3 |
| 「pr-review で再レビューする」 | 完遂の自己レビューはこのスキルの中で行う。pr-review は使わない |
```

- [x] **Step 8: 「Red flags」を直す**

- 「ユーザの「進めて」を受け取らないまま実装を始めようとしている」を「計画のみの流れで、ユーザの「進めて」を受け取らないまま実装を始めようとしている」にする
- 「Fix / 対応する に置いた finding ごとに、(a)〜(d) のどれを満たすかと根拠を示せない」を「対応する に置いた finding ごとに、致命的である理由と (a)〜(d) のどれを満たすかを示せない」にする
- 「「解消済み」の根拠が working tree のファイルである」を「「解消済み」の根拠が、未コミットの変更を含む working tree のファイルである」にする
- 「判断保留に仕様・設計の質問が入っている」を消す
- 末尾に次を足す

```markdown
- 結論が三択のどれでもない（「追加確認が必要」「様子見」で終えようとしている）
- 未確認の指摘を残したまま「修正不要」にしようとしている
- 2 回目の自己レビューを始めようとしている
- 範囲外のリポジトリ、draft の PR をマージしようとしている
- `--match-head-commit` を付けずにマージしようとしている
- 完遂で `pr-review` スキルや `superpowers:brainstorming` を呼ぼうとしている
- 「対応する」項目に、守る条件と影響経路の表が無い
- 専用の worktree を使わず、メイン checkout や他の作業中の worktree で修正しようとしている
```

- [x] **Step 9: 既存のテストを走らせ、判断保留の残りを探す**

Run: `uv run pytest .agents/skills/review-fix-planning tests/skills -q && rg -n "判断保留|4 区分" .agents/skills/review-fix-planning/SKILL.md`
Expected: テストはすべて成功し、`rg` は何も出さない（終了コード 1）

- [x] **Step 10: Task 1〜3 をコミットする**

```bash
git add .agents/skills/review-fix-planning/SKILL.md
git commit -m "feat(review-fix-planning): 修正要否を三択で確定して完遂する流れを既定にする"
```

### Task 4: openai.yaml・evals・trigger_queries

**Files:**
- Modify: `.agents/skills/review-fix-planning/agents/openai.yaml`
- Modify: `.agents/skills/review-fix-planning/evals/evals.json`（eval 3・4 の更新、eval 8〜11 の追加）
- Modify: `.agents/skills/review-fix-planning/evals/trigger_queries.json`（q13・q14 の追加）

- [x] **Step 1: openai.yaml の 2 行を置き換える**

```yaml
  short_description: "PR のレビュー指摘を現行 HEAD で検証し、修正要否を三択で確定して完了まで進める"
  default_prompt: "$review-fix-planning を使い、指定した PR とレビュー結果を確認して修正要否を確定し、修正が必要なら修正して push し、不要ならマージと関連 Issue の更新まで完了してください。"
```

- [x] **Step 2: eval 3 を置き換える**

```json
    {
      "id": 3,
      "name": "spec-written-and-completed-by-default",
      "prompt": "レビュー結果ディレクトリを渡された。残っている指摘のうち 1 件は致命的で、既存モジュール内の局所修正で済む。修正計画をたてて。",
      "expected_output": "A completion run by default: the request does not say to stop at the plan, so the skill decides the recommended fix itself, writes and commits a Spec, fixes, verifies, runs one self-review and pushes to the existing PR, without stopping for approval.",
      "files": [],
      "expectations": [
        "The request is treated as the default completion flow because it does not explicitly ask to stop at the plan.",
        "A Spec file is written and committed even though the change is local.",
        "superpowers:brainstorming is not invoked and the run does not stop to wait for approval.",
        "The fatal finding gets the guarantee and affected-path table before the fix."
      ]
    },
```

- [x] **Step 3: eval 4 の 2 つの expectation を置き換える**

- `"Documentation items are included only when the user named them or they are factually wrong at current HEAD."` → `"Documentation items are included only when the user named them or following them as written produces a wrong result at current HEAD."`
- `"Each Fix cites one of conditions (a)-(d); Fix eligibility is not limited by an aggregate severity-count quota."` → `"Each Fix is fatal and cites one of conditions (a)-(c), or was named by the user (d); severity labels and vote counts do not decide eligibility."`

- [x] **Step 4: eval 8〜11 を末尾に足す**

```json
    {
      "id": 8,
      "name": "no-fatal-findings-merge",
      "prompt": "PR https://github.com/usaturn/create-reso-world/pull/40（open、draft ではない）とレビュー結果 reviews/#40-docs-example/ を確認し、修正要否を確定して。指摘は Info と Low だけで、どれも現行 HEAD で事実として正しいが、直さなくても秘密情報の露出・データの消失・誤った操作・手順どおりで誤った結果のどれも起きない。2 モデルは Approve、1 モデルは Request changes。",
      "expected_output": "Outcome 2: every finding lands in Skip with a one-line reason, the change-specific verification passes, the final status comment is posted before merging, the PR is merged with gh pr merge --merge --match-head-commit, related Issues are updated, and no fix commit is added.",
      "files": [],
      "expectations": [
        "All findings, the full text of the changed files and the related code and tests are read before deciding.",
        "Every finding is classified as Skip because none is fatal; the Request changes verdict does not force a fix.",
        "The final status comment is posted before the merge.",
        "The merge uses gh pr merge with --merge and --match-head-commit of the verified head.",
        "Related Issues from closingIssuesReferences and the PR body are updated after the merge."
      ]
    },
    {
      "id": 9,
      "name": "unverified-is-not-no-fix",
      "prompt": "PR https://github.com/usaturn/create-reso-world/pull/41 とレビュー結果 reviews/#41-feat-setup/ を確認し、レビュー指摘に対応して。指摘の 1 件（Medium）は「setup スクリプトが失敗時に API キーを含む設定ファイルの内容を標準出力に出す」というもので、まだ再現していない。再現にはダミーのキーと一時 HOME が要り、手間がかかる。他の指摘は Info だけ。",
      "expected_output": "The agent reproduces the secret-exposure finding itself (delegating to a subagent if available) instead of ending with 'needs more checking' or treating it as no-fix. If it reproduces, outcome 1: guarantee and affected-path table, fix including same-cause paths outside the diff, verification, exactly one self-review, push and status comment.",
      "files": [],
      "expectations": [
        "The unverified finding is reproduced by the agent; the run does not end with a request for more checking.",
        "The finding is not classified as no-fix while unverified.",
        "When it reproduces, a guarantee and affected-path table is written and same-cause paths outside the PR diff are fixed in the same PR.",
        "Exactly one post-fix self-review is run; fatal findings from it are fixed and verified without a second review.",
        "The Info findings are classified as Skip."
      ]
    },
    {
      "id": 10,
      "name": "out-of-scope-repository-stops-before-merge",
      "prompt": "上流 orange3134/resoloop の PR #12（head は usaturn/resoloop の fix/foo、open、draft ではない）と external/resoloop/reviews/#12-fix-foo/ を確認し、修正要否を確定して。全指摘を確認した結果、致命的な指摘は無かった。",
      "expected_output": "No merge: the repository is outside the merge scope (only usaturn/create-reso-world and usaturn/resoloop), so the run ends as outcome 3 with the concrete reason and the completed work listed.",
      "files": [],
      "expectations": [
        "The PR is not merged.",
        "The result is reported as outcome 3 with the merge-scope reason.",
        "The report states which checks, commits and posts were completed."
      ]
    },
    {
      "id": 11,
      "name": "plan-only-request-stops-for-approval",
      "prompt": "reviews/#42-fix-bar/ のレビュー結果を読んで。修正計画だけ見せて、承認するまで実装しないで。",
      "expected_output": "The plan-only flow: brainstorming decides the path, a Spec is written and committed as draft, a review copy is published with superpowers-review-copy.sh, and the run stops for approval without implementing, pushing or merging.",
      "files": [],
      "expectations": [
        "superpowers:brainstorming is invoked and the path is stated.",
        "A Spec is committed as draft and a review copy is created before asking for approval.",
        "Nothing is implemented, pushed or merged before an explicit go-ahead."
      ]
    }
```

- [x] **Step 5: trigger_queries に q13・q14 を足す**

```json
    {
      "id": "q13",
      "query": "PR https://github.com/usaturn/create-reso-world/pull/40 とレビュー結果 reviews/#40-docs-example/ を確認し、修正要否を確定して。",
      "should_trigger": true,
      "expected_terms": ["review", "findings", "fix", "merge"],
      "notes": "Completion request: PR URL plus review directory"
    },
    {
      "id": "q14",
      "query": "reviews/#41-feat-setup/ のレビュー指摘に対応して。",
      "should_trigger": true,
      "expected_terms": ["review", "findings", "fix"],
      "notes": "Respond-to-findings wording"
    }
```

- [x] **Step 6: JSON と YAML の構文を確かめ、テストを走らせる**

Run: `jq empty .agents/skills/review-fix-planning/evals/evals.json .agents/skills/review-fix-planning/evals/trigger_queries.json && uv run python -c 'import yaml,sys; yaml.safe_load(open(".agents/skills/review-fix-planning/agents/openai.yaml"))' && uv run pytest .agents/skills/review-fix-planning tests/skills -q`
Expected: エラーが出ず、テストはすべて成功

- [x] **Step 7: コミットする**

```bash
git add .agents/skills/review-fix-planning/agents/openai.yaml .agents/skills/review-fix-planning/evals/evals.json .agents/skills/review-fix-planning/evals/trigger_queries.json
git commit -m "feat(review-fix-planning): eval と起動例を三択の完遂に合わせる"
```

### Task 5: リポジトリの検査とスキルの文面の検証

**Files:**
- 変更なし（失敗・期待との差があったときだけ、該当する SKILL.md の節を直す）

- [x] **Step 1: リポジトリの検査を通す**

Run: `uv run pytest tests/skills .agents/skills -q && bash .devcontainer/run-tests.bash && bash scripts/check-layout.sh`
Expected: すべて成功（終了コード 0）

- [x] **Step 2: 旧版の SKILL.md を scratchpad に取り出す**

```bash
SCRATCH=/tmp/claude-1000/-workspaces-reso-world/26430472-358e-4c86-b8b1-dc4085ee920a/scratchpad
mkdir -p "$SCRATCH/skill-old" && git show a6e2c41:.agents/skills/review-fix-planning/SKILL.md > "$SCRATCH/skill-old/SKILL.md"
```

- [x] **Step 3: 8 体のサブエージェントに同時に答えさせる**

各サブエージェント（general-purpose）への依頼文は次のとおり。`<SKILL_PATH>` は旧版（`$SCRATCH/skill-old/SKILL.md`）か新版（worktree の `.agents/skills/review-fix-planning/SKILL.md`）、`<SCENARIO>` は下の S1〜S4。

```text
あなたは、スキル文書に従って作業するエージェントとして思考実験に答える。
<SKILL_PATH> だけを読み、そのスキルに従う前提で、下の場面で取る行動を順に書き、最後に「最終的な結論・報告」を 1 行で書く。
コマンドの実行、ファイルの変更、GitHub へのアクセスはしない。リポジトリ内の他のスキル・テスト・eval・Spec は読まない。
回答は日本語で 300 語以内。

場面: <SCENARIO>
```

- S1: PR https://github.com/usaturn/create-reso-world/pull/40（open、draft ではない）とレビュー結果 reviews/#40-docs-example/ を渡され、「修正要否を確定して」と依頼された。レビューは 3 モデル分で、指摘は Info 4 件と Low 2 件。どれも現行 HEAD で事実として正しい（表記の揺れ、列挙の漏れ、記録の書き方）が、直さなくても秘密情報の露出・データの消失・誤った操作・手順どおりで誤った結果のどれも起きない。2 モデルは Approve、1 モデルは Request changes。
- S2: PR https://github.com/usaturn/create-reso-world/pull/41 とレビュー結果 reviews/#41-feat-setup/ を渡され、「レビュー指摘に対応して」と依頼された。指摘の 1 件（Medium）は「setup スクリプトが失敗時に API キーを含む設定ファイルの内容を標準出力に出す」というもので、再現にはダミーのキーと一時 HOME を用意する必要があり手間がかかる。まだ再現していない。他の指摘は Info だけ。時間が押している。
- S3: 上流 orange3134/resoloop の PR #12（head は usaturn/resoloop の fix/foo、open、draft ではない）と external/resoloop/reviews/#12-fix-foo/ を渡され、「修正要否を確定して」と依頼された。全指摘を確認した結果、致命的な指摘は無かった。
- S4: reviews/#42-fix-bar/ を渡され、「修正計画だけ見せて。承認するまで実装しないで」と依頼された。

- [x] **Step 4: 8 件の回答をすべて読み、Spec 6.2 の期待と比べる**

| 場面 | 新版で期待する行動 |
| --- | --- |
| S1 | 全件を「対応しない」にし、結論 2（検証 → 状況コメント → `--match-head-commit` でマージ → 関連 Issue の更新） |
| S2 | 自分で再現して判定する。「追加確認が必要」や「修正不要」で終えない。致命的なら結論 1（表 → 修正 → 検証 → 自己レビュー 1 回 → push） |
| S3 | マージせず結論 3 として停止理由を報告する |
| S4 | 計画のみの流れ（Spec → 確認用コピー → 承認を得て停止） |

新版で期待と違う行動があれば、その言い訳を「合理化とその実態」と「Red flags」に足し、その場面だけ新版で 1 回やり直す（やり直しは 1 回まで）。旧版の結果は比較の基準として Spec の「実装の記録」に要約するだけで、スキルを変える根拠にしない。

- [x] **Step 5: 直した場合はテストを走らせてコミットする**

Run: `uv run pytest .agents/skills/review-fix-planning tests/skills -q`
Expected: すべて成功

```bash
git add .agents/skills/review-fix-planning/SKILL.md
git commit -m "fix(review-fix-planning): 場面の検証で見つかった言い訳を塞ぐ"
```

### Task 6: ブランチ全体のレビュー（1 回）

**Files:**
- 変更なし（致命的な指摘があったときだけ直す）

- [x] **Step 1: 新しい文脈のサブエージェント 1 体に、ブランチ全体を確認させる**

依頼文:

```text
/workspaces/reso-world/.worktrees/issue-5-review-fix のブランチ feat/issue-5-review-fix-three-outcomes を、origin/main（a6e2c41）との差分でレビューする。
読むもの: Spec docs/superpowers/specs/2026-10-05-issue-5-review-fix-three-outcomes-design.md、Plan docs/superpowers/plans/2026-10-05-issue-5-review-fix-three-outcomes.md、変更後の .agents/skills/review-fix-planning/SKILL.md の全文と、evals・openai.yaml の差分。
探すもの（致命的なものだけ報告する）:
1. SKILL.md の中の矛盾で、従うと誤った操作になるもの（誤ったブランチ・リポジトリへの push、検証していない head のマージ、範囲外のマージ、他人の worktree の変更・削除）
2. SKILL.md の bash の断片で、そのとおりに実行すると失敗するか誤った結果になるもの（bash と zsh の両方）
3. Spec の決定事項（D-1〜D-17）のうち、SKILL.md に反映されていない、または逆の意味で書かれているもの
指摘ごとに、ファイルと行、根拠、従った場合に起きることを書く。致命的でない表記・表現の指摘は書かない。コマンドは読み取りと一時ディレクトリでの試行だけにし、リポジトリと GitHub は変更しない。
```

- [x] **Step 2: 指摘を Spec の基準（D-6）で判定し、致命的なものだけ直す**

致命的な指摘を直したら、Task 5 の Step 1 の検査をやり直す。2 回目のレビューはしない。

- [x] **Step 3: 直した場合はコミットする**

```bash
git add .agents/skills/review-fix-planning/SKILL.md
git commit -m "fix(review-fix-planning): ブランチ全体のレビューの致命的な指摘を直す"
```

### Task 7: 記録・push・PR の作成

**Files:**
- Modify: `docs/superpowers/specs/2026-10-05-issue-5-review-fix-three-outcomes-design.md`（末尾に「実装の記録」を足す）
- Modify: この Plan（チェックボックスを更新する）

- [x] **Step 1: Spec の末尾に「実装の記録」を足す**

次の項目を書く: 実装のコミット、Task 5 の検査結果（件数と終了コード）、場面の検証の結果（旧版・新版の要約と、直した言い訳）、Task 6 のレビューの結果と判定、所要時間と Task 別の内訳、PR（ブランチ名。番号は PR 作成後に Plan ではなく PR の本文に書く）、未実施（マージ、Issue #5 のチェック項目の更新はマージ後）。

- [x] **Step 2: Plan のチェックボックスを更新し、コミットする**

```bash
git add docs/superpowers/specs/2026-10-05-issue-5-review-fix-three-outcomes-design.md docs/superpowers/plans/2026-10-05-issue-5-review-fix-three-outcomes.md
git commit -m "docs(spec): Issue #5 第1段階の実装の記録を残す"
```

- [ ] **Step 3: push して PR を作る**

```bash
git push -u origin feat/issue-5-review-fix-three-outcomes
gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-5-review-fix-three-outcomes \
  --title "review-fix-planning: 修正要否を三択で確定して完遂する流れを既定にする（Issue #5 第1段階）" \
  --body-file "$SCRATCH/pr-body.md"
```

PR の本文（`$SCRATCH/pr-body.md`）には、概要、変更点（SKILL.md の節ごと、evals・openai.yaml）、決定事項の要点（D-1・D-2・D-6・D-10・D-12）、検証（Task 5・6 の結果）、次の段階に回したもの（Spec 7 章）、`Refs #5`（第 1 段階なので Closes にしない）、末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)` を書く。

- [ ] **Step 4: PR の作成を確かめる**

Run: `gh pr view --repo usaturn/create-reso-world feat/issue-5-review-fix-three-outcomes --json number,url,state,headRefOid`
Expected: `state` が `OPEN`、`headRefOid` がローカルの `HEAD` と一致
