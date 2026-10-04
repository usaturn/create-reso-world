# PR #16 Document Lifecycle Root-Cause Repair Plan

> **For agentic workers:** Execute with Superpowers subagent-driven-development in task order. This is an existing review-fix workflow: integrate on the existing PR branch, not main or a second repair PR. Do not invoke the `pr-review` skill.

## Execution record

- Status: draft (implementation explicitly authorized; this is not a claim that the user reviewed this Plan's content).
- Spec: `docs/superpowers/specs/2026-10-04-create-reso-world-pr16-document-lifecycle-root-cause-review-fixes-design.md`.
- Spec content approval: the user's instruction 「進めてください。プランを作成したら、そのまま実装を開始してください」 after presentation of that Spec.
- Execution authority: the same instruction explicitly requests execution immediately after creation of this Plan; do not introduce another approval wait. Record content approval separately from execution authority.
- Target: `usaturn/create-reso-world` PR #16, `docs/superpowers-document-lifecycle`.
- Starting HEAD: `b441c3b79b91f2945e60f9b948fd52dd77fcb02f` (matched remote PR HEAD before starting).
- PARENT_ROOT: `/workspaces/reso-world`; DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/superpowers-document-lifecycle`.
- Publication: pending. The existing review-fix-planning workflow authorizes committing/pushing tested work to that existing PR and updating its status comment. Merge is not authorized.
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
6. External review/planning requires an explicit absolute checkout root and exactly one remote name matching the requested owner/repo. Multiple matches, missing matches, subdirectories and ambiguity fail. Remote-less PR integration and general external implementation remain unsupported. An external implementation Plan is blocked, never marked ready merely because planning succeeded.
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

- [ ] **RED:** add real temporary-Git tests for the external-cwd bypass, duplicate matching remotes, a non-root explicit CODE_ROOT, missing/unsupported parent origin and known-route CODE_ROOT conflicts. Record expected failures against the old resolver/absent shared module, then retain equivalent execution coverage for the shared module and consumer shell snippets.
- [ ] **Implement common module:** expose small composable functions (URL normalization and verified checkout inspection) plus an operation-aware `resolve_context(...)`. A CLI accepts `--operation review-workspace|review-fix|review-copy`, `--parent-root`, `--doc-root`, `--code-root`, `--repo`, optional `--doc-branch`, `--head-repo`, `--head-branch`. Omitted/empty optional roots mean omitted, not guessed external roots. `--repo` supports a canonical owner/repo or GitHub PR URL; invalid hosts/identifiers fail clearly.
- [ ] **Define stable JSON:** `parent_root`, `tool_root`, `doc_root`, `code_root`, `repository`, `base_remote`, `head_remote`, `document_branch`, `document_head`, `code_branch`, `code_head` (not-applicable values null). `tool_root` is the verified parent; `TOPLEVEL`/`MAIN_ROOT` can remain legacy shell aliases for returned tool/code roots, never independently resolved identities. Expected validation errors use exit 66 with actionable stderr; usage errors may use argparse's exit 2.
- [ ] **Keep profiles separate:** review-workspace rejects linked code roots before its later fetch/worktree creation. Review-fix accepts explicitly verified same-repository repair worktrees, verifies requested document branch and (when supplied) unique head remote/head branch before later implementation/push steps. Review-copy verifies parent/doc roots but never treats its code cwd as parent.
- [ ] **Migrate consumers:** remove duplicated `github_repository` bodies and branch-specific root logic from both skills and copy script. Consumers obtain JSON from the helper before mutation, then read fields with jq. Use a helper path anchored in the declared parent/tool checkout, with an actionable failure if unavailable; do not resolve skill helpers from CODE_ROOT. Keep existing review source/worktree safety and read-only review behavior.
- [ ] **Behavioral tests:** HTTPS (optional `.git`/trailing slash), SCP SSH and `ssh://` URLs; foreign hosts; absent/unsupported origins; parent main/linked/foreign and explicit valid parent; doc main/linked/subdirectory and requested branch mismatch; known self/fork routes; explicit matching/conflicting code root; external implicit versus explicit root; zero/one/two matching remote names; base/head distinction; correct and missing/ambiguous head remote. For invalid cases compare repository HEAD, status and remote state to prove no mutations.
- [ ] **Consumer tests:** fixture checkouts must contain the common helper so extracted Bash/zsh skill blocks exercise the actual module. Preserve negative/positive cases rather than replacing behavior tests with source-string checks. Keep both Bash and available zsh coverage.
- [ ] **CI:** executable bash wrapper runs `uv run --no-project python -m unittest discover -s tests/scripts -p 'test_superpowers_*.py'`, with strict exit propagation, no new package installation. Verify the existing test runner lists this wrapper and execute it through that runner.
- [ ] **GREEN + commit:** focused new tests and both affected skill suites; shell syntax; full devcontainer/script runner, layout and all skill tests. Self-review. Commit only Task 1's files, leaving controller-owned Plan/Spec edits out of the child commit. Report timings and RED/GREEN evidence.

## Task 2: Immutable review-copy publication with deterministic races

**Depends on:** Task 1's context API. **Files:** create `scripts/superpowers_review_copy.py`, `tests/scripts/test_superpowers_review_copy.py`; rewrite `scripts/superpowers-review-copy.sh` as a thin uv/Python launcher; update `tests/scripts/test-superpowers-review-copy.bash` for non-replacing semantics.

- [ ] **RED:** deterministic publication-boundary barriers reproduce two distinct concurrent copies, a user annotation written before a paused publish, and a destination changed into a directory before publish. Avoid sleeps/stress loops; tests can patch the underlying `os.link` in a subprocess, without adding debug switches to production code. Also assert that old `--replace-from` usage is rejected and changes nothing.
- [ ] **Implement:** validate context through the shared module and preserve the existing path/name/commit/source/ignore/index/symlink checks. Read the exact committed blob, stage a completed file in the destination directory and publish using non-replacing `os.link`.
- [ ] **Existing destination:** on EEXIST, compare only a safely opened regular existing file. Matching bytes -> `unchanged`; differing bytes or non-regular destination -> clear error suggesting `-r2-spec.md` / `-r2-plan.md`. Never replace or delete an existing destination, and never move a temporary file inside a destination directory. Check symlinks without following them; do not block reading FIFO/special files.
- [ ] **Failures/cleanup:** remove only this invocation's temporary file. Preserve original destination contents/entry type. Unsupported hard links fail closed, with no `rename`/`replace`/`mv -f` fallback. Any destination created by a competitor must survive a failed or unchanged invocation.
- [ ] **Compatibility:** retain documented successful output including destination-relative path, selected full commit SHA and canonical source path. Reject `--replace-from` with a migration message before filesystem mutation. Keep `.sh` executable and callable via bash from arbitrary cwd with explicit roots.
- [ ] **Coverage:** clean committed Spec and Plan, old committed version versus dirty/new source, wrong kind/suffix, unsafe name/path, tracked/not-ignored destination, symlink ancestry, destination symlink/directory/FIFO, repeated identical copy, distinct concurrent copies (exactly one winner), concurrent identical copies (created/unchanged, no partial bytes), annotations, directory race, injected link failure and no temporary residue. Verify a new versioned name leaves the old copy untouched.
- [ ] **GREEN + commit:** both copy suites, common context tests and wrapper via `.devcontainer/run-tests.bash`; syntax; full devcontainer/script runner, layout and all skill tests. Self-review and Task 2-only commit. Record test output, timing and any filesystem limitation.

## Task 3: Lifecycle, permission, history and end-to-end acceptance alignment

**Depends on:** Tasks 1–2. **Files:** modify `AGENTS.md`, `docs/superpowers/README.md`, both review skill documents as needed, `.agents/skills/agent-handoff/SKILL.md`, `.agents/skills/agent-handoff/references/handoff-schema.md`, `.agents/skills/planning-parallel-issues/references/session-workflow.md`, their contract tests, limited lifecycle Spec/Plan and round1–3 history notices; create `tests/scripts/test_superpowers_lifecycle.py`. Controller owns final state/publication metadata in the new repair Spec/Plan.

- [ ] **RED:** add acceptance assertions that detect the present permission discrepancy, replacement instructions, historical Plan's misleading operational state, omitted committed approval version and unsupported external implementation being presented as ready.
- [ ] **Current instructions:** every current caller uses new versioned names; remove instructions invoking `--replace-from`. Mention its rejection only for migration. State that old copies and annotations remain intact and document the shared resolver's operation differences.
- [ ] **Permissions:** align the AGENTS table, lifecycle Spec/README and skill instructions. General external review/planning is allowed only through explicit validated CODE_ROOT; general external implementation and remote-less PR integration are unsupported. An external repair handoff states blocked/not ready and the missing authorization/rule, not an executable implicit push plan. Native and verified ResoLoop routes retain their permissions.
- [ ] **Canonical document selection:** workflow first searches current Spec/Plan by repository, Issue/PR, theme and canonical path, not only basename or date. Reuse a current relevant canonical document for ordinary review fixes; do not generate roundN Specs by default. If more than one plausible canonical document exists, stop and ask. Record an independently approved architectural redesign or other explicit reason when creating a genuinely new Spec. Preserve the existing invariant that submitted Spec/Plan draft content must be committed before presenting a review copy.
- [ ] **Approval/lifecycle:** distinguish approved content commit SHA, current/restore SHA, explicit execution authority, completion evidence and publication state. After approval, record metadata-only changes without inventing renewed approval. Substantive design/Plan changes require renewed approval unless explicitly covered by execution authority. Handoff schema/examples and session workflow transport those distinctions; no recovery artifact claims a review copy is canonical.
- [ ] **History:** the original implementation Plan now describes historical completed implementation. Add an accurate completion/history notice referring to commits/evidence; retain original unchecked lists as historical, not active commands. For original Spec and round1–3 fixes, mark/archive appropriately with a current-rule pointer rather than updating all old instructions. Do not fabricate dates, approval SHAs or completed individual actions when evidence is absent. Leave all 22 imported documents unchanged.
- [ ] **End-to-end acceptance:** temporary own-repository and external CODE_ROOT fixtures -> context resolution -> committed draft -> copy with exact bytes/full SHA -> approval version metadata -> execution authority -> versioned revised copy (old annotated copy intact) -> publication/restore metadata checks. Include a verified DOC_ROOT worktree and helper-origin parent; fake publication metadata must say it is simulated, not claim a real push. Exercise handoff restore rules with existing integration tests; new schema coverage must assert executable state for supported versus unsupported routes.
- [ ] **GREEN + commit:** lifecycle/common/copy wrapper; all four directly affected skill test suites; full devcontainer/script runner, layout and all-skill pytest; syntax and instruction/docs tests. Check imported-document hashes against `58c9ea8`. Self-review and Task 3-only commit; report timings and RED/GREEN evidence.

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
