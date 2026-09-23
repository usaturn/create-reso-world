---
name: agent-handoff
description: Use whenever work crosses between agents, in either direction. Reading side - the user asks you to continue, resume, inspect, or take over work another agent progressed (Claude Code, Superpowers, brainstorming, writing-plans, review-fix-planning, subagent-driven-development, python-tdd-team). Writing side - the user asks you to stop at a breakpoint and prepare material for another agent, says another agent will implement this, asks "hand this off", "write a handoff", "引き継ぎ資料を作って", or asks whether passing a spec alone is enough. Reads or writes repo-local handoff artifacts under tmp/docs_draft/claude_handoffs that carry the dispositions already decided, what the next agent must not touch, how to verify, and where the work lands - not just a summary of what happened.
---

# Agent Handoff

## Overview

A handoff moves work between agents. The receiving agent starts cold: it has the
repository and whatever you wrote down, and nothing else. This skill covers both ends of
that move — **writing** a handoff when you are the one stopping, and **reading** one when
you are the one continuing.

The artifact is a pair of files under `tmp/docs_draft/claude_handoffs/`, described in
`references/handoff-schema.md`. Read that file before writing or interpreting one.

**What makes a handoff fail is rarely a missing summary.** A cold agent can re-read the
diff. What it cannot recover is what was already decided and rejected. The expensive
failures are a receiver that re-litigates a settled call, acts on a finding you
deliberately excluded, invents its own verification and runs it against real state, or
opens a second PR. `decisions`, `out_of_scope`, `verification`, and `landing` exist for
exactly those four.

## Which direction are you in?

- The user is stopping you, or asking for material another agent will work from →
  **Writing a handoff**.
- The user is asking you to pick up work someone else progressed →
  **Reading a handoff**.

If it is ambiguous, ask. Writing when you should be reading wastes a turn; reading when
you should be writing loses the decisions.

## Writing a handoff

1. **Pick the breakpoint and say what it is.** A handoff written mid-edit is worse than
   no handoff. Either finish the unit of work or revert it — then record which in
   `session.stop_reason`. If you leave a partially applied edit in the working tree, the
   handoff must say so in the first section, because the receiver will otherwise assume
   the tree matches `git.head`.

2. **Decide where the reasoning lives.** Long-form argument belongs in the spec or plan
   (in this repository, `docs_draft/superpowers/`). The handoff carries one-line
   dispositions and points at the spec through `sources.spec`. Duplicating the argument
   in both places guarantees they drift. If there is no spec, set `sources.spec` to
   `null` (JSON) / `none` (Markdown) and state why. Do not invent a path.

3. **Write both files** under `tmp/docs_draft/claude_handoffs/` as
   `<timestamp>-<session>.handoff.md` and `.handoff.json` by hand against
   `references/handoff-schema.md`.

4. **Fill the fields only you can know.** You supply:

   - `decisions` — every call already made, with its disposition (`fix` / `skip` /
     `deferred` / `resolved`) and a one-line reason. The receiver needs `skip` entries
     as much as `fix` entries; without them, "skip" looks like "not done yet".
   - `out_of_scope` — binding, and worth stating even when it feels obvious. Name the
     near-misses: the adjacent file that looks like it needs the same fix, the refactor
     that would be tidy, the test suite that is not the gate here.
   - `verification` — the exact commands, plus the isolation they need. A receiver
     reproducing a config bug without `isolation` will reproduce it against the user's
     real config.
   - `landing` — branch, existing PR, what must not happen (new PR, side branch, a gate
     that does not apply), and any commit trailers the repository requires.
   - `git.worktree`, `git.branch`, `git.head`, `git.status` — where the work actually
     is, and the branch / HEAD / status of that checkout. When the parent checkout is
     detached or on another branch, record both; a receiver that runs your commands in
     the parent checkout edits the wrong tree.

5. **Check what hand-writing tends to drop.** Three gaps are common: an agent that
   never used a todo facility produces no `tasks` — say so rather than inventing them;
   files written through a shell heredoc rather than an editor tool leave no
   file-history trace and never appear in `sources.plan_files` — add them explicitly;
   and `git` may describe `project_dir` rather than the worktree — record the worktree
   by hand. Fill these in rather than shipping the gaps.

6. **Self-check before handing over.** Every required field in
   `references/handoff-schema.md` present (`sources.spec` and `landing.pr` may be
   `null`); every non-null path in the artifact exists; the
   receiver could start with only this artifact and the repository. If you would have to
   answer a follow-up question in chat, that answer belongs in the handoff.

## Reading a handoff

1. **Look for an existing one:**

   ```bash
   ls -t tmp/docs_draft/claude_handoffs/*.handoff.md 2>/dev/null | head
   ```

2. **If none fits, write one** before continuing — write it from what you can establish
   against `references/handoff-schema.md`, and confirm the gaps with the user rather
   than guessing.

3. **Read the newest `.handoff.md`**, and the paired `.handoff.json` when precise fields
   matter. Check `schema_version`: a version 1 artifact has no `decisions`,
   `out_of_scope`, `verification`, or `landing`, and those absences mean _unknown_, not
   _empty_.

4. **Report the state before acting**: session and agent, detected skills, current phase
   or gate, completed and pending tasks, decisions already made, what is out of scope,
   verification evidence, and the landing target.

5. **Continue only from the handoff state.** `out_of_scope` is binding. Do not reopen a
   `skip` decision because it looks like a small win — if you believe one is wrong, say
   so and stop. When the handoff contradicts your own memory of the session, the handoff
   wins. Run `verification.commands` with the stated isolation, and land through
   `landing` rather than through your usual habit.

## Writing the artifact

Write the pair by hand against `references/handoff-schema.md`.

## Validation

Use the `quick_validate.py` from the globally installed skill-creator.
`<skill-creator-path>` resolves per runtime:

- Codex: `~/.codex/skills/.system/skill-creator`
- Claude Code / Devin: locate the plugin copy with
  `find ~/.claude -name quick_validate.py`; the path's skill-creator directory
  is two levels above the script
- pi: `@howaboua/pi-skill-skill-creator` ships no `quick_validate.py`; run
  `~/.pi/agent/npm/node_modules/@howaboua/pi-skill-skill-creator/skills/skill-creator/scripts/skill-efficiency-check.py`
  with the same argument instead

- `uv run python <skill-creator-path>/scripts/quick_validate.py .agents/skills/agent-handoff`
- `uv run python <skill-creator-path>/scripts/quick_validate.py .claude/skills/agent-handoff`
- `uv run pytest .agents/skills/agent-handoff/tests -q` — checks that both
  runtime versions of this skill state the same handoff contract, and that every path
  the skills reference exists.

## Resources

- `references/handoff-schema.md`: the artifact schema, required fields, and version 1
  compatibility.
- `evals/evals.json`: behaviour checks for both directions.
- `evals/trigger_queries.json`: trigger coverage.
