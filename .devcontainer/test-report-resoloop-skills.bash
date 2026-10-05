#!/bin/bash
# .devcontainer/report-resoloop-skills.bash が、各プロジェクトの resoloop skills sync --check の結果を表示し、
# 差分や失敗があっても 0 で終わることを、一時リポジトリとモックの resoloop で検査する
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-12
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com

# 一時リポジトリ: 直下のプロジェクト ok・stale・edited・-dash と、プロジェクトでないもの（ネストした deep/sub、追跡していない loose）
repo="$tmp/repo"
git init -q "$repo"
mkdir -p "$repo/.devcontainer"
cp "$root/.devcontainer/report-resoloop-skills.bash" "$repo/.devcontainer/"
for p in ok stale edited -dash deep/sub loose; do
  mkdir -p "$repo/$p" && printf '{}\n' > "$repo/$p/.resoloop.json"
done
git -C "$repo" add -- .devcontainer ok stale edited -dash deep
git -C "$repo" commit -q -m init

# モックの resoloop: 呼び出しを MOCK_LOG に記録し、プロジェクトごとに実物と同じ形の結果を返す
mkdir -p "$tmp/bin"
cat > "$tmp/bin/resoloop" <<'EOF'
#!/bin/bash
printf '%s (cwd=%s)\n' "$*" "$PWD" >> "$MOCK_LOG"
[ "$1 $2 $4" = 'skills sync --check' ] || exit 64
case "$3" in
  ./ok|./-dash) exit 0 ;;
  ./stale)
    printf 'SKILL_SYNC_REQUIRED: Bundled skills or their lock need synchronization.\n  next: Review the reported paths, then run resoloop skills sync --update.\n' >&2
    exit 6 ;;
  ./edited)
    printf 'SKILL_SYNC_CONFLICT: Bundled skill sync stopped because one or more installed skills are modified or have no trusted lock.\n' >&2
    exit 6 ;;
  *) printf 'unexpected project %s\n' "$3" >&2; exit 65 ;;
esac
EOF
chmod +x "$tmp/bin/resoloop"
export MOCK_LOG="$tmp/calls"
: > "$MOCK_LOG"
report="$repo/.devcontainer/report-resoloop-skills.bash"

# 1. 別の cwd から実行しても、リポジトリのルートで各プロジェクトを確かめ、結果にかかわらず 0 で終わる
out="$(cd "$tmp" && PATH="$tmp/bin:$PATH" bash "$report" 2>&1)" || fail "the report failed: $out"
for s in 'ResoLoop skills: ok: up to date' 'ResoLoop skills: -dash: up to date' \
  'ResoLoop skills: stale: the installed resoloop bundles newer skills' '    SKILL_SYNC_REQUIRED: Bundled skills' \
  'ResoLoop skills: edited: the check failed (exit 6)' '    SKILL_SYNC_CONFLICT: Bundled skill sync stopped'; do
  grep -qF -- "$s" <<<"$out" || fail "the report lacks '$s': $out"
done
# 2. プロジェクトは .resoloop.json を追跡している直下のディレクトリだけで、resoloop には ./ 付きで渡す
[ "$(cut -d' ' -f3 "$MOCK_LOG" | LC_ALL=C sort | tr '\n' ' ')" = './-dash ./edited ./ok ./stale ' ] \
  || fail "unexpected projects: $(cat "$MOCK_LOG")"
grep -qF "(cwd=$repo)" "$MOCK_LOG" || fail 'resoloop did not run at the repository root'
# 3. resoloop が無ければ、表示して 0 で終わる
if PATH=/usr/bin:/bin command -v resoloop >/dev/null 2>&1; then fail 'resoloop is visible on PATH=/usr/bin:/bin'; fi
out="$(PATH=/usr/bin:/bin bash "$report" 2>&1)" || fail "the report failed without resoloop: $out"
grep -qF 'ResoLoop skills: resoloop not found; skipped the check.' <<<"$out" || fail "unexpected output without resoloop: $out"

printf 'PASS: postCreate reports the bundled skill state of each project without failing\n'
