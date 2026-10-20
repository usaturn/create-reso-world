# Issue #220: DSH の TMPDIR に残るハードリンクを停止後に消し、pytest の fixture で成功した回答を捨てない

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/220（親 Issue・ボード・先行 Issue は無い。コメント 1 件: PR #216 の PR 修正ループでも同じ原因で `dsh-ccd` が 2 サイクルとも却下され、発生源は agent_runner の外のテスト `tests/scripts/test_meshy.py` だった。直すときはテストの場所に依らない形にするのがよい、という指摘）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-21-create-reso-world-issue220-dsh-tmp-hardlinks.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-220-dsh-tmp-hardlinks`（branch `fix/issue-220-dsh-tmp-hardlinks`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-21（JST）、利用者が次のとおり指示した

  ```text
  /issue-to-pr https://github.com/usaturn/create-reso-world/issues/220 --merge --assign implement=self 利用者の決定を /workspaces/reso-world/tmp/agents/commander-219-220-221-206-212.0smdd1hj/decisions/issue-220.md に置いた。読んで Spec の決定記録に引用せよ
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #220`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）を回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う
  - 方針（D-220-1）は利用者の決定に従う。ほかの判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- ループのオプション（`loop.py check-options` の出力）: `max_cycles = 3`（既定の適用）、`assign = {"implement": ["self"]}`（利用者の指定 `--assign implement=self`）、`template = .devcontainer/agent-runner.toml`（既定の適用）、`config = null`。割り当ては、レビュー（`inspect`）が `devin-swe`・`pi-deepseek`・`claude-opus`・`pi-gpt`（個人設定 `~/.config/agent-runner/config.toml` の適用）、修正（`implement`）が `self`（利用者の指定）、自己レビュー（`self-review`）・修正の確認（`fix-check`）が `self`（雛形の既定の適用）。いずれも `fallback` なし
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の `workflows.issue` の既定の適用。個人設定に `workflows.issue` は無い。利用者の指定ではない）
- 基準: `origin/main` の `4d41f1a`

## 意図

DSH の担当（`dsh-ccd`・`dsh-go`）が自分の sandbox の中で pytest を実行すると、ハードリンクを作る fixture の残骸が DSH の TMPDIR（`<attempt>/dsh/tmp`）に残る。runner は停止後の redact で、リンク数（`st_nlink`）が 1 でない通常ファイルを unsafe として `sensitive_paths` に入れ、成功した回答（payload あり・識別情報あり）を `response_failed` に変える。このリポジトリには、ハードリンクを意図して作るテストが agent_runner の中にも外にもある（Issue 本文と、コメントの `test_meshy.py`）。そのため、それらを変える PR のレビューで DSH のレビュアーが関連テストを実行すると、有料のレビュー（実例は約 31 分）が秘密の値を含まない fixture のために捨てられ、レビュー本文も残らない。

利用者の決定（D-220-1）のとおり、停止後の `tmp/` の掃除（`_prune_scratch`）で、自分が所有するリンク数 2 以上の通常ファイルも、開かず書き換えずに名前を消す（今の symlink・FIFO と同じ扱い）。`tmp/` の外（`state/`・patch・receipt など）のハードリンクは今どおり成功にせず、redact が他のリンクの内容を消せないという理由を崩さない。

## 確認した事実（2026-10-21 JST、`4d41f1a`）

ログはどれも `/workspaces/reso-world/tmp/agents/issue-220.z5vcohqb/` にある。

- 停止後の処理は `_dispose_home` → `_prune_scratch` → `_redact_runtime_tree` の順（`tools/agent_runner/runner.py:493-497`）
  - `_prune_scratch`（`runner.py:168-205`）は `<attempt>/dsh/tmp` の下だけを辿り、`_unlink_special_entries`（`runner.py:145-165`）で、自分が所有し runtime root と同じ device にある、通常ファイルでないもの（symlink・FIFO など）を、一覧を閉じた後に `os.unlink(name, dir_fd=…)` で消す。開かず、辿らない。所有者・device が違うディレクトリには入らない
  - `_redact_runtime_tree`（`runner.py:72-89`）は `<attempt>/dsh` の全体を辿り、通常ファイルでないもの・`st_nlink != 1` のもの・redact に失敗したものを unsafe として返す。リンク数を見る条件は `or` の手前にあるので、ハードリンクは開かれず書き換えられない
  - unsafe があり state が `success` なら `response_failed` にする（`runner.py:524-525`）
- `redact_file`（`tools/agent_runner/process.py:197-233`）は、redact した一時ファイルを `os.replace` でその名前に置き換える。同じ inode の別の名前には元の内容が残るので、リンク数 2 以上のファイルを redact で安全にすることはできない（ハードリンクを成功にしない理由）
- DSH の native のプロセスは、`/` を読み取り専用にし、attempt を読み取り専用で bind したうえで、作業ディレクトリ・`dsh/home`・`dsh/state`・`dsh/tmp`・`review-scratch` をそれぞれ別の `--bind` で書き込み可にする（`tools/agent_runner/adapters/dsh.py:216-224・314-317`、`tools/agent_runner/dsh_sandbox.py:25-42`）。bash ツールの入れ子の sandbox は作業ディレクトリ・`dsh/home`・`dsh/tmp`・`review-scratch` を別々に bind する（`adapters/dsh.py:267-275`、`dsh_sandbox.py:56-73`）
  - `link(2)` は mount をまたげない（EXDEV）。bwrap で同じ形の mount を作って確かめた: `state→tmp`・`worktree→tmp`・`tmp→worktree` はどれも errno 18（Invalid cross-device link）、`tmp→tmp` は作れてリンク数 2。既存のテスト `test_native_process_has_private_tmp_and_readonly_attempt_metadata` も、patch から `dsh/tmp` へのハードリンクが拒否されることを確かめている（`tools/agent_runner/tests/adapters/dsh/fake_cli.py:170-174`、`test_runner.py:136`）
  - したがって、担当が `dsh/tmp` に作るハードリンクの名前は、すべて同じ `dsh/tmp` の中にある
- `dsh/tmp/exports`（`review_exports`）は `tmp` の中にある。親は停止の後に `review.md`・`findings.json` を `parent_data.regular_bytes`（リンク数 1 の通常ファイルだけを読む）で読み、無ければ失敗にする（`.agents/skills/pr-review/scripts/review_run.py:1290-1297`）。exports の中の symlink・FIFO は、今も `_prune_scratch` が消している
- ハードリンクを作るテストの実例
  - `tools/agent_runner/tests/adapters/dsh/test_adapter.py:744`: `credentials` と `worktree/shared-hardlink`（親と子のディレクトリにまたがる組）
  - `tools/agent_runner/tests/adapters/dsh/test_review_evidence.py:115`: `stdout.log` と対象（同じディレクトリの組）
  - `tests/scripts/test_meshy.py:1230`: `operation.json` と `operation.json.backup`（同じディレクトリの組。Issue のコメント）
- 基準の結果
  - `uv run pytest tools/agent_runner/tests/adapters/dsh -q -rfEs`: 283 passed・skip なし・終了コード 0（`baseline-dsh-dir.log`）
  - `test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link` は基準で通る。偽の CLI の `tmp-hardlink` が TMPDIR に作ったハードリンクの組で `response_failed` になり、`dsh/tmp/linked.json` が `sensitive_paths` に入る（Issue の挙動そのもの。`baseline-targeted.log`）

## 設計

### 1. `_prune_scratch` が `tmp/` のハードリンクの通常ファイルも消す

- `_unlink_special_entries` の判定を、「自分が所有し、runtime root と同じ device にある、通常ファイルでないもの」から「…にある、通常ファイルでないもの、またはリンク数 2 以上の通常ファイル」に広げる。関数名は `_unlink_unredactable_entries` に変える（D-220-3）
- 消し方は今の symlink・FIFO と同じ: 一覧の時点の `lstat` の情報で判定し、一覧を閉じた後に `os.unlink(name, dir_fd=…)` で名前を消す。ファイルを開かず、読まず、書き換えない
- 辿る範囲は今どおり `<attempt>/dsh/tmp` の下だけ。`state/`・patch（`dsh/provider.patch.yml`）・receipt・HOME の処理と、`_redact_runtime_tree`・`redact_file`・state の決め方は変えない
- リンク数は一覧を取った時点の値で判定する（D-220-2）
  - 同じディレクトリにある組は、すべての名前が消える
  - 親と子など別のディレクトリにまたがる組では、後で辿るディレクトリの名前が、先の unlink でリンク数 1 になって残ることがある。その名前は TMPDIR のほかの通常ファイルと同じく `_redact_runtime_tree` が redact して残す。リンク数 1 なので、redact は内容そのものを置き換え、秘密の値は残らない
  - unlink に失敗した名前はリンク数 2 以上のまま残り、`_redact_runtime_tree` が今どおり unsafe として報告する（成功にしない）
- 担当が作れるハードリンクは `dsh/tmp` の中で閉じる（確認した事実）。名前を消しても、redact も報告もされない場所に内容が残る名前は無い

### 2. 説明の更新

- `runner.py` の `_prune_scratch` の docstring と、停止後の処理のコメント（`runner.py:488-492`）に、ハードリンクの通常ファイルも消すことと理由（redact が別の名前の内容を消せない）を書く
- `tools/agent_runner/adapters/dsh.py` の module docstring（8〜10 行）の「links and special files tools leave in TMPDIR are unlinked」に、ハードリンクの通常ファイルを足す
- `.devcontainer/README.md:596` の「TMPDIR の通常ファイルとセッション状態は redact して実行記録に残す」に、TMPDIR のハードリンクは消すことを足す（D-220-6）

### 3. テスト（`tools/agent_runner/tests/adapters/dsh/`）

偽の CLI（`fake_cli.py`）を bwrap の中で動かす、runner の実経路（`run_workflow`）のテストで確かめる。

- 偽の CLI
  - `tmp-hardlink`: TMPDIR に、秘密の値（`COMMANDCODE_API_KEY` の値）を含む `original.json` と、そのハードリンク `linked.json` を作り、さらに子のディレクトリに 3 つ目の名前 `nested/shared.json` を作る（実例の、同じディレクトリの組と、親子にまたがる組を 1 つの inode で再現する）
  - `hardlink`（新規）: `state/`（DSH_HOME）に `original.json` とそのハードリンク `linked.json` を作る。`symlink`・`fifo` が `state/`、`tmp-symlink`・`tmp-fifo` が TMPDIR という今の名前の付け方に合わせる
  - pytest の合成のテスト（`_PYTEST_CASE`）の fixtures の場合に、`tmp_path` の中のハードリンクの組を足す（実際の pytest が TMPDIR の basetemp に残す形）
- `test_runner.py`
  - `test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link`: 対象を `state/` のハードリンク（`hardlink`）に移す。`response_failed` で、両方の名前が `sensitive_paths` に入り、両方とも残ってリンク数 2 のまま（redact で置き換えられていない）ことを確かめる
  - 新規 `test_scratch_hardlinks_are_unlinked_and_the_rest_redacted`: `tmp-hardlink` で `success`、`sensitive_paths == []`、同じディレクトリの組（`original.json`・`linked.json`）が消え、`dsh/tmp` の下に残る通常ファイルはどれもリンク数 1、`dsh/` の下のどのファイルにも秘密の値が無い
  - `test_scratch_unlink_failure_is_reported_not_success`: `tmp-hardlink` の 3 つの名前の unlink を失敗させる場合をパラメータに足す。3 つとも `sensitive_paths` に入り、`response_failed`
  - `test_real_pytest_scratch_is_accepted`: TMPDIR に残ってはいけないものに、リンク数 2 以上の通常ファイルを足す。`pytest`（ハードリンクなし）と `pytest-fixtures`（ハードリンクあり）の両方が `success`
- 残さない場合（対照）は、既存の `success` のテスト（`test_private_session_artifacts_are_redacted` の `sensitive_paths == []` など）と `test_real_pytest_scratch_is_accepted[pytest]` が受け持つ

### 4. 変えないもの

- `_redact_runtime_tree`・`redact_file`・`_dispose_home`・runner の state の決め方
- DSH の adapter の mount・grant・依頼文、pr-review の DSH への指示、親の取り込み（`review_run.py`）
- `tmp/` の中の、リンク数 1 の通常ファイルの扱い（redact して残す）

## 受け入れ条件

1. DSH の担当が sandbox の中で pytest を実行して、TMPDIR にハードリンクの fixture を残しても、ほかに理由が無ければ回答は `success` のまま返り、`sensitive_paths` は空である（Issue の受け入れ条件 1）
2. `tmp/` の外の処理は変えない。`state/` のハードリンクは今どおり `response_failed` になり、両方の名前が `sensitive_paths` に残る（Issue の受け入れ条件 2。`test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link` の意図を保ち、対象を `state/` に移す）
3. 偽の CLI で、TMPDIR にハードリンクを残す場合（`tmp-hardlink`、実際の pytest の `pytest-fixtures`）と残さない場合（`success`、`pytest`）の両方を、runner の実経路で確かめる（Issue の受け入れ条件 3）
4. 秘密の値を含むファイルが redact されないまま保持される経路を増やさない。`tmp/` のハードリンクは開かずに名前だけを消し、残る名前はリンク数 1 なら redact、2 以上なら報告する。秘密の値を書いたハードリンクを TMPDIR に残す実行で、`dsh/` の下のどのファイルにも秘密の値が残らない。unlink に失敗したら報告して成功にしない（Issue の受け入れ条件 4）
5. DSH のテスト全体と README の「テスト」の入口（ワールドの行を除く）で、この変更による失敗が無い

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-220-1 対応案 2 を採る（利用者の決定）**
  - 選択: `_prune_scratch` が、`tmp/` の中の自分が所有するリンク数 2 以上の通常ファイルも unlink する（開かない・書き換えない。今の symlink・FIFO と同じ扱い）。`tmp/` の外のハードリンクは今どおり成功にしない
  - 別案: 案 1（担当の pytest の一時ディレクトリを `--basetemp` などで redact の対象の外に置く）、案 3（依頼文で、テストの一時ディレクトリを `review-scratch` などに置くよう指示する）
  - 理由: 利用者の決定。案 1 は pytest 以外が作るハードリンクが残り、案 3 はモデルが従うかに左右される。Issue のコメントのとおり、テストの場所に依らない形になる
  - 委任指示: 利用者の決定。`/workspaces/reso-world/tmp/agents/commander-219-220-221-206-212.0smdd1hj/decisions/issue-220.md` の全文を次に引用する

    ```text
    ### #220
    - 対応案 2 を採る。`_prune_scratch` が、`tmp/` の中の自分が所有する `st_nlink > 1` の通常ファイルも unlink する（開かない・書き換えない。今の symlink・FIFO と同じ扱い）
    - `tmp/` の外（`state/`・patch・receipt など）のハードリンクは、今までどおり成功にしない。`test_runtime_hardlinks_are_rejected_before_redaction_hides_the_link` の意図を保つ
    - 案 1（pytest の `--basetemp`）は pytest 以外が作るハードリンクが残るので、案 3（依頼文での指示）はモデルが従うかに左右されるので採らない
    ```

- **D-220-2 リンク数は一覧の時点の値で、1 回の走査で判定する**
  - 選択: 今の走査（ディレクトリごとに一覧を取り、閉じた後に消す）のまま、一覧の時点の `st_nlink` で判定する。ディレクトリをまたぐ組で後に残った名前（リンク数 1）は、ほかの通常ファイルと同じく redact して残す
  - 別案: (a) 1 回目の走査で `tmp/` のハードリンクの inode（`st_dev`・`st_ino`）を集め、2 回目でその inode のすべての名前を消す、(b) ハードリンクを見つけたら、その inode の名前を探して同時に消す
  - 理由: 残る名前はリンク数 1 の通常ファイルで、redact で内容が置き換わるので、秘密の値は残らない（受け入れ条件 4）。(a)・(b) はすべての名前を消せるが、走査と状態が増え、得るのは診断用の fixture の残骸を 1 つ減らすことだけである。テストは、残る名前があるかどうかに依らない形（残る通常ファイルのリンク数が 1、どのファイルにも秘密の値が無い）で確かめる
- **D-220-3 関数名を `_unlink_unredactable_entries` に変える**
  - 選択: `_unlink_special_entries` を `_unlink_unredactable_entries` に変え、docstring に対象（リンク・特殊ファイル・ハードリンクの通常ファイル）と理由を書く。ローカル変数 `special` も合わせる
  - 別案: 名前を変えずに docstring だけを直す
  - 理由: 通常ファイルも消すようになるので、`special` の名前は対象を表さない。対象は、`_redact_runtime_tree` が種類・リンク数を理由に unsafe とするものと同じで、「redact で安全にできないもの」と名付けると、消す理由も伝わる。呼び出しは `_prune_scratch` の 1 か所だけ
- **D-220-4 テストは偽の CLI を使う runner の実経路で書く**
  - 選択: 設計 3 のとおり、既存のテストの形（`tmp-symlink`・`tmp-fifo` と `pytest-fixtures`）に合わせて、偽の CLI のモードと pytest の合成のテストを足す・変える
  - 別案: (a) `_prune_scratch` を直接呼ぶ単体テストにする、(b) リポジトリの実際のテスト（`test_adapter.py` の `test_approval_classification_does_not_mutate_input_state` など）を偽の担当に実行させるテストを commit する
  - 理由: Issue の受け入れ条件 3 が runner の実経路を求めている。(a) は bwrap の中で作られるハードリンクと、停止後の処理の順序（prune → redact）を確かめない。(b) は遅く、ほかのテストの中身に依存して壊れやすい。(b) の形の再現は、基準と修正後の対照として Plan の検証で 1 回だけ行い、記録する（commit しない）
- **D-220-5 `dsh/tmp/exports` も同じ扱いにする**
  - 選択: exports の中のハードリンクも消す（例外を作らない）
  - 別案: exports だけは消さずに、今どおり報告して `response_failed` にする
  - 理由: exports は `tmp` の中で、symlink・FIFO は今も消している。native の write/edit が作る成果はリンク数 1 の通常ファイルで、ハードリンクになるのは担当が自分で `ln` した場合だけである。そのときも、親は固定の outbox のファイルが無ければ取り込みを失敗にする（確認した事実）ので、黙って受け入れることにはならない。失敗する段階が runner から親の取り込みに移るだけである
- **D-220-6 README の要約に 1 句足す**
  - 選択: `.devcontainer/README.md:596` に、TMPDIR のハードリンクは消すことを足す
  - 別案: README は変えない（runner と adapter の説明だけを直す）
  - 理由: その行は、実行記録に何が残るかを利用者に説明している。ハードリンクの fixture が残らないことを書かないと、診断で探したときに食い違う
- **D-220-7 既知の制限**
  - ディレクトリをまたぐハードリンクの組は、後で辿るディレクトリの名前が redact されて残る（D-220-2）。どちらが残るかは走査の順で決まる
  - 担当が自分で `ln` した exports の成果は消え、親の取り込みで失敗する（D-220-5）
  - pytest の basetemp の、リンク数 1 の通常ファイルは今どおり redact して実行記録に残る（量は変わらない）
  - この PR のループのレビュアー（個人設定）には DSH の担当が含まれないので、Issue の場面はループの中では起きない。実際の DSH の担当での確認は、DSH をレビュアーに含むループで次に起きたときに分かる
