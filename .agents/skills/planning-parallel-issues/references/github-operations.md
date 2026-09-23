# GitHub operations and ownership

Use authenticated repository tools or `gh api`. Verify the repository/default branch and write authorization from the request/session before writes. For multiline bodies use structured arguments or files (`--body-file`); never interpolate untrusted Issue text into shell code.

Before declaring the board operational, inspect repository permissions, rulesets/branch protection applicable to `agent-claims/*`, and workflow event/branch filters. Record the required Issue-write/content-write access and the evidence that claim creation, reading, and exact-lease deletion are supported. Record any applicable automation, following the repository's existing execution policy. A blocked or unverified claim protocol leaves publication incomplete; do not replace it with comment-only ownership. Use read-only inspection and existing evidence; creating a probe ref is not mandatory. When an endpoint explicitly says that rulesets or branch protection are unavailable for the repository's plan, record the endpoint and response as evidence that this mechanism imposes no applicable restriction, then continue the remaining permission, workflow, and claim-capability checks. A permission-denied or otherwise ambiguous `403`/`404` remains unverified and blocks publication. The taking session rechecks these constraints with its own credentials before acquisition. This is an operational check, not a new approval gate.

## Native relationships

REST paths below are relative to `/repos/{owner}/{repo}`. `N` is the displayed Issue number; payload IDs are numeric database IDs, **not** Issue numbers or GraphQL node IDs.

| Action | Method/path | Payload or result |
|---|---|---|
| Read/create/edit Issue | GET/POST/PATCH `/issues[/N]` | Save returned `number`, `id`, `node_id`, `html_url` |
| Read children | GET `/issues/N/sub_issues` | Follow pagination |
| Read current parent | GET `/issues/N/parent` | Compare the returned parent's database `id` with the verified superseded parent before reparenting; for an otherwise readable child, 404 `No parent issue found` means it currently has no parent |
| Add/reparent existing child | POST `/issues/N/sub_issues` | `{"sub_issue_id": CHILD_DATABASE_ID}`; omit `replace_parent` when the child explicitly has no parent, and add `"replace_parent": true` only for a verified reparent |
| Verify an uncertain reparent | GET `/issues/CHILD/parent`, then GET `/issues/OLD_PARENT/sub_issues` and `/issues/NEW_PARENT/sub_issues` | Follow every child-collection page before retrying or declaring success |
| Remove child | DELETE `/issues/N/sub_issue` | `{"sub_issue_id": CHILD_DATABASE_ID}` |
| Read blockers | GET `/issues/N/dependencies/blocked_by` | Follow pagination |
| Add blocker to child N | POST `/issues/N/dependencies/blocked_by` | `{"issue_id": BLOCKER_DATABASE_ID}` |
| Remove blocker from child N | DELETE `/issues/N/dependencies/blocked_by/BLOCKER_DATABASE_ID` | The path uses the blocker's database ID; no body |
| Read/post child comments | GET/POST `/issues/N/comments` | Before state selection, GET every page (for example, `gh api --paginate /repos/{owner}/{repo}/issues/N/comments`); `{"body": "..."}` for POST |

Read every page of existing native relations before mutation. Reuse Issues with matching goal/scope and preserve existing unrelated text/links. Record the stable board/child keys and returned IDs in the parent Issue's Publication ledger after each Issue write, and read that managed section back before ending the session; a local ledger is only a staged copy. Treat a relation as managed only when the published ledger and current Issue bodies identify the child with this board; a dependency is managed only when both endpoints are managed children. Retain verified superseded-parent evidence in the ledger until exact refetch confirms the move. Immediately before a reparent, GET the child's current native parent. Use `replace_parent: true` only when the returned parent database ID matches the superseded same-goal board identified by both the ledger and current Issue bodies. If an otherwise readable child returns 404 `No parent issue found`, add it to the canonical parent without `replace_parent`. If the parent read is unavailable or instead returns an unknown parent, preserve the relation, report its IDs, and leave the board incomplete. Do not infer missing ledger evidence, or delete or reparent any extra relation whose ownership or purpose is unverified.

For an existing board, derive additions, verified reparents, and removals from one comparison of the fresh actual graph with the canonical direct-predecessor list. After a timeout or lost response, refetch the exact relation before retrying; for an uncertain reparent, GET the child's parent and every page of both the old and new parents' child collections. Never blindly repeat a write that may have succeeded. After edits, refetch every page and compare the managed child and dependency sets with the canonical graph. Any unknown extra or required relation failure keeps the board incomplete.

References: [Sub Issues](https://docs.github.com/en/rest/issues/sub-issues), [Issue dependencies](https://docs.github.com/en/rest/issues/issue-dependencies).

## Fixed-ref claim protocol

Use one repository-wide namespace: `refs/heads/agent-claims/issue-N`. Every participating session must follow the same protocol. An assignee/comment informs people but cannot exclude another session. A normal push of the same base SHA can report success to two sessions and is not acquisition.

1. Freshly fetch the target branch and obtain its commit SHA and tree SHA. Generate a session UUID and UTC timestamp. POST `/git/commits` with `tree` set to that tree, `parents` containing that base commit, and a message containing the Issue number, UUID, and timestamp. This is a session-unique empty commit; it changes no source tree.
2. Persist the returned claim SHA with repository, Issue, UUID, ref, base, and time **before** attempting to create the ref. It remains immutable for the claim's lifetime; work commits live on a separate feature branch.
3. POST `/git/refs` with `ref` equal to the full claim ref and `sha` equal to the persisted claim SHA. A successful new creation acquires it. On an error or lost response, GET `/git/ref/heads/agent-claims/issue-N`: your persisted SHA means your earlier request succeeded; another SHA means occupied; absence means classify the actual error before retrying. Do not assume every 422 is a race or overwrite an existing ref.
4. Recheck eligibility and ref ownership, then record owner/session/ref/SHA/purpose in the child. Recheck before subsequent external writes or source edits. Leave another owner's claim intact regardless of age. To recover an abandoned claim, use a separate explicitly authorized ownership-resolution action, not a timeout heuristic.
5. After verified publication or recorded partial handoff, conditionally delete your ref using the exact SHA you saved:

   ```sh
   git push --force-with-lease=refs/heads/agent-claims/issue-N:CLAIM_SHA origin :refs/heads/agent-claims/issue-N
   ```

   Substitute validated Issue number and SHA; confirm `origin` is the claimed repository. Fetch the remote ref again to confirm absence. The lease prevents deleting a replacement owner. Do not use unconditional `gh api --method DELETE`, force-update the ref, or transfer it to another session. The receiver acquires a fresh claim after release.

Concurrent child sessions update their own child comments. One coordinator refreshes parent managed sections from fresh children. If multiple coordinators may write concurrently, serialize that work with the same claim protocol on the parent Issue number. Do not release another session's lock or roll back its assignee/labels after losing a race.

References: [Create commit](https://docs.github.com/en/rest/git/commits#create-a-commit), [Create reference](https://docs.github.com/en/rest/git/refs#create-a-reference), [Git push leases](https://git-scm.com/docs/git-push#Documentation/git-push.txt---force-with-lease).
