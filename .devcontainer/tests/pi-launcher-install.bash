#!/bin/bash
# Test-only installer extraction and execution. Never source the full installer.

pi_launcher_install_fragment() {
    awk -v stop_marker='step "Installing the shared skills (herdr / find-skills)"' '
        /^step "Placing the launchers / {
            starts++
            if (stops) invalid = 1
            copying = 1
        }
        $0 == stop_marker {
            stops++
            if (!starts) invalid = 1
            copying = 0
            next
        }
        copying { body = body $0 "\n" }
        END {
            if (starts != 1 || stops != 1 || invalid) {
                print "Cannot isolate pi launcher installation: invalid section boundaries." > "/dev/stderr"
                exit 1
            }
            printf "%s", body
        }
    ' "$1"
}

pi_run_launcher_install() {
    local installer="$1" home="$2" fragment repo
    local body
    repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)" || return 1
    # Buffer before creating executable content: missing/duplicate/reversed
    # boundaries must never stream a partial installer into a shell.
    body="$(pi_launcher_install_fragment "$installer")" || return 1
    fragment="${home}/.pi-launcher-install.bash"
    {
        printf '%s\n' 'step() { :; }' 'fail() { printf "%s\n" "$1" >&2; exit 1; }'
        printf '%s\n' "$body"
    } > "$fragment" || return 1

    # Only this test-owned HOME is writable. In particular, an accidental tail
    # cannot change the repository, real /tmp or installed tools, or download.
    bwrap --die-with-parent --unshare-net --unshare-pid \
        --ro-bind / / --proc /proc --dev /dev --tmpfs /tmp \
        --ro-bind "$repo" "$repo" --chdir "$repo" \
        --bind "$home" "$home" --setenv HOME "$home" \
        -- /bin/bash -eu "$fragment"
}
