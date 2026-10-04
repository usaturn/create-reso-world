#!/usr/bin/env bash
# ff_merge_keep_untracked.sh — fast-forward without losing untracked files
# that the incoming commits would overwrite.
#
# Usage:
#   bash ff_merge_keep_untracked.sh --ref <rev> [--repo <path>]
#
# `git merge --ff-only <rev>` refuses to run while an untracked file sits on a
# path where <rev> has a file. This script copies every such file to a backup
# directory (cp -a keeps symlinks, modes and timestamps), checks each copy,
# removes the originals, runs the fast-forward once, and then copies every
# file back over the merged version and checks it again. A file that differs
# from <rev> afterwards shows up as modified; one that matched <rev> is clean.
#
# When the fast-forward fails, every file goes back to its original place and
# HEAD is left unchanged. The backup directory is never deleted: its path is
# printed on stderr before anything is removed, together with a NUL-separated
# list of the backed-up paths in <backup>/paths.
#
# Exit codes:
#   0  fast-forwarded (or already up to date) and every file was restored
#   1  no fast-forward happened, or a file could not be restored (stderr says
#      which; the backup directory still holds the originals)
#   2  usage error, not a git work tree, or unknown <rev>

set -u

readonly EXIT_OK=0
readonly EXIT_FAIL=1
readonly EXIT_USAGE=2

files=()
backup=""

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

main() {
  local repo="" ref=""
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

  local top target
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

  # Untracked files (ignored ones excluded, as git merge does) that sit on a
  # path where the target commit has a file. Other kinds of conflict make the
  # fast-forward fail below, and then every file is put back.
  local rel
  while IFS= read -r -d '' rel; do
    if [ "$(git cat-file -t "$target:$rel" 2>/dev/null)" = blob ]; then
      files+=("$rel")
    fi
  done < <(git ls-files --others --exclude-standard -z)

  if [ "${#files[@]}" -eq 0 ]; then
    git merge --ff-only "$target" || exit "$EXIT_FAIL"
    exit "$EXIT_OK"
  fi

  if ! backup="$(mktemp -d "${TMPDIR:-/tmp}/ff-merge-keep-untracked.XXXXXX")"; then
    printf 'cannot create a backup directory; nothing was changed\n' >&2
    exit "$EXIT_FAIL"
  fi
  printf 'backup directory: %s\n' "$backup" >&2
  printf '%s\0' "${files[@]}" >"$backup/paths"

  # Copy and check everything before the first file is removed.
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
  trap 'restore_all; exit "$EXIT_FAIL"' HUP INT TERM
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
