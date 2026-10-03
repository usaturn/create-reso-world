#!/bin/bash
# ルートの指示ファイル（AGENTS.md、CLAUDE.md、.pi/APPEND_SYSTEM.md）が仕様 5.2・5.3 のとおりであることを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
has() { grep -qF -- "$2" "$1" || fail "$1 lacks: $2"; }
lacks() { if grep -qF -- "$2" "$1"; then fail "$1 must not contain: $2"; fi; }

# CLAUDE.md: 1 行目が @AGENTS.md、続けて Claude Code 固有の注記
[ "$(head -n 1 CLAUDE.md)" = '@AGENTS.md' ] || fail 'CLAUDE.md line 1 must be @AGENTS.md'
for s in '## Claude Code 固有' 'AskUserQuestion' 'TaskOutput(block=true)' '.claude/skills'; do has CLAUDE.md "$s"; done

# AGENTS.md: 仕様 5.2 の節がこの順で並ぶ
expected='## リポジトリ概要
## 基本方針
## resoloop 注意
## 日本語表現
## ファイルとドラフト
## プロジェクト運用
## リポジトリ境界
## ResoLoop の版管理
## エージェント運用
## 環境
## 最新ドキュメントの取得'
actual="$(grep -E '^## ' AGENTS.md)"
[ "$actual" = "$expected" ] || fail "AGENTS.md sections differ:
$actual"
grep -qxF '### SDD 実行運用' AGENTS.md || fail 'AGENTS.md lacks ### SDD 実行運用'
[ "$(head -n 1 AGENTS.md)" = '# create-reso-world 共通規約' ] || fail 'AGENTS.md title'
# 冒頭（最初の節より前）で、本文のパスがリポジトリのルート基準であることを示す（プロジェクトを cwd にして読まれるため）
intro="$(sed -n '1,/^## /p' AGENTS.md)"
[[ "$intro" == *'本文に書くパスは、プロジェクトを cwd にしている場合も含めて、特記が無ければリポジトリのルート基準である。'* ]] \
  || fail 'AGENTS.md intro must say that paths are relative to the repository root'

# メイン作業ツリーの未コミット変更（統合時に破棄される）を取り込んでいる
for s in 'オブジェクトごとに、1つのメッシュにする' '長大なタスクであった場合は分割して実装する' 'agent-handoff' \
  '`docs_draft/` に Markdown で作成する' 'python3 を使ってよい' 'scripts/new-world.sh' \
  '.devcontainer/resoloop.lock' 'usaturn/create-reso-world' 'external/resoloop' \
  'monitoring-long-tasks' '.agents/monitoring-runtimes.md' 'find-docs' '3 回まで'; do
  has AGENTS.md "$s"
done
# AGENTS.md が参照するファイルが実在する（ResoLoop の版管理の 3 件はフェーズ 3 で作成、持ち越し N-5）
for f in .devcontainer/resoloop.lock scripts/resoloop-fork.sh docs/resoloop-fork-workflow.md \
  scripts/new-world.sh scripts/check-layout.sh .agents/monitoring-runtimes.md; do
  [ -e "$f" ] || fail "AGENTS.md refers to missing $f"
done
# 旧リポジトリ由来の記述とツール固有の記述を持ち込まない
for s in 'reStructuredText' 'Gitleaks' 'contingency' 'verify.sh' 'verify-devenv' 'AskUserQuestion' 'TaskOutput' 'npx ctx7'; do
  lacks AGENTS.md "$s"
done

# .pi/APPEND_SYSTEM.md
has .pi/APPEND_SYSTEM.md 'AGENTS.md を遵守すること'
lacks .pi/APPEND_SYSTEM.md 'CLAUDE.md を遵守'
lacks .pi/APPEND_SYSTEM.md 'subagent-launch-verification'
lacks .pi/APPEND_SYSTEM.md '# resoloop 注意'
lacks .pi/APPEND_SYSTEM.md '@.agents/skills/'
lacks .pi/APPEND_SYSTEM.md '親 checkout'
for s in '/skill:agent-handoff' 'herdr-agent-task' 'pi-model-name' 'simplify-in-subagent' 'MODEL_NAME'; do
  has .pi/APPEND_SYSTEM.md "$s"
done
# サブエージェントは Superpowers role API の同期実行で起動し、旧 API の async 引数は使わない
has .pi/APPEND_SYSTEM.md 'action、capabilities、async は指定しない'
lacks .pi/APPEND_SYSTEM.md 'async: false'
# ペルソナ節（## Response Persona 以降）は利用者が書く部分で、エージェントは 1 バイトも変えない。
# 利用者が意図して変えたときは、失敗の表示にある新しいハッシュで expected_persona を更新する
expected_persona=906d9d2570a9662427a95609efcc29454a5f46f1591352f8b264b996895e2995
persona="$(sed -n '/^## Response Persona/,$p' .pi/APPEND_SYSTEM.md | sha256sum | cut -d' ' -f1)"
[ "$persona" = "$expected_persona" ] \
  || fail "persona section changed (sha256 $persona); if the change is intended, update expected_persona in tests/scripts/test-instructions.bash"

printf 'PASS: root instruction files follow spec 5.2 and 5.3\n'
