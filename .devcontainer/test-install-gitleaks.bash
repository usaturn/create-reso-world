#!/bin/bash
# Gitleaks の導入（.devcontainer/install_gitleaks.bash）を、偽の curl と偽の gitleaks を入れた tar.gz で
# ネットワークを使わずに実行する。SHA-256 を確かめてから置くことと、失敗したときに既にある gitleaks を変えないことを確かめる
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
installer="$root/.devcontainer/install_gitleaks.bash"
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

version="$(sed -n 's/^readonly GITLEAKS_VERSION="\([^"]*\)"$/\1/p' "$installer")"
[ -n "$version" ] || fail 'install_gitleaks.bash lacks readonly GITLEAKS_VERSION'

mkdir -p "$tmp/bin" "$tmp/home/.local/bin" "$tmp/fixture"
cat > "$tmp/fixture/gitleaks" <<'FAKE'
#!/bin/bash
[ "$*" = version ] || exit 93
printf '%s\n' "$FAKE_VERSION"
FAKE
# 置くときに mode 755 にすることを確かめるため、アーカイブの中は 700 にする
chmod 0700 "$tmp/fixture/gitleaks"
tar -czf "$tmp/fixture.tar.gz" -C "$tmp/fixture" gitleaks
fixture_sha="$(sha256sum "$tmp/fixture.tar.gz" | cut -d' ' -f1)"

cat > "$tmp/bin/curl" <<'FAKE'
#!/bin/bash
out='' url=''
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    -*) shift ;;
    *) url="$1"; shift ;;
  esac
done
printf '%s\n' "$url" >> "$CALLS"
[ "${FAIL_CURL:-0}" = 0 ] || exit 22
cp "$FAKE_ARCHIVE" "$out"
FAKE
chmod +x "$tmp/bin/curl"

# 成功する場合は、固定した SHA-256 を fixture の値に差し替えた写しで確かめる（本物の release は取得しない）
sed "s/^readonly GITLEAKS_ARCHIVE_SHA256=.*/readonly GITLEAKS_ARCHIVE_SHA256=\"$fixture_sha\"/" "$installer" > "$tmp/install_fixture.bash"
grep -qF "\"$fixture_sha\"" "$tmp/install_fixture.bash" || fail 'could not replace the pinned SHA-256 in a copy of the installer'

export HOME="$tmp/home" PATH="$tmp/bin:/usr/bin:/bin" CALLS="$tmp/calls" FAKE_ARCHIVE="$tmp/fixture.tar.gz" FAKE_VERSION="$version"
installed="$HOME/.local/bin/gitleaks"
reset() {
  printf '#!/bin/sh\necho existing\n' > "$installed"
  chmod 0755 "$installed"
  cp "$installed" "$tmp/existing"
  : > "$CALLS"
}
run() { local script="$1"; shift; env "$@" bash "$script" > "$tmp/output" 2>&1; }
unchanged() { cmp -s "$installed" "$tmp/existing"; }

reset
if run "$installer"; then fail 'installer accepted an archive that does not match the pinned SHA-256'; fi
unchanged || fail 'installer replaced gitleaks although the SHA-256 did not match'

reset
run "$tmp/install_fixture.bash" || { cat "$tmp/output" >&2; fail 'installer failed with an archive that matches the SHA-256'; }
cmp -s "$installed" "$tmp/fixture/gitleaks" || fail 'installed gitleaks differs from the one in the archive'
[ "$(stat -c %a "$installed")" = 755 ] || fail "installed gitleaks is mode $(stat -c %a "$installed"), not 755"
expected_url="https://github.com/gitleaks/gitleaks/releases/download/v${version}/gitleaks_${version}_linux_x64.tar.gz"
[ "$(cat "$CALLS")" = "$expected_url" ] || fail "installer downloaded '$(cat "$CALLS")' instead of $expected_url"

for setting in FAIL_CURL=1 FAKE_VERSION=0.0.0; do
  reset
  if run "$tmp/install_fixture.bash" "$setting"; then fail "installer ignored $setting"; fi
  unchanged || fail "installer replaced gitleaks with $setting"
done

printf 'PASS: Gitleaks installer verifies the SHA-256 and the version before replacing gitleaks\n'
