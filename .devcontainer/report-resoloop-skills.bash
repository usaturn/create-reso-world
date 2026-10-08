#!/bin/bash
# 各ローカルプロジェクト（作業領域の直下にあり .resoloop.json を持つディレクトリ。
# 作業領域は worlds/ と追跡解除した従来位置の 4 名。scripts/check-layout.sh の collect_projects と同じ定義）で
# resoloop skills sync --check を実行し、結果を表示する。
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-12
# postCreate から呼ぶ。同梱スキルの同期は手動で行う（AGENTS.md の「プロジェクト運用」）ので、差分や失敗があっても常に 0 で終わる
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
say() { printf 'ResoLoop skills: %s\n' "$1"; }
relay() { [ -z "$1" ] || printf '%s\n' "$1" | sed 's/^/    /'; }

if ! command -v resoloop >/dev/null 2>&1; then
    say 'resoloop not found; skipped the check.'
    exit 0
fi
if ! cd -- "$root"; then
    say "cannot enter $root; skipped the check."
    exit 0
fi
# プロジェクトは Git で追跡しないので、作業ツリーを走査して探す
projects=()
while IFS= read -r d; do
    [ -f "$d/.resoloop.json" ] && projects+=("$d")
done < <( { for d in worlds/*/; do [ -d "$d" ] && printf '%s\n' "${d%/}"; done
            printf '%s\n' MyResoniteProject akichi slum02 slum03; } | LC_ALL=C sort -u )
if [ ${#projects[@]} -eq 0 ]; then
    say 'no projects found.'
    exit 0
fi
for p in "${projects[@]}"; do
    status=0
    # ./ を付けて、- で始まるプロジェクト名をオプションとして読ませない
    out="$(resoloop skills sync "./$p" --check </dev/null 2>&1)" || status=$?
    if [ "$status" -eq 0 ]; then
        say "$p: up to date"
    elif [ "$status" -eq 6 ] && [[ "$out" == SKILL_SYNC_REQUIRED* ]]; then
        say "$p: the installed resoloop bundles newer skills. Review the differences with 'resoloop skills sync --check' in $p, then run 'resoloop skills sync --update'."
        relay "$out"
    else
        say "$p: the check failed (exit $status). Resolve it before running 'resoloop skills sync --update'."
        relay "$out"
    fi
done
exit 0
