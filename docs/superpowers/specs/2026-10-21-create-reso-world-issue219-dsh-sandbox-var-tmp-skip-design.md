# Issue #219: DSH の attempt の中では、test_sandbox.py の /var/tmp を使う 5 件を理由付きで skip する

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/219（親 Issue・ボード・先行 Issue・コメントは無い）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-21-create-reso-world-issue219-dsh-sandbox-var-tmp-skip.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-219-dsh-sandbox-var-tmp-skip`（branch `fix/issue-219-dsh-sandbox-var-tmp-skip`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-21（JST）、利用者が次のとおり指示した

  ```text
  /issue-to-pr https://github.com/usaturn/create-reso-world/issues/219 --merge --assign implement=self 利用者の決定を /workspaces/reso-world/tmp/agents/commander-219-220-221-206-212.0smdd1hj/decisions/issue-219.md に置いた。読んで Spec の決定記録に引用せよ
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #219`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）を回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う
  - 方針（D-219-1）は利用者の決定に従う。ほかの判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- ループのオプション（`loop.py check-options` の出力）: `max_cycles = 3`（既定の適用）、`assign = {"implement": ["self"]}`（利用者の指定 `--assign implement=self`）、`template = .devcontainer/agent-runner.toml`（既定の適用）、`config = null`。割り当ては、レビュー（`inspect`）が `devin-swe`・`pi-deepseek`・`claude-opus`・`pi-gpt`（agent-runner の設定の適用）、修正（`implement`）が `self`（利用者の指定）、自己レビュー（`self-review`）・修正の確認（`fix-check`）が `self`（既定の適用）。いずれも `fallback` なし
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の `workflows.issue` の既定の適用。個人設定に `workflows.issue` は無い。利用者の指定ではない）
- 基準: `origin/main` の `5a6b096`

## 意図

`tools/agent_runner/tests/adapters/dsh/test_sandbox.py` の 3 つのテスト（パラメータ化で 5 件）は、`tempfile.TemporaryDirectory(dir="/var/tmp")` で作業領域を作る。DSH の担当（`dsh-ccd`・`dsh-go`）の attempt は `/` を読み取り専用で見せ、作業ディレクトリと attempt の下の決まったパスだけを書き込み可にするので、その中でこれらのテストを実行すると、作業領域を作る段階で `OSError: [Errno 30] Read-only file system` になり、5 件が必ず失敗する。

- `test_explicit_grants_preserve_neighboring_host_files`
- `test_readonly_does_not_apply_additional_grants`
- `test_unsafe_grants_or_profile_never_run_the_command[symlink]`・`[missing]`・`[invalid_profile]`

DSH のレビュアーが agent_runner や DSH を変える PR の関連テストを実行するたびに、PR と無関係な 5 件の失敗が出る。base との比較にレビューの期限を使い、取り違えると誤った指摘と、それを確かめるレビュー修正のサイクルが増える（#198 と同じ種類の問題）。利用者の決定（D-219-1）のとおり、`/var/tmp` に作業領域を作れないときだけ理由を付けて skip し、ホストでは今どおり 5 件を実行して、守る挙動の検査を失わないようにする。

## 確認した事実（2026-10-21 JST、`5a6b096`）

- 再現（ログはどれも `/workspaces/reso-world/tmp/agents/issue-219.f0wvtucb/` にある）
  - `/tmp` の下の使い捨ての worktree（`/tmp/issue-219-repro.Nr5wNG/wt`、自前の `.venv`）で、DSH の attempt と同じ形の mount（`bwrap --ro-bind / / --dev /dev --unshare-pid --proc /proc --die-with-parent --cap-drop ALL --tmpfs /tmp --bind <worktree> <worktree>`。`outer_command` から attempt と grant を除いた形。以下「DSH の形の mount」）の中から `test_sandbox.py` を実行 → 5 failed・1 passed。5 件とも `OSError: [Errno 30] Read-only file system: '/var/tmp/dsh-sandbox-test-…'`（`baseline-mount-tmp.log`）
  - 同じ worktree をホストで実行 → 6 passed（`baseline-host-tmp.log`）。`/workspaces` の下の feature worktree でも 6 passed（`baseline-host-workspaces.log`）
  - DSH の形の mount で `tools/agent_runner/tests/adapters/dsh` 全体 → 6 failed・277 passed（`baseline-mount-tmp-dsh-dir.log`）。5 件は上と同じ。残りの 1 件（`test_runner.py` の `test_native_process_has_private_tmp_and_readonly_attempt_metadata`）は、この mount の `--unshare-pid` で pytest が PID 2 になり、テストが起動する内側の PID 名前空間にも PID 2 があるので、`/proc/<pytest の PID>/root` が見えて失敗する（`fake_cli.py:176-177`。外側と内側の両方で PID 2 になり、`/proc/2/root` が見えることを別に確かめた）。pytest を mount の最初のプロセスとして起動する検証の形の性質で、この Issue とも PR とも関係しない（Issue の記録では、実際の DSH の attempt の中でこのテストは通っている）
  - Issue の再現と同じ、`--unshare-pid` 無しの mount（`bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --bind <worktree> <worktree>`。以下「Issue の形の mount」）で同じディレクトリ全体 → 5 failed・278 passed。failed は `test_sandbox.py` の 5 件だけで、Issue の記録（278 passed・5 failed）と同じ（`baseline-issue-mount-tmp-dsh-dir.log`）
- 失敗するのは、テスト自身のプロセスが作業領域を作る段階（`tempfile.TemporaryDirectory` の `__init__` が呼ぶ `mkdtemp`）で、テストの対象（`dsh_sandbox.py`）を起動する前である。作業領域の作成の失敗は、テストの対象の欠陥を表さない
- `/var/tmp` を使う理由は 82 行のコメントのとおり。テストが起動する profile は `--tmpfs /tmp` で `/tmp` を空にするので、近くのホストのファイル（`neighbor`・`git/protected`）が読み取り専用で見えることを確かめるには、作業領域を `/tmp` の外に置く必要がある
- DSH の attempt で書き込めるのは、作業ディレクトリと、attempt の下の `dsh/home`・`dsh/state`・`dsh/tmp`・review-scratch だけ（`tools/agent_runner/adapters/dsh.py` の `prepare`、`tools/agent_runner/dsh_sandbox.py` の `outer_command`）。PR 修正ループのレビュアーでは、これらがすべて `/tmp/create-reso-world-pr-loop-*` の下にあり、`/tmp` の外に書き込める場所が無い
- 追跡するファイルで `/var/tmp` を使うのは、この 3 つのテストだけ（`git grep -n /var/tmp`、`docs/` を除く）
- 同じファイルの `test_missing_bwrap_never_executes_command` は `tmp_path` を使い、mount の中でも通る

## 設計

### 1. `/var/tmp` の作業領域を fixture にし、作れないときは理由付きで skip する

- `test_sandbox.py` に function scope の fixture `root` を置く。`tempfile.TemporaryDirectory(prefix="dsh-sandbox-test-", dir="/var/tmp")` を作り、作成で `OSError` が出たら `pytest.skip` する。理由（英語）には、`/var/tmp` に作業領域を作れなかったことと、例外の文（errno・理由・パス）を含める
- 作れたら `Path` を渡し、テストの後に今と同じく `TemporaryDirectory` が消す
- 3 つのテストは fixture `root` を受け取る。本体（`make_paths`・`invoke`・assert）は変えない
- skip するのは作業領域の作成の失敗だけ。作成の後の `make_paths`・`invoke`・assert の失敗は、今どおり失敗になる
- 82 行のコメント（`/var/tmp` を使う理由）は fixture に移し、DSH の attempt では作業領域そのものを作れないことを 1 行足す

### 2. 変えないもの

- adapter の本体（`tools/agent_runner/adapters/dsh.py`）・`tools/agent_runner/dsh_sandbox.py`・DSH の grant
- `test_sandbox.py` の `invoke`・`make_paths`・`test_missing_bwrap_never_executes_command`
- ほかの DSH のテスト

### 3. 検証（テストは足さない。D-219-4）

- ホスト: `/workspaces` の下の feature worktree と、`/tmp` の下の使い捨ての worktree（自前の `.venv` と、pr-review と同じ使い方の親の `.venv`）で、`tools/agent_runner/tests/adapters/dsh` が 0 failed・0 skipped（`-rs`）。`test_sandbox.py` の 6 件はすべて passed
- mount の中: `/tmp` の下の使い捨ての worktree から、DSH の形と Issue の形の両方の mount で `test_sandbox.py` が 1 passed・5 skipped・0 failed で、skip の理由に `/var/tmp` と `Read-only file system` が出る。Issue の形の mount で `tools/agent_runner/tests/adapters/dsh` 全体を実行し、base の同じ実行と比べて、5 件が failed から skipped に変わり、ほかの結果が変わらない
- README の「テスト」の入口（ワールドの行を除く）: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`

## 受け入れ条件

1. ホスト（`/workspaces` の下と `/tmp` の下の checkout）で、5 件が skip されずに実行されて通る
2. DSH と同じ形の mount の中で、5 件が理由付きで skip され、失敗しない
3. skip するのは `/var/tmp` に作業領域を作れないときだけで、作れた後の失敗は失敗のまま（検査の対象を減らさない）
4. adapter の本体と DSH の grant は変えない（差分は `test_sandbox.py` と Spec・Plan だけ）
5. `uv run pytest tools/agent_runner/tests/adapters/dsh` と README の「テスト」の入口で、この変更による失敗が無い

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-219-1 Issue の候補 (a) を採る（利用者の決定）**
  - 選択: `/var/tmp` に作業領域を作れないときだけ、理由を付けて skip する。ホストでは今どおり実行する。adapter の本体と DSH の grant は変えない
  - 別案: (b) `/tmp` の外で書き込める別の場所を探して使う
  - 理由: 利用者の決定。PR 修正ループの DSH のレビュアーには `/tmp` の外に書き込める場所が無く、(b) を採っても (a) が要る（Issue の「対応の候補」）
  - 委任指示: 利用者の決定。`/workspaces/reso-world/tmp/agents/commander-219-220-221-206-212.0smdd1hj/decisions/issue-219.md` の全文を次に引用する

    ```text
    ### #219
    - 案 (a) を採る。`/var/tmp` に作業領域を作れないときだけ、理由を付けて skip する。ホストでは今どおり実行する。adapter の本体と DSH の grant は変えない
    ```

- **D-219-2 skip するかは、作業領域の作成を試して決める**
  - 選択: `TemporaryDirectory` の作成を試し、`OSError` なら skip する
  - 別案: (a) 事前に `os.access("/var/tmp", os.W_OK)` で調べる、(b) 環境変数などで DSH の attempt の中かを調べる、(c) errno を `EROFS`・`EACCES`・`EPERM` に絞り、ほかは失敗にする
  - 理由: 利用者の決定の「作業領域を作れないとき」をそのまま条件にする。(a) は調べた時と作る時で結果が違いうるうえ、Landlock のように `access(2)` が通っても作成を拒む仕組みでは外れる。(b) は DSH の attempt の中でも `/var/tmp` に書き込める構成なら実行できるのに skip し、DSH 以外の読み取り専用の環境では失敗が残る。(c) で失敗に残る errno（`/var/tmp` が無い `ENOENT`、容量不足など）も、テストの対象の欠陥ではなく前提の不成立である。理由に例外の文を含めるので、どの errno で skip したかは `-rs` で分かる
- **D-219-3 fixture にまとめる**
  - 選択: function scope の fixture `root`（`invoke`・`make_paths` の引数と同じ名前）
  - 別案: (a) 3 か所の `with` にそれぞれ `try`/`except` を書く、(b) skip する contextmanager の helper を作る
  - 理由: skip の判定を 1 か所に置け、テストの setup の skip として報告される。名前を揃えて、テストの本体を変えずに済む。(a) は同じ処理を 3 回書く。(b) は fixture と同じことを pytest の外で組み立てる
- **D-219-4 テストは足さない**
  - 選択: 既存の 5 件の前提だけを直し、ホストと mount の中の実行で、修正の前の失敗と後の skip・成功を確かめて Plan と PR に記録する
  - 別案: (a) mount の中で pytest を起動し、5 件の skip を確かめるテストを足す、(b) `mkdtemp` を失敗させて skip を確かめるテストを足す
  - 理由: 守る挙動は既存の 5 件そのもので、skip の分岐はテストの前提である。(a) は checkout と環境を mount に入れる仕組みが要り、遅く壊れやすい（D-198-4 と同じ）。(b) はテストのためのテストで、`AGENTS.md` の「テストの採用基準」の書く場合に当たらない
- **D-219-5 既知の制限を残す**
  - DSH の attempt の中では、`/tmp` の外に書き込める場所がある構成でも、`/var/tmp` に書き込めなければ 5 件は skip される。候補 (b) を採らないため
  - ホストで `/var/tmp` に書き込めない環境でも skip になり、失敗としては気付かない。skip の理由は `-rs` で出る。この Dev Container のホストでは `/var/tmp` に書き込める（確認した事実）
  - DSH の担当が実行した結果では、5 件は passed ではなく skipped と数えられる。この 5 件の検査はホストの実行（README の入口を含む）で行う
