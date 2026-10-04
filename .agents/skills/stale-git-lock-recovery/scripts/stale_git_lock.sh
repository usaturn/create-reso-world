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
# Exit codes:
#   0  no lock file (for clear: the lock was absent or was removed)
#   1  unexpected failure while removing the lock
#   2  usage error or not a git repository
#   10 lock exists and a live process holds it
#   11 lock exists and no holder was found (stale; clear may remove it)
#   12 lock exists and the holder could not be determined
#
# JSON output (--json): exactly one object on stdout with the keys
#   path, exists, removed, size, mtime, holder, stale
# `removed` is false for check and reports whether clear deleted the lock.
# Usage errors and removal failures are written to stderr and emit no JSON.
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

# A lock is "present" when the path exists, including a dangling symlink.
lock_exists() {
  [ -e "$1" ] || [ -L "$1" ]
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

# Does this PID look like a git process? Used only when its fd directory
# cannot be listed, so that a hidden git holder becomes "unknown" instead of
# silently counting as "no holder".
process_looks_like_git() {
  local pid="$1" comm="" cmdline=""
  comm="$(cat "$pid/comm" 2>/dev/null)" || comm=""
  cmdline="$(tr '\0' ' ' <"$pid/cmdline" 2>/dev/null)" || cmdline=""
  case "$comm" in
    git|git-*) return 0 ;;
  esac
  case "$cmdline" in
    "git"|"git "*|*"/git"|*"/git "*) return 0 ;;
  esac
  return 1
}

# Linux fallback: a holder is any process with an fd whose device:inode
# matches the lock (inode comparison also catches hardlinks and bind mounts).
# An fd directory that cannot be listed hides its holders; for a git process
# that is "unknown", never "absent".
holder_state_proc() {
  local path="$1" pid fd fd_id ref_id seen=0 has_fd=0
  ref_id="$(stat -Lc '%d:%i' -- "$path" 2>/dev/null)" || ref_id="$(stat -c '%d:%i' -- "$path" 2>/dev/null)" || ref_id=""
  for pid in "$PROC_ROOT"/[0-9]*; do
    [ -d "$pid" ] || continue
    seen=1
    has_fd=0
    for fd in "$pid"/fd/*; do
      [ -e "$fd" ] || [ -L "$fd" ] || continue
      has_fd=1
      fd_id="$(stat -Lc '%d:%i' -- "$fd" 2>/dev/null)" || continue
      if [ -n "$ref_id" ] && [ "$fd_id" = "$ref_id" ]; then
        case "${pid##*/}" in
          "$$"|"$BASHPID") continue ;;
        esac
        printf 'present\n'
        return 0
      fi
    done
    if [ "$has_fd" -eq 0 ] && process_looks_like_git "$pid"; then
      printf 'unknown\n'
      return 0
    fi
  done
  if [ "$seen" -eq 1 ]; then
    printf 'absent\n'
  else
    printf 'unknown\n'
  fi
  return 0
}

# Prints present | absent | unknown. A missing lsof must not turn into
# "absent": fall back to /proc. When both sources are usable their answers
# are combined as a union (present > unknown > absent), and only when neither
# source works is the answer unknown.
holder_state() {
  local path="$1" state="" combined=""
  if command -v lsof >/dev/null 2>&1; then
    state="$(holder_state_lsof "$path")"
    if [ "$state" = present ]; then
      printf 'present\n'
      return 0
    fi
    combined="$state"
  fi
  if [ -d "$PROC_ROOT" ] && [ -r "$PROC_ROOT" ]; then
    state="$(holder_state_proc "$path")"
    if [ "$state" = present ]; then
      printf 'present\n'
      return 0
    fi
    if [ "$state" = unknown ] || [ "$combined" = unknown ]; then
      combined="unknown"
    elif [ -z "$combined" ]; then
      combined="$state"
    fi
  fi
  if [ -z "$combined" ]; then
    combined="unknown"
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

  local lock_path
  if ! lock_path="$(resolve_lock_path "$repo")"; then
    printf 'not a git repository: %s\n' "$repo" >&2
    exit "$EXIT_USAGE"
  fi

  # Size and mtime are informational. The stale decision comes from the
  # holder state: absent is stale, present and unknown are not removable.
  local exists=0 size="null" mtime="null" holder="absent" stale="false" code=$EXIT_OK
  if lock_exists "$lock_path"; then
    exists=1
    holder="$(holder_state "$lock_path")"
    size="$(stat -c '%s' -- "$lock_path" 2>/dev/null)" || size="null"
    mtime="$(stat -c '%Y' -- "$lock_path" 2>/dev/null)" || mtime="null"
    [ -n "$size" ] || size="null"
    [ -n "$mtime" ] || mtime="null"
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
      printf 'remove it with: bash %s clear --repo %s\n' "$0" "$repo"
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
