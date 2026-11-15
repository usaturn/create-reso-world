# review-eval 収集の保存点への接続（#357）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- Spec: commit `f3716fc1` 時点の版（reflected sha256 `fa0753ca8538284d1ad66d0a30d6fa9a9580f1da5f23ebcdb30c9b74625f5080`）
- 状態: `draft`（issue-to-pr の run の実行許可で実行する。内容の承認ではない）
- **Goal:** 4 経路 7 関数の保存点から `tools/review_eval` の収集を呼び、有効時だけ記録を store へ写し、無効時と失敗時に helper の結果・終了コード・標準出力を変えない。
- **Architecture:** `--project` で動く helper は関数内の遅延 import で `capture.collect` を in-process に呼ぶ。`--no-project` でも動く `upsert_pr_comment.py`・`review_findings.py` は `tools/review_eval/shim.py` をファイルパスで読み込み、`run_hook` で subprocess の `hook` を起動する。どの呼び出しも `except Exception` で囲み、戻り値を使わない。
- **Tech Stack:** Python 3.14（uv、`--locked`）、pytest、pydantic（in-process 側のみ）。
- **Spec:** `docs/superpowers/specs/2026-11-15-issue-357-review-eval-hooks-design.md`

## Global Constraints

- 変更してよいファイルは Issue #357 の「変更してよいファイル」と、5 つの tests ディレクトリの `conftest.py`（Spec D5）に限る。`tools/review_eval/**`・root `conftest.py`・`tools/test_support/` は変えない
- helper の結果 JSON・終了コード・標準出力・既存の保存処理は変えない。収集は保存の後、標準出力に書く前に呼ぶ
- `capture.collect` はキーワード引数だけで呼ぶ。route は `pr-review`・`pr-review-fix-loop`・`review-fix-planning`・`review-verify`
- 仮想パスは `@finalize/<HEAD 12 桁>/result.json` と `@pr-comment/round-<round>/record.json` の形
- `attach-runner` は `deadline = time.monotonic() + 30.0` を全 review_dir で共有し、`allow_runner_child=True`
- shim に渡すパスは `resolve()` した絶対パス。`REVIEW_EVAL_CONFIG` が空でない相対パスなら、呼ぶ前に `os.environ` を絶対パスに置き換える
- テストは `tmp_path` の一時 config と store だけを使い、実 PR・ネットワーク・秘密値・モデル本文を使わない。記録本文に複数行と日本語を含める
- Python は `uv run --locked` で実行し、`python3` を直接使わない
- 必須の保存点は 7 関数・13 event（`prepare`・`complete`・`fail`・`attach-runner`・`accept`・`validate`・`finalize`・`run_roles`・`post`・`review`・`cycle_end`・`finish`・`recover`）。各 event の接続を、呼び出しを記録する偽の `collect`（shim 経路は偽の `run_hook`）で、helper の `main` かサブコマンドの dispatch を通して 1 件ずつ確かめる（重い本体は差し替えてよい）
- 有効時の collection テストは、テストファイル内の fixture で `monkeypatch.delenv("AGENT_RUNNER_DEPTH", raising=False)` する（実装担当は runner の子で pytest を動かす）。runner の子を確かめるテストだけが明示的に設定する

## 受け入れ基準

- 動作環境: Dev Container（Ubuntu 26.04）の feature worktree の root で `uv run --locked pytest`。review-eval は既定で無効
- 実入力: review_dir の `<model>.md`（複数行・日本語）・`findings/*.json`・`runs/*.json`・`verified/*.json`・`verified/*.planning.json`・`loop/<run_id>/run.json`・`cycle-<n>.json`、`unprotected_changes` の無い古い `dispatch.json`、finalize の結果 JSON、判断の記録 JSON（`review-records/v2`）
- 防御範囲
  - 書かない: 設定なし・`enabled = false`・`REVIEW_EVAL_CONFIG=""`・store 未初期化・`sources` で対象外・runner の子（`attach-runner` 以外）・期限超過
  - 写す（反例）: 有効な設定と初期化済み store。`attach-runner` は `AGENT_RUNNER_DEPTH` があっても写す
  - `collect` が例外を投げても helper の終了コード・標準出力は収集なしと同じ
- テストの採用基準: 下の collection テストは S（壊れてもエラーにならず、無効時に黙って書く・有効時に黙って写さない・期限超過や例外で結果が変わる損害を防ぐ）。各経路で「有効で写る」「無効で書かず結果同じ」を代表の 1 件ずつにし、組み合わせを網羅しない（D）。conftest の隔離 fixture 自体はテストしない（壊れると既存テストの実行時に利用者設定を読む危険はあるが、collection テストの無効ケースが代表で確かめる）

## Review Focus

1. 相対パスの `REVIEW_EVAL_CONFIG`・相対の `--records-file`: shim の子が `cwd=tool_root` で解決し直して黙って disabled になる → Task 3・2 の shim テストで絶対パスになることを確かめる
2. review_dir の外（`workspace_root/reviews` の外）の保存先: `out_of_scope` で何も書かず結果が同じ → 各経路の無効側テストで `REVIEW_EVAL_CONFIG=""` を代表にし、Task 1 で out_of_scope を 1 件
3. 記録の `round`・`reviewed_head` が無い・不正: その仮想記録を渡さず例外にしない → Task 3 で 1 件
4. loop の `LoopError` 経路: 保存した記録を収集し、終了コードは元のまま → Task 4 で 1 件
5. 収集が遅い（scanner の待ち）: attach-runner の 30 秒枠 → Task 1 の期限テスト

## 共通のテスト補助（各 Task のテストファイル内に書く。共通ファイルは作らない）

- `write_collection_config(path, store=..., workspace_root=tmp_path, repos=["usaturn/create-reso-world"])`（`tools.review_eval.tests.support`）で有効な設定を書き、`Store.init(store)`（`tools.review_eval.store`。名前は実装を読んで合わせる）で初期化する
- review_dir は `tmp_path/"reviews/usaturn/create-reso-world/#900-feature-demo"`
- store に写ったかは `Store.open(store).observations("usaturn/create-reso-world", 900)` の path 一覧で確かめる
- 無効のケースは `monkeypatch.setenv("REVIEW_EVAL_CONFIG", "")` と、store ディレクトリに observation が増えないこと
- 各 collection テストファイルに autouse の fixture を置き、`HOME`・`XDG_CONFIG_HOME` を `tmp_path` の下の一時ディレクトリに、`AGENT_RUNNER_DEPTH` を `delenv` する
- 5 つの tests ディレクトリの `conftest.py`（`review-fix-planning/tests` と `.agents/scripts/tests` は新規）に、`REVIEW_EVAL_CONFIG` を空文字にする autouse の fixture を足す（既存テストに利用者の設定を読ませない。Spec D5）

---

### Task 1: pr-review（`review_run.py`）

**Files:**
- Modify: `.agents/skills/pr-review/scripts/review_run.py`（`collect_outputs` の追加と `main` からの呼び出し）
- Modify: `.agents/skills/pr-review/tests/conftest.py`（`REVIEW_EVAL_CONFIG=""` の autouse fixture）
- Create: `.agents/skills/pr-review/tests/test_review_run_collection.py`

**Interfaces:**
- Produces: `collect_outputs(command: str, parent: Path | None, state: Mapping[str, Any] | None, result: Mapping[str, Any], *, deadline: float | None = None) -> None`。`command` は `prepare`・`complete`・`fail`・`attach-runner`。例外を出さない

- [ ] Step 1: テストを書く
  - `test_complete_copies_saved_outputs_when_enabled`: review_dir に `<model>.md`（複数行・日本語）・`findings/m-<12>.json`・`runs/<x>.json` を置き、`result = {"run_record": <runs の絶対パス>, "review_file": ..., "findings_file": ...}` で `collect_outputs("complete", ...)` → store の observation の path に 3 つが入る
  - `test_disabled_writes_nothing_and_main_output_unchanged`: `REVIEW_EVAL_CONFIG=""` で `main(["attach-runner", "--result", <偽の result.json>])` 相当を、`collect_outputs` を差し替えない場合と `capture.collect` が例外を投げる差し替えの場合で実行し、標準出力と終了コードが同じ・store に何も無い
  - `test_attach_runner_shares_deadline_and_skips_after_expiry`: 2 つの review_dir の run record を `attached` に含む結果で、`time.monotonic` を 1 つ目の収集の後に 31 秒進める差し替え → 2 つ目の review_dir の記録は store に無く、例外にならない。最初の呼び出しに渡った `deadline` が呼び出し時点 +30.0 であること
  - `test_attach_runner_collects_in_runner_child`: `AGENT_RUNNER_DEPTH=1` で `attach-runner` の収集が写る（`allow_runner_child=True`）。同じ環境の `complete` は写らない
  - `test_save_points_call_collect`（`prepare`・`complete`・`fail`・`attach-runner` の 4 event）: 偽の `collect` で、`main([...])` の各分岐（`args.handler`・`attach_runner` は差し替えてよい）が `route="pr-review"`・正しい `event`・review_dir を渡す
- [ ] Step 2: `uv run --locked pytest .agents/skills/pr-review/tests/test_review_run_collection.py -q` → FAIL（`collect_outputs` が無い）
- [ ] Step 3: 実装。`main` の各分岐で `print` の前に `collect_outputs(args.command, parent, state, result)` を呼ぶ。`attach-runner` は `result["attached"] + result["unchanged"]` の run record を `Path(p).parent.parent` で review_dir ごとにまとめ、共有の deadline を過ぎたら残りを呼ばない。他は `run_record`（絶対パス）の 2 つ上。無ければ `complete` の成功結果の `review_file`（絶対パス）の親。`prepare` の `review_file` は basename なので使わず、絶対パスを決められなければ呼ばない。`prepare` は `files=()` で sweep だけ
- [ ] Step 4: `uv run --locked pytest .agents/skills/pr-review/tests -q` → PASS
- [ ] Step 5: commit `feat(pr-review): collect review records at review_run save points (#357)`

### Task 2: review-verify（`dispatch.py`・`review_findings.py`）

**Files:**
- Modify: `.agents/skills/review-verify/scripts/dispatch.py`（`collect_accepted`）
- Modify: `.agents/scripts/review_findings.py`（`_collect_before_replacement`）
- Modify: `.agents/skills/review-verify/tests/conftest.py`、Create: `.agents/scripts/tests/conftest.py`（隔離 fixture）
- Create: `.agents/skills/review-verify/tests/test_review_verify_collection.py`

**Interfaces:**
- Produces: `collect_accepted(review_dir: Path, files: Sequence[Path], verifier: Mapping[str, Any] | None) -> None`、`_collect_before_replacement(path: Path) -> None`

- [ ] Step 1: テストを書く
  - `test_accept_copies_fix_check_when_enabled`: 既存の `test_dispatch.py` の accept 用 fixture を参考に、`unprotected_changes` を持たない `batch` の `dispatch.json` で `main(["accept", "--run-dir", ...])` → 終了コード 0、`verified/<12>.fix-check.json` と `.statement-candidates.json` が store に入る
  - `test_accept_disabled_output_unchanged`: `REVIEW_EVAL_CONFIG=""` で同じ入力 → 標準出力・終了コードが同じで store に何も無い
  - `test_validate_hooks_absolute_review_dir`: `shim.run_hook` を記録する偽物に差し替え、`verified/` の中の有効な文書で `review_findings.main(["validate", <相対パス>])` → 終了コード 0、`run_hook` に `route="review-verify"`・`event="validate"`・絶対パスの `review_dir`・絶対パスの `tool_root` が渡る。`verified/` の外のファイルと、検査に失敗したファイル（終了コード 65）では呼ばれない
  - `test_accept_calls_collect`: 偽の `collect` で `dispatch.main(["accept", ...])` が `route="review-verify"`・`event="accept"`・review_dir を渡す
- [ ] Step 2: 実行して FAIL を確かめる
- [ ] Step 3: 実装。`dispatch.main` の accept 成功分岐で `print` の前に呼ぶ。`review_findings.main` の `validate` 成功後（`return 0` の前）に呼ぶ。shim は `Path(__file__).resolve().parents[2] / "tools/review_eval/shim.py"` を `importlib.util.spec_from_file_location` で読み込む
- [ ] Step 4: `uv run --locked pytest .agents/skills/review-verify/tests .agents/scripts/tests -q` → PASS
- [ ] Step 5: commit `feat(review-verify): collect accepted and pre-replacement records (#357)`

### Task 3: review-fix-planning（`finalize.py`・`run_roles.py`・`upsert_pr_comment.py`）

**Files:**
- Modify: `.agents/skills/review-fix-planning/scripts/finalize.py`（`collect_result`）
- Modify: `.agents/skills/review-fix-planning/scripts/run_roles.py`（`collect_review_dir`、`main` の `finally`）
- Modify: `.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py`（`collect_round_record`）
- Create: `.agents/skills/review-fix-planning/tests/conftest.py`、`.agents/skills/review-fix-planning/tests/test_planning_collection.py`

**Interfaces:**
- Produces: `collect_result(record: Mapping[str, Any], record_file: Path, result_file: Path, result: Mapping[str, Any], *, spec_commit: str | None) -> None`、`collect_review_dir(planning_file: Path | None, phase: str) -> None`、`collect_round_record(repo: str, pr: int, records_file: Path | None, result: Mapping[str, Any]) -> None`

- [ ] Step 1: テストを書く
  - `test_finalize_result_copied_as_virtual_record`: `collect_result` を、`reviewed_head` 40 桁・`pr{repository, number=900}`・`round=2` の記録と結果ファイルで、`spec_commit=None`・結果に `comment` ありで呼ぶ → store に `@finalize/<12>/result.json` と `@pr-comment/round-2/record.json`。`spec_commit` ありでは `@pr-comment` が無い
  - `test_finalize_skips_virtual_record_without_round_or_head`: `round` の無い記録 → 例外にならず `@pr-comment` を渡さない
  - `test_run_roles_finally_collects_planning_dir`: `collect_review_dir(<review_dir>/verified/<12>.planning.json, "self-review")` → planning.json が store に入る。`None` では何もしない。`run_roles.main` が入力不正で終了コード 2 になる経路でも `finally` で呼ばれ、終了コードが変わらない（`collect_review_dir` の差し替えで呼び出しを記録）
  - `test_upsert_hooks_absolute_record_path`: `run_hook` を偽物に差し替え、相対の `--records-file` と相対の `REVIEW_EVAL_CONFIG` で `collect_round_record` → `records=[("@pr-comment/round-2/record.json", <絶対パス>)]`・`repository`・`pr=900` が渡り、`os.environ["REVIEW_EVAL_CONFIG"]` が絶対パスになる。`records_file=None` では呼ばれない
  - `test_save_points_call_collect`（`finalize`・`run_roles`・`post`）: 偽の `collect`／`run_hook` で、`finalize.main`（`finalize` 関数は差し替え）・`run_roles.main`（`run` は差し替え）・`upsert_pr_comment.main`（`upsert` は差し替え）が `route="review-fix-planning"` と各 event を渡す
  - `test_planning_disabled_writes_nothing`: `REVIEW_EVAL_CONFIG=""` で `collect_result` と `collect_review_dir` → store に何も無い
- [ ] Step 2: 実行して FAIL を確かめる
- [ ] Step 3: 実装。`finalize.main` は結果を保存した後（`os.replace` の後）に呼ぶ（終了コード 2 の経路では呼ばない）。`finalize.py` は関数内で repo root（`parents[4]`）を `sys.path` に足してから import する。`upsert_pr_comment.main` は `upsert` の成功後、`json.dump` の前に呼ぶ
- [ ] Step 4: `uv run --locked pytest .agents/skills/review-fix-planning/tests -q` → PASS
- [ ] Step 5: commit `feat(review-fix-planning): collect finalize, role and round records (#357)`

### Task 4: pr-review-fix-loop（`loop.py`・`records.md`）

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/scripts/loop.py`（`collect_records` と `dispatch` の `try/finally`）
- Modify: `.agents/skills/pr-review-fix-loop/references/records.md`（「収集の保存点」の 1 節）
- Modify: `.agents/skills/pr-review-fix-loop/tests/conftest.py`（隔離 fixture）
- Create: `.agents/skills/pr-review-fix-loop/tests/test_loop_collection.py`

**Interfaces:**
- Produces: `collect_records(event: str, run_dir: Path, *, record_file: Path | None = None, finalize_result: Path | None = None) -> None`（`event` は `review`・`cycle_end`・`finish`・`recover`。run と cycle は `run_dir` から読み直す。読めなければ sweep だけ）

- [ ] Step 1: テストを書く（既存の `conftest.py` の一時 Git・偽の gh の fixture を使う）
  - `test_cycle_end_copies_records_and_virtual_records`: 既存の cycle-end の正常系の流れで `--record-file`・`--finalize-result` を渡す → store に `loop/<run_id>/cycle-1.json`・`run.json`・`@pr-comment/round-<n>/record.json`・`@finalize/<head 12>/result.json`
  - `test_save_points_call_collect`（`review`・`cycle_end`・`finish`・`recover`）: 偽の `collect` で、`dispatch` の各分岐（本体の関数は差し替えてよい）が `route="pr-review-fix-loop"`・正しい `event`・review_dir を渡す。`finish`・`recover` は `verify_loop_run=<run_id>`
  - `test_review_sweeps_before_batch`: `review` の本体で、レビュアーの batch（`run_workflow` 相当）を起動する前に `collect(event="review")` が 1 回呼ばれ、その時点の `<model>.md` の旧版が store に入る（batch の偽物が `<model>.md` を書き換える）
  - `test_loop_error_still_collects_and_keeps_exit_code`: `LoopError` で終わるサブコマンド（例: 状態の誤り）→ 終了コードと標準出力が収集なしと同じで、`collect` は `run_dir` があるときだけ呼ばれる
  - `test_loop_disabled_writes_nothing`: `REVIEW_EVAL_CONFIG=""` で cycle-end → store に何も無い
- [ ] Step 2: 実行して FAIL を確かめる
- [ ] Step 3: 実装。`dispatch` の `review`・`cycle-end`・`finish`・`recover` の分岐を `try/finally` で囲み、`finally` で `run_dir.is_dir()` のときだけ `collect_records` を呼ぶ。round は record JSON の `round`、head はサイクルの `head`。`review` 関数の中で、レビュアーの batch を起動する直前にも `collect_records("review", run_dir)` を呼ぶ（Spec D9）
- [ ] Step 4: `records.md` に「収集の保存点」の節を足す（4 サブコマンドの後、既定で無効、結果・終了コードを変えない、`finish`・`recover` は参照の欠落を記録）
- [ ] Step 5: `uv run --locked pytest .agents/skills/pr-review-fix-loop/tests -q` → PASS
- [ ] Step 6: commit `feat(pr-review-fix-loop): collect loop records at save points (#357)`

### Task 5（統合・controller）: 全体の検証

- テスト不要（新しい挙動が無い）。代わりの検証:
  - `uv run --locked pytest .agents/skills/pr-review/tests .agents/skills/review-verify/tests .agents/skills/review-fix-planning/tests .agents/skills/pr-review-fix-loop/tests .agents/scripts/tests tools/review_eval/tests -q` → 全て PASS
  - `uv run --locked ruff check` と `uv run --locked ruff format --check`（変更ファイル）、型検査がリポジトリにあれば同じ入口
  - `bash scripts/check-layout.sh` → 終了コード 0
  - `rg -n "collect_outputs|collect_accepted|collect_result|collect_review_dir|collect_round_record|_collect_before_replacement|collect_records" .agents` で 7 関数が定義・呼び出されている
  - `git diff --stat <base>...HEAD` で所有外のファイルが無い

## 要件と Task の対応（convergence.md の 1 章）

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
|---|---|---|---|
| 13 event の接続 | 1（4）・2（2）・3（3）・4（4） | 偽の `collect`／`run_hook` が受けた route・event・review_dir | 各 Task の `test_*_call*` |
| 有効時に store に写る | 1〜4 | 一時 store の observation の path | 各 Task の enabled テスト |
| 無効時に書かず結果不変 | 1〜4 | store が空、標準出力・終了コードが同じ | 各 Task の disabled テスト |
| 収集の例外で結果不変 | 1（代表） | 例外の差し替えでも出力が同じ | Task 1 |
| attach-runner の 30 秒共有・runner の子 | 1 | 期限後の review_dir が無い、depth=1 で写る | Task 1 |
| 古い dispatch.json | 2 | accept が終了コード 0 | Task 2 |
| 上書き前の版（prepare の sweep、loop の batch 前） | 1・4 | 旧 bytes の observation | Task 1 の prepare、Task 4 |
| shim の絶対パス・相対 `REVIEW_EVAL_CONFIG` | 2・3 | `run_hook` の引数、`os.environ` | Task 2・3 |
| 所有ファイルだけの変更 | 5（統合） | `git diff --stat` | Task 5 |

共有する前提: 仮想パスの形（`@finalize/<HEAD12>/result.json`・`@pr-comment/round-<round>/record.json`）を Task 3 と Task 4 が使う。Task 5 で両者の文字列が同じ形であることを `rg` で確かめる。

## 実行方式

- 実装担当は `pi_opencode-go_deepseek4-flash_max`（利用者の `--implement`）。Task 1〜4 を 1 つずつ runner に依頼し、取り込み後に controller が Task のレビュー（自分）と関連テストを行う。Task 5 は controller が行う
- `--merge` のため、最終のブランチ全体レビューは PR 修正ループの 1 サイクル目で代える

## 実行予算

- Issue 全体の能動時間: 6 時間（Issue の見積り 3〜6 時間）。phase の目安: Spec・設計/Spec レビュー 1.5 時間、実装 4 Task で 2.5 時間、検証と PR 0.5 時間、ループ 3 サイクル × 約 1 時間
- worker の期限: implement 90 分（runner の既定）。無進捗の打ち切りは runner に任せる
- 再試行の上限: Task ごとに `retry`・`rejected` 合わせて 2 回、指摘の修正の依頼は Task ごとに 2 回
- checkpoint: Task 2 の取り込み後に経過を見て、予算の 60% を超えていれば Task 4 の Review Focus 4 を縮小（`LoopError` テストを省き、`finally` の確認を差し替えのテスト 1 件にする）
- ledger: `tmp/agents/issue-357.bs26hhfv/sdd/2026-11-15-issue-357-review-eval-hooks/progress.md`

## contingency（代替策）

- `Store` の初期化 API の名前・形が Plan の想定と違う: 実装を読んで合わせ、ledger に記録して続ける（意味は同じ）
- 既存の loop の fixture で cycle-end の正常系を組むのが重い: `collect_records` を直接呼ぶテストと、`dispatch` の `finally` を差し替えで確かめるテストに分ける
- 所有外のファイル（root `conftest.py`、`tools/**`）の変更が要ると分かった: 実装を止め、Issue の親ボードの coordinator への相談事項として停止報告する
- 担当が `failed`、または再試行の上限に達した: その Task で止まる（self で引き取らない）
