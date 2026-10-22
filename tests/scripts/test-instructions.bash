#!/bin/bash
# ルートの指示ファイルの読み込み指定と利用者所有部分を検査する。
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# CLAUDE.md の読み込み指定は実際のインターフェースなので維持する。
[ "$(head -n 1 CLAUDE.md)" = '@AGENTS.md' ] || fail 'CLAUDE.md line 1 must be @AGENTS.md'

# ペルソナ節（## Response Persona 以降）は利用者が書く部分で、エージェントは 1 バイトも変えない。
# 利用者が意図して変えたときは、失敗の表示にある新しいハッシュで expected_persona を更新する
expected_persona=906d9d2570a9662427a95609efcc29454a5f46f1591352f8b264b996895e2995
persona="$(sed -n '/^## Response Persona/,$p' .pi/APPEND_SYSTEM.md | sha256sum | cut -d' ' -f1)"
[ "$persona" = "$expected_persona" ] \
  || fail "persona section changed (sha256 $persona); if the change is intended, update expected_persona in tests/scripts/test-instructions.bash"

printf 'PASS: root instruction import and persona SHA\n'
