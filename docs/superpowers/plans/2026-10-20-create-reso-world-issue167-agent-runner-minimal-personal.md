# Issue #167 agent-runner の最小の個人設定 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/167
- worktree: `/workspaces/reso-world/.worktrees/issue-167-agent-runner-minimal-personal`（branch `fix/issue-167-agent-runner-minimal-personal`、基準 `origin/main` の `8f5074a`）

**Goal:** postCreate が個人設定に雛形を丸写しするのをやめ、`schema_version = 1` と上書きの例のコメントだけの最小のファイルを置く。

**Architecture:** 追跡するファイル `.devcontainer/agent-runner-personal.toml` を足し、`place_agent_runner_config` は写す元をそれに変えるだけにする。runner の設定の読み方（雛形 < 個人設定、table は統合・配列は置換）は変えない。

**Tech Stack:** bash（postCreate とその検査）、Python 3.14 + pydantic（`tools/agent_runner`、pytest）、TOML

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue167-agent-runner-minimal-personal-design.md`

## Global Constraints

- 新しいファイルのパスは `.devcontainer/agent-runner-personal.toml`。有効な行は `schema_version = 1` だけ。上書きの例はすべてコメントにし、agent 名は仮の名前（`agent-a`・`agent-b`）にする
- `place_agent_runner_config` の置く条件（`XDG_CONFIG_HOME` が絶対パスのときだけその下、それ以外は `~/.config` の下。既存の設定と壊れた symlink は変えない。置けなければ失敗を返す）は変えない
- `tools/agent_runner/config.py` は変えない
- `.devcontainer/` のファイルにワークスペースの絶対パスを書かない（`test-readme.bash` が検査する）
- テストに運用で変わる値（期限の秒数・モデル名・agent 名）を写さない（`AGENTS.md` のテストの採用基準 3）
- 利用者のホームの既存の個人設定（`~/.config/agent-runner/config.toml`）は書き換えない

## Review Focus

- 利用者が例のコメントを外したとき: `[roles.implement]` に `deadline_seconds` だけを書いても、雛形のほかの項目（`writes` など）は残る（table の統合）。例は文書であり、テストは足さない
- #167 より前に置かれた丸写しの個人設定: 自動では直さない。README の 1 文で扱う（Spec D-167-5）
- runner の schema が上がったとき: 最小の個人設定の `schema_version = 1` で `schema_version` の分類で止まる（Spec D-167-3。schema 2 が無いのでテストしない）
- postCreate の実行時に `AGENT_RUNNER_CONFIG` があるとき: 今までどおり保存先に使わない（関数の前のコメントを保つ）
- 雛形の行の書き方が変わり、T' を作る正規表現が当たらなくなったとき: Task 1 の検査は全役割・全 agent の値が変わったことを確かめるので、当たらなければ失敗する（黙って通らない）

## 要件・検証の対応

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 1 置く条件と内容 | Task 1 | 3 つの保存先で `cmp` が一致、既存・壊れた symlink・書けない保存先の検査が通る | `bash .devcontainer/test-install-beforehand.bash` |
| 2 雛形の変更が効く | Task 1 | T' と置いたファイルの `load_config` が T' だけと同じで、全役割の期限・全 agent のモデルが T' の値 | 同上（旧挙動で失敗することを Step 2 で確かめる） |
| 3 `check` が通る | Task 1 | `test_shipped_template_passes_check[postcreate]` が通る | `uv run pytest tools/agent_runner/tests/test_cli.py -k shipped_template` |
| 4 文書 | Task 2 | 4 か所の記述が新しい挙動と一致 | `git diff` の確認、`bash .devcontainer/test-readme.bash` |
| 5 全体の検証 | Task 3 | 3 つのコマンドの終了コード 0 | README の「テスト」のコマンド |

共有する条件: 置くファイル（`.devcontainer/agent-runner-personal.toml`）を、postCreate の関数・bash の検査・`test_cli.py` の 3 か所が同じパスで使う。Task 3（統合）で 3 か所のパスが一致することを `git grep` で確かめる。

## 実行方式

`self`（`implement_task.py check` の結果、雛形の既定）。`superpowers:executing-plans`（inline）で、このセッションが Task を順に行う。Task は 3 つで、検査と実装・文書が同じ数ファイルに集まるため（Spec D-167-8）。

## 実行予算

- 全体の能動時間: 150 分（似た規模の #145・#139 の実績は 60〜120 分。全体のテストに 10 分ほどかかる）。ledger: `/workspaces/reso-world/tmp/agents/issue-167.6_cewr0j/budget.jsonl`
- phase の目安: 準備・Spec・Plan 40 分、Task 1 30 分、Task 2 20 分、Task 3（検証）30 分、push・PR 20 分、予備 10 分
- worker: サブエージェント・runner の担当は使わない。長いコマンド（全体の pytest・`run-tests.bash`）は `run_in_background` で起動し、終了コード付きの完了通知で待つ。絶対期限は各 30 分、無進捗の打ち切りは 15 分
- 再試行の上限: 同じ失敗（同じ signature）の再試行は 1 回まで。安全の失敗は再試行しない
- checkpoint: Task の境界、能動時間の 50%（75 分）・100%、検証の失敗の直後
- 縮小・方法変更の候補: bash の検査の中の `load_config` の確認が uv の環境で不安定なら、同じ確認を `tools/agent_runner/tests/test_config.py` に移し、bash 側は `cmp` だけにする。`check-layout.sh` が環境の要因で失敗するなら、原因を示して報告し、この Issue では直さない

---

### Task 1: 最小の個人設定を postCreate が置く

テスト: 要る。postCreate の関数の挙動（写す元）と、置いたファイルが雛形の値を上書きしないことを、関数と `load_config` を実行して確かめる（Issue の検証の指定）。

**Files:**
- Create: `.devcontainer/agent-runner-personal.toml`
- Modify: `.devcontainer/install_beforehand.bash:76-90`（`place_agent_runner_config` とその前のコメント）
- Test: `.devcontainer/test-install-beforehand.bash:31-59`、`tools/agent_runner/tests/test_cli.py:353-369`

**Interfaces:**
- Produces: `.devcontainer/agent-runner-personal.toml`（Task 2 の文書が名前で参照する）

- [ ] **Step 1: `test-install-beforehand.bash` に雛形の変更が効くことの検査を足す**

  保存先の 3 通りのループの後に、1 つ目の保存先（`$tmp/home-empty/.config/agent-runner/config.toml`、ループの中で `user customization` に書き換える前に `$tmp/placed.toml` へ写しておく）を使う。雛形を次のように書き換えた T'（`$tmp/changed.toml`）を作る: `^deadline_seconds = ([0-9]+)$` の値に 1 を足し、`^model = "(.*)"$` の値に `-changed` を付ける。`(cd "$root" && uv run --project "$root" --locked python - <雛形> <T'> <置いたファイル>)` で次を確かめ、どれかが偽なら `fail` する。

  ```python
  base = load_config(template)
  changed = load_config(changed_template)
  merged = load_config(changed_template, placed)
  assert merged == changed
  assert all(merged.roles[name].deadline_seconds == role.deadline_seconds + 1 for name, role in base.roles.items())
  assert all(merged.agents[name].model == agent.model + "-changed" for name, agent in base.agents.items())
  ```

  この Step では、ループの `cmp` の比較先は雛形のままにする。

- [ ] **Step 2: 旧挙動で失敗することを確かめる**

  Run: `bash .devcontainer/test-install-beforehand.bash`
  Expected: FAIL（置いたファイルが雛形の写しなので、`merged` の期限・モデルが変える前の値になる）

- [ ] **Step 3: 最小の個人設定を作り、postCreate の写す元を変える**

  `.devcontainer/agent-runner-personal.toml` を Spec の「最小の個人設定」のとおりに作る（冒頭の 3 行程度の説明、`schema_version = 1`、役割の期限・`[workflows.issue.assignments.implement]` の `agents`・`fallback`・`[workflows.review]` の `after_run = []` の例をコメントで）。`place_agent_runner_config` の `cp` の元を `.devcontainer/agent-runner-personal.toml` に変え、関数の前のコメントに、雛形を写すと雛形の変更が rebuild まで効かないので最小のファイルを置くことを足す。`test-install-beforehand.bash` のループの `cmp` の比較先と、失敗の文言・節の先頭のコメントを新しいファイルに合わせる。

- [ ] **Step 4: `test_cli.py` の検査を置くファイルに合わせる**

  `test_shipped_template_passes_check` の parametrize の `"template-copy"` を `"postcreate"` にし、その場合に `.devcontainer/agent-runner-personal.toml` を `personal.toml` に写す。前のコメントの「postCreate copies the template as the personal config, so the copy must load too.」を、postCreate が置く最小の個人設定と一緒に読めることの説明に直す。

- [ ] **Step 5: 検査が通ることを確かめる**

  Run: `bash .devcontainer/test-install-beforehand.bash`
  Expected: `PASS: postCreate parses, ...`（終了コード 0）

  Run: `uv run --locked pytest tools/agent_runner/tests/test_cli.py -k shipped_template -q`
  Expected: 2 passed

- [ ] **Step 6: Commit**

  ```bash
  git add .devcontainer/agent-runner-personal.toml .devcontainer/install_beforehand.bash \
    .devcontainer/test-install-beforehand.bash tools/agent_runner/tests/test_cli.py
  git commit -m "fix(devcontainer): place a minimal agent-runner personal config instead of the template (#167)"
  ```

### Task 2: 文書を新しい挙動に合わせる

テスト: 要らない。文書とコメントだけの変更（`AGENTS.md` のテストの採用基準「書かない」）。代わりに `git diff` を読み、`bash .devcontainer/test-readme.bash` を実行する。

**Files:**
- Modify: `.devcontainer/README.md:526-532`（agent-runner の節）、`.devcontainer/README.md:568-569`（DSH の節）
- Modify: `tools/agent_runner/interfaces.rst:59`
- Modify: `.devcontainer/agent-runner.toml:2`

**Interfaces:**
- Consumes: Task 1 の `.devcontainer/agent-runner-personal.toml`

- [ ] **Step 1: README の agent-runner の節を直す**

  「雛形 `.devcontainer/agent-runner.toml` を写し、既存の設定は更新しない。…次の postCreate で雛形から作り直される。」を、次の内容にする: postCreate は `.devcontainer/agent-runner-personal.toml`（`schema_version = 1` と上書きの例のコメントだけ）を置き、既存の設定は更新しない。雛形は写さないので、個人設定に書いていない値は雛形を変えるとすぐに効く。個人設定には変えたい値だけを書き、要らなくなったら消す。#167 より前の postCreate が置いた個人設定は雛形の丸写しで、雛形の値をすべて上書きするので、自分の上書きを足していなければ消してよい（rebuild でも置き換わる）。mount していないので rebuild で消え、次の postCreate で作り直される。

- [ ] **Step 2: README の DSH の節を直す**

  「既存の個人 agent-runner 設定は上書きされない。保存済みの agent 定義が古ければ `[agents.dsh-*]` を雛形に合わせるか、確認用 config を `--config` で明示する。」を、個人設定に `[agents.dsh-*]` を書いて上書きしているときは、雛形に合わせるか消すか、確認用 config を `--config` で明示する、という内容にする。

- [ ] **Step 3: `interfaces.rst` と雛形の冒頭のコメントを直す**

  `interfaces.rst` の「雛形をコピーした後も、既存個人設定を導入処理で更新しない。」を、導入処理は個人設定が無いときだけ `.devcontainer/agent-runner-personal.toml` を置き、既存の個人設定は更新しない、雛形は写さないので個人設定に書いていない値は雛形の変更がすぐに効く、という内容にする。雛形の 2 行目のコメントを、個人設定はこの雛形に重ねて読み、postCreate は個人設定が無いときに `agent-runner-personal.toml` を置く（この雛形は写さない）という内容にする。

- [ ] **Step 4: 確かめる**

  Run: `git diff -- .devcontainer/README.md tools/agent_runner/interfaces.rst .devcontainer/agent-runner.toml` を読み、Spec の「文書」の 4 項目と一致することを確かめる。
  Run: `bash .devcontainer/test-readme.bash`
  Expected: 終了コード 0

- [ ] **Step 5: Commit**

  ```bash
  git add .devcontainer/README.md tools/agent_runner/interfaces.rst .devcontainer/agent-runner.toml
  git commit -m "docs(agent-runner): describe the minimal personal config placed by postCreate (#167)"
  ```

### Task 3: 統合の確認

テスト: 新しく書かない。README の「テスト」のコマンドで全体を確かめる。

**Files:** なし（失敗したときだけ、原因の Task のファイル）

- [ ] **Step 1: 共有する条件を確かめる**

  Run: `git grep -n "agent-runner-personal.toml"`
  Expected: `install_beforehand.bash`・`test-install-beforehand.bash`・`test_cli.py` が同じパスを使い、文書の記述と一致する

- [ ] **Step 2: 全体の検証（バックグラウンドで起動し、完了通知の終了コードで判定）**

  Run: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q`
  Expected: どれも終了コード 0。失敗したら `superpowers:systematic-debugging` で調べ、#167 の変更と関係ない環境の要因なら原因を示して報告する

- [ ] **Step 3: 受け入れ条件の照合**

  上の「要件・検証の対応」の各行について、観測した結果（終了コードと出力の要点）を PR 本文に書く。最後のブランチ全体のレビュー（`superpowers:requesting-code-review` の観点で自分が読む）で、Spec の除外範囲に触れていないことを `git diff origin/main --stat` で確かめる

## 実行記録（2026-10-20 JST）

- 実行方式: `superpowers:executing-plans`（inline、担当 `self`）。ledger は `AGENTS.md` の置き場所の規則に合わせて `/workspaces/reso-world/tmp/agents/issue-167.6_cewr0j/progress.md` に置いた（worktree の `.superpowers/sdd` は使わない）
- Task 1（`aee7be2`）: 旧挙動で `test-install-beforehand.bash` が `merged == load_config(changed)` の AssertionError で失敗することを確かめてから実装し、PASS。`test_cli.py -k shipped_template` は 2 passed
- Task 2（`412eb2e`）: 文書 4 か所。`test-readme.bash` は PASS。「すぐに効く」は runner が起動のたびに設定を読むので「次の実行から効く」にした
- Task 3: `run-tests.bash` は 33 件 PASS（EXIT=0）、`check-layout.sh` は EXIT=0（どちらも `412eb2e`）。`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools` は 3213 passed・1 failed（34 分）。失敗した `test_run_roles.py::test_environment_preflight_does_not_launch_or_consume_review[moved-self-review]`（`partial_success`）は、単独 3 回（6 passed×3）とファイル全体（46 passed）で再現しなかった。役割の期限 20 秒に対し全体の実行が通常より大きく遅れた負荷による失敗で、#167 の変更が触れない入力（テスト内の `Config`、存在しない個人設定）なので環境の要因と判断した
- 最後の全体レビュー（新しい文脈のレビュアー、opus）: Critical 0・Important 0・Minor 4。Minor 1（`after_run = []` の例に、止めた後に `finalize-parent`・`attach-runner` を実行する注意が無い）は、全員のホームに置かれる例をそのまま有効にすると PR レビューの結果が保存されないので Important に格付けし直して直した（`8c28737`、コメントだけの変更なのでテストは足さず、`test-install-beforehand.bash`・`test-readme.bash`・`test_cli.py`（39 passed）を再実行）。持ち越し: 例の仮の agent 名のまま外すと `invalid_reference` になる、README に既存の丸写しを確かめる手順が無い、T' が期限とモデルだけを変える
- 能動時間: 約 63 分（ledger の 53 分と、ledger を始める前の準備の約 10 分）。予算 150 分の範囲内
