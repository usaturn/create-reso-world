# PR #16 Document Lifecycle Root-Cause Repair Plan

> **For agentic workers:** Execute with Superpowers subagent-driven-development in task order. This is an existing review-fix workflow: integrate on the existing PR branch, not main or a second repair PR. Do not invoke the `pr-review` skill.

## Execution record

- Status: completed (implementation, review and acceptance passed; individual approval of this Plan's content is not recorded, and PR merge is separate).
- Spec: `docs/superpowers/specs/2026-10-04-create-reso-world-pr16-document-lifecycle-root-cause-review-fixes-design.md`.
- Spec content approval: the user's instruction 「進めてください。プランを作成したら、そのまま実装を開始してください」 after presentation of that Spec.
- Execution authority: the same instruction explicitly requests execution immediately after creation of this Plan; do not introduce another approval wait. Record content approval separately from execution authority.
- Target: `usaturn/create-reso-world` PR #16, `docs/superpowers-document-lifecycle`.
- Starting HEAD: `b441c3b79b91f2945e60f9b948fd52dd77fcb02f` (matched remote PR HEAD before starting).
- PARENT_ROOT: `/workspaces/reso-world`; DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/superpowers-document-lifecycle`.
- Publication: verified at `0f6ff4619e32dbf27b6204e2a7e010498c319b8c` on the existing PR branch. This completion-record snapshot will be published to the same branch; its final restore SHA and verification belong in the PR comment/handoff. Merge is not authorized.
- Baseline: 96 targeted skill cases pass, including zsh; the existing copy bash test passes, despite the demonstrated races.

**Goal:** Replace duplicated branch-specific checks with shared, read-only context validation; publish immutable, non-replacing review copies; make permissions, approvals, history and document reuse consistent across the end-to-end workflow.

**Architecture:** A Python-standard-library context module, exposed through a JSON CLI, owns GitHub URL and checkout/remote validation. Operation-specific profiles preserve different review, document and repair constraints. The existing shell copy entrypoint delegates to a small Python implementation that stages a completed file and publishes with `os.link`, never a replacing move. Normative workflow documents and behavioral tests share those rules without rewriting imported history.

**Stack:** Git, Bash/zsh, uv, Python >=3.12 standard library, existing pytest infrastructure. No new application dependencies.

## Global Constraints

1. No `pr-review` invocation, new repository search/clone, changes to external repositories, new repair PR, merge, or modification of unrelated work. Reading/editing the local pr-review implementation and its tests is part of the approved repair.
2. Work only in the clean existing PR worktree above. All commits go on `docs/superpowers-document-lifecycle`; controller alone fetches/pushes/comments and owns integration decisions. Subagents are synchronous; at most one writer; reviewers are read-only and do not run tests.
3. Helpers must validate before Git mutation or filesystem publication. Context validation never fetches, clones, checks out, creates worktrees, pushes, or changes an index. Errors identify the root/remote problem; no empty stderr or raw traceback for expected failures.
4. PARENT_ROOT is a verified create-reso-world **main checkout**, not an arbitrary cwd or linked worktree. DOC_ROOT can be a verified create-reso-world worktree. CODE_ROOT is independent and explicit where required. An external or linked cwd must not become a parent automatically; an explicitly supplied valid parent remains supported.
5. Known repository routes remain bounded: create-reso-world uses its parent checkout (or a repair worktree belonging to that same Git repository); ResoLoop uses the verified `PARENT_ROOT/external/resoloop` fork (`origin=usaturn/resoloop`, `upstream=orange3134/resoloop`). A conflicting explicit CODE_ROOT must fail, not be ignored.
6. External PR review/planning and its existing approved PR review-fix implementation require an explicit absolute checkout root and exactly one remote name matching the requested owner/repo. Multiple matches, missing matches, subdirectories and ambiguity fail. Remote-less PR integration and general external/Issue implementation remain unsupported. A Plan for an undefined external implementation route is blocked, never marked ready merely because planning succeeded; do not block the existing authorized PR repair route solely because it is external.
7. Non-replacing copy publication preserves existing successful copies and user annotations. Repeated identical content may report `unchanged`; differing content must fail and suggest a new versioned name. Symlinks, directories and special files are not acceptable existing destinations. Reject `--replace-from` without changing any file. No replacing fallback on unsupported hard links.
8. Preserve all existing copy safety checks: verified roots/origins, committed regular Spec/Plan only, correct path/name kind, clean source against selected commit, ignored and untracked destination, symlink-safe destination ancestry, exact committed bytes and cleanup on failure.
9. Approval refers to an actual committed content version, separately from restore/current SHA, execution authority, completion and publication. Metadata-only status/approval corrections do not invent approvals or demand reapproval of unchanged substantive content. Imported historical documents remain byte-for-byte untouched.
10. Implement RED before GREEN for behavior changes. Run focused tests while iterating, then required full validations synchronously before commits. Report task timing and precise commands/results; do not claim race tests prove universal concurrency safety or that future reviews cannot find bugs.

## File structure and integration inventory

- Create `scripts/superpowers_context.py`: URL parsing, checkout validation, operation-specific context resolution and JSON CLI in one focused, standard-library module.
- Create `tests/scripts/test_superpowers_context.py`: behavioral Git fixtures and cross-branch matrix, usable with both unittest discovery and pytest.
- Create `tests/scripts/test-superpowers-python.bash`: standard-library unittest discovery of `test_superpowers_*.py`. Existing `.devcontainer/run-tests.bash` automatically collects `tests/scripts/*.bash`; therefore CI executes the new Python tests through this wrapper. Merely placing `.py` tests in `tests/scripts` is not CI wiring.
- Create `scripts/superpowers_review_copy.py` and `tests/scripts/test_superpowers_review_copy.py`; retain `scripts/superpowers-review-copy.sh` as the documented entrypoint.
- Modify current callers: `AGENTS.md`; `docs/superpowers/README.md`; `.agents/skills/pr-review/SKILL.md`; `.agents/skills/review-fix-planning/SKILL.md`; `.agents/skills/agent-handoff/SKILL.md` and `references/handoff-schema.md`; `.agents/skills/planning-parallel-issues/references/session-workflow.md`. Adjust related skill tests and instruction/docs tests where behavior genuinely changes.
- Add `tests/scripts/test_superpowers_lifecycle.py` for document/permission/version/history acceptance assertions.
- Historical references (not current executable callers): the original `2026-10-03-superpowers-document-lifecycle-design.md`, its Plan, and round1–3 review-fix Specs. Add a limited implementation/history notice and state corrections where justified. Do not synchronize every past instruction, erase old unchecked tasks, or claim undocumented approvals.
- Do not modify the 22 documents imported in commit `58c9ea8`, original local archive, PR #15 draft, unrelated worktrees, or existing review artifacts. Preserve the original investigation/handoff in ignored local storage.

## Task 1: Shared read-only context validation and all resolver consumers

**Files:** create `scripts/superpowers_context.py`, `tests/scripts/test_superpowers_context.py`, `tests/scripts/test-superpowers-python.bash`; modify `.agents/skills/pr-review/SKILL.md`, `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py`, `.agents/skills/review-fix-planning/SKILL.md`, `.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`, and the root/remote validation portion of `scripts/superpowers-review-copy.sh`.

- [x] **RED:** add real temporary-Git tests for the external-cwd bypass, duplicate matching remotes, a non-root explicit CODE_ROOT, missing/unsupported parent origin and known-route CODE_ROOT conflicts. Record expected failures against the old resolver/absent shared module, then retain equivalent execution coverage for the shared module and consumer shell snippets.
- [x] **Implement common module:** expose small composable functions (URL normalization and verified checkout inspection) plus an operation-aware `resolve_context(...)`. A CLI accepts `--operation review-workspace|review-fix|review-copy`, `--parent-root`, `--doc-root`, `--code-root`, `--repo`, optional `--doc-branch`, `--head-repo`, `--head-branch`. Omitted/empty optional roots mean omitted, not guessed external roots. `--repo` supports a canonical owner/repo or GitHub PR URL; invalid hosts/identifiers fail clearly.
- [x] **Define stable JSON:** `parent_root`, `tool_root`, `doc_root`, `code_root`, `repository`, `base_remote`, `head_remote`, `document_branch`, `document_head`, `code_branch`, `code_head` (not-applicable values null). `tool_root` is the verified parent; `TOPLEVEL`/`MAIN_ROOT` can remain legacy shell aliases for returned tool/code roots, never independently resolved identities. Missing required inputs (including --operation, explicit external CODE_ROOT, required DOC_ROOT and incomplete head input) use exit 64; known ResoLoop fork prerequisite defects use 65; path/identity/remote candidate mismatch uses 66. Keep actionable stderr and empty normal stdout on failure. Malformed CLI syntax may retain argparse's exit 2; copy CLI retains usage 2/rejection 1.
- [x] **Keep profiles separate:** review-workspace rejects linked code roots before its later fetch/worktree creation. Review-fix accepts explicitly verified same-repository repair worktrees, verifies requested document branch and (when supplied) unique head remote/head branch before later implementation/push steps. Review-copy verifies parent/doc roots but never treats its code cwd as parent.
- [x] **Migrate consumers:** remove duplicated `github_repository` bodies and branch-specific root logic from both skills and copy script. Consumers obtain JSON from the helper before mutation, then read fields with jq. Use a helper path anchored in the declared parent/tool checkout, with an actionable failure if unavailable; do not resolve skill helpers from CODE_ROOT. Keep existing review source/worktree safety and read-only review behavior.
- [x] **Behavioral tests:** HTTPS (optional `.git`/trailing slash), SCP SSH and `ssh://` URLs; foreign hosts; absent/unsupported origins; parent main/linked/foreign and explicit valid parent; doc main/linked/subdirectory and requested branch mismatch; known self/fork routes; explicit matching/conflicting code root; external implicit versus explicit root; zero/one/two matching remote names; base/head distinction; correct and missing/ambiguous head remote. For invalid cases compare repository HEAD, status and remote state to prove no mutations.
- [x] **Consumer tests:** fixture checkouts must contain the common helper so extracted Bash/zsh skill blocks exercise the actual module. Preserve negative/positive cases rather than replacing behavior tests with source-string checks. Keep both Bash and available zsh coverage.
- [x] **CI:** executable bash wrapper runs `uv run --no-project python -m unittest discover -s tests/scripts -p 'test_superpowers_*.py'`, with strict exit propagation, no new package installation. Verify the existing test runner lists this wrapper and execute it through that runner.
- [x] **GREEN + commit:** focused new tests and both affected skill suites; shell syntax; full devcontainer/script runner, layout and all skill tests. Self-review. Commit only Task 1's files, leaving controller-owned Plan/Spec edits out of the child commit. Report timings and RED/GREEN evidence.

## Task 2: Immutable review-copy publication with deterministic races

**Depends on:** Task 1's context API. **Files:** create `scripts/superpowers_review_copy.py`, `tests/scripts/test_superpowers_review_copy.py`; rewrite `scripts/superpowers-review-copy.sh` as a thin uv/Python launcher; update `tests/scripts/test-superpowers-review-copy.bash` for non-replacing semantics.

- [x] **RED:** deterministic publication-boundary barriers reproduce two distinct concurrent copies, a user annotation written before a paused publish, and a destination changed into a directory before publish. Avoid sleeps/stress loops; tests can patch the underlying `os.link` in a subprocess, without adding debug switches to production code. Also assert that old `--replace-from` usage is rejected and changes nothing.
- [x] **Implement:** validate context through the shared module and preserve the existing path/name/commit/source/ignore/index/symlink checks. Read the exact committed blob, stage a completed file in the destination directory and publish using non-replacing `os.link`.
- [x] **Existing destination:** on EEXIST, compare only a safely opened regular existing file. Matching bytes -> `unchanged`; differing bytes or non-regular destination -> clear error suggesting `-r2-spec.md` / `-r2-plan.md`. Never replace or delete an existing destination, and never move a temporary file inside a destination directory. Check symlinks without following them; do not block reading FIFO/special files.
- [x] **Failures/cleanup:** remove only this invocation's temporary file. Preserve original destination contents/entry type. Unsupported hard links fail closed, with no `rename`/`replace`/`mv -f` fallback. Any destination created by a competitor must survive a failed or unchanged invocation.
- [x] **Compatibility:** retain documented successful output including destination-relative path, selected full commit SHA and canonical source path. Reject `--replace-from` with a migration message before filesystem mutation. Keep `.sh` executable and callable via bash from arbitrary cwd with explicit roots.
- [x] **Coverage:** clean committed Spec and Plan, old committed version versus dirty/new source, wrong kind/suffix, unsafe name/path, tracked/not-ignored destination, symlink ancestry, destination symlink/directory/FIFO, repeated identical copy, distinct concurrent copies (exactly one winner), concurrent identical copies (created/unchanged, no partial bytes), annotations, directory race, injected link failure and no temporary residue. Verify a new versioned name leaves the old copy untouched.
- [x] **GREEN + commit:** both copy suites, common context tests and wrapper via `.devcontainer/run-tests.bash`; syntax; full devcontainer/script runner, layout and all skill tests. Self-review and Task 2-only commit. Record test output, timing and any filesystem limitation.

## Task 3: Lifecycle, permission, history and end-to-end acceptance alignment

**Depends on:** Tasks 1–2. **Files:** modify `AGENTS.md`, `docs/superpowers/README.md`, both review skill documents as needed, `.agents/skills/agent-handoff/SKILL.md`, `.agents/skills/agent-handoff/references/handoff-schema.md`, `.agents/skills/planning-parallel-issues/references/session-workflow.md`, their contract tests, limited lifecycle Spec/Plan and round1–3 history notices; create `tests/scripts/test_superpowers_lifecycle.py`. Controller owns final state/publication metadata in the new repair Spec/Plan.

- [x] **RED:** add acceptance assertions that detect the present permission discrepancy, replacement instructions, historical Plan's misleading operational state, omitted committed approval version and unsupported external implementation being presented as ready.
- [x] **Current instructions:** every current caller uses new versioned names; remove instructions invoking `--replace-from`. Mention its rejection only for migration. State that old copies and annotations remain intact and document the shared resolver's operation differences.
- [x] **Permissions:** align the AGENTS table, lifecycle Spec/README and skill instructions. Arbitrary-repository PR review/planning and its existing approved review-fix-planning implementation are allowed only through explicit validated CODE_ROOT. General external/Issue implementation and remote-less PR integration are unsupported. An external handoff for an undefined execution route or with missing authority states blocked/not ready and the missing authorization/rule, not an executable implicit push plan. An explicitly authorized PR repair handoff remains supported. Native and verified ResoLoop routes retain their permissions.
- [x] **Canonical document selection:** workflow first searches current Spec/Plan by repository, Issue/PR, theme and canonical path, not only basename or date. Reuse a current relevant canonical document for ordinary review fixes; do not generate roundN Specs by default. If more than one plausible canonical document exists, stop and ask. Record an independently approved architectural redesign or other explicit reason when creating a genuinely new Spec. Preserve the existing invariant that submitted Spec/Plan draft content must be committed before presenting a review copy.
- [x] **Approval/lifecycle:** distinguish approved content commit SHA, current/restore SHA, explicit execution authority, completion evidence and publication state. After approval, record metadata-only changes without inventing renewed approval. Substantive design/Plan changes require renewed approval unless explicitly covered by execution authority. Handoff schema/examples and session workflow transport those distinctions; no recovery artifact claims a review copy is canonical.
- [x] **History:** the original implementation Plan now describes historical completed implementation. Add an accurate completion/history notice referring to commits/evidence; retain original unchecked lists as historical, not active commands. For original Spec and round1–3 fixes, mark/archive appropriately with a current-rule pointer rather than updating all old instructions. Do not fabricate dates, approval SHAs or completed individual actions when evidence is absent. Leave all 22 imported documents unchanged.
- [x] **End-to-end acceptance:** temporary own-repository and external CODE_ROOT fixtures -> context resolution -> committed draft -> copy with exact bytes/full SHA -> approval version metadata -> execution authority -> versioned revised copy (old annotated copy intact) -> publication/restore metadata checks. Include a verified DOC_ROOT worktree and helper-origin parent; fake publication metadata must say it is simulated, not claim a real push. Exercise handoff restore rules with existing integration tests; new schema coverage must assert executable state for supported versus unsupported routes.
- [x] **GREEN + commit:** lifecycle/common/copy wrapper; all four directly affected skill test suites; full devcontainer/script runner, layout and all-skill pytest; syntax and instruction/docs tests. Check imported-document hashes against `58c9ea8`. Self-review and Task 3-only commit; report timings and RED/GREEN evidence.

## Controller integration and publication

1. Save the approved architectural Spec unchanged in DOC_ROOT and commit it with the created Plan as the initial document snapshot. Record that commit as the approved Spec content version in subsequent metadata; do not claim the unseen Plan was content-approved. Creation and immediate execution are explicitly authorized.
2. Create plan-scoped `.superpowers/sdd/<plan-basename>/` briefs, reports and ledger. Record each Task's BASE before dispatch, commit HEAD after implementation, task-specific spec/quality verdicts and unresolved issues. Resume the original implementer for findings. No parallel writers.
3. Required validations before each task commit are the existing review-fix gates; controller can make a final independently observed run of all gates. Run focused tests during iteration, not the entire suite after every edit.
4. After Task 3, inspect the net change against the approved acceptance matrix, run final full verification and obtain a read-only whole-change review (not the `pr-review` skill). Fix Critical/Important findings with the original implementer and fresh evidence. Record residual limitations, not universal safety claims.
5. Update this Plan and approved Spec status/implementation evidence truthfully. Use `completed` only after acceptance gates pass; publication remains pending until verified push. Preserve approval SHA and distinguish local metadata commit from approved content.
6. Produce non-replacing parent review copies of the committed current Spec/Plan using explicit DOC_ROOT/PARENT_ROOT and new names `create-reso-world-pr16-root-cause-spec.md` / `create-reso-world-pr16-root-cause-plan.md` (use `-r2-` if occupied). Record returned full SHA and canonical paths. Verify copied bytes. These copies do not request another approval or become authoritative.
7. Fetch/recheck PR #16 OPEN and remote HEAD. If remote changed, stop for safe integration/reverification; never overwrite remote commits or force-push. Otherwise push the existing branch and verify PR HEAD through API. No new PR; no merge.
8. Post/update only the controller model's review-fix status comment using the canonical helper, exact model identifier from `PI_PROVIDER` plus `PI_MODEL`, original R1–R17 classifications and actual tests. Do not rerun investigation or edit another agent's comments.
9. Save a fresh Markdown/JSON handoff with approved content SHA, restore/current SHA, supported/blocked scope, publication state, evidence, timings and any next action. Mark Herdr completed only after stopping/completing deliberately. If a gate cannot be satisfied, report the blocker and do not call the implementation complete or publish it.

## Final validation commands

Run from DOC_ROOT (all synchronous, preserving exit status):

```bash
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
uv run pytest tests/skills .agents/skills
bash -n scripts/superpowers-review-copy.sh tests/scripts/test-superpowers-review-copy.bash tests/scripts/test-superpowers-python.bash
uv run --no-project python -m unittest discover -s tests/scripts -p 'test_superpowers_*.py'
git diff --check
```

The environment may legitimately report the layout check's existing unavailable-ResoLoop skip. Record that explicitly; it is not new context/copy coverage. No unrelated world builds or fork-wide tests are required. Any new test must appear in the existing CI runner's `--list` or existing pytest scope and be demonstrated executing there.

## 実施結果（2026-10-04 UTC、運用受入完了）

- Spec承認内容の保存版: `79330776e52a4b077c8a596b035ab8f48a242123`。Plan本文の個別内容承認は記録されていない。作成直後の実行と今回の続行は明示指示済み
- 検証コードHEAD: `1987715653fba088bafa0033b48b8304166f42c7`。Task 1/2は引き継ぎ時のレビュー済み実装を保持し、Task 3と全体レビューの必要な修正だけを続行
- Task 1: `7933077..895596c`、Task 2: `895596c..0d42f00`、Task 3/受入修正: `0d42f00..1987715`。各タスクレビューと全体レビューの指摘修正を確認済み、未解決のCritical/Importantなし
- 最終版のローカル検証: bash 27本、unittest 72件、スキル399 passed / 1既存skip、実配置・ResoLoop同期4件、構文/diffが成功。controllerの全体独立検証と、最後のCI/文書/ライフサイクル20件の追加検証も成功
- CIのdevcontainer-tests checkoutは履歴取得を設定し、22取り込み文書の `58c9ea8` 基準blob照合を維持。浅いローカルfixtureで欠落/履歴取得後の成功を確認
- 過去の2 Specはsupersededの履歴、旧Planはcompletedの履歴として、実行指示と不明な個別内容承認を分離。本文・43個の旧チェック項目は保持
- 実行方法: subagent-driven-development。前セッションのpi担当はこのランタイムから再開できないため、既存brief/reportを読んだ代替担当が必要な修正を実施
- 運用受入: `0f6ff4619e32dbf27b6204e2a7e010498c319b8c` のSpec/Planを親checkoutへ非置換コピーし、コミット内のバイト列とSHA-256が一致。push成功、PR API HEAD一致、GitHub contents APIから空の一時領域への復元と完全一致を確認。一時復元領域は除去済み
- GitHub CI: [push実行](https://github.com/usaturn/create-reso-world/actions/runs/37190611006)・[PR実行](https://github.com/usaturn/create-reso-world/actions/runs/37190613778)の各4チェックが成功。監視終了は2026-10-04 08:59:40 UTC、終了0
- 最終記録の反映: このメタデータ更新をコミットし、別名の確認用コピーを作成して同じPRへpushする。最終SHAのAPI/復元/CI確認、結果コメント、handoffはその公開結果を記録する。マージ未実施
- このCodex実行では手順8のpi固有変数の代わりに、現在のsession turn_contextに記録された厳密な識別子 `gpt-6.1-sol` を使い、同じモデルのマーカーだけを正規helperで更新する
- 既存R1–R17の分類は調査時点の7/8/0/2を保持し、R8/R17を新たに修正済みとは扱わない。自然言語規約の遵守・全並行実行の普遍的な保証は行わない

## Task 4: 調査で実証した2件を関連経路も含めて修正する

- 状態: 実装・ローカル検証・最終確認完了（公開前の記録）。Task 1–3の完了記録は保持する。公開の実際は本コミットを指すPRコメントへ記録する。
- 実行指示: 「再レビュー時に不具合が発覚して修正コミットが積みあがらないように修正をお願いします」。今回作成する追記本文への個別内容承認とは区別する。
- 開始HEAD: `e2dd691e2f84033810979402c06cf3e005718a7c`。
- Spec: 同名のroot-cause Spec §11。
- Goal: 文書検査がPR固有履歴なしでも動き、URLの拒否診断が認証情報を出さないこと。
- Architecture / Stack: 追跡JSONの固定SHA-256、既存Python標準ライブラリの比較と診断を使用する。新しい依存関係は追加しない。
- Global Constraints: 既存PR/worktreeで実施し、22取り込み文書、終了コード、URLの受入範囲、読み取り専用性、gitleaksの履歴取得を保持する。main・無関係な作業・外部リポジトリ・PRマージは対象外。
- 実行方式: executing-plansによる担当者の直接実装と、別担当による最終確認1回。Task 1–3の実行方式は当時の履歴として保持する。
- Review Focus: 固定期待値の出所、履歴なしで実行できること、改変の検出、同じURL検証の診断経路、既存消費側とCIの退行。

**Files:** `scripts/superpowers_context.py`、context/lifecycle unittest、文書hash fixture、`.github/workflows/ci.yml`、`tests/scripts/test-ci.bash`、README、review-fix-planning Skill、本Spec/Plan。

- [x] **RED:** 通常/浅い単一コミットcloneとGit情報のない配布物で現行の文書検査が失敗するテストを追加する。認証情報入りorigin・push URLと不正なrepo/head-repo入力が診断に流出するテストを追加し、失敗理由を確認する。
- [x] **Implement:** `58c9ea8` のblobから22件の固定hashを一度生成し、対象一覧との一致と現在のバイト列を検査する。URLを含まないエラーに変更し、CIの不要な履歴依存と2箇所の説明を補正する。
- [x] **GREEN:** focused unittest、1文書の改変検出、既存のURL・終了コード・Git状態の検査を確認する。
- [x] **Required gates:** `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills`、`git diff --check`。追加テストが既存CI経路で実行されることも確認する。
- [x] **Final review:** 今回の変更と影響する既存経路を一度、読み取り専用の別担当で確認する。重要な指摘があれば再現テストと修正を1回の対応で行い、必要な検証を再実行する。再レビューの連鎖は行わない。
- [ ] **Publish:** 全検証後に1コミットへまとめる。PRのhead repo/branch・実効push先を再確認し、既存PRへpushしてAPIでHEADを確認する。正規helperで同じ担当の結果コメントを更新する。マージしない。

**Commit:** `fix: make lifecycle checks portable and keep credentials out of diagnostics`

所要時間とRED/GREEN・必須検証・最終確認結果は、完了時にこの節へ記録する。最終コミットSHAと公開/CIの結果はPRコメントに記録し、それだけのための追記コミットは作らない。

### Task 4 実施結果（公開前）

- RED: 追加7テストで22の想定どおりの失敗を確認（4.006秒）。修正前のcontext/lifecycle 49件は成功（17.407秒）。
- GREEN: context/lifecycle 56件成功（20.606秒）。Git情報なし、単一コミットmain-only bareからの通常/depth 1 clone、1文書の改変検出、認証情報入り診断、既存終了コードとGit状態を検査した。
- 必須検証: 環境ランナー27本成功（追加分を含むSuperpowers unittest 79件を実行）、スキル399 passed / 1既存skip（42.55秒）、実配置・全4プロジェクトのResoLoop同期成功、diff検査成功。
- 固定hashは元の `58c9ea8` の22 blobと一致し、22文書の現在のバイト列も同じ。今回の開始HEADからも文書変更なし。
- 別担当の最終確認: stagedの10ファイルと影響する呼び出し元を確認。Critical/Important/Minorなし、判断対象外への保留なし。追加の修正・再レビューは実施していない。
- 所要時間: 着手11:07:13 UTCからローカル受入11:23 UTCまで約16分。方針・資料照合と計画追記約8分、再現テスト/修正約3分、必須検証約2分、最終確認/公開前確認約3分（一部は並行）。コミット・push・GitHub CI監視の時間と結果はPRコメントで追記する。
- Publishチェックは公開前の事実として未完了のまま保存する。公開後は本コミットを参照するPRコメントが結果の記録となり、チェック更新だけのコミットは作らない。今回の追記本文への個別内容承認やマージ許可は推定しない。
