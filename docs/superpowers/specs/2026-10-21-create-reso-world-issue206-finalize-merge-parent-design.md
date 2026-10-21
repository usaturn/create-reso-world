# Issue #206: finalize.py がマージの後に merge commit の最初の親を照合し、未検証の組み合わせを完了扱いしない

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/206（親 Issue・ボード・先行 Issue・コメントは無い。関連: #196・PR #203（マージの前の照合）、#207・PR #215（`merged` の 3 値）、#221・PR #226、#138（`Closes` による自動の close）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-21-create-reso-world-issue206-finalize-merge-parent.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-206-finalize-merge-parent`（branch `fix/issue-206-finalize-merge-parent`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-21（JST）、利用者が次のとおり指示した

  ```text
  /issue-to-pr https://github.com/usaturn/create-reso-world/issues/206 --merge --assign implement=self 利用者の決定を /workspaces/reso-world/tmp/agents/commander-219-220-221-206-212.0smdd1hj/decisions/issue-206.md に置いた。読んで Spec の決定記録に引用せよ
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #206`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）を回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う
  - 方針（D-206-1）は利用者の決定に従う。ほかの判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- ループのオプション（`loop.py check-options` の出力）: `max_cycles = 3`（既定の適用）、`assign = {"implement": ["self"]}`（利用者の指定 `--assign implement=self`）、`template = .devcontainer/agent-runner.toml`（既定の適用）、`config = null`。割り当ては、レビュー（`inspect`）が `devin-swe`・`pi-deepseek`・`claude-opus`・`pi-gpt`（個人設定 `~/.config/agent-runner/config.toml` の適用）、修正（`implement`）が `self`（利用者の指定）、自己レビュー（`self-review`）・修正の確認（`fix-check`）が `self`（雛形の既定の適用）。いずれも `fallback` なし
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の `workflows.issue` の既定の適用。個人設定に `workflows.issue` は無い。利用者の指定ではない）
- 基準: `origin/main` の `49aa950`

## 意図

`finalize.py` は、検証の後に base が進んだ PR をマージしないよう、状況の投稿の前とマージの直前に base ブランチの先端を照合する（#196）。それでも、最後の照合から GitHub がマージを処理するまでの間に別のセッションのマージで base が進むと、検証していない組み合わせがマージされる。GitHub のマージは base を固定できない。今の helper は、マージの後に state と head しか確かめないので、そのまま関連 Issue を閉じて `no_fix_needed` を返す。create-reso-world は CI を止めているので、ほかに気付く仕組みが無い。

利用者の決定（D-206-1）のとおり、マージの後の確認で merge commit とその最初の親を読み、検証の記録の `base` と照合して、helper の完了条件にする。一致しない・読めないときは、関連 Issue を更新せずに、マージ済みの事実と照合した SHA を残して止まる。完了は、merge commit のツリーで同じ検証をした記録で `finalize.py` を再実行する経路で行う。ループの中での自動の再検証と、マージの排他制御は入れない。

## 確認した事実（2026-10-21 JST、`49aa950`）

- `finalize.py`（`.agents/skills/review-fix-planning/scripts/finalize.py`）
  - `FIELDS`（`:48-59`）に `mergeCommit` が無い
  - `check_base`（`:218-244`）は base ブランチの先端（`gh api repos/<repo>/branches/<base>`）を検証の記録の `base` と比べる。呼ぶのは状況の投稿の前（`:405-407`、`--spec-commit` が無いとき）とマージの直前（`:423-426`）だけ。直前のコメント（`:423-424`）は、そこから GitHub がマージを処理するまでの前進は止められないと書く
  - マージ（`:427-434`）は `gh pr merge --merge --match-head-commit <head>`。`--match-head-commit` が固定するのは head だけ
  - マージの後の確認（`:435-439`）は state・`mergedAt`・head だけで、その後に closing Issue を閉じて（`:440-449`）`no_fix_needed` を返す（`:450`）
  - 最初の確認で既にマージ済みの PR（Issue の更新だけを行う再実行・手動マージ）は、マージの前の照合（`:396-434`）を通らず、同じマージの後の確認に進む
  - `Stop`（`:64-78`）は `wait_for` と `base_moved` を持ち、`finalize` がそのまま結果に写す（`:451-456`）
- 再現（このセッション、偽の gh だけ。`/workspaces/reso-world/tmp/agents/issue-206.zn83426u/repro-before.log`）: Issue の手順（`gh pr merge` の処理の直前に偽のサーバーの base を `NEW_BASE` に進める）で、`--spec-commit` の有無の両方が `no_fix_needed`・`merged: true`・`issues: [901]` を返す。マージの最初の親は `NEW_BASE`、検証した base は `BASE`
- GitHub の応答（読み取りだけ。PR #226）
  - `gh pr view 226 --repo usaturn/create-reso-world --json mergeCommit` は `{"mergeCommit":{"oid":"49aa9506…"}}`
  - `gh api repos/usaturn/create-reso-world/git/commits/49aa9506…` のキーは `author`・`committer`・`html_url`・`message`・`node_id`・`parents`・`sha`・`tree`・`url`・`verification`。`parents` は `[{"sha":"b741085…"}, {"sha":"09a4b8b…"}]` で、最初の親はマージしたときの main の先端、2 つ目は PR の head
- 状況コメント
  - 投稿 helper（`upsert_pr_comment.py:304-315`）は、PR が open で、head が記録の `reviewed_head` と同じときだけ記録付きで投稿する。マージの後は記録付きの状況コメントを足せず、直せない
  - `.agents/review-records.md:495`（7.1）: 状況コメントは人が編集しない。補足は別のコメントに書く
  - `references/execution.md:170`（3.4 節の手順 3）: 状況コメントを直せないときの補足は、planner が `gh pr comment <PR> --repo <repo> --body-file <file>` で投稿する。1 行目は `補足（review-fix-planning、<MODEL_NAME>）:` で、判断の記録・マーカー（`<!--`）を含めない
  - pr-review-fix-loop の SKILL.md:24: loop 自身は PR にコメントしない。PR への書き込みは、review-fix-planning の状況コメント（補足を含む）と最終化だけ
- 手順書
  - `references/execution.md` 3.5 節（`:177-180`）は、この競合を既知の制限とし、merge commit の最初の親を比べて補足に書く方法を示すが、helper の完了条件ではない
  - review-fix-planning の SKILL.md:263（結論 2 の手順 7）は `wait_for` と `base_moved` の再実行を計画の中で行い、ほかの `stopped` を結論 3 にする。SKILL.md:267 はこの競合を 3.5 節の既知の制限として参照する
  - pr-review-fix-loop の SKILL.md:68 は、`wait_for`・`base_moved` の再実行を計画の中で行うと書く。SKILL.md:109（「最終化の停止」）は、ループが終わった後に `--round-dir` の記録・本文・検証の記録で finalize.py を再実行する経路を書く。SKILL.md:128 は、関連 Issue を finalize の結果の state で報告すると書く
  - issue-to-pr の SKILL.md:223 は、ループの結果が `stopped`（`ended_by: outcome`）なら `stop_reason` を書き、`merged: true` ならマージ済みと分けて書く
- ループ（`.agents/skills/pr-review-fix-loop/scripts/loop.py`）
  - `cycle_end`（`:1494-1541`）は、`no_fix_needed` の記録に finalize の結果を受け取り、PR の実際のマージ状態を `merged` に保存し、finalize が `stopped` なら finalize の `stop_reason` で run を `stopped` にする。結果の内容は `planning.finalize.result` にそのまま残る（`references/records.md` 6 章）
  - finalize がマージ済み（`true`）を返して止まり、PR の head がサイクルの HEAD と同じ組み合わせのテストは無い（`test_loop_state.py:437-472` は `false`・`null`・別の head の `true`）
- テスト
  - `test_finalize.py` の偽の gh（`:102-210`）は、マージで state を MERGED にし、base の先端を `MERGE_COMMIT` に進める。merge commit とその親は持たない。テストは 152 件
  - `test_loop_state.py` は 69 件
- #138（open）: 同じリポジトリの Issue に `Closes` を付けると、マージで GitHub が Issue を閉じる。finalize の照合とは関係なく起きる

## 設計

### 1. マージの後に merge commit の最初の親を照合する（`finalize.py`）

- `FIELDS` に `mergeCommit` を足す
- `check_merge_parent(runner, repo, view, verified)` を足す。PR の応答の `mergeCommit.oid` を読み、`gh api repos/<repo>/git/commits/<oid>` の `parents` の先頭の `sha` を、検証の記録の `base`（`verified`）と比べる（D-206-2・D-206-3）
  - `oid`・応答の `sha`・最初の親が完全な SHA で、応答の `sha` が `oid` と同じとき、最初の親を読めたとする。どれかが欠ける・形が違う・`gh` が失敗したときは読めない（D-206-6）
  - 読めない、または最初の親が `verified` と違えば `Stop` を上げる。`Stop` は `merge_parent = {"verified": <検証の記録の base>, "merge_commit": <oid か null>, "first_parent": <最初の親か null>}` を持ち、`finalize` が結果に写す（D-206-4）
- 呼ぶのは、マージの後の確認（state・`mergedAt`・head の照合）の直後、closing Issue の更新の前。この run がマージした場合も、最初から既にマージ済みだった場合（Issue の更新だけを行う再実行・手動マージ）も同じに照合する。後者は base の先端ではなく、過去の merge commit を照合する
- 止まったときの結果は `outcome: stopped`・`merged: true`・`issues: []`・`merge_parent`。関連 Issue は読まず、閉じない。`stop_reason` は `external:` で始まり、不一致なら 3 つの SHA の先頭 12 文字と、merge commit のツリーで検証し直して記録を作り直してから再実行することを書く。読めないときは、照合できないことと、読めるようになってから同じ記録で再実行し、違っていれば merge commit のツリーで再検証することを書く
- 一致したときの結果は今までと同じ（新しいキーを足さない）
- 再実行: 同じ記録では同じ停止になる（merge commit は変わらない）。検証の記録を、`base` を merge commit の最初の親、`commands` を merge commit のツリーで実行した検証にして作り直せば、同じ照合が通り、投稿もマージもせずに関連 Issue を更新して `no_fix_needed` を返す（D-206-5）
- モジュールの docstring と、マージの直前のコメントを、マージの後の照合に合わせて直す

### 2. 手順書（`references/execution.md`）

- 3.3 節: base の項の「マージ済みの PR では base の先端を確かめない」に、代わりに過去の merge commit の最初の親を照合することを足す。新しい項で、マージの後の照合（読むもの・比べるもの・止まったときの結果）を書く
- 3.4 節: `merge_parent` の項を足す
  - `merge_parent` があれば、マージの後の照合で止まった。PR はマージ済み（`merged: true`）で、helper は関連 Issue を更新していない。どちらの場合も、補足のコメント（3.4 節の手順 3 と同じ形。サイクル、`merge_parent` の 3 つの値（読めなかった値は読めなかったこと）、関連 Issue を更新していないこと、次の手順）を投稿して結論 3 にする（D-206-7・D-206-9）。finalize に渡した記録・本文・検証の記録とセッションディレクトリは消さずに残し、完全パスを報告する
  - `first_parent` が null（読めない）: 照合できていない。原因が解消してから、同じ記録・本文・検証の記録で再実行すると読み直して照合する
  - `first_parent` が `verified` と違う: base に検証していない組み合わせが入った。待っても、同じ記録で再実行しても解消しない。merge commit のツリーで検証し直すまで関連 Issue を更新しない
  - 完了させるときの手順（利用者の指示で行う）: merge commit を取得し、`mktemp` の隔離 worktree で checkout して結論 2 の手順 1 と同じ検証を通す → 検証の記録を `head` はそのまま、`base` を `first_parent`、`commands` をその実行にして作り直す（検証し直さずに `base` だけを書き換えない） → 補足のコメントに、merge commit のツリーで実行したコマンドと終了コードを書く → 同じ判断の記録・本文で finalize.py を再実行する。検証が失敗したら再実行せず（関連 Issue を閉じない）、補足のコメントに失敗を書いて報告する
- 3.5 節: 競合そのものは今も防げない（base を固定できず、セッションの間の排他も無い）が、helper がマージの後に見つけて止まること、止まった時点で base には検証していない組み合わせが入っていること、`Closes` による自動の close（#138）は照合と関係なく起きること、を書く

### 3. review-fix-planning の SKILL.md

- 結論 2 の手順 7 に、`merge_parent` 付きの `stopped` の扱いを足す。マージ済みで、helper は関連 Issue を更新していない。どちらの場合も、execution.md 3.4 節のとおり補足のコメントを投稿して結論 3 にする。読めないだけなら、原因が解消してから同じ入力で再実行すると読み直す。最初の親が違えば、再検証せずに止まる（merge commit のツリーでの再検証と再実行は、利用者の指示で別に行う）
- 「base が進んだときのやり直し」の最後の文（3.5 節の既知の制限の参照）を、helper がマージの後に見つけて止まることに直す。この停止はやり直しの回数に数えない

### 4. pr-review-fix-loop の SKILL.md

- 「守ること」の PR への書き込みの括弧書き（SKILL.md:24）に、マージの後の照合で止まったときの補足を足す
- 「サイクル」の 3（計画）: マージの後の照合の停止（`merge_parent`）は、計画の中で再検証せずに `cycle-end` に渡す（run は `stopped`・`merged: true` で終わる）
- 「止まったとき」の「最終化の停止」: `merge_parent` で止まったときの扱いを足す。PR はマージ済みで、関連 Issue は finalize が更新していない。`first_parent` が null なら同じ記録で再実行する。違っていればループの中では再検証しない。完了させるときは、利用者の指示で、execution.md 3.4 節のとおり merge commit のツリーで検証し、`--round-dir` の検証の記録を作り直してから finalize.py を再実行する。そのため `--round-dir` を消さずに残す
- 「最終報告」: finalize の結果に `merge_parent` があれば、3 つの SHA と、関連 Issue を finalize が更新していないこと（`Closes` による GitHub の自動の close は別。#138）、再検証の手順（execution.md 3.4 節）を書く

### 5. テスト

- `test_finalize.py` の偽の gh に、merge commit とその親を持たせる。マージの処理で merge commit の親を「そのときの base の先端・PR の head」にし、PR の応答に `mergeCommit` を入れる。`gh api repos/<repo>/git/commits/<sha>` に答える。最初から MERGED の PR は、最初の親が `BASE` の merge commit を持つ。マージの処理の直前に base を進める設定と、commit の応答の差し替え・失敗の設定を足す
- 足すテスト
  - Issue の再現と対照: `--spec-commit` の有無 × base を進める・進めない。進めたら `stopped`・`merged: true`・`issues: []`・`merge_parent`（`BASE`・`MERGE_COMMIT`・`NEW_BASE`）で、Issue を閉じない。進めなければ `no_fix_needed` で `merge_parent` が無い
  - 操作の順: 不一致で止まる → 同じ記録で再実行しても止まったまま（書き込みなし）→ `base` を `NEW_BASE` にした検証の記録で再実行すると、投稿もマージもせずに Issue を閉じて `no_fix_needed`
  - 読めない: `mergeCommit` が無い・SHA でない、commit の取得の失敗、応答の `sha` の違い、`parents` が空・形の違い。どれも `stopped`・`merged: true`・`issues: []` で、読めた値だけが `merge_parent` に入る。取得の失敗は、読めるようになってから同じ記録で再実行すると完了する
  - 既存の `test_rerun_after_the_merge_does_not_compare_the_moved_base` に、過去の merge commit を照合することを足す
- `test_loop_state.py` の `test_finalize_stopped_keeps_the_real_merge` に、finalize がマージ済みを返して止まり、PR の head がサイクルの HEAD と同じ組み合わせ（新しい停止の形。`merge_parent` 付き）を足し、run が `stopped`・`merged: true` で終わり、`planning.finalize.result` に `merge_parent` が残ることを確かめる。偽の結果ファイルの helper（`conftest.py` の `finalize_result`）に `merge_parent` を渡せるようにする

### 6. 変えないもの

- マージの前の照合（`check_base`・`base_moved`・`wait_for`）と、その順序
- 検証の記録の形（`head`・`base`・`commands`）
- `loop.py`（`cycle-end` は finalize の結果をそのまま残し、PR の実際のマージ状態を保存する）
- 投稿 helper（`upsert_pr_comment.py`）と判断の記録の形
- issue-to-pr の SKILL.md と pr-review-fix-loop の `references/records.md`（ループの最終報告と `planning.finalize.result` が新しい結果を含む）
- `Closes` の扱い（#138）

## 受け入れ条件

1. 最後の照合の後、マージの処理までに base が進むと、`--spec-commit` の有無の両方で、`stopped`・`merged: true`・`issues: []` と `merge_parent`（検証した base・merge commit・実際の最初の親）を返し、関連 Issue を更新しない（Issue の受け入れ条件 1）
2. base が動かない対照は今までどおり `no_fix_needed`。既にマージ済みの PR の再実行（Issue の更新の再開）は、過去の merge commit の最初の親を照合して完了する（Issue の受け入れ条件 2）
3. 不一致で止まった後、同じ記録の再実行は止まったまま。merge commit のツリーで検証し直した記録（`base` が実際の最初の親）で再実行すると、投稿もマージもせずに関連 Issue を更新して完了する。merge commit を読めないときも、`merged: true` の `stopped` で関連 Issue を更新しない（Issue の受け入れ条件 3）
4. PR 修正ループは新しい停止を `stopped`・`merged: true` で終え、`planning.finalize.result` に `merge_parent` を残す。手順書（execution.md、review-fix-planning・pr-review-fix-loop の SKILL.md）が、新しい結果と、補足のコメント・再検証・再実行の手順を書く（Issue の受け入れ条件 4）
5. テストは偽の gh で操作の順と状態を実行して確かめる。文書の文言を照合するテストと GitHub Actions は足さない。README の「テスト」の入口（ワールドの行を除く）で、この変更による失敗が無い（Issue の受け入れ条件 5）

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-206-1 マージの後に merge commit の最初の親を照合し、完了は再検証した記録での再実行で行う（利用者の決定）**
  - 選択: マージの後の確認で `mergeCommit` とその最初の親を読み、検証の記録の `base` と照合する。一致しない・読めないときは、関連 Issue を更新せず、`stopped`・`merged: true` を返し、検証した base・merge commit・実際の最初の親を結果と状況コメントに残す。`stop_reason` は merge commit での再検証が要ると分かる文にする。完了は、merge commit のツリーで同じ検証をした記録で finalize.py を再実行する経路で行う。ループの中での自動の再検証と、排他制御は入れない。`Closes` による自動の close は #138 の範囲として扱わない
  - 別案: Issue の「対応案」の、排他制御で競合そのものを防ぐ案、不一致のときに再検証の手順へ自動で進める案
  - 理由: 利用者の決定
  - 委任指示: 利用者の決定。`/workspaces/reso-world/tmp/agents/commander-219-220-221-206-212.0smdd1hj/decisions/issue-206.md` の全文を次に引用する

    ```text
    ### #206
    - マージ後の確認で、`mergeCommit` とその最初の親を取得し、検証した base と照合する
    - 一致しない、または merge commit を読めないときは、関連 Issue を更新せず、`outcome: stopped`・`merged: true` を返す。検証した base・merge commit・実際の最初の親を、結果と状況コメントに残す。`stop_reason` は、merge commit での再検証が要ると分かる文にする
    - 完了は、merge commit のツリーで同じ検証をした記録を渡して `finalize.py` を再実行する経路で行う（受け入れ条件 3）。ループの中での自動の再検証と、排他制御は入れない
    - `Closes` による自動の close は #138 の範囲なので扱わない
    ```

- **D-206-2 merge commit は `gh pr view --json mergeCommit`、最初の親は `gh api repos/<repo>/git/commits/<oid>` で読む**
  - 選択: PR の応答（`FIELDS`）に `mergeCommit` を足して `oid` を読み、Git の commit の API の `parents` の先頭を最初の親とする。応答の `sha` が `oid` と同じことも確かめる
  - 別案: (a) `gh api repos/<repo>/commits/<sha>`（変更ファイルの一覧も返す）、(b) `gh api graphql` で `mergeCommit { parents }` を読む、(c) ローカルの checkout に merge commit を fetch して `git rev-parse <merge commit>^1` で読む
  - 理由: Git の commit の API は親と tree だけの小さい応答で、ファイル数に左右されない（(a) は大きなマージで応答が膨らみ、ページ分けもある）。helper は今も `gh api repos/<repo>/branches/…`・`compare/…` を同じ runner で読んでおり、偽の gh でも同じ形で答えられる。(b) は問い合わせの文と応答の形を新しく足すことになる。(c) は helper が今は使っていないローカルの checkout と remote に依存する
- **D-206-3 照合するのは最初の親だけ**
  - 選択: `parents` の先頭が検証の記録の `base` と同じことだけを完了条件にする。2 つ目の親（head）は照合しない
  - 別案: `parents` が `[検証した base, マージした head]` と完全に一致することを求める
  - 理由: 利用者の決定が最初の親の照合を求めている。マージした head は、マージの後の確認が PR の `headRefOid` で既に照合している。完全一致を求めると、手で squash でマージされた PR（親は base の先端 1 つで、ツリーは検証した組み合わせと同じ）まで止める。最初の親が base の先端にならないマージ（2 つ以上の commit の rebase、fast-forward の push）は止まる（安全側。D-206-11）
- **D-206-4 結果には停止のときだけ `merge_parent` を足す**
  - 選択: `merge_parent = {"verified", "merge_commit", "first_parent"}`（読めなかった値は null）を、この照合で止まったときだけ結果に入れる。一致して完了したときは足さない
  - 別案: (a) 完了のときも入れる、(b) 平たいキー（`merge_commit` など）で入れる、(c) 既存の `base_moved` を使う
  - 理由: 既存の `base_moved` と同じく、停止の種類をキーの有無で分けられ、手順書が「`merge_parent` があれば」で分岐を書ける。(a) は完了の結果にも入ると、この分岐が `outcome` との組み合わせになる。完了のときの merge commit は、PR から読み直せる。(b) は 3 つの値の組がばらける。(c) の `base_moved` は「まだマージしていない。新しい先端で検証し直してからマージする」停止で、マージ済みのこの停止とは次の手順が違う
- **D-206-5 再検証の記録は今の形のまま、`base` を実際の最初の親にする**
  - 選択: 再実行に渡す検証の記録は `head`・`base`・`commands` の今の形で、`base` を merge commit の最初の親、`commands` を merge commit のツリーで実行した検証にする。helper の完了条件は、通常のマージでも再実行でも「merge commit の最初の親が、検証の記録の `base` と同じ」の 1 つ
  - 別案: (a) 検証の記録に `merge_commit` を足し、PR の実際の merge commit と照合する、(b) 再検証用の引数（`--reverified-merge` など）を足す
  - 理由: 今の `base` の定義は「検証したツリーが含む base の commit」で、merge commit のツリーは head と最初の親を含むので、そのまま当てはまる。完了条件が 1 つなら、Issue の更新の再開の経路（受け入れ条件 2）も同じ照合で済む。(a)・(b) は入力の形を増やし、マージの前に使われたときの扱いも要る。どの形でも、コマンドを実際にどのツリーで実行したかは helper から確かめられない（今の検証の記録と同じ）ので、増やした分の照合は検証の根拠を強めない
- **D-206-6 読めないときも同じ停止にし、同じ記録の再実行で読み直す**
  - 選択: `mergeCommit` が無い・SHA でない、commit の取得の失敗、応答の `sha` の違い、`parents` が空・形の違いは、どれも「読めない」とし、`merged: true` の `stopped` に読めた値だけを入れた `merge_parent` を付ける。待てば進む停止（`wait_for`）にはしない
  - 別案: (a) 取得の失敗を、ほかの `gh` の失敗と同じ `external: <step> の取得・検査・書込みに失敗した`（`merge_parent` なし）にする、(b) `wait_for` を付ける
  - 理由: 利用者の決定が、読めないときも照合した値を残すことを求めている。(a) では何が欠けたかが結果に残らない。(b) の `wait_for` は、待てば解消すると分かっている状態（CI の実行中・mergeable の計算中・push の反映前）だけに使っている。読めない原因は一時的な障害とは限らない
- **D-206-7 状況コメントには planner が補足で残す（利用者の決定の解釈）**
  - 選択: 「結果と状況コメントに残す」を、helper が結果に `merge_parent` を入れ、planner が review-fix-planning の補足のコメント（`gh pr comment`、1 行目 `補足（review-fix-planning、<MODEL_NAME>）:`）に `merge_parent` の 3 つの値を書く、と解する。補足は、一致しないときも読めないときも書く（読めなかった値は読めなかったと書く）。手順は execution.md 3.4 節に書く。最初の版は補足を一致しないときだけにしていたが、最後のブランチ全体のレビュー（Minor 1）で利用者の決定の文言と食い違うと分かったので、両方で書くように直した
  - 別案: (a) helper が止まったときに補足のコメントを自動で投稿する、(b) 記録付きの状況コメントを書き換える
  - 理由: マージの後は記録付きの状況コメントを足せず、直せない（投稿 helper が拒否する。review-records 7.1 は状況コメントの編集を禁じ、補足は別のコメントに書くとする）ので (b) は取れない。このリポジトリでは、補足（push の後に base が進んだときのもの）も review-fix-planning の状況コメントに含めて扱い（pr-review-fix-loop の SKILL.md:24）、planner が書いている。(a) は、止まる経路に新しい GitHub への書き込みを足し、再実行のたびの重複と投稿の失敗の扱いが要る。再検証の結果（実行したコマンドと終了コード）は helper が知らないので、どのみち planner が補足を書く。書き手を planner にそろえる
- **D-206-8 ループの `loop.py` は変えず、SKILL.md で扱いを書く**
  - 選択: `cycle-end` は今のまま、finalize の `stopped` で run を `stopped` にし、PR の実際のマージ状態（`true`）を保存し、finalize の結果（`merge_parent` を含む）を `planning.finalize.result` に残す。SKILL.md に、計画の中で再検証しないこと、`--round-dir` を残すこと、完了させるときの再実行の経路、最終報告に書くことを足す。この組み合わせのテストを足す
  - 別案: (a) `loop.py` が `merge_parent` を見て、再検証用の次の手順（`next`）を返す、(b) ループが merge commit のツリーで自動で再検証する
  - 理由: (b) は利用者の決定（ループの中での自動の再検証は入れない）に反する。(a) は、まれな停止のためにループの状態の遷移を増やす。今の `cycle-end` で必要な事実（停止・マージ済み・SHA）は失われない
- **D-206-9 review-fix-planning でも、不一致は結論 3 にする**
  - 選択: ループの中か外かに関わらず、最初の親が違う停止は、補足のコメントを投稿して結論 3 にする。merge commit のツリーでの再検証と finalize.py の再実行は、利用者の指示で別に行う（execution.md 3.4 節の手順）
  - 別案: ループの外の review-fix-planning は、`base_moved` と同じく計画の中で再検証して再実行する
  - 理由: マージは済んでいて、再検証しても何も防げない。再検証が失敗すれば base が壊れているので、取り消し・修正の判断は利用者が行う。呼び出し元で手順を分けると、ループの中で誤って再検証する余地が残る
- **D-206-10 テストは偽の gh の操作の順で書く**
  - 選択: 設計 5 のとおり。偽の gh に merge commit とその親を持たせ、Issue の再現と対照、不一致 → 同じ記録の再実行 → 再検証した記録の再実行の順、読めない場合、ループの記録を確かめる。文書の変更は、文言を照合するテストを作らず、`git diff` の確認と最後のブランチ全体のレビューで確かめる（AGENTS.md「テストの採用基準」）
  - 別案: `check_merge_parent` を単体で直接テストする
  - 理由: Issue の受け入れ条件 5 が、偽の gh で操作の順と状態を実行して確かめることを求めている。マージの後に止まり、同じ記録では完了せず、再検証した記録で Issue の更新だけが進む順序は、`finalize` の実経路でないと確かめられない
- **D-206-11 既知の制限**
  - 最後の照合から GitHub がマージを処理するまでの base の前進は、今も防げない。helper はマージの後に見つけて止まるが、その時点で base には検証していない組み合わせが入っている（排他制御は利用者の決定で入れない）
  - PR 本文の `Closes` による GitHub の自動の close は、照合と関係なくマージの時に起きる（#138）。止まっても関連 Issue が既に閉じていることがあり、helper は開き直さない
  - helper は、再検証の記録のコマンドを実際に merge commit のツリーで実行したかを確かめられない（今の検証の記録と同じく、司令塔が実際の実行を書く）
  - 2 つ以上の commit を rebase でマージした PR や、fast-forward の push でマージされた PR は、最初の親が PR の commit になり、base の先端と違うので止まる（安全側）。そのときの再検証の記録の `base` は、PR の commit になる
