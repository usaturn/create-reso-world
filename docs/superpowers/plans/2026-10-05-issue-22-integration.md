# Issue #22 移植の比較表・README の整合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** maatlog-poc から pi と Claude Code の設定を移植した記録として、移植元の全ファイルを網羅する比較表を `docs/maatlog-poc-porting.md` に作り、README 2 本を移植の結果に揃え、rebuild での確認項目と基準値を記録して `main` 向けの PR（`Closes #22`）を作る。

**Architecture:** 変更は文書だけ（新規 1、変更 2）。比較表の網羅と README の内容は、scratchpad に置く一時の検査スクリプトで、変更前に失敗し変更後に通ることを確かめる。既存のテスト（`test-readme.bash`・`test-docs.bash` など）と配置検査で回帰がないことを確かめる。

**Tech Stack:** Markdown、bash、`uv run --no-project` の Python 3（一時スクリプト）、`gh`（移植元のツリーの取得、PR）

**Spec:** `docs/superpowers/specs/2026-10-05-issue-22-integration-design.md`

- 状態: draft（利用者の 2026-10-05 の指示「途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」による実行許可。Plan 自体の明示承認は得ていない）
- 作業場所: worktree `/workspaces/reso-world/.worktrees/issue-22-integration`、ブランチ `feat/issue-22-integration`（`origin/main` の `01affb7` から作成）
- 計画の検証: 2026-10-05 に、Spec のコミットから作った使い捨ての worktree で Task 1〜3 の内容を当て、各検査の RED と GREEN、`test-readme.bash`・`test-docs.bash`・`check-layout.sh`・`run-tests.bash` の成功を確かめた。実装ブランチのテストは実行時にもう一度行う

## Global Constraints

- 編集するのは `docs/maatlog-poc-porting.md`（新規）、`README.md`、`.devcontainer/README.md` だけ（Spec・Plan を除く）。テストファイル、導入スクリプト、ランチャー、設定ファイル、スキル、ワールドのプロジェクトは変えない
- 移植元の基準は usaturn/maatlog-poc の `1f2aadb864cb03e674ba96b0b2fbbd103caa1a6a`（blob 455 件と gitlink 1 件の計 456 件）
- 判断は「移植」「適応」「既存維持」「除外」「対象外」の 5 区分。子の Spec の別の表記は判断の後ろに括弧で残す。担当 Issue は #17〜#22
- `.devcontainer/` 配下の文に、移植元の名前（maatlog。大文字小文字を問わない）、3 桁の Issue 番号（`#NNN`）、`/workspaces/reso-world`、除外したツールの導入の記述を入れない（`.devcontainer/test-readme.bash` の 5・6）
- ルートの `README.md` に `##` の見出しを足さない（`tests/scripts/test-docs.bash` の 1）
- Python は `uv run --no-project` で実行する。一時ファイルは scratchpad（下の `$S`）に置き、リポジトリに入れない。削除コマンドの対象にシェル変数を使うときは `${VAR:?}` で空値を防ぎ、パス全体を引用する
- 認証情報の値を表示・記録しない。bind mount された利用者の設定（`~/.pi`・`~/.claude`・`~/.claude.json`）を変更するコマンドは実行しない

## Review Focus

1. 比較表の判断の読み違え: 子の Spec の表記（「削除」「不採用」「新規・適応」など）を 5 区分に揃えるときに、判断そのものを変えてしまう。Task 1 の Step 7 で子の表の全行と突き合わせる
2. README の API トークン節とランチャーの実装の食い違い: `pigs`・`pixg` の引き継ぎの条件、`ccdu` の優先順位、`ccdd`・`ccddg` の停止、MCP のヘッダーの変数。Task 2 の Step 4 で実装の該当行と照合する
3. `.devcontainer/README.md` の新しい文が `test-readme.bash` の禁止語に触れる。Task 2 の Step 6 で実行する
4. 「節名」の参照が存在しない見出しを指す。Task 3 の Step 5 で一時スクリプトを実行する
5. rebuild の確認表のコマンドが書き誤りで動かない、または利用者の設定を変える。Task 1 の Step 8 で読み取り専用のコマンドを現行コンテナで実行し、rebuild 前の列の値と一致することを確かめる。設定を変える R-6 の再実行と R-8 は実行しない

---

すべての Task で次の変数を使う。

```bash
W=/workspaces/reso-world/.worktrees/issue-22-integration
S=/tmp/claude-1000/-workspaces-reso-world/dc720f2b-7047-486a-81f6-e1bd7fb6f23d/scratchpad
cd "$W"
```

別のセッションで実行する場合は、`S` を自分の scratchpad に読み替える。

### Task 1: 比較表 `docs/maatlog-poc-porting.md`

**Files:**
- Create: `docs/maatlog-poc-porting.md`
- Test: `$S/check_porting_table.py`（一時。リポジトリに入れない）

**Interfaces:**
- Consumes: 移植元のツリー（GitHub API）、子の Spec の比較表（#18 9 章、#19「ファイル別比較表（#22 の集約用）」、#20 9 章、#21「ファイル別比較と判断」）
- Produces: `docs/maatlog-poc-porting.md` の `## 比較表`・`## 網羅の確認`・`## 指示文・MCP の読み込み`・`## rebuild での確認` の節。Task 3 がルートの `README.md` から `docs/maatlog-poc-porting.md` の「rebuild での確認」を参照する

- [ ] **Step 1: 移植元のツリーを取得する**

```bash
gh api 'repos/usaturn/maatlog-poc/git/trees/1f2aadb864cb03e674ba96b0b2fbbd103caa1a6a?recursive=1' \
  -q '.tree[] | "\(.type) \(.mode) \(.path)"' > "$S/src-tree.txt"
awk '$1!="tree"' "$S/src-tree.txt" | wc -l
```

Expected: `456`

- [ ] **Step 2: 網羅の検査スクリプトを書く**

`$S/check_porting_table.py` を次の内容で作る。

~~~~python
"""docs/maatlog-poc-porting.md の比較表が移植元のツリーを網羅しているかを確かめる（Issue #22 の一時スクリプト）。

使い方: uv run --no-project check_porting_table.py <src-tree.txt> <maatlog-poc-porting.md>
src-tree.txt は `gh api repos/usaturn/maatlog-poc/git/trees/<sha>?recursive=1 -q '.tree[] | "\\(.type) \\(.mode) \\(.path)"'` の出力。
"""
import re
import sys

JUDGEMENTS = {"移植", "適応", "既存維持", "除外", "対象外"}
ISSUES = {f"#{n}" for n in range(17, 23)}


def split_row(line):
    cells, buf, i = [], "", 0
    body = line.strip()[1:-1]
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body) and body[i + 1] == "|":
            buf += "|"
            i += 2
            continue
        if body[i] == "|":
            cells.append(buf.strip())
            buf = ""
        else:
            buf += body[i]
        i += 1
    cells.append(buf.strip())
    return cells


def main(tree_path, doc_path):
    src = set()
    for line in open(tree_path, encoding="utf-8"):
        kind, _mode, path = line.rstrip("\n").split(" ", 2)
        if kind in ("blob", "commit"):
            src.add(path)
    tops = {p.split("/", 1)[0] for p in src}

    rows, in_table_section = [], False
    for line in open(doc_path, encoding="utf-8"):
        if line.startswith("## "):
            in_table_section = line.strip() == "## 比較表"
            continue
        if not in_table_section or not line.startswith("| "):
            continue
        cells = split_row(line)
        if cells[0] == "移植元のパス" or set(cells[0]) <= {"-", " "}:
            continue
        rows.append(cells)

    errors, patterns = [], []
    for cells in rows:
        if len(cells) != 5:
            errors.append(f"column count {len(cells)}: {cells[0][:60]}")
            continue
        judgement = re.sub(r"（.*）$", "", cells[2])
        if judgement not in JUDGEMENTS:
            errors.append(f"judgement {cells[2]!r}: {cells[0][:60]}")
        if cells[4] not in ISSUES:
            errors.append(f"issue {cells[4]!r}: {cells[0][:60]}")
        for token in re.findall(r"`([^`]+)`", cells[0]):
            if token.split("/", 1)[0] not in tops:
                continue
            if token.endswith("/**"):
                prefix = token[:-2]
                if not any(p.startswith(prefix) for p in src):
                    errors.append(f"glob matches nothing: {token}")
            elif token not in src:
                errors.append(f"not in source tree: {token}")
            patterns.append(token)

    def covered(path):
        for pat in patterns:
            if pat.endswith("/**"):
                if path.startswith(pat[:-2]):
                    return True
            elif path == pat:
                return True
        return False

    missing = sorted(p for p in src if not covered(p))
    for p in missing:
        errors.append(f"not covered: {p}")

    print(f"source paths: {len(src)}  rows: {len(rows)}  path tokens: {len(patterns)}  missing: {len(missing)}")
    for e in errors:
        print("ERROR", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
~~~~

- [ ] **Step 3: 比較表が無い状態で検査が失敗することを確かめる**

Run: `uv run --no-project "$S/check_porting_table.py" "$S/src-tree.txt" docs/maatlog-poc-porting.md; echo "exit=$?"`
Expected: `FileNotFoundError` で終わり、`exit=1`

- [ ] **Step 4: 比較表を書く**

`docs/maatlog-poc-porting.md` を次の内容で作る（末尾の改行を含む）。

~~~~markdown
# maatlog-poc からの移植の比較表

[usaturn/maatlog-poc](https://github.com/usaturn/maatlog-poc) の pi と Claude Code の設定を、このリポジトリへ移植したときの記録である（Issue #17、子 Issue #18〜#22）。移植元の全ファイルについて、移植したか、移植先に合わせて変えたか、持ち込まなかったかを、理由と担当 Issue とともに残す。

利用者が参照する現在の手順は `README.md` と `.devcontainer/README.md` にある。既存の環境への反映は `.devcontainer/README.md` の「既存環境の更新」を参照する。

## 基準

- 移植元: usaturn/maatlog-poc の [`1f2aadb864cb03e674ba96b0b2fbbd103caa1a6a`](https://github.com/usaturn/maatlog-poc/tree/1f2aadb864cb03e674ba96b0b2fbbd103caa1a6a)。ファイル（blob）455 件と submodule 1 件（`public`）
- 移植先: このリポジトリの `main`。比較を始めた時点は `9699e94`、#18〜#21 の変更がそろった時点は `01affb7`
- 移植元の `main` は 2026-10-05 02:55 UTC 時点で `e1f042e` に進んでいる。追加の 17 コミットで変わった 28 ファイルは、レビュー系ツール（`tools/herdr_pr_review/**`・`pr-review-fix-loop`・`.devcontainer/herdr-pr-review.toml`）、`.devcontainer/README.md` のその説明、`CLAUDE.md` の「正本」の言い換えの規則だけである。最後のものは、このリポジトリの `AGENTS.md` に同じ文がある。どれも取り込まない

## 判断の区分

| 判断 | 意味 |
| --- | --- |
| 移植 | 移植元の内容（撤去を含む）を、そのまま取り込んだ |
| 適応 | 移植元の方針を、移植先の構成（配置、ランチャー、安全策など）に合わせて取り込んだ |
| 既存維持 | 移植先の現状を保った。移植元と同一、移植先の方が新しい、移植先にだけある、のいずれか |
| 除外 | 検討して持ち込まなかった。#17 の除外 3 項目（Grok Build・`ccda`・dsh）と、各子 Issue が採用しなかったもの |
| 対象外 | 比較の範囲外とした。#17 の「対象外とした項目」（スキル、レビュー系ツール、pi の Context7）、MaatLog 固有のもの、pi と Claude Code 以外のエージェントとツール |

## 読み方

- パスはリポジトリのルートからの相対パスで書く。`**` はそのディレクトリの配下の全ファイルを表す
- 移植元のパスが「なし」の行は、移植先にだけあるファイルや変更である
- 移植元のパスの列で移植元の見出しを「」で引くときは、見出しの中のバッククォートを省く（`public/` などを含む見出し）。下の「網羅の確認」が、この列のバッククォートの中をパスとして読むため
- 1 つのファイルを節ごとに別の子 Issue が担当した場合は、節ごとに行を分けた
- 担当 Issue は、その判断を記録した Issue である。#17 の本文で範囲外と決めた項目は #17 とした
- 子 Issue の Spec が別の表記（「削除」「不採用」など）を使った行は、判断の後ろに括弧でその表記を残した。表記を揃えただけで、判断は変えていない
- 各子 Issue の判断の詳細は、その Spec にある: #18 `docs/superpowers/specs/2026-10-04-issue-18-remove-excluded-agents-design.md`、#19 `docs/superpowers/specs/2026-10-04-issue-19-pi-migration-design.md`、#20 `docs/superpowers/specs/2026-10-04-issue-20-pi-launchers-design.md`、#21 `docs/superpowers/specs/2026-10-04-issue-21-claude-code-design.md`、#22 `docs/superpowers/specs/2026-10-05-issue-22-integration-design.md`

## 比較表

### pi 本体・拡張・MCP

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/install_beforehand.bash` の pi の導入、旧拡張の撤去（`Removing npm:pi-mcp-adapter`・`Removing npm:pi-distill`）、拡張の導入、`models.json` の配置 | 同じファイルの同じ手順 | 適応 | 撤去は移植先の `cleanup_pi_mcp.py` で行い、pi の導入の直後・全拡張の導入の前に実行する。pi-distill と tool-display の調整の呼び出しを削除した。手順の数は変えず、`STEP_TOTAL` は 25 のまま。#18 と #20 の変更を保持する | #19 |
| なし | `.devcontainer/cleanup_pi_mcp.py` | 適応 | 既存の安全策（symlink・hard link の拒否、npm の巻き添えの防止）を保ち、pi-distill、単独登録の tool-display と i18n、`-builtin:mcp` の撤去を足した。`@upstash/context7-pi` と `pi-mcp-adapter` の撤去も続ける | #19 |
| なし | `.devcontainer/pi_json.py` | 適応（#19: 新規、PR #27 のレビュー修正） | cleanup と 3 つの provider setup が共有する JSON の読み込み（有限の数値の検査）・保存（一時ファイルでの置き換え、mode の保持）・バックアップ・リンクの拒否。移植元には無い | #19 |
| なし | `.devcontainer/tests/fake_pi_packages.py` | 適応 | `pi update --extensions` による再構築をオフラインで模擬し、撤去した拡張の再混入と導入の順序を検査する | #19 |
| なし | `.devcontainer/tests/test_pi_mcp_cleanup.py`・`.devcontainer/test-pi-mcp-cleanup.bash` | 適応（#19: 適応・維持） | 拡張の撤去、バックアップ、設定の保持、実 npm の依存の扱い、初回と再実行を検査する。wrapper の公開 CLI は保つ | #19 |
| なし | `.devcontainer/setup_pi_tool_display.py`（削除） | 適応（#19: 削除） | 廃止した拡張への調整を行わない。移植元は pi-distill の廃止とともにこの調整を持たない | #19 |
| `scripts/setup_pi.zsh` | `.devcontainer/setup_pi.zsh` | 適応 | deepinfra だけを同期する。配置は `.devcontainer/` のまま。既存のモデルと他の provider を保持する | #19 |
| `.devcontainer/pi-models.json` | 同じ | 適応 | `deepinfra-distill` だけを削除した。`union-alpha` などの移植先の定義は保つ | #19 |
| `.devcontainer/zshrc.txt` の pi の環境変数 | 同じファイルの同じ箇所 | 適応 | `PI_EXTENSIONS_LOCALE` と `PI_DISTILL_*` の設定と説明を削除した。ランチャーと `update()` は保つ | #19 |
| `.pi/settings.json` | 同じ | 適応（#19: 新規・適応） | `extensions` を `["+builtin:mcp"]` にした。移植元にある MaatLog 専用の `version-export` の skills は含めない | #19 |
| `.pi/mcp.json` | 同じ | 適応（#19: 新規・適応） | Google Developer Knowledge の HTTP の設定だけを移植した。`context7` は含めない（pi の Context7 は #17 で対象外） | #19 |
| `.pi-lens.json` | 同じ | 既存維持 | 移植先の ignore（`tmp`・`.venv`・`artifacts`・`.resoloop`・`external`・`private`）は移植元を包含する | #19 |
| `.pi/APPEND_SYSTEM.md` | 同じ | 適応 | 正式なモデル名の根拠としての `PI_DISTILL_MODEL` の記述だけを削除した。persona と Superpowers の role API の運用は保つ。移植元の旧 API の記述は持ち込まない | #19 |
| なし | `.devcontainer/test-install-beforehand.bash` | 適応 | cleanup の実行の順序と、廃止した helper が呼ばれないことを検査する | #19 |
| なし | `tests/scripts/test-agent-config.bash`・`tests/scripts/test-instructions.bash` | 適応（#19: 既存維持・適応） | agent-config の既存の検査は保ち、instructions に廃止した指示が無いことの検査を足した。共有の pi の設定とワールドの cwd の検査は cleanup のテストにまとめた | #19 |
| `.devcontainer/README.md` の pi の拡張・MCP・pi-distill の節（「pi-distill の撤去（#508）」「setup スクリプトを使う場面」） | 同じファイルの「pi の旧拡張・MCP 設定の移行」「組み込み MCP と廃止した拡張」「setup スクリプトを使う場面」 | 適応 | 移行、バックアップ、既存の provider の保持を説明し、pi-distill を使う手順を削除した | #19 |

### pi のランチャー・モデル・サブエージェント

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/pi-superagents-exec.zsh` | 同じ | 移植 | pi を `--tui-mode regular` で起動する。setup の案内のパスは `.devcontainer/` のまま | #20 |
| `.devcontainer/pi-superagents/pigs.json`・`.devcontainer/pi-superagents/pixg.json` | 同じ | 移植 | `cheap`（`pixg` は `balanced` も）を `opencode-go/deepseek-v4.1-flash` の `max` にした | #20 |
| `.devcontainer/pi-superagents/pigo.json`・`.devcontainer/pi-superagents/pigod.json`・`.devcontainer/pi-superagents/piccg.json`・`.devcontainer/pi-superagents/piccd.json`・`.devcontainer/pi-superagents/piga.json`・`.devcontainer/pi-superagents/pigl.json` | 同じ | 既存維持 | 移植元と同一 | #20 |
| なし | `.devcontainer/pi-superagents/pigou.json` | 既存維持 | 移植先にだけあるランチャー | #20 |
| `.devcontainer/pigs` | 同じ | 移植 | `OPENCODE_GO_API_KEY` から `OPENCODE_API_KEY` への引き継ぎを足した。Codex OAuth の確認は保つ。案内のパスは `.devcontainer/` | #20 |
| `.devcontainer/pixg` | 同じ | 移植 | Codex OAuth の確認をやめ、引き継ぎを足した。案内のパスは `.devcontainer/` | #20 |
| `.devcontainer/pigo`・`.devcontainer/pigod`・`.devcontainer/piccg`・`.devcontainer/piccd`・`.devcontainer/piga`・`.devcontainer/pigl` | 同じ | 既存維持 | 差分は setup の案内のパスだけ。setup スクリプトを `.devcontainer/` に置く決定に合わせる | #20 |
| なし | `.devcontainer/pigou` | 既存維持 | 移植先にだけあるランチャー。`--tui-mode regular` は共通ヘルパで付く | #20 |
| `scripts/setup_pi_superagents.zsh`・`scripts/setup_pi_opencode_go.zsh`・`scripts/setup_pi_commandcode_goat.zsh` | `.devcontainer/` の同名のファイル | 適応 | 配置は `.devcontainer/` に残す。`pigou` を保ち、コメントの言い回しは移植先のまま | #20 |
| `scripts/setup_pi_opencode_go.zsh`・`scripts/setup_pi_commandcode_goat.zsh` | `.devcontainer/` の同名のファイル | 適応（PR #27 のレビュー修正） | 入力の事前検査、`pi_json` による保存とバックアップ、`~` の展開を `setup_pi.zsh` と揃えた。provider の選択とランチャーは変えていない | #19 |
| `.devcontainer/install_beforehand.bash` のランチャーの配置と `setup_pi_superagents.zsh --if-absent` の呼び出し | 同じファイルの同じ手順 | 既存維持 | 呼び出し方は変えない（#20 の D-11）。移植先は `pigou` を含む 9 本を置く。`--if-absent` が共通ヘルパを毎回更新する | #20 |
| `.agents/sp-implementer.md` | 同じ | 既存維持 | 移植元と同一 | #20 |
| `.devcontainer/test-pi-superagents.bash` | 同じ | 適応 | `--tui-mode`、argv の一致、tier、`pixg` の認証、引き継ぎ、ヘルパの更新の検査を取り込んだ。here-string と `pigou` の検査は保つ。pi-distill の検査は #19 が別のテストで行う | #20 |
| `.devcontainer/test-pi-openai-codex.bash` | 同じ | 適応 | `--tui-mode`、全ランチャーの配置の検査、Pi 0.99.1 を取り込んだ。導入の手順の切り出しは移植先の手順に合わせた | #20 |
| `.devcontainer/README.md` の GPT-6・Grok 4.7・TUI モード・tier の節 | 同じファイルの同じ節 | 適応 | tier、認証、Pi の最小版、`--tui-mode regular` の節を移植し、`pigou` と `.devcontainer/` のパスに合わせた。既存環境の更新手順を足した | #20 |

### Claude Code

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/zshrc.txt` の `ccd`・`ccdo`・`ccds` | 同じファイルの alias | 移植 | `ccd` はモデルを固定せず、`ccdo` は opus、`ccds` は sonnet で起動する | #21 |
| `.devcontainer/zshrc.txt` の `claude-deepinfra`・`ccdd` | 同じ名前の関数 | 移植 | fable を `zai-org/GLM-5.3`、opus を `deepseek-ai/DeepSeek-V4.1-Flash` にし、既定を `--model opus` にした | #21 |
| `.devcontainer/zshrc.txt` の `claude-deepinfra-glm`・`ccddg` | 同じ名前の関数 | 既存維持 | 4 つのモデルの割り当てと既定の opus が一致する | #21 |
| `.devcontainer/zshrc.txt` の `cc_launcher_unsets` | 同じ名前の配列 | 既存維持 | 移植先は `ccdu` の入力のキーも含む。`.devcontainer/test-herdr-migration.bash` の `expected_unsets` と完全に一致することを検査する | #21 |
| なし | `.devcontainer/zshrc.txt` の `claude-opencode-union`・`ccdu` | 既存維持 | 移植先にだけある機能。モデル、認証の優先順位、子プロセスの設定を変えない | #21 |
| `.claude/settings.json` | 同じ | 既存維持 | env・marketplace・`feedbackSurveyRate` は一致する。移植先だけが `feature-dev` を足している | #21 |
| `.devcontainer/install_beforehand.bash` の Claude Code とプラグインの導入 | 同じファイルの同じ手順 | 既存維持 | 移植先は 5 つのプラグインを導入する上位集合。`.devcontainer/test-install-beforehand.bash` が宣言との一致を検査する | #21 |
| `CLAUDE.md` の AskUserQuestion・監視・言語の運用 | `CLAUDE.md` | 適応 | `@AGENTS.md` とワールドの指示の継承を保ち、終了コードの確認を含む監視の手順への参照をはっきりさせた | #21 |
| `CLAUDE.md` の共通規約 | `AGENTS.md` | 既存維持 | リポジトリの境界、uv、設計、文書、SDD の監視は既に定めてある。MaatLog 固有の親子リポジトリ、CI の免除、リリースの権限、検証の入口、文書の配置は持ち込まない | #21 |
| `.mcp.json` | 同じ | 既存維持（#21: 既存維持・編集対象外） | 移植元と同一。移植元に `.claude/agents/` の追加の定義は無い | #21 |
| `.claude/settings.local.json` | なし | 除外 | 個人設定。取得・コピー・コミットしない | #21 |
| `scripts/poke_claude_onboarding.py`・`scripts/unpoke_claude_onboarding.py` | なし | 除外（#21: 不採用） | `~/.claude.json` はファイルの bind mount なので、一時ファイルからの置き換えが失敗し得る。onboarding の状態を書き換えず、通常の初回設定を使う | #21 |
| `.devcontainer/test-herdr-migration.bash` の Claude のランチャーの検査 | 同じファイル | 適応 | fake CLI に渡る argv・環境変数・終了コードを実行して確かめる | #21 |
| なし | `.devcontainer/README.md` の「Claude Code の起動と更新」 | 適応 | 移植元の `.devcontainer/README.md` に Claude Code のランチャーの節は無い（#21 の Spec の「Claude Code の案内」の行）。alias、モデルの対応、認証、手動の更新、onboarding のスクリプトを採用しないことを説明する | #21 |

### Grok Build・`ccda`・dsh

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/dsh-launcher.bash`・`.devcontainer/dshccd`・`.devcontainer/dshccd.patch.yml`・`.devcontainer/dshgo`・`.devcontainer/dshgo.patch.yml` | なし | 除外 | dsh は #17 で除外した。持ち込まない | #18 |
| `.devcontainer/dsh-cordis.patch.yml` | `.devcontainer/dsh-cordis.patch.yml`（削除） | 除外 | 同上。移植先の既存のファイルも撤去した | #18 |
| なし | `.devcontainer/dsh-settings.yaml`（削除） | 除外 | 移植先にだけあった dsh の雛形 | #18 |
| `.devcontainer/install_beforehand.bash` の dsh 0.2.0 系の導入（pi-tui の profile、managed block、ランチャーの配置）、Grok Build の導入、`skills add` の `-a grok` | 同じファイルの dsh 0.1.5 の導入と定数、書き込みの確認のリストの `.grok`・`.dsh` | 除外 | 移植元の手順は持ち込まず、移植先の手順も撤去した | #18 |
| `.devcontainer/devcontainer.json` の `.grok`・`.dsh` の mount、`pnpmVersion` の固定、`forwardPorts` の `3080` | 同じファイルの同じ箇所 | 適応 | 撤去し、pnpm は `"none"` にした。`name`・dotnet・`remoteEnv`・秘密情報の mount・`--network=host` の差分は、移植先が新しいので保つ | #18 |
| `.devcontainer/initialize.bash` の `.grok`・`.dsh` | 同じ | 適応 | 撤去した。他の差分は移植先が新しいので保つ | #18 |
| `.devcontainer/zshrc.txt` の `grok update`、`cc_launcher_unsets` | 同じファイルの `ccda`、`MAAS_ANTHROPIC_TOKEN`、`grok update`、コメント | 除外 | 撤去した。移植元も `ccda` を撤去済み | #18 |
| `.devcontainer/README.md` の dsh・Grok Build の記述 | 同じファイルの dsh の節、ツールの表、読み込みの制約、秘密情報 | 適応 | 案内を撤去し、既存環境向けの注記を足した | #18 |
| `.devcontainer/docs/herdr-session-cwd-restore.md` | 同じ | 適応 | grok の例を外した。maatlog 固有のパスは移植先で汎用化済みなので保つ | #18 |
| なし | `AGENTS.md`・`README.md` の対象エージェントの一覧 | 適応 | 一覧から dsh を外した | #18 |
| `.devcontainer/test-herdr-migration.bash` の `ccda` の検査 | 同じファイル | 適応 | `ccda` の検査を外し、再混入の検査を足した。here-string などの差分は移植先が新しいので保つ | #18 |
| なし | `.devcontainer/test-initialize-mounts.bash`・`.devcontainer/test-readme.bash`・`.devcontainer/test-shell-tools.bash`・`tests/scripts/test-docs.bash` | 適応 | 除外したものを必須にしていた検査を新しい方針に合わせ、再混入の検査を足した | #18 |

### Dev Container・シェル・文書の共有ファイル

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/install_beforehand.bash` の Codex・Cursor・Devin・uv・Starship・Herdr・共有スキル（herdr / find-skills）の導入と、`pi-subagents` から `@teelicht/pi-superagents` への置き換え | 同じファイルの同じ手順 | 既存維持 | 移植先の手順で足りる。`pi-subagents` の置き換えは移植元と同等（差分はコメントの Issue 番号だけ） | #22 |
| `.devcontainer/install_beforehand.bash` の `~` 配下の書き込み可能なディレクトリの用意、apt の設定、基本パッケージとロケール、Herdr の補助スクリプトの配置、作業領域の掃除、`~/.zshrc` への連結 | 同じファイルの同じ手順 | 既存維持 | 移植先の手順で足りる。違いは、ディレクトリの一覧（`.grok`・`.dsh` は #18 で撤去し、移植先は秘密情報の置き場 `~/.config/create-reso-world` を持つ）、移植先だけが導入する `blender`、基本パッケージの前の重複した `apt update`（移植先は直前の手順の 1 回だけ）、移植元だけが置くレビュー系ツールの herdr-pr-review（移植先は `cleanup-workspace.bash` を symlink ではなくコピーで置く）と、コメントの Issue 番号 | #22 |
| `.devcontainer/install_beforehand.bash` の `public` の checkout、Gitleaks と Playwright の導入 | なし | 対象外 | MaatLog の公開アプリケーションと検証のための手順 | #22 |
| なし | `.devcontainer/install_beforehand.bash` の ResoLoop の導入と Resonite のツールの確認 | 既存維持 | 移植先にだけある手順 | #22 |
| `.devcontainer/zshrc.txt` の Cursor と Devin の alias（`cur`・`curo`・`dev`・`devo`・`devs` のモデルの固定） | 同じファイルの `cur`・`dev` | 対象外 | #17 の実行ボードで、Cursor と Devin の alias はどの子も変えないと決めた | #17 |
| `.devcontainer/zshrc.txt` の `maatlog_periodic_cleanup` と `update()` | 同じファイルの `workspace_periodic_cleanup` と `update()` | 既存維持 | 移植先は定期の掃除を汎用化し、`update()` は無いツールを飛ばす `update_if_present` を使う。`grok update` の撤去は #18 | #22 |
| なし | `.devcontainer/zshrc.txt` の `require_command`・`update_if_present`、秘密情報の `env` の読み込み、.NET のツールの PATH | 既存維持 | 移植先にだけある補助 | #22 |
| `.devcontainer/zshrc.txt` のほかの行で扱わない設定（シェルの基本設定、PATH、git の alias、`genv`・`cod`・`buni`、`EDITOR`・`LANG`、Herdr の起動の関数、Starship の初期化） | 同じファイルの同じ箇所 | 既存維持 | 移植元と同じ。違いは、関数の `require_command` の呼び出し（移植先にだけある補助）と、bun の補完のパス（移植先は `$BUN_INSTALL` を使う）だけ | #22 |
| `.devcontainer/cleanup-workspace.bash` | 同じ | 既存維持 | 移植先は汎用化した版（`WORKSPACE_CLEANUP_*`）。移植元の版は対象外のレビュー系ツールの reaper CLI に依存する | #22 |
| `.devcontainer/herdr-agent-task.bash`・`.devcontainer/herdr-git-status.bash`・`.devcontainer/herdr-status-updater.bash`・`.devcontainer/herdr.toml` | 同じ | 既存維持 | 移植元と同一 | #22 |
| `.devcontainer/test-herdr-agent-task.bash`・`.devcontainer/test-herdr-status.bash` | 同じ | 既存維持 | 移植先が新しい（here-string で SIGPIPE を避ける）。コメントの言い換えは、移植元だけのコメントの言い換えの行で扱う | #22 |
| `.devcontainer/zshrc.txt`・`.devcontainer/test-herdr-migration.bash`・`.devcontainer/test-pi-superagents.bash`・`.devcontainer/test-herdr-agent-task.bash` のコメントの言い換え（「正本」を「基準」「元ファイル」に、「契約」を「仕様」にしたもの） | 同じファイル（コメントは変えない） | 除外 | 移植元は `AGENTS.md` の日本語表現の規則に合わせてコメントを言い換えた。これらのファイルは #22 の編集範囲外で、言い換えは動作に関わらないので取り込まない。移植先の `AGENTS.md` にも同じ規則があるので、言い換えはこれらのファイルを変える別の作業で行う | #22 |
| `.devcontainer/starship.toml` | 同じ | 既存維持 | 移植先は cwd から上へ最寄りの `.venv` を探し、ワールドごとの `.venv` に対応する。移植元はリポジトリのルートの `.venv` だけを見る | #22 |
| `.cursor/rules/shell-env-hygiene.mdc` | 同じ | 既存維持 | 移植元と同一 | #22 |
| `.gitignore` | 同じ | 既存維持 | 移植先の追跡の方針（2026-09-26 の再設計の 4.4 節）を保つ。`docs_draft/`・`/.worktrees/`・`/.claude/worktrees/` は移植先にもある。MaatLog と Node.js 向けの除外は持ち込まない | #22 |
| `.devcontainer/README.md` の pi の「API トークン」 | 同じファイルの「秘密情報」「API トークン」と新設の「既存環境の更新」 | 適応 | #18〜#21 の変更に合わせて、変数の説明と既存環境の手順をまとめた | #22 |
| `.devcontainer/README.md` の「Codex で CLAUDE.md を指示ファイルとして読む」「Herdr サイドバーの設定移行」「エージェント向けツールの導入」 | 同じファイルの「エージェントの読み込みの制約」「Herdr サイドバーの設定移行」「エージェント向けツールの導入」 | 既存維持 | 移植先の Codex は `AGENTS.md` を直接読むので、fallback の設定は不要と説明している。Herdr と導入の節は移植先の構成（9 本のランチャー、5 つのプラグイン）で書いてある | #22 |
| `.devcontainer/README.md` の「pi のモデル定義とランチャー」「モデル定義の正」 | 同じファイルの同じ節 | 既存維持 | 差分は setup スクリプトのパス（移植先は `.devcontainer/` に置く）と、移植先にだけある `pigou` の説明だけ | #22 |
| `.devcontainer/README.md` の冒頭の説明と「public/ checkout の検査と復旧」「npm への一本化（#147）と既存環境の移行」 | なし | 対象外 | MaatLog の親子リポジトリと `public/` submodule（Playwright の導入を含む）、yarn からの移行の手順 | #22 |
| `.devcontainer/README.md` の「PR レビューの一括起動（herdr-pr-review）」 | なし | 対象外 | レビュー系ツール | #17 |
| `README.md` | `README.md` | 対象外 | 移植元の README は MaatLog の開発ワークスペースの説明で、エージェントの設定を含まない。移植先の README の更新は下の行と #18 の行 | #22 |
| なし | `README.md` の ResoLoop の版の説明 | 適応（PR #27 のレビュー修正） | ResoLoop の導入の説明を `.devcontainer/resoloop.lock` の nuget / fork モードに合わせた | #19 |
| なし | `README.md` の「構成」「エージェントで作業する」「対象外」 | 適応 | この比較表への参照と、pi の project trust の注意を足した | #22 |
| なし | `docs/maatlog-poc-porting.md`（この文書） | 適応 | #17 の比較表と rebuild での確認の記録 | #22 |
| なし | `tests/skills/test_legacy_references.py` の `EXCLUDED` | 適応 | この文書は移植元の全ファイルを載せる移行の記録なので、追跡ファイルに移植元の名前を禁じるガードの例外にした。設計記録（`docs/superpowers`）と同じ扱い | #22 |

### 対象外: スキル・レビュー系ツール・pi の Context7

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.agents/skills/**`（85 件。agent-handoff、find-docs、herdr-agent-task、monitoring-long-tasks、pi-model-name、planning-parallel-issues、pr-review、pr-review-fix-loop、repo-cleanup-after-merge、repository-ownership、review-fix-planning、simplify-in-subagent、version-export） | `.agents/skills/` | 対象外 | スキルは移植・統合しない。移植先の現在の内容と `.claude/skills/` の symlink の構成を保つ | #17 |
| `.claude/skills/**`（109 件。agent-handoff、herdr-agent-task、monitoring-long-tasks、planning-parallel-issues、pr-review、pr-review-fix-loop、python-extension-docs、repo-cleanup-after-merge、repository-ownership、review-fix-planning、rst-writer、version-export） | `.claude/skills/` | 対象外 | 同上 | #17 |
| `.agents/monitoring-runtimes.md` | 同じ | 対象外 | スキルが参照する文書。移植先の内容を保つ | #17 |
| `.agents/review-records.md`・`.agents/scripts/**`（4 件。`agent_tmp.py`・`review_records.py` とそのテスト） | なし | 対象外 | レビュー系ツール | #17 |
| `.devcontainer/herdr-pr-review.bash`・`.devcontainer/herdr-pr-review-launch.bash`・`.devcontainer/herdr-pr-review.toml` | なし | 対象外 | レビュー系ツール | #17 |
| `tools/__init__.py`・`tools/herdr_pr_review/**`（116 件）・`tools/review_triage/**`（37 件）・`tools/devenv/**`（3 件）・`tools/devenv_migration/**`（16 件）・`tools/test_support/**`（10 件） | なし | 対象外 | レビュー系ツールとその支援 | #17 |
| `.devcontainer/install_beforehand.bash` の `npm:@upstash/context7-pi` の導入、`.pi/mcp.json` の `context7` | なし | 対象外 | pi の Context7 は持ち込まない。移植先の `cleanup_pi_mcp.py` による `@upstash/context7-pi` の撤去は続ける。Claude Code・Codex・Cursor の Context7 と `find-docs` は変えない | #17 |

### 対象外: MaatLog 固有・他のエージェント

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.gitmodules`・`public` | なし | 対象外 | MaatLog の `public/` submodule（公開アプリケーション） | #17 |
| `.github/workflows/ci.yml`・`scripts/ci/verify-devenv.sh` | なし（移植先は自分の `.github/workflows/ci.yml` を持つ） | 対象外 | MaatLog の CI と検証の入口 | #17 |
| `.cursor/rules/repository-ownership.mdc` | なし | 対象外 | Cursor の設定で、MaatLog の親子リポジトリの規約 | #17 |
| `.codex/.gitkeep` | なし（移植先は `.codex/config.toml` を持つ） | 対象外 | standalone Codex の新しい設定は #17 の範囲外 | #17 |
| `.devin/skills/**`（3 件。pr-review、simplify-in-subagent） | なし | 対象外 | Devin の設定とスキル | #17 |
| `opencode.json` | なし | 対象外 | OpenCode CLI の設定（Superpowers のプラグインと pyright の LSP）。移植先は OpenCode CLI を導入しない。`ccdu` と `pigo` などは OpenCode Go の API を使うが、この設定は使わない | #22 |
| `scripts/add_pi_skills_setting.py` | なし | 除外 | pi は `.agents/skills` を cwd から git のルートまで自動で読むので不要。`~/.pi/agent/settings.json` に `.claude/skills` の絶対パスを足すと、ホストと共有する `~/.pi` を通じて他のワークスペースの pi にも効く。スキルの読み込みは #17 で対象外 | #22 |

## 網羅の確認

移植元のファイルがすべていずれかの行に当たることを、次の方法で確かめた（#22 の Plan の一時スクリプト）。

1. GitHub の API で移植元 `1f2aadb` のツリーを取得し、ファイル（blob）と submodule（gitlink）のパスを列挙する
2. 上の比較表の「移植元のパス」の列から、バッククォートで囲んだパスを取り出す。`**` で終わるものはそのディレクトリの配下全体、それ以外は完全一致として扱う
3. 移植元の全パスが、いずれかの行に当たることを確かめる
4. 表に書いたパス（`**` を除く）が、移植元に存在することを確かめる
5. 判断の列が 5 つの区分のどれかで、担当 Issue の列が #17〜#22 のどれかであることを確かめる

結果（2026-10-05）: 移植元の 456 件（blob 455 件、gitlink 1 件）がすべていずれかの行に当たり、表の移植元のパスはすべて移植元に存在した。判断と担当 Issue の列もすべて定めた値だった。

## 指示文・MCP の読み込み

リポジトリのルートと 4 つのワールド（`MyResoniteProject/`・`akichi/`・`slum02/`・`slum03/`）を cwd にしたときに読まれるものは次のとおり。

| エージェント | 指示文 | スキル | プロジェクトの設定・MCP |
| --- | --- | --- | --- |
| Claude Code | `CLAUDE.md` を cwd から祖先まで読む。ルートとワールドの `CLAUDE.md` は `@AGENTS.md` で同じ階層の `AGENTS.md` を読み込む | `.claude/skills` を cwd から git のルートまで読む。ルートの `.claude/skills/<name>` は `.agents/skills/<name>` への symlink | `.mcp.json`（Context7、Google Developer Knowledge）は git のルートで解決する。ワールドの `.claude/settings.json` はルートの設定への symlink |
| pi | `AGENTS.md` を cwd から祖先まで読む（project trust に関係なく読む） | `.agents/skills` を cwd から git のルートまで読む。project trust が必要 | `.pi/settings.json`（`+builtin:mcp`）・`.pi/mcp.json`（Google Developer Knowledge）・`.pi/APPEND_SYSTEM.md` は cwd の直下だけを読む。ワールドは `.pi -> ../.pi` で同じ設定を読む。project trust が必要 |
| Codex | `AGENTS.md` を git のルートから cwd まで読む | `.agents/skills` を cwd から git のルートまで読む | `.codex/config.toml`（`context7_stdio`）は、プロジェクトを trust したときだけ読む |

確かめた方法（2026-10-05、`01affb7` の後の作業ブランチ）:

- `bash scripts/check-layout.sh` がワールドの `.pi -> ../.pi`、`.claude/settings.json` の symlink、`.claude/skills/` の symlink を検査し、PASS した
- `tests/scripts/test-instructions.bash`・`tests/scripts/test-agent-config.bash`・`.devcontainer/tests/test_pi_mcp_cleanup.py`（ルートと各ワールドの cwd から `.pi/settings.json`・`.pi/mcp.json` を読む検査を含む）が PASS した
- 各ワールドで `.pi`・`.claude/settings.json` の解決先と `CLAUDE.md` の内容を静的に確かめた
- 実際の CLI での読み込みは project trust の承認が要るので、rebuild 後の確認の R-11 で確かめる

## rebuild での確認

### 手順

1. ホストの作業ツリー（`/workspaces/reso-world`）を最新の `origin/main` に追従させる。rebuild は作業ツリーの `.devcontainer/` を使う。#22 の PR は文書とテストの例外の 1 行だけを変え、導入スクリプトと設定ファイルを変えないので、`origin/main`（`01affb7` 以降）で rebuild すれば、移植の結果を確かめられる
2. `.devcontainer/README.md` の「既存環境の更新」に従って、ホストの `~/.config/create-reso-world/env` を見直す
3. VS Code で Dev Containers: Rebuild Container を実行する
4. 下の表の各項目を「確認のコマンド」で確かめ、「rebuild 後」の列に結果を書く。R-6 の `cleanup_pi_mcp.py` の再実行、R-8、R-11 は利用者の設定を変える操作や対話の承認を含むので、利用者が行うか、利用者の了承を得てから行う

### 確認項目と記録

「rebuild 前」は、移植前の `main` から作られたコンテナで 2026-10-05 に読み取り専用のコマンドで確かめた値である。認証情報の値は記録しない。「確認のコマンド」も値を表示しない（R-4 は変数名だけを出す）。

| 番号 | 確認項目 | 確認方法 | 期待する結果 | rebuild 前（2026-10-05） | rebuild 後 |
| --- | --- | --- | --- | --- | --- |
| R-1 | postCreate が全手順を完了する | Dev Containers のログ（postCreateCommand の出力） | `[install_beforehand] [25/25] Installing Herdr` まで進み、エラーで止まっていない | （記録なし） | 未記録 |
| R-2 | mount が 12 件で、dsh と Grok Build の mount が無い | `/home/vscode` 配下の mount の数と、`.dsh`・`.grok` の mount（R-2 のコマンド） | 12 件、`.dsh`・`.grok` は無い | 14 件。`~/.dsh`・`~/.grok` がある | 未記録 |
| R-3 | dsh・Grok Build が無く、pnpm を npm で導入せず、転送するポートは 8000 だけ | `dsh`・`grok` のコマンド、npm の大域パッケージの `pnpm`、`pnpm` のコマンドの実体（R-3 のコマンド）と、VS Code の「ポート」 | `dsh`・`grok` は無い。npm の大域パッケージに `pnpm` が無い（`(empty)`）。Node の feature が `corepack enable` で置く `pnpm` の shim は残ってよい（`readlink -f` が `corepack/dist/pnpm.js` を指す）。3080 は転送しない | `dsh` がある。`grok` は無い。`pnpm` は npm の大域パッケージ（`pnpm@12.4.1`） | 未記録 |
| R-4 | 廃止した環境変数が新しいシェルに無い | 新しいシェルの環境変数の名前（R-4 のコマンド。値は表示しない） | 何も出ない（`MAAS_ANTHROPIC_TOKEN` は `env` から消した場合）。残っていれば変数名だけが出て、値は出ない | `PI_DISTILL_*` の 3 つ、`PI_EXTENSIONS_LOCALE`、`MAAS_ANTHROPIC_TOKEN` がある | 未記録 |
| R-5 | 撤去した拡張が残らず、設定とモデルが残る | `pi list --no-approve`（プロジェクトの trust を問わない）、pi 管理の npm マニフェストの依存、settings の `extensions`、`models.json` の provider（R-5 のコマンド） | `pi-mcp-adapter`・`@upstash/context7-pi`・`pi-distill`・`pi-extensions-tool-display`・`pi-extensions-i18n` が無い。`extensions` に `-builtin:mcp` が無い。provider は rebuild 前と同じ | `@upstash/context7-pi` が登録され、npm マニフェストにもある。`extensions` は空。provider は `commandcode`・`deepinfra`・`deepinfra-distill`・`opencode-go` | 未記録 |
| R-6 | バックアップは変更が必要なときだけ作られる | バックアップの一覧を見て、cleanup を再実行してから同じ一覧を見る（R-6 のコマンド） | rebuild で 1 つ作られ（rebuild 前に `@upstash/context7-pi` があるため）、再実行では増えない | `migration-backups` は無い | 未記録 |
| R-7 | 全ランチャーが `--tui-mode regular` で起動し、追加の指定が後ろに残る | 9 本のランチャーの dry-run（R-7 のコマンド）。dry-run でも、argv を出す前に各ランチャーの前提を確かめる: `piga`・`pigs`・`pigl` は Codex OAuth、`pixg` は xAI OAuth（どちらも `~/.pi/agent/auth.json`）、`piccg`・`piccd` は `COMMANDCODE_API_KEY` と `models.json` の commandcode の定義（`piccd` は DeepSeek のモデルも）、`pigou` は `models.json` の `union-alpha` の定義。9 本に共通の `bwrap`・共通ヘルパ・ランチャー別の設定は rebuild で配置される | 前提がそろったランチャーは、pi の引数の先頭に `--tui-mode`・`regular` があり、後ろに `--tui-mode`・`fullscreen` が残る。前提が無いランチャーは案内を出して終了するので、「前提が未設定のため未確認」と記録する | `pigo`・`pigs`・`pixg` の 3 本で確かめ、ヘルパが付ける `--tui-mode regular` が無い（`--tui-mode` は利用者が渡した 1 つだけ） | 未記録 |
| R-8 | `pigs`・`pixg` の tier がリポジトリの値になる | setup を `--if-absent` なしで実行してから、`pigs`・`pixg` のランチャー別の設定の tier をリポジトリの値と比べる（R-8 のコマンド） | 一致する（差分が出ない）。変更があった設定はバックアップされる | すでに一致している（ホストと共有する `~/.pi` を別の環境で更新済みと考えられる） | 未記録 |
| R-9 | Claude Code のランチャーがそろい、`ccda` が無い | Claude Code の alias と関数（R-9 のコマンド） | 3 つの alias と 6 つの関数がある。`ccda`・`claude-alibaba` は無い | alias は `ccd` だけ。`ccda`・`claude-alibaba` がある | 未記録 |
| R-10 | Claude Code のプラグインが宣言と一致する | `claude plugin list`（R-10 のコマンド） | `example-skills`・`feature-dev`・`ripgrep`・`superpowers`・`web-quality-skills` がある | 5 つともある | 未記録 |
| R-11 | pi がルートとワールドでプロジェクトの設定を読む | ルートと、ワールドの代表として `slum02/` で素の `pi` を起動し、project trust を承認してから `/mcp` を開く（4 つのワールドは同じ `.pi -> ../.pi` を持ち、R-12 の `check-layout.sh` が検査する） | `google-dev-knowledge` が表示される（キーが無ければ接続のエラーを 1 回通知する） | 未確認 | 未記録 |
| R-12 | テスト一式が通る | リポジトリのルートでテスト一式を実行する（R-12 のコマンド） | すべて成功する | PASS、27/27、516 passed・1 skipped（`01affb7` の worktree） | 未記録 |

### 確認のコマンド

表のセルにはコマンドを書かない。表のセルでは `|` を `\|` と書く必要があり、Markdown のソースから写すとシェルが別のコマンドとして実行する（R-4 では環境変数の値がすべて表示される）。コマンドは次のブロックから写し、リポジトリのルートで実行する。

読み取り専用のコマンド（利用者の設定を変えない）:

```bash
# R-2
findmnt -rn -o TARGET | grep -c '^/home/vscode'
findmnt -rn -o TARGET | grep -E '/\.(dsh|grok)$'
# R-3
command -v dsh grok
npm ls -g --depth=0 pnpm
readlink -f "$(command -v pnpm)"
# R-4（変数名だけを出し、値は出さない）
zsh -ic 'env' 2>/dev/null | grep -oE '^(PI_DISTILL_[A-Z_]+|PI_EXTENSIONS_LOCALE|MAAS_ANTHROPIC_TOKEN)='
# R-5（`--no-approve` は、プロジェクトの trust を決めていないときの確認を出さない）
pi list --no-approve
jq '.dependencies' ~/.pi/agent/npm/package.json
jq '.extensions' ~/.pi/agent/settings.json
jq '.providers | keys' ~/.pi/agent/models.json
# R-6（一覧だけ。cleanup の再実行は下のブロック）
ls -d ~/.pi/agent/migration-backups/pi-retired-*
# R-7
for l in pigo pigod pigou piccg piccd piga pigs pigl pixg; do PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 $l --tui-mode fullscreen; done
# R-9（標準入力を閉じる。端末から実行しても、`~/.zshrc` の末尾が herdr を起動しない）
zsh -ic 'alias ccd ccdo ccds; whence -w ccdd ccddg ccdu claude-deepinfra claude-deepinfra-glm claude-opencode-union ccda claude-alibaba' </dev/null
# R-10
claude plugin list
# R-12
bash scripts/check-layout.sh
bash .devcontainer/run-tests.bash
uv run pytest tests/skills .agents/skills
```

利用者の設定を変えるコマンド（利用者が行うか、利用者の了承を得てから実行する）:

```bash
# R-6: cleanup を再実行し、バックアップの一覧が増えないことを確かめる
uv run --no-project .devcontainer/cleanup_pi_mcp.py
ls -d ~/.pi/agent/migration-backups/pi-retired-*
# R-8: tier を置き直し、pigs と pixg の tier をリポジトリの値と比べる（一致すれば何も出ない）
zsh .devcontainer/setup_pi_superagents.zsh
for l in pigs pixg; do diff <(jq -cS .superagents.modelTiers ~/.pi/agent/extensions/subagent.d/$l/config.json) <(jq -cS .superagents.modelTiers .devcontainer/pi-superagents/$l.json); done
```

### 実認証のスモークテスト（別枠）

次は実際の認証と provider への接続が要るので、この記録の対象外とし、未検証である。

- pi の 9 ランチャーの起動と応答（OpenCode Go、Command Code、ChatGPT Pro の Codex OAuth、xAI OAuth）
- pi-superagents の子 Pi の tier ごとの起動
- `ccdd`・`ccdd --model fable`・`ccddg`（DeepInfra）と `ccdu`（OpenCode Go）
- pi と Claude Code の Google Developer Knowledge の MCP の接続
~~~~

- [ ] **Step 5: 網羅の検査を通す**

Run: `uv run --no-project "$S/check_porting_table.py" "$S/src-tree.txt" docs/maatlog-poc-porting.md; echo "exit=$?"`
Expected:

```text
source paths: 456  rows: 96  path tokens: 114  missing: 0
exit=0
```

- [ ] **Step 6: 検査が漏れと書き間違いを検出することを確かめる**

```bash
grep -v '^| `.gitignore`' docs/maatlog-poc-porting.md \
  | sed 's/`opencode.json`/`opencode.jsn`/; s/| 適応 | deepinfra だけ/| 移す | deepinfra だけ/' > "$S/broken.md"
uv run --no-project "$S/check_porting_table.py" "$S/src-tree.txt" "$S/broken.md"; echo "exit=$?"
```

Expected: `ERROR judgement '移す'`、`ERROR not covered: .gitignore`、`ERROR not covered: opencode.json` が出て `exit=1`

- [ ] **Step 7: 子の Spec の行と突き合わせる**

```bash
sed -n '/^## 9. 比較表の行/,/^## 10/p' docs/superpowers/specs/2026-10-04-issue-18-remove-excluded-agents-design.md | grep '^| `\|^| なし'
sed -n '/^## ファイル別比較表/,/^## 移行処理/p' docs/superpowers/specs/2026-10-04-issue-19-pi-migration-design.md | grep '^| `'
sed -n '/^## 9. 比較表の行/,/^## 10/p' docs/superpowers/specs/2026-10-04-issue-20-pi-launchers-design.md | grep '^| `\|^| なし'
sed -n '/^## ファイル別比較と判断/,/^## 設計と決定/p' docs/superpowers/specs/2026-10-04-issue-21-claude-code-design.md | grep '^| `\|^| 同ファイル\|^| 対応なし\|^| ランチャー\|^| Claude'
```

Expected: 出力は #18 が 12 行、#19 が 18 行、#20 が 13 行、#21 が 14 行。各行について、比較表に同じファイル（と節）の行があり、判断が同じ（子の表記が 5 区分と違う行は、比較表の判断の後ろの括弧にその表記がある）。違いがあれば比較表を直してから Step 5 に戻る

- [ ] **Step 8: rebuild の確認表の読み取り専用のコマンドを確かめる**

```bash
findmnt -rn -o TARGET | grep -c '^/home/vscode'
findmnt -rn -o TARGET | grep -E '/\.(dsh|grok)$'
for c in dsh grok pnpm; do printf '%s=%s\n' "$c" "$(command -v "$c" >/dev/null && echo yes || echo no)"; done
zsh -ic 'env' 2>/dev/null | grep -oE '^(PI_DISTILL_[A-Z_]+|PI_EXTENSIONS_LOCALE|MAAS_ANTHROPIC_TOKEN)=' | sort
pi list | grep -E 'pi-mcp-adapter|context7-pi|pi-distill|tool-display|i18n'
jq -r '.dependencies | keys[]' ~/.pi/agent/npm/package.json | grep -E 'pi-mcp-adapter|context7-pi|pi-distill|tool-display|i18n'
jq -c '.extensions' ~/.pi/agent/settings.json
jq -r '.providers | keys | join(",")' ~/.pi/agent/models.json
for l in pigo pigs pixg; do printf '%s tui=%s\n' "$l" "$(PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 "$l" --tui-mode fullscreen | grep -c -- '--tui-mode')"; done
zsh -ic 'alias ccd ccdo ccds; whence -w ccdd ccddg ccdu claude-deepinfra claude-deepinfra-glm claude-opencode-union ccda claude-alibaba' </dev/null 2>&1
claude plugin list | grep -oE '❯ [^ ]+' | sort -u
```

Expected（移植前の `main` から作られた現行コンテナの場合）: mount は `14`、`.dsh`・`.grok` が出る。`dsh=yes`・`grok=no`・`pnpm=yes`。`MAAS_ANTHROPIC_TOKEN`・`PI_DISTILL_*` の 3 つ・`PI_EXTENSIONS_LOCALE` が出る。`npm:@upstash/context7-pi` が `pi list` と npm マニフェストに出る。`extensions` は `[]`。provider は `commandcode,deepinfra,deepinfra-distill,opencode-go`。`--tui-mode` の数は各 `1`（利用者の引数の分だけ）。alias は `ccd` だけで、`ccda`・`claude-alibaba` は function。5 つのプラグインがある。比較表の「rebuild 前」の列と一致しない値があれば、その列を実際の値に直す。R-6 の cleanup の再実行と R-8 の setup は利用者の設定を変えるので実行しない

- [ ] **Step 9: コミットする**

```bash
git add docs/maatlog-poc-porting.md
git commit -m "docs: add the maatlog-poc porting table and rebuild checklist

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: `.devcontainer/README.md` の整合

**Files:**
- Modify: `.devcontainer/README.md`（「秘密情報」の変数の例、「秘密情報」の次に「既存環境の更新」を新設、「API トークン」の本文、PR #33 のレビュー修正で「Superpowers スキルの探索パス」配下の同名の `#####` の見出しを「pi-superagents の版の更新」に改名）
- Test: `$S/check_readme_integration.bash`（一時）、`.devcontainer/test-readme.bash`、`tests/scripts/test-docs.bash`

**Interfaces:**
- Consumes: 既存の節の見出し（「pi の旧拡張・MCP 設定の移行」「pi の TUI モードと Herdr のスクロール履歴」「Claude Code の起動と更新」「pi-superagents のランチャー別 model tier」「組み込み MCP と廃止した拡張」「エージェント向けツールの導入」「API トークン」）。見出しは変えない
- Produces: `## 既存環境の更新`。Task 3 のルートの `README.md` は「API トークン」と「組み込み MCP と廃止した拡張」を参照する

- [ ] **Step 1: 受け入れ検査のスクリプトを書く**

`$S/check_readme_integration.bash` を次の内容で作る（Task 3 でも使う）。

~~~~bash
#!/usr/bin/env bash
# Issue #22 の README の整合を確かめる一時の受け入れ検査。
# 使い方: bash check_readme_integration.bash <repo-root> devcontainer|root
set -euo pipefail
root="$1"
target="$2"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
section() { sed -n "/^$2\$/,/^#\\{2,3\\} /p" "$1" | sed '1d;$d'; }

case "$target" in
devcontainer)
  f="$root/.devcontainer/README.md"
  grep -qxF '## 既存環境の更新' "$f" || fail 'no ## 既存環境の更新'
  # 「秘密情報」の次に置く
  [ "$(grep -E '^## ' "$f" | grep -A1 -xF '## 秘密情報' | tail -n 1)" = '## 既存環境の更新' ] || fail '既存環境の更新 must follow 秘密情報'
  update="$(section "$f" '## 既存環境の更新')"
  for s in 'origin/main' '~/.config/create-reso-world/env' 'MAAS_ANTHROPIC_TOKEN' 'GOOGLE_DEV_KNOWLEDGE_API_KEY' \
    'Rebuild Container' '--tui-mode regular' 'zsh .devcontainer/setup_pi_superagents.zsh' 'project trust' \
    'deepinfra-distill' 'uv run --no-project .devcontainer/cleanup_pi_mcp.py' 'ルートの `README.md` の「対象外」'; do
    grep -qF -- "$s" <<<"$update" || fail "既存環境の更新 lacks: $s"
  done
  secrets="$(section "$f" '## 秘密情報')"
  grep -qF 'GOOGLE_DEV_KNOWLEDGE_API_KEY' <<<"$secrets" || fail '秘密情報 lacks GOOGLE_DEV_KNOWLEDGE_API_KEY'
  tokens="$(section "$f" '### API トークン')"
  for s in '`pigs`・`pixg` の OpenCode Go の tier' 'OPENCODE_GO_API_KEY` は旧名' 'OPENCODE_GO_CLAUDE_API_KEY' \
    '`ccdd`・`ccddg`' 'GOOGLE_DEV_KNOWLEDGE_API_KEY' '`.mcp.json`' 'CONTEXT7_API_KEY' 'COMMANDCODE_API_KEY'; do
    grep -qF -- "$s" <<<"$tokens" || fail "API トークン lacks: $s"
  done
  ;;
root)
  f="$root/README.md"
  grep -qF '統合手順、maatlog-poc からの移植の記録' "$f" || fail '構成 lacks the porting record'
  grep -qF -- '- pi: プロジェクトを信頼（trust）すると、`.pi/settings.json`' "$f" || fail 'no pi trust bullet'
  grep -qF '`docs/maatlog-poc-porting.md` の「rebuild での確認」' "$f" || fail '対象外 lacks the porting record'
  [ -f "$root/docs/maatlog-poc-porting.md" ] || fail 'docs/maatlog-poc-porting.md is missing'
  grep -qxF '## rebuild での確認' "$root/docs/maatlog-poc-porting.md" || fail 'porting record lacks ## rebuild での確認'
  ;;
*) fail "unknown target: $target" ;;
esac
printf 'PASS: %s README integration\n' "$target"
~~~~

- [ ] **Step 2: 変更前に失敗することを確かめる**

Run: `bash "$S/check_readme_integration.bash" "$W" devcontainer; echo "exit=$?"`
Expected: `FAIL: no ## 既存環境の更新`、`exit=1`

- [ ] **Step 3: パッチを当てる**

次のパッチを `$S/patch-devcontainer-readme.diff` に保存し、`git apply --index "$S/patch-devcontainer-readme.diff"` で当てる。

~~~~diff
diff --git a/.devcontainer/README.md b/.devcontainer/README.md
index 18ed593..304d9c4 100644
--- a/.devcontainer/README.md
+++ b/.devcontainer/README.md
@@ -53,12 +53,50 @@ touch ~/.config/create-reso-world/env && chmod 600 ~/.config/create-reso-world/e
 ```
 
 書式は `KEY=VALUE` の 1 行 1 変数である（zsh が読むので、空白や記号を含む値は引用符で囲む）。
-対象は `DEEPINFRA_TOKEN`、`COMMANDCODE_API_KEY`、`OPENCODE_API_KEY`、`CONTEXT7_API_KEY` などで、
-書き換えたら新しいシェルを開く。
+対象は `DEEPINFRA_TOKEN`、`COMMANDCODE_API_KEY`、`OPENCODE_API_KEY`、`CONTEXT7_API_KEY`、
+`GOOGLE_DEV_KNOWLEDGE_API_KEY` などで、書き換えたら新しいシェルを開く。
+変数ごとの用途と、無いときの挙動は「API トークン」の節にある。
 
 撤去した `ccda` が使っていた `MAAS_ANTHROPIC_TOKEN` は、もう使わない。`env` に残っていれば削除する。
 プロバイダ切替ランチャー（`ccdd` など）はこの変数を子プロセスから外さないため、残すと子プロセスにも渡る。
 
+## 既存環境の更新
+
+2026-10 に pi と Claude Code の設定を取り込み、pi のランチャー・拡張・MCP、Claude Code のランチャー、
+除外したツール（dsh・Grok Build・`ccda`）の扱いが変わった。既存の環境には次の順に反映する。
+
+1. ホストの作業ツリーを最新の `origin/main` に追従させる。rebuild は作業ツリーの `.devcontainer/` を使う。
+2. ホストの `~/.config/create-reso-world/env` を見直す。`MAAS_ANTHROPIC_TOKEN` を削除し、
+   Google Developer Knowledge の MCP を使う場合は `GOOGLE_DEV_KNOWLEDGE_API_KEY` を足す（「API トークン」）。
+3. Dev Containers: Rebuild Container を実行する。postCreate が次を行う。
+   - pi の旧拡張の撤去と、settings の `-builtin:mcp` の除去。変更が必要なときだけバックアップを作る
+     （「pi の旧拡張・MCP 設定の移行」）
+   - 9 本の pi ランチャーと共通ヘルパの配置。ヘルパは pi を `--tui-mode regular` で起動する
+     （「pi の TUI モードと Herdr のスクロール履歴」）
+   - Claude Code の alias（`ccd`・`ccdo`・`ccds`）とプロバイダ関数を含むシェル設定の配置
+     （「Claude Code の起動と更新」）
+   - dsh と Grok Build を導入せず、mount もしない。`PI_DISTILL_*` と `PI_EXTENSIONS_LOCALE` を export しない
+4. rebuild では変わらないものを反映する。
+   - ランチャー別の tier: `--if-absent` を付けずに `zsh .devcontainer/setup_pi_superagents.zsh` を実行する。
+     変更のある設定はバックアップされる（「pi-superagents のランチャー別 model tier」）
+   - pi の project trust: まだ承認していなければ、リポジトリのルートで素の `pi` を起動して承認する。
+     承認の後に `.pi/settings.json`・`.pi/mcp.json`・`.pi/APPEND_SYSTEM.md`（pi 固有の指示）と
+     プロジェクトのスキル（`.agents/skills`）が読まれる
+     （「組み込み MCP と廃止した拡張」）
+   - `~/.pi/agent/models.json` に残る `deepinfra-distill` は自動では消さない。不要なら定義を確かめてから削除する
+5. 確かめる項目と、rebuild 前の状態の記録は、ルートの `README.md` の「対象外」が案内する移植の記録にある。
+
+rebuild しない場合は、3 の代わりに次を行う。dsh は rebuild するまでコンテナに残る。
+
+- pi の旧拡張の撤去: 「pi の旧拡張・MCP 設定の移行」の `uv run --no-project .devcontainer/cleanup_pi_mcp.py`
+- 廃止した環境変数: 「組み込み MCP と廃止した拡張」の `unset` と、`~/.zshrc` の export 行の削除。
+  2 で `env` から消した `MAAS_ANTHROPIC_TOKEN` も、使用中のシェルでは `unset MAAS_ANTHROPIC_TOKEN` で外す
+- pi のランチャーと共通ヘルパ: 「エージェント向けツールの導入」の 9〜17 の `install -m 0755` で 9 本を置き直す。
+  同じ節の 8 の `models.json` のコピーは既存の定義を上書きするので行わない。共通ヘルパは、4 で実行する
+  `zsh .devcontainer/setup_pi_superagents.zsh` が更新する
+- Claude Code のランチャー: 「Claude Code の起動と更新」の `~/.zshrc` への反映。古い `~/.zshrc` に残る
+  `ccda`（`claude-alibaba`）の関数と、`update()` の Grok Build の行も削除する
+
 ## テストの実行
 
 リポジトリのルートで次を実行する。CI（`.github/workflows/ci.yml`）も同じコマンドを実行する。
@@ -526,21 +564,35 @@ commandcode の 2 つのランチャを `setup_pi_commandcode_goat.zsh` が同
 
 ### API トークン
 
-`OPENCODE_API_KEY`、`DEEPINFRA_TOKEN`、`COMMANDCODE_API_KEY` は、「秘密情報」の節の
-`~/.config/create-reso-world/env` に書けばシェルの起動時に export される。書かない場合は、
-必要なときに手動で export する。
+次の変数は、「秘密情報」の節の `~/.config/create-reso-world/env` に書けばシェルの起動時に
+export される。書かない場合は、必要なときに手動で export する。
 
-- `OPENCODE_API_KEY` は `pigo`・`pigod`・`pigou` の実行には不要である。bind mount した
-  `auth.json` に資格情報が残るため、pi はそこから読む
+- `OPENCODE_API_KEY` は `pigo`・`pigod`・`pigou` と、`pigs`・`pixg` の OpenCode Go の tier の
+  子 Pi の実行には不要である。bind mount した `auth.json` に資格情報が残るため、pi はそこから読む
   （`pi auth check --provider opencode-go` が `ready` を返す）。
-  `setup_pi_opencode_go.zsh` でキーを更新するときだけ必要になる
+  `setup_pi_opencode_go.zsh` でキーを更新するときと、`auth.json` に資格情報が無い環境で
+  pi の OpenCode Go を使うときに必要になる
+- `OPENCODE_GO_API_KEY` は旧名である。OpenCode Go を使う `pigo`・`pigod`・`pigou`・`pigs`・`pixg` は、
+  `OPENCODE_API_KEY` が空のときだけこの値を `OPENCODE_API_KEY` に引き継いでから起動する
+- `ccdu`（Claude Code で OpenCode Go を使う）は `auth.json` を読まない。
+  `OPENCODE_GO_CLAUDE_API_KEY`、`OPENCODE_API_KEY`、`OPENCODE_GO_API_KEY` の順に
+  最初の空でない値を使い、どれも無ければ起動を止める
 - `DEEPINFRA_TOKEN` は `models.json` の `apiKey` が `$DEEPINFRA_TOKEN` を
-  参照するため、deepinfra を使うシェルで export しておく必要がある。
+  参照するため、pi で deepinfra を使うシェルで export しておく必要がある。
+  Claude Code の `ccdd`・`ccddg`（通常名は `claude-deepinfra`・`claude-deepinfra-glm`）も
+  この変数を使い、無ければ起動を止める
 - `COMMANDCODE_API_KEY` は `DEEPINFRA_TOKEN` と同じ方式である。`models.json`
   の `apiKey` が `$COMMANDCODE_API_KEY` を参照するため、`piccg` と `piccd` を
   使うシェルで export しておく必要がある。未設定のまま実行すると
   ランチャがエラーメッセージを出して終了する。キーは
   `https://commandcode.ai/settings/keys` で作成する
+- `GOOGLE_DEV_KNOWLEDGE_API_KEY` は Google Developer Knowledge の MCP サーバーが使う。
+  pi は `.pi/mcp.json`、Claude Code は `.mcp.json` のヘッダーでこの変数を参照する。
+  無い場合の pi の挙動は「組み込み MCP と廃止した拡張」にある
+- `CONTEXT7_API_KEY` は `.codex/config.toml` の `env_vars` で Codex の Context7 の MCP サーバー
+  （`context7_stdio`）に渡す。未設定のまま `cod` を起動すると、入力を求める。
+  共有の `find-docs` スキルが使う Context7 の CLI と、Claude Code（`.mcp.json`）・Cursor（`.cursor/mcp.json`）の
+  Context7 の MCP サーバー（`@upstash/context7-mcp`）も、受け取った環境にこの変数があれば使う。無くても動くが、レート制限が低くなる
 
 ### pi の TUI モードと Herdr のスクロール履歴
 
@@ -620,7 +672,7 @@ pi-superagents v1.14.3 以降は、git で導入したパッケージの `packag
 [upstream の修正 #72](https://github.com/teelicht/pi-superagents/pull/72) は
 [v1.14.3](https://github.com/teelicht/pi-superagents/releases/tag/v1.14.3) に含まれる。
 
-##### 既存環境の更新
+##### pi-superagents の版の更新
 
 古い環境では、回避設定を整理する前に pi-superagents を v1.14.3 以降へ更新する。
 `pi --version` は Pi 本体の版なので、拡張の版は別に確認する。
~~~~

- [ ] **Step 4: 書いた内容を実装と照合する**

```bash
sed -n '30,35p' .devcontainer/pigs .devcontainer/pixg
grep -n 'OPENCODE_GO_CLAUDE_API_KEY:-\|DEEPINFRA_TOKEN:?' .devcontainer/zshrc.txt
jq -c '.mcpServers["google-dev-knowledge"].headers' .mcp.json .pi/mcp.json
grep -n 'env_vars' .codex/config.toml
grep -n -A3 '^function cod' .devcontainer/zshrc.txt
```

Expected: `pigs`・`pixg` は `OPENCODE_API_KEY` が空で `OPENCODE_GO_API_KEY` があるときだけ `export OPENCODE_API_KEY="${OPENCODE_GO_API_KEY}"` を行う。`ccdu` は `OPENCODE_GO_CLAUDE_API_KEY`→`OPENCODE_API_KEY`→`OPENCODE_GO_API_KEY` の `:-` の連鎖と最後の `:?`、`ccdd`・`ccddg` は `DEEPINFRA_TOKEN:?`。2 つの MCP 設定はどちらも `{"X-Goog-Api-Key":"${GOOGLE_DEV_KNOWLEDGE_API_KEY}"}`。`.codex/config.toml` は `env_vars = ["CONTEXT7_API_KEY"]`、`cod` は未設定なら `read -rs` で入力を求める。README の記述と違えば README を直す

- [ ] **Step 5: 受け入れ検査を通す**

Run: `bash "$S/check_readme_integration.bash" "$W" devcontainer; echo "exit=$?"`
Expected: `PASS: devcontainer README integration`、`exit=0`

- [ ] **Step 6: README の既存のテストを通す**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-readme.bash tests/scripts/test-docs.bash`
Expected: `PASS: 2 test(s)`

- [ ] **Step 7: コミットする**

```bash
git commit -m "docs(devcontainer): consolidate the existing-environment update and API tokens

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: ルートの `README.md` の整合

**Files:**
- Modify: `README.md`（「構成」の `docs/` の行、「エージェントで作業する」の pi の項目、「対象外」の 2 行目）
- Test: `$S/check_readme_integration.bash`（Task 2 で作成）、`$S/check_section_refs.py`（一時）、`tests/scripts/test-docs.bash`

**Interfaces:**
- Consumes: Task 1 の `docs/maatlog-poc-porting.md` の `## rebuild での確認`、Task 2 の `.devcontainer/README.md` の「API トークン」「組み込み MCP と廃止した拡張」
- Produces: なし（最終の文書）

- [ ] **Step 1: 変更前に失敗することを確かめる**

Run: `bash "$S/check_readme_integration.bash" "$W" root; echo "exit=$?"`
Expected: `FAIL: 構成 lacks the porting record`、`exit=1`

- [ ] **Step 2: パッチを当てる**

次のパッチを `$S/patch-root-readme.diff` に保存し、`git apply --index "$S/patch-root-readme.diff"` で当てる。

~~~~diff
diff --git a/README.md b/README.md
index c6faaf1..8fdcb9f 100644
--- a/README.md
+++ b/README.md
@@ -13,7 +13,7 @@
 ├── .devcontainer/             Dev Container の設定、導入スクリプト、テスト（詳細は .devcontainer/README.md）
 ├── scripts/                   new-world.sh（プロジェクトの作成）、resoloop-fork.sh（fork の運用）、check-layout.sh（レイアウト検査）
 ├── templates/world-project/   プロジェクトの雛形
-├── docs/                      設計と計画（docs/superpowers/）、fork の運用、統合手順
+├── docs/                      設計と計画（docs/superpowers/）、fork の運用、統合手順、maatlog-poc からの移植の記録
 ├── tests/                     スクリプトのテスト（tests/scripts/）とスキルのテスト（tests/skills/）
 └── MyResoniteProject/ akichi/ slum02/   ワールドのプロジェクト（resoloop のプロジェクト）
 ```
@@ -48,6 +48,9 @@
 - cursor-agent: `.cursor/mcp.json` の MCP サーバーは、初回に承認を求められる。
 - Devin: `.claude/skills` の symlink 経由で同じスキルが見えても、一覧には 1 回だけ表示される（`.devin/config.json` は置かない）。
 - Cursor: スキルの一部が見えない。詳細は `.devcontainer/README.md` の「エージェントの読み込みの制約」。
+- pi: プロジェクトを信頼（trust）すると、`.pi/settings.json`（組み込み MCP の有効化）と `.pi/mcp.json`（Google Developer Knowledge の
+  MCP サーバー）が読まれる。ワールドは `.pi -> ../.pi` から同じ設定を読む。キーと挙動は `.devcontainer/README.md` の「API トークン」と
+  「組み込み MCP と廃止した拡張」にある。
 - pi-superagents: 組み込みと同じ定義（`sp-*.md`）は追跡しない。独自に変えた `.agents/sp-implementer.md` だけを追跡する。
 
 ## プロジェクトを作る
@@ -85,4 +88,5 @@ uv run pytest tests/skills .agents/skills  # スキルのテスト
 ## 対象外
 
 リポジトリの公開と LICENSE の選定、Git LFS、flux-sdk の導入、Rebuild を伴う確認の自動化は対象外である。
-Rebuild 後の確認は、ユーザが `docs/integration.md` の手順で行う。
+Rebuild 後の確認は、ユーザが `docs/integration.md` の手順で行う。maatlog-poc からの pi と Claude Code の設定の移植（Issue #17）で
+確かめる項目と記録は、`docs/maatlog-poc-porting.md` の「rebuild での確認」にある。
~~~~

- [ ] **Step 3: 受け入れ検査を通す**

Run: `bash "$S/check_readme_integration.bash" "$W" root; echo "exit=$?"`
Expected: `PASS: root README integration`、`exit=0`

- [ ] **Step 4: 節名の参照の検査スクリプトを書く**

`$S/check_section_refs.py` を次の内容で作る。

~~~~python
"""README と比較表の「節名」の参照が、参照先の見出しとして実在するかを確かめる（Issue #22 の一時スクリプト）。

使い方: uv run --no-project check_section_refs.py <repo-root>
対象は変更した 2 つの README（比較表は移植元の節名や列名を引用するので対象にしない）。
参照先は、参照の直前に現れたファイル名（同じ行、無ければ前の 2 行）のファイル、無ければ同じファイルとする。
"""
import re
import sys
from pathlib import Path

FILES = ["README.md", ".devcontainer/README.md"]
TARGETS = {
    "`.devcontainer/README.md`": ".devcontainer/README.md",
    "`docs/maatlog-poc-porting.md`": "docs/maatlog-poc-porting.md",
    "`docs/integration.md`": "docs/integration.md",
    "ルートの `README.md`": "README.md",
}


def headings(path):
    return {m.group(1).strip() for m in re.finditer(r"^#{2,6} (.+)$", path.read_text(encoding="utf-8"), re.M)}


def main(root):
    root = Path(root)
    errors, checked = [], 0
    for name in FILES:
        lines = (root / name).read_text(encoding="utf-8").splitlines()
        for no, line in enumerate(lines, 1):
            refs = re.findall(r"「([^」]+)」", line)
            if not refs:
                continue
            for m in re.finditer(r"「([^」]+)」", line):
                ref = m.group(1)
                context = " ".join(lines[max(0, no - 3):no - 1]) + " " + line[:m.start()]
                target, best = name, -1
                for marker, path in TARGETS.items():
                    pos = context.rfind(marker)
                    if pos > best:
                        target, best = path, pos
                heads = headings(root / target)
                checked += 1
                if ref not in heads and f"`{ref}`" not in heads:
                    errors.append(f"{name}:{no}: 「{ref}」 is not a heading of {target}")
    print(f"checked refs: {checked}")
    for e in errors:
        print("ERROR", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
~~~~

- [ ] **Step 5: 節名の参照を検査する**

Run: `uv run --no-project "$S/check_section_refs.py" "$W"; echo "exit=$?"`
Expected: `checked refs: 22`、`exit=0`。続けて、参照を 1 つ壊したコピーで検出することを確かめる。

```bash
B="$S/brk"
mkdir -p "$B/.devcontainer" "$B/docs"
sed 's/「API トークン」と$/「API トークンX」と/' README.md > "$B/README.md"
cp .devcontainer/README.md "$B/.devcontainer/README.md"
cp docs/maatlog-poc-porting.md docs/integration.md "$B/docs/"
uv run --no-project "$S/check_section_refs.py" "$B"; echo "exit=$?"
```

Expected: `ERROR README.md:52: 「API トークンX」 is not a heading of .devcontainer/README.md`、`exit=1`

- [ ] **Step 6: テストを通す**

Run: `bash .devcontainer/run-tests.bash tests/scripts/test-docs.bash .devcontainer/test-readme.bash`
Expected: `PASS: 2 test(s)`

- [ ] **Step 7: コミットする**

```bash
git commit -m "docs: point the root README at the porting record and pi trust

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: 全体の検証と PR

**Files:**
- なし（検証と公開）。結果が比較表の記述と食い違ったときだけ `docs/maatlog-poc-porting.md` を直す

**Interfaces:**
- Consumes: Task 1〜3 のコミット
- Produces: `main` 向けの PR（`Closes #22`）

- [ ] **Step 1: テスト一式を実行する**

```bash
bash scripts/check-layout.sh; echo "EXIT=$?"
bash .devcontainer/run-tests.bash; echo "EXIT=$?"
uv run pytest -q tests/skills .agents/skills; echo "EXIT=$?"
```

Expected: `PASS: check-layout`、`PASS: 27 test(s)`、`516 passed, 1 skipped`、いずれも `EXIT=0`（`01affb7` の基準と同じ）

- [ ] **Step 2: ワールドの読み込みを静的に確かめる**

```bash
for d in MyResoniteProject akichi slum02 slum03; do
  printf '%s pi=%s settings=%s claude=%s mcp=%s\n' "$d" "$(readlink "$d/.pi")" \
    "$(readlink "$d/.claude/settings.json")" "$(head -n 1 "$d/CLAUDE.md")" \
    "$(jq -r '.mcpServers | keys | join(",")' "$d/.pi/mcp.json")"
done
head -n 1 CLAUDE.md
```

Expected: 4 つのワールドとも `pi=../.pi settings=../../.claude/settings.json claude=@AGENTS.md mcp=google-dev-knowledge`。ルートの `CLAUDE.md` の 1 行目は `@AGENTS.md`

- [ ] **Step 3: 変更の範囲を確かめる**

Run: `git diff --stat origin/main`
Expected: `.devcontainer/README.md`、`README.md`、`docs/maatlog-poc-porting.md`、Spec、Plan の 5 ファイルだけ

- [ ] **Step 4: push して PR を作る**

```bash
git push -u origin feat/issue-22-integration
gh pr create --base main --head feat/issue-22-integration \
  --title "docs: maatlog-poc 移植の比較表・README の整合・rebuild の確認項目（#22）" \
  --body-file "$S/pr-body.md"
```

`$S/pr-body.md` は次の項目で書く: 概要（3 ファイルの変更）、`Closes #22`、マージの条件（利用者が `origin/main` で rebuild し、`docs/maatlog-poc-porting.md` の「rebuild 後」の列に結果を記録してからマージする。記録の前にマージすると #22 が閉じる）、判断（Spec の D-1〜D-14 の要点）、検証の結果（Step 1〜3 と Task 1〜3 の検査）、未検証（rebuild、実認証のスモークテスト、実 CLI での trust の後の読み込み）、GitHub Actions が無効なので CI のチェックが付かないこと、Spec と Plan のパス。末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)` を付ける

- [ ] **Step 5: PR を確かめる**

Run: `gh pr view --json number,state,headRefOid,body -q '"\(.number) \(.state) \(.headRefOid)"'`
Expected: `OPEN` で、`headRefOid` がローカルの `git rev-parse HEAD` と一致し、本文に `Closes #22` がある

## 実行後の報告（Plan の範囲外の運用）

- #22 に作業報告（planning / implementation の状態、PR、コミット、検証の結果、所要時間と内訳、未検証の項目、rebuild の記録の依頼）を書く
- 予約 `refs/heads/agent-claims/issue-22` を、保存した SHA の lease 付きで削除し、ref が無いことを確かめる
- 親 #17 の実行ボードは調整役が更新する。この Plan の実行者は #22 にだけ書く

## 実行時の変更（2026-10-05）

Task 4 の Step 1 で、全体の pytest の `tests/skills/test_legacy_references.py::test_tracked_files_do_not_refer_to_the_migration_source` が失敗した（比較表の 17 か所とルートの `README.md` の 3 か所）。このガードは、設計記録（`docs/superpowers`）などを除く追跡ファイルに移植元の名前・`public/`・`verify-devenv` などを禁じる。計画の検証では `run-tests.bash` と README のテストだけを試作で実行し、pytest を実行していなかったため見落とした。

Spec の D-15 として次のように直した（コミット `9ebeb29`）。上の Task 3 のパッチと、Task 2・3 の一時の検査スクリプトに埋め込んだ README の期待値は、この変更の前の版である。

- `tests/skills/test_legacy_references.py` の `EXCLUDED` に `docs/maatlog-poc-porting.md` を足した（移行の記録なので、設計記録と同じ扱い）
- ルートの `README.md` の「構成」を「統合手順、pi と Claude Code の設定の移植の記録」に、「対象外」の参照を「`docs/` にある移植の比較表（Issue #22）の「rebuild での確認」」に直し、移植元の名前を書かない
- 一時の検査スクリプトの期待値を新しい文に合わせ、ルートの `README.md` に移植元の名前が無いことの検査を足した。節名の参照の検査には「移植の比較表」を比較表への目印として足した
- ガードは修正の前に失敗し（20 か所）、修正の後に通る。ルートの `README.md` に移植元の名前を足すと、引き続き失敗することを確かめた

## PR #33 のレビュー修正（2026-10-05）

PR #33 のレビューの指摘と、修正後の PR 全体の再レビューの指摘を `docs/superpowers/specs/2026-10-05-pr33-issue-22-integration-review-fixes-design.md` で選別し、比較表、`.devcontainer/README.md`、ルートの `README.md`、Issue #22 の Spec を直した。個々の修正はその Spec の F-1 以降にある。この Plan は次のように扱う。

- Task 1 の Step 4 の埋め込み文書は、最終版の `docs/maatlog-poc-porting.md` と同じ内容にした。全文の埋め込みなので機械的に揃えられ、値を表示する R-4 の旧い確認方法を Plan に残さない。Step 5 の期待値は最終版の値（`rows: 96`、`path tokens: 114`）にした。Task 1 の時点の版（91 行）はコミット `0132c84` にあり、そこからの変更は上の D-15 の行と、レビュー修正の Spec に記録した修正である
- Task 2 の Step 3 のパッチは、`01affb7` から最終版の `.devcontainer/README.md` への差分にした。Task 2 の受け入れ検査はこのパッチで通る。Task 2 の時点のパッチはコミット `4e932e8` の差分で、そこからの変更はレビュー修正の Spec に記録した修正である
- 次は計画の時点の記述のまま残す。最終の状態は次のとおり
  - Architecture と Global Constraints: 変更したファイルには D-15 のテストの例外の 1 行（`tests/skills/test_legacy_references.py`）が加わった
  - Task 3 のパッチと、Task 2・3 の一時の検査スクリプトのうちルートの `README.md` の期待値: 上の「実行時の変更」の D-15 と、レビュー修正（ルートの `README.md` の pi の項目に、trust の後に読まれるものとして `.pi/APPEND_SYSTEM.md` とプロジェクトのスキルを足した）の前の版である。実際に使った検査スクリプトの期待値（pi の項目の書き出しなど）は、最終版でも通る
  - Task 3 の Step 4 の節名の参照の検査スクリプト: 上の「実行時の変更」で「移植の比較表」の目印を足す前の版である。この版を最終版に当てると、ルートの `README.md` の 92 行の「rebuild での確認」を `docs/integration.md` の見出しとして探して失敗する。目印を足した版では、最終版でも参照は 22 件で、すべて参照先の見出しに当たる
  - Task 4 の Step 3 の変更の範囲: `origin/main` は作業中に進んだので、`git diff --stat origin/main...HEAD` で比べる。最終版の変更は `.devcontainer/README.md`・`README.md`・`docs/maatlog-poc-porting.md`・`tests/skills/test_legacy_references.py`、Issue #22 の Spec、この Plan、レビュー修正の Spec の 7 ファイルである
  - Task 4 の Step 4 の PR の本文の項目（3 ファイルの変更、D-1〜D-14）: 実際の本文は、テストの例外を含む 4 ファイルと D-1〜D-15 で書いた
  - Task 1 の Step 8 のコマンド: rebuild 前の値を取るために計画時に使ったもので、比較表の「確認のコマンド」とは、判定の方法（R-3 は `command -v pnpm` で判定する。最終版は npm の大域パッケージの有無で判定する）、出力の形（R-4・R-5・R-7・R-9・R-10）、対象（R-6 の一覧が無く、R-7 は 3 本だけ）、R-5 の `pi list` の `--no-approve` の有無が違う。rebuild 後の確認には比較表の「確認のコマンド」を使う
- Task 1 の Step 8 の R-9 のコマンドには、後から `</dev/null` を足した。herdr のペインの外の端末で `zsh -ic` を実行すると、`~/.zshrc` の末尾の `herdrstart` が herdr を前面で起動するためである（標準入力が端末でなければ起動しない）。出力は変わらない
