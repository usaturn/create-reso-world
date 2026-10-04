#!/usr/bin/env bash
# ff_merge_keep_untracked.sh — fast-forward without losing untracked files
# that the incoming commits would overwrite.
#
# Usage:
#   bash ff_merge_keep_untracked.sh --ref <rev> [--repo <path>]
#
# `git merge --ff-only <rev>` refuses to run while an untracked file sits on a
# path that <rev> adds, and it silently overwrites an ignored file on such a
# path. This script copies every untracked file on a path that <rev> adds,
# ignored or not, to a backup directory (cp -a keeps symlinks, modes and
# timestamps), checks each copy, removes the originals, runs the fast-forward
# once, and then copies every file back over the merged version and checks it
# again. A file that differs from <rev> afterwards shows up as modified; one
# that matched <rev> is clean.
#
# git would also remove untracked or ignored content that cannot be put back
# in place: files under a directory where <rev> adds a file, or a file or
# symlink where <rev> needs a directory. The script refuses to run then and
# lists those paths, so they can be moved away first.
#
# When the fast-forward fails or the run is interrupted (HUP, INT, TERM),
# every file goes back to its original place. The backup directory is never
# deleted: its path is printed on stderr before anything is removed, together
# with a NUL-separated list of the backed-up paths in <backup>/paths.
#
# Exit codes:
#   0  fast-forwarded (or already up to date) and every file was restored
#   1  the run did not complete: no fast-forward was possible, some paths
#      must be moved away first, the fast-forward failed, a file could not be
#      restored, or the run was interrupted. stderr says which, and whether
#      HEAD moved; the backup directory still holds the originals
#   2  usage error, not a git work tree, or unknown <rev>

set -u

readonly EXIT_OK=0
readonly EXIT_FAIL=1
readonly EXIT_USAGE=2

files=()
backup=""
ref=""
target=""

usage() {
  cat >&2 <<'EOF'
usage: ff_merge_keep_untracked.sh --ref <rev> [--repo <path>]
EOF
}

# Drop GIT_DIR, GIT_WORK_TREE and the other repository-local variables that a
# caller (for example a git hook) may export, so --repo alone selects the
# repository instead of silently being overridden.
clear_git_env() {
  local var
  for var in $(git rev-parse --local-env-vars); do
    unset "$var"
  done
}

# True when both paths are the same kind of file with the same content: two
# symlinks with the same target, or two regular files with the same bytes and
# permission bits.
same_file() {
  local a="$1" b="$2"
  if [ -L "$a" ] || [ -L "$b" ]; then
    [ -L "$a" ] && [ -L "$b" ] && [ "$(readlink -- "$a")" = "$(readlink -- "$b")" ]
    return
  fi
  [ -f "$a" ] && [ -f "$b" ] && cmp -s -- "$a" "$b" &&
    [ "$(stat -c '%a' -- "$a")" = "$(stat -c '%a' -- "$b")" ]
}

# Put every backed-up file back in place. A path that already holds the
# original is skipped, so this is safe to run again after an interruption.
restore_all() {
  local rel failed=0
  for rel in "${files[@]}"; do
    same_file "$rel" "$backup/files/$rel" && continue
    if mkdir -p -- "$(dirname -- "$rel")" && rm -f -- "$rel" &&
      cp -a -- "$backup/files/$rel" "$rel" && same_file "$rel" "$backup/files/$rel"; then
      continue
    fi
    printf 'failed to restore %s; the original is kept in %s\n' "$rel" "$backup/files/$rel" >&2
    failed=1
  done
  return "$failed"
}

# Paths that the target commit adds to HEAD, NUL-separated.
added_paths() {
  git diff --no-renames --name-only -z --diff-filter=A HEAD "$target"
}

# Report where an interrupted run left HEAD, after putting the files back.
on_signal() {
  trap - HUP INT TERM
  restore_all
  if [ "$(git rev-parse HEAD 2>/dev/null)" = "$target" ]; then
    printf 'interrupted after the fast-forward to %s; HEAD moved; the originals are kept in %s\n' "$ref" "$backup/files" >&2
  else
    printf 'interrupted before the fast-forward; HEAD is unchanged; the originals are kept in %s\n' "$backup/files" >&2
  fi
  exit "$EXIT_FAIL"
}

main() {
  local repo=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --repo|--ref)
        if [ $# -lt 2 ]; then
          usage
          exit "$EXIT_USAGE"
        fi
        if [ "$1" = --repo ]; then repo="$2"; else ref="$2"; fi
        shift 2
        ;;
      --repo=*)
        repo="${1#--repo=}"
        shift
        ;;
      --ref=*)
        ref="${1#--ref=}"
        shift
        ;;
      -h|--help)
        usage
        exit "$EXIT_OK"
        ;;
      *)
        printf 'unknown argument: %s\n' "$1" >&2
        usage
        exit "$EXIT_USAGE"
        ;;
    esac
  done
  if [ -z "$ref" ]; then
    usage
    exit "$EXIT_USAGE"
  fi
  [ -n "$repo" ] || repo="$PWD"

  clear_git_env

  local top
  if ! top="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || [ -z "$top" ]; then
    printf 'not a git work tree: %s\n' "$repo" >&2
    exit "$EXIT_USAGE"
  fi
  # Every path below is relative to the top of the work tree.
  cd -- "$top" || exit "$EXIT_USAGE"
  if ! target="$(git rev-parse --verify --quiet --end-of-options "$ref^{commit}")"; then
    printf 'unknown revision: %s\n' "$ref" >&2
    exit "$EXIT_USAGE"
  fi

  if git merge-base --is-ancestor "$target" HEAD 2>/dev/null; then
    printf 'already up to date with %s\n' "$ref"
    exit "$EXIT_OK"
  fi
  if ! git merge-base --is-ancestor HEAD "$target" 2>/dev/null; then
    printf 'not a fast-forward: HEAD is not an ancestor of %s; nothing was changed\n' "$ref" >&2
    exit "$EXIT_FAIL"
  fi

  if ! backup="$(mktemp -d "${TMPDIR:-/tmp}/ff-merge-keep-untracked.XXXXXX")"; then
    printf 'cannot create a backup directory; nothing was changed\n' >&2
    exit "$EXIT_FAIL"
  fi

  # Untracked files, ignored ones included, exactly on the paths that the
  # target commit adds. git ls-files lists only real files and symlinks and
  # never looks through a symlinked directory, so nothing outside the work
  # tree is picked up; a pathspec also matches the files under a directory of
  # that name, hence the exact intersection with comm. Other kinds of conflict
  # make the fast-forward fail below, and then every file is put back. If the
  # list cannot be built, stop: a plain merge would overwrite ignored files.
  if ! (
    set -o pipefail
    added_paths | LC_ALL=C sort -z >"$backup/added" &&
      xargs -0 -r git --literal-pathspecs ls-files --others -z -- <"$backup/added" |
      LC_ALL=C sort -z >"$backup/untracked" &&
      LC_ALL=C comm -z -12 "$backup/added" "$backup/untracked" >"$backup/paths"
  ); then
    printf 'cannot list the untracked files on the paths that %s adds; nothing was changed\n' "$ref" >&2
    rm -rf -- "$backup"
    exit "$EXIT_FAIL"
  fi

  # git also removes ignored content without asking where <rev> puts a file
  # over a directory, or a directory over a file or symlink, and such content
  # could not be put back in its place afterwards. Refuse instead: a directory
  # holding untracked or ignored files on a path that <rev> adds, or an
  # untracked or ignored file or symlink on a leading directory of such a path.
  local added dir
  local -a blocked=()
  while IFS= read -r -d '' added; do
    if [ -d "$added" ] && [ ! -L "$added" ] &&
      [ -n "$(git --literal-pathspecs ls-files --others -- "$added/")" ]; then
      blocked+=("$added/")
    fi
    dir="$added"
    while [ "${dir%/*}" != "$dir" ]; do
      dir="${dir%/*}"
      if [ -L "$dir" ] || { [ -e "$dir" ] && [ ! -d "$dir" ]; }; then
        if [ -z "$(git --literal-pathspecs ls-files --cached -- "$dir")" ]; then
          blocked+=("$dir")
        fi
        break
      fi
    done
  done <"$backup/added"
  if [ "${#blocked[@]}" -gt 0 ]; then
    printf '%s puts a file or a directory where these untracked or ignored paths are; move them out of the work tree and run again; nothing was changed:\n' "$ref" >&2
    printf '  %s\n' "${blocked[@]}" | LC_ALL=C sort -u >&2
    rm -rf -- "$backup"
    exit "$EXIT_FAIL"
  fi

  mapfile -d '' -t files <"$backup/paths"
  rm -f -- "$backup/added" "$backup/untracked"

  if [ "${#files[@]}" -eq 0 ]; then
    rm -rf -- "$backup"
    git merge --ff-only "$target" || exit "$EXIT_FAIL"
    exit "$EXIT_OK"
  fi
  printf 'backup directory: %s\n' "$backup" >&2

  # Copy and check everything before the first file is removed.
  local rel
  for rel in "${files[@]}"; do
    if { [ -L "$rel" ] || [ -f "$rel" ]; } &&
      mkdir -p -- "$backup/files/$(dirname -- "$rel")" &&
      cp -a -- "$rel" "$backup/files/$rel" && same_file "$rel" "$backup/files/$rel"; then
      continue
    fi
    printf 'cannot back up %s; nothing was changed\n' "$rel" >&2
    exit "$EXIT_FAIL"
  done

  # From here on the originals live only in the backup until restore_all.
  trap on_signal HUP INT TERM
  local removed=1 merged=0 restored=1
  for rel in "${files[@]}"; do
    if ! rm -f -- "$rel"; then
      removed=0
      break
    fi
  done
  if [ "$removed" -eq 1 ] && git merge --ff-only "$target"; then
    merged=1
  fi
  restore_all || restored=0
  trap - HUP INT TERM

  if [ "$restored" -eq 0 ]; then
    if [ "$merged" -eq 1 ]; then
      printf 'fast-forwarded to %s, but some files could not be restored; the originals are in %s\n' "$ref" "$backup/files" >&2
    else
      printf 'fast-forward failed and some files could not be restored; HEAD is unchanged; the originals are in %s\n' "$backup/files" >&2
    fi
    exit "$EXIT_FAIL"
  fi
  if [ "$merged" -eq 0 ]; then
    printf 'fast-forward failed; restored %d untracked file(s); HEAD is unchanged\n' "${#files[@]}" >&2
    exit "$EXIT_FAIL"
  fi
  printf 'fast-forwarded to %s; restored %d untracked file(s) over the merged version\n' "$ref" "${#files[@]}"
  printf 'files that differ from %s now show as modified; the backup is kept in %s\n' "$ref" "$backup"
  exit "$EXIT_OK"
}

main "$@"
