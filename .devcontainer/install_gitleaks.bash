#!/bin/bash
# 承認済みの版の Gitleaks を ~/.local/bin/gitleaks に置く。release の tar.gz を SHA-256 で確かめ、
# 展開した gitleaks の版も確かめてから置き換える（途中で失敗しても、既にある gitleaks を変えない）。
# 版はここにだけ書く。CI の gitleaks ジョブの GITLEAKS_VERSION とそろえ（tests/scripts/test-ci.bash が比べる）、
# scripts/scan-before-push.sh はこの版の gitleaks でないと検査しない。rebuild せずに入れるときもこのスクリプトを実行する
set -euo pipefail
readonly GITLEAKS_VERSION="8.30.1"
readonly GITLEAKS_ARCHIVE_SHA256="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
fail() { printf '[install_gitleaks] ERROR: %s\n' "$1" >&2; exit 1; }

tmp="$(mktemp -d)" || fail 'Cannot create a temporary directory.'
trap 'rm -rf -- "${tmp:?}"' EXIT
archive="$tmp/gitleaks.tar.gz"
url="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
curl -fsSL -o "$archive" "$url" || fail "Downloading ${url} failed."
printf '%s  %s\n' "$GITLEAKS_ARCHIVE_SHA256" "$archive" | sha256sum -c --status - ||
    fail "The downloaded archive does not match the pinned SHA-256 ${GITLEAKS_ARCHIVE_SHA256}."
tar -xzf "$archive" -C "$tmp" gitleaks || fail 'Extracting gitleaks from the archive failed.'
extracted="$("$tmp/gitleaks" version)" || fail 'The extracted gitleaks does not run.'
[ "$extracted" = "$GITLEAKS_VERSION" ] || fail "The extracted gitleaks is version ${extracted}, not ${GITLEAKS_VERSION}."
mkdir -p "${HOME}/.local/bin" || fail 'Failed to create ~/.local/bin.'
install -m 0755 "$tmp/gitleaks" "${HOME}/.local/bin/gitleaks" || fail 'Failed to place ~/.local/bin/gitleaks.'
printf '[install_gitleaks] Gitleaks %s installed at %s.\n' "$GITLEAKS_VERSION" "${HOME}/.local/bin/gitleaks"
