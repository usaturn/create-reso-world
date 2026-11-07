---
name: planning-parallel-issues
description: Use when a task needs a GitHub parent Issue and parallel Sub Issues, an existing Issue board needs dependency or ownership boundaries, or an agent must select a ready child from a parent Issue and prepare its implementation handoff.
---

# Planning Parallel Issues

Make the parent Issue the entry point for independent sessions. Parallelism comes from explicit dependencies and disjoint ownership; readiness comes from fresh evidence. A claimed planning task ends with recoverable Spec, Plan, and handoff artifacts.

Announce this skill. Read repository instructions, existing Issues, code, and available skills before writing. Use the user's language for Issue bodies and reports.

## Target repository

Boards, Issues and claim refs live in `usaturn/create-reso-world`, this repository's `origin`. Before the first write, confirm that `git remote get-url origin` names it, and use it wherever the references write `{owner}/{repo}`. Work on ResoLoop itself belongs to the fork (`usaturn/resoloop`, checked out at `external/resoloop`) under the repository boundary table in the root `AGENTS.md`; build a board there only when the user names that repository. Do not build a board in any other repository. A child may still name another repository as its implementation target: record its exact identifier (`owner/repo` on GitHub), and the checkout only when the user or a verified handoff names it (`CODE_ROOT`). Its Spec and Plan go where the root `AGENTS.md` ("Spec・Plan の保存と公開") puts them: in `usaturn/create-reso-world`, unless the target repository commits the declaration line in its own `AGENTS.md` (`docs/superpowers/README.md`). A declared target keeps them in its own `docs/superpowers/`, committed in the checkout the user or a verified handoff names; without that checkout, stop instead of committing them in create-reso-world. Stop instead of guessing when the target or its checkout is unclear.

## Choose the requested operation

| Request | Required procedure | Finish line |
|---|---|---|
| Decompose a task; create/update parent and Sub Issues | Read [issue-board.md](references/issue-board.md) and [github-operations.md](references/github-operations.md) | Published board, native relationships, verified entry instructions |
| Start from a parent; take a ready child | Read [session-workflow.md](references/session-workflow.md) and [github-operations.md](references/github-operations.md) | One child's Spec → Plan → paired handoff, recovery verified, claim released |
| Both | Build/verify the board, then take one eligible child | Both finish lines |

Reuse existing Issues and valid artifacts. Board creation alone does not claim every child. A URL without a clear action inherits the conversation's request; do not silently replace “update the board” with implementation.

## Completion rules

- **Board:** concrete acceptance criteria, dependency DAG, file ownership, shared-interface owner, verification, native Sub Issues and `blocked_by`, and a self-contained start instruction in the parent. Follow the required output slots in the reference.
- **Selection:** refresh children, every comment page, dependency outcomes, PRs, and claim refs before deciding. A single comments response is incomplete evidence; with GitHub CLI, use `gh api --paginate`. A parent's Ready label is a snapshot. Only a predecessor closed with `state_reason=completed` satisfies the default completion gate. `not_planned` and `duplicate` are unsatisfied; replace a duplicate predecessor with its canonical Issue in the board and verify that Issue before selection. An unmerged required PR or another session's claim also blocks selection.
- **Ownership:** create a unique empty claim commit and atomically create one fixed remote ref. Save its SHA before ref creation. Recheck ownership before writes; release with an expected-SHA lease. Comments and assignees are visibility, not locks.
- **Planning:** REQUIRED SUB-SKILLS: `superpowers:brainstorming`, then `superpowers:writing-plans`, then `agent-handoff`. The user's requested artifacts require the written-spec path even for bounded children. Use recommended choices and continue through all three. Record agent decisions, not invented human approval. User authorization overrides routine approval/“which execution mode?” pauses.
- **Recovery:** publish exact artifact contents with hashes and restore them into a fresh directory before announcing readiness. A local path or commit that was never published is insufficient.
- **Boundary:** an implementation child stays open with `planning: ready`, `implementation: not-started`. Code, implementation tests, merge, and deployment need their own authorized execution task. An undefined execution route — general external implementation or remote-less PR integration — is a blocker recorded in the handoff with its execution authority absent; planning completion alone does not make it ready. The existing approved PR review-fix implementation route through review-fix-planning remains supported with explicit validated CODE_ROOT; general external/Issue implementation does not inherit it. No eligible child means report blockers and finish without holding claims.

## Common mistakes

| Temptation | Required action |
|---|---|
| “Comment, assign, then reread prevents a race” | Atomic creation of the fixed ref with a session-unique SHA |
| “The old claim is probably abandoned” | Leave it intact; report its owner/ref |
| “The files exist on this host” | Verify a remote round trip of every artifact |
| “The spec is done; ask before the plan” | Continue with the recommended choice through handoff |

Stop and repair before declaring success if ownership is uncertain, parallel children edit the same shared interface, or any handoff artifact cannot be restored.
