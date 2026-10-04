# PR #27 pi Migration JSON Safety Implementation Plan

- 文書管理／対象リポジトリ: `usaturn/create-reso-world`
- 対象Issue／PR: #19／#27
- 検証コードHEAD: `4ae2cb5af8cab7370b2933593ab1a3e3b8b8b19c`（Task 2）。Task 1は`26d8b1ca757179b9b9c3b406728f1fa1e700d664`
- 状態: completed（実装・独立レビュー・検証を完了。具体的な実行許可はSpecに記録し、コミットだけでapprovedにはしない）
- 今回更新するPlan: `docs/superpowers/plans/2026-10-04-pr27-pi-migration-round2-review-fixes.md`。従来版はGitの`26d8b1c`・`4ae2cb5`から参照する。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax. User already authorized recommended fixes and push; no second approval stop. Only controller commits and publishes, as one cohesive commit after review and verification.

**Goal:** Prevent partial pi migration and loss/corruption of unrelated settings/models on numeric, Unicode, lockfile and repeated-setup edge cases.
**Architecture:** Extend preflight and share a small strict JSON utility between cleanup and existing provider setup writers. Preserve existing pi/npm removal and provider-selection policies. Keep model-save staging and backups safe without introducing a new subsystem.
**Tech Stack:** Python stdlib, zsh, unittest, real offline npm/pi, uv.
**Spec:** `docs/superpowers/specs/2026-10-04-pr27-pi-migration-round2-review-fixes-design.md`

## Global Constraints

- No pr-review, real credentials, actual user configuration, registry or external API mutation.
- Preserve cleanup path/link/hardlink safety, unrelated settings/providers/auth/native MCP, original-byte backups, file modes and clean rerun bytes.
- Unsupported numeric tokens must stop cleanup before backup, pi calls or state unlink. Valid escaped surrogates must round-trip, not be rejected.
- Exact `~` and `~/` only are HOME-expanded; no eval or other-user expansion.
- No arbitrary npm lockfile edits. Detect target-containing shadowed package-lock with shrinkwrap and explain reconciliation before mutation.
- Keep DeepInfra cp failure propagation and auth mode 0600/no auth backup. Existing model-save failure and validation guards remain effective.
- Only controller manages refs, commits, pushes and PR/Issue updates. Do not merge after fixes. No force push or second PR.
- All scratch/logs belong to the plan's isolated workspace/temporary parent; all subprocesses are synchronous and awaited.

## Review Focus

- Integer tokens beyond Number's finite range (not merely float exponents): test cleanup and setup rejection before mutation.
- Valid escaped surrogates in object keys, arrays and values: test parsed value equivalence and actual pi model loader.
- Two root lockfiles where npm ignores package-lock: real npm success controls and refusal before any pi call.
- Same-time setup and failed writes: test original backup generations/modes and live-file preservation.
- Related provider auth/models at tilde/space paths: test expected HOME, original unrelated providers and auth, absence of cwd literal tilde.

### Task 1: Repair the shared migration and setup JSON safety boundaries

**Files:**
- Create `.devcontainer/pi_json.py` (strict object decode + fully serialized atomic save utilities).
- Modify `.devcontainer/cleanup_pi_mcp.py`, `.devcontainer/setup_pi.zsh`, `.devcontainer/setup_pi_opencode_go.zsh`, `.devcontainer/setup_pi_commandcode_goat.zsh`.
- Modify `.devcontainer/tests/test_pi_mcp_cleanup.py` and relevant existing setup tests if necessary. Add focused test file/wrapper only if needed; ensure run-tests includes it.
- Modify `.devcontainer/README.md` only to explain actionable numeric/dual-lock stop and safe setup saving/backups.

**Interfaces:**
- `load_object(path: Path) -> dict`: UTF-8-sig strict JSON object, rejects nonstandard constants and numbers outside finite JS Number range while retaining accepted integers as int; errors include path.
- `write_object(path: Path, data: dict) -> None`: serialize with ensure_ascii=True/allow_nan=False and newline before opening output; unique same-directory temp, preserve existing mode (new 0600), flush/replace, unlink temp on failure.
- Cleanup retains its existing `read_object` safety/missing-file behavior, delegating decode to utility. Existing module direct-guard test uses runpy; ensure helper import works without relying on caller cwd.
- Shell inline setup snippets locate helper from the repository model source's parent, independent of project cwd. Do not require installation of a new dependency.

- [x] Step 1: Add named failing end-to-end regression tests for each R3-1 through R3-6; use raw numeric tokens, fake pi call logging, full storage snapshots and frozen-date backup fixtures. Add positive controls for finite bounds/zero/Unicode/single-lock/noop. Test invalid source and write/backup failure without weakening original guards.
- [x] Step 2: Run only new regressions before any implementation; record expected assertion failures per repair group. Existing baseline was 58 passing. Run with `PYTHONDONTWRITEBYTECODE=1` and scratch `TMPDIR` inside isolated parent.
- [x] Step 3: Implement strict parser and lossless serializer. Wire cleanup decode and ASCII-escaped existing settings writer, leaving its preflight checks intact. Add shadowed-lock preflight before backup/removal. Avoid automatic lock pruning.
- [x] Step 4: Wire existing provider setup inputs and safe saves to helper; preserve current provider behavior, source validation, zsh error propagation, post-validation, and mode/no-auth-backup. Make model backups unique without removing the cp failure guard. Apply exact tilde expansion to two related setup scripts.
- [x] Step 5: Run new tests GREEN and all existing cleanup/setup tests synchronously. Include one real pi no-prefix numeric refusal/surrogate success and real npm lock controls. Confirm model output using installed credential-blind loader/Node JSON parse, with no API connection. Run applicable bash syntax, diff checks and targeted environment scripts; leave a detailed report with commands, results, RED evidence, coverage, concerns and task timings.
- [x] Step 6: Self-review full change and provide report. Do not commit; controller will create review packages including untracked files, obtain Task/spec-quality and final branch review, run full `.devcontainer/run-tests.bash` and layout, verify pristine main exceptions, then commit/push once.

### Task 2: Refuse linked destinations and invalid inputs before any change (R4-1〜R4-4)

**Files:**
- Modify `.devcontainer/pi_json.py` (add `require_plain_file`; `write_object` checks it first).
- Modify `.devcontainer/cleanup_pi_mcp.py` (`read_object` reuses `require_plain_file`; keep `safe_storage`).
- Modify `.devcontainer/setup_pi.zsh`, `.devcontainer/setup_pi_opencode_go.zsh`, `.devcontainer/setup_pi_commandcode_goat.zsh` (preflight every file the script may write before backup/chmod/write).
- Modify `.devcontainer/tests/test_pi_mcp_cleanup.py`, `.devcontainer/README.md` (setup and builtin MCP sections), root `README.md`, and the Issue #19 Spec/Plan headers and comparison table.

**Interfaces:**
- `require_plain_file(path: Path) -> None`: `lstat` only; absent is allowed; symlink (including dangling), non-regular file and `st_nlink != 1` raise `ValueError` containing the path.
- Setup preflight: `python3 - <models source> <files...>` imports the helper from the model source's directory, loads the model source, checks each file the script may write with `require_plain_file` and loads it when present, prints `ERROR: <reason>` once and exits 1 under `set -e`. It runs before backup, chmod and any write; main blocks keep their checks with the duplicated prefix removed.

- [x] Step 1: Add `test_r4_shared_writer_refuses_linked_or_special_destinations`, `test_r4_provider_setups_refuse_linked_destinations_before_changes` and the control `test_r4_provider_setups_accept_symlinked_agent_directory`, with an lstat-based snapshot of the agent directory and shared targets.
- [x] Step 2: Run them before implementation. RED: the writer staged a temp file for all 5 kinds, and all 15 setup cases exited 0. The control already passed (existing behavior to keep).
- [x] Step 3: Implement the helper, the writer check, the cleanup reuse and the 3 setup preflights. Update the README setup section, including the wording of the same-directory temp-file replacement.
- [x] Step 4: Run the new tests, existing link/hard-link/FIFO cleanup tests, the whole migration/setup suite, related bash checks, the full environment suite, layout and skill tests synchronously.
- [x] Step 5: From the independent whole-PR review, strengthen the unsafe-number and invalid-source setup tests to compare the whole agent directory and count the path once, require no backup for broken models JSON, and assert `Invalid JSON constant` in the constant test (RED: 32 setup failures; constant test verified by a mutant that disables `reject_constant`). Extend the preflight to the inputs (R4-2), restore the guard (R4-3), and fix the documents (R4-4).
- [x] Step 6: Re-run the related tests and the full environment suite, layout and skill tests. Commit once, have an independent agent re-review the whole PR at that commit, fix and re-verify until no finding remains, then push `HEAD:refs/heads/feat/issue-19-pi-migration` normally.

## Controller integration and publication

- Use new detached implementation worktree at pinned PR HEAD; merge latest origin/main with `--no-commit --no-ff` before Task 1 so the final single commit also preserves main ancestry.
- Read and package all owned diffs including new files. Run independent Task review with spec and quality verdicts; then final whole-branch review against fixed merge-base. Fix findings before final commit.
- Full environment suite and direct layout, plus changed-path active LSP. Compare any known layout failure to pristine origin/main, keeping worlds/ResoLoop unchanged.
- Fetch, verify existing remote PR HEAD has not advanced, commit merged main plus repairs once, push `HEAD:refs/heads/feat/issue-19-pi-migration` normally.
- Upsert own existing status comment with precise model marker and all classifications/decisions/results. Record missing actual-auth/registry/rebuild checks. Since fixes were needed, keep PR and related Issues open.

## Self-review

All six repair groups map to Task 1 and share JSON/storage boundaries; batching avoids conflicting implementers on the same fixture. Existing guards are preserved, shadowed-lock tests distinguish intentional preflight refusal from successful single-lock migration, and no new source of truth or external dependency is introduced. Spec, signatures and tests agree. Public commit and main integration are controller-only.

## 完了記録

Task仕様・品質レビューの指摘（backup重複／mode）は公開前に修正し、限定再レビューとPR全体最終レビューに未解決指摘なし。controllerの最終検証は移行・setup76テスト、環境27/27スクリプト、layout、スキル408成功・1skip（最新main統合後）、実PR差分検査が成功。main `4e6f1d0`の取り込みで以前のslum03同期失敗も解消済み。公開前にさらに進んだmain `fc5c7ea`も競合なく取り込み、レビュー済みのruntime不変と全体再検証を確認した。詳細・未検証境界はSpec、公開SHAと所要時間はPRコメントに記録する。既存PRへ追加1コミットで通常pushし、今回はマージしない。
