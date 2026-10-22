# Issue #232: .agents/scripts・review-fix-planning・review-verify のテストを新しい採用基準で減らす

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/232（親 #228、ボード `test-reduction-board`、子のキー `review-helper-tests`。先行 #229 は completed、PR #240 は `main` にマージ済み）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-22-create-reso-world-issue232-review-helper-tests.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-232-review-helper-tests`（branch `feat/issue-232-review-helper-tests`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-22（JST）、利用者が次のとおり指示した

  ```text
  /issue-to-pr #232 --merge
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #232`）まで行い、`--merge` により PR 修正ループを回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う。Issue の「マージは利用者が行う（利用者が明示した指示がある場合を除く）」は、この `--merge` を明示の指示として扱う
  - 方針は #228 の「利用者の決定（2026-10-21）」と「削除と採用の基準」、`AGENTS.md` の「テストの採用基準」に従い、議論し直さない。ほかの判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- ループのオプション（`loop.py check-options`）: `max_cycles = 3`、`assign = {}`、`template = .devcontainer/agent-runner.toml`、`config = null`（いずれも既定の適用）。割り当て: レビュー（`inspect`）が `pi-gpt`・`devin-swe`・`dsh-ccd`・`cursor-grok47`、修正（`implement`）が `claude-opus`、自己レビュー・修正の確認が `self`。`fallback` なし
- 実装の担当: `implement_task.py check` は `agents = ["self"]`・`self: true`（雛形の既定の適用。利用者の指定ではない）。このセッションが、サブエージェントに領域を分けて依頼する（D-232-2）
- 予約: `refs/heads/agent-claims/issue-232` = `b50af656cc4396d6d8d727754466dcec80db8742`（セッション `64c605ef-b8eb-4b82-b400-be797a1bb277`、2026-10-22T15:52:19Z）
- 基準: `origin/main` の `481a047`

## 意図

#228 の方針に従い、この領域（`.agents/scripts`、`review-fix-planning`、`review-verify`）のテストを、`AGENTS.md` の「テストの採用基準」で F（F∩S を除く）・L・D の余りに当たるものを消して減らす。残るのは S（F∩S を含む）と D の代表だけで、棚卸しの表に全てのテストの分類と理由を残す。数を合わせるために、気付けない損害を防ぐテストは消さない（#228 の決定 6）。

## 基準値（`481a047`、コミット済みの状態）

| 指標 | 値 |
| --- | --- |
| 件数 | 1,056 |
| 行数 | 9,919 |

ファイル別の件数: `test_agent_tmp.py` 21、`test_issue_budget.py` 15、`test_review_findings.py` 231、`test_review_records.py` 205、`test_review_target.py` 59、`test_finalize.py` 169、`test_review_fix_planning_skill_contract.py` 70、`test_run_roles.py` 49、`test_upsert_pr_comment.py` 75、`test_dispatch.py` 151、`test_evaluation.py` 11（`conftest.py` は 33 行）。

## 設計

### 1. 範囲と禁止

Issue 本文の「範囲と禁止」のとおり。変えてよいのは、この領域のテストと、使われなくなった経路のコードの撤去（`git grep` などで呼び出し元が無いと確かめたものだけ）、撤去した経路を説明する行だけである。`pr-review`・`pr-review-fix-loop`・`tools/test_support/`・ルートの `conftest.py`・`pyproject.toml`・`AGENTS.md`・ほかの領域は変えない。

### 2. 進め方

1. テストのファイルごとに、全てのテスト（関数・クラス・parametrize の群）を F・F∩S・L・S・D・撤去・迷いに分類する。S は防ぐ損害と重さ（高・中・低）、L は気付ける経路、撤去は使われていない根拠を書く
2. F・L・D の余り・撤去は消す。消したテストだけが使っていた fixture・補助も消す
3. 重さが高の守りで代表に絞ったものは、守る処理を一時的に壊した使い捨てのコピー（`/tmp` に `mktemp -d`）で、残したテストが失敗することを 1 回ずつ確かめる
4. `test_review_findings.py` の factory のうち `review-verify/tests/test_dispatch.py` が読み込むものは、`test_dispatch.py` を整理するまで残す（Issue の順序の注意）
5. 層をまたぐ重複は、守りを実装している側のテストを残す。`tools/agent_runner` が実装している checkout の事前検査は、run_roles・dispatch の側を消してよい（#228 の「層をまたぐ重複」）

### 3. 棚卸しの表

この節の下の「棚卸し」に、ファイル別の表を置く。同じ理由のテストはファイル・クラス・parametrize の群で 1 行にまとめる。

### 4. 検証

- 領域: `uv run --locked pytest .agents/scripts .agents/skills/review-fix-planning .agents/skills/review-verify`
- 全体: `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`git diff --check`
- 計測: Issue の「検証」のコマンド（コミット済みの状態）

## 受け入れ条件

1. 棚卸しの表があり、全てのテストに分類と理由がある
2. F（F∩S を除く）・L・D の余り・撤去したもののテストと、それだけが使っていた fixture・補助が消えている
3. 重さが高の守りで代表に絞ったものについて、一時的に壊したコピーで残したテストが失敗することを確かめ、結果を「検証の記録」に書いている
4. 残したテストが通る。全体の入口で、この変更による失敗が無い
5. 前後の件数・行数を「検証の記録」と Issue に書いている

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-232-1 ファイルごとの分類と削除を行い、削除は基準の定義だけで決める**
  - 選択: 11 のテストファイルを単位に、上の設計 2 の手順で分類して消す。件数・行数の目標値は設けず、基準に当たるものだけを消す
  - 別案: 行数の目標（基準値の 1/3）に合わせて、守りの軽いものから消す
  - 理由: #228 の決定 6。1/3 に届かない分は `integration` の一覧を見て利用者が決める。この子で気付けない損害を防ぐテストを消すと、取り戻せない
  - 停止条件: 分類に迷うものは残し、表に「迷い」と書く
- **D-232-2 実装は、領域を分けたサブエージェントに同期で依頼し、このセッションが commit・統合・検証する**
  - 選択: `superpowers:subagent-driven-development` の形で、テストのファイル単位の Task をサブエージェント（general-purpose）に依頼する。担当は自分のファイルとそのコードだけを変え、commit・push しない。棚卸しの行は担当のファイルの断片（セッションディレクトリ）に書かせ、このセッションが Spec に統合する
  - 別案: (a) このセッションが全て inline で行う、(b) runner の担当に依頼する（`--implement` の指定は無い）
  - 理由: 分類は 1,056 件を読む作業で、ファイルごとに独立している。1 つのファイルの読みと分類を子の文脈に閉じると、controller の文脈が持つ。同じファイルを同時に書かせない
- **D-232-3 順序は 2 段階にし、`test_dispatch.py` は `test_review_findings.py` の後にする**
  - 選択: 第 1 段階で `test_review_findings.py`、`test_review_records.py`、`test_review_target.py`・`test_agent_tmp.py`・`test_issue_budget.py`・`test_evaluation.py`、`test_finalize.py`、`test_run_roles.py`・`test_upsert_pr_comment.py`・skill_contract を並行して行う。第 2 段階で `test_dispatch.py`
  - 別案: 全て直列、または全て並行
  - 理由: `test_dispatch.py` は `test_review_findings.py` を読み込んで factory を使う。コードの撤去が複数のファイルにまたがるので、撤去の候補は担当が `git grep` で確かめ、別の担当の領域のコードは変えない
- **D-232-4 コードの撤去は、`git grep`・文書・雛形・設定からの参照で呼び出し元が無いと確かめたものに限り、根拠を表に書く**
  - 選択: #228 の決定 5 のとおり。確かめられないものは撤去せず、S か L として扱う
  - 別案: テストの無い経路を、使われていないと推定して撤去する
  - 理由: `review_records.py`・`review_findings.py`・`finalize.py` などは pr-review・pr-review-fix-loop・issue-to-pr からも使われる
- **D-232-5 重さが高の守りの確認は、使い捨てのコピーで 1 回ずつ行う**
  - 選択: `mktemp -d` で作ったコピーに守る処理を壊す変更を入れ、残したテストが落ちることを確かめる。作業ツリーのコードは壊さない。結果を「検証の記録」に書く
  - 別案: 作業ツリーで壊して戻す
  - 理由: Issue の受け入れ条件。作業ツリーを壊すと、他の担当の並行作業に影響する
- **D-232-6 branch は `feat/issue-232-review-helper-tests`、worktree は Issue の指定の `.worktrees/issue-232-review-helper-tests`**
  - 別案: `fix/`
  - 理由: 不具合の修正ではなく、テストの整理である

## 棚卸し

（実装中に、ファイル別の表を追記する。凡例: F・F∩S・L・S・D・撤去・迷い。S は「損害 / 重さ」を書く）

## 検証の記録

（実装後に追記する）
