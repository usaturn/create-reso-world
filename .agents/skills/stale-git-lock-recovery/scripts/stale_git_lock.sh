#!/usr/bin/env bash
# stale_git_lock.sh — inspect and safely clear a stale git index.lock.
#
# Usage:
#   bash stale_git_lock.sh check [--json] [--repo <path>]
#   bash stale_git_lock.sh clear [--json] [--repo <path>]
#
# `check` reports whether index.lock exists and whether a live process holds
# it. `clear` removes index.lock only when `check` proves that no live holder
# exists. There is deliberately no --force.
#
# A holder is either a process with an open fd on the lock, or a live git
# process working on the same work tree: git keeps index.lock while it runs
# the hooks or the commit message editor with the lock's fd already closed
# (for example `git commit -a`), so an fd scan alone cannot prove the lock
# stale. --repo must be inside the work tree (not inside .git); GIT_DIR,
# GIT_WORK_TREE and the other repository-local variables inherited from the
# caller are ignored. Concurrent `clear` runs on the same lock are serialized
# with flock.
#
# Exit codes:
#   0  no lock file (for clear: the lock was absent or was removed)
#   1  unexpected failure (removing the lock, or serializing clear)
#   2  usage error, or --repo is not inside a git work tree
#   10 lock exists and a live process holds it
#   11 lock exists and no holder was found (stale; clear may remove it)
#   12 lock exists and the holder could not be determined, including a live
#      git process in the repository that may hold it with its fd closed
#
# JSON output (--json): exactly one object on stdout with the keys
#   path, exists, removed, size, mtime, holder, stale
# `removed` is false for check and reports whether clear deleted the lock.
# Usage errors and removal failures are written to stderr and emit no JSON.
# The processes behind a present or unknown holder are listed on stderr.
#
# Environment:
#   PROC_ROOT  location of the process filesystem (default /proc; a test
#              injection point, normally left unset)

set -u

readonly PROC_ROOT="${PROC_ROOT:-/proc}"

readonly EXIT_OK=0
readonly EXIT_FAIL=1
readonly EXIT_USAGE=2
readonly EXIT_HOLDER=10
readonly EXIT_STALE=11
readonly EXIT_UNKNOWN=12

usage() {
  cat >&2 <<'EOF'
usage: stale_git_lock.sh check [--json] [--repo <path>]
       stale_git_lock.sh clear [--json] [--repo <path>]
EOF
}

# Drop GIT_DIR, GIT_WORK_TREE and the other repository-local variables that a
# caller (for example a git hook) may export. Otherwise they override
# `git -C "$repo"` and the script would inspect another repository's lock.
clear_git_env() {
  local var
  for var in $(git rev-parse --local-env-vars); do
    unset "$var"
  done
}

# A lock is "present" when the path exists, including a dangling symlink.
lock_exists() {
  [ -e "$1" ] || [ -L "$1" ]
}

# Identity of the lock file itself (not a symlink's target). A removed and
# re-created lock gets a new change time even when the inode number is reused.
lock_identity() {
  stat -c '%d:%i:%z' -- "$1" 2>/dev/null
}

# Is $1 equal to the directory $2 or inside it? The quoted part of the pattern
# is matched literally, so glob characters in the directory name are safe.
path_is_under() {
  case "$1/" in
    "$2/"*) return 0 ;;
  esac
  return 1
}

# Print a process that makes the lock not removable, for the caller to act on.
report_process() {
  local pid="$1" reason="$2" comm="?"
  { IFS= read -r comm <"$pid/comm"; } 2>/dev/null
  printf 'pid %s (%s): %s\n' "${pid##*/}" "$comm" "$reason" >&2
}

is_self() {
  case "${1##*/}" in
    "$$"|"$BASHPID") return 0 ;;
  esac
  return 1
}

# Resolve the lock path through git itself so linked worktrees report
# .git/worktrees/<name>/index.lock instead of the main .git/index.lock.
# Only the parent directory is normalized: the lock itself may be a symlink,
# and resolving it would make clear delete the link's target instead.
resolve_lock_path() {
  local repo="$1" raw parent
  if ! raw="$(git -C "$repo" rev-parse --git-path index.lock 2>/dev/null)"; then
    return 1
  fi
  case "$raw" in
    /*) ;;
    *) raw="$repo/$raw" ;;
  esac
  if parent="$(readlink -f -- "$(dirname -- "$raw")" 2>/dev/null)" && [ -n "$parent" ]; then
    raw="$parent/$(basename -- "$raw")"
  fi
  printf '%s\n' "$raw"
}

# Escape a string for embedding in a JSON string literal. Control characters
# are emitted as \u00XX so a newline or quote in a path cannot break the JSON.
json_escape() {
  local text="$1" escaped="" char code i
  for (( i=0; i<${#text}; i++ )); do
    char="${text:i:1}"
    case "$char" in
      '"') escaped+='\"' ;;
      '\') escaped+='\\' ;;
      $'\n') escaped+='\n' ;;
      $'\r') escaped+='\r' ;;
      $'\t') escaped+='\t' ;;
      *)
        if printf -v code '%d' "'$char" 2>/dev/null && [ "$code" -lt 32 ]; then
          printf -v escaped '%s\\u%04x' "$escaped" "$code"
        else
          escaped+="$char"
        fi
        ;;
    esac
  done
  printf '%s' "$escaped"
}

# Holder detection with lsof. lsof exits 1 when nothing matches; any other
# failure means the answer is unknown, not "no holder". A header row or this
# script's own process must not be mistaken for a holder.
holder_state_lsof() {
  local path="$1" output status line
  output="$(lsof -- "$path" 2>/dev/null)"
  status=$?
  if [ -n "$output" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] || continue
      # lsof columns: COMMAND PID USER FD ... (the header is skipped too)
      set -- $line
      [ "${1:-}" = "COMMAND" ] && [ "${2:-}" = "PID" ] && continue
      case "${2:-}" in
        "$$"|"$BASHPID") continue ;;
      esac
      printf 'pid %s (%s): has the lock open\n' "${2:-?}" "${1:-?}" >&2
      printf 'present\n'
      return 0
    done <<< "$output"
    printf 'absent\n'
    return 0
  fi
  case "$status" in
    0|1) printf 'absent\n' ;;
    *) printf 'unknown\n' ;;
  esac
  return 0
}

# Is this PID a git process? Decided by the executable name (comm) or by the
# program name in argv[0], never by other words in the command line.
is_git_process() {
  local pid="$1" comm="" argv0=""
  { IFS= read -r comm <"$pid/comm"; } 2>/dev/null
  case "$comm" in
    git|git-*) return 0 ;;
  esac
  { IFS= read -r -d '' argv0 <"$pid/cmdline"; } 2>/dev/null
  case "${argv0##*/}" in
    git|git-*) return 0 ;;
  esac
  return 1
}

# Linux fallback: a holder is any process with an fd whose device:inode
# matches the lock (inode comparison also catches hardlinks and bind mounts).
# An fd directory that cannot be listed hides its holders; for a git process
# that is "unknown", never "absent". Every PID is scanned, so a holder found
# after an unknown one still makes the answer "present".
holder_state_proc() {
  local path="$1" pid fd fd_id ref_id seen=0 has_fd result=absent
  ref_id="$(stat -Lc '%d:%i' -- "$path" 2>/dev/null)" || ref_id="$(stat -c '%d:%i' -- "$path" 2>/dev/null)" || ref_id=""
  for pid in "$PROC_ROOT"/[0-9]*; do
    [ -d "$pid" ] || continue
    seen=1
    is_self "$pid" && continue
    has_fd=0
    for fd in "$pid"/fd/*; do
      [ -e "$fd" ] || [ -L "$fd" ] || continue
      has_fd=1
      fd_id="$(stat -Lc '%d:%i' -- "$fd" 2>/dev/null)" || continue
      if [ -n "$ref_id" ] && [ "$fd_id" = "$ref_id" ]; then
        report_process "$pid" "has the lock open"
        printf 'present\n'
        return 0
      fi
    done
    if [ "$has_fd" -eq 0 ] && is_git_process "$pid"; then
      report_process "$pid" "git process whose open files cannot be listed"
      result=unknown
    fi
  done
  [ "$seen" -eq 1 ] || result=unknown
  printf '%s\n' "$result"
  return 0
}

# Does a git process name the repository from elsewhere? It may do so with
# GIT_DIR, GIT_WORK_TREE, GIT_COMMON_DIR or GIT_INDEX_FILE in its environment,
# or with --git-dir / --work-tree on its command line. A relative value cannot
# be resolved reliably (git may have changed directory since it started), and
# an environment or command line that cannot be read hides the values, so both
# count as naming the repository.
git_process_refers_to() {
  local pid="$1" entry value root option=""
  local -a values=()
  shift
  { : <"$pid/environ" && : <"$pid/cmdline"; } 2>/dev/null || return 0
  while IFS= read -r -d '' entry; do
    case "$entry" in
      GIT_DIR=*|GIT_WORK_TREE=*|GIT_COMMON_DIR=*|GIT_INDEX_FILE=*) values+=("${entry#*=}") ;;
    esac
  done <"$pid/environ"
  while IFS= read -r -d '' entry; do
    if [ -n "$option" ]; then
      values+=("$entry")
      option=""
      continue
    fi
    case "$entry" in
      --git-dir=*|--work-tree=*) values+=("${entry#*=}") ;;
      --git-dir|--work-tree) option="$entry" ;;
    esac
  done <"$pid/cmdline"
  for value in "${values[@]}"; do
    case "$value" in
      /*) ;;
      *) return 0 ;;
    esac
    value="$(readlink -m -- "$value" 2>/dev/null)" || return 0
    for root in "$@"; do
      path_is_under "$value" "$root" && return 0
    done
  done
  return 1
}

# git keeps index.lock while it runs the hooks or the commit message editor
# with the lock's fd already closed (`git commit -a` writes the new index into
# the lock, closes it, runs the hooks, then renames it). An fd scan sees no
# holder then, so any live git process working on the same work tree is a
# possible holder. git runs from the top of its work tree, so the lock that git
# would use from the process's cwd tells which work tree it works on; this also
# keeps git processes in nested worktrees or submodules apart. A process that
# names the repository from elsewhere (git_process_refers_to), or whose cwd
# cannot be read, cannot be ruled out either. Arguments: the lock directory,
# then the roots of the repository.
git_activity_state() {
  local lock_dir="$1" pid cwd their_lock result=absent
  shift
  for pid in "$PROC_ROOT"/[0-9]*; do
    [ -d "$pid" ] || continue
    is_self "$pid" && continue
    is_git_process "$pid" || continue
    if ! cwd="$(readlink -- "$pid/cwd" 2>/dev/null)" || [ -z "$cwd" ]; then
      report_process "$pid" "git process whose working directory cannot be read"
      result=unknown
      continue
    fi
    if { their_lock="$(resolve_lock_path "$cwd")" && [ "$(dirname -- "$their_lock")" -ef "$lock_dir" ]; } ||
      git_process_refers_to "$pid" "$@"; then
      report_process "$pid" "git process working on this work tree; it may hold the lock with its fd closed"
      result=unknown
    fi
  done
  printf '%s\n' "$result"
  return 0
}

# Prints present | absent | unknown. A missing lsof must not turn into
# "absent": fall back to /proc. When both sources are usable their answers
# are combined as a union (present > unknown > absent). "absent" also needs
# the /proc check for live git processes on the work tree (the roots given
# after the path), so without /proc the answer is never "absent".
holder_state() {
  local path="$1" state="" combined=""
  shift
  if command -v lsof >/dev/null 2>&1; then
    state="$(holder_state_lsof "$path")"
    if [ "$state" = present ]; then
      printf 'present\n'
      return 0
    fi
    combined="$state"
  fi
  if ! [ -d "$PROC_ROOT" ] || ! [ -r "$PROC_ROOT" ]; then
    printf 'unknown\n'
    return 0
  fi
  state="$(holder_state_proc "$path")"
  if [ "$state" = present ]; then
    printf 'present\n'
    return 0
  fi
  if [ "$state" = unknown ] || [ "$combined" = unknown ]; then
    combined="unknown"
  else
    combined="$state"
  fi
  if [ "$combined" = absent ]; then
    combined="$(git_activity_state "$(dirname -- "$path")" "$@")"
  fi
  printf '%s\n' "$combined"
  return 0
}

main() {
  local mode="" json=0 repo=""
  while [ $# -gt 0 ]; do
    case "$1" in
      check|clear)
        if [ -n "$mode" ]; then
          usage
          exit "$EXIT_USAGE"
        fi
        mode="$1"
        shift
        ;;
      --json)
        json=1
        shift
        ;;
      --repo)
        if [ $# -lt 2 ]; then
          usage
          exit "$EXIT_USAGE"
        fi
        repo="$2"
        shift 2
        ;;
      --repo=*)
        repo="${1#--repo=}"
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

  if [ -z "$mode" ]; then
    usage
    exit "$EXIT_USAGE"
  fi
  [ -n "$repo" ] || repo="$PWD"

  clear_git_env

  # The work tree is required: git runs from its top while it holds the lock,
  # and inside .git (for example .git/worktrees/<name>) there is no top to
  # look for, so a running git there could be missed.
  local lock_path top
  if ! top="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || [ -z "$top" ] ||
    ! lock_path="$(resolve_lock_path "$repo")"; then
    printf 'not inside a git work tree: %s (pass the work tree, not a path inside .git)\n' "$repo" >&2
    exit "$EXIT_USAGE"
  fi

  # Directories that a git process naming this repository may point at: the
  # top of the work tree, the git dir and the common git dir.
  local roots=() dir
  for dir in "$top" "$(git -C "$repo" rev-parse --absolute-git-dir 2>/dev/null)" \
    "$(git -C "$repo" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"; do
    [ -n "$dir" ] || continue
    if dir="$(readlink -f -- "$dir" 2>/dev/null)" && [ -n "$dir" ]; then
      roots+=("$dir")
    fi
  done

  if [ "$mode" = clear ]; then
    # One clear at a time per lock directory. Otherwise a concurrent clear
    # could remove a lock that a new git process created after this run had
    # judged the previous one stale. The directory itself is locked, so no
    # extra file is left behind.
    if ! command -v flock >/dev/null 2>&1 || ! exec 9<"$(dirname -- "$lock_path")" ||
      ! flock -x -w 30 9; then
      printf 'cannot serialize clear with flock on %s; nothing was removed\n' "$(dirname -- "$lock_path")" >&2
      exit "$EXIT_FAIL"
    fi
  fi

  # Size and mtime are informational. The stale decision comes from the
  # holder state: absent is stale, present and unknown are not removable.
  local exists=0 size="null" mtime="null" holder="absent" stale="false" code=$EXIT_OK identity=""
  if lock_exists "$lock_path"; then
    exists=1
    identity="$(lock_identity "$lock_path")"
    size="$(stat -c '%s' -- "$lock_path" 2>/dev/null)" || size="null"
    mtime="$(stat -c '%Y' -- "$lock_path" 2>/dev/null)" || mtime="null"
    [ -n "$size" ] || size="null"
    [ -n "$mtime" ] || mtime="null"
    holder="$(holder_state "$lock_path" "${roots[@]}")"
    case "$holder" in
      present) code=$EXIT_HOLDER ;;
      absent)
        code=$EXIT_STALE
        stale="true"
        ;;
      *)
        holder="unknown"
        code=$EXIT_UNKNOWN
        ;;
    esac
  fi

  # The lock must still be the file that was judged stale; a replacement may
  # belong to a live git process.
  if [ "$code" = "$EXIT_STALE" ] && [ "$mode" = clear ] &&
    { [ -z "$identity" ] || [ "$(lock_identity "$lock_path")" != "$identity" ]; }; then
    printf 'the lock changed while it was being checked: %s\n' "$lock_path" >&2
    holder="unknown"
    stale="false"
    code=$EXIT_UNKNOWN
  fi

  local removed=0
  if [ "$mode" = clear ] && [ "$code" = "$EXIT_STALE" ]; then
    rm -f -- "$lock_path"
    if lock_exists "$lock_path"; then
      printf 'failed to remove: %s\n' "$lock_path" >&2
      exit "$EXIT_FAIL"
    fi
    removed=1
    exists=0
    size="null"
    mtime="null"
    holder="absent"
    stale="false"
    code=$EXIT_OK
  fi

  local exists_json="false" removed_json="false"
  [ "$exists" -eq 1 ] && exists_json="true"
  [ "$removed" -eq 1 ] && removed_json="true"

  if [ "$json" -eq 1 ]; then
    printf '{"path":"%s","exists":%s,"removed":%s,"size":%s,"mtime":%s,"holder":"%s","stale":%s}\n' \
      "$(json_escape "$lock_path")" "$exists_json" "$removed_json" "$size" "$mtime" "$holder" "$stale"
  else
    if [ "$code" = "$EXIT_OK" ]; then
      if [ "$removed" -eq 1 ]; then
        printf 'removed: %s\n' "$lock_path"
      else
        printf 'no index.lock: %s\n' "$lock_path"
      fi
    elif [ "$code" = "$EXIT_STALE" ]; then
      printf 'stale index.lock (no live holder): %s\n' "$lock_path"
      printf 'remove it with: bash %q clear --repo %q\n' "$0" "$repo"
    elif [ "$code" = "$EXIT_HOLDER" ]; then
      printf 'index.lock is held by a live process: %s\n' "$lock_path"
    else
      printf 'cannot determine the holder of index.lock: %s\n' "$lock_path"
    fi
  fi

  if [ "$mode" = clear ] && [ "$code" != "$EXIT_OK" ]; then
    case "$code" in
      10) printf 'not removed: a live process holds %s\n' "$lock_path" >&2 ;;
      12) printf 'not removed: the holder of %s cannot be determined\n' "$lock_path" >&2 ;;
    esac
    exit "$code"
  fi

  if [ "$removed" -eq 1 ]; then
    if [ "$json" -eq 1 ]; then
      printf 'removed %s; re-run the git command that failed to acquire the lock (git switch / git merge --ff-only / git add / git commit)\n' \
        "$lock_path" >&2
    else
      printf 're-run the git command that failed to acquire the lock (eg: git switch main; git merge --ff-only origin/main)\n'
    fi
  fi

  exit "$code"
}

main "$@"
