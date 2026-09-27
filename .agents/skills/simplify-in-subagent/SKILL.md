---
name: simplify-in-subagent
description: "Subagent-portable /simplify: git-diff-scoped code simplification. Use when /simplify slash unavailable, parent requests simplify equivalent, or handling --staged/--ref/file-scoped simplify in subagent/worktree. Not main-session /simplify."
argument-hint: "[--staged|--ref=<ref>|<files>]"
subagent: true
---

# Simplify in Subagent

対象指定: $ARGUMENTS

Only changed lines. Never whole-file refactors. Run every `git` command in own cwd, not the parent's.

## ランタイム別の注意

- 冒頭の `対象指定` 行は、呼び出し引数を本文へ展開するランタイム（Claude Code、Devin）が埋める補間欄である。値が空欄、またはドル記号で始まるプレースホルダ表記のまま残っている場合は未指定とみなし、呼び出し元のメッセージで指定された ref・`--staged`・ファイル一覧を使う。どれも無ければ既定の `HEAD` との diff を対象にする
- 引数を展開するランタイムは `＄ARGUMENTS` と `＄0`〜`＄9`（ドル記号と数字 1 文字）を置換する（この節では置換されないよう全角で書いている）。埋め込みのコードに位置パラメータを書かず、入力は stdin や名前付き変数で受ける
- Devin では `subagent: true` により本文がサブエージェントの task として実行される。サブエージェントでは `ask_user_question` が使えないため、不明点や異常は質問にせず Recovery に従って報告に回す。`run_subagent` / `read_subagent` もサブエージェント内では無効だが、本手順はネストしたサブエージェントを必要としない
- Devin には `/simplify` 相当の組み込みコマンドが無いため、メインセッションからの直呼び出しでも `subagent: true` によりサブエージェントで実行される

## Inputs

- Required routing context: target repository and intended working root, resolved by the caller from the repository boundary table in the root `AGENTS.md` before delegation. Pass these as task context, not new slash-command flags. Do not infer the target from the current cwd, the skill's location, or the presence of `src/`.
- Required: one of ref (default `HEAD`), `--staged`, or explicit file list, taken from the interpolated 対象指定 line. An empty or placeholder line means `HEAD`.
- Optional: test command. Default: relevant existing tests.

## Repository preflight

Before deriving files or reading diffs, confirm the routing context for every input mode: default `HEAD`, `--ref`, `--staged`, and explicit files. The repository boundary table in the root `AGENTS.md` is the routing authority; the table below restates it. If the target repository or intended working root cannot be established, stop and report the missing context.

Run these read-only commands in your own cwd (the last one only on the fork route):

```bash
git rev-parse --show-toplevel
git remote get-url origin
git remote get-url upstream
```

Compare the Git root with the intended working root using their resolved filesystem paths. Compare origin's GitHub owner/repository, and on the fork route also upstream's, with the route below. Standard GitHub HTTPS and SSH URLs, with or without a trailing `.git`, can identify the same repository; different hosts, owners, repositories, or unrecognized URL forms do not pass. Do not guess SSH aliases.

| Route | Declared target | Working root and remotes | Meaning of `origin/main` |
| --- | --- | --- | --- |
| This repository | `usaturn/create-reso-world` | This repository's checkout or one of its worktrees; origin is `usaturn/create-reso-world` | This repository's remote-tracking ref |
| ResoLoop fork | `usaturn/resoloop` or `orange3134/resoloop` | `external/resoloop` under this repository's root, or a worktree of that checkout; origin is `usaturn/resoloop` and upstream is `orange3134/resoloop` | The fork's remote-tracking ref, which mirrors `upstream/main` only right after a sync |

On the fork route, `origin/main` mirrors `upstream/main` only immediately after `bash scripts/resoloop-fork.sh sync` has run. Before relying on `origin/main`, either run `sync` first (with the user's confirmation; in Claude Code, via AskUserQuestion), or, for an upstream PR, derive the changed-line ranges from `upstream/main` directly so they match the PR.

Any other target repository has no route: stop before deriving files and report the declared target.

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

- This repository: caller declares target `usaturn/create-reso-world` and a worktree of this repository as the working root for `/simplify-in-subagent --ref=origin/main`. In that worktree, verify root/origin, resolve that repository's `origin/main`, then simplify `scripts/check-layout.sh` lines 10–18 from the diff. Only those changed lines may be edited; run relevant tests and report the route and changes.
- ResoLoop fork: caller declares target `orange3134/resoloop` (an upstream PR) and `external/resoloop` as the working root for `/simplify-in-subagent --ref=origin/main`. Verify root, origin and upstream there. Since this is an upstream PR, either run `sync` first (with the user's confirmation) so `origin/main` mirrors `upstream/main`, or derive the changed-line ranges from `upstream/main` directly, before simplifying `src/RLoop.Cli/...`.
- Wrong route: target is `usaturn/resoloop`, but the current cwd is this repository's root while the request names `src/RLoop.Cli/Program.cs` and `--ref=origin/main`. Stop at preflight, report the mismatch, and ask the caller to rerun in `external/resoloop`. Do not read this repository's diff or invoke fallback. Here, "ask the caller" means return this instruction in the result report; it does not require a question tool.
