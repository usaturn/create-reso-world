# Taking one child through planning handoff

## Select from live evidence

Read the parent as the entry point, then fetch native children, current bodies, every page of comments, dependencies, PR states, and claim refs. Do not treat the first comments response as complete evidence: follow pagination before state selection, using `gh api --paginate` when using GitHub CLI. Verify target-branch inclusion for required changes, not just a closed Issue. Default eligibility requires each predecessor to be closed with `state_reason=completed` and its necessary PRs merged. `not_planned` and `duplicate` are unsatisfied; replace a duplicate predecessor with its canonical Issue in the board and evaluate that Issue before selection. For artifact-only predecessors, require their explicit completion evidence. An earlier planning gate is usable only if the board names it and its required inputs are verified.

Skip claimed children and already planning-ready children with valid recoverable artifacts. Select one eligible child, using the board's priority or the smallest number as a stable tie-breaker. If resuming a named planning-ready child, validate/recover its artifacts and report that endpoint instead of generating duplicates. If nothing is eligible, report each blocker and finish without polling indefinitely or accumulating claims.

Acquire and validate ownership with [github-operations.md](github-operations.md). Check readiness again after acquisition. If it changed, release your own claim and reevaluate. Track elapsed time and major task durations when repository policy requires it.

## Continue without routine approval pauses

The requested endpoint is **Spec → Plan → agent-handoff**, using recommended choices. Read and apply those installed skills in sequence; do not merely imitate their headings. This workflow carries the user's authorization to complete routine planning steps. Record recommended choices and their rationale as agent decisions, never as human approval. Do not stop at a design presentation, after the Spec, or at writing-plans' execution-mode choice.

The user explicitly requires written artifacts for every child. This takes precedence over brainstorming's bounded-task shortcut that omits Spec and Plan. Use its written-spec path even for a small existing-code change; scale document detail to the task, then continue to writing-plans and handoff. Do not reclassify a simple change as complex merely to justify the requested documents.

| Observable condition | Action |
|---|---|
| Existing full-text Spec/Plan with hash | Restore exact bytes, verify, inspect fit with current Issue/base, reuse valid portions |
| Ordinary ambiguity with a compatible default | Choose the recommendation, record alternatives/reason, continue |
| Spec changes while planning | Update Spec and its hash, then reconcile Plan and handoff |
| Valid completed planning handoff | Recover and verify; do not restart brainstorming merely to recreate files |
| Missing required input/authorization or scope-changing unresolved decision | Preserve partial artifacts, record blocker and specific recovery action; release your claim after recording progress |
| Required skill missing | Search installed skills; report exact missing dependency if unavailable, preserve partial work; never label a substitute as having run that skill |
| Undefined implementation route (general external implementation, or remote-less PR integration) | Record the blocker and missing authorization in the handoff (`sources.execution_authority`: null); the child is blocked / not ready for implementation, not executable |

The existing approved PR review-fix implementation route remains supported through
review-fix-planning with explicit validated CODE_ROOT. General external/Issue
implementation does not inherit that permission. Before resuming implementation,
check the committed approved/current Spec and Plan and the specific execution
authority using agent-handoff's Continuation gates. Metadata-only record additions
retain approved_commit while document_commit advances; substantive changes require
renewed approval unless the recorded authority names that change. Missing v2 facts
are unknown; completed/superseded/cancelled Plans do not resume ordinary implementation.

An existing artifact's hash establishes byte identity, not design validity. Before writing new artifacts, search the current Spec/Plan by target repository, Issue/PR, theme and canonical path (`docs/superpowers/specs/`, `plans/`), not by basename or date alone. Reuse and update the current canonical document for ordinary review fixes; do not generate roundN files by default. If more than one plausible canonical document exists and successor links or explicit paths cannot settle it, stop and ask. Creating a genuinely new Spec requires a recorded explicit reason, such as an independently approved architectural redesign. The committed-draft invariant stays: submitted Spec/Plan draft content must be committed before a review copy is presented. Read its decisions and check current interfaces before accepting it. If inheriting another agent's artifacts, apply `agent-handoff` on the reading side too.

## Required artifact set

Determine paths from repository instructions. Superpowers defaults apply only when the repository does not override them. Ignored draft files still need remote recovery; do not force-add ignored artifacts merely to make links work.

Specs and Plans for a child are committed under `docs/superpowers/` of `usaturn/create-reso-world`, except when its code targets a repository that declares its own (the root `AGENTS.md` and `docs/superpowers/README.md`); those go in that repository's checkout (resolved by issue-to-pr for a registered tool, or named by the user or a verified handoff), and the child stops if there is none. When a person is asked to read one, first create the review copy with `bash scripts/superpowers-review-copy.sh` (add `--doc-repo <owner>/<repo>` for a declared repository) in the parent checkout's `tmp/superpowers-review/`. The copy is a viewing aid, not a recovery artifact; recovery still uses the published manifest below.

1. **Spec:** goal, scope/exclusions, constraints, proposed design, alternatives with recommended choice, interfaces, acceptance criteria, dependency evidence, and decided ambiguities. Use `superpowers:brainstorming`, including its review steps. Mark the continuation authority accurately.
2. **Plan:** use `superpowers:writing-plans`, including review. Link the real Spec; specify exact files, task sequence, interface details, meaningful verification with expected results, and landing constraints. Preserve child ownership and prerequisite gates. Implementation/test commands are future instructions, not claims of execution. Follow repository contingency requirements.
3. **Handoff pair:** use `agent-handoff` and its installed schema. Write `tmp/docs_draft/claude_handoffs/<timestamp>-<session>.handoff.md` and matching `.handoff.json`, with the same facts. Schema v2 requires `schema_version`, `generated_at`, `project_dir`, `session.id/stop_reason`, `decisions`, `out_of_scope`, `verification.commands/isolation`, `landing.branch/pr/prohibited`, `git.worktree/branch/head/status`, and `sources.spec`. Also include `sources.plan` and the next action. Populate actual Git facts, not the parent checkout by accident; verify every non-null source path exists. A not-yet-created PR is null, with its permitted creation/reuse policy stated. Record the lifecycle facts separately: `sources.approved_commit` (the committed content version a user approved, or `null` with the reason — never inferred from a status field or a review copy), `sources.execution_authority` (the explicit authorization to execute, or `null` with the missing rule stated as a blocker — blocked, not ready), `sources.completion_evidence`, and `sources.document_published` (null plus "公開未実施" for a local commit only). A recovery artifact never claims the review copy is canonical; restore from the committed canonical document.
4. **Recovery manifest:** store one entry per file with role, portable path, SHA-256, byte count, remote URL/comment ID, encoding/chunk order, artifact revision and base SHA. Retain original host paths only as provenance; explain how a receiver maps them to the new checkout and regenerates host-specific handoff facts. Link all entries from a final child status comment.

## Publish, recover, then release

Before each external write, confirm the claim still equals the saved SHA. Publish through authorized Issue comments or a repository location. Preserve exact bytes. Small files can use fenced full text; for reliable arbitrary content use base64 chunks with ordering and decoded byte hashes. Never publish credentials or private runtime logs. Include the full Spec, Plan, and both handoff files; a local path, summary, SHA alone, or unpushed commit is not recovery.

Fetch the published contents into a new empty directory without copying local originals. Decode/reconstruct all four files and verify manifest hashes and byte counts. Parse the handoff JSON, check required fields, compare its facts with Markdown, and resolve portable source paths in the reconstructed bundle. Check Spec/Plan consistency. Only after this round trip publish `planning: ready`, `implementation: not-started`, the manifest link and an actionable next step. Keep implementation Issues open; planning completion does not satisfy downstream implementation dependencies.

Release using the exact-SHA lease and confirm absence. A failed upload/round trip yields `planning: incomplete`, partial-result pointers, and a recovery action; release only your own claim after publishing progress. If GitHub is unavailable, save the recovery record locally and report an unreleased claim explicitly. A foreign SHA means ownership lost: stop writes and do not delete it. Never finish with an unexplained held claim waiting for the receiver.

Final response: child URL, actual four artifact paths/remote manifest, checks actually performed, planning/implementation state, claim-release result, and next action. Do not offer to create the Plan or handoff later; they are part of this task.
