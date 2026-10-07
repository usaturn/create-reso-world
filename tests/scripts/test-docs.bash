#!/bin/bash
# 現行文書が示すリポジトリ内のファイル・スキルが実在することを検査する。test-instructions.bash も --refs で使う
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

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
            # 実在を要求しない参照だけを文書・名前・backtick に限定する。周囲の文面では除外しない。
            if match[1] and name == "README.md" and ref == ".devin/config.json":
                continue  # Devin に設定ファイルを用意しない方針の注記で、配置先の案内ではない
            if match[1] and name == "AGENTS.md" and ref == "page-types.md":
                continue  # 文書名と関係を具体的に書く方針を示す架空のファイル名
            if match[1] and name == "docs/resoloop-fork-workflow.md" and ref == "global.json":
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

printf 'PASS: current docs refer only to existing files and skills\n'
