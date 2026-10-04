# Agent Handoff Schema

**`schema_version` 2.** Readers must still accept version 1 artifacts; see
[Reading a version 1 artifact](#reading-a-version-1-artifact).

A handoff is a pair of files under `tmp/docs_draft/claude_handoffs/`:

- `<timestamp>-<session>.handoff.md` — what a person reads
- `<timestamp>-<session>.handoff.json` — what a program reads

The two carry the same facts. Write both.

## Contents

- [How a handoff gets written](#how-a-handoff-gets-written)
- [Required fields](#required-fields)
- [JSON fields](#json-fields)
- [Markdown sections](#markdown-sections)
- [Reading a version 1 artifact](#reading-a-version-1-artifact)
- [Safety](#safety)

## How a handoff gets written

Write the pair by hand against this schema.

**Why these fields matter.** Only the outgoing agent knows what was _decided_ and what the
next agent is _forbidden_ to touch. `decisions`, `out_of_scope`, `verification`, and
`landing` come from the outgoing agent, every time. A draft with those fields empty is
a draft, not a handoff.

## Required fields

A handoff is complete when all of these are present. Empty is allowed only when it is
true and stated (`"decisions": []` means "nothing was decided", not "not filled in yet").

| Field | Why it is required |
|---|---|
| `schema_version`, `generated_at`, `project_dir` | Identify the artifact |
| `session.id`, `session.stop_reason` | Where it came from and why it stopped |
| `decisions` | Without dispositions the receiver re-litigates settled calls |
| `out_of_scope` | Without it the receiver "helpfully" does the work you deliberately excluded |
| `verification.commands`, `verification.isolation` | Without it the receiver invents a check, or runs a destructive one |
| `landing.branch`, `landing.pr`, `landing.prohibited` | Without it the receiver opens a second PR |
| `git.worktree`, `git.branch`, `git.head`, `git.status` | The parent checkout is often not where the work is |
| `sources.spec` | Long-form rationale lives in the spec when there is one. `null` / `none` when there is not, with a reason |

Everything else — `skills`, `tasks`, `reports`, `next_work`, `sources.plan`,
`sources.ledger`, `sources.session_jsonl`, `sources.plan_files`, `git.merge_base` — is
optional and worth including when it is true.

## JSON fields

- `schema_version`: `"2"`.
- `generated_at`: UTC timestamp.
- `project_dir`: repo path the handoff describes.
- `session`:
  - `id`, `path`, `ai_title`, `agent_name`, `permission_mode`, `last_prompt`
  - `stop_reason`: the breakpoint in one line — what is finished, what is not started.
- `skills`: skill names in play (detected `attributionSkill` values, or what you invoked).
- `tasks`: `id`, `subject`, `status`. From the runtime's todo/plan facility when one was
  used. An agent that never opened a todo list has no tasks; say so rather than inventing them.
- `reports`: redacted report snippets with `timestamp`, `skill`, `text`.
- `decisions`: one entry per call already made. Do not restate the reasoning here — one
  line, and point at `sources.spec` for the argument.
  - `id`: stable label used in the spec (`"F-1"`, `"M-2"`).
  - `disposition`: `"fix"` (act on it) | `"skip"` (deliberately not acting) |
    `"deferred"` (waiting on a human decision) | `"resolved"` (already true at current HEAD).
    When the call came from `review-fix-planning`, map buckets as follows:

    | review-fix-planning | disposition |
    |---|---|
    | Fix | `fix` |
    | Hold | `deferred` |
    | Skip | `skip` |
    | Resolved | `resolved` |

    Questions of intended behaviour stay Skip and therefore `skip`; do not raise them
    to `deferred`.

  - `subject`: what it is about.
  - `rationale`: one line. Why this disposition.
  - `source`: where it came from (review file and finding id, issue number, user message).
  - `status`: `"pending"` | `"in_progress"` | `"done"` — only for `fix` entries.
- `out_of_scope`: things the receiver must not do, as plain sentences. This is binding,
  not advisory. Include the near-misses that look helpful: adjacent files, "while I'm here"
  refactors, the findings marked `skip`.
- `verification`:
  - `commands`: exact commands the receiver runs to confirm the work.
  - `isolation`: how to keep those commands from touching real state — temp dirs,
    env overrides, which real paths must not be written. Omit this and a receiver
    reproducing a config bug will do it against the user's live config.
  - `evidence`: what has already been verified and does not need redoing.
- `landing`:
  - `branch`: the branch the work lands on.
  - `pr`: the existing PR, `owner/repo#N` or `#N`. `null` when there is none — then say
    in `prohibited` whether opening one is allowed.
  - `prohibited`: what must not happen at landing time (new PRs, side branches, gates
    that do not apply).
  - `commit_trailers`: trailers the repository requires on commits, verbatim.
- `next_work`: ordered next steps, most immediate first.
- `sources`:
  - `spec` (required): path to the design/spec that holds the reasoning, or `null` /
    `none` when there is no spec — then say why, the same way `landing.pr` does.
  - `plan`, `ledger`, `sdd_workspace`, `session_jsonl`, `plan_files`: when they exist.
  - `doc_root`: the create-reso-world checkout where the spec and plan are committed
    (`DOC_ROOT`). Specs and plans for every repository live there.
  - `document_commit`: the full SHA of the current/restore commit that holds the
    spec and plan, and `document_published`: the remote ref it was pushed to, or
    `null` when it is a local commit only (say "公開未実施" in Markdown).
  - `approved_commit`: when a user approved a specific committed content version, its
    full SHA. `null` means no recorded content approval — do not infer it from the
    status field or from a review copy. It differs from `document_commit` when later
    metadata-only edits (status lines, record additions, typo fixes) moved the
    current/restore version; those do not require renewed approval. A substantive
    design/Plan change requires renewed approval unless the recorded execution
    authority explicitly covers it.
  - `execution_authority`: the explicit instruction or rule that authorizes executing
    the work, in one line. `null` when nothing authorizes execution: then the next
    step is blocked, not ready — name the missing authorization or rule as a blocker
    instead of an implicit plan. General external implementation and remote-less PR
    integration have no authorized route.
  - `completion_evidence`: the verified commands/results backing the reported status;
    `null` before implementation exists. A recovery artifact never claims the review
    copy is canonical.
  - `review_copy`: the copy under the parent checkout's `tmp/superpowers-review/` that a
    person reads. It is a viewing aid, never a restore source; restore from
    `document_commit`.
  - Files written through a shell heredoc rather than an editor tool are easy to forget. List them explicitly.
- `git`:
  - `worktree` (required): the checkout the work actually lives in. When the parent
    checkout differs (detached, on another branch), record it too — a receiver that
    reads `branch` and runs it against the parent checkout edits the wrong tree.
  - `branch`, `head`, `status` (required): record them in the same terms as the
    Required fields table.
  - `merge_base`: add when a branch point matters.
  - `parent_checkout`: the parent checkout a person reads (`PARENT_ROOT`) with its branch,
    HEAD and status, when it differs from `worktree`.
  - `code`: when the code lives in a repository other than create-reso-world, its
    `repository`, `worktree` (`CODE_ROOT`), `branch`, `head`, `status` and `pr`. Keep them
    apart from the document checkout above.

## Markdown sections

Same facts, readable order. `Session`, `Detected Skills`, `Current Phase / Gate`,
`Task State`, `Decisions`, `Out of Scope`, `Verification`, `Landing`,
`Next Recommended Work`, `Sources`, `Git`.

`Decisions` reads well as a table:

```markdown
## Decisions

| ID | Disposition | Subject | Rationale |
|---|---|---|---|
| F-1 | fix | piccg の provider 判定が非 dict で traceback | 現行 HEAD で再現。宣言した fail-open に反する |
| S-4 | skip | setup:287 に同じガードを足す | ステップ 2 が先に落ちるため到達不能 |
```

`Out of Scope` and `Landing` read well as lists. Keep `Landing`'s prohibitions as
imperatives — "do not open a new PR" survives skimming in a way that "the existing PR is
preferred" does not.

## Reading a version 1 artifact

Version 1 has no `decisions`, `out_of_scope`, `verification`, or `landing`, and its `git`
section may describe the parent checkout rather than the worktree. Treat those as
**unknown, not empty**. Ask the user for the missing dispositions and landing target
before acting; do not infer them from the transcript or from the fact that a file was
edited.

## Safety

Redact assignment-like secret names containing `SECRET`, `TOKEN`, `CREDENTIAL`,
`PASSWORD`, or `API_KEY`. `verification.commands` is the place this leaks most easily —
an env var name is fine, a value is not. Review a handoff before sharing it outside the
local development environment.
