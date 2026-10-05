# Issue #43 review-fix-planning 第 2 段階 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `review-fix-planning` に、同じ条件の再発時の設計の見直し（経路の引き上げ）、失敗時の検証の方針、公開の単位を入れる。

**Architecture:** 既存の SKILL.md の節見出し・番号付き手順の名前・実行される bash ブロックを残したまま、「守る条件と影響経路」の後に新しい節「同じ条件の再発と設計の見直し」「失敗時の検証」を足し、手順 4・5、結論 1・3、自己レビュー、状況コメントのテンプレート、Spec の必須の中身、合理化の表、Red flags から参照する。eval を 3 件足す。

**Tech Stack:** Markdown（SKILL.md）、JSON（evals）、pytest、bash、`gh`

**Spec:** `docs/superpowers/specs/2026-10-06-issue-43-review-fix-stage2-design.md`（`062c70f`、draft。利用者の「推奨案で進めて、途中で止めずに PR まで作成せよ」に基づき、エージェントが推奨値で決めた。明示承認は得ていない）

**実行方法:** Native（`superpowers:executing-plans`）。利用者が途中で止めないことを指示しているため、推奨の方法を選んだ。タスクはすべて同じ SKILL.md の文面で互いに参照し合い、件数も少ないので、同じセッションで実装し、最後に新しい文脈のレビューを 1 回行う。

## Global Constraints

- 作業場所: worktree `/workspaces/reso-world/.worktrees/issue-43-review-fix-stage2`、ブランチ `feat/issue-43-review-fix-stage2`（`origin/main` の `e6edcf8` から作成）
- 編集してよいファイル: `.agents/skills/review-fix-planning/SKILL.md`、`.agents/skills/review-fix-planning/evals/evals.json`、この Plan と Spec。`agents/openai.yaml`・`evals/trigger_queries.json`・`tests/**`・`scripts/upsert_pr_comment.py` は変えない
- 節見出し（`## 実装後`・`## 作業終了前の PR 投稿`・`## Spec のコミットと確認用コピー`・`## Spec の正本を選んでから更新する`・`## 第1引数の解決`・`## 手順`）と手順の名前（「1. **範囲を固定する**」〜「7. **承認を得て停止する**」）は変えない
- `## 実装後` の節は変えない
- 行頭（空白を除く）が「例:」で始まる行を足さない
- 新しい文に `--operation review-fix`・`--pr "$PR_NUMBER"`・`docs_draft`・`$MAIN_ROOT/docs`・`$TOPLEVEL/docs/superpowers/specs/` を書かない
- 新しい固定文字列のテストは書かない。既存のテストが失敗したら、固定値を書き換える前に要否を利用者に示す（#36）
- 日本語表現: 「正本」「契約」「原子的」「製品」「着地」を新しい文に使わない（既存の見出しの引用を除く）
- この Plan の実行では `main` 向けの PR を作るまで行い、マージはしない。PR の本文に `Refs #5` と `Closes #43` を書く

## Review Focus

- 以前のコミットはあるが、レビュー修正ではない（機能の実装のコミットだけの）PR の 1 回目: きっかけ 1・2 に当てはめず、通常の結論 1 にする。Task 4 の場面 S4
- 同じ条件に触れる致命的でない指摘: 数えない（「対応する」項目だけを数える）。Task 1 の新しい節の文面で「数えるのは「対応する」項目だけ」を書く
- 自己レビューでの再発（きっかけ 3）: 2 回目の自己レビューをせず、見直しを再レビューしていないことを記録する。Task 1 の新しい節と結論 1 の手順 4
- 失敗時の扱いを直さない修正（文面だけの PR など）: 「失敗時の検証」を求めない。Task 1 の新しい節の適用条件（守る条件が失敗・拒否・中断の扱いのとき）
- 保証を狭める直し方を選んだとき: PR の説明の保証と既知の制限を直す。Task 1 の新しい節の手順 3

---

### Task 1: SKILL.md の手順 4・5、新しい 2 節、結論 1・3、自己レビュー

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（手順 4・5、「守る条件と影響経路」の後、「三択の結論」の結論 1・結論 3、「修正後の自己レビュー」）

**Interfaces:**
- Produces: 節の名前「同じ条件の再発と設計の見直し」「失敗時の検証」、きっかけの名前「同じ守る条件の 2 回目」「修正が生んだ回帰」「自己レビューでの再発」（Task 2 のテンプレート・必須の中身・合理化・Red flags と Task 3 の eval が参照する）

- [ ] **Step 1: 手順 4 を書き換える**

置き換え前:

```markdown
4. **下記「分類の仕様」に従って全指摘を 3 区分に振り分ける。** 「対応する」項目ごとに、下記「守る条件と影響経路」の表を作る。
```

置き換え後:

```markdown
4. **下記「分類の仕様」に従って全指摘を 3 区分に振り分ける。** 「対応する」項目ごとに、下記「守る条件と影響経路」の表を作り、下記「同じ条件の再発と設計の見直し」のきっかけに当たるかを確かめる。
```

- [ ] **Step 2: 手順 5 を書き換える**

置き換え前:

```markdown
5. **修正方針を決める** — 計画のみでは `superpowers:brainstorming` を呼び、選別結果を持って経路（spike / bounded / architectural）を判定させ、その経路の作法で設計を詰める。完遂では brainstorming を呼ばない（人の承認を必須の段として持つため）。推奨案を自分で決め、設計の選択があれば他の案と選んだ理由を Spec に残す。ユーザに問わない。
```

置き換え後:

```markdown
5. **修正方針を決める** — 計画のみでは `superpowers:brainstorming` を呼び、選別結果を持って経路（spike / bounded / architectural）を判定させ、その経路の作法で設計を詰める。きっかけに当たった項目があれば、そのきっかけと根拠を渡して architectural にさせる。完遂では brainstorming を呼ばない（人の承認を必須の段として持つため）。推奨案を自分で決め、設計の選択があれば他の案と選んだ理由を Spec に残す。ユーザに問わない。きっかけに当たった項目は、点の修正ではなく設計の見直しで直す。
```

- [ ] **Step 3: 「守る条件と影響経路」の節の末尾（「「修正する」の行は、PR の差分外でも同じ PR で直す。」の後、`## 三択の結論` の前）に 2 節を足す**

````markdown
## 同じ条件の再発と設計の見直し

「対応する」項目ごとに、表を作るときに次のきっかけに当たるかを確かめる。当たった項目は点の修正で直さず、設計の見直しに切り替える（経路の引き上げ）。同じ仕組みへの修正が、回帰と適用漏れを繰り返すのを止めるためである。

**きっかけ**（どれか 1 つ）:

1. **同じ守る条件の 2 回目** — 破れている条件、または直す仕組み（関数・state の項目・判定）が、同じ PR の以前の回で致命的な指摘として直したものと同じである。前の回の表で漏れた隣の経路も含む
2. **修正が生んだ回帰** — 指摘の原因が、同じ PR の以前のレビュー修正のコミットが入れた変更である
3. **自己レビューでの再発** — 修正後の自己レビューで、この回に直した条件がまた破れている、またはこの回の修正が原因の致命的な指摘が出た

以前の回は、同じテーマの Spec の記録（以前の回の表・結論・コミット）と、PR のコミット履歴（`git log`）のうちレビュー指摘の修正として入ったコミットで確かめる。回帰は `git log -L`・`git blame`、またはそのコミットの前後での再現で確かめる。以前のレビュー修正が Spec にも PR の履歴にも無ければ、1・2 には当たらない。数えるのは「対応する」項目だけである。

**計画のみでは**、brainstorming に経路を判定させるときに、当たったきっかけと根拠を渡し、architectural にさせる。Spec には下の 1〜3 を書いて承認を求める。

**完遂では**、止まらずに（結論 3 にしない）、結論 1 の修正の中で次を行う。

1. **守る条件を文書にする** — Spec に「守る条件の設計」を書く。条件を、再現した 1 経路ではなく、その仕組みが扱うすべての状態・操作順・停止位置で成り立つ性質として書く。条件を保つ仕組みと、以前の回の修正（コミット）それぞれで足りなかった理由も書く
2. **影響経路を全面的に見直す** — 表を、今回の指摘の経路からではなく仕組みから作り直す。その state の項目を書くすべての箇所、その関数のすべての呼出元、すべての停止・失敗の位置を列挙する。表に「変更前の挙動」と「確かめる assertion（何を比べるか）」の列を足す
3. **直し方を選び直す** — 少なくとも「点の修正を続ける」「条件を 1 か所で保つ形にまとめる」「PR の保証を狭めて条件を不要にする」を比べて推奨案を選び、他の案と理由を Spec に残す。条件が構造で成り立つ案を優先する。点の修正を続けるなら、列挙したすべての経路で条件が成り立つ根拠を書く。保証を狭めたら、PR の説明の保証と既知の制限を直す。PR の分割は第二の PR になるので行わず、より良いと考えたら他の案として残す
4. **全経路で確かめる** — 検証を、再現した場面だけでなく、列挙したすべての経路で条件を確かめる形にする。失敗時の扱いなら下記「失敗時の検証」に従う
5. 結論 1 の残りの手順に戻る。自己レビューの反証の担当には、守る条件の設計も渡す

きっかけ 3 で切り替えたときも、自己レビューの 2 回目はしない。見直した内容を再レビューしていないことを Spec と状況コメントに書く。

## 失敗時の検証

「対応する」項目の守る条件が、失敗・拒否・中断したときの扱い（「不正な入力なら何も変えずに止まる」「途中で止まっても中途半端な状態が残らない」など）であるとき、その修正の検証を次の形にする。終了コード・メッセージ・対象の 1 ファイルだけを見る検証は、別の状態が先に変わる実装を見逃す。

1. **状態全体を比べる** — 失敗させる前と後で、その処理が管理する状態全体を比べる。対象のファイルに加え、共有先（symlink の参照先、hard link の相手）、バックアップ、認証、一時ファイル、キャッシュ、外部コマンドの呼出しを含める。ファイルは有無・バイト列・mode・リンクの種類と参照先を見る。期待値は失敗させる前の状態から取り、固定値を書かない
2. **副作用の順序を確かめる** — 入力の不正で止める処理は、どの状態を変えるよりも前に、すべての入力（構文・値・必要な内部構造・保存先の種類）を検査しているかを確かめる。書き込みの途中の I/O の失敗は入力の不正と分け、何が残り、どこまで戻すかを Spec に書いて確かめる
3. **負例には異常を 1 つだけ入れる** — 他の条件は正常にし、想定した理由で拒否されたことと、状態が変わっていないことを確かめる。異常を 2 つ入れた負例は別の拒否の理由で止まり、確かめたいガードが無くても通る
4. **ガードを外した対照で検出力を確かめる** — 修正の中心になるガードを 1 つだけ外した版で、そのガードを確かめるすべての負例が失敗することを確かめる。ガードを外すのは、手順 3 と同じ `mktemp` の方法で作った隔離 worktree に修正後の内容を写したものだけで、専用の worktree では外さない。終わったら手順 3 の teardown と同じ方法で消す。安全に関わる境界のガードに絞り、すべてのコードの変異テストは求めない

テストを足すのは、致命的な指摘の修正と検証に要るときだけである（「分類の仕様」）。比べた状態と、対照で失敗した負例の数を Spec に書く。
````

- [ ] **Step 4: 結論 1 の番号付き手順を置き換える**

置き換え前（`### 結論 1: 修正して push する` の「「対応する」が 1 件以上あるとき。」の後の 6 項目）:

```markdown
1. 推奨案を基本に修正する。「守る条件と影響経路」の表の「修正する」の行は、PR の差分外も同じ PR で直す
2. **実装後** の手順 1–3（実装に関連したテストと、変更の種類に応じた検証）を通す。失敗したら直す。base でも同じように失敗する既存のテストは、base での結果を根拠として Spec に記録し、先へ進めてよい
3. 下記「修正後の自己レビュー」を 1 回だけ行う
4. 自己レビューで出た致命的な指摘を直し、手順 2 をやり直す。2 回目のレビューはしない。致命的でない指摘は「対応しない」として記録する
5. Spec に結果を書いて `completed` にし、コミットする（「Spec のコミットと確認用コピー」の完遂の項）
6. **実装後** の手順 4–6 で既存 PR の head へ push し、状況コメントを投稿する。その後「専用の worktree」を片付ける
```

置き換え後:

```markdown
1. 推奨案を基本に修正する。「守る条件と影響経路」の表の「修正する」の行は、PR の差分外も同じ PR で直す。「同じ条件の再発と設計の見直し」のきっかけに当たった項目は、その節の手順で直す
2. **実装後** の手順 1–3（実装に関連したテストと、変更の種類に応じた検証）を通す。失敗時の扱いを直したなら「失敗時の検証」も行う。失敗したら直す。base でも同じように失敗する既存のテストは、base での結果を根拠として Spec に記録し、先へ進めてよい
3. 下記「修正後の自己レビュー」を 1 回だけ行う
4. 自己レビューで出た致命的な指摘を直し、手順 2 をやり直す。2 回目のレビューはしない。致命的でない指摘は「対応しない」として記録する。この回に直した条件の再発や、この回の修正が原因の指摘は、きっかけ 3 として設計の見直しで直す
5. Spec に結果を書いて `completed` にする
6. **公開の前に揃える** — 次がすべて済むまで、Spec のコミットと push をしない。途中の修正を先に push しない
   - 最後の修正の後に、手順 2 の検証が通っている
   - 自己レビューの全指摘に判定がある（直した、または「対応しない」と理由）。未確認の事項は、未確認として Spec と状況コメントに書く
   - Spec と PR の説明に書いた件数・参照先・保証が、実装と検証の結果に合っている
   - 公開済みのコミットを書き換えない（force push しない）
7. Spec をコミットし（「Spec のコミットと確認用コピー」の完遂の項）、**実装後** の手順 4–6 で既存 PR の head へ push し、状況コメントを投稿する。その後「専用の worktree」を片付ける
```

- [ ] **Step 5: 結論 3 の「理由にならない」一覧に足す**

置き換え前:

```markdown
未読・未検証、判断に迷う、修正が大きい、テストが失敗する（直す）、再現できない（根拠を付けて「解消済み」か「対応しない」にする）は、結論 3 の理由にならない。
```

置き換え後:

```markdown
未読・未検証、判断に迷う、修正が大きい、テストが失敗する（直す）、再現できない（根拠を付けて「解消済み」か「対応しない」にする）、同じ条件の再発（「同じ条件の再発と設計の見直し」で直す）は、結論 3 の理由にならない。
```

- [ ] **Step 6: 自己レビューの観点 3 に足す**

置き換え前:

```markdown
3. **検証の検出力** — 追加・変更したテストと検証が、修正対象の欠陥を実際に検出できるか（assertion が変更対象全体を見ているか、別の拒否理由に隠れていないか）
```

置き換え後:

```markdown
3. **検証の検出力** — 追加・変更したテストと検証が、修正対象の欠陥を実際に検出できるか（assertion が変更対象全体を見ているか、別の拒否理由に隠れていないか）。失敗時の扱いを直したなら「失敗時の検証」の 4 点で見る
```

- [ ] **Step 7: 既存のテストを通す**

Run: `uv run pytest .agents/skills/review-fix-planning tests/scripts/test_superpowers_lifecycle.py -q`
Expected: すべて成功（exit 0）。失敗したら、固定値を書き換える前に、どの検査がどの文字列で落ちたかを確かめ、文面の側で Global Constraints に反していないかを直す

- [ ] **Step 8: コミット**

```bash
git add .agents/skills/review-fix-planning/SKILL.md
git commit -m "feat(review-fix-planning): switch to a design review when the same condition breaks again

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: SKILL.md の記録・合理化・Red flags

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（「作業終了前の PR 投稿」のテンプレート、「Spec は経路に関わらず必須」、「合理化とその実態」、「Red flags」）

**Interfaces:**
- Consumes: Task 1 の節の名前ときっかけの名前

- [ ] **Step 1: 状況コメントのテンプレートの「作業判断」に 1 行足す**

置き換え前（markdown のテンプレートの中。bash の heredoc のブロックは変えない）:

```markdown
- 解消済み: 件数と代表根拠

### 作業結果
```

置き換え後:

```markdown
- 解消済み: 件数と代表根拠
- 設計の見直し: なし | 項目の ID、きっかけ（同じ守る条件の 2 回目／修正が生んだ回帰／自己レビューでの再発）、選んだ直し方

### 作業結果
```

- [ ] **Step 2: 「Spec は経路に関わらず必須」の必須の中身に 1 項目足す**

置き換え前:

```markdown
  - 計画のみでは brainstorming が判定した経路名。完遂では結論（三択のどれか）、実行許可（依頼の文言の要旨）、実行した検証と結果、自己レビューの観点と結果
```

置き換え後:

```markdown
  - 計画のみでは brainstorming が判定した経路名。完遂では結論（三択のどれか）、実行許可（依頼の文言の要旨）、実行した検証と結果、自己レビューの観点と結果
  - きっかけに当たった項目は、きっかけと根拠、守る条件の設計、比べた直し方と選んだ理由。「失敗時の検証」を行ったときは、比べた状態と対照の結果
```

- [ ] **Step 3: 合理化の表の末尾（「「pr-review で再レビューする」」の行の後）に 7 行足す**

```markdown
| 「前の回と同じ条件だが、今回の経路は別なので点の修正で足りる」 | 同じ守る条件の 2 回目である。設計の見直しに切り替え、仕組みから経路を列挙し直す |
| 「回帰は、入れたコミットを直せば済む」 | 修正が生んだ回帰は、前の回の列挙が足りなかった証拠である。設計の見直しに切り替える |
| 「同じ問題が続いたので、止めて利用者に判断を仰ぐ」（完遂） | 完遂では止まらない。設計の見直しを修正の中で行う。計画のみなら architectural にさせる |
| 「拒否のテストは非ゼロ終了を確かめているので十分」 | 状態全体を比べる。対象のファイルが変わらなくても、バックアップや認証が先に変わることがある |
| 「異常を詰め込んだ負例 1 本で網羅できる」 | 別の拒否の理由で止まり、ガードの欠落を見逃す。負例には異常を 1 つだけ入れる |
| 「ガードを入れたのでテストも効いているはず」 | ガードを外した対照で、負例が失敗することを確かめる |
| 「直した分だけ先に push しておく」 | 検証・自己レビューの判定・記録の確認が揃うまで push しない |
```

- [ ] **Step 4: Red flags の末尾に 6 行足す**

```markdown
- きっかけに当たるのに、守る条件の設計を書かずに点の修正をしようとしている
- 同じ条件の再発を理由に結論 3 で止まろうとしている
- 失敗時の扱いを直したのに、検証が終了コード・メッセージ・対象の 1 ファイルしか見ていない
- 1 つの負例に異常を 2 つ以上入れている
- ガードを外した対照を専用の worktree で行おうとしている
- 自己レビューの指摘の判定や記録の確認が済む前に push しようとしている
```

- [ ] **Step 5: 既存のテストを通し、禁止の文字列が無いことを確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning tests/scripts/test_superpowers_lifecycle.py -q`
Expected: すべて成功（exit 0）

Run: `git diff e6edcf8 -- .agents/skills/review-fix-planning/SKILL.md | grep '^+' | grep -nE '正本|契約|原子的|製品|着地|docs_draft|^\+\s*例:'`
Expected: 出力なし（exit 1）

- [ ] **Step 6: コミット**

```bash
git add .agents/skills/review-fix-planning/SKILL.md
git commit -m "feat(review-fix-planning): record design reviews and guard failure-path checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: eval の追加

**Files:**
- Modify: `.agents/skills/review-fix-planning/evals/evals.json`（`evals` の配列の末尾、id 11 の後）

**Interfaces:**
- Consumes: Task 1・2 の節の名前ときっかけの名前

- [ ] **Step 1: id 12〜14 を足す**

`evals` の配列の末尾に、次の 3 件を足す（既存の id 1〜11 は変えない）。

```json
    {
      "id": 12,
      "name": "same-condition-second-violation-switches-to-design-review",
      "prompt": "（思考実験として、取る行動を順に書く。コマンドの実行、ファイルの変更、GitHub への操作はしない）usaturn/create-reso-world の PR #901（open、draft ではない）とレビュー結果 reviews/#901-fix-sync/ を確認し、修正要否を確定して。同じテーマの Spec には前の回の記録があり、「同期の途中で止まっても state の index は Slot の並びと一致する」という条件を、コミット abc1234 で直している。今回のレビューには、同じ条件を別の経路（削除の後）で破る致命的な指摘が 1 件あり、現行 HEAD で再現する。",
      "expected_output": "Conclusion 1 with a design review: the finding is 対応する and recognized as the second violation of the same condition; the run neither stops nor applies another point patch; it writes the condition design into the Spec, rebuilds the path table from the mechanism, compares fix designs, verifies every path, runs one self-review and the pre-publication checks, then pushes.",
      "files": [],
      "expectations": [
        "The finding is classified as 対応する and identified as the second violation of the same condition, citing the earlier Spec record or commit abc1234.",
        "The run does not stop with conclusion 3 and does not ask the user to choose; it switches to the design review inside conclusion 1.",
        "The Spec gets the condition design, a table rebuilt from the mechanism (all writers, callers and stop points, with prior behavior and assertions) and the compared fix designs with the chosen one.",
        "Verification covers every enumerated path, the self-review runs once, and the push happens only after the pre-publication checks."
      ]
    },
    {
      "id": 13,
      "name": "regression-from-earlier-fix-switches-to-design-review",
      "prompt": "（思考実験として、取る行動を順に書く。コマンドの実行、ファイルの変更、GitHub への操作はしない）usaturn/create-reso-world の PR #902（open、draft ではない）とレビュー結果 reviews/#902-fix-cache/ を確認し、レビュー指摘に対応して。致命的な指摘が 1 件あり、現行 HEAD で再現する。原因は、前の回のレビュー修正のコミット def5678 が足した分岐で、そのコミットの前の版では再現しない。",
      "expected_output": "The cause is traced to the earlier review-fix commit and treated as a regression from a fix; the run switches to the design review inside conclusion 1 instead of patching the new branch, without stopping or asking the user, and records the trigger and its evidence in the Spec.",
      "files": [],
      "expectations": [
        "The cause is traced to commit def5678 (git log -L, git blame or reproduction before and after it) and identified as a regression from an earlier fix.",
        "The agent switches to the design review instead of patching the branch, without stopping with conclusion 3 or asking the user.",
        "The Spec records the trigger, its evidence, the condition design and why the earlier fix fell short."
      ]
    },
    {
      "id": 14,
      "name": "failure-path-fix-checks-whole-state-and-control",
      "prompt": "（思考実験として、取る行動を順に書く。コマンドの実行、ファイルの変更、GitHub への操作はしない）usaturn/create-reso-world の PR #903（open、draft ではない）のレビュー指摘に対応している。致命的な指摘は「不正な models.json で止まるとき、models.json は変わらないが、先にバックアップが作られ auth.json が書き換わる」で、現行 HEAD で再現した。修正後のテストは、終了コードが非ゼロであることと models.json のバイト列だけを比べている。負例の入力には、不正な数値と壊れた lock の 2 つの異常が入っている。この後どう検証するか。",
      "expected_output": "The failure-path verification: compare the whole managed state before and after (backup, auth, links, temp files) with expectations taken from the pre-run state, confirm all inputs are validated before any state changes, split the negative case so each has one anomaly, and run a control with the central guard removed in an isolated mktemp worktree where every negative case for that guard fails; record the results in the Spec.",
      "files": [],
      "expectations": [
        "The test compares the whole managed state before and after (backup, auth, links, temp files), with expectations taken from the pre-run state rather than fixed values.",
        "It checks that every input is validated before any state changes.",
        "Each negative case carries exactly one anomaly and asserts the expected rejection reason.",
        "A control with only the central guard removed runs in an isolated mktemp worktree, not the dedicated worktree, every negative case for that guard fails, and the results go into the Spec."
      ]
    }
```

- [ ] **Step 2: JSON として読めて、id が重ならないことを確かめる**

Run: `uv run --no-project python -c "import json; ids=[e['id'] for e in json.load(open('.agents/skills/review-fix-planning/evals/evals.json'))['evals']]; assert len(ids)==len(set(ids)), ids; print(ids)"`
Expected: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]`

- [ ] **Step 3: コミット**

```bash
git add .agents/skills/review-fix-planning/evals/evals.json
git commit -m "test(review-fix-planning): add evals for design reviews and failure-path checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: リポジトリの検査とスキルの文面の検証

**Files:**
- 変更なし（結果は Task 6 で Spec に書く）

- [ ] **Step 1: リポジトリの検査を順に実行する**

Run（worktree のルートで、1 つずつ）:

```bash
uv run pytest tests/skills .agents/skills
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
```

Expected: 3 つとも exit 0。件数（passed・skipped、PASS の本数）を記録する

- [ ] **Step 2: 比べる 2 版を、版の分からない名前で用意する**

```bash
SP=/tmp/claude-1000/-workspaces-reso-world/6bbdb1fc-9ecc-4e26-853b-0a26981c4201/scratchpad
git show e6edcf8:.agents/skills/review-fix-planning/SKILL.md > "$SP/skill-A.md"
cp .agents/skills/review-fix-planning/SKILL.md "$SP/skill-B.md"
```

`skill-A.md` が旧版、`skill-B.md` が新版である（対応はサブエージェントに伝えない）。

- [ ] **Step 3: 場面ごとにサブエージェントを起動する（旧版 S1〜S3、新版 S1〜S4 の計 7 回、並行してよい）**

各サブエージェント（新しい文脈、general-purpose）への依頼文:

```text
次のファイルに書かれたスキル（エージェント向けの手順書）だけに従って行動する前提で、下の場面で取る行動を順に書いてください。
読み取り専用の思考実験です。Read ツールでそのファイルを読むことだけを行い、コマンドの実行、ファイルの変更、GitHub への操作、他のファイルの読み込みはしないでください。

スキルのファイル: <SP>/skill-<A|B>.md

場面: <下の S1〜S4 のどれか>

回答の形式:
1. 取る行動（番号付きで順に。どの段で何を書く・確かめる・コミットする・push するか）
2. 最終的な結論（三択のどれか、計画のみ、または停止）
3. 従ったスキルの節の名前
```

場面の文面:

- S1: 「usaturn/create-reso-world の PR #901（open、draft ではない）とレビュー結果 reviews/#901-fix-sync/ を確認し、修正要否を確定して」と頼まれた。同じテーマの Spec には前の回の記録があり、「同期の途中で止まっても state の index は Slot の並びと一致する」という条件を、コミット abc1234 で直している。今回のレビューには、同じ条件を別の経路（削除の後）で破る致命的な指摘が 1 件あり、現行 HEAD で再現する。他の指摘は致命的ではない
- S2: 「usaturn/create-reso-world の PR #902（open、draft ではない）とレビュー結果 reviews/#902-fix-cache/ を確認し、レビュー指摘に対応して」と頼まれた。致命的な指摘が 1 件あり、現行 HEAD で再現する。原因は、前の回のレビュー修正のコミット def5678 が足した分岐で、そのコミットの前の版では再現しない
- S3: usaturn/create-reso-world の PR #903（open、draft ではない）のレビュー指摘に完遂で対応している。致命的な指摘は「不正な models.json で止まるとき、models.json は変わらないが、先にバックアップが作られ auth.json が書き換わる」で、現行 HEAD で再現した。修正を書き終え、テストは終了コードが非ゼロであることと models.json のバイト列だけを比べている。負例の入力には、不正な数値と壊れた lock の 2 つの異常が入っている。ここから push までに何をするか
- S4: 「usaturn/create-reso-world の PR #904（open、draft ではない）とレビュー結果 reviews/#904-feat-export/ を確認し、修正要否を確定して」と頼まれた。1 回目のレビューで、PR のコミットは機能の実装の 2 件だけ（レビュー修正のコミットは無く、同じテーマの Spec も無い）。致命的な指摘が 1 件あり、現行 HEAD で再現する。失敗時の扱いに関する指摘ではない

- [ ] **Step 4: 回答をすべて読み、期待と比べる**

| 場面 | 新版で期待する行動 |
| --- | --- |
| S1 | 「対応する」にし、同じ守る条件の 2 回目と判定する。結論 3 にしない、利用者に問わない。守る条件の設計を Spec に書き、仕組みから経路を列挙し直し、直し方を比べて選び、全経路で確かめ、自己レビュー 1 回、公開の前の確認の後に push（結論 1） |
| S2 | def5678 が原因の回帰と判定し、S1 と同じく設計の見直しで結論 1 |
| S3 | 状態全体（バックアップ・auth・リンク・一時ファイル）を前後で比べる（期待値は実行前の状態から）、検査が副作用より前かを確かめる、負例を異常 1 つずつに分ける、隔離 worktree でガードを外した対照で負例が失敗することを確かめる、結果を Spec に書く、その後に自己レビューと公開の前の確認 |
| S4 | 設計の見直しに切り替えず、通常の結論 1（表 → 修正 → 検証 → 自己レビュー 1 回 → push） |

新版で期待と違う行動があれば、その言い訳を合理化の表と Red flags に足して（Task 2 と同じ書き方）、その場面だけ新しいサブエージェントでやり直す（やり直しは 1 回まで）。旧版の結果でスキルを変える判断はしない。文面を直したら Step 1 をやり直し、コミットする:

```bash
git add .agents/skills/review-fix-planning/SKILL.md
git commit -m "fix(review-fix-planning): close gaps found by the scenario checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 5: ブランチ全体のレビュー（1 回）

**Files:**
- 指摘を直す場合だけ `.agents/skills/review-fix-planning/SKILL.md`・`evals/evals.json`

- [ ] **Step 1: 新しい文脈のサブエージェント 1 体にレビューを依頼する**

依頼文:

```text
usaturn/create-reso-world の worktree /workspaces/reso-world/.worktrees/issue-43-review-fix-stage2 のブランチ feat/issue-43-review-fix-stage2 を、e6edcf8 との差分（git diff e6edcf8...HEAD）でレビューしてください。読み取りだけを行い、ファイルの変更・commit・push・GitHub への書き込みはしないでください。
設計は docs/superpowers/specs/2026-10-06-issue-43-review-fix-stage2-design.md、計画は docs/superpowers/plans/2026-10-06-issue-43-review-fix-stage2.md にあります。
報告するのは致命的な問題だけです。致命的とは、この SKILL.md に従うエージェントが、実在する使い方で、秘密情報の露出、データの消失・破損、了承の無い設定変更や誤った対象への操作、手順どおりに進めて誤った結果になること、主要な処理が止まること、のどれかを起こし得ることです。表記・言い回し・網羅の粗さは報告しないでください。
各指摘に、ファイルと行、起こる場面（どの依頼で、どの段で、何が起きるか）を付けてください。指摘が無ければ「致命的な指摘なし」と書いてください。
```

- [ ] **Step 2: 指摘を判定する**

各指摘を #38 の Spec の D-6（致命的かどうか、現行 HEAD で確かめられるか）で判定する。致命的なものだけを直し、Task 4 の Step 1 をやり直してコミットする。2 回目のレビューはしない。致命的でない指摘は「対応しない」として Task 6 で記録する。

```bash
git add .agents/skills/review-fix-planning/SKILL.md .agents/skills/review-fix-planning/evals/evals.json
git commit -m "fix(review-fix-planning): address the branch review

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 6: 記録・push・PR の作成

**Files:**
- Modify: `docs/superpowers/specs/2026-10-06-issue-43-review-fix-stage2-design.md`（末尾に「8. 実装の記録」、冒頭の状態）

- [ ] **Step 1: Spec に実装の記録を書く**

末尾に「## 8. 実装の記録」を足し、次を書く: 実行方法、コミットの一覧、6.1 の検査の結果（コマンドごとの件数と exit code）、6.2 の場面ごとの新版・旧版の行動の要約と期待との差、6.3 のレビューの指摘と判定、Plan との差、所要時間（UTC）、未実施（マージ、#5 の本文の A のチェック。どちらも調整役か利用者が行う）。冒頭の状態を「completed（実装・検証・PR の作成まで完了。マージは未実施。Spec 自体の明示承認は得ていない）」にする。

- [ ] **Step 2: 最終の検査をやり直す**

Run: Task 4 の Step 1 の 3 コマンド
Expected: 3 つとも exit 0

- [ ] **Step 3: コミットして push する**

```bash
git add docs/superpowers/specs/2026-10-06-issue-43-review-fix-stage2-design.md
git commit -m "docs(spec): record the issue #43 implementation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin feat/issue-43-review-fix-stage2
```

- [ ] **Step 4: PR を作る**

```bash
gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-43-review-fix-stage2 \
  --title "review-fix-planning 第 2 段階: 同じ条件の再発時の設計の見直し・失敗時の検証・公開の単位" \
  --body-file <本文のファイル>
```

本文には、概要、利用者の判断が要る点（D-1）の扱い（選択肢と推奨、「推奨案で進めて」の指示で (b) を採用したこと、PR のレビューで変えられること）、変更内容、検証（6.1・6.2・6.3 の結果）、範囲外、`Refs #5`、`Closes #43`、末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)` を書く。

- [ ] **Step 5: #43 に作業報告を書き、予約を解放する**

#43 に `planning: ready`、`implementation: done`（PR の URL、マージ待ち）、所要時間を書く。予約が保存した SHA のままなら、次で解放し、ref が無いことを確かめる。

```bash
git push --force-with-lease=refs/heads/agent-claims/issue-43:392935bf793b6aa9ccf4dd4e48014aa49cb1c2cc origin :refs/heads/agent-claims/issue-43
gh api repos/usaturn/create-reso-world/git/ref/heads/agent-claims/issue-43
```

Expected: 2 つ目は 404（Not Found）
