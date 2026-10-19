# Issue #156 pr-review-fix-loop の移植 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans（この run の実行方式。理由は「実行方式」）。Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移植元 `usaturn/agent-workspace@415b366` の pr-review-fix-loop を、移植先の helper と規則に合わせて `.agents/skills/pr-review-fix-loop/` に取り入れ、この PR で実機の 1 サイクルを回す。

**Architecture:** helper `scripts/loop.py` は移植元を基に、Spec の D-3〜D-12 の適応だけを加える。司令塔の手順は `SKILL.md` と `references/records.md`。テストは偽の `gh`・偽の adapter・一時の Git だけで、loop.py の公開関数と CLI を動かす。

**Tech Stack:** Python 3.14、pydantic 2、pytest（`--import-mode=importlib`）、git、gh、agent-runner（`tools/agent_runner`）

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue156-pr-review-fix-loop-design.md`

- 状態: `draft`
- 実行許可: Spec の冒頭のとおり（利用者の `/issue-to-pr #156 --merge` を「`--merge` 相当」として扱う）
- 参照: #116 の「着手するエージェントへの注意（利用者決定: 2026-10-18）」。判断の基準・三択・修正後の自己レビューは最大 1 回を変えない

## 実行方式

`superpowers:executing-plans`（このセッションが実装する）。issue-to-pr の表の「`self` が true で、同じファイルの逐次変更」に当たる。Task 1・2 はどちらも `loop.py` を変え、テストもその API に結び付く。移植元と移植先の差の調査（Spec の「確認した事実」）を持つ controller が実装し、サブエージェントへ同じ調査を渡し直さない。独立した確認は次の 3 つで行う。

- Task 4: スキル無し・ありの行動の比較（新しいコンテキストのサブエージェント 2 件）
- Task 5: PR の前のブランチ全体のレビュー（新しいコンテキストのレビュアー 1 件）
- Task 6: PR の後の「`--merge` 相当」のサイクル（agent-runner の設定の inspect のレビュアー）

## Global Constraints

- Python は `requires-python = ">=3.14"`。helper は `uv run --project <root> --locked python` で動かす（`tools/devenv` は無い）
- 判断の基準・三択の結論・修正後の自己レビューは最大 1 回は review-fix-planning のまま。loop は採否を決めない
- loop 自身は PR にコメントしない。新しい PR を作らない。force push・`main` への直接の push・admin マージをしない
- `--controller-runtime` は `claude-code`・`devin`・`pi`・`codex`・`cursor`
- 変えないもの: `.agents/skills/review-fix-planning/`・`pr-review/`・`review-verify/`・`issue-to-pr/`、`.agents/scripts/`、`tools/`、`AGENTS.md`、`.devcontainer/`
- テストは偽の `gh`・偽の adapter・一時の Git だけを使う。本物のモデルを起動するのは Task 6 だけ
- テストは `AGENTS.md` の「テストの採用基準」に従う（文言の照合、消えたことの確認、運用で変わる値の写しを書かない）
- 文書は `AGENTS.md` の「日本語表現」に従う

## Review Focus

1. resoloop の PR（`usaturn/resoloop`）では、レビュアーの helper の Git の書き込み先が `external/resoloop` になる。書き込みの例外の `source_git` がそこを指すこと（Task 2 の `test_write_exceptions_name_the_target_checkout_git`）
2. finalize の結果が `merged: true` で、`spec_commit` が文字列でない・SHA の形でない。finalize の結果として読まず終了コード 2（Task 1 の `test_cycle_end_rejects_a_malformed_spec_commit`）
3. 利用者自身の判断の記録が `CONTRIBUTOR` で投稿されている（上流の PR）。認証済みの login で読み、`record_missing` にしない（Task 1 の `test_cycle_end_reads_the_authenticated_users_record`）
4. DSH と DSH 以外の混ざったレビュアー。runner に `sandbox_write_paths` を渡さず、DSH の担当の環境から GitHub の token を外す（Task 2 の `test_review_passes_no_sandbox_grants_and_strips_dsh_tokens`）
5. `gh api user` が空白だけを返す（未認証の環境の形）。記録を読まずに止まる（Task 1 の `test_records_need_the_authenticated_login` のパラメータ）

---

### Task 1: loop.py の移植と、状態・検査のテスト

**テストの要否:** 要る。ロック・状態の順序・判断の記録の照合・扱う PR の範囲・login・`spec_commit` の照合は、コードを実行して確かめる分岐と安全条件である。

**Files:**
- Create: `.agents/skills/pr-review-fix-loop/scripts/loop.py`
- Create: `.agents/skills/pr-review-fix-loop/tests/conftest.py`
- Create: `.agents/skills/pr-review-fix-loop/tests/test_loop_state.py`
- Create: `.agents/skills/pr-review-fix-loop/tests/test_loop_check_options.py`
- Create: `.agents/skills/pr-review-fix-loop/tests/test_loop_herdr_pane.py`

**Interfaces:**
- Produces（Task 2・3・6 が使う）: 移植元と同じ名前の `LoopError(code, stage, reason, *, next_command=None, requires_input=None)`、`GitHub(runner)`（`pull(repository, number) -> PullState`、`comments(repository, number) -> Any`、新しく `login() -> str`）、`start(...)`・`check_options(...)`・`cycle_begin(run_dir, *, github=None)`・`review(run_dir, *, github=None, adapter_loader=load_adapter, tmp_root=None)`・`cycle_end(run_dir, *, finalize_result=None, round_dir=None, role_runs=(), record_file=None, github=None)`・`finish(run_dir, *, abort=None)`・`status(...)`・`recover(...)`・`main(argv)`、定数 `TMP_PREFIX = "create-reso-world-pr-loop-"`・`RUNTIMES = ("claude-code", "devin", "pi", "codex", "cursor")`
- `start` は `hold_action` を受け取らない。`Options` は `max_cycles`・`assign`・`template`・`config`・`fresh_review`。`planning_guidance(run)` は `review_dir`・`pr_url`・`run_roles_options`

- [ ] **Step 1: 移植元のテスト 3 本と conftest を写し、移植先に合わせる**

  - conftest: `REPOSITORY = "usaturn/create-reso-world"`。親の origin は `https://github.com/usaturn/create-reso-world.git`。`review_dir` は `parent/reviews/usaturn/create-reso-world/#900-feature-demo`。`FakeGitHub.runner` は `["gh", "api", "user", "--jq", ".login // empty"]` に `self.login`（既定 `"usaturn\n"`）を返す。`post_record` は `author_association` と `login` を引数で変えられる（既定 `OWNER`・`usaturn`）
  - `test_loop_state.py`・`test_loop_check_options.py` から `hold_action` の場面を外す（`test_start_records_options_and_effective_assignments` の `hold_options` の parametrize、`test_status_returns_the_next_command_after_a_restart` の parametrize、check-options の `options` の期待値）
  - URL の大文字小文字のテストは `https://github.com/Usaturn/Create-Reso-World/pull/900`

- [ ] **Step 2: 移植先で足す挙動のテストを書く**

  - `test_start_refuses_a_pr_whose_checkout_cannot_be_resolved`: 偽の gh が `usaturn/resoloop-meshy` の PR を返す。`start("https://github.com/usaturn/resoloop-meshy/pull/900")` が `(2, "arguments")` で止まり、`reviews/usaturn/resoloop-meshy/.../loop` を作らない
  - `test_records_need_the_authenticated_login`（parametrize: 失敗の終了コード 1、空の出力、空白だけ）: `cycle_begin` が `(5, "github")` で止まりサイクルを作らない。`cycle_end` も同じ login の失敗で `(5, "github")`、サイクルは `planning` のまま
  - `test_cycle_end_reads_the_authenticated_users_record`: 記録を `author_association="CONTRIBUTOR"`・`login="usaturn"` で投稿すると `cycle_end` が受け付ける。`login="someone-else"` の `CONTRIBUTOR` は読まず `record_missing`
  - `test_cycle_end_accepts_a_spec_commit_merge`: no_fix_needed の記録の後、PR の branch に commit S を足してマージした状態で、`{"outcome": "no_fix_needed", "merged": true, "issues": [], "spec_commit": S}` を渡すと `outcome == "no_fix_needed"`・`merged is True`。S と違う SHA を渡すと `(4, "merge_mismatch")`
  - `test_cycle_end_rejects_a_malformed_spec_commit`（parametrize: `None`・`123`・`"abc"`・大文字の 40 桁）: `(2, "arguments")`

- [ ] **Step 3: テストを実行して失敗を確かめる**

  Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests -q`
  Expected: loop.py が無いので収集で失敗する

- [ ] **Step 4: loop.py を移植する**

  移植元の `loop.py` を写し、次だけを変える（Spec の判断の番号）。
  - D-12: `command()` は `uv run --project str(ROOT) --locked python str(HELPER) ...`
  - D-5: `RUNTIMES` から `grok-build` を外す
  - D-4: `Options.hold_action`、`check_options` と `start` の `hold_action`、CLI の `--hold-action`、`planning_guidance` の `hold_action` を外す
  - D-11: `TMP_PREFIX = "create-reso-world-pr-loop-"`、`LEGACY_TMP_PREFIXES` を外し、回収の名前の確認は `TMP_PREFIX` だけ
  - D-3: `resolve_pr` から `require_planning_owner` を外す。`_target_error` は移植先の終了コード（2・11 → `arguments`、7 → `parent`、ほか → `github`）。`start` は `github.pull` の後、ロックの前に `target.target_checkout(root, pull.repository)` を呼び、`TargetError` を `LoopError(2, "arguments", ...)` にする（理由に、loop は CODE_ROOT を受け付けず create-reso-world と ResoLoop の PR だけを扱うことを書く）
  - D-9: `GitHub.login() -> str` は `gh api user --jq '.login // empty'` の出力を strip し、失敗・空で `LoopError(5, "github", ...)`。`_read_records` は `trusted_login=github.login()` を `read_state` に渡し、その login を返す。`cycle_end` の読み直し（`exclude_comment_ids`）にも同じ login を渡す
  - D-10: `_read_finalize` は `spec_commit` があれば `[0-9a-f]{40}` か `[0-9a-f]{64}` の文字列だけを受け付ける。`cycle_end` の `merged` の照合は、`spec_commit` があれば PR の head が `spec_commit`、無ければサイクルの HEAD
  - モジュールの docstring とコメントの移植元固有の語（`tools/devenv`、`verify-devenv.sh`、`agent-workspace`）を移植先に合わせる

- [ ] **Step 5: テストを実行して通ることを確かめる**

  Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests -q`
  Expected: PASS

- [ ] **Step 6: Commit**

  ```bash
  git add .agents/skills/pr-review-fix-loop/scripts/loop.py .agents/skills/pr-review-fix-loop/tests
  git commit -m "feat(pr-review-fix-loop): port loop.py with state and option checks (#156)"
  ```

### Task 2: レビュアーの起動・検査・回収と、DSH の親の準備・確定

**テストの要否:** 要る。レビュアーの結果の検査、1 回だけの再実行、資源の回収、DSH の親の準備・確定、書き込みの例外は、コードを実行して確かめる安全条件である。

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/scripts/loop.py`（`review_write_exceptions`・`_review_batch` の起動の引数）
- Create: `.agents/skills/pr-review-fix-loop/tests/test_loop_review.py`
- Create: `.agents/skills/pr-review-fix-loop/tests/test_loop_reviewer_protocol.py`

**Interfaces:**
- Consumes: Task 1 の公開関数
- Produces: `review_write_exceptions(run: RunRecord) -> tuple[str, ...]`（DSH 以外のレビュアーの例外。`source_git` は `target.target_checkout(parent, run.pr.repository).root` の Git の共通ディレクトリ）。`run_workflow` には常に `sandbox_write_paths=()` を渡す

- [ ] **Step 1: 移植元の `test_loop_review.py` を写し、移植先に合わせる**

  - `test_dsh_review_grants_only_artifacts_and_regular_save_lock` は写さない（D-8）
  - `dsh_parent_env` は PR を `usaturn/create-reso-world` にし、`GIT_CONFIG_*` の insteadOf の値を `https://github.com/usaturn/create-reso-world.git` にする
  - `staged_reviewer` は移植先の DSH の子の形にする: 依頼の `prompt` に `parent_pr_data` があり、`prepare` の `temp_root` は attempt の `dsh/tmp`、本文の冒頭は `- レビュアー: actual/model（ランタイム: dsh）`、下書きは prepare が返す outbox の `review.md`・`findings.json`、attempt の `stdout.log` に outbox への write の tool_call と結果の記録を書く（移植先の `.agents/skills/pr-review/tests/test_review_run.py` の `staged_batch` と同じ形）
  - `test_cleanup_output_accepts_current_and_legacy_prefixes` は、`TMP_PREFIX` を回収し、ほかの名前を残すことだけを確かめる形にする（旧接頭辞は持ち込まない）
  - 移植元の `agent-workspace-pr-loop-` の名前は `loop.TMP_PREFIX` を使う

- [ ] **Step 2: 移植先で足す挙動のテストを書く**

  - `test_write_exceptions_name_the_target_checkout_git`: create-reso-world の PR では例外に親の `.git` が入り、`external/resoloop`（origin が usaturn/resoloop、upstream が orange3134/resoloop の一時の checkout）を置いた親で `usaturn/resoloop` の PR では `external/resoloop/.git` の行が入る
  - `test_review_passes_no_sandbox_grants_and_strips_dsh_tokens`: `run_workflow` を差し替えて受け取った引数を記録する。alpha を DSH にした設定で `sandbox_write_paths == ()`、DSH の担当の `env` に `GH_TOKEN`・`GITHUB_TOKEN` が無く、`write_exceptions` が `review_write_exceptions(run)` と同じ

- [ ] **Step 3: `test_loop_reviewer_protocol.py` を写す**

  tool_root の写しに `scripts/superpowers_context.py` と、それが読み込む同じ checkout のファイルを足す。偽の gh は移植先の `prepare` が呼ぶ形だけに答える。実際の helper の `prepare` → 下書きの記入 → `complete` が、宣言した例外の中だけに書くことを確かめる（移植元と同じ判定）

- [ ] **Step 4: テストを実行して失敗を確かめる**

  Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests/test_loop_review.py .agents/skills/pr-review-fix-loop/tests/test_loop_reviewer_protocol.py -q`
  Expected: Step 2 の 2 件が失敗する（`review_write_exceptions` の引数・`source_git`、`sandbox_write_paths`）

- [ ] **Step 5: `review_write_exceptions(run)` と `_review_batch` を直す**

  移植元の `review_write_paths` を外し、`run_workflow(..., sandbox_write_paths=(), write_exceptions=review_write_exceptions(run))`。`review_write_exceptions` は `helper_write_exceptions(tool_root=..., parent=..., parent_git=..., review_dir=..., number=..., source_git=<target checkout の Git の共通ディレクトリ>)` に移植元の 1 行を足す

- [ ] **Step 6: テストを実行して通ることを確かめる**

  Run: `uv run pytest .agents/skills/pr-review-fix-loop -q` と `env AGENT_RUNNER_DEPTH=1 uv run pytest .agents/skills/pr-review-fix-loop -q`
  Expected: どちらも PASS

- [ ] **Step 7: Commit**

  ```bash
  git add .agents/skills/pr-review-fix-loop
  git commit -m "feat(pr-review-fix-loop): run reviewers with the target pr-review and DSH rules (#156)"
  ```

### Task 3: SKILL.md・records.md・symlink・手順のテスト・監視の文書

**テストの要否:** 手順のテストは 1 件だけ書く。`disable-model-invocation: true` は、push・マージまで進むスキルをモデルが自分で起動しないための権限の固定値で、`AGENTS.md` の「安全な操作範囲・権限…を守るための固定値は使ってよい」に当たる。文書の文面・参照先はテストにせず、Step 4 の構造の確認で代える。

**Files:**
- Create: `.agents/skills/pr-review-fix-loop/SKILL.md`
- Create: `.agents/skills/pr-review-fix-loop/references/records.md`
- Create: `.agents/skills/pr-review-fix-loop/tests/test_pr_review_fix_loop_skill_contract.py`
- Create: `.claude/skills/pr-review-fix-loop`（`../../.agents/skills/pr-review-fix-loop` への相対 symlink）
- Modify: `.agents/monitoring-runtimes.md`（対応表の pi の行、注記の最後の項目）

- [ ] **Step 1: SKILL.md を書く**（Spec の D-13）

  移植元の節の構成を保つ。frontmatter は `name`・`description`（日本語）・`disable-model-invocation: true`・`argument-hint: "<PR番号またはURL> [--max-cycles N] [--assign ROLE=AGENT[,AGENT]] [--template PATH] [--config PATH] [--fresh-review]"`。起動のコマンドは `uv run --project "$TOOL_ROOT" --locked python "$TOOL_ROOT/.agents/skills/pr-review-fix-loop/scripts/loop.py" start ...`、`TOOL_ROOT` は親の main checkout（`agent_tmp.py root`）。計画は review-fix-planning の完遂（Hold の方針を書かない）。`cycle-end` の引数（`--role-run`・`--finalize-result`・`--round-dir`・`--record-file`）、create-reso-world の PR の結論 2 は finalize.py の `--spec-commit`、扱う PR（D-3）

- [ ] **Step 2: references/records.md を書く**

  移植元の 1〜6 章を保ち、`options` から `hold_action` を外し、runner の出力先を `${TMPDIR:-/tmp}/create-reso-world-pr-loop-XXXXXX/` にし、`cycle-end` の `merged` の照合（`spec_commit`）と、記録を読むときの認証済みの login を書く

- [ ] **Step 3: 手順のテストと symlink と monitoring-runtimes.md**

  - `test_loop_skill_runs_only_when_explicitly_invoked`: frontmatter の行に `disable-model-invocation: true` がある（防ぐ誤りと、値を変えるときにテストも直すことをコメントに書く）
  - pi の行の「完了」に `loop.py review` の foreground 実行（bash ツールの `timeout` を付けない）と標準出力の JSON・終了コードの確認、「OR 待機の組み方」に中断・保持の回収（`loop.py status`・`recover --operator-confirmed-stopped`）を足す。注記の最後の文を「pi の行は、bash ツールの foreground 実行と `task_watch.py`、PR 修正ループの `loop.py review` の同期実行という、このリポジトリで確認済みの仕組みだけを書く」にする

- [ ] **Step 4: 確かめる**

  Run: `uv run pytest .agents/skills/pr-review-fix-loop -q`、`bash scripts/check-layout.sh`
  Expected: PASS。加えて、SKILL.md・records.md が参照する `scripts/`・`references/`・`.agents/skills/review-fix-planning/references/execution.md` などのパスが実在することを `ls` で確かめ、結果を ledger に書く

- [ ] **Step 5: Commit**

  ```bash
  git add .agents/skills/pr-review-fix-loop .claude/skills/pr-review-fix-loop .agents/monitoring-runtimes.md
  git commit -m "docs(pr-review-fix-loop): add the skill, records and pi monitoring notes (#156)"
  ```

### Task 4: スキル無し・ありの行動の比較

**テストの要否:** 不要（文書の評価）。代わりに、新しいコンテキストのサブエージェント 2 件（スキル無し・あり）に同じ場面を答えさせ、差を記録する（`superpowers:writing-skills`）。

**Files:**
- Create: `.agents/skills/pr-review-fix-loop/evals/2026-10-20-issue156-behavior.md`

- [ ] **Step 1: 場面を決める**

  A: `cycle-begin` が `reuse` を返した後の次の操作。B: レビュアー 1 人が `rejected`（`rejected_stage: payload`）で `next` が `review`。C: `finish` が終了コード 7 を返し、利用者がロックを消してほしいと言う。D: create-reso-world の PR で修正不要と判断した後の、Spec の commit・投稿・finalize・`cycle-end` の順。E: 利用者が移植元の癖で `--hold-action fix` を付けて起動を頼む

- [ ] **Step 2: 2 件を同じモデル・同じ場面で実行する**（スキルありには SKILL.md と records.md の全文を読ませる）
- [ ] **Step 3: 差と、スキルの文面を直す必要の有無を記録する**。判断が規則と食い違ったら SKILL.md を直し、もう一度ありで確かめる
- [ ] **Step 4: Commit**

### Task 5: 全体の検証・ブランチ全体のレビュー・PR

**テストの要否:** 新しいテストは書かない。全体の検証とレビュー。

- [ ] **Step 1: 全体の検証**

  Run: `uv run pytest tests/skills .agents/skills .agents/scripts tools -q`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`env AGENT_RUNNER_DEPTH=1 uv run pytest .agents/skills/pr-review-fix-loop -q`
  Expected: すべて終了コード 0。件数はベースライン（`8f5074a`）より増える

- [ ] **Step 2: ブランチ全体のレビュー**（新しいコンテキストのレビュアー 1 件。Spec・Plan・差分を渡し、要件の対応・回帰・テストの採用基準を見る）。指摘は Spec の判断の基準（致命的か）で選別し、直したら Step 1 をやり直す
- [ ] **Step 3: Spec・Plan に実行の記録（受け入れ条件と証拠、検証、所要時間）を書いて commit**
- [ ] **Step 4: push の前の検査と push、PR の作成**（issue-to-pr の 5 章。`Closes #156`）

### Task 6: PR の後の「`--merge` 相当」のサイクル（実機の 1 サイクル）

Spec の D-17 のとおり。本物のレビュアー（agent-runner の設定の inspect）を起動する。

- [ ] **Step 1: `start`**: feature worktree の `loop.py start <PR の URL> --controller-model claude-opus-5-5 --controller-runtime claude-code`。`warnings`・`herdr_pane` を記録する
- [ ] **Step 2: サイクル**: `cycle-begin` → `review`（Bash の `run_in_background: true` で終了の通知を待つ）→ 親の main checkout の review-fix-planning の完遂（`planning.review_dir`、`run_roles.py` に `planning.run_roles_options`）→ `cycle-end`
- [ ] **Step 3: 終わり方**: `no_fix_needed` なら finalize.py（`--spec-commit`）がマージし、`cycle-end --finalize-result --round-dir` → `finish`。`fixes_pushed` なら次のサイクル（最大 3 回）。`stopped`・上限は止まって報告する
- [ ] **Step 4: 記録**: #156 に run の記録（run ID、サイクルごとの HEAD・レビュアーの状態・判断の記録・結果）をコメントし、#116・#158 に申し送りをコメントし、予約を解放する

## 要件の対応（実装前の照合）

| Spec の条件 | 担当 Task | 観測する結果 | 確かめ方 |
| --- | --- | --- | --- |
| D-3 扱う PR | 1 | 決まらない PR を lock の前に `(2, arguments)` | `test_start_refuses_a_pr_whose_checkout_cannot_be_resolved` |
| D-4 `--hold-action` を持たない | 1・3 | `Options` に無い、CLI が受け付けない | 移植したテストの `options` の期待値、SKILL.md の起動の節 |
| D-6 依頼文 | 2 | 実際の helper が宣言した例外の中で完了する | `test_loop_reviewer_protocol.py` |
| D-7 書き込みの例外 | 2 | `source_git` が target checkout の Git | `test_write_exceptions_name_the_target_checkout_git` |
| D-8 DSH の起動 | 2 | 許可は空、token を外す、親の準備・確定 | `test_review_passes_no_sandbox_grants_and_strips_dsh_tokens`、DSH の親のテスト |
| D-9 login | 1 | 取得の失敗で止まる、`CONTRIBUTOR` の自分の記録を読む | Review Focus 3・5 のテスト |
| D-10 `spec_commit` | 1 | S のマージを受け付け、食い違いを拒否 | Step 2 のテスト |
| D-11・D-12 | 1・2 | 接頭辞・コマンド | 移植した回収と `next` のテスト |
| D-13・D-14 | 3・4 | 手順の文書と監視の表 | 構造の確認、行動の比較 |
| D-17 実機 | 6 | 1 サイクル以上の記録 | `<review_dir>/loop/<run_id>/`、#156 のコメント |

共有する条件: 判断の記録の読み方（login）と `finalize.py` の結果の形は、review-fix-planning（#155）と共有する。Task 1 が `finalize.py` の実際の結果の形（`spec_commit` を含む）で照合を確かめ、Task 6 が実際の finalize.py の結果で `cycle-end` を通す。

## 実行予算

`.agents/execution-budget.md` に従う。ledger: `/workspaces/reso-world/tmp/agents/issue-156.vtjmipf1/budget.jsonl`（2026-10-19 15:20Z 開始。着手は 15:08Z）。

- Issue 全体の能動時間の予算: 480 分。根拠: #155（移植のコード約 1,500 行）は PR の作成まで約 2 時間 35 分、サイクル 1 回で約 1 時間。#156 は loop.py 2,139 行とテスト約 3,000 行
- phase の目安: 準備・Spec・Plan 90 分、Task 1 90 分、Task 2 90 分、Task 3 45 分、Task 4 30 分、Task 5 45 分、Task 6 は 1 サイクル 60〜90 分
- worker の期限: runner のレビュアーは役割の期限 2700 秒（停止の猶予を足して約 50 分）。implement の担当は 5400 秒。サブエージェント（評価・レビュー）は 30 分で、無進捗 15 分なら打ち切る
- 再試行の上限: 同じ失敗の再試行は 1 回。安全の失敗は再試行しない
- checkpoint: phase の境界、予算の 50%・100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) `test_loop_reviewer_protocol.py` が移植先の helper の前提（fetch・bundle・保存のロック）で動かせなければ、`prepare` の失敗までの検査に縮め、残りを持ち越し候補にする。(2) DSH の staged の再開のテストが移植先の DSH の形で組めなければ、`finalize_parent_batch` の呼び出しと再開の分岐だけを偽の関数で確かめる。(3) Task 6 のサイクルが上限に達したら、マージせず未完了として報告する

## Contingency

- 移植先の helper の挙動が Spec の「確認した事実」と違ったら、意味を保つ最小の修正をして ledger と Spec の決定記録に書く。意味を変える必要があれば止まって報告する
- 移植したテストが移植先の前提（例: `gh` の呼び方、DSH の outbox）で落ちたら、systematic-debugging で原因を確かめてから、テストの fixture を移植先の形に合わせる。挙動の保証を狭めて通さない
- 本物のレビュアーの起動の失敗（認証待ち・クレジット切れ・`response_failed`）は loop の判定（`rejected`）どおりに扱い、全員が失敗したら `finish --abort` で止まる
