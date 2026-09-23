---
name: monitoring-long-tasks
description: Use when waiting for or supervising a long-running command, verification job, background process, or sub-agent where completion, liveness, progress, or stall detection matters.
---
# Monitoring Long Tasks

Completion (artifact or notification arrived), liveness (target process still exists), and progress (log output advancing) are separate signals; never infer one from another.

## Workflow

1. Wait for `report exists OR worker is not alive`; never wait on the report alone. The controller owns this wait and stall polling and keeps its turn until `report exists OR worker is not alive` resolves. A completion notification means a runtime process-exit notification carrying an exit status, not a report, artifact, or sub-agent result. It can satisfy the `worker is not alive` branch, but it is not permission to end the controller's turn while the worker is alive. Use runtime wait or notification facilities, never a foreground sleep loop. The only stop exception is a predeclared read-only PR review delegation past its deadline or progress cutoff (see `Predeclared PR review delegation deadlines`).
2. Treat exit without the expected report as abnormal: recheck the report once after observed death, then handle as failure and confirm the terminal `EXIT=<code>` in the log.
3. Prefer a known PID with `kill -0` for liveness. For `verify.sh`, take the numeric suffix from the printed log basename (`verify-<profile>-<timestamp>-<pid>.log`) and validate it against `^[0-9]+$`. After `kill -0` succeeds on a `verify.sh` target, verify the PID's identity: `ps -p <pid> -o args=` contains `scripts/ci/verify.sh`, and `readlink -f /proc/<pid>/cwd` equals the target worktree. If either identity check fails, treat the target worker as not alive; do not fall back to `pgrep` for that PID. For any other target, `kill -0` plus the intended command line and target cwd is enough; do not require `scripts/ci/verify.sh` in args. After either wait condition ends for `verify.sh`, confirm the terminal `EXIT=<code>` in its log.
4. Use `pgrep -f` only when no PID is available. Match the target command line, and keep the pattern in a script file or use a path-qualified bracket form such as `[s]cripts/ci/verify\.sh` so the pattern text itself cannot match. A bare target path elsewhere in the monitor command can still self-match. Inspect the matches, discard the monitor PID and every ancestor PID. When the target is `verify.sh`, apply step 3's `verify.sh` command/cwd identity to each remaining PID. When it is not, keep PIDs whose command line matches the intended target command and whose cwd is the target worktree. If none remains, the target worker is not alive. Never use the log path as the process marker or match a profile such as `full` alone.
5. Monitor the log path printed by `verify.sh`; do not require a fixed manual redirect.
6. Check log mtime, size, or last line about every ten minutes. Two consecutive unchanged checks mean report a stall; a live stalled task is never permission to kill it, except for a predeclared read-only PR review delegation handled under `Predeclared PR review delegation deadlines`.
7. Report before dispatching dependent work. Every status report carries task identity, actual log path, known or unknown exit status, and last progress.

## Predeclared PR review delegation deadlines

This is a narrow, predeclared exception to the never-stop-a-live-worker rule. It covers only a read-only PR review delegation whose target identity, absolute deadline, no-progress cutoff, and cancellation means are recorded before dispatch. The parent sets the delegation deadline to the earlier of dispatch time + 10 minutes and the review research deadline, and stops the worker at the deadline or after 5 minutes without substantive progress. Whether progress is substantive follows the time-budget reference: heartbeat, repeated identical state, and log-mtime-only updates do not reset the no-progress clock.

- Stop the worker at its deadline; do not extend it for progress and do not re-dispatch it.
- Confirm the stop once (about one attempt, capped near 30 seconds). On unconfirmed cancellation, report the delegation target, its unconfirmed state, and every path it may still use, then end the turn. Do not start dependent work, and do not remove its worktree.
- This exception does not apply to verification commands or implementation workers, and must never be reused to stop a generic task. Liveness, progress, and completion stay separate signals, and PID identity checks still apply.

## Quick reference

| State | Action |
| --- | --- |
| `completed` | Report arrived; consume it and continue. |
| `exited without report` | Abnormal; recheck report, report failure, confirm `EXIT=<code>`. |
| `alive and progressing` | Keep waiting; record latest log position. |
| `alive but stalled` | Report stall with all four fields; keep the task alive and hold dependents. |
| `predeclared PR review delegation past deadline` | Stop at its deadline or progress cutoff; confirm once; on unconfirmed stop, report and end the turn without dependents. |

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Wait on report existence only | Wait for `report exists OR worker is not alive`. |
| Inline `pgrep -f` that matches the monitor | Use a script file or bracket pattern; inspect matches. |
| Use the log path as the `pgrep` marker | Match the command line; keep log path for progress only. |
| Require a fixed manual log redirect | Use the printed log path for each run. |
| Kill a live stalled task to meet a deadline | Report the stall and request a decision, unless it is a predeclared read-only PR review delegation past its deadline or progress cutoff (see `Predeclared PR review delegation deadlines`). |
| Stop a live worker outside the predeclared exception | Only a predeclared read-only PR review delegation may be stopped, and only at its deadline or progress cutoff. |
| Start dependent work before reporting | Report first, including all four status fields. |

Do not use this skill for short synchronous commands that already return their result.
