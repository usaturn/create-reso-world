# Issue #198: DSH の adapter のテスト 2 件を、checkout の場所に依らず通るようにする

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/198（親 Issue・ボード・先行 Issue は無い。重複の #199 は close 済み）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue198-dsh-test-tmp-checkout.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-198-dsh-test-tmp-checkout`（branch `fix/issue-198-dsh-test-tmp-checkout`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-20（JST）、利用者が `/issue-to-pr #198 --merge` で着手を指示した。issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #198`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）を回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う
  - 下の判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- ループのオプション（`loop.py check-options` の出力）: `max_cycles = 3`、`assign = {}`、`template = .devcontainer/agent-runner.toml`、`config = null`。どれも既定の適用で、利用者の指定ではない。割り当ては、レビュー（`inspect`）が `pi-gpt`・`devin-swe`・`dsh-ccd`・`cursor-grok47`、修正（`implement`）が `claude-opus`、自己レビュー・修正の確認が `self`（いずれも `fallback` なし）
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の既定の適用。利用者の指定ではない）
- 基準: `origin/main` の `f2350a4`

## 意図

`tools/agent_runner/tests/adapters/dsh/test_adapter.py` の次の 2 件は、リポジトリの checkout が `/tmp` の下にあると落ちる。DSH のサンドボックスは `/tmp` を空の tmpfs にし、決まったパスだけを読み取り専用で戻すので、テストが前提にしている checkout の中のファイルが見えなくなる。

- `test_tmp_launch_script_and_shared_environment_are_visible_readonly`
- `test_tmp_parent_review_inputs_are_readonly_in_native_and_inner_bash`

pr-review の `/tmp/pr-review-*`、review-fix-planning・review-verify の `mktemp -d "${TMPDIR:-/tmp}/..."` の隔離 worktree は `/tmp` の下にあるので、その中で DSH の adapter を変える PR を確かめると、変更と無関係な失敗が出て、レビュアーが PR の欠陥と取り違えるおそれがある。テストの前提だけを直し、checkout がどこにあっても同じ検査が実行されるようにする。

## 確認した事実（2026-10-20、`f2350a4`）

- 再現: `/tmp` の下の使い捨ての worktree で `uv run --locked pytest tools/agent_runner/tests/adapters/dsh` は 2 failed・281 passed（worktree 自身の `.venv`）。pr-review と同じ使い方（`PYTHONPATH="$WT" uv run --project /workspaces/reso-world --locked python -m pytest ...`）では 1 failed（2 件目）・282 passed
  - 1 件目: `bwrap: execvp <checkout>/.venv/bin/python: No such file or directory`
  - 2 件目: サンドボックスの中の helper が `FileNotFoundError: <checkout>/.agents/scripts/review_target.py`
- adapter（`tools/agent_runner/adapters/dsh.py:248-266`）が `/tmp` の下で戻すのは、attempt、adapter の checkout の `tools/`、`sys.prefix`、親の入力（snapshot・bundle・親の checkout）、担当のコマンドのうち絶対パスのファイル（`resolve` した実体）、作業ディレクトリの Git だけ。checkout の `.agents/` と、checkout の `.venv/bin/python`（`resolve` すると `/usr/bin/python3.14` になり、`/tmp` の外なので戻す対象から外れる）は戻らない
- 1 件目は `sys.prefix` を `/tmp` の下の別のディレクトリに差し替えるので、checkout の `.venv` が戻らない。担当のコマンドに `sys.executable`（checkout の `.venv/bin/python`）を使うため、`.venv` が `/tmp` の下だと起動できない。親の `.venv`（`/workspaces` の下）を使う pr-review の使い方では通る
- 同じファイルの `test_adapter_cache_paths_are_writable_with_its_scoped_runner`（102〜103 行）は、同じ理由で `Path(sys.executable).resolve()`（実体の interpreter）を使っている
- 2 件目は `fake_cli.py` の `parent-input` モードが、checkout のルート（`Path(__file__).resolve().parents[5]`）の `.agents/scripts/review_target.py` を、内側のサンドボックスの helper から読む。`fake_cli.py` 自身と `tools.test_support.dsh` は、adapter が戻す `tools/` の中にあるので見える。`.venv` は `sys.prefix` として戻るので見える。見えないのは `.agents/` だけ
- `review_target.py` は標準ライブラリだけを import し（34〜46 行）、`require_parent_root` は `git -C <親の checkout>` だけを呼ぶ。ほかのファイル（`agent_tmp.py`・`superpowers_context.py`）は、それを使う関数の中で遅れて読む
- `fake_cli.py` の `parent-input` モードを使うのは 2 件目のテストだけ
- 実際の運用では、tool root（skill と helper の置き場所）は親の main checkout（`/workspaces/reso-world`）で、読み取り専用の `/` 越しに見えるので、この問題は起きない（Issue の「本番への影響の確認と決定」）

## 設計

### 1. 1 件目: 担当のコマンドを実体の interpreter にする

`context.agent.command` の interpreter を `sys.executable` から `str(Path(sys.executable).resolve())` に変え、`test_adapter_cache_paths_are_writable_with_its_scoped_runner` と同じ理由のコメントを付ける。起動するスクリプト（`tmp_path/cli.py`）は標準ライブラリだけを使うので、venv が無くても動く。検査の対象（`/tmp` の下の起動スクリプトと、`sys.prefix` として戻る共有の環境が見え、書き込めないこと）は変わらない。

### 2. 2 件目: helper の写しを attempt に置き、そのパスを渡す

- `parent_review` fixture で、checkout の `.agents/scripts/review_target.py` を attempt（`context.receipt_path.parent`）に写し、そのパスを依頼のパラメータ `probe_helper` に入れる（同じ fixture の `probe_neighbor` と同じ形）
- `fake_cli.py` の `parent-input` モードは、checkout のルートから求める代わりに `parameters["probe_helper"]` の helper を読む
- attempt は外側・内側の両方のサンドボックスで読み取り専用で戻るので、checkout がどこにあっても helper が見える。実際の運用で tool root が読み取り専用で見えるのと同じ条件になる
- 検査の対象（親の入力が native と内側の bash の両方で見え、書き込めないこと、helper の `require_parent_root` が親の checkout を確かめられること）は変わらない

### 3. 変えないもの

- adapter の本体（`tools/agent_runner/adapters/dsh.py`）・`dsh_sandbox.py`・`dsh_paths.py`
- review-fix-planning・review-verify・pr-review の手順（worktree を `/tmp` の下に作ること）
- ほかの DSH のテスト（`/tmp` の下で通ることを確かめるだけ）

### 4. 検証（テストは足さない。D-198-4）

- `/tmp` の下の使い捨ての worktree（修正後の commit）で、worktree 自身の `.venv` と、pr-review と同じ使い方（親の `.venv`、`PYTHONPATH` を worktree）の両方で `tools/agent_runner/tests/adapters/dsh` を実行し、すべて通ること。skip が 0 件であること
- `/workspaces` の下の feature worktree で `uv run pytest tools/agent_runner/tests/adapters/dsh` がすべて通ること
- `README.md` の「テスト」の入口（ワールドの行を除く）: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`

## 受け入れ条件

1. `/tmp` の下の checkout で、worktree 自身の `.venv` でも、pr-review と同じ使い方でも、`tools/agent_runner/tests/adapters/dsh` が通る
2. `/workspaces` の下の checkout で、同じディレクトリが通る
3. 2 件のテストは skip されずに実行され、検査の対象を減らさない
4. adapter の本体と検証の手順は変えない
5. `README.md` の「テスト」の入口で、この変更による失敗が無い

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-198-1 テストの前提だけを直す（Issue の候補 (a)）**
  - 選択: テストと `fake_cli.py` だけを変える
  - 別案: (b) 検証の手順の worktree を `/tmp` の外に作る、(c) adapter が tool root の `.agents/` を戻す（#199 の案 1）
  - 理由: Issue の決定（2026-10-20）。(b) は複数のスキルの手順を変え、Issue のコメントのとおり `TMPDIR` を checkout の中に向けると別の誤った失敗が出る。(c) は通常の運用に影響しない問題のために、サンドボックスが戻す範囲を広げる
  - 委任指示: Issue の決定に従う
- **D-198-2 1 件目は実体の interpreter を使う**
  - 選択: `Path(sys.executable).resolve()` を担当のコマンドにする
  - 別案: (a) checkout の `.venv` が `/tmp` の下なら skip する、(b) `sys.prefix` を差し替えず checkout の `.venv` を戻させる
  - 理由: 同じファイルの別のテストと同じ扱いで、検査の対象を減らさない。(a) はレビュー用の worktree で検査が実行されなくなる。(b) はテストが確かめる「共有の環境（`sys.prefix`）が戻る」の前提を変える
- **D-198-3 2 件目は helper の写しを attempt に置き、依頼のパラメータで渡す**
  - 選択: `parent_review` fixture が `review_target.py` を attempt に写し、`probe_helper` で `fake_cli.py` に渡す
  - 別案: (a) checkout が `/tmp` の下なら skip する、(b) 写しを作業ディレクトリ（`context.work_dir`）に置く、(c) helper のパスを担当のコマンドの引数に足し、adapter の「コマンドのファイルを戻す」で見せる、(d) 環境変数（`FAKE_HOST_TARGET` と同じ形）で渡す
  - 理由: attempt は両方のサンドボックスで読み取り専用で戻り、tool root が読み取り専用で見える実際の運用と同じ条件になる。(a) は検査が実行されなくなる。(b) は helper が書き込める場所になり、実際の運用と条件が違う。(c) は `fake_cli.py` の引数の形（`--profile headless` が先頭）を崩し、別の目的の仕組みに頼る。(d) でも動くが、同じ fixture は検査用の値（`probe_neighbor`）を依頼のパラメータで渡しているので、それに揃える
  - 既知の制限: 2 件目は、checkout の `.agents/` そのものが読み取り専用の `/` 越しに見えることを確かめなくなる。これは `--ro-bind / /` の性質で、checkout が `/tmp` の外にあるときだけ成り立つ前提だった
- **D-198-4 テストは足さず、`/tmp` と `/workspaces` の両方の実行で確かめる**
  - 選択: 変更するのは既存の 2 件のテストと fake CLI だけ。修正の前の失敗と後の成功を、両方の場所での実行で確かめ、結果を Plan と PR に記録する
  - 別案: checkout を `/tmp` の下に写して 2 件を実行するテストを足す
  - 理由: 守る挙動は既存の 2 件そのもので、検査の場所を変えるテストは、checkout の写しと uv の環境づくりが要り、遅く壊れやすい。`AGENTS.md` の「テストの採用基準」に従う
- **D-198-5 既知の制限を残す**
  - tool root を `/tmp` の下に置く例外の運用（main に無い版の loop を実機で試すなど）では、DSH の子が tool root の skill・helper を読めない。Issue の決定のとおり、この PR では扱わない
  - `TMPDIR` を checkout の中に向けると出る別の誤った失敗（Issue のコメント）も扱わない。候補 (b) を見直すときの注意として Issue に残っている
