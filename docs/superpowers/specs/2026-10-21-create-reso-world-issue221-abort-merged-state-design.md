# Issue #221: finalize のマージの後にループを abort しても、マージ済みの事実を失わない

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/221（親 Issue・ボード・先行 Issue・コメントは無い。関連: #207、PR #215）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-21-create-reso-world-issue221-abort-merged-state.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-221-abort-merged-state`（branch `fix/issue-221-abort-merged-state`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-21（JST）、利用者が次のとおり指示した

  ```text
  /issue-to-pr https://github.com/usaturn/create-reso-world/issues/221 --merge --assign implement=self 利用者の決定を /workspaces/reso-world/tmp/agents/commander-219-220-221-206-212.0smdd1hj/decisions/issue-221.md に置いた。読んで Spec の決定記録に引用せよ
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #221`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）を回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う
  - 方針（D-221-1）は利用者の決定に従う。ほかの判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- ループのオプション（`loop.py check-options` の出力）: `max_cycles = 3`（既定の適用）、`assign = {"implement": ["self"]}`（利用者の指定 `--assign implement=self`）、`template = .devcontainer/agent-runner.toml`（既定の適用）、`config = null`。割り当ては、レビュー（`inspect`）が `devin-swe`・`pi-deepseek`・`claude-opus`・`pi-gpt`（個人設定 `~/.config/agent-runner/config.toml` の適用）、修正（`implement`）が `self`（利用者の指定）、自己レビュー（`self-review`）・修正の確認（`fix-check`）が `self`（雛形の既定の適用）。いずれも `fallback` なし
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の `workflows.issue` の既定の適用。個人設定に `workflows.issue` は無い。利用者の指定ではない）
- 基準: `origin/main` の `b741085`

## 意図

PR 修正ループの中で `finalize.py` が PR をマージした後に `cycle-end` が止まり（GitHub の読み取りの一時的な失敗など）、司令塔が `finish --abort` で run を終えると、run の結果は `merged: false` になる。issue-to-pr の `--merge` の最終報告も、ループのエラーのときは「マージ: していない」と決めている。マージは取り消せないので、マージ済みの PR を未マージと報告すると、利用者や後続の作業（司令塔の次の Issue など）が実際の状態と違う前提で動く。#207（PR #215）は finalize と `cycle-end` の経路を直したが、`finish --abort` は PR を読まずに `false` を書くので、この経路が残っている。

利用者の決定（D-221-1）のとおり、`finish --abort` が PR の実際の状態と、司令塔が渡した最後の finalize の結果を読み、`merged` を finalize の `merged`（#207）と同じ意味の 3 値（true・false・null）にする。読む側（issue-to-pr の表、pr-review-fix-loop の `references/records.md` と SKILL.md、`loop.py`、テスト）を 3 値に合わせ、`cycle-end` が finalize の後に止まったときに finalize の結果の `merged` を確かめる段を SKILL.md に足す。

## 確認した事実（2026-10-21 JST、`b741085`）

- `finish`（`.agents/skills/pr-review-fix-loop/scripts/loop.py:2021-2060`）は、`--abort` のとき PR を読まずに `RunResult(outcome="stopped", ended_by="abort", stop_reason=abort, merged=False, ...)` を書く（`loop.py:2032-2034`）。`RunResult.merged` は `bool`（`loop.py:178-183`）
- `cycle_end`（`loop.py:1430-1583`）は、最初に `_read_records` で認証済みの login と PR のコメントを読み（`loop.py:1448`。失敗は終了コード 5 `github`）、記録を照合した後に `github.pull` で PR を読んで `merged = pull.merged` を保存する（`loop.py:1491-1496`）。finalize の結果が `true` なのに PR が未マージ、または `no_fix_needed` で head が違えば終了コード 4 `merge_mismatch`（`loop.py:1524-1535`）。失敗したときはサイクルの記録を書き換えない（`records.md` 5 章）
- finalize の結果ファイルは review-fix-planning のセッションディレクトリにあり（`execution.md` 3.2 節の `--result-file "$SESSION/finalize-result.json"`）、loop が場所を知るのは `cycle-end --finalize-result` で渡されたときだけである。`cycle-end` が途中で止まると、その場所はどの記録にも残らない
- `_read_finalize`（`loop.py:1384-1401`）は finalize の結果の形（`outcome` が `no_fix_needed`・`stopped`、`merged` が真偽値か null、`issues` がリスト、`spec_commit` があれば SHA）を確かめ、違えば終了コード 2 `arguments`
- `GitHub.pull`（`loop.py:544-568`）は `gh api repos/<repo>/pulls/<N>` の `state`・`merged`・`head.sha` を読む。gh の失敗・JSON でない応答・形の違い・依頼と違う PR は終了コード 5 `github` の `LoopError`。gh を起動できなければ `OSError` がそのまま上がる
- finalize の `merged`（`.agents/skills/review-fix-planning/scripts/finalize.py:247-257・358-463`、`references/execution.md` 3.4 節）: `true` はマージ済みを観測した、`false` は未マージを観測し、その後にマージを依頼していない、`null` は確かめていない。一度観測した `true` は後の応答で戻さない
- 読む側
  - `references/records.md:55` は `result` の形だけを書き、`merged` の値の範囲を書いていない。`records.md:113` は「`finish --abort` が書く `result.merged` は PR を読まずに `false` なので、マージ状態を表さない」と注記している（PR #215）
  - `.agents/skills/issue-to-pr/SKILL.md:219-224` の表は、`stopped` の行が「結果のとおり」、ループのエラーの行が「していない」
  - pr-review-fix-loop の SKILL.md は、abort を「終わり方」（`SKILL.md:97`）に、最終報告の「マージしたか」を `SKILL.md:124` に書いている。finalize の後に `cycle-end` が止まったときの手順は無い（`SKILL.md:84` の 5 `github` は「直せなければ利用者に報告して止まる」だけ）
  - `loop.py` の中で run の `merged` を使うのは `RunResult` と、それを出力する `finish`・`status`・`recover` だけ。リポジトリの中に run.json の `merged` を読むコードはほかに無い
- 偽の gh（`.agents/skills/pr-review-fix-loop/tests/conftest.py:166-239`）は、`login_status` で `gh api user` を失敗させられるが、PR の読み取りは常に成功する
- テストで `finish(..., abort=...)` を呼ぶ箇所は 9 か所（`test_loop_state.py` 3 か所、`test_loop_review.py` 6 か所）で、どれも `github` を渡していない（今の `finish` は GitHub を読まないため）
- 基準の検証（`/workspaces/reso-world/tmp/agents/issue-221.439bd74f/baseline/`）: `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` は終了コード 0。pytest の入口の結果は Plan に書く

## 設計

### 1. `finish --abort` が観測したマージ状態を保存する（`loop.py`）

- `RunResult.merged` を `bool | None` にする。`cycle-end` が保存する値は今までどおり真偽値で、null になるのは `finish --abort` だけである
- `finish` に `--finalize-result <file>` を足す（`--abort` と一緒のときだけ。D-221-2）。関数は `finish(run_dir, *, abort=None, finalize_result=None, github=None)` にする
- `--abort` のとき、形の検査と「結果が決まっていない」の検査の後に、次の順で `merged` を決める（D-221-4）
  1. `--finalize-result` があれば `_read_finalize` で読む（cycle-end と同じ検査。誤りは終了コード 2 で、run を変えない）
  2. `GitHub.pull` で PR を読む。`LoopError`・`OSError` は「読めない」として扱い、abort は止めない
  3. PR を読めたら、PR の `merged`。ただし finalize の結果が `true` で PR が未マージなら null（食い違い）
  4. 読めなければ、finalize の結果の `merged`（true・false・null）。渡されていなければ null
- 3 の食い違いと 4 のときは、決めた理由（読み取りの失敗の理由、使った値）を run の `notes` に `<時刻> finish --abort: …` の形で残す（D-221-7）。PR の状態だけで決まったときは残さない
- `--finalize-result` を `--abort` なしで渡したら、終了コード 2（`arguments`）で止め、run を変えない
- 決めた `merged` を `RunResult` に入れた後の処理（資源の監査、`held`、ロックの解放）は今までどおり。`held` で止まっても `result` は保存され、`recover` の出力にも同じ値が出る
- `cycle-end`・`cycle-begin`・`review`・`recover`・`status`・`_next_step` の動きは変えない

### 2. SKILL.md（pr-review-fix-loop）

- 「止まったとき」に「finalize の後の `cycle-end` の停止」を足す（D-221-5）: finalize.py を実行した後に `cycle-end` が止まったら（5 `github`、4 `merge_mismatch` など）、やり直すか `finish --abort` で終えるかを決める前に、渡した結果ファイルの `merged` を確かめる。`true` は取り消せないマージの観測なので、PR に commit を足さず、マージ済みとして扱う。abort するときは同じファイルを `--finalize-result` で渡す。`null` は未確認で、未マージと報告しない
- 「終わり方」の abort の項に、このサイクルで finalize.py を実行していたら最後の結果ファイルを `--finalize-result` で渡すことと、`merged` の決め方を足す
- 「最終報告」の「マージしたか」を 3 値にする（`null` は未確認と書き、PR の状態を読み直す）

### 3. `references/records.md`

- 3 章の `result` の行に、`merged` が true・false・null で、null は `finish --abort` だけが書く未確認であることを足す。`notes` の行に、`finish --abort` が `merged` を PR の状態だけで決められなかった理由を足す
- 6 章の注記（`records.md:113` の「PR を読まずに `false`」）を、`finish --abort` の `merged` の決め方（設計 1）に置き換える

### 4. issue-to-pr の 5 章の表（D-221-6）

- `stopped` の行を `stopped`（`ended_by: outcome`）とし、`finish --abort` で終えた run（`ended_by: abort`）はループのエラーの行で扱うと分かるようにする
- ループのエラーの行の「マージ」を「PR の状態を読み直して書く。読めなければ未確認（`finish --abort` の結果の `merged` が `true` なら、マージ済みと書く）」にする

### 5. テスト（`.agents/skills/pr-review-fix-loop/tests/`）

- 偽の gh（`conftest.py`）に `pull_status` を足し、0 以外なら PR の読み取り（`gh api repos/<repo>/pulls/<N>`）を失敗させる
- `test_loop_state.py` に足す
  - Issue の再現の手順: `no_fix_needed` の記録の投稿、マージ、finalize の結果（`merged: true`）、login の失敗で `cycle-end` が終了コード 5 `github` で止まる → `finish --abort --finalize-result`。PR を読める・読めないの両方で、`finish` の結果と run.json の `merged` が `true`
  - `merged` の決め方の組み合わせ（PR のマージ状態・読めるか・finalize の結果の有無と値）。PR を読めず finalize の結果も無い・null なら null で、`false` にしない。食い違いは null
  - 引数の誤り: `--finalize-result` を `--abort` なしで渡す、形の違う結果ファイルを渡す → 終了コード 2 で、run の `result` は null のまま、ロックも残る
  - CLI の配線: `loop.main(["finish", "--run", …, "--abort", …, "--finalize-result", …])` が終了コード 0 で、出力の `merged` が `true`
- 既存の `finish(..., abort=...)` のうち PR を読むところまで進む呼び出しには `github=env.github` を渡す（偽の gh を使い、実際の GitHub を読ませない）。マージしていない run の abort が `merged: false` のままであることを、既存の `test_abort_needs_a_classified_reason` で確かめる

### 6. 変えないもの

- `cycle-end` の照合（`merge_mismatch`・`pushed_head_mismatch`・`record_*`）と、`cycle-end` が保存する `merged`（PR の実際の状態）
- `finalize.py`・review-fix-planning の手順と記録
- 既存の run.json（`merged` が真偽値）は今までどおり読める

## 受け入れ条件

1. finalize がマージした後にループが `cycle-end` のエラーで止まり、`finish --abort` で終えても、run の結果の `merged` は `true` になる（PR を読めるときも、読めずに finalize の結果を渡したときも）。issue-to-pr の最終報告の手順も、マージ済みの事実を失わない（Issue の受け入れ条件 1）
2. PR の状態を読めず、finalize が観測した状態も無い（渡されていない・`null`）ときは、`merged` を `null`（未確認）にし、`false` にしない。報告の手順も未マージと書かない（Issue の受け入れ条件 2）
3. マージしていない run の abort（PR を読めて open）は今までどおり `merged: false`。正常な `finish` と `cycle-end` の既存の照合は変わらない（Issue の受け入れ条件 3。既存のテストが通る）
4. テストは偽の gh とローカルの Git の fixture で行う（Issue の受け入れ条件 4）
5. 読む側（`records.md`、pr-review-fix-loop の SKILL.md、issue-to-pr の表）が 3 値に合っている。README の「テスト」の入口（ワールドの行を除く）で、この変更による失敗が無い

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-221-1 `finish --abort` が PR の状態と finalize の結果を読み、`merged` を 3 値にする（利用者の決定）**
  - 選択: `finish --abort` が PR の状態と、あれば最後の finalize の結果を読み、`merged` を true・false にする。どちらも読めなければ null（未確認）。意味は #207 の finalize の `merged` と同じ。読む側（issue-to-pr の表、`records.md`、`loop.py`、テスト）を 3 値に合わせ、issue-to-pr の表のループのエラーの行は「マージ: PR の状態を読み直して書く。読めなければ未確認」にする。`cycle-end` が finalize の後に止まったときに finalize の結果の `merged` を確かめる段を SKILL.md に足す
  - 別案: Issue の「対応方針の候補」の、`merged` を真偽値のまま報告する側だけで読み直す形
  - 理由: 利用者の決定
  - 委任指示: 利用者の決定。`/workspaces/reso-world/tmp/agents/commander-219-220-221-206-212.0smdd1hj/decisions/issue-221.md` の全文を次に引用する

    ```text
    ### #221
    - `finish --abort` は、PR の状態（`gh pr view --json state,mergedAt,headRefOid`）と、あれば最後の `finalize-result.json` を読み、`merged` を true / false にする。どちらも読めなければ null（未確認）にする。#207 で 3 値にした finalize の `merged` と同じ意味にする
    - run の `merged` を読む側（issue-to-pr の 5 章の表、pr-review-fix-loop の `references/records.md`、`loop.py` の中の参照、テスト）を 3 値に合わせる。issue-to-pr の表のループのエラーの行は「マージ: PR の状態を読み直して書く。読めなければ未確認」にする
    - `cycle-end` が finalize の後に止まったときは、やり直すか abort する前に `finalize-result.json` の `merged` を確かめる段を、pr-review-fix-loop の SKILL.md に足す
    ```

- **D-221-2 finalize の結果は `finish --abort --finalize-result <file>` で渡す**
  - 選択: `finish` に `--finalize-result` を足し、`--abort` と一緒のときだけ受け付ける。司令塔は、このサイクルで実行した finalize.py の最後の結果ファイル（`cycle-end` に渡したものと同じ）を渡す
  - 別案: (a) `cycle-end` が GitHub を読む前に、渡された結果ファイルの場所をサイクルの記録に保存し、`finish` が拾う、(b) `finish` が review-fix-planning のセッションディレクトリを探す
  - 理由: (a) は、失敗した `cycle-end` が記録を書き換えることになり、「失敗しても保存した記録を書き換えない」（`records.md` 5 章）と「状態は変わらない」（SKILL.md の `record_missing`）を崩す。やり直しの `cycle-end` で別の結果ファイルを渡したときの扱いも増える。(b) は loop がセッションディレクトリの場所を知らず、推測になる。明示の引数は `cycle-end --finalize-result` と同じ形で、D-221-5 の段で司令塔が確かめたファイルをそのまま渡せる
- **D-221-3 PR の状態は loop の既存の `GitHub.pull` で読む**
  - 選択: `gh api repos/<repo>/pulls/<N>` の `state`・`merged`・`head.sha`（`GitHub.pull`）を使う。司令塔が報告のために読み直すときは、文書のとおり `gh pr view <PR> --repo <repo> --json state,mergedAt,headRefOid` を使う（`execution.md` 3.4 節と同じ）
  - 別案: 決定の括弧書きのとおり、loop に `gh pr view --json state,mergedAt,headRefOid` の読み取りを足す
  - 理由: 決定の括弧書きは、読む情報（状態・マージ済みか・head）を示すものと解した。`GitHub.pull` は同じ情報を返し、`cycle-end` が `merged` を保存するときと同じ読み方なので、abort と `cycle-end` の `merged` の根拠がそろう。応答の形の検査（依頼と違う PR を拒否する）も共有でき、偽の gh もこの読み方に対応している。2 つ目の読み方を足すと、同じ PR について形の違う 2 つの応答を照合する箇所が増える
- **D-221-4 `merged` の決め方: PR を読めればその状態、読めなければ finalize の結果、食い違いは null**
  - 選択: 設計 1 の 3・4。PR を読めたら PR の `merged`（finalize の結果が `true` で PR が未マージなら null）。読めなければ finalize の結果の `merged`。どちらも無ければ null
  - 別案: (a) 食い違いは `true`（finalize の `observe_merged` と同じく、観測したマージ済みを戻さない）、(b) 食い違いは `false`（今の PR の読み取りを採る）、(c) 食い違いで abort を拒否する（`cycle-end` の `merge_mismatch` と同じ終了コード 4）、(d) PR を読めないときは finalize の `false` も使わず null にする
  - 理由: 食い違いは、どちらかの読み取りが誤っている状態で、abort の中ではどちらが正しいかを確かめられない。(a) は誤った結果ファイル（別の PR・別の run のもの）でマージ済みと書き、(b) は GitHub の応答の遅れでマージ済みを未マージと書く（この Issue と同じ誤り）。(c) は run を終えられず、ロックが残る。null なら未マージとも書かずに読み直しへ回せる。(d) は、決定の「どちらも読めなければ null」（片方を読めれば true・false にする）に反する。finalize の `false` は「未マージを観測し、その後にマージを依頼していない」で、loop と司令塔は finalize の外でマージしないので、最後の結果を渡す限り abort の時点でも同じ意味を保つ。Issue の受け入れ条件 2（PR の状態を読めないときは未マージとも報告しない）は、abort の時点の読み取りと finalize が観測した状態のどちらも無いときと解し、そのときは null にする
- **D-221-5 finalize の後の `cycle-end` の停止の段は「止まったとき」に置く**
  - 選択: SKILL.md の「止まったとき」に 1 項を足し、「終わり方」の abort の項から `--finalize-result` を案内する
  - 別案: `cycle-end` の拒否の表の 5 `github` の行に書き足す
  - 理由: finalize の後かどうかは、終了コード 5（`github`）でも 4（`merge_mismatch` など）でも起きる（Issue の原因）。表の 1 行に書くと、ほかの終了コードのときに読まれない。止まったときの手順にまとめると、やり直しと abort の両方から同じ段を使える
- **D-221-6 issue-to-pr の表は、決定の文言に、run が観測した `true` を使う補足を足す**
  - 選択: ループのエラーの行の「マージ」を「PR の状態を読み直して書く。読めなければ未確認（`finish --abort` の結果の `merged` が `true` なら、マージ済みと書く）」にする。`stopped` の行は `ended_by: outcome` の run と明記し、abort で終えた run をループのエラーの行で扱う
  - 別案: (a) 決定の文言だけにする、(b) `stopped` の行で abort の run も扱い、「結果のとおり（null は未確認）」にする
  - 理由: (a) は、Issue の場面（GitHub の読み取りの失敗）が報告のときも続くと、run が観測したマージ済みを「未確認」と書き、受け入れ条件 1 の「最終報告がマージ済みの事実を失わない」を満たさない。マージは戻らないので、観測した `true` は読み直せなくても有効である。`false`・`null` は報告の時点で古くなりうるので、決定どおり読めなければ未確認にする。(b) は、abort の原因（ループの `stage`・`reason`・`next`）を書く行と分かれ、同じ run を 2 つの行で読めてしまう
- **D-221-7 PR の状態だけで決められなかった理由を run の `notes` に残す**
  - 選択: PR を読めなかったとき、PR と finalize の結果が食い違ったときだけ、理由（読み取りの失敗の理由、使った値）を `notes` に足す。`finish` の出力の形は変えない
  - 別案: (a) 残さない、(b) `finish` の出力に `warnings` を足す
  - 理由: null や finalize の値を使った根拠が run.json に無いと、後から `merged` を確かめられない。`notes` は `recover` の確認の事実を残している場所で、形を変えずに足せる。司令塔の報告は D-221-6 のとおり PR を読み直すので、出力に足さなくても足りる
- **D-221-8 引数の誤りは止め、PR の読み取りの失敗では止めない**
  - 選択: `--finalize-result` を `--abort` なしで渡したとき、読めない・finalize の結果の形でないファイルを渡したときは、run を変えずに終了コード 2（`arguments`）。PR の読み取りの失敗（gh の失敗・応答の誤り・gh を起動できない）は、読めないとして D-221-4 で決め、abort を続ける
  - 別案: 読めない結果ファイルを、渡されなかったものとして扱う
  - 理由: 渡したファイルを黙って無視すると、マージ済みの事実を失っても気付かない。引数の誤りは run を変えずに止めれば、正しく呼び直せる（`cycle-end` の `--finalize-result` と同じ `_read_finalize` で検査する）。PR の読み取りの失敗で abort できないと、GitHub の障害の間 run を終えられず、ロックが残る
- **D-221-9 テストは偽の gh の実経路で書く**
  - 選択: 設計 5 のとおり。偽の gh に `pull_status` を足し、Issue の再現の手順、`merged` の決め方の組み合わせ、引数の誤り、CLI の配線を確かめる。文書の変更は、文言を照合するテストを作らず、`git diff` の確認と最後のブランチ全体のレビューで確かめる（AGENTS.md「テストの採用基準」）
  - 別案: `finish` の中の判定を単体の関数として直接テストする
  - 理由: Issue の受け入れ条件 4 が偽の gh とローカルの Git の fixture を求めている。`cycle-end` の失敗が記録を変えずに残り、その後の abort で `merged` が決まる順序は、実経路でないと確かめられない
- **D-221-10 既知の制限**
  - `--finalize-result` を渡し忘れ、PR も読めなければ `merged` は null（未確認）になる。未マージとは書かない
  - loop は、渡された finalize の結果ファイルがこの PR・この run のものかを確かめない（`cycle-end` と同じ）。PR を読めれば、食い違いは null になる
  - `cycle-end` のエラーの後に司令塔が `finish --abort` を実行せずに止まったときは、run は `running` のままで、`merged` は保存されない（今までどおり。報告は issue-to-pr の表のとおり PR を読み直す）
  - `finish --abort` は PR を期限なしで読む（loop のほかの GitHub の読み取りと同じ）。応答が返らない障害のときは abort が戻らない。run を保存する前に読むので途中の状態は残らず、障害が直ってからやり直せる（最後のブランチ全体のレビューの Minor 4。持ち越し）
