---
name: repository-ownership
description: Use when starting any work in this repository — decides whether a change belongs to the public application repository (usaturn/maatlog, checked out at public/) or the parent development-environment repository (usaturn/maatlog-poc), before creating issues, worktrees, verification runs, or PRs. Load before routing any edit, test run, or PR to a repository.
---

# Repository Ownership

MaatLog work is split across two repositories. Routing work to the wrong one
either loses it (an application change committed only to the parent, whose
application tree is removed at cutover) or corrupts the public mirror (a
parent commit that drags the `public/` gitlink along).

| Concern | Repository | Checkout | Default base |
|---|---|---|---|
| Application: `src/`, `tests/`, `docs/`, `pyproject.toml`, `uv.lock`, README, distribution | `usaturn/maatlog` (public) | the `public/` submodule, or a standalone clone | public `origin/main` |
| Environment: `.agents/`, `.claude/`, `.devin/`, `.codex/`, `.pi/`, `.cursor/`, `tools/`, `scripts/ci/verify-devenv.sh`, `.devcontainer/` | `usaturn/maatlog-poc` (this parent) | this checkout | parent `origin/main` |

## Decide the route before acting

Inside the parent checkout, run this route check before creating a branch,
worktree, Issue, or PR. It confirms the parent `origin` and that
`git -C public remote get-url origin` equals the `.gitmodules` URL — a value
that disagrees with `.gitmodules` means the submodule points somewhere else
and must be fixed before any application work.

```bash
# repository-ownership route check
TOPLEVEL="$(git rev-parse --show-toplevel)"

app_root() {
    local expected actual
    if ! expected="$(git -C "$TOPLEVEL" config -f .gitmodules --get submodule.public.url)"; then
        printf 'repository-ownership: public/ is not registered in %s/.gitmodules\n' "$TOPLEVEL" >&2
        return 1
    fi
    if ! actual="$(git -C "$TOPLEVEL/public" remote get-url origin 2>/dev/null)"; then
        printf 'repository-ownership: %s/public is not a readable checkout; run: git -C %s submodule update --init public\n' "$TOPLEVEL" "$TOPLEVEL" >&2
        return 1
    fi
    if [[ "$actual" != "$expected" ]]; then
        printf 'repository-ownership: public/ origin %s does not match .gitmodules %s; fix the submodule remote before application work\n' "$actual" "$expected" >&2
        return 1
    fi
    printf '%s\n' "$TOPLEVEL/public"
}

env_root() {
    printf '%s\n' "$TOPLEVEL"
}

assert_no_gitlink_staged() {
    if git -C "$TOPLEVEL" diff --cached --name-only | grep -qx 'public'; then
        printf 'repository-ownership: the public gitlink is staged; unstage it unless this commit is an intentional checkpoint\n' >&2
        return 1
    fi
}
```

If `app_root` fails, stop — do not guess a fallback root. A missing `public/`
checkout is repaired with `git submodule update --init public`; a mismatched
`origin` is repaired on the submodule remote. Never retarget application work
to the parent because the public checkout looks wrong.

## Application route (public)

Everything that ships to users lives in `usaturn/maatlog`.

- **Worktree base:** public `origin/main`, fetched inside the submodule. The
  worktree path must live **outside** the public checkout — a worktree created
  under `public/` shows up as `modified: public (untracked content)` in the
  parent and can be swept into the public repo by a blanket `git add` there.
  Put it under the parent's ignored `.claude/worktrees/` instead:

  ```bash
  # repository-ownership app worktree
  APP_ROOT="$(app_root)"
  git -C "$APP_ROOT" fetch origin main
  git -C "$APP_ROOT" worktree add "$TOPLEVEL/.claude/worktrees/<name>" -b <branch> origin/main
  ```

  Never cut an application branch from the parent's `origin/main`: it lacks
  the application tree after cutover and diverges from public history today.

- **Issues and PRs:** `gh --repo usaturn/maatlog ...`. A bare `gh pr` call in
  a parent checkout resolves against the parent's `origin` and silently
  targets the wrong repository; pin `--repo` every time.

- **Verification:** `./scripts/ci/verify.sh <profile>` inside the public
  checkout. The `full`/`quick`/`static` profiles are that verifier's
  contract (see `CLAUDE.md`). The parent's CI waiver never applies here.

## Environment route (parent)

Development-environment work stays in `usaturn/maatlog-poc`.

- **Worktree base:** parent `origin/main`:

  ```bash
  git fetch origin main
  git worktree add .claude/worktrees/<name> -b <branch> origin/main
  ```

  When a parent Issue names an integration branch, merge it into the feature
  branch before testing and target the PR at that branch, not at `main`.

- **Issues and PRs:** `gh --repo usaturn/maatlog-poc ...`, after
  `git remote get-url origin` confirms this checkout is the parent.

- **Verification:** `./scripts/ci/verify-devenv.sh` at the parent root.

## The public gitlink is a checkpoint, not a diff

The parent's `public/` entry is a gitlink — a pinned pointer to a public
commit. Routine environment commits must never move it:

- Stage parent changes by explicit path. Blanket staging is prohibited in
  the parent.
- Before every parent commit, run `assert_no_gitlink_staged` from the route
  check. If it fails, unstage `public` and split the commit.
- Only an intentional checkpoint commit — a release/compatibility pin that a
  task explicitly requests — may stage the `public` gitlink by its explicit
  path, in a commit of its own.

## Wrong-route symptoms

| Symptom | Cause |
|---|---|
| App PR opened against `usaturn/maatlog-poc` | `gh` ran without `--repo usaturn/maatlog` in a parent checkout |
| App worktree missing `src/` | branched from parent `origin/main` instead of public |
| `modified: public` after an env commit | gitlink swept up by blanket staging; unstage and re-commit |
| Public CI skipped as "waived" | the CI waiver covers parent PRs only; public PRs keep the public CI green gate |
