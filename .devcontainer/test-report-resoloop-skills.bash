#!/bin/bash
# .devcontainer/report-resoloop-skills.bash が、各ローカルプロジェクトの resoloop skills sync --check の結果を表示し、
# 差分や失敗があっても 0 で終わることを、一時リポジトリとモックの resoloop で検査する
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-12
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# 一時ディレクトリ: worlds/ の直下の ok・stale・edited と、報告スクリプトの写し。スクリプトは Git を使わず作業ツリーを走査する
repo="$tmp/repo"
mkdir -p "$repo/.devcontainer"
cp "$root/.devcontainer/report-resoloop-skills.bash" "$repo/.devcontainer/"
for p in worlds/ok worlds/stale worlds/edited; do
  mkdir -p "$repo/$p" && printf '{}\n' > "$repo/$p/.resoloop.json"
done

# モックの resoloop: 呼び出しを MOCK_LOG に記録し、プロジェクトごとに実物と同じ形の結果を返す
mkdir -p "$tmp/bin"
cat > "$tmp/bin/resoloop" <<'EOF'
#!/bin/bash
printf '%s (cwd=%s)\n' "$*" "$PWD" >> "$MOCK_LOG"
[ "$1 $2 $4" = 'skills sync --check' ] || exit 64
case "$3" in
  ./worlds/ok) exit 0 ;;
  ./worlds/stale)
    printf 'SKILL_SYNC_REQUIRED: Bundled skills or their lock need synchronization.\n  next: Review the reported paths, then run resoloop skills sync --update.\n' >&2
    exit 6 ;;
  ./worlds/edited)
    printf 'SKILL_SYNC_CONFLICT: Bundled skill sync stopped because one or more installed skills are modified or have no trusted lock.\n' >&2
    exit 6 ;;
  *) printf 'unexpected project %s\n' "$3" >&2; exit 65 ;;
esac
EOF
chmod +x "$tmp/bin/resoloop"
export MOCK_LOG="$tmp/calls"
: > "$MOCK_LOG"
report="$repo/.devcontainer/report-resoloop-skills.bash"

# 差分があれば「更新が必要」、失敗すれば「確認に失敗」と表示し（読み違えて「最新」と出すと、同梱スキルの更新に気付けない）、
# どの結果でも 0 で終わる（0 以外だと postCreate が止まる）
out="$(cd "$tmp" && PATH="$tmp/bin:$PATH" bash "$report" 2>&1)" || fail "the report failed: $out"
for s in 'ResoLoop skills: worlds/ok: up to date' \
  'ResoLoop skills: worlds/stale: the installed resoloop bundles newer skills' '    SKILL_SYNC_REQUIRED: Bundled skills' \
  'ResoLoop skills: worlds/edited: the check failed (exit 6)' '    SKILL_SYNC_CONFLICT: Bundled skill sync stopped'; do
  grep -qF -- "$s" <<<"$out" || fail "the report lacks '$s': $out"
done

printf 'PASS: postCreate reports the bundled skill state of each project without failing\n'
