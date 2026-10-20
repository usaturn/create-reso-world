#!/bin/bash
# .devcontainer/report-resoloop-skills.bash が、各ローカルプロジェクトの resoloop skills sync --check の結果を表示し、
# 差分や失敗があっても 0 で終わることを、一時リポジトリとモックの resoloop で検査する
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-12
set -euo pipefail
# 外から渡された GIT_* を除く。linked worktree の git rebase --exec は GIT_DIR を export するので、残すと
# 直接実行したときに一時リポジトリの git init・git -C が、そのリポジトリの設定・index・ブランチを書き換える（#200）
while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com

# 一時リポジトリ: worlds/ の直下の ok・stale・edited・-dash と、従来位置の akichi。
# プロジェクトでないもの: ネストした worlds/deep/sub、.resoloop.json の無い worlds/loose、
# 作業領域の外（ルート直下の任意名）にある stray。
# プロジェクトは Git で追跡しない（ignore 対象）。検出が index に依存しないことを確かめるため、
# .gitignore に worlds/ と akichi/ を書いて commit だけに含める
repo="$tmp/repo"
git init -q "$repo"
mkdir -p "$repo/.devcontainer"
cp "$root/.devcontainer/report-resoloop-skills.bash" "$repo/.devcontainer/"
printf '/worlds/\n/akichi/\n' > "$repo/.gitignore"
for p in worlds/ok worlds/stale worlds/edited worlds/-dash akichi worlds/deep/sub stray; do
  mkdir -p "$repo/$p" && printf '{}\n' > "$repo/$p/.resoloop.json"
done
mkdir -p "$repo/worlds/loose" && printf 'x\n' > "$repo/worlds/loose/notes.txt"
git -C "$repo" add -- .devcontainer .gitignore
git -C "$repo" commit -q -m init

# モックの resoloop: 呼び出しを MOCK_LOG に記録し、プロジェクトごとに実物と同じ形の結果を返す
mkdir -p "$tmp/bin"
cat > "$tmp/bin/resoloop" <<'EOF'
#!/bin/bash
printf '%s (cwd=%s)\n' "$*" "$PWD" >> "$MOCK_LOG"
[ "$1 $2 $4" = 'skills sync --check' ] || exit 64
case "$3" in
  ./worlds/ok|./worlds/-dash|./akichi) exit 0 ;;
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

# 1. 別の cwd から実行しても、リポジトリのルートで各プロジェクトを確かめ、結果にかかわらず 0 で終わる
out="$(cd "$tmp" && PATH="$tmp/bin:$PATH" bash "$report" 2>&1)" || fail "the report failed: $out"
for s in 'ResoLoop skills: worlds/ok: up to date' 'ResoLoop skills: worlds/-dash: up to date' \
  'ResoLoop skills: akichi: up to date' \
  'ResoLoop skills: worlds/stale: the installed resoloop bundles newer skills' '    SKILL_SYNC_REQUIRED: Bundled skills' \
  'ResoLoop skills: worlds/edited: the check failed (exit 6)' '    SKILL_SYNC_CONFLICT: Bundled skill sync stopped'; do
  grep -qF -- "$s" <<<"$out" || fail "the report lacks '$s': $out"
done
# 2. プロジェクトは作業領域（worlds/ の直下と従来位置の 4 名）で .resoloop.json を持つものだけで、
#    ネストしたものや .resoloop.json の無いものは含まない。resoloop には ./ 付きで渡す
[ "$(cut -d' ' -f3 "$MOCK_LOG" | LC_ALL=C sort | tr '\n' ' ')" = './akichi ./worlds/-dash ./worlds/edited ./worlds/ok ./worlds/stale ' ] \
  || fail "unexpected projects: $(cat "$MOCK_LOG")"
grep -qF "(cwd=$repo)" "$MOCK_LOG" || fail 'resoloop did not run at the repository root'
# 3. resoloop が無ければ、表示して 0 で終わる
if PATH=/usr/bin:/bin command -v resoloop >/dev/null 2>&1; then fail 'resoloop is visible on PATH=/usr/bin:/bin'; fi
out="$(PATH=/usr/bin:/bin bash "$report" 2>&1)" || fail "the report failed without resoloop: $out"
grep -qF 'ResoLoop skills: resoloop not found; skipped the check.' <<<"$out" || fail "unexpected output without resoloop: $out"
# 4. プロジェクトが 1 つも無ければ、表示して 0 で終わる
empty="$tmp/empty" && git init -q "$empty"
mkdir -p "$empty/.devcontainer" && cp "$root/.devcontainer/report-resoloop-skills.bash" "$empty/.devcontainer/"
out="$(PATH="$tmp/bin:$PATH" bash "$empty/.devcontainer/report-resoloop-skills.bash" 2>&1)" || fail "the report failed with no projects: $out"
grep -qF 'ResoLoop skills: no projects found.' <<<"$out" || fail "unexpected output with no projects: $out"

printf 'PASS: postCreate reports the bundled skill state of each project without failing\n'
