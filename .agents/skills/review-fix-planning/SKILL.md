---
name: review-fix-planning
description: Use when handed a directory of review results (e.g. `reviews/BRANCH/`, `docs/reviews/main/`, or `#<number>` for `reviews/#<number>-*`) and asked for a fix plan, a disposition for the findings, or which findings to act on — including requests like "read the reviews and plan the fixes", "only pick up the valid findings", or "consolidate these multi-model reviews" — or when implementing or landing already-approved review-fix work for a reviewed branch or PR
---

# Review Fix Planning

Select only the findings that are still alive at the current HEAD, then reach a fix plan through a Spec and an explicit approval.

**Core principle: a review is advice about a past HEAD. A finding that does not reproduce against current code is not a finding.**

## Resolving the review directory

When the first argument is `#<number>` (e.g. `#300`), resolve it to a review directory before starting the procedure:

- Look only at directories directly under `reviews/` at the parent repository root and under `public/reviews/` (where `usaturn/maatlog` PR reviews land). Do not recurse; files at those levels are not candidates.
- A directory matches when its name starts with the given `#<number>-` (i.e. the number followed by a hyphen, e.g. `reviews/#300-fix-issue-299-pr-review-budget/`).
- Exactly one match → that directory is the review directory.
- No match → stop and report that nothing under `reviews/` or `public/reviews/` starts with the argument.
- Multiple matches → stop, list the candidate directory names, and ask the user to pass the full path.

A first argument that is not `#<number>` keeps its existing meaning: the path to the review directory.

## Procedure

If the request is only to land already-approved, already-implemented review-fix work (no new triage), skip steps 1–7. Confirm the reviewed branch / PR with `git` / `gh`, then run **After implementation**.

Otherwise, create one task per procedure item using the runtime's plan/todo facility (for Codex, use `update_plan`) before starting.

1. **Fix the scope** — read every file under the resolved review directory. Record the target HEAD stated at the top of each. Multiple generations of HEAD are the norm. Review artifacts are often gitignored and uncommitted (this repository's `reviews/` is), but anything inside the given directory is valid input regardless of its Git tracking state.
2. **Identify the current HEAD** — confirm the tip of the reviewed branch / PR with `git` / `gh`. Fix the reviewed PR's repository here too: `PR_REPO` is its `owner/name`, and `MAIN_ROOT` resolves the way `pr-review` does — `usaturn/maatlog-poc` → the parent toplevel `$TOPLEVEL` (`git rev-parse --show-toplevel` in the parent checkout), `usaturn/maatlog` → the verified public submodule at `$TOPLEVEL/public` (`git -C "$TOPLEVEL/public" remote get-url origin` must equal `submodule.public.url` in `.gitmodules`), anything else → stop. Skill helpers such as `upsert_pr_comment.py` exist only in the parent repository, so resolve them from `$TOPLEVEL`, never `$MAIN_ROOT`.
3. **Verify each finding against COMMITTED content at the current HEAD** — read with `git show <HEAD>:<path>`. A committed source or test blob at `REVIEWED_HEAD` for a cited path is valid verification evidence. For behavioural findings, reproduce in an isolated worktree whose path and reviewed HEAD are separate arguments:

   ```bash
   REPRO_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/review-fix-planning.XXXXXX")"
   WT="$REPRO_ROOT/worktree"
   git -C "$MAIN_ROOT" worktree add --detach "$WT" "$REVIEWED_HEAD"
   test "$(git -C "$WT" rev-parse HEAD)" = "$(git -C "$MAIN_ROOT" rev-parse "$REVIEWED_HEAD^{commit}")"
   ```

   `WT` is a unique temporary path outside the main checkout. If the SHA does not match, stop and do not use that worktree as evidence. Anything that does not reproduce drops to "resolved".

   **Never read the source/test under verification from working-tree files.** A working tree may carry someone's uncommitted changes and will produce false "already fixed" verdicts. This misjudgement has actually occurred. This constrains verification evidence only; it does not apply to reading the review artifacts that are the input.

   **Containment:** Put every temporary file this session creates for verification (HEAD notes, logs, pytest output, scratch) under `$REPRO_ROOT`. Do not create `review-fix-planning-*`, `review-fix-planning-*.txt`, or hyphenated names such as `review-fix-planning-wt` / `review-fix-planning-head` / `review-fix-planning-repro-root` directly in `${TMPDIR:-/tmp}`. The only path at that root is the directory `mktemp` returned.

   **Teardown (end of step 3):** After every finding that needed `$WT` has been verified, remove this session's worktree and then the parent directory. Do not wait until spec writing or approval. If you need to re-verify later, create a new `mktemp` directory; do not reuse a removed one.

   ```bash
   git -C "$MAIN_ROOT" worktree remove --force "$WT" && rm -rf -- "$REPRO_ROOT"
   ```

   If `worktree remove` fails, do not `rm -rf` the parent (that would leave git's worktree registration pointing at a missing path). Stop, report the full paths of `$WT` and `$REPRO_ROOT`, and leave the directory for `.devcontainer/cleanup-workspace.bash`. Do not hand-assemble `rm -rf` without `worktree remove`.
4. **Sort every finding into the four buckets below.**
5. **Invoke `superpowers:brainstorming`** — bring the triage to it, let it classify the path (spike / bounded / architectural), and work the design in that path's style.
6. **Write the Spec** — always, whatever the path (see below).
7. **Stop for approval** — present the Spec and do not start implementing until the user explicitly says to proceed. Posting **PR status comment before finishing** without implementation is optional (任意); it is required only after landing. After that implementation is done, follow **After implementation**.

## After implementation

This section runs only after the user has explicitly approved the Spec and the Fix items are implemented. Planning still stops at step 7. It also runs when a later request is only to land that already-approved, already-implemented work. When implementing, create one task per recipe step.

**Landing recipe — do this, in this order:**

1. Run **only the tests related to the implementation**: the verification method recorded per Fix item in the Spec, tests that cover the files you changed, and tests added as part of the Fix.
2. If they fail: fix them. Do not commit.
3. `git fetch origin` and confirm the reviewed branch tip. If the related tests pass: commit on the reviewed branch (the existing PR's head). Not `main`. Not a new `*-review-fixes` branch.
4. `git push` that branch to the **existing PR**. Confirm the push succeeded. If it is rejected, rebase or merge, re-run the related tests, and push again. Do not open a new PR. Do not present the `finishing-a-development-branch` menu.
5. Run **PR status comment before finishing** before reporting completion.

If there is no open PR for the reviewed branch, stop and report. Do not create one unless the user asks. Do not post a comment either.

**This section is the standing commit/push instruction.** Do not wait for a second "commit" or "push". 「進めて」 approved implementation; this recipe lands it.

**Not a landing gate:** the full verifier of the reviewed PR's repository (`./scripts/ci/verify.sh full` in `usaturn/maatlog`, `./scripts/ci/verify-devenv.sh` in `usaturn/maatlog-poc`; CI still runs it on the existing PR), the whole suite, `superpowers:verification-before-completion`'s full-suite rule, `superpowers:finishing-a-development-branch`.

Example: Spec verification named `uv run pytest tests/theme/test_rail.py` — an application change, so the reviewed PR is `usaturn/maatlog` #142 and `MAIN_ROOT` is the verified `public/` checkout. That file plus tests covering the CSS you changed pass. Commit on `feature/issue-102-author-right-rail` and `git -C "$MAIN_ROOT" push origin HEAD` to the public PR, with `PR_REPO=usaturn/maatlog` for the status comment. Do not run `./scripts/ci/verify.sh full` first. Do not open `feature/issue-102-review-fixes`. After the push, create or update the status comment on that same PR.

A parent environment PR works the same way on the parent route: `PR_REPO=usaturn/maatlog-poc`, `MAIN_ROOT` is the parent toplevel, and the parent's full verifier `./scripts/ci/verify-devenv.sh` is likewise not a landing gate.

## PR status comment before finishing

The purpose of this comment is only a durable record for later agents and reviewers. It is not a stall remedy for waiting on completion notices; stalls are the monitor's (Monitor / PID) problem.

The comment must stand alone: a reader with only the PR can understand the decisions without the Spec.

**Required only after landing (only after landing turns with commit / push).** If this turn implements through landing, post once after landing. If this turn stops for approval without implementation, posting is optional (任意). Update this agent's existing comment when one exists; otherwise create a new one. Other agents' comments may be read but must not be edited.

**Do not post** when the reviewed branch has no open PR. As elsewhere, do not create one; report in chat and stop.

**Repository:** set `PR_REPO` to the `owner/name` holding the reviewed PR. The helper never infers it from the working directory, so a PR number alone cannot reach the wrong repository.

**Model identifier:** set `MODEL_NAME` to the exact identifier the runtime presents. Do not guess from filenames or family names. If it cannot be obtained, stop and ask instead of posting.

**Write the comment in Japanese.** Use only these three headings, in this order. Do not paste the full Spec. On an early stop, write what is known and mark unfinished sections as `未実施`. A landing-only request still summarises the approved Spec under レビュー状況 and 作業判断; do not re-verify.

```markdown
## review-fix-planning（<MODEL_NAME>）

対象 PR: #<N>（`<branch>`） / 現行 HEAD: `<sha>`

### レビュー状況
- 入力: `<review-dir>`（読んだファイルと各対象 HEAD）
- 分類: 解消済み N / 対応する N / 判断保留 N / 対応しない N

### 作業判断
- 対応する: 各 ID と (a)–(d) と一行
- 判断保留: あるなら一行。ユーザが選んだ結果
- 対応しない: 全件を ID と一行理由で記載する（件数要約のみにしない）
- 解消済み: 件数と代表根拠

### 作業結果
- このターン: 計画のみ | push 済み | 途中停止
- Spec: `<path>`（gitignore 対象でローカルにしか無い）または未作成
- commit / push: `<sha>` またはしていない
- 次: 承認待ち | 完了 | 停止理由
```

```bash
TOPLEVEL="$(git rev-parse --show-toplevel)"   # run from the parent checkout
HELPER="$TOPLEVEL/.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"
uv run --no-project python "$HELPER" --pr "$PR_NUMBER" --repo "$PR_REPO" --model-name "$MODEL_NAME" <<EOF
## review-fix-planning（$MODEL_NAME）

対象 PR: #$PR_NUMBER（\`$HEAD_BRANCH\`） / 現行 HEAD: \`$HEAD_SHA\`

### レビュー状況
...
### 作業判断
...
### 作業結果
...
EOF
```

The helper prefixes `<!-- review-fix-planning:agent:<sanitized> -->` and updates only the comment that already carries that marker. Do not use `gh pr comment --edit-last`; that would overwrite another agent sharing the same GitHub account. If the helper fails, stop and report stderr; do not assemble a substitute `gh` call. Multiple comments with this agent's marker are also a stop.

## The classification contract

Place every finding in exactly one bucket and report a count per bucket.

| Bucket | What belongs here |
|---|---|
| **Resolved** | Verified against current HEAD and does not reproduce. Add a one-line basis (commit, line) |
| **Fix** | Only what satisfies one of:<br>(a) a malfunction reproduced at current HEAD<br>(b) a statement (code comment, docs) confirmed factually wrong at current HEAD<br>(c) restoring a regression guard that was removed without reason<br>(d) the user asked for that specific finding by name |
| **Hold** | Not the above, but a **few-line fix that removes a latent bug**. This only. Offer it in one line and let the user choose |
| **Skip** | Everything else. Write a one-line reason |

**Skip is the default.** Anything failing (a)–(d) lands there. Adding documentation and adding tests are both work — do not slip them in because they are cheap.

Typical Skip material:

- **Questions of intended behaviour** ("which behaviour is correct?") — do not put these in Hold and do not ask the user. Skip them and leave the question as one line in the Spec
- **Compatibility that only affects third-party themes or downstream users** — skip when the first-party path is self-consistent
- Future-proofing, conservative over-approximation of performance, Info-level omissions

A question a repository policy file (CLAUDE.md and friends) has already settled goes to Skip, citing that policy.

## The Spec is mandatory on every path

`superpowers:brainstorming` says bounded and spike paths need no Spec. **Here the user's instruction wins: write a Spec on all three paths.**

- Location: follow the repository's own rule (in this repository, `$TOPLEVEL/docs_draft/superpowers/` — always the parent; `docs_draft/` is only gitignored there, so a Spec must never go under `$MAIN_ROOT` when `MAIN_ROOT` is `public/`)
- Naming: `YYYY-MM-DD-<topic>-review-fixes-design.md`
- Required contents:
  - Every finding and its bucket (drop none)
  - A one-line basis for each Resolved and each Skip
  - Fix approach and verification method per Fix item
  - The path brainstorming classified

## Scope

Work only on the resolved review directory and the branch / PR it reviews.

- **Do not go read uncommitted changes in other worktrees or branches.** If you find them, keep them out of the plan
- Do not go hunting for problems the reviews did not raise
- Implementation comes after approval. Do not edit product code during planning
- After implementation, land on the reviewed PR. Do not open a second PR
- After landing, post review status, decisions, and results on the reviewed existing PR. Posting without implementation is optional (任意). Do not open a second PR

## Rationalizations and what is actually true

| Excuse | Reality |
|---|---|
| "It is bounded, so no Spec" | The user's instruction outranks the skill. Write one on all three paths |
| "I presented the whole plan, so approval is implied" | Presenting is not approving. Wait for an explicit go-ahead |
| "One line of docs is not over-fixing" | Docs are work too. Failing (a)–(d), it goes to Skip |
| "It needs a design call, but it is only one extra test" | Adding a test is work. If a call is needed, ask for the call |
| "There were already changes in another worktree, so let me build on them" | A diff of unknown provenance is out of scope. Look only at what you were given |
| "Four models flagged it, so obviously fix it" | The basis is reproduction at current HEAD, not vote count |
| "I can design this myself, so skip brainstorming" | Path classification and the approval gate live in brainstorming |
| "The working tree shows it fixed, so it is resolved" | That may be someone's uncommitted diff. Confirm with `git show <HEAD>:<path>` |
| "Fixing the required-template contract solves it at the root" | Third-party compatibility work. If policy settled it, skip it |
| "It is a question of intended behaviour, so let me ask" | Hold is for few-line latent-bug fixes. Behaviour questions go to Skip plus one Spec line |
| "進めて is implementation only, not commit/push" | This section is the commit/push instruction. After related tests pass, land |
| "Related tests are not enough; CLAUDE.md wants verify.sh full" | Local landing gate is related tests. Full verify is CI on the existing PR |
| "Don't commit unless the user types commit" | This section is that instruction for this workflow |
| "Present the finishing-a-development-branch menu" | Do not. Push to the existing PR |
| "Review fixes get their own PR / that's how #144 did it" | Push to the existing reviewed PR. Extra `*-review-fixes` PRs are out |
| "The extra review-fixes branch already exists, throwing it away is waste" | Sunk cost. Land on the reviewed PR's head branch |
| "The plan is enough in chat" | After landing, leaving results on the PR is part of landing; planning-only turns post only optionally (任意) |
| "I did not implement, so I should not post" | Planning-only posting is optional (任意); only landing turns must post |
| "I already pushed, so a comment is unnecessary" | Leaving results on the PR is part of landing |
| "--edit-last is enough" | That overwrites another agent sharing the same GitHub account. Update only the comment with this agent's marker |

## Red flags — stop and return to the procedure

- You cannot state the Spec's path
- You cannot state the reproduction steps for something you put in Fix
- A finding or review artifact brought in from outside the resolved review directory, or an uncommitted source/test file, is load-bearing as verification evidence (review artifacts inside the resolved directory are valid input whatever their tracking state)
- You are about to implement without the user's explicit go-ahead
- For a finding placed in Fix / 対応する, you cannot show which of (a)–(d) it satisfies and the evidence
- A Resolved verdict rests on a working-tree file
- Hold contains a question about intended behaviour
- You are about to run `./scripts/ci/verify.sh full` or `./scripts/ci/verify-devenv.sh` as a condition of commit/push
- You are about to open a new PR for the review fixes, or push a `*-review-fixes` branch
- You are about to present the `finishing-a-development-branch` menu
- You are waiting for a second "commit" / "push" after related tests passed
- You are about to commit with failing related tests
- You are about to write `review-fix-planning-*` directly under `${TMPDIR:-/tmp}`
- You are about to skip `worktree remove` and only `rm -rf` (breaks git registration)
- You are about to leave `$REPRO_ROOT` in place after step 3
- You are about to use a hyphenated name (`review-fix-planning-wt`, `-head`, `-repro-root`) instead of `mktemp`
- You are about to finish a landing turn (commit / push) while the reviewed PR is open and no status comment was posted
- You are about to use `gh pr comment --edit-last`
- You are about to edit another agent's PR comment
- You are about to create a new comment when this agent's marker already exists
