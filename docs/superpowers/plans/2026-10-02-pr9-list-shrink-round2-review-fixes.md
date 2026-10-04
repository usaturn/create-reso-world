# PR #9 Index Recovery and List Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A failed index refresh following Component deletion must never rebind a managed key to an unrelated Component after a world reload; document the actual list-recreate scope.

**Architecture:** Persist a provisional invalid index on affected Slot bindings before deletion, then refresh and checkpoint indexes after deletion. If the session changes before refresh, reject positional rematching before mutation. Preserve same-session recovery through saved IDs; never infer an absent Component by type and position. No new state schema or implicit destructive consent.

**Tech Stack:** .NET 10, C#, xUnit; fork `usaturn/resoloop`.

**Spec:** `docs/superpowers/specs/2026-10-02-pr9-list-shrink-round2-review-fixes-design.md` in the enclosing create-reso-world repository.

## Global Constraints

- Only the approved PR #9 findings (xai M-2, commandcode L-3, qwen L-2).
- Read/implement on the existing `fix/list-shrink-recreate-split` branch; never create a new PR.
- Preserve `--prune --yes`, reject ambiguous matches before writes, keep live Resonite tests opt-in.
- The review-fix-planning approval already authorizes implementation, commit, push and same-PR status comment after related tests pass; do not gate on unrelated full-fork tests.

## Review Focus

- An unmanaged same-type Component behind a removed managed sibling stays unchanged after a failed index refresh and reload: Task 1.
- A failed index read followed by a same-session retry repairs and persists indexes: Task 1.
- A lost remove response after successful deletion keeps the pending checkpoint safe on both same-session and reload: Task 1.
- Relocation that removes a source Component cannot silently rebind a remaining sibling after reload: Task 2.
- Direct `fields` list versus nested `syncObject` list: Task 3.

---

### Task 1: Checkpoint invalid indexes around prune and recover safely

**Files:** Modify `external/resoloop/src/RLoop.Core/WorldService.cs` and `external/resoloop/tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs` (paths relative to outer repository).

**Interfaces:** `MarkSlotIndexesUnverified(PreparedApply prepared, string slotKey)` sets saved indexes of matching Slot keys to `-1` and checkpoints before removal; `ReconcileUnverifiedIndexesAsync(PreparedApply prepared, ApplyOptions options, CancellationToken cancellationToken)` repairs by saved ID and removes missing undeclared keys only when prune was explicitly requested. Both stay private. `MatchComponent` must not use position/ordinal when index is `-1` and saved ID does not match.

- [ ] Add `APruneInterruptedBeforeIndexSaveCannotWriteToAnUnmanagedSiblingAfterReload`: initial managed v1,v2 and unmanaged same-type with `Value=999`; cancel directly after v1 removal; assert saved v2 index is invalid; reload; apply without prune rejects before any write; unmanaged value remains 999. Run a targeted `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter FullyQualifiedName~APruneInterruptedBeforeIndexSaveCannotWriteToAnUnmanagedSiblingAfterReload` and confirm red on the invalid-index assertion or unmanaged mutation.
- [ ] Add same-session recovery test and lost-removal-response case for prune: no rebind, accurate saved index, absent removed key is cleared after explicit `--prune --yes` retry; verify red where new recovery is required.
- [ ] Implement provisional checkpoint *before* `RemoveComponentAsync`, then final checkpoint after `SaveSlotIndexesAsync`; preflight rejects session changes with pending `-1` before `BuildComponentPlans` / `BuildDeletionPlans`, with an actionable validation error. Repair pending state by ID at start of apply, before other mutations, and persist.
- [ ] Run focused SlotIndexes tests and confirm green.

### Task 2: Protect movement/recreate deletion paths

**Files:** Same WorldService and SlotIndexes files; optionally `ApplyWorkflowTests.ListShrink.cs` for an affected recreate case.

**Interfaces:** Reuse Task 1 marking/reconciliation for each Component removal that shifts indexes; do not introduce a second pending encoding.

- [ ] Add relocation interruption after source removal, then reload; assert no write to unrelated Component and no silent binding. Run targeted test and confirm red.
- [ ] Use the common before-remove marking before relocation and, if needed, recreate/undo removal; ensure successful writes clear pending marker. Run relevant filtered `ApplyWorkflowTests` and confirm green.

### Task 3: Correct list shrink documentation

**Files:** Modify fork `docs/DECLARATIVE.md`, `README.md`, `README_JA.md`. No nested-list behavior change.

- [ ] Compare `ListShrinkReason` and `AShorterListInsideASyncObjectIsNotRecreated` with the existing prose: only direct `fields` list members produce `recreate`; nested lists are outside this path and have no convergence guarantee.
- [ ] Update the inaccurate general statements in these three documents; rerun `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter FullyQualifiedName~ApplyWorkflowTests`.

### Task 4: Verify and reflect on existing PR

- [ ] Run test filters that cover all changes, then `dotnet test` for the affected `RLoop.Tests` project (not unrelated fork-wide suites). Confirm zero failures and capture counts.
- [ ] Review `git diff --check`, status, source diagnostics if available, and PR head SHA after `git fetch origin`; do not incorporate other worktrees' changes.
- [ ] Commit on `fix/list-shrink-recreate-split`, push `origin HEAD`, confirm remote PR head, then upsert one Japanese review-fix-planning comment using the supplied helper and `PI_PROVIDER`/`PI_MODEL`. Do not create another PR.
