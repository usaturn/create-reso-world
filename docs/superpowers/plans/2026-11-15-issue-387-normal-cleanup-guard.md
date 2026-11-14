# Issue #387 実装計画: 通常の cleanup でも利用者作業を検査して保持する

## 管理

- 状態: `draft`（issue-to-pr の実行委任。内容の承認は得ていない）
- Spec: `docs/superpowers/specs/2026-11-15-issue-387-normal-cleanup-guard-design.md`
- 対象: https://github.com/usaturn/create-reso-world/issues/387
- base: origin / `refs/heads/main` / `c8a2f58ffb65eced3e18993d97c439bb2d23197b`
- worktree: `.worktrees/issue-387-normal-cleanup-guard`（branch `fix/issue-387-normal-cleanup-guard`）

## 実行方式と理由

- `implement_task.py check` の `self` が false（`--implement pi_alibaba_qwen4-max_max`）なので、issue-to-pr の「Task の実装を runner の担当に依頼する」で、SDD の形により Task を 1 つずつ runner の担当に依頼する。
- Task は 1 つ（同じモジュールの小さな変更とテスト・文書）。分けると同じファイルを逐次に書くだけになるため 1 Task にまとめる。
- `--merge` が適用されるため、実装スキルの最終のブランチ全体レビューは PR 修正ループの 1 サイクル目で代える（issue-to-pr 4 章 8）。Task のレビューは controller が行う。

## 受け入れ基準

- 動作環境: Dev Container（Ubuntu 26.04、git、uv）。ローカルの実 Git fixture（pytest の `tmp_path`）。実モデルの起動・実 PR の削除はしない。
- 実入力: 非 ASCII・空白を含む submodule パス `sub módulo`、`ignore=all` の submodule、submodule 内のローカル commit（複数行の `local.txt`）。親 worktree の HEAD は固定 commit のまま（CLI の cleanup・complete の両経路で同じ入力）。
- 防御範囲: 対象は非 strict `cleanup`（CLI の `cleanup --state` と `review_run.complete` の両方の入口）が、`_require_clean_worktree` が拒否する状態のセッションを消さないこと（worktree・submodule gitdir・セッションディレクトリ・commit オブジェクト・保存レビューを保持し、CLI は終了コード 1 と `status: "retained"`・`reason`・`retained_paths`、complete は `status: failed`・`cleanup: failed`・`reason`・`review_file`・`retained_paths` を返す）。拒否時は pinned ref も消さない。対象外の反例: clean な保存済みセッションは従来どおり非 strict `cleanup` と `complete` で退役する（既存テスト `test_cleanup_removes_session_after_successful_save` と complete の成功テストが正常対照）。cache（`.venv`・`__pycache__` など）だけの ignored ファイルは退役を妨げない。strict 退役の判定内容、version 7/8 の pinned ref の compare-and-delete、保存ロック、候補一覧の検査は変えない。

## Task 1: 非 strict cleanup に利用者作業の検査を足す

- 担当ファイル:
  - `.agents/skills/pr-review/scripts/pr_review_workspace.py`
  - `.agents/skills/pr-review/tests/test_pr_review_workspace.py`
  - `.agents/skills/pr-review/tests/test_review_run.py`
  - `.agents/skills/pr-review/references/noninteractive.md`
- テストの要否: 要（S）。壊れると、保存成功・終了コード 0 のまま利用者のローカル commit が回復不能に消える（無言のデータ損失）。
- 手順（TDD）:
  1. RED: `test_pr_review_workspace.py` に `test_cleanup_keeps_a_submodule_local_commit` を足す。`test_strict_reap_keeps_a_submodule_local_commit` と同じ fixture（`make_submodule_fixture`・`create_session`・`init_submodules`・`saved_session`）で submodule `sub módulo` にローカル commit を置き、`workspace.main(["cleanup", "--state", state_file])` が 1 を返し、出力 JSON が `status: "retained"` で `reason` を持ち `retained_paths["session_dir"]` がセッションディレクトリであること、セッションディレクトリ・worktree が残り、submodule の HEAD がローカル commit のまま、`git -C <submodule> cat-file -e <commit>` が成功し、保存レビューの本文が `review\n` のままであることを確かめる。実装前に実行して失敗（終了コード 0 で削除）を確認する。
  2. RED: `test_review_run.py` に、通常の `review_run.complete` 経路のテストを足す。`prepared` fixture の対象リポジトリを submodule（`ignore=all`、パス `sub módulo`）付きにできる場合はそうし（`test_pr_review_workspace.py` の `make_submodule_fixture`・`init_submodules` と同じ作り方を流用してよい）、`review_run.prepare` → worktree の submodule 初期化 → `mark_reviewed` の後、submodule 内でファイルを足してローカル commit を作る（親 worktree の HEAD は変えない。user.name / user.email は submodule の config で設定）。`review_run.complete` を実行し、`status == "failed"`・`cleanup == "failed"`・`reason` が空でない・`Path(review_file).is_file()`・`Path(findings_file).is_file()`・`retained_paths["worktree"] == result["worktree"]`・worktree と state_file が残り、submodule の HEAD がローカル commit のまま `git cat-file -e` で読めることを確かめる。親 worktree の HEAD を変える入力は使わない（save の `verify_state` が先に拒否し cleanup に到達しない）。実装前に失敗（`cleanup: success` で削除）を確認する。
  3. GREEN: `pr_review_workspace.cleanup` の非 strict 経路で、`with review_save_lock(repo):` の中、`require_saved_findings(repo, state)` の後かつ pinned ref の削除（`delete_pinned_ref`）と `git worktree remove --force` の前に、`_require_clean_worktree(worktree, target, state)` を呼ぶ。`WorkspaceError` を受けたら `RetirementRefused(str(error), retirement="saved")` として送出する（`from error`）。他の検査・順序は変えない。
  4. `noninteractive.md` の結果の表の `cleanup` 行と、「保存済みで cleanup だけ失敗したとき」の段落に、worktree・submodule に利用者作業（strict 退役と同じ検査）があると通常の cleanup も削除を拒否してセッションと pinned ref を残すこと、CLI の通常 `cleanup` はそのとき終了コード 1・`status: "retained"` を返すことを 1〜2 文で足す。
  5. 検証: リポジトリルートで `uv run --locked pytest -q .agents/skills/pr-review/tests/test_pr_review_workspace.py .agents/skills/pr-review/tests/test_review_run.py`。リポジトリに ruff・pyright は導入されていないので、静的チェックは `uv run --locked python -m py_compile` に代える（import・構文の誤りはテストの実行でも現れる）。
- commit メッセージ: `fix(pr-review): keep user work when the normal cleanup retires a session (#387)`

## 検証の入口（最終）

- `uv run --locked pytest -q .agents/skills/pr-review .agents/skills/pr-review-fix-loop`（pr-review と、その結果を読む loop のテスト）
- `bash scripts/check-layout.sh`

## 実行予算

- Issue 全体の能動時間の予算: 4 時間（Issue の見積もり 2〜4 時間の上限）。
- phase の目安: Spec・Spec レビュー 45 分、Plan 15 分、Task 1 の実装依頼とレビュー 60 分、最終検証・PR 20 分、PR 修正ループ 最大 3 サイクル ×（レビュー 45 分＋計画・修正 30 分）。
- worker の期限: 実装担当は `implement` の役割の期限 90 分（runner の設定）。無進捗の打ち切りは runner の既定に従う。
- 再試行の上限: 実装依頼の `retry`・`rejected` は合わせて 2 回まで（指摘の修正の依頼は別に 2 回まで）。上限で止まる。
- checkpoint: Task 1 の取り込み後（テスト結果で継続を判断）、PR 作成後。
- 縮小・切り出し・方法変更の候補: `prepared` fixture に submodule を足すのが PR head の fetch の都合で難しい場合は、手順 2 の入力を「worktree に cache 以外の未追跡ファイル（利用者のファイル、複数行・非 ASCII の本文）を置く」に替え、そのファイルが内容ごと残ることを確かめる（save は未追跡ファイルを検査しないので cleanup に到達する。submodule のデータは手順 1 の workspace 側テストが確かめる）。替えたことと理由を ledger に記録する。

## contingency（代替策）

- 最初の RED で、`_require_clean_worktree` が clean な通常完了のセッション（既存テスト）まで拒否すると判明した場合（例: `review-backup` などの配置でなく、worktree に complete が書く物がある）: 仕様の意味（利用者作業を消さない・clean は退役）を保つ最小修正として、拒否の原因になる helper 自身の生成物だけを検査の前提に合わせる。検査の範囲を狭めて利用者作業を見逃す変更は意味が変わるので行わず、止まる。
- `RetirementRefused` を送出すると complete の `except` で捕まらない場合（基底が変わった等）: complete の `except` に含まれる基底（`RuntimeError`）を確認し、捕まらなければ止まる。
- 実装担当の `failed`: その Task で止まり、別の担当に切り替えない（issue-to-pr）。
