# create-reso-world 再設計 フェーズ 2（指示ファイルとスキル配置、プロジェクト雛形）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** プロジェクトを cwd にして起動したどのエージェントにも、共通規約・プロジェクトの AGENTS.md・共有スキル・resonite-* スキルが仕様 5.1 の表どおりに届く配置にし、3 つのワールドプロジェクトを同じ雛形に揃える。

**Architecture:** 共通規約の正本をルート `AGENTS.md`、共有スキルの正本をルート `.agents/skills/` に一本化し、Claude Code 用の `.claude/skills/<name>` はすべて相対 symlink にする。ランタイム別に分かれていたスキル本文は 1 本に統合し、ランタイム固有の手順は本文の「ランタイム別の注意」節に残す。プロジェクトは `templates/world-project/` と `scripts/new-world.sh` で雛形を適用し、`scripts/check-layout.sh` がルートとプロジェクトの配置を検査する。

**Tech Stack:** bash（`set -euo pipefail`、既存の `tests/scripts/*.bash` と同じ書き方）、git、uv / pytest / PyYAML、resoloop CLI 0.1.0-preview.14.pr1.20260925、Codex CLI 0.157.1・Devin CLI 3000.11.3・cursor-agent（到達性の実測にだけ使う）

**Spec:** `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md`（4.2・4.3 節、5 章、8.1 節、9.1 節、10 章のフェーズ 2）。前フェーズの計画は `docs/superpowers/plans/2026-09-26-redesign-phase0-1-safety-and-hygiene.md`。

## 判断事項（2026-09-26 にユーザ承認済み）

計画作成時の実測で、仕様の文面どおりに進めると不都合な点が 2 つ見つかった。本計画は下の「推奨」で書いてあり、2026-09-26 にユーザが計画全体と D-1 の推奨案を承認した（実行は新しいセッションで Subagent-driven）。

| ID | 事項 | 推奨（本計画の内容） | 代案 |
| --- | --- | --- | --- |
| D-1 | pi-superagents の定義 `MyResoniteProject/.agents/sp-*.md`（未追跡 9 件）の扱い（仕様 4.2 は全件をルートへ移して追跡） | `sp-implementer.md` の 1 件だけをルート `.agents/` に置いて追跡し、各プロジェクトから symlink する。残り 8 件はパッケージ同梱の組み込み定義（`@teelicht/pi-superagents` 1.14.4 の `agents/`）とバイト単位で同一であり、追跡すると古い版で組み込み定義を上書きし続けるため追跡しない。`sp-implementer.md` は組み込み版と `model: balanced`（組み込みは `cheap`）の 1 行だけが違う | 仕様どおり 9 件すべてを追跡し、各プロジェクトに 9 本の symlink を置く |
| D-2 | 仕様 10 章はスキル本文の統合（8.1）をフェーズ 5 に置いているが、フェーズ 2 の `.claude/skills` の symlink 化は統合なしにはできない | 8.1（配置と、ランタイム別に分かれた本文の統合）をフェーズ 2 で行い、8.2（maatlog 由来の記述の書き直し）はフェーズ 5 に残す。前回の引き継ぎ書（next_work）もこの範囲を指定している | なし（統合しないと `.claude` 版の内容が失われる） |

仕様 10 章のフェーズ 2 の完了条件「check-layout 全項目」は、9.1 節の検査のうちフェーズ 2 で成立するもの（ルートのスキル配置、各プロジェクトの標準レイアウト、`resoloop skills sync --check`、追跡禁止ファイル）とする。ロックファイルの検査はフェーズ 3、マウントの検査はフェーズ 4 で足す（持ち越し N-7・N-8）。

実測で仕様の想定が当たらなかったため、仕様の条件どおり作らないものが 1 つある。

- `.devin/config.json`: 仕様 5.5 は「Devin が `.claude/skills` の symlink 経由で同名スキルを二重掲示する場合は」Claude 互換読込を無効化するとしている。複製リポジトリで `.claude/skills/<name>` を `.agents/skills/<name>` への symlink にして `devin skills list` を実行したところ、同じ実体は 1 回しか表示されなかった。条件が成立しないので作らない。なお `read_config_from.claude=false` はスキルだけでなく CLAUDE.md・`.mcp.json`・`~/.claude` 配下の取り込みもまとめて止める。

## Global Constraints

- 変数: `M=/workspaces/reso-world`（メイン作業ツリー、ブランチ feat/slum02-slum、別セッションが slum02 を編集中）、`W=/workspaces/reso-world/.worktrees/repo-redesign`（作業用 worktree、ブランチ chore/repo-redesign）。各ステップのコマンドは `export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign` を実行してから、特記が無ければ `cd "$W"` で実行する。
- メイン作業ツリー `$M` では読み取りだけを行う。追跡ファイルの編集、`git add` / `commit` / `checkout` / `stash` / `reset` / `clean`、ファイルの移動・削除をしない。Task 11 と Task 13 の読み取り（`cmp`、`diff`、`git ls-files`、`git ls-tree`）は許可する。
- 変更のコミットはすべて `$W` で行う。コミットメッセージの末尾に、コミットするエージェント自身のモデル名の trailer を付ける（例: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`）。
- `git add` には明示したパスだけを渡す。`$W` で `git add -A` / `git add .` を使わない（テストが作る一時リポジトリの中は除く）。
- `git push --force` 系を使わない。push は Task 14 で controller が `git push origin chore/repo-redesign`（fast-forward を確認してから）だけ行う。`main`・`feat/*`・`wip/*` を push・rebase・削除しない。PR を開かない。
- Python は uv で実行する（`uv run ...`、`uv run --no-project ...`）。`python3` を直接呼ばない。
- 説明・文書・コミットの日本語で「契約」「原子的」「製品」「着地」を使わない（ルール本文を引用する `AGENTS.md` の「日本語表現」節を除く）。
- 触らないもの: TRPG 本文（`private/trpg/`、`tmp/` の `ATS.txt`・`BTD.txt`・`TNX.txt`）、`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json`、`.pi/APPEND_SYSTEM.md` の `## Response Persona` 以降、`.git/info/exclude`、`.devcontainer/` 配下、`.claude/settings.json`、`.mcp.json`。
- 既存プロジェクトのディレクトリの中で `resoloop init` や `resoloop skills sync --update` を実行しない（`content/main.json` の生成やスキルの上書きを避ける）。`resoloop init` は一時ディレクトリでだけ実行し、`resoloop skills sync` は `--check` だけ使う。
- フェーズ 2 の範囲外（持ち越し節を参照）に手を出さない。特に、統合したスキルに残る maatlog・`public/`・`verify.sh` の記述（仕様 8.2、フェーズ 5）、repository-ownership の削除（フェーズ 5）、`.cursor/rules/repository-ownership.mdc` の削除（フェーズ 5）、README（フェーズ 6）。
- スキルのテストの既知の失敗: フェーズ 2 の開始時点は `37 failed, 169 passed`。完了時点では `pi-model-name/tests/test_pi_model_name_contract.py` の 27 件と `repository-ownership/tests/test_public_release_guidance.py` の 7 件の計 34 件だけが失敗する（どちらもフェーズ 5 で扱う）。各 Task の最後に次を実行し、何も表示されないことを確認する。3 行目以降の除外は、その失敗を直す Task（Task 5、Task 6、Task 8）が終わるまでの一時的なもの。

```bash
cd "$W" && uv run pytest -q -rf 2>&1 | grep '^FAILED' \
  | grep -v -e 'pi-model-name/tests/test_pi_model_name_contract.py' \
            -e 'repository-ownership/tests/test_public_release_guidance.py' \
            -e 'test_pr_review_helpers_are_identical' \
            -e 'test_claude_helper_is_symlink_to_agents_helper' \
            -e 'test_repository_ownership.py::test_claude_skill_is_symlink_to_agents_skill' || true
```

- 既存の検査はどの Task の後も通る: `bash tests/scripts/test-gitignore.bash`、`bash tests/scripts/test-check-layout.bash`、`bash scripts/check-layout.sh`、`git ls-files -i -c --exclude-standard` が `MyResoniteProject/.resoloop/tokyo-nova/pipeline.json` の 1 行だけ。

## Review Focus

- `scripts/new-world.sh` を同じプロジェクトに 2 回適用する、または既存ファイルが雛形と食い違うプロジェクトに適用する: 2 回目は何も変えずに終了コード 0、食い違いがあれば全件を報告して何も変更せずに終了コード 1（Task 10 のケース 4・6・7・8）。
- `scripts/new-world.sh` に不正な名前（空文字、空白入り、`..`、`/` 入り、先頭が `-` や `.`）を渡す: 何も作らずに終了コード 2（Task 10 のケース 1）。
- `.claude/skills` の symlink の不足・余分・向き違い・実ディレクトリ化（ルートとプロジェクトの両方）: check-layout が FAIL で検出する（Task 8 のケース 14〜17、Task 12 のケース 28〜30）。
- スキルの統合でランタイム固有の手順が落ちる（Codex のモデル名解決、Devin・Claude Code の引数補間、Claude Code の `--temp-root /tmp` と `allowed-tools`、pi の description 長）: 各スキルの contract テストと frontmatter テストで固定する（Task 3・5・7）。
- resoloop が無い環境（フェーズ 4 の CI）と、resoloop 同梱スキルが古いプロジェクト: check-layout は前者で skip を表示して通過し、後者で FAIL を出す（Task 12 のケース 22・23）。

## 実行前の準備（controller）

- [x] 1. 計画作成時点で worktree はクリーン、HEAD は `2dfeaaf` だった。
- [x] 2. 本計画書は承認時にコミット済み（`2dfeaaf` の次のコミット）。実行開始時は `git -C "$W" status --short | wc -l` が 0 で、`git -C "$W" log -1 --format=%s` が `docs: add redesign phase 2 implementation plan` であることを確認する。
- [ ] 3. SDD の作業ディレクトリと台帳を作る（`bash <sdd-skill>/scripts/sdd-workspace <この計画のパス>`）。
- [ ] 4. フェーズ 0・1 の SDD 作業ディレクトリ `$W/.superpowers/sdd/2026-09-26-redesign-phase0-1-safety-and-hygiene/` を削除する。保留事項は本計画の「持ち越し」節に転記済み（前回の引き継ぎ書の指示）。

---

### Task 1: MyResoniteProject に pyproject.toml と uv.lock を置く（FR-Me）

フェーズ 1 でルートに `pyproject.toml` を置いたため、`MyResoniteProject/` で `uv run pytest` を実行するとルートの環境に解決され、`modeling` を import できずに 6 件の収集エラーになる。プロジェクト側に pyproject を置いて直す。

**Files:**
- Create: `MyResoniteProject/pyproject.toml`
- Create: `MyResoniteProject/uv.lock`（`uv lock` が生成）

**Interfaces:**
- Produces: `MyResoniteProject` の uv プロジェクト（Task 11・12 は `pyproject.toml` と `uv.lock` が追跡されていることを前提にする）

- [ ] **Step 1: 失敗を確認する**

```bash
cd "$W/MyResoniteProject" && uv run pytest -q 2>&1 | tail -n 3
```

Expected: `ModuleNotFoundError: No module named 'modeling'` による `6 errors`。

- [ ] **Step 2: pyproject.toml を書く**（akichi・slum02 と同じ形）

```toml
[project]
name = "myresoniteproject"
version = "0.1.0"
description = "Tokyo Nova world for Resonite via resoloop + Blender"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 3: ロックを作ってテストを通す**

```bash
cd "$W/MyResoniteProject" && uv lock && uv run pytest -q 2>&1 | tail -n 1
uv run python -c 'import sys; print(sys.prefix)'
```

Expected: `52 passed`。`sys.prefix` が `.../MyResoniteProject/.venv`。

- [ ] **Step 4: 共通の検査を実行してコミットする**

```bash
cd "$W" && git status --short        # ?? MyResoniteProject/pyproject.toml と ?? MyResoniteProject/uv.lock の 2 行だけ
git add MyResoniteProject/pyproject.toml MyResoniteProject/uv.lock
git commit -m "build(MyResoniteProject): add its own uv project so tests stop resolving to the root env" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 2: ルートの AGENTS.md・CLAUDE.md と .pi/APPEND_SYSTEM.md（仕様 5.2・5.3）

**Files:**
- Create: `AGENTS.md`
- Modify: `CLAUDE.md`（全面置き換え）
- Modify: `.pi/APPEND_SYSTEM.md`（`## Response Persona` より前だけ置き換え）
- Test: `tests/scripts/test-instructions.bash`（新規、実行権付き）

**Interfaces:**
- Produces: ルート `AGENTS.md`（先頭行 `# create-reso-world 共通規約`。Task 14 の Codex 実測はこの見出しを目印にする）

メイン作業ツリーの `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` には未コミットの変更がある（resoloop 注意の節、docs_draft を Markdown にする規則、Gitleaks・contingency・verify.sh の行の削除）。統合時にユーザはこれを破棄するので、ここで新しい文書に取り込む。下の本文はその取り込みを済ませたもの。

- [ ] **Step 1: 失敗するテストを書く**（`tests/scripts/test-instructions.bash`、`git add` の前に `chmod +x`）

```bash
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

# メイン作業ツリーの未コミット変更（統合時に破棄される）を取り込んでいる
for s in 'オブジェクトごとに、1つのメッシュにする' '長大なタスクであった場合は分割して実装する' 'agent-handoff' \
  '`docs_draft/` に Markdown で作成する' 'python3 を使ってよい' 'scripts/new-world.sh' \
  '.devcontainer/resoloop.lock' 'usaturn/create-reso-world' 'external/resoloop' \
  'monitoring-long-tasks' '.agents/monitoring-runtimes.md' 'find-docs' '3 回まで'; do
  has AGENTS.md "$s"
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
for s in '/skill:agent-handoff' 'async: false' 'herdr-agent-task' 'pi-model-name' 'simplify-in-subagent' 'MODEL_NAME'; do
  has .pi/APPEND_SYSTEM.md "$s"
done
# ペルソナ節（## Response Persona 以降）は 1 バイトも変えない
persona="$(sed -n '/^## Response Persona/,$p' .pi/APPEND_SYSTEM.md | sha256sum | cut -d' ' -f1)"
[ "$persona" = 906d9d2570a9662427a95609efcc29454a5f46f1591352f8b264b996895e2995 ] || fail 'persona section changed'

printf 'PASS: root instruction files follow spec 5.2 and 5.3\n'
```

- [ ] **Step 2: 失敗を確認する**

Run: `bash tests/scripts/test-instructions.bash`
Expected: `FAIL: CLAUDE.md line 1 must be @AGENTS.md`

- [ ] **Step 3: `AGENTS.md` を作る**

次の本文を使う。「日本語表現」節は現在の `CLAUDE.md` の同名節と一字一句同じ（書き写すときは `diff <(sed -n '/^## 日本語表現/,/^## ファイルとドラフト/p' CLAUDE.md) <(sed -n '/^## 日本語表現/,/^## ファイルとドラフト/p' AGENTS.md)` で出力が無いことを確かめる）。

```markdown
# create-reso-world 共通規約

このリポジトリで作業するコーディングエージェント（Claude Code、Codex、pi、Cursor、Devin、dsh）の共通規約。Claude Code 固有の注意は `CLAUDE.md`、pi 固有の注意は `.pi/APPEND_SYSTEM.md` にある。ワールドのプロジェクトでは、この規約に加えてプロジェクト直下の `AGENTS.md` が適用される。

## リポジトリ概要

[resoloop](https://github.com/orange3134/resoloop) と Blender で Resonite 上に 3D モデルやワールドを作成する開発環境。Dev Container の定義と、ワールドのプロジェクト（`MyResoniteProject/`、`akichi/`、`slum02/`）を同じリポジトリで管理する。

## 基本方針

- ユーザの指示が曖昧な場合は、作業を始める前にユーザに質問する
- 複雑なモデルを作る時や、計画や設計が必要な変更は、方針を決めてから実装する
- Python を使う時は uv 必須であり python3 コマンドを使わないこと。リポジトリ内の Python ツールも `uv` で実行する
- 例外として、Dev Container のブートストラップ（`.devcontainer/` 配下）と zsh ヘルパーは uv の導入前にも動く必要があるため、python3 を使ってよい

## resoloop 注意

- 後から人間がインスペクターで触りやすいように、オブジェクトごとに、1つのメッシュにする
- タスク開始前に、タスクの内容を確認し、長大なタスクであった場合は分割して実装する
- 長時間タスクは同一セッションを使いまわすと Context Rot が起こるので、区切りのいいところで agent-handoff スキルを使って引き継ぐ

## 日本語表現

コードレビューや説明、PR や Issue への起票では、不自然な直訳表現を避け、日本人エンジニアに一般的な表現を使うこと。

- `contract` を「契約」と訳さず、文脈に応じて「仕様」「API仕様」「インターフェース仕様」「既存の挙動」などと表現する。
- `atomic` / `atomically` を「原子的」「原子的に」と訳さず、文脈に応じて「アトミック」「一括で」「途中状態を残さず」「不可分な操作として」などと表現する。
- 単なる言い換えではなく、可能な限り具体的に何が保証されるか、何が問題になるかを説明する。
- `product` / `production` を機械的に「製品」と訳さない。「製品」「製品実装」は原則として使用せず、文脈に応じて自然な日本語に言い換えること。

  - 「製品」→「システム」「アプリケーション」「機能」「実装」「対象」など
  - 「製品実装」→「実装作業」「本実装」「機能実装」など

- 作業終了を表す際に「着地」「着地完了」は使用しない。

  - 文脈に応じて「完了」「作業完了」「対応完了」「実装完了」「修正完了」を使用する。

## ファイルとドラフト

- `docs_draft/` はローカルの下書き置き場で、git では追跡しない。タスクで指定された場合だけ読む
- ユーザから作成を依頼された文書は、`docs_draft/` に Markdown で作成する
- リポジトリに残す文書は `docs/` に置く。設計仕様は `docs/superpowers/specs/`、実装計画は `docs/superpowers/plans/` に置く

## プロジェクト運用

- ワールドの作業は、そのプロジェクトのディレクトリ（例: `slum02/`）を cwd にしてエージェントを起動する。プロジェクト固有の規約と安全ルールは、プロジェクト直下の `AGENTS.md` にある
- 新しいプロジェクトは `scripts/new-world.sh <name>` で作る。既存プロジェクトの雛形の不足分は `scripts/new-world.sh --apply <name>` で補う
- 各プロジェクトのテストは、そのプロジェクトのディレクトリで `uv run pytest` を実行する
- resoloop 同梱のスキル（`resonite-*`）が導入済みの resoloop と一致しているかは、プロジェクトのディレクトリで `resoloop skills sync --check` を実行して確かめる。更新は差分を確認してから `resoloop skills sync --update` で行う
- リポジトリ全体の配置は `scripts/check-layout.sh` で検査する

## リポジトリ境界

作業や PR の対象リポジトリごとに、作業ルートと確認事項を次のとおりとする。

| PR や作業対象の owner/repo | 作業ルート | 確認事項 |
| --- | --- | --- |
| usaturn/create-reso-world（このリポジトリの origin） | `git rev-parse --show-toplevel` | `origin` の URL が一致すること |
| usaturn/resoloop または orange3134/resoloop | `<toplevel>/external/resoloop` | `origin` が usaturn/resoloop、`upstream` が orange3134/resoloop であること。checkout が無ければ `scripts/resoloop-fork.sh clone` を案内して停止する |
| それ以外 | 推測せず停止する | — |

## ResoLoop の版管理

- 導入する ResoLoop の版は `.devcontainer/resoloop.lock` を正とする。既定は fork モードで、Blender 5 の UV 修正を含むビルドを使う
- 版を変えるときはロックファイルを明示的に更新してコミットする。`dotnet tool update` などで手元の導入だけを変えない
- fork の取得・ビルド・導入は `scripts/resoloop-fork.sh` で行い、手順は `docs/resoloop-fork-workflow.md` に従う

## エージェント運用

- 長時間コマンド、検証、バックグラウンド処理、サブエージェントの完了・生存・進捗を監視するときは monitoring-long-tasks スキルを使う。監視手順はスキルが正本であり、各ランタイムでどのツールを使うかはリポジトリルートの `.agents/monitoring-runtimes.md` を参照する（プロジェクトを cwd にしている場合も、パスはリポジトリルート基準）

### SDD 実行運用

- 実装サブエージェントはテスト、lint、回帰を同期実行し、完了を待ってからターンを終える。monitoring-long-tasks の監視ルールは controller が長時間タスクを監視するためのものであり、実装サブエージェント内部の待ちをバックグラウンド化する根拠にしない
- controller は monitoring-long-tasks の終了条件が成立するまでターンを保持し、stall ポーリングを担当する。完了通知は harness の終了コード付きプロセス終了通知を指し、成果物やサブエージェントの結果通知とは区別する。これは対象停止の判定材料であり、対象の実行中にターンを終える根拠にしない。ただし事前宣言した読み取り専用の PR レビュー委譲の期限・無進捗打ち切りに限り、停止確認不能のときは委譲対象・停止状態・残存パスを報告してターンを終えてよい
- 各担当は着手から成果提出までの所要時間と主要 Task 別の内訳を作業報告に記録する

## 環境

Windows 11 の WSL2（Gentoo Linux）上で Docker を動かし、Ubuntu 26.04 LTS の Dev Container を使用する。

## 最新ドキュメントの取得

- ライブラリ、フレームワーク、SDK、API、CLI、クラウドサービスの仕様は Context7 で確認する。手順は find-docs スキルを正本とする
- 問い合わせは 1 件につき 3 回までとする
```

`.devcontainer/resoloop.lock`、`scripts/resoloop-fork.sh`、`docs/resoloop-fork-workflow.md` はフェーズ 3、`scripts/new-world.sh` は Task 10 で作る。同じブランチでマージ前に揃うので、ここでは先に参照してよい（持ち越し N-5）。

- [ ] **Step 4: `CLAUDE.md` を置き換える**

```markdown
@AGENTS.md

## Claude Code 固有

- ユーザの指示が曖昧な場合は AskUserQuestion で確認する
- `TaskOutput(block=true)` の raw dump は読まず、途中経過は出力ファイルを必要な範囲だけ読む
- 共有スキルの正本は `.agents/skills/` にあり、Claude Code は `.claude/skills/<name>` の symlink 経由で読む。スキルを追加・改名・削除したら `.claude/skills/` の symlink も合わせ、`scripts/check-layout.sh` で確認する
- ワールドのプロジェクトでは、プロジェクトの `CLAUDE.md`（`@AGENTS.md` の 1 行）がプロジェクトの `AGENTS.md` を読み込む
```

- [ ] **Step 5: `.pi/APPEND_SYSTEM.md` の前半を置き換える**

`## Response Persona` の行とそれ以降は変えない。前半だけを次の本文にする（`{ cat 新しい前半; sed -n '/^## Response Persona/,$p' .pi/APPEND_SYSTEM.md; } > 一時ファイル` の後に移す）。前半と `## Response Persona` の間は空行 1 行にする。

```markdown
# 基本ルール

- AGENTS.md を遵守すること。プロジェクトを cwd にしている場合は、プロジェクトとリポジトリルートの両方の AGENTS.md が対象になる
- 独立した調査・検証は積極的に subagent に委譲して並列化すること
- メインコンテキストには要約結果だけを戻し、メイン Agent は設計・実装・統合判断に集中すること
- 区切りのいいところでの引き継ぎは `/skill:agent-handoff` で行うこと
- `HERDR_ENV=1` のときは、タスクに着手した直後と完了したときに
  `herdr-agent-task set "<タスク名>"` / `herdr-agent-task set "<タスク名>" --state completed`
  を実行し、Herdr 左サイドバーへ担当タスクを反映すること。
  詳細は herdr-agent-task スキル（リポジトリルートの `.agents/skills/herdr-agent-task/SKILL.md`）を参照すること

## サブエージェントの起動

- 起動前に `subagent` ツールへ `{ action: "list", capabilities: true }` を投げ、`executable` かつ `launchable` なエージェントを確認する
- 単発起動は同期実行とし、`async: false` を必ず指定する（例: `{ agent: "worker", task: "...", async: false }`）
- `async` の省略は禁止。省略時はバックグラウンド起動扱いとなる
- `async: true` のワークフロー一括起動は、この環境では使用しない。pi がスタンドアロン版で `@earendil-works/pi-server` 系が無く、child session を作成できず失敗する（2026-09-06 確認）
- 複数タスクは同期呼び出しで直列に回す。worktree を共有する場合は同時書き込みを避け、一度に書く子は1件にする
- `reviewer` に bash は無い。テスト実行の裏取りは bash 持ち（implementer / worker / delegate）にやらせるか、調整役が引き受ける。レビュー子には差分照合だけを頼む
- 予約 ref・Issue 更新・PR は調整役の一元管理とし、子には触らせない
- サブエージェントが /simplify を使いたいときは simplify-in-subagent スキルを使う

## モデル名の抽出

スキル: pr-review の `MODEL_NAME` は pi-model-name スキルの手順で決める。

1. pi の bash ツール内で `PI_PROVIDER` と `PI_MODEL` の両方を確認する。スクリプトを使う場合は、同スキルに記載された親 checkout からの絶対パス取得手順に従う。
2. 片方でも空なら停止し、ユーザに正確なモデル識別子を確認する。セッション履歴の `model_change` や `PI_DISTILL_MODEL` を正式な `MODEL_NAME` の根拠にしない。
```

- [ ] **Step 6: テストを通し、Codex での到達性を実測する**

```bash
bash tests/scripts/test-instructions.bash
out="$(mktemp)"; (cd "$W/slum02" && codex debug prompt-input "hi" > "$out" 2>/dev/null)
grep -c 'create-reso-world 共通規約' "$out"      # 1 以上（ルート AGENTS.md）
grep -c 'ResoLoop project guide' "$out"          # 1 以上（slum02/AGENTS.md）
```

Expected: `PASS: root instruction files follow spec 5.2 and 5.3`、2 つの grep がどちらも 1 以上。`codex debug prompt-input` はモデル API を呼ばずにモデルへ渡る入力を表示する（2026-09-26 に実測済み）。

- [ ] **Step 7: 共通の検査を実行してコミットする**

```bash
git add AGENTS.md CLAUDE.md .pi/APPEND_SYSTEM.md tests/scripts/test-instructions.bash
git update-index --chmod=+x tests/scripts/test-instructions.bash
git commit -m "docs: make root AGENTS.md the shared rulebook and slim CLAUDE.md and pi append" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 3: Blender 系スキルをルートの .agents/skills に移し、スキルのテストを tests/skills に置く

**Files:**
- Move: `MyResoniteProject/.agents/skills/{blender-modeler,brutalist-mood,dark-gritty-mood,geometry-nodes,hard-surface,horror-style,procedural-modeling,prop-artist,sci-fi-punk-worlds,uv-workflow,references}` → `.agents/skills/` 直下
- Move: `MyResoniteProject/.agents/skills/tests/test_skill_packages.py` → `tests/skills/test_skill_packages.py`（`SKILLS_ROOT` と docstring を修正）
- Create: `tests/skills/test_skill_frontmatter.py`

**Interfaces:**
- Produces: ルート `.agents/skills/<Blender 系 10 本>` と `.agents/skills/references/`（Task 8 が `.claude/skills` の symlink を張る）。`tests/skills/test_skill_frontmatter.py`（Task 4〜8 はこのテストを通し続ける）

frontmatter テストの根拠: pi 0.87.1 のスキル読み込み（`@earendil-works/pi-coding-agent` の `dist/core/skills.js`）は `name`・`description`（1024 文字まで）・`disable-model-invocation` だけを読み、他のキーは無視する。Codex 0.157.1 は `codex debug prompt-input` のスキル一覧で確認する（Task 14）。Claude Code は `allowed-tools` をカンマ区切りの文字列として読む。どれも計画作成時に確認済み（仕様 12 章の「`allowed-tools` を Codex と pi が無視するか」への回答）。

- [ ] **Step 1: テストを先に移して失敗させる**

```bash
mkdir -p tests/skills
git mv MyResoniteProject/.agents/skills/tests/test_skill_packages.py tests/skills/test_skill_packages.py
```

`tests/skills/test_skill_packages.py` の 2 か所を直す。

```python
"""Packaging and behavior guards for the shared Blender skills under .agents/skills.

Run with: uv run pytest tests/skills/test_skill_packages.py -q
For sequential validation, run the targeted test with SKILL_UNDER_TEST=<name>.
"""
```

```python
SKILLS_ROOT = Path(__file__).resolve().parents[2] / ".agents" / "skills"
```

Run: `uv run pytest tests/skills/test_skill_packages.py -q 2>&1 | tail -n 1`
Expected: `missing required skill` などで失敗する。

- [ ] **Step 2: frontmatter テストを書く**（`tests/skills/test_skill_frontmatter.py`）

```python
"""Frontmatter guards for every shared skill under .agents/skills (spec 8.1).

pi validates `name` and `description` against the Agent Skills spec (description up
to 1024 characters) and ignores other keys. Claude Code reads `allowed-tools` as a
comma-separated string. A merged skill that breaks either rule silently drops out of
one runtime, so every shared skill is checked here.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

SKILLS_ROOT = Path(__file__).resolve().parents[2] / ".agents" / "skills"
SKILL_FILES = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_DESCRIPTION = 1024


def frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert match, f"{path}: missing YAML frontmatter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict), f"{path}: frontmatter must be a mapping"
    return data


def test_shared_skills_are_discovered() -> None:
    assert len(SKILL_FILES) >= 10


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: p.parent.name)
def test_frontmatter_is_valid_for_every_runtime(path: Path) -> None:
    data = frontmatter(path)
    name = data.get("name")
    assert name == path.parent.name
    assert isinstance(name, str) and NAME_PATTERN.match(name) and len(name) <= 64
    description = data.get("description")
    assert isinstance(description, str) and description.strip()
    assert len(description) <= MAX_DESCRIPTION, f"{name}: description has {len(description)} characters"
    if "allowed-tools" in data:
        assert isinstance(data["allowed-tools"], str), f"{name}: allowed-tools must be a comma-separated string"


def test_every_skill_directory_has_a_skill_file() -> None:
    for directory in sorted(p for p in SKILLS_ROOT.iterdir() if p.is_dir()):
        if directory.name == "references":
            continue
        assert (directory / "SKILL.md").is_file(), directory
```

- [ ] **Step 3: スキルを移す**

```bash
for n in blender-modeler brutalist-mood dark-gritty-mood geometry-nodes hard-surface horror-style \
         procedural-modeling prop-artist sci-fi-punk-worlds uv-workflow references; do
  git mv "MyResoniteProject/.agents/skills/$n" ".agents/skills/$n"
done
find MyResoniteProject/.agents -depth -type d -empty -delete   # 移動後に残る空ディレクトリ（skills/tests など）を消す
git ls-files MyResoniteProject/.agents | wc -l      # 0
[ ! -e MyResoniteProject/.agents ] && echo 'MyResoniteProject/.agents removed'
```

空ディレクトリを残すと、Task 11 の new-world.sh より前に `.agents/skills/tests` が見えてしまう（計画作成時のシミュレーションで見つかった問題。new-world.sh 側も `SKILL.md` を持つディレクトリだけを対象にして防ぐ）。

- [ ] **Step 4: テストを通す**

```bash
uv run pytest tests/skills -q 2>&1 | tail -n 1
```

Expected: 失敗 0（`test_targeted_skill_semantics` の 1 件は `SKILL_UNDER_TEST` 未設定で skip）。`blender-skills-sources.json` の `output_paths`（`.agents/skills/...`）は `SKILLS_ROOT.parent.parent`（リポジトリルート）から解決されるので変更しない。

- [ ] **Step 5: 共通の検査（既知の失敗以外が無いこと）を実行してコミットする**

```bash
git add tests/skills/test_skill_frontmatter.py
git commit -m "refactor(skills): move Blender skills to the root .agents/skills and their tests to tests/skills" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 4: agent-handoff を 1 本に統合する（仕様 8.1）

`.agents` 版（英語、Codex・pi 向け）と `.claude` 版（日本語、Claude Code 向け）を、日本語版を軸に `.agents/skills/agent-handoff/SKILL.md` の 1 本へ統合し、`.claude/skills/agent-handoff` を symlink にする。

**Files:**
- Modify: `.agents/skills/agent-handoff/SKILL.md`
- Delete: `.claude/skills/agent-handoff/`（実ディレクトリ）→ Create: symlink `.claude/skills/agent-handoff -> ../../.agents/skills/agent-handoff`
- Modify: `.agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py`

**Interfaces:**
- Consumes: Task 3 の `tests/skills/test_skill_frontmatter.py`
- Produces: symlink の形（`../../.agents/skills/<name>`）。Task 5〜8 と Task 8 の check-layout が同じ形を前提にする

統合の規則:

| 部分 | 採用するもの |
| --- | --- |
| frontmatter | `.claude` 版の `name`・`description`・`allowed-tools` をそのまま使う |
| 見出し | `# エージェント引き継ぎ`（「（Claude Code 版）」を外す） |
| 本文（概要〜handoff を読む〜アーティファクトの作成） | `.claude` 版。ただし手順 5 の書き出し「このランタイムでは次が定番の穴になる。」を「特に Claude Code では次が定番の穴になる。他のランタイムでも、todo 機能を使わなかったセッション、シェル経由で書いたファイル、委譲した作業の根拠は同じ扱いにする。」に変える（`TodoWrite`・`heredoc`・`サブエージェント` の語は残す） |
| 検証 | 英語版の内容を日本語で書く。`<skill-creator-path>` の解決先を Codex（`~/.codex/skills/.system/skill-creator`）、Claude Code と Devin（`find ~/.claude -name quick_validate.py` で見つかるパスの 2 階層上）、pi（`quick_validate.py` が無いので `~/.pi/agent/npm/node_modules/@howaboua/pi-skill-skill-creator/skills/skill-creator/scripts/skill-efficiency-check.py` を同じ引数で実行）の 3 つとも書く。コマンドは `uv run python <skill-creator-path>/scripts/quick_validate.py .agents/skills/agent-handoff` と `uv run pytest .agents/skills/agent-handoff/tests -q` の 2 行にする（`.claude/skills/agent-handoff` は同じディレクトリなので行を消す） |
| 参照 | `references/handoff-schema.md` に加え、英語版にだけある `evals/evals.json`（両方向の挙動確認）と `evals/trigger_queries.json`（起動条件の網羅）を載せる |
| 変えないもの | `docs_draft/superpowers/` などの旧パスの記述（仕様 8.2、フェーズ 5） |

英語版の各節が統合版のどこに入ったかを、実装報告に表（英語版の節 → 統合版の節、または「日本語版に同じ内容あり」）で記録する。

- [ ] **Step 1: テストを統合後の形に直して失敗させる**

`test_agent_handoff_skill_contract.py` を次のとおり変える。

- 定数 `CLAUDE_SKILL` を削除し、`CLAUDE_LINK = REPO_ROOT / ".claude/skills/agent-handoff"` を足す。先頭に `import os` を足す。
- `test_claude_skill_states_the_handoff_contract` を削除する（統合版 1 本を下のテストで検査する）。
- 次の 4 つの関数を、同名の旧関数（`test_agents_skill_states_the_handoff_contract`、`test_claude_skill_declares_allowed_tools`、`test_claude_skill_covers_claude_code_specific_gaps`、`test_validation_quick_validates_claude_skill`）の置き換えとして書く。

```python
def test_skill_states_the_handoff_contract() -> None:
    content = read(AGENTS_SKILL)
    assert_shared_handoff_contract(content)
    assert "handoff を書く" in content
    assert "handoff を読む" in content
    assert "拘束力" in content


def test_skill_declares_claude_code_allowed_tools() -> None:
    """Claude Code gates the skill's tool surface; Codex and pi ignore the key."""
    assert "allowed-tools:" in read(AGENTS_SKILL).split("---", 2)[1]


def test_skill_covers_the_gaps_hand_written_handoffs_drop() -> None:
    content = read(AGENTS_SKILL)
    assert "TodoWrite" in content
    assert "heredoc" in content
    assert "サブエージェント" in content


def test_validation_quick_validates_the_shared_skill() -> None:
    assert "quick_validate.py .agents/skills/agent-handoff" in read(AGENTS_SKILL)


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    assert CLAUDE_LINK.is_symlink()
    assert os.readlink(CLAUDE_LINK) == "../../.agents/skills/agent-handoff"
    assert CLAUDE_LINK.resolve() == SKILL_DIR.resolve()
```

- `test_every_referenced_path_exists` の `for source in (AGENTS_SKILL, CLAUDE_SKILL, SCHEMA):` を `for source in (AGENTS_SKILL, SCHEMA):` にする。
- `test_validation_placeholder_comes_with_a_resolution` を次に置き換える。

```python
def test_validation_names_every_runtime_resolution() -> None:
    content = read(AGENTS_SKILL)
    assert "<skill-creator-path>" in content
    for hint in SKILL_CREATOR_RESOLUTIONS:
        assert hint in content
    assert "skill-efficiency-check.py" in content
```

Run: `uv run pytest .agents/skills/agent-handoff/tests -q 2>&1 | tail -n 1`
Expected: `test_skill_states_the_handoff_contract` など複数が失敗する（統合前の `.agents` 版は英語）。

- [ ] **Step 2: 統合版を書き、`.claude` 側を symlink にする**

```bash
# 上の表に従って .agents/skills/agent-handoff/SKILL.md を書き換えた後
git rm -rq .claude/skills/agent-handoff
ln -s ../../.agents/skills/agent-handoff .claude/skills/agent-handoff
git add .claude/skills/agent-handoff .agents/skills/agent-handoff
```

- [ ] **Step 3: テストを通す**

```bash
uv run pytest .agents/skills/agent-handoff/tests tests/skills -q 2>&1 | tail -n 1
```

Expected: 失敗 0（skip 1）。

- [ ] **Step 4: 共通の検査を実行してコミットする**

```bash
git commit -m "refactor(skills): merge agent-handoff into one shared skill with runtime notes" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 5: pr-review を 1 本に統合する（仕様 8.1）

3 版とも日本語で、差分はランタイム固有の記述にある。`.agents` 版（Codex と非 Codex の両方の分岐を持つ）を軸にし、`.claude` 版と `.devin` 版にしか無い記述を取り込む。

**Files:**
- Modify: `.agents/skills/pr-review/SKILL.md`
- Delete: `.claude/skills/pr-review/`、`.devin/skills/pr-review/` → Create: symlink `.claude/skills/pr-review -> ../../.agents/skills/pr-review`
- Modify: `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py`

**Interfaces:**
- Consumes: Task 4 の symlink の形
- Produces: 「ランタイム別の注意」節の形（見出し `## ランタイム別の注意`、その下に `### 対象 PR の受け取り`、`### Claude Code`、`### Codex`、`### Devin`、`### pi`）。Task 7 の simplify-in-subagent も同じ見出しを使う

統合の規則（`diff .agents/skills/pr-review/SKILL.md .claude/skills/pr-review/SKILL.md` と `.devin` 版との diff の各ハンクの扱い）:

| 箇所 | 扱い |
| --- | --- |
| frontmatter | `.agents` 版の `name`・`description` に、`.claude` 版の `allowed-tools`（そのまま）と `.devin` 版の `argument-hint: "<PR番号またはURL>"` を足す |
| 見出し・導入 | 見出しは `# GitHub PR レビュー`。導入段落の直後に空行を挟んで `対象 PR（スキル呼び出しの引数）: $ARGUMENTS` の 1 行を置く。「ヘルパーは各ランタイム版で相対 symlink を共有」という `.claude`・`.devin` 版の段落は取り込まない（実体が 1 本になったため） |
| 新しい節 | 導入の後、最初の既存の節の前に、下の「ランタイム別の注意」節を置く |
| 手順 1 の PR 指定 | `.devin` 版の 3 項目（補間値の読み取り、`PR_ARG` 確定時、未指定時）を採り、1 項目目を「対象 PR は、冒頭の `対象 PR` 行が補間済みならその値、未指定ならユーザのメッセージで指定された PR 番号・URL から読み取り、前後空白を除去して `PR_ARG` に入れる。」で始める。以降の文（`gh pr view` が解釈できる形式、URL の owner/repository）は既存のまま |
| `github_repository()` | `.devin` 版の stdin で受ける形（`sed -nE \` で始まり、呼び出しは `printf '%s\n' "$PR_URL" \| github_repository`）に置き換える。位置パラメータ `$1` を本文から無くすため |
| `HELPER=` の行 | `.agents` 版のまま（`$TOPLEVEL/.agents/skills/pr-review/scripts/pr_review_workspace.py`） |
| `create` | Codex 用と非 Codex 用の 2 つのコードブロックを残し、両方の末尾に `--temp-root /tmp` を付ける。説明文の `${TMPDIR:-/tmp}/pr-review-...` は `/tmp/pr-review-<PR_NUMBER>-<ランダム値>/worktree`（`--temp-root /tmp` で固定する。Claude Code の `allowed-tools` と一致させるため、どのランタイムでも同じにする）に変える |
| 委譲の制限 | `.claude` 版にだけある記述をすべて取り込む: 委譲先は `$WT` 上のコードと PR 差分だけを調べ `reviews/` と既存 review 本文を除外する 2 項目、`$PREVIOUS_REVIEW` の読解はメインエージェントだけが行う文、手順 5 の「条件付き早期委譲」の本文（「指摘の根拠となる精読をサブエージェント任せにしない」を含む）、手順 6 の括弧書き、再検証の最終判定はメインエージェントが行う文、反証試行の追加委譲をしない段落、チェックリストの 2 項目の追記 |
| チェックリスト | `.devin` 版の「冒頭の `対象 PR` 行から引数を読み取り、未指定判定を正しく行ったか」と、「正確な `$MODEL_NAME` を `--model-name "$MODEL_NAME"` で渡し、filename から推測していないか（Codex はヘルパーが確定する）」を足す |
| 時間予算の参照 | `.agents` 版の相対リンク `references/time-budget.md` のまま（symlink 経由でも同じディレクトリから解決される） |
| 変えないもの | maatlog・`public/`・`verify.sh` の記述（仕様 8.2、フェーズ 5） |

「ランタイム別の注意」節の本文:

```markdown
## ランタイム別の注意

このスキルの実体は `.agents/skills/pr-review/` の 1 つだけで、Claude Code は `.claude/skills/pr-review` の symlink 経由で同じファイルを読む。ヘルパーも `.agents/skills/pr-review/scripts/pr_review_workspace.py` の 1 本だけを使う。

### 対象 PR の受け取り

- 冒頭の `対象 PR` 行は、呼び出し引数を本文へ展開するランタイム（Claude Code、Devin）が埋める補間欄である。値が空欄、またはドル記号で始まるプレースホルダ表記のまま残っている場合は「未指定」とみなす
- 未指定のときは、ユーザのメッセージで PR 番号・URL が指定されていればそれを使う。どちらも無ければ手順 1 のとおり現在のブランチの PR を使う
- 引数を展開するランタイムは `＄ARGUMENTS` と `＄0`〜`＄9`（ドル記号と数字 1 文字）を呼び出し引数で置換する（この節では置換されないよう全角で書いている）。埋め込みのシェルコードに位置パラメータを書かず、入力は stdin か名前付き変数で受ける

### Claude Code

- frontmatter の `allowed-tools` は Edit と Write を `/tmp/pr-review-*/review-backup/**` に限っている。`create` には必ず `--temp-root /tmp` を渡し、ヘルパーの一時ディレクトリをこの範囲に置く
- `MODEL_NAME` は Claude Code ランタイムが提示する正確なモデル識別子を使う

### Codex

- `create` に `--model-name` を渡さない。ヘルパーが `CODEX_THREAD_ID` と Codex の session metadata からモデル名を確定する

### Devin

- `MODEL_NAME` はシステムプロンプトの `You are powered by <MODEL>` が提示する識別子を使う（例: `SWE-2 High`）
- 過去のセッションの transcript（`~/.local/share/devin/cli/transcripts/` の `agent.model_name` など）は実行中のランタイムの提示ではないため、`MODEL_NAME` の根拠にしない

### pi

- `MODEL_NAME` は pi-model-name スキルの手順で決める。セッション履歴（`~/.pi/agent/sessions` 配下）の `model_change` は根拠にしない
```

- [ ] **Step 1: テストを統合後の形に直して失敗させる**

`test_pr_review_skill_contract.py` を次のとおり変える。

- 先頭に `import os` を足す。定数 `CLAUDE_SKILL`、`DEVIN_SKILL`、`CLAUDE_HELPER`、`DEVIN_HELPER` を削除し、`CLAUDE_LINK = REPO_ROOT / ".claude/skills/pr-review"` を足す。
- `@pytest.mark.parametrize("skill", [AGENTS_SKILL, CLAUDE_SKILL, DEVIN_SKILL])` と `@pytest.mark.parametrize("skill_path", [AGENTS_SKILL, CLAUDE_SKILL, DEVIN_SKILL])` をすべて `[AGENTS_SKILL]` に、`for skill in (AGENTS_SKILL, CLAUDE_SKILL, DEVIN_SKILL):` を `for skill in (AGENTS_SKILL,):` にする。
- `test_review_budget_reference_is_required_and_resolves` のパラメータを `[(AGENTS_SKILL, "references/time-budget.md")]` だけにする。
- 次の 3 つを旧関数（`test_pr_review_helpers_are_identical`、`test_devin_skill_interpolates_only_target_line`、`test_claude_skill_allows_required_commands`）の置き換えとして書き、1 つを新しく足す。

```python
def test_helper_has_one_real_copy_shared_through_the_skill_symlink() -> None:
    assert AGENTS_HELPER.is_file() and not AGENTS_HELPER.is_symlink()
    assert AGENTS_HELPER.stat().st_size > 0
    assert CLAUDE_LINK.is_symlink()
    assert os.readlink(CLAUDE_LINK) == "../../.agents/skills/pr-review"
    assert not (REPO_ROOT / ".devin/skills").exists()


def test_skill_interpolation_is_limited_to_the_target_line() -> None:
    content = read(AGENTS_SKILL)
    # Claude Code and Devin replace $ARGUMENTS and $0-$9 in the body with the
    # invocation arguments. Only the target-PR line may carry $ARGUMENTS, and
    # embedded shell code must not use positional parameters.
    assert content.count("$ARGUMENTS") == 1
    assert "対象 PR（スキル呼び出しの引数）: $ARGUMENTS" in content
    assert re.search(r"\$[0-9]", content) is None


def test_skill_keeps_claude_code_permissions_consistent() -> None:
    content = read(AGENTS_SKILL)
    head = content.split("---", 2)[1]
    assert "allowed-tools:" in head
    assert "Bash(date *)" in head
    assert "Edit(/tmp/pr-review-*/review-backup/**)" in head
    assert 'argument-hint: "<PR番号またはURL>"' in head
    assert '--model-name "$MODEL_NAME"' in content
    assert "CODEX_THREAD_ID" in content
    create_lines = [line for line in content.splitlines() if '"$HELPER" create' in line]
    assert len(create_lines) >= 2
    for line in create_lines:
        # allowed-tools only permits Edit/Write under /tmp/pr-review-*, so every
        # runtime pins the helper's temp root there.
        assert "--temp-root /tmp" in line, line


def test_skill_keeps_runtime_specific_notes() -> None:
    content = read(AGENTS_SKILL)
    assert "## ランタイム別の注意" in content
    for heading in ("### 対象 PR の受け取り", "### Claude Code", "### Codex", "### Devin", "### pi"):
        assert heading in content
    assert "You are powered by" in content
    assert "pi-model-name" in content
```

Run: `uv run pytest .agents/skills/pr-review/tests -q 2>&1 | tail -n 1`
Expected: 新しい 4 つが失敗する（`$ARGUMENTS` や `ランタイム別の注意` がまだ無い）。

- [ ] **Step 2: 統合版を書き、`.claude`・`.devin` 側を消して symlink にする**

```bash
# 上の表に従って .agents/skills/pr-review/SKILL.md を書き換えた後
git rm -rq .claude/skills/pr-review .devin/skills/pr-review
ln -s ../../.agents/skills/pr-review .claude/skills/pr-review
git add .claude/skills/pr-review .agents/skills/pr-review
```

- [ ] **Step 3: テストを通す**

```bash
uv run pytest .agents/skills/pr-review/tests tests/skills -q 2>&1 | tail -n 1
```

Expected: 失敗 0（skip 1）。`test_pr_review_workspace.py`（ヘルパー本体のテスト）も通る。

- [ ] **Step 4: 共通の検査を実行してコミットする**（除外リストの `test_pr_review_helpers_are_identical` はこの Task 以降、該当しない）

```bash
git commit -m "refactor(skills): merge the three pr-review copies into one shared skill" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 6: review-fix-planning と repo-cleanup-after-merge を統合する（仕様 8.1）

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`、`.agents/skills/repo-cleanup-after-merge/SKILL.md`
- Delete: `.claude/skills/review-fix-planning/`、`.claude/skills/repo-cleanup-after-merge/` → Create: 2 本の symlink
- Modify: `.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`

**Interfaces:**
- Consumes: Task 4 の symlink の形

統合の規則:

- review-fix-planning: `.claude` 版（日本語）を軸にする。2 版は節の構成が同じ翻訳関係にある（英語版の `Resolving the review directory`・`Procedure`・`After implementation`・`PR status comment before finishing`・`The classification contract`・`The Spec is mandatory on every path`・`Scope`・`Rationalizations and what is actually true`・`Red flags` が、日本語版の `第1引数の解決`・`手順`・`実装後`・`作業終了前の PR 投稿`・`分類の仕様`・`Spec は経路に関わらず必須`・`スコープ`・`合理化とその実態`・`Red flags` に対応する）。節ごとに段落・箇条を突き合わせ、英語版にしか無い文だけを日本語にして対応する節へ足す。frontmatter は `.claude` 版の `name`・`description`・`allowed-tools` をそのまま使う。見出しは `.claude` 版のまま。突き合わせの結果は、実装報告に「英語版の節 → 取り込んだ文、または『日本語版に同じ内容あり』」の表で記録する。
- repo-cleanup-after-merge: `.agents` 版（`gh` が非 0 終了したときに停止する規則を持つ）を軸にする。frontmatter は `.agents` 版の `name`・`description` の末尾に、`.claude` 版の description にある依頼の例（「PR が全て Merge されたことを確認して branch, worktree を整理してローカルを更新して」から「リポジトリを整理して」まで）を「例:」として足し、`.claude` 版の `allowed-tools` をそのまま足す。ゲート B の「対象を提示してユーザー確認を求め」の後に「（Claude Code では AskUserQuestion を使う）」を足す。それ以外の `.claude` 版との差分は言い回しの違いだけなので取り込まない。
- どちらも maatlog・`public/`・`verify.sh`・`python3` の記述は変えない（仕様 8.2、フェーズ 5）。

- [ ] **Step 1: テストを統合後の形に直して失敗させる**

`test_review_fix_planning_skill_contract.py` を次のとおり変える。

- 先頭に `import os` を足す。定数 `CLAUDE_SKILL` と `CLAUDE_HELPER` を削除し、`REPO_CLEANUP_SKILLS` を `(REPO_ROOT / ".agents/skills/repo-cleanup-after-merge/SKILL.md",)` にする。
- `assert_english_landing_contract` と `assert_english_number_argument_contract` を削除する。
- `test_agents_skill_resolves_number_argument_to_reviews_dir` の本体を `assert_japanese_number_argument_contract(read(AGENTS_SKILL))` に、`test_agents_skill_lands_on_existing_pr_after_related_tests` の本体を `assert_japanese_landing_contract(read(AGENTS_SKILL))` にし、`test_claude_skill_resolves_number_argument_to_reviews_dir` と `test_claude_skill_lands_on_existing_pr_after_related_tests` を削除する。
- `for path in (AGENTS_SKILL, CLAUDE_SKILL):` をすべて `for path in (AGENTS_SKILL,):` にする。
- 次の関数を、同名または対応する旧関数（`test_claude_helper_is_symlink_to_agents_helper`、`test_pr_comment_lists_skipped_findings_without_spec_dependency`、`test_pr_posting_required_only_after_landing`、`test_pr_comment_purpose_is_record_not_stall_relief`、`test_skill_descriptions_do_not_advertise_pr_posting`）の置き換えとして書き、最後の 2 つを新しく足す。

```python
def test_helper_has_one_real_copy_shared_through_the_skill_symlinks() -> None:
    assert AGENTS_HELPER.is_file() and not AGENTS_HELPER.is_symlink()
    assert AGENTS_HELPER.stat().st_size > 0
    for name in ("review-fix-planning", "repo-cleanup-after-merge"):
        link = REPO_ROOT / ".claude/skills" / name
        assert link.is_symlink(), link
        assert os.readlink(link) == f"../../.agents/skills/{name}"


def test_pr_comment_lists_skipped_findings_without_spec_dependency() -> None:
    """Issue #235 A: no dangling reference to the gitignored Spec."""
    content = read(AGENTS_SKILL)
    assert "全件は Spec を参照" not in content
    spec_lines = [line for line in content.splitlines() if line.strip().startswith("- Spec:")]
    assert spec_lines, "the template must keep a Spec: line"
    assert any("gitignore" in line for line in spec_lines)
    assert "単体で読める" in content


def test_pr_posting_required_only_after_landing() -> None:
    """Issue #235 B: mandatory posting is limited to landing turns."""
    content = read(AGENTS_SKILL)
    assert "計画のみのセッションも投稿する" not in content
    assert "承認待ちで止まるターンは停止直前に1回" not in content
    assert "commit / push まで完了したターン" in content
    assert "任意" in content


def test_pr_comment_purpose_is_record_not_stall_relief() -> None:
    """Issue #235 C: the comment is only a durable record, not stall relief."""
    content = read(AGENTS_SKILL)
    assert "永続的な記録" in content
    assert "stall" in content.lower()
    assert "Monitor" in content


def test_skill_descriptions_do_not_advertise_pr_posting() -> None:
    """Issue #235 D: posting lives in the body section, not the description."""
    description = frontmatter_description(read(AGENTS_SKILL))
    assert "作業終了前の PR 投稿" not in description
    assert "Before finishing, post review status" not in description


def test_merged_skills_keep_claude_code_allowed_tools() -> None:
    for path in (AGENTS_SKILL, *REPO_CLEANUP_SKILLS):
        assert "allowed-tools:" in frontmatter_description(read(path)), path


def test_repo_cleanup_keeps_gh_failure_stop_and_user_confirmation() -> None:
    content = read(REPO_CLEANUP_SKILLS[0])
    assert "が非0終了した場合、PR の状態は不明である" in content
    assert "AskUserQuestion" in content
```

Run: `uv run pytest .agents/skills/review-fix-planning/tests -q 2>&1 | tail -n 1`
Expected: 日本語の文言を求めるテストと `allowed-tools` のテストが失敗する。

- [ ] **Step 2: 統合版を書き、`.claude` 側を symlink にする**

```bash
# 上の規則に従って 2 つの SKILL.md を書き換えた後
git rm -rq .claude/skills/review-fix-planning .claude/skills/repo-cleanup-after-merge
ln -s ../../.agents/skills/review-fix-planning .claude/skills/review-fix-planning
ln -s ../../.agents/skills/repo-cleanup-after-merge .claude/skills/repo-cleanup-after-merge
git add .claude/skills/review-fix-planning .claude/skills/repo-cleanup-after-merge \
        .agents/skills/review-fix-planning .agents/skills/repo-cleanup-after-merge
```

- [ ] **Step 3: テストを通す**

```bash
uv run pytest .agents/skills/review-fix-planning/tests tests/skills -q 2>&1 | tail -n 1
```

Expected: 失敗 0（skip 1）。

- [ ] **Step 4: 共通の検査を実行してコミットする**（除外リストの `test_claude_helper_is_symlink_to_agents_helper` はこの Task 以降、該当しない）

```bash
git commit -m "refactor(skills): merge review-fix-planning and repo-cleanup-after-merge into shared skills" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 7: simplify-in-subagent を統合し、rst-writer を .agents に移す（仕様 8.1）

`.devin` 版は `.agents` 版の英語本文に Devin 固有の frontmatter と節を足したもの。`.agents` 版を軸に Devin 固有の部分を取り込む。rst-writer は `.claude` にしか無いので移すだけにする。

**Files:**
- Modify: `.agents/skills/simplify-in-subagent/SKILL.md`
- Delete: `.devin/skills/simplify-in-subagent/` → Create: symlink `.claude/skills/simplify-in-subagent -> ../../.agents/skills/simplify-in-subagent`
- Move: `.claude/skills/rst-writer/` → `.agents/skills/rst-writer/` → Create: symlink `.claude/skills/rst-writer -> ../../.agents/skills/rst-writer`
- Test: `.agents/skills/simplify-in-subagent/tests/test_simplify_in_subagent_contract.py`（新規）

**Interfaces:**
- Consumes: Task 5 の「ランタイム別の注意」の見出し

統合の規則（simplify-in-subagent）:

- frontmatter: `.agents` 版の `name`・`description` に、`.devin` 版の `argument-hint: "[--staged|--ref=<ref>|<files>]"` と `subagent: true` を足す。`.devin` 版の YAML リスト形式の `allowed-tools`（`read`・`edit`・`grep`・`glob`・`exec`）は取り込まない。Claude Code は `allowed-tools` を許可するツール名の一覧として読むため、存在しないツール名の一覧になると使えるツールが無くなる。
- 見出し `# Simplify in Subagent` の直後に空行を挟んで `対象指定: $ARGUMENTS` の 1 行を置く。
- `## Inputs` の前に次の節を置く。

```markdown
## ランタイム別の注意

- 冒頭の `対象指定` 行は、呼び出し引数を本文へ展開するランタイム（Claude Code、Devin）が埋める補間欄である。値が空欄、またはドル記号で始まるプレースホルダ表記のまま残っている場合は未指定とみなし、呼び出し元のメッセージで指定された ref・`--staged`・ファイル一覧を使う。どれも無ければ既定の `HEAD` との diff を対象にする
- 引数を展開するランタイムは `＄ARGUMENTS` と `＄0`〜`＄9`（ドル記号と数字 1 文字）を置換する（この節では置換されないよう全角で書いている）。埋め込みのコードに位置パラメータを書かず、入力は stdin や名前付き変数で受ける
- Devin では `subagent: true` により本文がサブエージェントの task として実行される。サブエージェントでは `ask_user_question` が使えないため、不明点や異常は質問にせず Recovery に従って報告に回す。`run_subagent` / `read_subagent` もサブエージェント内では無効だが、本手順はネストしたサブエージェントを必要としない
- Devin には `/simplify` 相当の組み込みコマンドが無いため、メインセッションからの直呼び出しでも `subagent: true` によりサブエージェントで実行される
```

- `## Inputs` の 2 項目目を `.devin` 版の文（`Required: one of ref (default \`HEAD\`), \`--staged\`, or explicit file list, taken from the interpolated 対象指定 line. An empty or placeholder line means \`HEAD\`.`）にする。
- それ以外の本文は `.agents` 版のまま。repository-ownership への言及（仕様 8.2 のルーティング表の書き直し）はフェーズ 5 に残す。

- [ ] **Step 1: 失敗するテストを書く**（`.agents/skills/simplify-in-subagent/tests/test_simplify_in_subagent_contract.py`）

```python
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / ".agents/skills/simplify-in-subagent/SKILL.md"


def split(content: str) -> tuple[dict[str, object], str]:
    _, head, body = content.split("---", 2)
    return yaml.safe_load(head), body


def test_interpolation_is_limited_to_the_target_line() -> None:
    content = SKILL.read_text(encoding="utf-8")
    assert content.count("$ARGUMENTS") == 1
    assert "対象指定: $ARGUMENTS" in content
    assert re.search(r"\$[0-9]", content) is None


def test_frontmatter_keeps_only_keys_every_runtime_can_live_with() -> None:
    head, _ = split(SKILL.read_text(encoding="utf-8"))
    assert head["argument-hint"] == "[--staged|--ref=<ref>|<files>]"
    assert head["subagent"] is True
    # Devin's YAML list of its own tool names would become Claude Code's
    # allow-list of tools that do not exist there.
    assert "allowed-tools" not in head


def test_runtime_notes_keep_the_devin_specific_rules() -> None:
    content = SKILL.read_text(encoding="utf-8")
    assert "## ランタイム別の注意" in content
    assert "ask_user_question" in content
    assert "An empty or placeholder line means `HEAD`" in content


def test_claude_code_reads_the_same_skill() -> None:
    link = REPO_ROOT / ".claude/skills/simplify-in-subagent"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/simplify-in-subagent"
```

Run: `uv run pytest .agents/skills/simplify-in-subagent/tests -q 2>&1 | tail -n 1`
Expected: 4 件とも失敗する。

- [ ] **Step 2: 統合版を書き、配置を変える**

```bash
# 上の規則に従って .agents/skills/simplify-in-subagent/SKILL.md を書き換えた後
git rm -rq .devin/skills/simplify-in-subagent
ln -s ../../.agents/skills/simplify-in-subagent .claude/skills/simplify-in-subagent
git mv .claude/skills/rst-writer .agents/skills/rst-writer
ln -s ../../.agents/skills/rst-writer .claude/skills/rst-writer
git add .agents/skills/simplify-in-subagent .claude/skills/simplify-in-subagent .claude/skills/rst-writer
git ls-files .devin | wc -l     # 0
```

- [ ] **Step 3: テストを通す**

```bash
uv run pytest .agents/skills/simplify-in-subagent/tests tests/skills -q 2>&1 | tail -n 1
```

Expected: 失敗 0（skip 1）。

- [ ] **Step 4: 共通の検査を実行してコミットする**

```bash
git commit -m "refactor(skills): merge the Devin simplify-in-subagent notes and move rst-writer to .agents" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 8: 残りの .claude/skills を symlink にし、check-layout にルートのスキル検査を足す（仕様 4.2・8.1・9.1、L72、P-6）

**Files:**
- Delete: `.claude/skills/herdr-agent-task/`、`.claude/skills/monitoring-long-tasks/`（`.agents` 版と同一の実ディレクトリ）
- Create: `.agents/skills/*` のうち `.claude/skills` にまだ無いものすべての symlink（find-docs、pi-model-name、planning-parallel-issues、repository-ownership、Blender 系 10 本、references、herdr-agent-task、monitoring-long-tasks）
- Modify: `scripts/check-layout.sh`、`tests/scripts/test-check-layout.bash`

**Interfaces:**
- Consumes: Task 3〜7 の配置
- Produces: `check_skill_links <prefix>`（`scripts/check-layout.sh` 内の関数。引数はルートなら空文字、プロジェクトなら `slum02/` のように末尾に `/` を付けた接頭辞。問題があれば `fail`、無ければ `ok: <prefix>.claude/skills links are 1:1 with <prefix>.agents/skills` を出す）。Task 12 がプロジェクトごとに呼ぶ

check-layout に足す検査:

- `check_skill_links ""`: `<prefix>.agents/skills/` 直下で追跡ファイルを持つディレクトリ（直下のファイル、例えば `.resoloop-bundled.json` は対象外）と、`<prefix>.claude/skills/` 直下の追跡エントリが 1:1 に対応する。各エントリは mode 120000 の symlink で、`readlink` が `../../.agents/skills/<同名>` と一致する。メッセージ: `<prefix>.claude/skills: missing link <name>`、`<prefix>.claude/skills/<name> is not a symlink`、`<prefix>.claude/skills/<name> has unexpected target <target>`、`<prefix>.claude/skills/<name> has no matching <prefix>.agents/skills/<name>`。
- `check_skill_hygiene`: `.devin/skills` 配下を追跡していない（`.devin/skills is still tracked`）。パスが正規表現 `(^|/)\.(agents|claude)/skills/` に当たる追跡ファイル（mode 120000 を除く）に 0 バイトのものが無い（`empty tracked file: <path>`）。
- L72: 検査 3 の `git ls-files -z -i -c --exclude-standard` を `git -c core.excludesFile=/dev/null ls-files -z -i -c --exclude-standard` にする。

- [ ] **Step 1: 失敗するテストを足す**（`tests/scripts/test-check-layout.bash` の `# 12.` の後、最後の `printf 'PASS: ...'` の前に追加）

P-6 として、既存のケース 12 の実行行を `GIT_CEILING_DIRECTORIES="$tmp" bash "$tmp/detached/check-layout.sh" --root "$tmp/clean" | grep -qF 'PASS: check-layout'` に変える。そのうえで次を足す。

```bash
# .agents/skills/foo を持つ一時リポジトリを作る（.claude 側は各ケースで作る）
skill_repo() {
  new_repo "$1"
  mkdir -p "$1/.agents/skills/foo" "$1/.claude/skills"
  printf -- '---\nname: foo\ndescription: d\n---\n' > "$1/.agents/skills/foo/SKILL.md"
}
commit_paths() {  # $1=リポジトリ、残り=追加するパス
  local r="$1"; shift
  git -C "$r" add -- "$@" && git -C "$r" commit -q -m change
}

# 13. .agents/skills と .claude/skills が 1:1 の symlink なら通過する
skill_repo "$tmp/skills-ok"
ln -s ../../.agents/skills/foo "$tmp/skills-ok/.claude/skills/foo"
commit_paths "$tmp/skills-ok" .agents .claude
bash "$checker" --root "$tmp/skills-ok" | grep -qF 'PASS: check-layout'

# 14. symlink が無ければ失敗する
skill_repo "$tmp/skills-missing"
commit_paths "$tmp/skills-missing" .agents
expect_fail_with "$tmp/skills-missing" 'missing link foo'

# 15. .claude/skills/foo が実ディレクトリなら失敗する
skill_repo "$tmp/skills-realdir"
mkdir -p "$tmp/skills-realdir/.claude/skills/foo"
cp "$tmp/skills-realdir/.agents/skills/foo/SKILL.md" "$tmp/skills-realdir/.claude/skills/foo/SKILL.md"
commit_paths "$tmp/skills-realdir" .agents .claude
expect_fail_with "$tmp/skills-realdir" '.claude/skills/foo is not a symlink'

# 16. 行き先が .agents/skills/foo でなければ失敗する
skill_repo "$tmp/skills-target"
mkdir -p "$tmp/skills-target/other/foo" && printf 'x\n' > "$tmp/skills-target/other/foo/SKILL.md"
ln -s ../../other/foo "$tmp/skills-target/.claude/skills/foo"
commit_paths "$tmp/skills-target" .agents .claude other
expect_fail_with "$tmp/skills-target" '.claude/skills/foo has unexpected target ../../other/foo'

# 17. 対応する .agents/skills の無いリンクは失敗する
skill_repo "$tmp/skills-extra"
ln -s ../../.agents/skills/foo "$tmp/skills-extra/.claude/skills/foo"
mkdir -p "$tmp/skills-extra/elsewhere/bar" && printf 'x\n' > "$tmp/skills-extra/elsewhere/bar/SKILL.md"
ln -s ../../elsewhere/bar "$tmp/skills-extra/.claude/skills/bar"
commit_paths "$tmp/skills-extra" .agents .claude elsewhere
expect_fail_with "$tmp/skills-extra" '.claude/skills/bar has no matching .agents/skills/bar'

# 18. .devin/skills を追跡していれば失敗する
new_repo "$tmp/devin"
mkdir -p "$tmp/devin/.devin/skills/x" && printf 'x\n' > "$tmp/devin/.devin/skills/x/SKILL.md"
commit_paths "$tmp/devin" .devin
expect_fail_with "$tmp/devin" '.devin/skills is still tracked'

# 19. スキル配下の 0 バイトの追跡ファイルは失敗する
skill_repo "$tmp/empty"
ln -s ../../.agents/skills/foo "$tmp/empty/.claude/skills/foo"
mkdir -p "$tmp/empty/.agents/skills/foo/scripts" && : > "$tmp/empty/.agents/skills/foo/scripts/helper.py"
commit_paths "$tmp/empty" .agents .claude
expect_fail_with "$tmp/empty" 'empty tracked file: .agents/skills/foo/scripts/helper.py'

# 20. ユーザのグローバル ignore が追跡ファイルを ignore していても誤検知しない（L72）
printf 'README.md\n' > "$tmp/global-ignore"
printf '[core]\n\texcludesFile = %s\n' "$tmp/global-ignore" > "$tmp/global-gitconfig"
GIT_CONFIG_COUNT=0 GIT_CONFIG_GLOBAL="$tmp/global-gitconfig" bash "$checker" --root "$tmp/clean" | grep -qF 'PASS: check-layout'
```

Run: `bash tests/scripts/test-check-layout.bash`
Expected: ケース 14 で `FAIL: ... was accepted`（検査がまだ無い）。

- [ ] **Step 2: check-layout に検査を足す**

`scripts/check-layout.sh` の検査 3 の後、最後の呼び出し列の前に次を足し、呼び出し列を `check_forbidden_tracked` → `check_symlinks_resolve` → `check_tracked_ignored` → `check_skill_links ""` → `check_skill_hygiene` の順にする。検査 3 の `git ls-files -z -i -c --exclude-standard` は `git -c core.excludesFile=/dev/null ls-files -z -i -c --exclude-standard` にする（L72）。

```bash
# 4. <prefix>.claude/skills の各エントリが <prefix>.agents/skills の同名ディレクトリへの symlink で、1:1 に対応する（仕様 4.2・8.1・9.1）
# 引数: 接頭辞。ルートは ""、プロジェクトは "slum02/" のように末尾に / を付ける
check_skill_links() {
  local prefix="$1"
  local agents="${prefix}.agents/skills/" claude="${prefix}.claude/skills/"
  local -A dirs=() links=()
  local problems=() path record meta mode rest name target
  if ! git ls-files -z -- "${prefix}.agents/skills" > "$tmp_list"; then
    fail "git ls-files failed for ${agents}"
    return
  fi
  while IFS= read -r -d '' path; do
    rest="${path#"$agents"}"
    [ "$rest" != "${rest#*/}" ] || continue   # 直下のファイル（.resoloop-bundled.json など）は対象外
    dirs["${rest%%/*}"]=1
  done < "$tmp_list"
  if ! git ls-files -s -z -- "${prefix}.claude/skills" > "$tmp_list"; then
    fail "git ls-files -s failed for ${claude}"
    return
  fi
  while IFS= read -r -d '' record; do
    meta="${record%%$'\t'*}"
    path="${record#*$'\t'}"
    mode="${meta%% *}"
    rest="${path#"$claude"}"
    name="${rest%%/*}"
    [ -z "${links[$name]+x}" ] || continue
    links["$name"]=1
    if [ "$mode" != 120000 ] || [ "$rest" != "$name" ]; then
      problems+=("${claude}${name} is not a symlink")
      continue
    fi
    target="$(readlink "$path" 2>/dev/null || true)"
    [ "$target" = "../../.agents/skills/$name" ] || problems+=("${claude}${name} has unexpected target ${target:-<none>}")
    [ -n "${dirs[$name]+x}" ] || problems+=("${claude}${name} has no matching ${agents}${name}")
  done < "$tmp_list"
  for name in "${!dirs[@]}"; do
    [ -n "${links[$name]+x}" ] || problems+=("${claude%/}: missing link ${name}")
  done
  if [ ${#problems[@]} -gt 0 ]; then
    local p
    for p in "${problems[@]}"; do fail "$p"; done
  else
    ok "${claude%/} links are 1:1 with ${agents%/}"
  fi
}

# 5. 旧 .devin/skills を追跡していない。スキル配下に 0 バイトの追跡ファイルが無い（仕様 5.5・8.1・11 章）
check_skill_hygiene() {
  local hits=() record meta path mode re='(^|/)\.(agents|claude)/skills/'
  if ! git ls-files -z -- .devin/skills > "$tmp_list"; then
    fail "git ls-files failed for .devin/skills"
    return
  fi
  [ ! -s "$tmp_list" ] || hits+=(".devin/skills is still tracked")
  if ! git ls-files -s -z > "$tmp_list"; then
    fail "git ls-files -s failed"
    return
  fi
  while IFS= read -r -d '' record; do
    meta="${record%%$'\t'*}"
    path="${record#*$'\t'}"
    mode="${meta%% *}"
    [ "$mode" != 120000 ] || continue
    [[ "$path" =~ $re ]] || continue
    [ -s "$path" ] || hits+=("empty tracked file: $path")
  done < "$tmp_list"
  if [ ${#hits[@]} -gt 0 ]; then
    local h
    for h in "${hits[@]}"; do fail "$h"; done
  else
    ok "skill trees hold no retired or empty tracked files"
  fi
}
```

- [ ] **Step 3: ルートの .claude/skills をすべて symlink にする**

```bash
for d in .agents/skills/*/; do
  n="$(basename "$d")"
  [ -L ".claude/skills/$n" ] && continue
  if [ -d ".claude/skills/$n" ]; then
    # .claude 側の各ファイルが .agents 側と同一であること（.agents 側にだけある tests/ などは問題ない）
    differs="$(cd ".claude/skills/$n" && find . -type f | while IFS= read -r f; do
      cmp -s "../../../.agents/skills/$n/$f" "$f" || printf '%s ' "$f"; done)"
    if [ -n "$differs" ]; then echo "STOP: .claude/skills/$n differs: $differs"; break; fi
    git rm -rq ".claude/skills/$n"
  fi
  ln -s "../../.agents/skills/$n" ".claude/skills/$n"
  git add ".claude/skills/$n"
done
rmdir .devin/skills .devin 2>/dev/null || true
ls -la .claude/skills | grep -vc -- '->'            # 3（total 行と . と ..）
```

`STOP:` が出たら、その Task を止めて controller に報告する（herdr-agent-task と monitoring-long-tasks の `.claude` 側の `SKILL.md` は `.agents` 側と同一で、`.agents` 側にだけ `tests/` があることを計画作成時に確認済み）。

- [ ] **Step 4: テストを通す**

```bash
bash tests/scripts/test-check-layout.bash     # PASS（ケース 6 でこのリポジトリ自身も通る）
bash scripts/check-layout.sh                 # ok: ×5、PASS: check-layout
uv run pytest -q 2>&1 | tail -n 1            # 34 failed（pi-model-name 27 件と repository-ownership の public_release 7 件だけ）
```

- [ ] **Step 5: Devin の表示を実測する**

```bash
(cd "$W/slum02" && devin skills list 2>&1) | grep -E '/(claude|devin|agents):' || echo 'no prefixed duplicates'
```

Expected: `no prefixed duplicates`（同じ実体の二重掲示が無い）。

- [ ] **Step 6: 共通の検査を実行してコミットする**（この Task 以降、除外リストの一時的な 3 行はどれも該当しない）

```bash
git add scripts/check-layout.sh tests/scripts/test-check-layout.bash
git commit -m "feat(layout): link every shared skill into .claude/skills and check the links" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 9: エージェントの設定ファイルと pi-superagents の定義（仕様 5.5・4.2、判断事項 D-1）

**Files:**
- Create: `.codex/config.toml`、`.cursor/mcp.json`
- Modify: `.pi-lens.json`
- Create: `.agents/sp-implementer.md`（メイン作業ツリーの未追跡ファイル `$M/MyResoniteProject/.agents/sp-implementer.md` の読み取りコピー）
- Test: `tests/scripts/test-agent-config.bash`（新規、実行権付き）

**Interfaces:**
- Produces: ルート `.agents/sp-implementer.md`（Task 10 の new-world.sh は、ルートの `.agents/sp-*.md` ごとにプロジェクトへ symlink を張る。Task 12 はその symlink を検査する）

- [ ] **Step 1: 失敗するテストを書く**（`tests/scripts/test-agent-config.bash`）

```bash
#!/bin/bash
# エージェントの設定ファイルと pi-superagents の定義が仕様 5.5・4.2 と判断事項 D-1 のとおりであることを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

uv run --no-project python - <<'PY'
import json
import tomllib

codex = tomllib.load(open(".codex/config.toml", "rb"))
c7 = codex["mcp_servers"]["context7"]
assert c7["command"] == "npx", c7
assert c7["args"] == ["-y", "@upstash/context7-mcp"], c7
assert c7.get("env_vars") == ["CONTEXT7_API_KEY"], c7

cursor = json.load(open(".cursor/mcp.json", encoding="utf-8"))
cc7 = cursor["mcpServers"]["context7"]
assert cc7["command"] == "npx" and cc7["args"] == ["-y", "@upstash/context7-mcp"], cc7

lens = json.load(open(".pi-lens.json", encoding="utf-8"))
assert "$schema" not in lens, lens
for pattern in (".devcontainer/devcontainer.json", "**/*.md", "**/*.markdown", "**/*.mdx",
                "**/tmp/**", "**/.venv/**", "**/artifacts/**", "**/.resoloop/**", "external/**", "private/**"):
    assert pattern in lens["ignore"], pattern
PY

# pi-superagents: 組み込み定義と内容が違う sp-implementer.md だけを追跡する（判断事項 D-1）
grep -qxF 'name: sp-implementer' .agents/sp-implementer.md || fail '.agents/sp-implementer.md missing'
grep -qxF 'model: balanced' .agents/sp-implementer.md || fail 'sp-implementer must keep model: balanced'
[ "$(cd .agents && ls sp-*.md 2>/dev/null)" = 'sp-implementer.md' ] || fail 'unexpected sp-*.md set under .agents'
# Devin は symlink 経由の同名スキルを 1 回だけ表示するので、Claude 互換読込は止めない（仕様 5.5 の条件が成立しない）
[ ! -e .devin/config.json ] || fail '.devin/config.json must not be created'

printf 'PASS: agent configuration follows spec 5.5\n'
```

Run: `bash tests/scripts/test-agent-config.bash`
Expected: `FileNotFoundError: ... .codex/config.toml` で失敗する。

- [ ] **Step 2: 設定ファイルを書く**

`.codex/config.toml`:

```toml
# Codex のプロジェクト設定。Codex がこのリポジトリを信頼済み（trusted）として扱うときだけ読まれる。
# プロジェクトのディレクトリを cwd にして起動しても、.git のあるルートまで遡ってこのファイルが読まれる。
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp"]
env_vars = ["CONTEXT7_API_KEY"]
```

`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

`.pi-lens.json`:

```json
{
  "ignore": [
    ".devcontainer/devcontainer.json",
    "**/*.md",
    "**/*.markdown",
    "**/*.mdx",
    "**/tmp/**",
    "**/.venv/**",
    "**/artifacts/**",
    "**/.resoloop/**",
    "external/**",
    "private/**"
  ]
}
```

- [ ] **Step 3: sp-implementer.md を読み取りでコピーする**

```bash
P="$HOME/.pi/agent/npm/node_modules/@teelicht/pi-superagents/agents"
diff "$P/sp-implementer.md" "$M/MyResoniteProject/.agents/sp-implementer.md"   # model: cheap / model: balanced の 1 行だけ
for f in sp-brainstorm sp-debug sp-implement-parallel sp-implement sp-plan sp-recon sp-research sp-review; do
  cmp "$P/$f.md" "$M/MyResoniteProject/.agents/$f.md"                            # 8 件とも同一（出力なし）
done
install -m 0644 "$M/MyResoniteProject/.agents/sp-implementer.md" .agents/sp-implementer.md
```

`diff` が 1 行以外の差分を出す、または `cmp` が差分を出したら、止めて controller に報告する（判断事項 D-1 の前提が変わっている）。

- [ ] **Step 4: テストを通し、到達性を実測する**

```bash
bash tests/scripts/test-agent-config.bash
S="$(mktemp -d)"; printf '[projects."%s"]\ntrust_level = "trusted"\n' "$W" > "$S/config.toml"
(cd "$W/slum02" && CODEX_HOME="$S" codex mcp list 2>/dev/null) | grep -E '^context7 +npx'
(cd "$W/slum02" && cursor-agent mcp list 2>&1) | grep -F 'context7'
```

Expected: `PASS: agent configuration follows spec 5.5`。Codex は隔離した `CODEX_HOME` でこのリポジトリを信頼済みにしたときだけ、プロジェクト cwd からルートの `.codex/config.toml` の context7（`npx`）を表示する。cursor-agent はプロジェクト cwd からルートの `.cursor/mcp.json` を見つけ、`context7: not loaded (needs approval)` を表示する（どちらも 2026-09-26 に複製リポジトリで実測済み）。`CODEX_HOME` が `/tmp` 配下のため出る helper binaries の WARNING は無視してよい。

- [ ] **Step 5: 共通の検査を実行してコミットする**

```bash
git add .codex/config.toml .cursor/mcp.json .pi-lens.json .agents/sp-implementer.md tests/scripts/test-agent-config.bash
git update-index --chmod=+x tests/scripts/test-agent-config.bash
git commit -m "chore(agents): add Codex and Cursor MCP config, tidy pi-lens and track the customised sp-implementer" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 10: プロジェクト雛形と scripts/new-world.sh（仕様 4.3）

**Files:**
- Create: `templates/world-project/CLAUDE.md`、`templates/world-project/pyproject.toml`、`templates/world-project/AGENTS.local.md`、`templates/world-project/resoloop-gitignore`
- Create: `scripts/new-world.sh`（実行権付き）
- Test: `tests/scripts/test-new-world.bash`（新規、実行権付き）

**Interfaces:**
- Consumes: ルートの `.claude/settings.json`、`.pi/`、`.agents/sp-*.md`（Task 9）
- Produces: `scripts/new-world.sh [--apply] [--no-sync] [--root DIR] <name>`。終了コード 0 成功、1 既存ファイルとの食い違いあり（何も変更しない）、2 使い方の誤り、3 前提不足。成功時は最後に `DONE: <name>` を出す。Task 11 が `--apply` で 3 プロジェクトに使う

仕様 4.3 の「差分があれば報告して終了コード非 0 で止まる」は、次のように解釈する（どれも最初の走査で全件を集め、1 件でもあれば何も変更せずに終了コード 1）。

- `CLAUDE.md` が存在して雛形と内容が違う、または通常ファイルでない
- 作るべき symlink の位置に、行き先の違う symlink や実ファイル・実ディレクトリがある
- 作るべき symlink の行き先が存在しない
- `.claude/skills/<name>` に対応する `.agents/skills/<name>/SKILL.md` が無い（行き先の無いリンク）

リンクを張る対象は `.agents/skills/` 直下で `SKILL.md` を持つディレクトリだけとする（空ディレクトリや参照資料だけのディレクトリには張らない）。

`pyproject.toml` は雛形を出発点にするだけなので、存在すれば内容を比べない。`AGENTS.md` は「## このプロジェクト固有」の行が無ければ固有節を追記し、`.resoloop/.gitignore` は無ければ作り、`cache/` の行が無ければ追記する。

- [ ] **Step 1: 雛形を作る**

`templates/world-project/CLAUDE.md`:

```markdown
@AGENTS.md
```

`templates/world-project/pyproject.toml`:

```toml
[project]
name = "{{name}}"
version = "0.1.0"
description = "Resonite world {{name}} built with resoloop and Blender"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

`templates/world-project/AGENTS.local.md`:

```markdown
## このプロジェクト固有

- テスト: このディレクトリで `uv run pytest` を実行する
- ワールド: {{name}}。所有キーと所有ルートスロットは、ワールドの設計が決まったらここに書く
- state ファイル: `flux/resoloop.flux.json` の `worldState` を既定とする。ワールドごとに分ける場合はここに書く
```

`templates/world-project/resoloop-gitignore`:

```
state/
flux-state/
cache/
```

- [ ] **Step 2: 失敗するテストを書く**（`tests/scripts/test-new-world.bash`）

```bash
#!/bin/bash
# scripts/new-world.sh の作成・適用・冪等性・食い違いの検出を、一時リポジトリとモックの resoloop / uv で検査する
set -euo pipefail
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
script="$repo_root/scripts/new-world.sh"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# モック: resoloop init は最小の scaffold を作り、skills sync と uv は呼び出しを記録するだけ
mkdir -p "$tmp/mockbin"
cat > "$tmp/mockbin/resoloop" <<'EOF'
#!/bin/bash
printf '%s\n' "resoloop $*" >> "$MOCK_LOG"
case "$1" in
  init)
    d="$2"
    mkdir -p "$d/.agents/skills/resonite-build" "$d/.resoloop" "$d/flux"
    printf '{}\n' > "$d/.resoloop.json"
    printf '# ResoLoop project guide\n' > "$d/AGENTS.md"
    printf -- '---\nname: resonite-build\ndescription: mock\n---\n' > "$d/.agents/skills/resonite-build/SKILL.md"
    printf '{}\n' > "$d/.agents/skills/.resoloop-bundled.json"
    printf 'state/\nflux-state/\n' > "$d/.resoloop/.gitignore"
    printf '{}\n' > "$d/flux/resoloop.flux.json"
    ;;
  skills) exit 0 ;;
  *) exit 64 ;;
esac
EOF
cat > "$tmp/mockbin/uv" <<'EOF'
#!/bin/bash
printf '%s\n' "uv $* (cwd=$PWD)" >> "$MOCK_LOG"
EOF
chmod +x "$tmp/mockbin/resoloop" "$tmp/mockbin/uv"
export MOCK_LOG="$tmp/mock.log"
: > "$MOCK_LOG"
export PATH="$tmp/mockbin:$PATH"

# 雛形と共有物（.claude/settings.json、.pi、.agents/sp-implementer.md）を持つ一時リポジトリ
new_root() {
  local r="$1"
  git init -q "$r"
  mkdir -p "$r/scripts" "$r/.claude" "$r/.pi" "$r/.agents"
  cp -r "$repo_root/templates" "$r/templates"
  cp "$script" "$r/scripts/new-world.sh"
  printf '{}\n' > "$r/.claude/settings.json"
  printf 'pi\n' > "$r/.pi/APPEND_SYSTEM.md"
  printf -- '---\nname: sp-implementer\n---\n' > "$r/.agents/sp-implementer.md"
}
run() { local r="$1"; shift; bash "$r/scripts/new-world.sh" --root "$r" "$@"; }
expect_exit() {  # $1=期待する終了コード、$2=出力に含まれるべき文字列、残り=run の引数
  local want="$1" needle="$2" got=0
  shift 2
  run "$@" > "$tmp/out.txt" 2>&1 || got=$?
  [ "$got" -eq "$want" ] || { cat "$tmp/out.txt" >&2; fail "expected exit $want, got $got: $*"; }
  grep -qF -- "$needle" "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; fail "expected output '$needle': $*"; }
}
snapshot() {
  (cd "$1" && find . -printf '%y %p %l\n' | sort && find . -type f -print0 | sort -z | xargs -0 -r sha256sum)
}

# 1. 不正な名前は 2
new_root "$tmp/r1"
for bad in '' 'a b' '../x' '-x' 'x/y' '.hidden'; do
  expect_exit 2 '' "$tmp/r1" --no-sync "$bad"
done
[ -z "$(ls -A "$tmp/r1" | grep -vxE 'scripts|templates|\.claude|\.pi|\.agents|\.git')" ] || fail 'invalid name created something'

# 2. 新規作成: resoloop init の後に雛形と symlink を作る
new_root "$tmp/r2"
expect_exit 0 'DONE: demo' "$tmp/r2" --no-sync demo
p="$tmp/r2/demo"
[ "$(cat "$p/CLAUDE.md")" = '@AGENTS.md' ] || fail 'CLAUDE.md content'
grep -qxF 'name = "demo"' "$p/pyproject.toml" || fail 'pyproject name'
grep -qxF '## このプロジェクト固有' "$p/AGENTS.md" || fail 'AGENTS.md section'
[ "$(grep -cxF 'cache/' "$p/.resoloop/.gitignore")" -eq 1 ] || fail 'cache/ appended once'
for link in '.claude/skills/resonite-build|../../.agents/skills/resonite-build' \
            '.claude/settings.json|../../.claude/settings.json' '.pi|../.pi' \
            '.agents/sp-implementer.md|../../.agents/sp-implementer.md'; do
  rel="${link%%|*}" target="${link#*|}"
  [ "$(readlink "$p/$rel")" = "$target" ] || fail "link $rel"
  [ -e "$p/$rel" ] || fail "dangling $rel"
done
grep -qF "resoloop init $p" "$MOCK_LOG" || fail 'resoloop init not called'

# 3. 既存ディレクトリに --apply 無しで実行すると 2
expect_exit 2 'use --apply' "$tmp/r2" --no-sync demo

# 4. --apply を繰り返しても何も変わらない
before="$(snapshot "$p")"
expect_exit 0 'DONE: demo' "$tmp/r2" --apply --no-sync demo
[ "$before" = "$(snapshot "$p")" ] || fail 'second --apply changed files'

# 5. 存在しないプロジェクトへの --apply は 2
expect_exit 2 'drop --apply' "$tmp/r2" --apply --no-sync missing

# 6. .pi が実ディレクトリなら 1 を返し、何も変更しない（CLAUDE.md も作らない）
new_root "$tmp/r6"
run "$tmp/r6" --no-sync demo >/dev/null
rm "$tmp/r6/demo/.pi" "$tmp/r6/demo/CLAUDE.md" && mkdir "$tmp/r6/demo/.pi"
before="$(snapshot "$tmp/r6/demo")"
expect_exit 1 'CONFLICT: .pi exists and is not a symlink' "$tmp/r6" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r6/demo")" ] || fail 'conflicting --apply changed files'

# 7. CLAUDE.md が雛形と違えば 1
new_root "$tmp/r7"
run "$tmp/r7" --no-sync demo >/dev/null
printf 'other\n' > "$tmp/r7/demo/CLAUDE.md"
expect_exit 1 'CONFLICT: CLAUDE.md differs from templates/world-project/CLAUDE.md' "$tmp/r7" --apply --no-sync demo

# 8. 対応する .agents/skills の無い .claude/skills のリンクは 1
new_root "$tmp/r8"
run "$tmp/r8" --no-sync demo >/dev/null
ln -s ../../.agents/skills/stale "$tmp/r8/demo/.claude/skills/stale"
expect_exit 1 'CONFLICT: .claude/skills/stale has no matching .agents/skills/stale' "$tmp/r8" --apply --no-sync demo

# 9. resoloop プロジェクトでないディレクトリへの --apply は 3
new_root "$tmp/r9"
mkdir "$tmp/r9/plain"
expect_exit 3 'not a resoloop project' "$tmp/r9" --apply --no-sync plain

# 10. resoloop が無ければ新規作成は 3
new_root "$tmp/r10"
if PATH=/usr/local/bin:/usr/bin:/bin command -v resoloop >/dev/null 2>&1; then fail 'resoloop visible on the reduced PATH'; fi
PATH=/usr/local/bin:/usr/bin:/bin expect_exit 3 'resoloop not found' "$tmp/r10" --no-sync demo

# 11. 同期ありでは uv sync をプロジェクトで実行し、resoloop skills sync --check を呼ぶ
new_root "$tmp/r11"
: > "$MOCK_LOG"
expect_exit 0 'ok: resoloop skills sync --check' "$tmp/r11" demo
grep -qF "uv sync (cwd=$tmp/r11/demo)" "$MOCK_LOG" || fail 'uv sync not run in the project'
grep -qF "resoloop skills sync $tmp/r11/demo --check" "$MOCK_LOG" || fail 'skills sync --check not run'

# 12. 既存の .resoloop/.gitignore に cache/ が無ければ 1 回だけ追記する
new_root "$tmp/r12"
run "$tmp/r12" --no-sync demo >/dev/null
printf 'state/\nflux-state/\n' > "$tmp/r12/demo/.resoloop/.gitignore"
run "$tmp/r12" --apply --no-sync demo >/dev/null
run "$tmp/r12" --apply --no-sync demo >/dev/null
[ "$(grep -cxF 'cache/' "$tmp/r12/demo/.resoloop/.gitignore")" -eq 1 ] || fail 'cache/ appended more than once'

# 13. SKILL.md の無いディレクトリ（移動後に残った空ディレクトリなど）にはリンクを張らない
new_root "$tmp/r13"
run "$tmp/r13" --no-sync demo >/dev/null
mkdir -p "$tmp/r13/demo/.agents/skills/leftover"
expect_exit 0 'DONE: demo' "$tmp/r13" --apply --no-sync demo
if [ -e "$tmp/r13/demo/.claude/skills/leftover" ] || [ -L "$tmp/r13/demo/.claude/skills/leftover" ]; then
  fail 'linked a directory without SKILL.md'
fi

printf 'PASS: new-world script behaves as specified\n'
```

Run: `bash tests/scripts/test-new-world.bash`
Expected: スクリプトが無いため失敗する。

- [ ] **Step 3: `scripts/new-world.sh` を書く**

```bash
#!/bin/bash
# ワールドのプロジェクトを作る、または既存プロジェクトに雛形の不足分を適用する。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 4.2・4.3 節
# 使い方: scripts/new-world.sh [--apply] [--no-sync] [--root DIR] <name>
# 終了コード: 0 成功 / 1 既存ファイルとの食い違いあり（何も変更しない） / 2 使い方の誤り / 3 前提不足
set -euo pipefail

usage() {
  printf 'usage: %s [--apply] [--no-sync] [--root DIR] <name>\n' "${BASH_SOURCE[0]}" >&2
  exit 2
}
die() { printf 'ERROR: %s\n' "$2" >&2; exit "$1"; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
apply=0 sync=1 root="" name="" name_given=0
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) apply=1; shift ;;
    --no-sync) sync=0; shift ;;
    --root)
      [ $# -ge 2 ] || usage
      root="$(git -C "$2" rev-parse --show-toplevel 2>/dev/null)" || usage
      shift 2
      ;;
    -*) usage ;;
    *) [ "$name_given" -eq 0 ] || usage; name="$1"; name_given=1; shift ;;
  esac
done
[ "$name_given" -eq 1 ] || usage
[[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || die 2 "invalid project name '$name' (use letters, digits, '-' and '_'; start with a letter or digit)"
[ -n "$root" ] || root="$(git -C "$script_dir" rev-parse --show-toplevel)"
tmpl="$root/templates/world-project"
[ -d "$tmpl" ] || die 3 "template directory not found: $tmpl"
proj="$root/$name"

if [ -e "$proj" ] || [ -L "$proj" ]; then
  [ "$apply" -eq 1 ] || die 2 "$name already exists; use --apply to add the missing scaffold"
else
  [ "$apply" -eq 0 ] || die 2 "$name does not exist; drop --apply to create it"
  command -v resoloop >/dev/null 2>&1 || die 3 "resoloop not found; install it before creating a project"
  resoloop init "$proj" --json >/dev/null
fi
[ -f "$proj/.resoloop.json" ] || die 3 "$name is not a resoloop project (.resoloop.json is missing)"
[ -f "$proj/AGENTS.md" ] || die 3 "$name/AGENTS.md is missing; run resoloop init first"

render() { sed -e "s/{{name}}/$name/g" "$1"; }

# 1 周目: 作るもの・追記するものを集め、既存ファイルとの食い違いを集める。食い違いがあれば何も変更しない
conflicts=() plan_files=() plan_links=() append_section=0 append_cache=0

want_file() {  # $1=相対パス、$2=雛形、$3=既存と比べるなら 1
  local rel="$1" src="$2" compare="$3"
  if [ -L "$proj/$rel" ] || { [ -e "$proj/$rel" ] && [ ! -f "$proj/$rel" ]; }; then
    conflicts+=("$rel is not a regular file")
  elif [ -f "$proj/$rel" ]; then
    if [ "$compare" -eq 1 ] && ! diff -q <(render "$src") "$proj/$rel" >/dev/null; then
      conflicts+=("$rel differs from templates/world-project/$(basename "$src")")
    fi
  else
    plan_files+=("$rel|$src")
  fi
}

want_link() {  # $1=相対パス、$2=期待する行き先
  local rel="$1" target="$2" current
  if [ -L "$proj/$rel" ]; then
    current="$(readlink "$proj/$rel")"
    [ "$current" = "$target" ] || conflicts+=("$rel points to $current, expected $target")
  elif [ -e "$proj/$rel" ]; then
    conflicts+=("$rel exists and is not a symlink")
  elif [ ! -e "$(realpath -m "$(dirname "$proj/$rel")/$target")" ]; then
    conflicts+=("$rel would point to missing $target")
  else
    plan_links+=("$rel|$target")
  fi
}

want_file CLAUDE.md "$tmpl/CLAUDE.md" 1
want_file pyproject.toml "$tmpl/pyproject.toml" 0
grep -qxF '## このプロジェクト固有' "$proj/AGENTS.md" || append_section=1
if [ -f "$proj/.resoloop/.gitignore" ] && [ ! -L "$proj/.resoloop/.gitignore" ]; then
  grep -qxF 'cache/' "$proj/.resoloop/.gitignore" || append_cache=1
else
  want_file .resoloop/.gitignore "$tmpl/resoloop-gitignore" 0
fi
want_link .claude/settings.json ../../.claude/settings.json
want_link .pi ../.pi
for sp in "$root"/.agents/sp-*.md; do
  [ -f "$sp" ] || continue
  want_link ".agents/$(basename "$sp")" "../../.agents/$(basename "$sp")"
done
for f in "$proj"/.agents/skills/*/SKILL.md; do
  [ -f "$f" ] || continue
  n="$(basename "$(dirname "$f")")"
  want_link ".claude/skills/$n" "../../.agents/skills/$n"
done
for l in "$proj"/.claude/skills/*; do
  [ -e "$l" ] || [ -L "$l" ] || continue
  n="$(basename "$l")"
  [ -f "$proj/.agents/skills/$n/SKILL.md" ] || conflicts+=(".claude/skills/$n has no matching .agents/skills/$n")
done

if [ ${#conflicts[@]} -gt 0 ]; then
  printf 'CONFLICT: %s\n' "${conflicts[@]}" >&2
  printf 'no changes were made to %s\n' "$name" >&2
  exit 1
fi

# 2 周目: 適用する
for entry in ${plan_files[@]+"${plan_files[@]}"}; do
  rel="${entry%%|*}" src="${entry#*|}"
  mkdir -p "$(dirname "$proj/$rel")"
  render "$src" > "$proj/$rel"
  printf 'created: %s\n' "$rel"
done
if [ "$append_section" -eq 1 ]; then
  { printf '\n'; render "$tmpl/AGENTS.local.md"; } >> "$proj/AGENTS.md"
  printf 'appended: AGENTS.md (## このプロジェクト固有)\n'
fi
if [ "$append_cache" -eq 1 ]; then
  printf 'cache/\n' >> "$proj/.resoloop/.gitignore"
  printf 'appended: .resoloop/.gitignore (cache/)\n'
fi
for entry in ${plan_links[@]+"${plan_links[@]}"}; do
  rel="${entry%%|*}" target="${entry#*|}"
  mkdir -p "$(dirname "$proj/$rel")"
  ln -s "$target" "$proj/$rel"
  printf 'linked: %s -> %s\n' "$rel" "$target"
done

if [ "$sync" -eq 1 ]; then
  (cd "$proj" && uv sync)
  if ! command -v resoloop >/dev/null 2>&1; then
    printf 'skip: resoloop not found (skills sync check)\n'
  elif resoloop skills sync "$proj" --check; then
    printf 'ok: resoloop skills sync --check\n'
  else
    printf 'WARN: resoloop skills sync --check failed for %s; review the report, then run resoloop skills sync %s --update\n' "$name" "$name" >&2
  fi
fi
printf 'DONE: %s\n' "$name"
```

- [ ] **Step 4: テストを通す**

```bash
chmod +x scripts/new-world.sh tests/scripts/test-new-world.bash
bash tests/scripts/test-new-world.bash
```

Expected: `PASS: new-world script behaves as specified`。

- [ ] **Step 5: 共通の検査を実行してコミットする**

```bash
git add templates/world-project scripts/new-world.sh tests/scripts/test-new-world.bash
git update-index --chmod=+x scripts/new-world.sh tests/scripts/test-new-world.bash
git commit -m "feat(scripts): add the world-project template and new-world.sh" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 11: 3 プロジェクトに雛形を適用する（仕様 4.2・4.3）

worktree の `MyResoniteProject/` と `akichi/` には、resoloop の scaffold（`AGENTS.md`、`.resoloop.json`、`.resoloop/.gitignore`、resonite-* スキル、`flux/`）が無い（メイン作業ツリーでは未追跡）。一時ディレクトリで `resoloop init` した結果から写し、メイン作業ツリーの未追跡ファイルと同じ内容であることを読み取りで確かめる（`resoloop init` を同名の一時ディレクトリで実行すると、`flux/` と `.resoloop.json` がメイン作業ツリーのものと同一になることを計画作成時に確認済み）。`AGENTS.md` は resoloop preview.14 の文面（slum02 と同じ）に揃え、固有節を足す。

**Files:**
- Create（MyResoniteProject、akichi）: `AGENTS.md`、`CLAUDE.md`、`.resoloop.json`、`.resoloop/.gitignore`、`.agents/skills/.resoloop-bundled.json`、`.agents/skills/resonite-{blender,build,debug,flux,inspect,uix}/`、`.agents/sp-implementer.md`（symlink）、`.claude/skills/resonite-*`（symlink 6 本）、`.claude/settings.json`（symlink）、`.pi`（symlink）、`flux/{.gitignore,Main.pg,protograph.toml,resoloop.flux.json}`
- Modify（slum02）: `AGENTS.md`（固有節を追記）。Create: `CLAUDE.md`、`.resoloop/.gitignore`、`.agents/sp-implementer.md`、`.claude/skills/resonite-*`、`.claude/settings.json`、`.pi`

**Interfaces:**
- Consumes: Task 10 の `scripts/new-world.sh --apply`、Task 9 の `.agents/sp-implementer.md`、Task 1 の `MyResoniteProject/pyproject.toml`
- Produces: 仕様 4.2 を満たす 3 プロジェクト（Task 12 の検査の対象）

各プロジェクトの固有節（`## このプロジェクト固有`）:

MyResoniteProject:

```markdown
## このプロジェクト固有

- テスト: このディレクトリで `uv run pytest` を実行する
- ワールド: Tokyo Nova の西側スラム。所有キーは `tokyo-nova-west-slum`、所有ルートスロットは `TokyoNova_WestSlum`（`content/tokyo-nova/pipeline-config.json` の `ownership`）
- state ファイル: `.resoloop/tokyo-nova/state/blockout.json`（プローブは `.resoloop/tokyo-nova/state/probe.json`）
- `.resoloop/tokyo-nova/pipeline.json` はテストが参照する証跡ファイルで、ignore 規則の既知の例外として追跡している。移動・削除しない
```

akichi:

```markdown
## このプロジェクト固有

- テスト: このディレクトリで `uv run pytest` を実行する
- ワールド: akichi（サイバーパンクのスラム街区）。所有キーは `akichi`、所有ルートスロットは `Akichi_Slum`
- state ファイル: `.resoloop/akichi/state/akichi-slum.json`
```

slum02:

```markdown
## このプロジェクト固有

- テスト: このディレクトリで `uv run pytest` を実行する
- ワールド: slum02（サイバーパンクのスラム）。所有キーは `slum02`、所有ルートスロットは `Slum02_Slum`。akichi の `Akichi_Slum` を含む所有範囲外のコンテンツは変更しない
- state ファイル: `.resoloop/slum02/state/slum02.json`
```

- [ ] **Step 1: 前提を確かめる**

```bash
git ls-files MyResoniteProject/AGENTS.md akichi/AGENTS.md MyResoniteProject/.resoloop.json akichi/.resoloop.json | wc -l   # 0
git ls-files slum02/AGENTS.md slum02/.resoloop.json | wc -l                                                              # 2
bash scripts/check-layout.sh | tail -n 1                                                                                # PASS: check-layout
```

- [ ] **Step 2: MyResoniteProject と akichi の scaffold を写す**

```bash
for P in MyResoniteProject akichi; do
  gen="$(mktemp -d)/$P"
  resoloop init "$gen" --json >/dev/null
  for f in AGENTS.md .resoloop.json .resoloop/.gitignore .agents/skills/.resoloop-bundled.json \
           flux/.gitignore flux/Main.pg flux/protograph.toml flux/resoloop.flux.json; do
    if [ -e "$W/$P/$f" ]; then echo "STOP: $P/$f already exists"; exit 1; fi
    install -D -m 0644 "$gen/$f" "$W/$P/$f"
  done
  mkdir -p "$W/$P/.agents/skills"
  for d in "$gen"/.agents/skills/resonite-*; do
    n="$(basename "$d")"
    if [ -e "$W/$P/.agents/skills/$n" ]; then echo "STOP: $P/.agents/skills/$n already exists"; exit 1; fi
    cp -r "$d" "$W/$P/.agents/skills/$n"
  done
  # メイン作業ツリーの未追跡 scaffold と同じ内容であることを読み取りで確かめる（AGENTS.md は preview.14 の文面に揃えるので除く）
  for f in .resoloop.json .resoloop/.gitignore .agents/skills/.resoloop-bundled.json \
           flux/.gitignore flux/Main.pg flux/protograph.toml flux/resoloop.flux.json; do
    cmp -s "$W/$P/$f" "$M/$P/$f" || echo "STOP: $P/$f differs from the main tree's untracked copy"
  done
  for d in "$W/$P"/.agents/skills/resonite-*; do
    diff -rq "$d" "$M/$P/.agents/skills/$(basename "$d")" >/dev/null || echo "STOP: $P/.agents/skills/$(basename "$d") differs"
  done
  diff -q "$gen/AGENTS.md" "$W/slum02/AGENTS.md" >/dev/null || echo "STOP: slum02/AGENTS.md is not the preview.14 text"
done
```

`STOP:` が 1 行でも出たら、止めて controller に報告する（`M` を export し忘れた場合も `STOP:` になる）。

- [ ] **Step 3: 固有節を追記する**

上の 3 つの固有節を、それぞれのプロジェクトの `AGENTS.md` の末尾に、空行 1 行を挟んで追記する。

- [ ] **Step 4: `--apply` を 3 プロジェクトに適用する**

```bash
for P in MyResoniteProject akichi slum02; do bash scripts/new-world.sh --apply "$P"; done
```

Expected: 3 つとも `ok: resoloop skills sync --check` と `DONE: <name>` を出して終了コード 0。`created: CLAUDE.md`、`appended: .resoloop/.gitignore (cache/)`（slum02 は `created: .resoloop/.gitignore`）、`linked:` が 9 行（`.claude/settings.json`、`.pi`、`.agents/sp-implementer.md`、`.claude/skills/resonite-*` の 6 本）。`appended: AGENTS.md` は出ない（Step 3 で固有節を書いたため）。

- [ ] **Step 5: 各プロジェクトを検証する**

```bash
for P in MyResoniteProject akichi slum02; do
  resoloop skills sync "$P" --check >/dev/null && echo "sync ok: $P"
  (cd "$P" && uv run pytest -q 2>&1 | tail -n 1)
done
bash scripts/check-layout.sh | tail -n 1
```

Expected: `sync ok` が 3 行。テストは MyResoniteProject `52 passed`、akichi `66 passed`、slum02 `215 passed`。check-layout は `PASS: check-layout`。

- [ ] **Step 6: 明示したパスだけを追加してコミットする**

```bash
for P in MyResoniteProject akichi; do
  git add -- "$P/AGENTS.md" "$P/CLAUDE.md" "$P/.resoloop.json" "$P/.resoloop/.gitignore" "$P/.agents/skills" \
    "$P/.agents/sp-implementer.md" "$P/.claude/skills" "$P/.claude/settings.json" "$P/.pi" "$P/flux"
done
git add -- slum02/AGENTS.md slum02/CLAUDE.md slum02/.resoloop/.gitignore slum02/.agents/sp-implementer.md \
  slum02/.claude/skills slum02/.claude/settings.json slum02/.pi
git status --porcelain | grep -v '^[AM] ' || echo 'only staged changes'
git commit -m "feat(projects): apply the world-project template to MyResoniteProject, akichi and slum02" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

Expected: `only staged changes`（未追跡や未ステージの変更が残っていない）。

---

### Task 12: check-layout にプロジェクト検査と resoloop skills sync の検査を足す（仕様 9.1）

**Files:**
- Modify: `scripts/check-layout.sh`、`tests/scripts/test-check-layout.bash`

**Interfaces:**
- Consumes: Task 8 の `check_skill_links <prefix>`、Task 11 の 3 プロジェクト

検査の内容:

- `collect_projects`: `git ls-files -z -- '*/.resoloop.json'` のうち、パスが `^[^/]+/\.resoloop\.json$` に当たるもの（リポジトリ直下のディレクトリ）をプロジェクトとする。
- `check_project <dir>`: 次の追跡ファイルがある（`<dir>: missing tracked file <f>`）: `AGENTS.md`、`CLAUDE.md`、`.resoloop.json`、`.resoloop/.gitignore`、`pyproject.toml`、`uv.lock`、`.agents/skills/.resoloop-bundled.json`、`flux/resoloop.flux.json`。`CLAUDE.md` の内容が `@AGENTS.md` だけ（`<dir>: CLAUDE.md must be exactly @AGENTS.md`）。`AGENTS.md` に `## このプロジェクト固有` の行がある（`<dir>: AGENTS.md lacks ## このプロジェクト固有`）。`.resoloop/.gitignore` に `cache/` の行がある（`<dir>: .resoloop/.gitignore lacks cache/`）。`.claude/settings.json` → `../../.claude/settings.json`、`.pi` → `../.pi`、ルートで追跡している `.agents/sp-*.md` ごとに `.agents/<同名>` → `../../.agents/<同名>` が、追跡された mode 120000 の symlink である（`<dir>: <path> must be a symlink to <target>`）。最後に `check_skill_links "<dir>/"` を呼ぶ。問題が無ければ `ok: project <dir> layout`。
- `check_resoloop_skills`: `resoloop` が PATH に無ければ `skip: resoloop not found (skills sync check)` を出して通過する。あれば各プロジェクトで `resoloop skills sync <dir> --check` を実行し、失敗したら `resoloop skills sync --check failed for <dir>`、成功なら `ok: resoloop skills sync --check (<dir>)`。

- [ ] **Step 1: 失敗するテストを足す**（`tests/scripts/test-check-layout.bash` の Task 8 のケースの後、最後の `printf 'PASS: ...'` の前）

```bash
# 仕様 4.2 を満たすプロジェクト demo を 1 つ持つリポジトリを作る
project_repo() {
  local r="$1" p="$1/demo"
  new_repo "$r"
  mkdir -p "$r/.claude" "$r/.pi" "$r/.agents" "$p/.agents/skills/resonite-build" "$p/.claude/skills" "$p/.resoloop" "$p/flux"
  printf '{}\n' > "$r/.claude/settings.json"
  printf 'pi\n' > "$r/.pi/APPEND_SYSTEM.md"
  printf -- '---\nname: sp-implementer\n---\n' > "$r/.agents/sp-implementer.md"
  printf '# guide\n\n## このプロジェクト固有\n\n- test\n' > "$p/AGENTS.md"
  printf '@AGENTS.md\n' > "$p/CLAUDE.md"
  printf '{}\n' > "$p/.resoloop.json"
  printf 'state/\nflux-state/\ncache/\n' > "$p/.resoloop/.gitignore"
  printf '[project]\nname = "demo"\n' > "$p/pyproject.toml"
  printf 'version = 1\n' > "$p/uv.lock"
  printf '{}\n' > "$p/.agents/skills/.resoloop-bundled.json"
  printf -- '---\nname: resonite-build\ndescription: d\n---\n' > "$p/.agents/skills/resonite-build/SKILL.md"
  printf '{}\n' > "$p/flux/resoloop.flux.json"
  ln -s ../../.agents/skills/resonite-build "$p/.claude/skills/resonite-build"
  ln -s ../../.claude/settings.json "$p/.claude/settings.json"
  ln -s ../.pi "$p/.pi"
  ln -s ../../.agents/sp-implementer.md "$p/.agents/sp-implementer.md"
  commit_paths "$r" .claude .pi .agents demo
}

# モックの resoloop: MOCK_RESOLOOP_FAIL と同名のプロジェクトだけ skills sync --check に失敗する
mkdir -p "$tmp/mockbin"
cat > "$tmp/mockbin/resoloop" <<'EOF'
#!/bin/bash
[ "$1 $2 $4" = 'skills sync --check' ] || exit 64
case "$3" in "${MOCK_RESOLOOP_FAIL:-__none__}"|*/"${MOCK_RESOLOOP_FAIL:-__none__}") echo 'SKILL_SYNC_REQUIRED' >&2; exit 6 ;; esac
exit 0
EOF
chmod +x "$tmp/mockbin/resoloop"
mock_path="$tmp/mockbin:$PATH"

# 21. 標準レイアウトのプロジェクトは通過し、resoloop があれば同期を確かめる
project_repo "$tmp/proj-ok"
PATH="$mock_path" bash "$checker" --root "$tmp/proj-ok" > "$tmp/proj-ok.out"
grep -qF 'ok: project demo layout' "$tmp/proj-ok.out"
grep -qF 'ok: resoloop skills sync --check (demo)' "$tmp/proj-ok.out"
grep -qF 'PASS: check-layout' "$tmp/proj-ok.out"

# 22. resoloop が無い環境（CI）では skip を表示して通過する
if PATH=/usr/local/bin:/usr/bin:/bin command -v resoloop >/dev/null 2>&1; then
  printf 'FAIL: resoloop visible on the reduced PATH\n' >&2; exit 1
fi
PATH=/usr/local/bin:/usr/bin:/bin bash "$checker" --root "$tmp/proj-ok" > "$tmp/proj-skip.out"
grep -qF 'skip: resoloop not found (skills sync check)' "$tmp/proj-skip.out"
grep -qF 'PASS: check-layout' "$tmp/proj-skip.out"

# 23. resoloop 同梱スキルの同期ずれは失敗する
PATH="$mock_path" MOCK_RESOLOOP_FAIL=demo expect_fail_with "$tmp/proj-ok" 'resoloop skills sync --check failed for demo'

# 24〜30. 標準レイアウトからの逸脱は失敗する（以降は mock の resoloop で実行する）
export PATH="$mock_path"
project_repo "$tmp/p24" && git -C "$tmp/p24" rm -q demo/CLAUDE.md && git -C "$tmp/p24" commit -q -m rm
expect_fail_with "$tmp/p24" 'demo: missing tracked file CLAUDE.md'

project_repo "$tmp/p25" && printf 'other\n' > "$tmp/p25/demo/CLAUDE.md" && commit_paths "$tmp/p25" demo
expect_fail_with "$tmp/p25" 'demo: CLAUDE.md must be exactly @AGENTS.md'

project_repo "$tmp/p26" && printf '# guide\n' > "$tmp/p26/demo/AGENTS.md" && commit_paths "$tmp/p26" demo
expect_fail_with "$tmp/p26" 'demo: AGENTS.md lacks ## このプロジェクト固有'

project_repo "$tmp/p27" && printf 'state/\nflux-state/\n' > "$tmp/p27/demo/.resoloop/.gitignore" && commit_paths "$tmp/p27" demo
expect_fail_with "$tmp/p27" 'demo: .resoloop/.gitignore lacks cache/'

project_repo "$tmp/p28" && rm "$tmp/p28/demo/.pi" && ln -s ../.agents "$tmp/p28/demo/.pi" && commit_paths "$tmp/p28" demo
expect_fail_with "$tmp/p28" 'demo: .pi must be a symlink to ../.pi'

project_repo "$tmp/p29" && git -C "$tmp/p29" rm -q demo/.claude/skills/resonite-build && git -C "$tmp/p29" commit -q -m rm
expect_fail_with "$tmp/p29" 'demo/.claude/skills: missing link resonite-build'

project_repo "$tmp/p30" && git -C "$tmp/p30" rm -q demo/.agents/sp-implementer.md && git -C "$tmp/p30" commit -q -m rm
expect_fail_with "$tmp/p30" 'demo: .agents/sp-implementer.md must be a symlink to ../../.agents/sp-implementer.md'

# 31. .resoloop.json の無いディレクトリはプロジェクトとして扱わない
project_repo "$tmp/p31"
mkdir -p "$tmp/p31/notes" && printf '# notes\n' > "$tmp/p31/notes/AGENTS.md" && commit_paths "$tmp/p31" notes
bash "$checker" --root "$tmp/p31" | grep -qF 'PASS: check-layout'
```

`expect_fail_with` は `bash "$checker" --root "$dir"` を呼ぶので、`PATH=... MOCK_RESOLOOP_FAIL=... expect_fail_with ...` の一時的な環境変数は関数の実行中だけ効く。

Run: `bash tests/scripts/test-check-layout.bash; echo "exit=$?"`
Expected: ケース 21 の `grep -qF 'ok: project demo layout'` が見つからず、メッセージ無しで `exit=1`。

- [ ] **Step 2: check-layout に検査を足す**

呼び出し列の最後（`check_skill_hygiene` の後）に `collect_projects`、各プロジェクトの `check_project`、`check_resoloop_skills` を足す。

```bash
# 6. 各プロジェクト（.resoloop.json を追跡している直下のディレクトリ）が仕様 4.2 の標準レイアウトを満たす
projects=()
collect_projects() {
  local path
  if ! git ls-files -z -- '*/.resoloop.json' > "$tmp_list"; then
    fail "git ls-files failed for */.resoloop.json"
    return
  fi
  while IFS= read -r -d '' path; do
    [[ "$path" =~ ^[^/]+/\.resoloop\.json$ ]] && projects+=("${path%%/*}")
  done < "$tmp_list"
}

check_project() {
  local p="$1" problems=() f link target sp
  for f in AGENTS.md CLAUDE.md .resoloop.json .resoloop/.gitignore pyproject.toml uv.lock \
           .agents/skills/.resoloop-bundled.json flux/resoloop.flux.json; do
    git ls-files --error-unmatch -- "$p/$f" >/dev/null 2>&1 || problems+=("missing tracked file $f")
  done
  [ "$(cat "$p/CLAUDE.md" 2>/dev/null)" = '@AGENTS.md' ] || problems+=("CLAUDE.md must be exactly @AGENTS.md")
  grep -qxF '## このプロジェクト固有' "$p/AGENTS.md" 2>/dev/null || problems+=("AGENTS.md lacks ## このプロジェクト固有")
  grep -qxF 'cache/' "$p/.resoloop/.gitignore" 2>/dev/null || problems+=(".resoloop/.gitignore lacks cache/")
  local links=(".claude/settings.json|../../.claude/settings.json" ".pi|../.pi")
  if ! git ls-files -z -- '.agents/sp-*.md' > "$tmp_list"; then
    fail "git ls-files failed for .agents/sp-*.md"
    return
  fi
  while IFS= read -r -d '' sp; do
    links+=(".agents/${sp##*/}|../../.agents/${sp##*/}")
  done < "$tmp_list"
  for link in "${links[@]}"; do
    f="${link%%|*}" target="${link#*|}"
    if [ "$(git ls-files -s -- "$p/$f" | cut -d' ' -f1)" != 120000 ] || [ "$(readlink "$p/$f" 2>/dev/null)" != "$target" ]; then
      problems+=("$f must be a symlink to $target")
    fi
  done
  if [ ${#problems[@]} -gt 0 ]; then
    local q
    for q in "${problems[@]}"; do fail "$p: $q"; done
  else
    ok "project $p layout"
  fi
  check_skill_links "$p/"
}

# 7. resoloop が使える環境では resoloop skills sync --check が各プロジェクトで成功する
check_resoloop_skills() {
  local p
  if ! command -v resoloop >/dev/null 2>&1; then
    printf 'skip: resoloop not found (skills sync check)\n'
    return
  fi
  for p in ${projects[@]+"${projects[@]}"}; do
    if resoloop skills sync "$p" --check >/dev/null 2>&1; then
      ok "resoloop skills sync --check ($p)"
    else
      fail "resoloop skills sync --check failed for $p"
    fi
  done
}
```

```bash
check_forbidden_tracked
check_symlinks_resolve
check_tracked_ignored
check_skill_links ""
check_skill_hygiene
collect_projects
for p in ${projects[@]+"${projects[@]}"}; do check_project "$p"; done
check_resoloop_skills
```

- [ ] **Step 3: テストを通す**

```bash
bash tests/scripts/test-check-layout.bash      # PASS（ケース 6 で 3 プロジェクトと resoloop の同期も通る）
bash scripts/check-layout.sh                  # ok: project MyResoniteProject / akichi / slum02 layout、ok: resoloop skills sync --check ×3、PASS
```

- [ ] **Step 4: 共通の検査を実行してコミットする**

```bash
git add scripts/check-layout.sh tests/scripts/test-check-layout.bash
git commit -m "feat(layout): check each world project against the standard layout and resoloop skills" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 13: 統合手順にフェーズ 2 の分を追記する（docs/integration.md）

フェーズ 2 で新しく追跡したパスのうち、メイン作業ツリーに未追跡のまま存在するものは、マージや rebase の checkout で「untracked working tree files would be overwritten」として中断の原因になる。事前に退避する手順と、マージ後に不要になる未追跡物の削除手順を書く。

**Files:**
- Modify: `docs/integration.md`

**Interfaces:**
- Consumes: Task 1〜12 のコミット（`chore/repo-redesign`）

- [ ] **Step 1: 衝突するパスを読み取りで数える**

```bash
git -C "$M" ls-tree -r -z --name-only chore/repo-redesign | while IFS= read -r -d '' p; do
  if [ -e "$M/$p" ] || [ -L "$M/$p" ]; then
    git -C "$M" ls-files --error-unmatch -- "$p" >/dev/null 2>&1 || printf '%s\n' "$p"
  fi
done > "$(mktemp -d)/collisions.txt"
```

結果を分類ごとに数える。計画作成時のシミュレーション（Task 1〜12 を複製リポジトリに適用して同じコマンドを実行）では 68 件で、内訳は MyResoniteProject と akichi の resoloop scaffold（`AGENTS.md`、`.resoloop.json`、`.resoloop/.gitignore`、`.agents/skills/.resoloop-bundled.json`、resonite-* スキル、`flux/` の 4 ファイル）、`MyResoniteProject/.agents/sp-implementer.md`、`slum02/.resoloop/.gitignore`、ルート `.claude/skills/` の Blender 系 symlink 10 件と `references`、それにフェーズ 1 で追跡に戻した `.devcontainer/devcontainer-lock.json`（メイン作業ツリーでは未追跡のまま存在する）だった。

- [ ] **Step 2: `docs/integration.md` に節を足す**

「## マージ前にユーザが行うこと」の既存項目の後に項目 2・3 を、「## マージ後にユーザが行うこと（随時追記）」の既存項目の後に項目 5〜7 を足す。本文は次のとおりとし、「2026-09-26 時点の該当」の行は Step 1 の実際の結果（分類と件数）で書く。

```markdown
2. `chore/repo-redesign` が新しく追跡するパスのうち、作業ツリーに未追跡のまま存在するものは、マージや rebase の checkout を中断させる（git は未追跡ファイルを上書きしない）。次のコマンドで一覧を出し、同じ相対パスのまま `~/reso-world-untracked-backup/` へ移してからマージする。
   （Step 1 のコマンドを、`chore/repo-redesign` を `origin/chore/repo-redesign` に、`$M` を `/workspaces/reso-world` に置き換えて載せる）
   2026-09-26 時点の該当: （Step 1 の分類と件数）
3. 退避したファイルは、マージ後に同じパスに入る追跡版と内容を比べてから削除する。`AGENTS.md`（先頭を resoloop preview.14 の文面に揃え、固有節を追加）と `.resoloop/.gitignore`（`cache/` を追加）以外は同一のはず。
```

```markdown
5. 不要になった未追跡物を削除する。`akichi/.agents/skills/` の Blender 系 10 スキルと `references/`・`tests/`（ルートの `.agents/skills/` に移ったため）、`akichi/.claude/skills/` と `MyResoniteProject/.claude/skills/` の Blender 系 symlink、ルート `.claude/skills/` の `resonite-*` の未追跡 symlink（resonite-* はプロジェクト側で読む）、`MyResoniteProject/.agents/sp-*.md` のうち `sp-implementer.md` 以外の 8 件（pi-superagents の組み込み定義と同一のため）。
6. `MyResoniteProject/` で `uv sync` を実行し、`uv run pytest` が通ることを確認する（プロジェクト専用の環境になった）。
7. `bash scripts/check-layout.sh` がすべて `ok` で `PASS: check-layout` になることを確認する。
```

- [ ] **Step 3: コミットする**

```bash
git add docs/integration.md
git commit -m "docs(integration): add the phase 2 steps for untracked scaffold collisions" -m "Co-Authored-By: <モデル名> <noreply@anthropic.com>"
```

---

### Task 14: フェーズ 2 の一括検証と push（controller が実行）

コード変更は無い。controller が実行し、結果を台帳に記録する。

- [ ] **Step 1: 一括検証**

```bash
cd "$W"
git status --short | wc -l                                                     # 0
for t in tests/scripts/*.bash; do bash "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done
                                                                               # 5 件とも PASS（gitignore、check-layout、instructions、agent-config、new-world）
bash scripts/check-layout.sh                                                   # ok: がルート 5 件＋プロジェクトごと 3 件、PASS: check-layout
git ls-files -i -c --exclude-standard                                          # MyResoniteProject/.resoloop/tokyo-nova/pipeline.json だけ
for t in .devcontainer/test-*.bash; do bash "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done
                                                                               # 8 PASS、test-herdr-migration だけ FAIL（既知、フェーズ 4）
uv run pytest -q 2>&1 | tail -n 1                                              # 34 failed（Global Constraints の既知の失敗だけ）
for P in MyResoniteProject akichi slum02; do (cd "$P" && uv run pytest -q 2>&1 | tail -n 1); done
                                                                               # 52 passed / 66 passed / 215 passed
for P in MyResoniteProject akichi slum02; do
  out="$(mktemp)"; (cd "$P" && codex debug prompt-input "hi" > "$out" 2>/dev/null)
  printf '%s root=%s project=%s shared=%s resonite=%s\n' "$P" \
    "$(grep -c 'create-reso-world 共通規約' "$out")" "$(grep -c 'ResoLoop project guide' "$out")" \
    "$(grep -c 'agent-handoff/SKILL.md' "$out")" "$(grep -c 'resonite-build/SKILL.md' "$out")"
done                                                                           # 各行の 4 つの値がすべて 1 以上
(cd slum02 && devin skills list 2>&1) | grep -E '/(claude|devin|agents):' || echo 'no prefixed duplicates'
git log --oneline main..HEAD | wc -l                                           # 28（フェーズ 1 までの 14 ＋計画書 1 ＋Task 1〜13 の 13）
git -C "$M" status --short | grep -c '^?? private/'                             # 0
```

Expected は各行のコメントのとおり。`main..HEAD` の件数は fix round のコミットがあれば増える（台帳に記録する）。

- [ ] **Step 2: push**

```bash
git -C "$W" fetch origin
git -C "$W" merge-base --is-ancestor origin/chore/repo-redesign HEAD && git -C "$W" push origin chore/repo-redesign
git -C "$M" ls-remote --heads origin                                            # 5 本、chore/repo-redesign が HEAD と一致
```

- [ ] **Step 3: ブランチ全体の最終レビューと handoff**

最上位モデルのレビュアーに `MERGE_BASE..HEAD`（`MERGE_BASE` は `2dfeaaf`）のレビューを依頼し、指摘は fix wave で直す。完了後、台帳の最後に `PHASE 2 COMPLETE.` を書き、区切りとして agent-handoff で引き継ぎ書を作る。

---

## 持ち越し（フェーズ 3〜6）

前回の引き継ぎ書と本計画で見つかった保留事項。本計画では着手しない。

| ID | フェーズ | 内容 |
| --- | --- | --- |
| P-4 | 4 | テストの git 設定の隔離で `safe.directory` も外れる。CI では `GIT_CONFIG_COUNT=2`、`GIT_CONFIG_KEY_1=safe.directory`、`GIT_CONFIG_VALUE_1="$root"` を足す。本計画で増えた `test-new-world.bash` も同じ隔離を使う |
| N-1 | 4 | CI で `tests/scripts/*.bash`（test-gitignore、test-check-layout、test-instructions、test-agent-config、test-new-world）も実行する |
| N-6 | 4 | `.claude/settings.json` のプラグイン一覧を Dev Container の導入一覧と合わせる（仕様 7.1） |
| N-5 | 3 | ルート `AGENTS.md` が参照する `.devcontainer/resoloop.lock`、`scripts/resoloop-fork.sh`、`docs/resoloop-fork-workflow.md` を作る |
| N-7 | 3 | check-layout に仕様 9.1 のロック検査（`.devcontainer/resoloop.lock` の必須キー、`RESOLOOP_FORK_SDK` が `devcontainer.json` の `additionalVersions` に含まれる）を足す |
| N-8 | 4 | check-layout に仕様 9.1 のマウント検査（`initialize.bash` の mkdir 集合と `devcontainer.json` の mounts 集合の一致）を足す |
| N-2 | 5 | 統合したスキルに残る maatlog・`public/`・`verify.sh`・`docs_draft/superpowers/` の記述の書き直し（仕様 8.2）。repository-ownership の削除（スキル、テスト、`.cursor/rules/repository-ownership.mdc`、`.claude/skills/repository-ownership` の symlink）。pi-model-name の 27 件の失敗 |
| N-3 | 6 | README に書くこと: Codex は信頼済みのときだけ `.codex/config.toml` を読む、cursor-agent は初回に MCP の承認が要る、Devin は symlink 経由の同名スキルを 1 回だけ表示する（`.devin/config.json` は不要）、Cursor と dsh のスキル可視性の制約、pi-superagents の組み込み定義は追跡しない（判断事項 D-1） |
| N-4 | 6 | マージ直前に Task 13 の衝突一覧を再実行し、`docs/integration.md` の件数を最新にする |
| P-1 | 6 | `docs/integration.md` と仕様 10.1 の退避手順に `git checkout -- .claude/settings.local.json` を足し、CLAUDE.md / APPEND_SYSTEM.md の破棄を「マージ前」節へ移す |
| P-2 | 6 | `.git/info/exclude` の `/private/` の行は、tokyo-nova 系ブランチを新しい main に rebase した後に消す |
| P-3 | 6 | フェーズ 0・1 の計画書 380 行目の注記の誤りと、830 行目の integration.md ひな形の古い文面を直す |
| P-7 | 6 | 仕様 4.4 の `/tmp/`・`**/tmp/`・`/docs_draft/`・`**/docs_draft/` の表記を実際の `tmp/`・`docs_draft/` に揃える |
| M-5 | 6 | main の再 fast-forward は `git fetch . feat/slum02-slum:main` で行う |
