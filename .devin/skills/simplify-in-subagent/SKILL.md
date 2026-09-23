---
name: simplify-in-subagent
description: git diff 範囲限定のコード簡素化。変更行だけを対象にネスト解消・命名改善・冗長削減を行い、サブエージェントとして実行する。--staged / --ref=<ref> / ファイル指定を受け付ける。Devin には組み込みの /simplify が無いため、このスキルが simplify 相当の経路になる
argument-hint: "[--staged|--ref=<ref>|<files>]"
subagent: true
allowed-tools:
  - read
  - edit
  - grep
  - glob
  - exec
---

# Simplify in Subagent（Devin 版）

対象指定: $ARGUMENTS

Only changed lines. Never whole-file refactors. Run every `git` command in own cwd, not the parent's.

## Devin 固有の注意

- Devin CLI はスキル呼び出し時、本文中の `＄ARGUMENTS` と `＄1`〜`＄9`（ドル記号+数字1文字）形式のプレースホルダを呼び出し引数で全文置換する（この節では補間されないよう意図的に全角で表記している。半角で書くとこの説明文自体が引数で上書きされる）。埋め込みコードではシェルの位置パラメータ表記を使わず、入力は stdin や名前付き変数で受けること
- 冒頭の `対象指定` 行がこの補間欄である。値が空欄、またはドル記号始まりのプレースホルダ表記のまま残っている場合は未指定（既定の `HEAD` との diff）として扱う
- `subagent: true` により本文はサブエージェントの task として実行される。サブエージェントでは `ask_user_question` が常に使えないため、不明点や異常は質問にせず Recovery に従って報告に回す。`run_subagent` / `read_subagent` もサブエージェント内では無効だが、本手順はネストしたサブエージェントを必要としない
- Devin には `/simplify` 相当の組み込みコマンドが無いため、メインセッションからの直呼び出しでも `subagent: true` によりサブエージェントで実行される

## Inputs

- Required routing context: target repository and intended working root, resolved by the caller using `repository-ownership` before delegation. Pass these as task context, not new slash-command flags. Do not infer the target from the current cwd, the skill's location, or the presence of `src/`.
- Required: one of ref (default `HEAD`), `--staged`, or explicit file list, taken from the interpolated 対象指定 line. An empty or placeholder line means `HEAD`.
- Optional: test command. Default: relevant existing tests.

## Repository preflight

Before deriving files or reading diffs, confirm the routing context for every input mode: default `HEAD`, `--ref`, `--staged`, and explicit files. `repository-ownership` is the routing authority. If the target repository or intended working root cannot be established, stop and report the missing context.

Run these read-only commands in your own cwd:

```bash
git rev-parse --show-toplevel
git remote get-url origin
```

Compare the Git root with the intended working root using their resolved filesystem paths. Compare origin's GitHub owner/repository with the declared target. Standard GitHub HTTPS and SSH URLs, with or without a trailing `.git`, can identify the same repository; different hosts, owners, repositories, or unrecognized URL forms do not pass. Do not guess SSH aliases.

| Task | Target repository | Working root | Meaning of `origin/main` |
| --- | --- | --- | --- |
| Application | `usaturn/maatlog` | `public/` or a worktree from the public repository | Public repository's remote-tracking ref |
| Environment | `usaturn/maatlog-poc` | Parent checkout or a worktree from the parent repository | Parent repository's remote-tracking ref |

For `--ref=origin/main`, only after the route matches, resolve the ref in that same cwd:

```bash
git rev-parse --verify 'origin/main^{commit}'
```

Record its SHA before continuing. Other input modes still require the route check; they do not require `origin/main` unless they use it.

If a command fails, the root or origin differs, or the selected ref cannot be resolved, stop before deriving files or editing. Report expected target/root, observed root/origin, and the failing command/reason. Do not use the empty-diff `HEAD~1` fallback to bypass a failed preflight. Do not change cwd, use another repository via `git -C`, rewrite remotes, or fetch as an implicit repair; the caller must supply a correct working context and rerun.

## Workflow

1. **Derive files.** After the repository preflight succeeds, run the matching `name-status` command. Map `M→modified`, `A→added`, `R→renamed`, `C→copied`; renamed/copied use the new path. Ignore other statuses.

   | Request | Command in own cwd |
   | --- | --- |
   | default | `git diff --name-status HEAD` |
   | `--staged` | `git diff --name-status --cached` |
   | `--ref=X` | Replace `HEAD` with `X` above |
   | `<files>` | Treat as `modified`, skip `name-status` |
   | empty result | Fall back to `git diff --name-status HEAD~1` once |

2. **Derive lines.** Per file (skip `added`), parse `+start,count` hunks from `git diff --unified=0 --no-ext-diff <ref|--cached> -- <path>` into ranges; merge adjacent. `added` = entire file. Zero ranges = deletions only.
3. **Apply inside ranges only.** Preserve functionality; follow `CLAUDE.md`/`AGENTS.md`; reduce nesting and redundancy, improve names; keep rationale/intent comments, remove only true noise; no nested ternary; no clever code, mega-functions, or removed abstractions. Read surroundings for context. One file at a time. No features, API changes, or unchanged-code edits.
4. **Verify, report.** Run relevant tests. Output per-file changes with reasons plus out-of-scope ideas (mentioned, never edited). Include the verified target repository, Git root, origin, and comparison ref (with resolved SHA when applicable) in the report.

## Validation

- Repository preflight succeeded before any diff or edit.
- Ranges derived before any edit; `added`/deletions-only handled per step 2.
- Every edit inside a listed range; surrounding code read-only.
- Tests pass before reporting.

## Recovery

- Route or ref check failed → follow the Repository preflight stop-and-report procedure before any diff or edit.
- No changed files (including after fallback) → report that and stop.
- Diff failed → inspect `git diff` manually before editing; do not guess ranges.
- File missing or path empty in own cwd → stop, report mismatch; do not edit substitutes.
- Format-only tools (ruff/prettier) never substitute for the clarity pass.

## Examples

- Application: caller declares target `usaturn/maatlog` and a public worktree as the working root for `/simplify-in-subagent --ref=origin/main`. In that worktree, verify root/origin, resolve that repository's `origin/main`, then simplify `src/foo.py` lines 10–18 from the diff. Only those changed lines may be edited; run relevant tests and report the route and changes.
- Environment: caller declares target `usaturn/maatlog-poc` and a parent worktree for `/simplify-in-subagent --ref=origin/main`. Verify root/origin there before using that repository's `origin/main` for changed lines in `tools/devenv/...`.
- Wrong route: target is `usaturn/maatlog`, but the current cwd is the parent checkout while the request names `src/foo.py` and `--ref=origin/main`. Stop at preflight, report the mismatch, and ask the caller to rerun in the intended public worktree. Do not read the parent's diff or invoke fallback. Here, "ask the caller" means return this instruction in the result report; it does not require a question tool.
