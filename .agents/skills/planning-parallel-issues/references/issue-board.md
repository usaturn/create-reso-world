# Building an executable Issue board

## Inspect before splitting

Read repository instructions, the task, relevant code/tests, existing parent/child Issues and every page of their comments, and linked PRs. Identify the actual target repository and default branch. Reuse an existing board for the same goal; preserve its decisions and unrelated content. Record the source URLs and relevant base SHA.

Find shared interfaces, fixtures, configuration, generated files, and validation resources. Extract shared changes into a foundation child; give subsequent children disjoint file ownership or precise nonoverlapping sections. Specify how integration happens without both branches editing the registry. Do not remove real dependencies merely to make the graph look parallel.

Each child must be independently reviewable and small enough for one implementation session. Use as many children as the work requires. Separate final integration/measurement when it consumes multiple branches. A dependency means a concrete input: name that input and how its availability will be verified.

Create one canonical list of direct predecessor IDs for each child. Generate the parent table, child blocker lists, diagram, edge count, and native API writes from that same list. Describe transitive inputs separately from direct blockers: a CLI consuming two exporters also uses their shared interface, but that does not add another native edge when the interface already precedes both exporters.

## Required parent body, in this order

1. **Outcome and boundaries:** measurable completion criteria, exclusions, source Issues, current base branch/SHA.
2. **Execution map:** child links, purpose, owned files, predecessors, required input, completion evidence, planning state, implementation state. State when the snapshot was checked. Keep claim/state authority in fresh child data.
3. **Publication ledger:** a managed parent-body section containing a stable board key and, for each child, its stable child key, Issue `number`, database `id`, `node_id`, `html_url`, and canonical parent. Record managed dependency endpoints with their stable keys and database IDs. While a reparent is pending, retain the verified superseded parent's `number`, database `id`, and operation state until exact refetch confirms the move. This published section is the durable authority for later sessions; a local ledger is only a staged copy.
4. **Dependency DAG and parallel waves:** foundation, independent lanes, integration; native `blocked_by` must match the diagram. Describe any verification resources that cannot run concurrently, including the shared lock location and owner.
5. **Shared interface and ownership:** frozen signatures/artifacts, owning child, consumers, forbidden cross-child edits, and integration owner. If two children edit one file, identify nonoverlapping sections or move that edit to one owner.
6. **Operating rules:** readiness, claim namespace, required access and verified repository constraints, release, artifact storage/recovery, and distinction between planning-ready and implemented. The coordinator maintains the parent snapshot; child sessions publish status to their own child, avoiding concurrent full-body rewrites of the parent.
7. **Start instruction:** paste the complete block below, replacing repository-specific choices with actual values. The reader should need no earlier conversation or installed copy of this skill to identify and take a child.

### Start instruction to embed in the parent

Adapt the language to the user. Resolve the repository, default branch, artifact roots, verification commands, and skill locations from this repository; leave no unresolved placeholders in the published body.

> Start one child from this parent and finish its planning handoff in this session.
>
> 1. Read repository instructions, this parent including its Publication ledger, every page of native Sub Issues, each candidate's latest body, every page of each candidate's comments and `blocked_by` relations, required PRs, and `refs/heads/agent-claims/issue-N`. Do not treat the first response for any paginated collection as complete evidence: follow pagination before state selection, using `gh api --paginate` when using GitHub CLI. The table is a snapshot. Choose one open child only when each required predecessor is closed with `state_reason=completed`, required PRs are merged into the target branch, and needed interfaces/artifacts are available. `not_planned` and `duplicate` do not satisfy a dependency; replace a duplicate predecessor with its canonical Issue in the board and evaluate that Issue before selection. Artifact-only predecessors need their stated verified deliverables. If this board defines a separate earlier planning gate, verify its named evidence; implementation dependencies still apply. Existing claims, including old claims, exclude a child. Skip a child with an already valid planning handoff unless explicitly resuming it. If none qualifies, list blockers and finish without a claim.
> 2. Claim only that child. Verify current Issue-write and repository-content permissions, applicable ref rulesets, and workflow branch filters: this session must be able to create, read, and conditionally delete the claim ref under the board's recorded constraints. When an endpoint explicitly says that rulesets or branch protection are unavailable for the repository's plan, record the endpoint and response as evidence that this mechanism imposes no applicable restriction, then continue the other permission, workflow, and claim-capability checks. A permission-denied or otherwise ambiguous `403`/`404` remains unverified and blocks acquisition. If the protocol is unavailable, report the concrete blocker without acquiring a claim. Create a unique empty Git commit using the latest target-branch tree and parent, with Issue number, session UUID, and UTC time in its message. Persist the resulting SHA. Atomically POST a new Git ref `refs/heads/agent-claims/issue-N` pointing to that SHA. A normal push to the shared base SHA, assignment, or a comment is insufficient. On failure or uncertain response, GET the ref; only your persisted SHA proves ownership. A different SHA is another owner, even after two idle days. Never force-update or age-steal the ref. Record owner, session, ref, SHA, and purpose in the child.
> 3. Recheck the ref and readiness after claim and before external writes. Use an isolated worktree for any tracked work. Recover existing Spec/Plan/handoff artifacts from their published contents and verify SHA-256 before reuse. Read `agent-handoff` when inheriting previous work. Rebase local artifact paths to this host and record their source hashes.
> 4. Use `superpowers:brainstorming` to create or validate the Spec, `superpowers:writing-plans` to finish the Plan, and `agent-handoff` to write both `.handoff.md` and schema-version-2 `.handoff.json`. The user's requirement for written artifacts overrides brainstorming's bounded-task no-Spec/no-Plan shortcut: use the written-spec path even for a small change, scaling detail to its size. Follow repository artifact-path rules. Apply recommended defaults for ordinary ambiguity, record reasons/alternatives as agent decisions, and continue without routine confirmation or execution-mode pauses. Never invent human approval. Genuine missing authorization, unavailable required input, or an unresolved decision that changes scope must be recorded as a blocker, preserving completed work.
> 5. The handoff pair must agree on decisions/dispositions, exclusions, exact verification commands and isolation, landing branch/PR/prohibited actions, actual worktree/branch/HEAD/status, Spec/Plan sources, and next action. Validate required fields and existing non-null paths against the installed `agent-handoff` schema. Do not run the implementation or report its tests as passed during this planning task.
> 6. Publish Spec, Plan, and both handoff files as exact recoverable contents in the child or an authorized repository location. Publish a manifest listing artifact role, portable path, SHA-256, byte count, source URL/comment ID, encoding/chunk order, revision/base SHA, and planning state. For size limits split at UTF-8-safe boundaries or store base64 chunks; references or summaries alone are insufficient. Fetch only the remote copy into a fresh directory, reconstruct bytes, verify every hash, parse the JSON, and check Spec/Plan/handoff consistency. If permission or retrieval fails, planning remains incomplete; preserve local results and the exact recovery error.
> 7. Publish `planning: ready`, `implementation: not-started`, manifest URL, and the next action in the child; leave an implementation Issue open. Release the immutable claim only if it still equals your SHA, using `git push --force-with-lease=refs/heads/agent-claims/issue-N:CLAIM_SHA origin :refs/heads/agent-claims/issue-N`. Confirm the ref is absent. If the SHA differs, do not delete it; report ownership loss. If blocked, publish partial progress and a recovery action before releasing your own claim. Do not hold a claim while waiting for the next agent. Report actual artifacts and remaining work; let the coordinator refresh the parent snapshot.

## Required child body

| Slot | Concrete content |
|---|---|
| Parent and objective | Parent link; one observable result |
| Scope and exclusions | Separate lists of allowed edits and forbidden edits, with no path in both; owned files match the parent table |
| Dependencies | Predecessor links, exact input/evidence, default completion gate; any earlier planning gate must be explicit |
| Interface | Inputs/outputs, errors, frozen signatures and owner |
| Acceptance | Observable behavior and regression/detection constraints |
| Verification | Exact commands, working directory, required services/data, isolation/locks |
| Deliverables | Spec, Plan, handoff pair, recovery manifest; eventual implementation PR if required |
| State and landing | Separate planning/implementation states, claim protocol inherited from parent, target branch, PR reuse/creation policy |

## One worked split

For CSV/JSON export, use this graph:

```text
Interface and registry ─┬─ CSV exporter ──┬─ CLI integration
                        └─ JSON exporter ─┘
```

The canonical direct predecessors are `interface: []`, `csv: [interface]`, `json: [interface]`, `cli: [csv, json]`: exactly four edges. The CLI's transitive interface input is documented as an input, not a fifth `blocked_by` edge.

The foundation owns `app/export_registry.py` and `tests/test_export_registry.py`: the request/result interface and a registration mechanism requiring no later edits by exporter owners. CSV owns `app/csv_export.py` and its tests; JSON owns `app/json_export.py` and its tests. Integration owns `app/cli.py` and `tests/test_cli_export.py`, imports the exporters, and registers them through the frozen API. Exporter children never both edit the registry. Verification commands come from the actual project. Dependency completion requires the frozen interface to be available on the target branch, not just a checkbox ticked in the parent.

## Publish and verify

Before publication, compare every child's allowed and forbidden file lists with the parent ownership table. Each planned edit, including tests and registration, needs an owner; no child may forbid its own assigned files or silently edit a sibling's files. Correct contradictions across sections before writing to GitHub.

Use [github-operations.md](github-operations.md). After each Issue write, save returned IDs and URLs in the parent-body Publication ledger and read it back before depending on those values across sessions. Populate actual child links and reconcile native Sub Issue and dependency relations against the canonical predecessor list, not a separately handwritten count. Add, remove, or reparent only relations proven managed by the published ledger and current Issue bodies. Immediately before using `replace_parent: true`, read the child's native parent and require its database ID to match the verified superseded parent of the same board. If the readable child instead returns 404 `No parent issue found`, add it to the canonical parent without `replace_parent`. Preserve an unreadable or unknown current-parent relation and leave the board incomplete. After an uncertain reparent or add, refetch the child's parent plus every page of the relevant old and new parents' child collections before retrying or declaring success. Refetch every relation page after mutation and compare the managed edge sets with the canonical graph. Compare ownership lists, ledger, and bodies too. Check for cycles and duplicate children. The published start instruction and all linked inputs must be accessible to the intended agents.

An API error leaves a partially prepared board: report precisely which relationships or fields are missing and resume from saved IDs. Do not advertise it as ready or silently downgrade native dependencies to prose. Updating an existing board is a scoped edit of managed sections after rereading the current bodies and every comment page; never overwrite another author's unrelated changes.
