# Issue #166: テストの git に、外から渡された `GIT_*` を引き継がない

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/166（親 Issue・ボード・先行 Issue は無い）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue166-test-git-env-isolation.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-166-test-git-env-isolation`（branch `fix/issue-166-test-git-env-isolation`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-20（JST）、利用者が `/issue-to-pr #166` で着手を指示した。issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #166`）まで行う。マージはしない
  - 下の判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の既定の適用。利用者の指定ではない）
- 基準: `origin/main` の `8f5074a`
- builder check（brainstorming の読み合わせ、2026-10-20、model sonnet）の 2 点（`GIT_*` をすべて除くと、git が暗黙に読む値に頼るテストが壊れないか、ルートの `conftest.py` が各スイートで読まれるか）は、どちらも調べて決められたので、「確認した事実」の最後の 2 項目に書き込んだ。利用者に確かめる必要のある点は無かった

## 意図

linked worktree で `git rebase --exec <テスト>` を実行すると、git は `GIT_DIR=<common>/.git/worktrees/<name>` を export してコマンドを起動する。テストの fixture が `GIT_*` を除かずに git を起動すると、`git init`・`git -C <一時ディレクトリ>` も `GIT_DIR` のリポジトリを使い、実リポジトリの共有の設定・index・ブランチを書き換える。規約（`AGENTS.md` の「編集前の確認」）で追跡ファイルは linked worktree で編集するので、各コミットでテストを通す使い方で実害が出る。テストの git が `GIT_*` を引き継がないようにする。

## 確認した事実（2026-10-20）

- #166 に open PR・予約・worktree・branch は無い。ボードの子ではない
- Issue のコメント（2026-10-18）で、`.agents/scripts/tests/test_agent_tmp.py` と `tests/scripts/test_superpowers_context.py` も、linked worktree の `git rebase --exec` で共有の設定を `core.bare=true` などに書き換えることが確かめられている
- 一時リポジトリを作る pytest のテストのうち、`GIT_*` を除いていないもの: `tools/agent_runner/tests/` の `test_cli.py`・`test_runner.py`・`test_review_regressions.py`・`test_workspace.py` と、`adapters/` の `claude_code`・`devin`・`pi` の `conftest.py`・`codex`・`cursor` の `test_integration.py`・`dsh` の `test_adapter.py`・`test_sandbox.py`、`.agents/scripts/tests/test_agent_tmp.py`、`.agents/skills/` の `agent-handoff`・`issue-to-pr`（`test_resolve_issue.py`）・`review-fix-planning`（`test_review_fix_planning_skill_contract.py`。`GIT_CONFIG_*` だけを足し、`GIT_DIR` は残す）・`stale-git-lock-recovery` のテスト
- 既に `GIT_*` を除いているもの: `.agents/skills/pr-review/tests/conftest.py`（スイート全体）、`.agents/scripts/tests/test_review_target.py`・`test_review_findings.py`、`.agents/skills/issue-to-pr/tests/test_implement_task_run.py`、`review-fix-planning/tests/test_run_roles.py`、`review-verify/tests/test_dispatch.py`・`test_evaluation.py`、`repo-cleanup-after-merge/tests/test_detached_update.py`、`tools/agent_runner/tests/adapters/dsh/test_runner.py`。どれもテストの関数の scope の autouse fixture か、`env=` に渡す辞書で除く。いくつかは `GIT_CONFIG_GLOBAL=/dev/null`・HOME も差し替える
- `tests/scripts/test_superpowers_context.py`・`test_superpowers_review_copy.py` は unittest で、`tests/scripts/test-superpowers-python.bash`（`python -m unittest discover`）から実行される。git はすべて `self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")` で起動する
- `.devcontainer/run-tests.bash`（`README.md` の「テスト」の 1 つ目の入口）が実行する bash のテストのうち 8 本（`tests/scripts/test-scan-before-push.bash` など）が `git init` で一時リポジトリを作り、`GIT_*` を除いていない
- 一時リポジトリを作る fixture は、どれもテストの関数の scope で、モジュールの import の時点で git を書き換える処理は無い（scope が module の fixture は `tests/scripts/test_meshy_conversion.py`・`review-verify/tests/test_dispatch.py` にあるが、git を使わない）
- テストが外の環境の `GIT_*` の値を読む箇所は無い（`os.environ["GIT_..."]`・`getenv("GIT_...")` は 0 件）。runner が `GIT_*` を除くことを確かめる既存のテスト（`test_runner.py`・`test_workspace.py`）は、テストの本体で `monkeypatch.setenv("GIT_DIR", ...)` する
- pytest 9.1.1 は、独自の設定（`pyproject.toml`）を持つディレクトリで実行すると、その rootdir より上の `conftest.py` を読まない（一時ディレクトリで確かめた）。リポジトリのルートに `conftest.py` を置いても、`worlds/<name>/`・`external/` の pytest には効かない
- 逆に、リポジトリの中のテストは、どれもルートの `pyproject.toml` で rootdir がリポジトリのルートに決まる（`uv run pytest --co tools/agent_runner/tests/test_workspace.py` の `rootdir:` で確認）。`tools`・`.agents`・`tests` の下にある pytest の設定は `.agents/skills/rst-writer/evals/fixtures/` の評価用の 2 つだけで、テストの実行には使われない
- Dev Container は `GIT_*` を export しない（`.devcontainer/*.json` に 0 件）。このセッションの環境の `GIT_*` は Claude Code が設定する `GIT_EDITOR=true` だけ。一時リポジトリに commit するテストは、リポジトリの設定か `-c` で作者を設定する。`GIT_*` をすべて除く既存の fixture（`pr-review` の conftest など）で、そのスイートは通っている。`-m` の無い `git commit` などエディタを起動する git はテストに無い

## 設計

### 1. pytest のテスト全体: ルートの `conftest.py`

リポジトリのルートに `conftest.py` を新しく作り、テストの関数の scope の autouse fixture で、`os.environ` の `GIT_` で始まる変数をすべて `monkeypatch.delenv` で除く。`pyproject.toml` の `testpaths`（`tests/skills`・`.agents/skills`・`.agents/scripts`・`tools`）と、パスを指定した `uv run pytest <パス>` の両方で効く。

- fixture の名前は、既存の `isolated_git_environment`（`pr-review` の conftest・各テストのファイル）と別にする。同じ名前だと下の階層の fixture が上書きし、ルートの fixture が動かない
- pytest は autouse fixture を、上の階層（ルートの conftest）から順に準備する。既存の fixture が足す `GIT_CONFIG_GLOBAL=/dev/null` などは、ルートの fixture の後に設定されるので消えない（実装の後に `--setup-plan` で順序を確かめる）
- 除くのは `GIT_*` だけ。HOME・利用者の git の全体設定は変えない（D-166-3）
- テストの本体で設定した `GIT_DIR` などは、今までどおり monkeypatch がテストの後に戻す

### 2. unittest のテスト: `tests/scripts/` の 2 本

`test_superpowers_context.py`・`test_superpowers_review_copy.py` の `self.env` を、`os.environ` から `GIT_` で始まる変数を除いた辞書に `GIT_CONFIG_NOSYSTEM`・`GIT_CONFIG_GLOBAL` を足す形にする。pytest の conftest は unittest の実行（`python -m unittest`）には効かない。

### 3. bash のテスト: `.devcontainer/run-tests.bash`

テストを順に実行する前に、ランナーのシェルで export された `GIT_*` をすべて `unset` する（`compgen -e -X '!GIT_*'` で名前を得る）。ランナーから起動する bash のテストと、その中の unittest（`test-superpowers-python.bash`）に `GIT_*` が渡らない。個々の bash のテストを直接実行する場合は対象外（既知の制限）。

### 4. 回帰テスト

- **pytest**: `tools/agent_runner/tests/test_git_isolation.py` を新しく作る。fixture と同じ形の git（`git -C <tmp> init`・`config user.name`・`add`・`commit`）を行い、git の管理領域が一時ディレクトリの `.git` であることを確かめるテストと、それを別の pytest のプロセスで起動するテストを置く。後者は、一時ディレクトリに作ったリポジトリと linked worktree について、その worktree の `GIT_DIR`（`rev-parse --absolute-git-dir`）を export した環境で前者を実行し、終了コード 0 と、共有の設定（`.git/config`）・worktree の HEAD のブランチと commit・index・`status --porcelain` が変わらないことを確かめる。内側の pytest の `--basetemp` は外側のテストの一時ディレクトリの中にする
- **bash**: `.devcontainer/test-run-tests.bash` に 4 番目の場合を足す。一時ディレクトリのリポジトリの `.git` を `GIT_DIR` にして、`git init`・`git -C <dir> config` を行う偽のテストを `run-tests.bash` に渡し、そのリポジトリの `.git/config` が変わらず、偽のテストのリポジトリが自分の `.git` に作られることを確かめる
- **unittest の 2 本**: テストを足さない。統合確認で `GIT_DIR` を export した環境で実行し、元のリポジトリが変わらないことを確かめる（D-166-6）

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-166-1 範囲は `README.md` の「テスト」の入口のテスト全体**
  - 選択: agent_runner のテストに加え、pytest のテスト全体、`tests/scripts/` の unittest 2 本、`run-tests.bash` が実行する bash のテストを対象にする
  - 別案: (a) Issue の「やること」の必須部分だけ（`tools/agent_runner/tests/`）、(b) Issue が挙げた Python のテストまで
  - 理由: Issue のコメントで `test_agent_tmp.py`・`test_superpowers_context.py` の実害が確かめられ、本文の「未確認」が解消している。Issue の「検証」は `README.md` の「テスト」の入口を挙げており、その入口の 1 つ（`run-tests.bash`）の bash のテストも同じ形で一時リポジトリを作る。(a)・(b) では、同じ使い方（`git rebase --exec` で入口のテストを通す）で実害が残る
- **D-166-2 pytest はルートの `conftest.py` に 1 つの fixture を置く**
  - 選択: リポジトリのルートの `conftest.py` に autouse fixture を置く
  - 別案: 各スイート（`tools/agent_runner/tests/conftest.py`、`.agents/scripts/tests/`、各スキルの `tests/`）に同じ fixture を置く
  - 理由: Issue の「やること」が挙げる選択肢の 1 つで、`testpaths` のすべてと今後のテストに 1 か所で効く。別案は同じ処理を 6 か所以上に写し、新しいスイートで再発しうる。ワールドのプロジェクトと `external/` には効かない（「確認した事実」の最後）
- **D-166-3 除くのは `GIT_*` だけで、HOME・全体設定は変えない**
  - 選択: `GIT_` で始まる変数を除くだけにする
  - 別案: `test_detached_update.py` のように、HOME・`XDG_CONFIG_HOME`・`GIT_CONFIG_GLOBAL=/dev/null`・`GIT_CONFIG_NOSYSTEM=1` も設定する
  - 理由: Issue の「やること」は `GIT_*` を除くこと。全体設定の隔離はテスト全体が読む設定（署名・hook など）を変える別の問題で、PR #185 のレビューの L-1 は対応しない判断をしている。runner 自身の git も `GIT_*` を除いて起動するので、テストの側で `GIT_CONFIG_GLOBAL` を設定しても runner の git には届かない。必要なスイートは今までどおり自分で設定する
- **D-166-4 既存の個別の fixture は残す**
  - 選択: `pr-review` の conftest などの既存の隔離は変えない
  - 別案: ルートの fixture と重なる部分を消す
  - 理由: 既存の fixture は HOME・全体設定も隔離しており、ルートの fixture では代わりにならない。消すのは整理であり、この Issue の不具合の修正ではない
- **D-166-5 bash のテストは `run-tests.bash` でまとめて除く**
  - 選択: ランナーでテストを実行する前に `GIT_*` を `unset` する
  - 別案: (a) 8 本の bash のテストをそれぞれ直す、(b) `tests/scripts/lib/` の共通部分で除く
  - 理由: `README.md` の入口は `run-tests.bash` で、1 か所で今後のテストにも効く。(b) は `.devcontainer/test-*.bash` が読まない
  - 既知の制限: bash のテストを 1 本ずつ直接実行する場合は除かない
- **D-166-6 unittest の 2 本は `self.env` で除き、テストは足さない**
  - 選択: `self.env` の作り方を変え、統合確認で `GIT_DIR` を export した実行の結果を記録する
  - 別案: (a) `run-tests.bash` の修正だけに頼る、(b) 2 本それぞれに、別のプロセスで自分を起動する回帰テストを足す
  - 理由: (a) では `python -m unittest` で直接実行したときに残る。(b) は pytest の回帰テストと同じ仕組みの検査を重ねるだけで、守る挙動（`GIT_*` を含まない辞書で git を起動する）は 1 行の変更で、統合確認の実行で確かめられる
- **D-166-7 回帰テストの置き場所は `tools/agent_runner/tests/`**
  - 選択: `tools/agent_runner/tests/test_git_isolation.py`
  - 別案: (a) `tests/` の下に新しいディレクトリを作り、`testpaths` と入口のコマンドに足す、(b) `tests/skills/`
  - 理由: Issue の主な対象が agent_runner のテストで、`README.md` の pytest の入口に含まれる。(a) は入口のコマンドを書いた文書（`README.md`・`.devcontainer/README.md`・スキルの手順）を変えることになる。(b) はスキルのパッケージの検査の置き場所
- **D-166-8 実行方式は inline（`superpowers:executing-plans`）**
  - 選択: このセッションが Plan の Task を順に実装する
  - 別案: `superpowers:subagent-driven-development`
  - 理由: `check` の `self` が true。Task はどれも数行の変更で、子に文脈（再現の形・既存の fixture の順序）を渡す手間が実装より大きい。最後のブランチ全体のレビューは省かない

## 受け入れ条件

1. `GIT_DIR` に linked worktree の管理領域を export した環境で `uv run pytest tests/skills .agents/skills .agents/scripts tools`・`bash .devcontainer/run-tests.bash`・`python -m unittest discover -s tests/scripts -p 'test_*.py'` を実行しても、そのリポジトリの共有の設定・HEAD（ブランチと commit）・index・作業ツリーが変わらない（使い捨ての clone で確かめる）
2. Issue の再現（linked worktree で `git rebase --exec 'uv run pytest -q tools/agent_runner/tests/test_workspace.py::test_resolve_revision_pins_commit_not_branch' HEAD~1`）が途中で止まらずに終わり、共有の設定に `user.name=Test` が書き込まれない
3. 新しい回帰テスト（pytest と bash）は、修正の前に失敗し、修正の後に通る
4. 既存の fixture が足す `GIT_CONFIG_GLOBAL` などが、ルートの fixture に消されない（`--setup-plan` で順序を確かめる）
5. `README.md` の「テスト」の入口（ワールドの行を除く）が、変更の前の基準と同じ結果になる（新しいテストの分だけ件数が増える）

## 範囲外

- 個々の bash のテストを直接実行する場合（D-166-5 の既知の制限）
- テストが読む利用者の git の全体設定・HOME の隔離（D-166-3）
- 既存の個別の fixture の整理（D-166-4）
- ワールドのプロジェクトと `external/` のテスト
- runner・helper 本体（`tools/agent_runner/`・各スクリプト）の変更。本体は既に `GIT_*` を除いている

## 実装者に任せること

- fixture の名前・docstring の文面
- 回帰テストの一時リポジトリの作り方の細部（ファイル名・commit のメッセージ）
