#!/bin/bash
# 現行文書のリポジトリ内参照と撤去ツールの禁止、過去の再設計記録の検査を行う。
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
has() { grep -qF -- "$2" "$1" || fail "$1 lacks: $2"; }
lacks() { if grep -qF -- "$2" "$1"; then fail "$1 must not contain: $2"; fi; }

# 指示ファイルも同じ小さい参照検査を使う。文面・見出し・リンクの表示名は検査しない。
check_refs() {
  uv run --no-project python - "$@" <<'PY'
from pathlib import Path
import re
import sys

for name in sys.argv[1:]:
    doc = Path(name)
    text = doc.read_text(encoding="utf-8")
    if name == ".pi/APPEND_SYSTEM.md":
        text = text.split("\n## Response Persona", 1)[0]  # 利用者所有部分は既存 SHA だけで保護
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if re.match(r"\s*(```|~~~)", line):
            fenced = not fenced
        if fenced:
            continue  # コードブロックはコマンド・サンプル
        for match in re.finditer(r"`([^`]+)`|\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", line):
            ref = (match[1] or match[2]).split("#", 1)[0]
            if ref.startswith("/skill:") or (match[1] and re.match(r"\s*スキル", line[match.end():])):
                ref = ".agents/skills/" + ref.removeprefix("/skill:")
            ref = ref.removeprefix("@")
            if not ref or re.search(r"[\s*?\[\]<>{}$]", ref) or re.match(r"^(?:[\w+.-]+:|[/~]|-|\.\.\.)", ref):
                continue  # 外部・ホーム・絶対パス、コマンド、glob、プレースホルダ
            if match[1] and (re.match(r"\s*は置かない", line[match.end():]) or ("/" not in ref and "のように" in line)):
                continue  # 存在しない設定の注記、ファイル名の例
            if name == "docs/resoloop-fork-workflow.md" and ref == "global.json":
                continue  # fork checkout 側のファイル（このリポジトリには置かない）
            if not re.search(r"\.(?:md|sh|bash|zsh|py|json|toml|ya?ml|txt)$", ref) and not re.match(r"^\.(?:agents|claude)/skills(?:/|$)", ref):
                continue
            paths = [doc.parent / ref] if match[2] else [Path(ref), doc.parent / ref, Path(".devcontainer") / ref]
            if not any(path.exists() for path in paths):
                sys.exit(f"FAIL: {name}:{number} refers to missing {ref}")
PY
}
if [ "${1:-}" = --refs ]; then
  shift
  check_refs "$@"
  exit 0
fi
check_refs README.md docs/superpowers/README.md docs/resoloop-fork-workflow.md

# 撤去した dsh を対象エージェントに戻さない
for f in AGENTS.md README.md; do lacks "$f" 'dsh'; done

# 再設計の統合記録: マージ前の片付け（P-1）、一覧の件数（N-4）、sp-implementer.md の比較先と同じシェル（N-12）、
# main の再 ff（M-5）、/private/ の行を消す時期（P-2）、Rebuild 後の確認（N-17・N-18・N-25・N-27）
doc=docs/integration.md
before_merge="$(sed -n '/^## PR のマージ前にユーザが行うこと$/,/^## PR のマージ後にユーザが行うこと$/p' "$doc")"
for s in 'git checkout -- .claude/settings.local.json' 'git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md' \
  '手順 2 の 2 つのコードブロックは同じシェルで実行する' 'ルートの `.agents/sp-implementer.md` と比べる' '2026-09-27 時点の該当: 68 件' 'reso-world-untracked-backup.list'; do
  grep -qF -- "$s" <<<"$before_merge" || fail "the pre-merge section of $doc lacks: $s"
done
for s in 'git fetch . feat/slum02-slum:main' 'マージに置き換えた' '## Rebuild 後に確かめること（仕様 9.3）' \
  'dotnet --list-sdks' '/home/vscode/.local/bin' '~/.config/create-reso-world' 'simplify-in-subagent' \
  'GitHub Actions' 'resoloop-fork.sh sync' 'wip/tokyo-nova-refinement` を新しい `main` に rebase した後' 'Codex は初回の起動時にプロジェクトの trust を承認する'; do
  has "$doc" "$s"
done
lacks "$doc" '随時追記'
lacks "$doc" 'Task 14'

# 過去の仕様・フェーズ 0・1 の計画書の表記（P-3・P-7・N-24）は凍結した履歴として維持する
spec=docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md
lacks "$spec" '`**/tmp/`'
lacks "$spec" '`.agents/skills/*/SKILL.md` ごとに'
has "$spec" 'git fetch . feat/slum02-slum:main'
has "$spec" 'フェーズ 4 の D-10'
has "$spec" '別の環境の postCreate が、ロックのコミットを origin から取得できるようにするため'
phase01=docs/superpowers/plans/2026-09-26-redesign-phase0-1-safety-and-hygiene.md
lacks "$phase01" '`**/` 前置に修正された'
lacks "$phase01" '追跡解除後もローカルファイルとして残る'

printf 'PASS: current doc references, removed-tool guard and archived redesign assertions\n'
