# create-reso-world 再設計 フェーズ 6（仕上げと PR）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ルートの README を置き、統合手順（`docs/integration.md`）と仕様書・過去の計画書・運用文書の表記を実装に揃えたうえで、最新の `feat/slum02-slum` を取り込み、`main` 宛ての PR を 1 本開く。

**Architecture:** 文書の変更は 1 つの Task にまとめ、`tests/scripts/test-docs.bash` が README の節と案内先の実在、統合手順の要点、仕様書などの表記を検査する（`.devcontainer/run-tests.bash` と CI の devcontainer-tests が実行する）。PR までの操作（検証、最終レビュー、`feat/slum02-slum` の取り込み、`main` の fast-forward、push、PR の作成）は controller が行う。

**Tech Stack:** Markdown、bash（`set -euo pipefail`）、git、gh

**Spec:** `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md`（4.1 節の README、5.1 節、9.3 節、10 章のフェーズ 6、10.1 節、11 章）。前フェーズの計画は `docs/superpowers/plans/2026-09-27-redesign-phase5-skill-rewrites.md`。

## 判断事項（2026-09-27、controller の裁定）

2026-09-27 のユーザの指示「PR を出すまで止めないでください」により、本計画も controller の裁定で承認して実行する（フェーズ 4 の D-9）。文書の変更は scratchpad の複製（フェーズ 5 の全 Task を当てた tree）で試作し、テストが変更前に失敗し、変更後に通ることと、ミューテーション（文書ごとに元へ戻すとテストが失敗する）を確かめた。

| ID | 事項 | 本計画の内容 | 理由 |
| --- | --- | --- | --- |
| D-32 | 最新の `feat/slum02-slum` の取り込み（仕様 10.1 の 1） | rebase ではなく、`chore/repo-redesign` へのマージ（マージコミット）で取り込む。`main` は `git fetch . feat/slum02-slum:main` で fast-forward してから push する（M-5） | `chore/repo-redesign` は push 済みで、force push をしない（引き継ぎ書の禁止事項）。仕様 10.1 の 1 と統合手順にこの置き換えを明記する |
| D-33 | fork の checkout に残る `reviews/`（N-28） | スクリプトは変えない。pr-review が `external/resoloop/reviews/` に保存するレビューは未追跡のまま残り、`scripts/resoloop-fork.sh` の未コミットの変更の判定（未追跡を数えない）にも影響しない | fork の `.git/info/exclude` を書き換えると、利用者の checkout の設定を黙って変える。実害が無い |
| D-34 | rst-writer の OSS profile（N-29） | フェーズ 5 の D-28 のとおり、未接続の予約として残す | 使う見込みの判断は利用者に任せる。削除は後からでもできる |
| D-35 | `.git/info/exclude` の `/private/`（P-2） | エージェントは消さない。統合手順の「マージ後」に、tokyo-nova 系のブランチを新しい `main` に rebase した後に消すと書く | `.git` は全 worktree で共有され、メイン作業ツリーの見え方を変える。古い `.gitignore` のままのブランチで TRPG 本文を隠すために、それまでは要る |
| D-36 | GitHub Actions の確認（N-27） | アカウントの課金の設定によりジョブが開始されないため、PR の時点では GitHub 上の CI を確かめられない。手元で CI と同じコマンドを、CI 相当の PATH で実行し、Action の参照の実在（`git ls-remote`）と gitleaks（8.30.1、Action と同じ引数）を確かめて代わりとする。PR の説明と統合手順に明記する | 課金の設定は利用者のアカウントの操作で、エージェントは変えない |
| D-37 | フェーズ 4・5 で据え置いた Minor | 本計画では直さない。「持ち越し」節に一覧を残し、PR の説明にも載せる | それぞれの最終レビューが「マージ前に直す必要は無い」と判断した |

## Global Constraints

- 変数: `M=/workspaces/reso-world`（メイン作業ツリー。ブランチ feat/slum02-slum で、別セッションが slum02 を編集中）、`W=/workspaces/reso-world/.worktrees/repo-redesign`（作業用 worktree。ブランチ chore/repo-redesign）。各ステップのコマンドは `export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign` を実行してから、特記が無ければ `cd "$W"` で実行する。
- メイン作業ツリー `$M` では読み取りだけを行う。追跡ファイルの編集、`git add` / `commit` / `checkout` / `stash` / `reset` / `clean` / `fetch`、ファイルの移動・削除をしない。
- 変更のコミットはすべて `$W` で行う。コミットメッセージの末尾に、コミットするエージェント自身のモデル名の trailer を付ける（例: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`）。
- `git add` には明示したパスだけを渡す。`$W` で `git add -A` / `git add .` を使わない。
- `git push --force` 系を使わない。push は Task 2 で controller が、fast-forward を確かめてから `git push origin chore/repo-redesign` と `git push origin main` だけ行う。`feat/*`・`wip/*` を push・rebase・削除しない。PR は Task 2 で 1 本だけ開く。
- Python は uv で実行する。説明・文書・コミットの日本語で「契約」「原子的」「製品」「着地」を使わない（ルール本文を引用する `AGENTS.md` の「日本語表現」節を除く）。
- 触らないもの: TRPG 本文、`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json`、`.pi/APPEND_SYSTEM.md` の `## Response Persona` 以降、`.git/info/exclude`、スキル、`.devcontainer/`、`scripts/`。
- **実環境を変えるコマンドを実行しない**（`install_beforehand.bash`、`dotnet tool install|update`、実ロックに対する `scripts/resoloop-fork.sh sync|build|test|install`、実際の `HOME` での `initialize.bash`）。
- 各 Task の後に次が通る: `bash .devcontainer/run-tests.bash | tail -n 1`（Task 1 の後は `PASS: 24 test(s)`）、`uv run pytest -q tests/skills .agents/skills 2>&1 | tail -n 1`（失敗 0 件。フェーズ 5 の終了時点で `passed` と `1 skipped` だけが表示される）、`bash scripts/check-layout.sh | tail -n 1`（`PASS: check-layout`）、`git ls-files -i -c --exclude-standard`（`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json` の 1 行だけ）。
- 差分は `git diff` の形式で載せてある。`git apply` で当ててよい。新しいファイルは全文を載せてある。

## Review Focus

- 統合手順をそのまま実行する利用者: マージの前に片付ける未コミットの変更（`.claude/settings.local.json`、`CLAUDE.md`、`.pi/APPEND_SYSTEM.md`）と、退避する未追跡ファイルの一覧で、マージが止まらない。手順 1〜3 を同じシェルで続けて実行できる（Task 1 のケース 4）。
- README だけを読んだ新しい利用者: 案内されたファイルや節が実在し、エージェントの初回の操作（Codex の trust、cursor-agent の MCP の承認）が分かる（Task 1 のケース 2・3）。
- Rebuild の後の確認: 仕様 9.3 と持ち越しの N-17・N-18・N-25・N-27 の項目が統合手順にそろっている（Task 1 のケース 4）。
- PR の時点の `feat/slum02-slum`: 別セッションが進めたコミットを取り込んでも、全検証が通る（Task 2 の手順 4）。

## 実行前の準備（controller）

- [ ] 1. フェーズ 5 が完了し（台帳の末尾が `PHASE 5 COMPLETE.`）、worktree がクリーンであることを確かめる。フェーズ 5 の修正ラウンドで本計画の対象ファイルが変わった場合は、`git apply --check` で差分が当たるかを確かめる。
- [ ] 2. 本計画書をコミットする（`docs: add redesign phase 6 implementation plan`）。
- [ ] 3. SDD の作業ディレクトリと台帳を作る。フェーズ 4 と 5 の SDD 作業ディレクトリは、据え置きの一覧を本計画の「持ち越し」節に転記したことを確かめてから削除する。

---

### Task 1: ルートの README と文書の整合（仕様 4.1・9.3・10.1、持ち越し N-3・N-4・N-12・N-17・N-18・N-24・N-25・N-27・P-1〜P-3・P-7・M-5）

ルートに README.md を置く。`docs/integration.md` に、PR の前に行うこと、マージ前の片付け（P-1）、一覧の件数の更新（N-4）、sp-implementer.md の比較先と同じシェルでの実行（N-12）、`/private/` の行を消す時期（P-2）、Rebuild 後の確認（N-17・N-18・N-25・N-27）を足す。仕様書の 4.4・6.4・7.2・9.1・9.2・9.3・10.1、運用文書の環境変数の説明、フェーズ 0・1 の計画書の 2 か所（P-3）を実装に揃える。

**Files:**
- Create: `README.md`、`tests/scripts/test-docs.bash`（mode 100755）
- Modify: `docs/integration.md`、`docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md`、`docs/resoloop-fork-workflow.md`、`docs/superpowers/plans/2026-09-26-redesign-phase0-1-safety-and-hygiene.md`

**Interfaces:**
- Produces: `tests/scripts/test-docs.bash`（`.devcontainer/run-tests.bash` の対象が 24 本になる）。Task 2 は統合手順の「2026-09-27 時点の該当: 68 件」を PR の直前に確かめる。

- [ ] **Step 1: 失敗するテストを書く**

`tests/scripts/test-docs.bash` を次の内容で作り、`chmod +x` する。

```bash
#!/bin/bash
# ルートの README.md と統合手順（docs/integration.md）が仕様 4.1・5.1・9.3・10.1 と持ち越しの N-3・N-4・N-12・N-17・N-18・N-24・N-25・P-1〜P-3・P-7 のとおりで、
# 書いてあるファイルや節が実在することを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
has() { grep -qF -- "$2" "$1" || fail "$1 lacks: $2"; }
lacks() { if grep -qF -- "$2" "$1"; then fail "$1 must not contain: $2"; fi; }

# 1. README.md: 仕様 4.1 の内容（目的、Dev Container の起動、プロジェクトの作成、ResoLoop の版、変更の流れ）とテストの節がある
[ "$(head -n 1 README.md)" = '# create-reso-world' ] || fail 'README.md title'
expected='## 構成
## Dev Container を起動する
## エージェントで作業する
## プロジェクトを作る
## ResoLoop の版
## 変更の流れ
## テスト
## 対象外'
[ "$(grep -E '^## ' README.md)" = "$expected" ] || fail "README.md sections differ:
$(grep -E '^## ' README.md)"

# 2. README.md が案内するファイルは実在する
for f in AGENTS.md CLAUDE.md .agents/skills .devcontainer/README.md .devcontainer/install_beforehand.bash \
  .devcontainer/verify-resonite-tooling.bash .devcontainer/resoloop.lock .devcontainer/run-tests.bash \
  scripts/new-world.sh scripts/resoloop-fork.sh scripts/check-layout.sh templates/world-project \
  docs/resoloop-fork-workflow.md docs/integration.md .github/workflows/ci.yml .codex/config.toml .cursor/mcp.json \
  .agents/sp-implementer.md; do
  has README.md "$f"
  [ -e "$f" ] || fail "README.md refers to missing $f"
done
# .devcontainer/README.md の節への案内は、その節が実在する
for section in 秘密情報 エージェントの読み込みの制約; do
  has README.md "「$section」"
  grep -qxF "## $section" .devcontainer/README.md || fail ".devcontainer/README.md lacks ## $section"
done

# 3. N-3: エージェントごとに初回に要る操作と制約
for s in 'trust' 'cursor-agent' '.devin/config.json' 'sp-*.md' 'Cursor と dsh'; do has README.md "$s"; done
lacks README.md 'maatlog'

# 4. 統合手順: マージ前の片付け（P-1）、一覧の件数（N-4）、sp-implementer.md の比較先と同じシェル（N-12）、
#    main の再 ff（M-5）、/private/ の行を消す時期（P-2）、Rebuild 後の確認（N-17・N-18・N-25・N-27）
doc=docs/integration.md
before_merge="$(sed -n '/^## マージ前にユーザが行うこと$/,/^## マージ後にユーザが行うこと$/p' "$doc")"
for s in 'git checkout -- .claude/settings.local.json' 'git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md' \
  '同じシェル' 'ルートの `.agents/sp-implementer.md` と比べる' '2026-09-27 時点の該当: 68 件'; do
  grep -qF -- "$s" <<<"$before_merge" || fail "the pre-merge section of $doc lacks: $s"
done
for s in 'git fetch . feat/slum02-slum:main' 'マージに置き換えた' '## Rebuild 後に確かめること（仕様 9.3）' \
  'dotnet --list-sdks' '/home/vscode/.local/bin' '~/.config/create-reso-world' 'simplify-in-subagent' \
  'GitHub Actions' 'resoloop-fork.sh sync' 'wip/tokyo-nova-refinement` を新しい `main` に rebase した後'; do
  has "$doc" "$s"
done
lacks "$doc" '随時追記'
lacks "$doc" 'Task 14'

# 5. 仕様・運用文書・フェーズ 0・1 の計画書の表記（P-3・P-7・N-24）
spec=docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md
lacks "$spec" '`**/tmp/`'
lacks "$spec" '`.agents/skills/*/SKILL.md` ごとに'
has "$spec" 'git fetch . feat/slum02-slum:main'
has "$spec" 'フェーズ 4 の D-10'
has "$spec" '`install` の `checkout` は origin にあるコミットしか取り出せない'
has docs/resoloop-fork-workflow.md 'テストと特殊な運用向け'
lacks docs/resoloop-fork-workflow.md '主にテスト用'
phase01=docs/superpowers/plans/2026-09-26-redesign-phase0-1-safety-and-hygiene.md
lacks "$phase01" '`**/` 前置に修正された'
lacks "$phase01" '追跡解除後もローカルファイルとして残る'

printf 'PASS: README and integration docs follow spec 4.1 and 10.1\n'
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && bash tests/scripts/test-docs.bash; echo "exit=$?"
```

Expected: `head: cannot open 'README.md'` と `FAIL: README.md title` で終了コード 1。

- [ ] **Step 3: README を作る**

`README.md` を次の内容で作る。

````markdown
# create-reso-world

[resoloop](https://github.com/orange3134/resoloop) と Blender で Resonite のワールドを作るための開発環境（Dev Container）と、
ワールドのプロジェクトをまとめたリポジトリ。コーディングエージェント（Claude Code、Codex、pi、Cursor、Devin、dsh）で
作業する前提で、共通の規約とスキルをリポジトリに置いている。

## 構成

```
.
├── AGENTS.md                  共通規約の正本（CLAUDE.md は @AGENTS.md を読み込む）
├── .agents/skills/            共有スキルの正本（.claude/skills/ はここへの symlink）
├── .devcontainer/             Dev Container の設定、導入スクリプト、テスト（詳細は .devcontainer/README.md）
├── scripts/                   new-world.sh（プロジェクトの作成）、resoloop-fork.sh（fork の運用）、check-layout.sh（レイアウト検査）
├── templates/world-project/   プロジェクトの雛形
├── docs/                      設計と計画（docs/superpowers/）、fork の運用、統合手順
├── tests/                     スクリプトのテスト（tests/scripts/）とスキルのテスト（tests/skills/）
└── MyResoniteProject/ akichi/ slum02/   ワールドのプロジェクト（resoloop のプロジェクト）
```

## Dev Container を起動する

1. ホスト側に秘密情報の置き場を用意する（任意）。手順は `.devcontainer/README.md` の「秘密情報」にある。
2. VS Code の Dev Containers: Reopen in Container で開く。`initializeCommand` がホスト側に mount のソースを作り、
   `postCreateCommand`（`.devcontainer/install_beforehand.bash`）が各エージェントの CLI、uv、Blender、ResoLoop などを導入する。
   ResoLoop は `.devcontainer/resoloop.lock` が指定する fork をビルドするため、ネットワークと数分の時間を要する。
3. 導入を確かめる。

   ```bash
   bash .devcontainer/verify-resonite-tooling.bash
   bash scripts/resoloop-fork.sh status
   ```

コンテナの resoloop から Windows ホストの ResoniteLink に届くことが前提である（WSL2 の mirrored networking など）。
導入するツールの一覧、mount、ResoniteLink への接続は `.devcontainer/README.md` にまとめてある。

## エージェントで作業する

エージェントは、作業するプロジェクト（例: `slum02/`）を cwd にして起動する。共通の規約はルートの `AGENTS.md`、
プロジェクト固有の規約はプロジェクトの `AGENTS.md` にあり、どちらも読み込まれる。

初回や設定の変更後に、次の操作が要る。

- Codex: プロジェクトを信頼（trust）すると、`.codex/config.toml` の MCP の設定（context7）が読まれる。初回の起動時に承認する。
- cursor-agent: `.cursor/mcp.json` の MCP サーバーは、初回に承認を求められる。
- Devin: `.claude/skills` の symlink 経由で同じスキルが見えても、一覧には 1 回だけ表示される（`.devin/config.json` は置かない）。
- Cursor と dsh: スキルの一部が見えない。詳細は `.devcontainer/README.md` の「エージェントの読み込みの制約」。
- pi-superagents: 組み込みと同じ定義（`sp-*.md`）は追跡しない。独自に変えた `.agents/sp-implementer.md` だけを追跡する。

## プロジェクトを作る

```bash
bash scripts/new-world.sh <name>            # resoloop init の後に雛形（CLAUDE.md、pyproject.toml、symlink など）を適用する
bash scripts/new-world.sh --apply <name>    # 既存のプロジェクトに、雛形の足りない分だけを適用する
```

既存のファイルは上書きせず、食い違いがあれば報告して止まる。プロジェクトのテストは、そのディレクトリで `uv run pytest` を実行する。

## ResoLoop の版

導入する ResoLoop の版は `.devcontainer/resoloop.lock` で決める。既定は fork モードで、Blender 5 の UV の修正を含む
fork（usaturn/resoloop）をビルドして導入する。上流（orange3134/resoloop）がリリースしたら nuget モードに戻す。
fork の checkout は `external/resoloop`（git の追跡対象外）に置く。版の変え方、fork の修正と上流への PR の流れは
`docs/resoloop-fork-workflow.md` にある。

## 変更の流れ

- 変更は作業ブランチで行い、`main` へは PR で入れる。並行作業には `.worktrees/` 配下の worktree を使う（git の追跡対象外）。
- PR を出す前に、下の「テスト」をすべて通す。CI（`.github/workflows/ci.yml`）も push と PR のたびに同じ検査を行う。
- 設計と実装計画は `docs/superpowers/` に置く。ローカルの下書きは `docs_draft/`（git の追跡対象外）に置く。

## テスト

```bash
bash .devcontainer/run-tests.bash          # Dev Container とスクリプトのテスト
bash scripts/check-layout.sh               # リポジトリのレイアウト
uv run pytest tests/skills .agents/skills  # スキルのテスト
(cd slum02 && uv run pytest)               # 各プロジェクトのテスト
```

## 対象外

リポジトリの公開と LICENSE の選定、Git LFS、flux-sdk の導入、Rebuild を伴う確認の自動化は対象外である。
Rebuild 後の確認は、ユーザが `docs/integration.md` の手順で行う。
````

- [ ] **Step 4: 統合手順・仕様書・運用文書・フェーズ 0・1 の計画書を直す**

````diff
diff --git a/docs/integration.md b/docs/integration.md
index 0697408..6229f17 100644
--- a/docs/integration.md
+++ b/docs/integration.md
@@ -1,6 +1,6 @@
 # 再設計の統合手順
 
-仕様: `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md` 10.1 節。フェーズ 6 で完成させる。ここには各フェーズで実施した「メイン作業ツリー側の操作」と、マージ後に必要な手順を積み上げる。
+仕様: `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md` 10.1 節。各フェーズで実施した「メイン作業ツリー側の操作」、PR を出す前に行ったこと、マージの前後にユーザが行うこと、Rebuild 後の確認をまとめる。
 
 ## フェーズ 0 で実施したこと
 
@@ -14,10 +14,20 @@
 - `.git/info/exclude` から存在しない `.devin/mcp_config.local.json` の行を外した（同じ規則はルート `.gitignore` に移した）。
 - `.git/info/exclude`（全 worktree 共通）に `/private/` を暫定追加した。マージ後はルート `.gitignore` が同じ規則を持つので、この行は削除してよい。
 
+## PR を出す前に行ったこと（フェーズ 6）
+
+1. `chore/repo-redesign` に、その時点の `feat/slum02-slum` をマージした（マージコミット）。仕様 10.1 は rebase としていたが、`chore/repo-redesign` は push 済みで force push をしないため、マージに置き換えた（フェーズ 6 の判断事項）。
+2. `main` を `feat/slum02-slum` の HEAD へ fast-forward し（`git fetch . feat/slum02-slum:main`）、`main` と `chore/repo-redesign` を push してから、`main` 宛ての PR を 1 本だけ開いた。
+3. 下の「マージ前にユーザが行うこと」の手順 2 の一覧を PR の直前に作り直し、件数を更新した。
+
 ## マージ前にユーザが行うこと
 
-1. 作業ツリー（`/workspaces/reso-world`）の `.claude/settings.local.json` は `feat/slum02-slum` で追跡されており、未コミットの変更が乗っている。`chore/repo-redesign` はこのファイルを index から削除するため、マージ・rebase の前に `cp /workspaces/reso-world/.claude/settings.local.json ~/settings.local.json.bak` などで退避し、マージ後に元の場所へ戻す（マージ後は ignore 対象になるので再追跡されない）。`feat/tokyo-nova-world` と `wip/tokyo-nova-refinement` も同じファイルを追跡しているため、これらを新しい `main` に rebase するときも同様の退避が必要。
-2. `chore/repo-redesign` が新しく追跡するパスのうち、作業ツリーに未追跡のまま存在するものは、マージや rebase の checkout を中断させる（git は未追跡ファイルを上書きしない）。まず一覧を NUL 区切りでファイルに書き出して確認する。`origin/chore/repo-redesign` をまだ取得していない場合は、先に `git fetch origin` を実行する（Task 14 で push 済みならこれで参照できる）。
+手順 1〜3 は同じシェルで続けて実行する（手順 2 の `list` 変数を手順 3 まで使う）。
+
+1. 作業ツリー（`/workspaces/reso-world`）の未コミットの変更のうち、マージで上書きされるものを片付ける。
+   - `.claude/settings.local.json` は `feat/slum02-slum` で追跡されており、未コミットの変更が乗っている。`chore/repo-redesign` はこのファイルを index から削除するため、`cp /workspaces/reso-world/.claude/settings.local.json ~/settings.local.json.bak` で退避してから `git checkout -- .claude/settings.local.json` で変更を戻す。マージ後に退避した内容を元の場所へ戻す（マージ後は ignore 対象になるので再追跡されない）。`feat/tokyo-nova-world` と `wip/tokyo-nova-refinement` も同じファイルを追跡しているため、これらを新しい `main` に rebase するときも同様の退避が必要。
+   - `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` の未コミット変更は、フェーズ 2 で新設計（`AGENTS.md` と新しい `.pi/APPEND_SYSTEM.md`）に取り込み済みであることを確認したうえで、`git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md` で破棄する。どちらもマージで変わるため、変更が残っているとマージが止まる。
+2. `chore/repo-redesign` が新しく追跡するパスのうち、作業ツリーに未追跡のまま存在するものは、マージや rebase の checkout を中断させる（git は未追跡ファイルを上書きしない）。まず一覧を NUL 区切りでファイルに書き出して確認する。`origin/chore/repo-redesign` を最新にするため、先に `git fetch origin` を実行する。
 
    ```bash
    cd /workspaces/reso-world
@@ -51,22 +61,34 @@
    done
    ```
 
-   2026-09-26 時点の該当: 68 件。内訳は次のとおり。
+   2026-09-27 時点の該当: 68 件（2026-09-26 と同じ）。内訳は次のとおり。
    - MyResoniteProject と akichi の resoloop scaffold（各 27 件、計 54 件）: `AGENTS.md`、`.resoloop.json`、`.resoloop/.gitignore`、`.agents/skills/.resoloop-bundled.json`、resonite-blender/resonite-build/resonite-debug/resonite-flux/resonite-inspect/resonite-uix の `SKILL.md` 6 件、resonite-uix の `recipes/` 配下 8 件と `references/` 配下 5 件、`flux/` 配下 4 ファイル（`.gitignore`、`Main.pg`、`protograph.toml`、`resoloop.flux.json`）
    - `MyResoniteProject/.agents/sp-implementer.md`: 1 件
    - `slum02/.resoloop/.gitignore`: 1 件
    - ルート `.claude/skills/` の Blender 系 symlink 10 件（blender-modeler、brutalist-mood、dark-gritty-mood、geometry-nodes、hard-surface、horror-style、procedural-modeling、prop-artist、sci-fi-punk-worlds、uv-workflow）と `references`: 計 11 件
    - `.devcontainer/devcontainer-lock.json`: 1 件
-3. `~/reso-world-untracked-backup/` へ退避したファイルは、マージ後に同じパスに入る追跡版と内容を比べてから削除する。`AGENTS.md`（先頭を resoloop preview.14 の文面に揃え、固有節を追加）と `.resoloop/.gitignore`（`cache/` を追加）以外は同一のはず。
+3. `~/reso-world-untracked-backup/` へ退避したファイルは、マージ後に同じパスに入る追跡版と内容を比べてから削除する。`AGENTS.md`（先頭を resoloop preview.14 の文面に揃え、固有節を追加。仕様 4.2）と `.resoloop/.gitignore`（`cache/` を追加。仕様 4.3）以外は同一のはず。`MyResoniteProject/.agents/sp-implementer.md` はブランチでは `../../.agents/sp-implementer.md` への symlink なので、退避した実ファイルはルートの `.agents/sp-implementer.md` と比べる。
 
-## マージ後にユーザが行うこと（随時追記）
+## マージ後にユーザが行うこと
 
-1. `git -C /workspaces/reso-world fetch origin` の後、`feat/slum02-slum` を `origin/main` に rebase するか ff-merge する。
-2. `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` の未コミット変更は、フェーズ 2 で新設計に取り込み済みであることを確認したうえで `git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md` で破棄する。`.claude/settings.local.json` は「マージ前にユーザが行うこと」で退避した内容を元の場所へ戻す。
+1. `git -C /workspaces/reso-world fetch origin` の後、`feat/slum02-slum` を `origin/main` に追従させる。PR の後に `feat/slum02-slum` へコミットしていなければ `git merge --ff-only origin/main` で済む。コミットしていれば rebase するかマージする。
+2. `.claude/settings.local.json` は「マージ前にユーザが行うこと」で退避した内容を元の場所へ戻す。
 3. `MyResoniteProject/modeling/tokyo_nova/layout.py.orig` は新しい `.gitignore` で見えなくなる。不要なら削除する。
-4. `.git/info/exclude` に暫定追加した `/private/` の行を削除する（ルート `.gitignore` の `/private/` 規則に置き換わる）。
-5. 不要になった未追跡物を削除する。`akichi/.agents/skills/` の Blender 系 10 スキルと `references/`・`tests/`（ルートの `.agents/skills/` に移ったため）、`akichi/.claude/skills/` と `MyResoniteProject/.claude/skills/` の Blender 系 symlink、ルート `.claude/skills/` の `resonite-*` の未追跡 symlink（resonite-* はプロジェクト側で読む）、`MyResoniteProject/.agents/sp-*.md` のうち `sp-implementer.md` 以外の 8 件（pi-superagents の組み込み定義と同一のため）。
+4. `.git/info/exclude` に暫定追加した `/private/` の行は、`feat/tokyo-nova-world` と `wip/tokyo-nova-refinement` を新しい `main` に rebase した後に削除する（ルート `.gitignore` の `/private/` 規則に置き換わる）。それまでは、古い `.gitignore` のままのブランチで TRPG 本文を見えなくするために要る。
+5. 不要になった未追跡物を削除する（どれも追跡している正本が別の場所にある。仕様 4.2 と 5.1）。`akichi/.agents/skills/` の Blender 系 10 スキルと `references/`・`tests/`（ルートの `.agents/skills/` に移ったため）、`akichi/.claude/skills/` と `MyResoniteProject/.claude/skills/` の Blender 系 symlink、ルート `.claude/skills/` の `resonite-*` の未追跡 symlink（resonite-* はプロジェクト側で読む）、`MyResoniteProject/.agents/sp-*.md` のうち `sp-implementer.md` 以外の 8 件（pi-superagents の組み込み定義と同一のため）。
 6. `MyResoniteProject/` で `uv sync` を実行し、`uv run pytest` が通ることを確認する（プロジェクト専用の環境になった）。
 7. `bash scripts/check-layout.sh` がすべて `ok` で `PASS: check-layout` になることを確認する。
 8. （任意）Rebuild の前に `tmp/resoloop-blender5-uv-20260925` を `external/resoloop` へ移すと、postCreate の clone を省ける。手順は `docs/resoloop-fork-workflow.md` の「`tmp/` にある旧 checkout の整理」にある。
 9. Rebuild の postCreate は `.devcontainer/resoloop.lock` の fork をビルドして導入する（ネットワークと数分を要する）。終わったら `bash scripts/resoloop-fork.sh status` で、導入済みの版と checkout がロックと一致することを確認する。`tmp/` の残りの旧 checkout は同じ節の手順で整理する。
+
+## Rebuild 後に確かめること（仕様 9.3）
+
+Dev Containers: Rebuild Container を実行した後、コンテナの中で次を確かめる。
+
+1. `bash .devcontainer/verify-resonite-tooling.bash` が 0 で終わる。`dotnet --list-sdks` に `10.0.201` がある。
+2. postCreate の fork のビルドと導入が通っている: `bash scripts/resoloop-fork.sh status` で導入済みの版と checkout がロックと一致し、`resoloop --version` がロックの `RESOLOOP_FORK_PACKAGE_VERSION` を返す。fork へ push する `bash scripts/resoloop-fork.sh sync` を初めて使うときは、GitHub への push の認証が通ることを確かめる。
+3. VS Code のターミナルと、エージェントが起動するプロセスの PATH に `/home/vscode/.local/bin`・`/home/vscode/bin`・`/home/vscode/.dotnet/tools` がある（`remoteEnv.PATH`）。
+4. ホストに `~/.config/create-reso-world` が mode 700 で作られ、コンテナに mount されている。`env` を置いた場合は、新しいシェルでその変数が export されている。
+5. `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash`、各プロジェクトの `uv run pytest` が通る。
+6. Devin で simplify-in-subagent を呼んだとき、サブエージェントが edit と exec のツールを持つ。
+7. GitHub Actions の CI（devcontainer-tests、layout、skill-tests、gitleaks）がすべて成功する。PR の時点では、アカウントの課金の設定によりジョブが開始されず、GitHub 上では確かめられていない。
diff --git a/docs/resoloop-fork-workflow.md b/docs/resoloop-fork-workflow.md
index 6bce866..084c209 100644
--- a/docs/resoloop-fork-workflow.md
+++ b/docs/resoloop-fork-workflow.md
@@ -51,7 +51,7 @@ fork の checkout は `external/resoloop`（ルートの `.gitignore` で無視
 
 終了コード: 0 成功、1 状態が期待と違う（git の checkout でない、remote の食い違い、未コミットの変更、コミットが `origin` に無い、fork の `main` が上流から分岐、導入後の版の不一致など）、2 使い方の誤り、3 前提不足（ロックの欠落・不正、git / dotnet が無い、SDK が無い、checkout が無い）、4 git や dotnet のコマンドの失敗。
 
-環境変数 `RESOLOOP_LOCK_FILE`（ロックファイル）と `RESOLOOP_FORK_CHECKOUT`（checkout の位置）で既定の場所を差し替えられる。主にテスト用。
+環境変数 `RESOLOOP_LOCK_FILE`（ロックファイル）と `RESOLOOP_FORK_CHECKOUT`（checkout の位置）で既定の場所を差し替えられる。テストと特殊な運用向け。
 
 ## 状態を確かめる
 
diff --git a/docs/superpowers/plans/2026-09-26-redesign-phase0-1-safety-and-hygiene.md b/docs/superpowers/plans/2026-09-26-redesign-phase0-1-safety-and-hygiene.md
index 45fa0d8..331e944 100644
--- a/docs/superpowers/plans/2026-09-26-redesign-phase0-1-safety-and-hygiene.md
+++ b/docs/superpowers/plans/2026-09-26-redesign-phase0-1-safety-and-hygiene.md
@@ -377,7 +377,7 @@ docs_draft/
 node_modules/
 ```
 
-（実装後の最終レビューで `**/` 前置に修正された。理由は仕様 4.4 を参照。）
+（この節の `tmp/` と `docs_draft/` は実装後の最終レビューを受けた書き方で、末尾だけに `/` があるのでどの階層にも一致する。`**/` の前置は、途中に `/` を含むパターンにだけ要る。フェーズ 6 で注記を訂正した。）
 
 - [ ] **Step 4: lock を追跡し、`slum02/.gitignore` を削除し、下書き文書を移動する**
 
@@ -827,7 +827,7 @@ Expected: `trpg texts no longer visible to git`（`private/` は現行の .gitig
 ## マージ後にユーザが行うこと（随時追記）
 
 1. `git -C /workspaces/reso-world fetch origin` の後、`feat/slum02-slum` を `origin/main` に rebase するか ff-merge する。
-2. `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` の未コミット変更は新設計に取り込み済みなので `git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md` で破棄してよい。`.claude/settings.local.json` は追跡解除後もローカルファイルとして残る。
+2. `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` の未コミット変更は新設計に取り込み済みなので `git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md` で破棄してよい。`.claude/settings.local.json` はマージで削除されるので、マージの前に退避してマージ後に書き戻す（この雛形は古い。現行の手順は `docs/integration.md`。フェーズ 6 で注記）。
 3. `MyResoniteProject/modeling/tokyo_nova/layout.py.orig` は新しい `.gitignore` で見えなくなる。不要なら削除する。
 ```
 
diff --git a/docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md b/docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md
index d4c20d7..ee3dd0e 100644
--- a/docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md
+++ b/docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md
@@ -141,11 +141,11 @@ Blender 系スキル（arjun988/blender-skills 派生の 10 スキルと referen
 - Blender: `*.blend1`、`*.blend2`、`*.blend@`
 - 編集の残骸: `*.orig`、`*.rej`、`*.bak`、`*.log`
 - resoloop: `**/.resoloop/**` と `!**/.resoloop/.gitignore`（state、flux-state、cache、作業物をすべて除外）、`**/flux/build/`、`**/flux/.protograph/`、`*.brson`
-- ローカル専用ディレクトリ: `/tmp/`、`**/tmp/`、`/docs_draft/`、`**/docs_draft/`、`/reviews/`、`/external/`、`/private/`、`/.worktrees/`、`/.claude/worktrees/`、`/.superpowers/`、`/.restructure-backup/`、`/MyResoniteProject/content/tokyo-nova/city/export-static/`、`/MyResoniteProject/content/tokyo-nova/city/export-refinement/`
+- ローカル専用ディレクトリ: `tmp/`、`docs_draft/`、`/reviews/`、`/external/`、`/private/`、`/.worktrees/`、`/.claude/worktrees/`、`/.superpowers/`、`/.restructure-backup/`、`/MyResoniteProject/content/tokyo-nova/city/export-static/`、`/MyResoniteProject/content/tokyo-nova/city/export-refinement/`
 - 個人設定: `**/.claude/settings.local.json`、`**/.devin/mcp_config.local.json`、`.env`、`.env.*`、`.secrets/`
 - Node（npx などが作る）: `node_modules/`
 
-途中に `/` を含むパターンはリポジトリルート基準で固定されるため、`slum02/` や `akichi/` などプロジェクト配下にも届かせるには `**/` を前置している。
+途中に `/` を含むパターンはリポジトリルート基準で固定されるため、`slum02/` や `akichi/` などプロジェクト配下にも届かせるには `**/` を前置している。末尾だけに `/` がある `tmp/` と `docs_draft/` は、どの階層のディレクトリにも一致するので 1 行で足りる（フェーズ 6 で実際の `.gitignore` に表記を揃えた）。
 
 `devcontainer-lock.json` は追跡に戻す。`.claude/settings.local.json` は `git rm --cached` で追跡を外す。`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json`（セッション記録）は `tests/tokyo_nova/test_task1_fix_regressions.py` が証跡ファイルとして参照しており、tokyo-nova の進行中作業と競合するため今回は移動しない。追跡済みのまま `**/.resoloop/**` の ignore 規則の既知の例外として `scripts/check-layout.sh` の許可リストに載せ、tokyo-nova 側の作業で `artifacts/` へ移す候補として記録する。`MyResoniteProject/docs_draft/` の強制追加済み 2 件は `docs/worlds/tokyo-nova/` へ移す。`slum02/.gitignore` はルートに吸収して削除する。
 
@@ -257,7 +257,7 @@ SDK は `devcontainer.json` の dotnet Feature に `"additionalVersions": "10.0.
 `docs/resoloop-fork-workflow.md` に次を書く。
 
 - checkout の位置（`external/resoloop`）と remote 構成、`/workspaces` 直下に置かない理由（root 所有のコンテナ内ディレクトリで再作成時に消える）
-- 修正の流れ: `sync` → ブランチ作成 → 修正 → `test` → ロックのコミットを差し替えて `install` → fork へ push → 上流へ PR
+- 修正の流れ: `sync` → ブランチ作成 → 修正 → `test` → ロックのコミットを差し替えて `install` → fork へ push → 上流へ PR（運用文書では、ロックを差し替える前に fork へ push する。`install` の `checkout` は origin にあるコミットしか取り出せないため）
 - fork 内 PR（usaturn/resoloop#1）はレビュー用としてマージしない。上流にマージ・リリースされたら `RESOLOOP_MODE=nuget` と `RESOLOOP_NUGET_VERSION` を更新する
 - 上流への PR 候補: scaffold の `.resoloop/.gitignore` に `cache/` が無い、global.json の `rollForward` が `latestPatch` で SDK の feature band を跨げない
 - `tmp/` の旧 checkout の整理手順（uv0-fix の未コミット草稿は patch として保存してから削除する）
@@ -284,7 +284,7 @@ SDK は `devcontainer.json` の dotnet Feature に `"additionalVersions": "10.0.
 ### 7.2 変更点
 
 - `initialize.bash`: mount のソース 14 個（既存 13 ＋秘密情報）をすべて `mkdir -p` する。
-- `devcontainer.json`: `name` を `create-reso-world`、`remoteEnv.PATH` に `${containerEnv:HOME}/.local/bin` と `${containerEnv:HOME}/bin` と `${containerEnv:HOME}/.dotnet/tools` を追加、dotnet Feature に `additionalVersions`、秘密情報の mount を追加。`devcontainer-lock.json` を追跡する。
+- `devcontainer.json`: `name` を `create-reso-world`、`remoteEnv.PATH` に `${containerEnv:HOME}/.local/bin` と `${containerEnv:HOME}/bin` と `${containerEnv:HOME}/.dotnet/tools` を追加（実装では mounts と同じく `/home/vscode/...` を直接書いた。`${containerEnv:HOME}` が root の HOME に解決されるおそれがあるため。フェーズ 4 の D-10）、dotnet Feature に `additionalVersions`、秘密情報の mount を追加。`devcontainer-lock.json` を追跡する。
 - `install_beforehand.bash`: Codex 導入ステップと Claude プラグイン（superpowers、feature-dev）を追加、uv の導入を pi 設定より前に移し `python3 scripts/setup_pi_tool_display.py` を `uv run` に置換、重複した `apt update` と `PATH` export を削除、pi 用スクリプトの移動に伴うパス修正、`STEP_TOTAL` の更新。
 - `zshrc.txt`: `cod`、`genv`、`buni`、`update()` の各項目を `command -v` で保護。`BUN_INSTALL` は `$HOME` 基準。秘密情報 `env` の読み込みを追加。
 - `starship.toml`: `custom.uv_python` は `$PWD` から上方向に最寄りの `.venv/pyvenv.cfg` を探す。
@@ -329,7 +329,7 @@ SDK は `devcontainer.json` の dotnet Feature に `"additionalVersions": "10.0.
 
 終了コード非 0 で失敗を報告する。CI と review-fix-planning の検証ゲートで使う。
 
-- ルート: `.claude/skills/*` がすべて `.agents/skills` への解決可能な symlink であり、`.agents/skills/*/SKILL.md` ごとに対応する symlink があること
+- ルート: `.claude/skills/*` がすべて `.agents/skills` への解決可能な symlink であり、ファイルを 1 つ以上持つ `.agents/skills` 直下のディレクトリごとに対応する symlink があること（`references/` のように SKILL.md を持たない共有ディレクトリも含む。フェーズ 3 の D-7）
 - 各プロジェクト（`.resoloop.json` を持つ直下ディレクトリ）: 4.2 の必須ファイルと symlink が存在し解決できること、`.claude/skills` が `.agents/skills` の実ディレクトリと 1:1 であること、`AGENTS.md` に固有節があること、`.resoloop/.gitignore` に `cache/` があること
 - resoloop が使える環境では `resoloop skills sync --check` が各プロジェクトで成功すること（無い環境では skip と表示）
 - 追跡ファイルに禁止パターンが無いこと（`ATS.txt`、`BTD.txt`、`TNX.txt`、`.claude/settings.local.json`、`*.blend1`、`*.orig`）
@@ -343,13 +343,13 @@ SDK は `devcontainer.json` の dotnet Feature に `"additionalVersions": "10.0.
 - `devcontainer-tests`: `bash .devcontainer/run-tests.bash`
 - `layout`: `bash scripts/check-layout.sh`（resoloop 無しの環境）
 - `skill-tests`: `uv run pytest tests/skills .agents/skills`
-- `gitleaks`: gitleaks の公式 Action
+- `gitleaks`: gitleaks の公式 Action（設定は `.gitleaks.toml`。resoloop のマニフェストの識別子を誤検出から外し、`[[allowlists]]` を読める版を `GITLEAKS_VERSION` で固定する。フェーズ 4 の D-13）
 
 ワールドのビルド（Blender）は CI で実行しない。
 
 ### 9.3 実機確認（ユーザが実施）
 
-マージ後に Dev Containers: Rebuild Container を実行し、`bash .devcontainer/verify-resonite-tooling.bash`、`dotnet --list-sdks` に 10.0.201 があること、`resoloop --version` がロックと一致すること、`bash scripts/check-layout.sh`、各プロジェクトで `uv run pytest` を確認する。
+マージ後に Dev Containers: Rebuild Container を実行し、`bash .devcontainer/verify-resonite-tooling.bash`、`dotnet --list-sdks` に 10.0.201 があること、`resoloop --version` がロックと一致すること、`bash scripts/check-layout.sh`、各プロジェクトで `uv run pytest` を確認する。あわせて、postCreate の fork のビルドと導入、`remoteEnv.PATH`、秘密情報の mount と `env` の読み込み、Devin の simplify-in-subagent のサブエージェントのツール、GitHub Actions の 4 ジョブの成功を確かめる（手順は `docs/integration.md` の「Rebuild 後に確かめること」）。
 
 ## 10. 実装フェーズと統合
 
@@ -369,9 +369,9 @@ SDK は `devcontainer.json` の dotnet Feature に `"additionalVersions": "10.0.
 
 ### 10.1 統合手順（`docs/integration.md`）
 
-1. `chore/repo-redesign` を最新の `feat/slum02-slum` に rebase し、`main` を再度 slum02 の HEAD へ ff してから PR を `main` に出す。
+1. `chore/repo-redesign` に最新の `feat/slum02-slum` を取り込み、`main` を再度 slum02 の HEAD へ ff（`git fetch . feat/slum02-slum:main`）してから PR を `main` に出す。取り込みは、push 済みのブランチを force push しないよう rebase ではなくマージで行う（フェーズ 6 の判断事項）。
 2. マージ後、作業ツリー側で `git fetch origin` し、`feat/slum02-slum` を `origin/main` に rebase するか ff-merge する。
-3. 作業ツリーに残る `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` の未コミット変更は、フェーズ 2 で新設計に取り込み済みであることを確認したうえで `git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md` で破棄する。`.claude/settings.local.json` はマージ前に `~/settings.local.json.bak` などへ退避しておき、この時点で元の場所へ書き戻す（マージ後は ignore 対象になるので再追跡されない）。
+3. マージの前に、作業ツリーに残る `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` の未コミット変更を、フェーズ 2 で新設計に取り込み済みであることを確認したうえで `git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md` で破棄する。`.claude/settings.local.json` は `~/settings.local.json.bak` などへ退避してから `git checkout -- .claude/settings.local.json` で変更を戻し、マージ後に元の場所へ書き戻す（マージ後は ignore 対象になるので再追跡されない）。手順の詳細は `docs/integration.md`。
 4. Dev Containers: Rebuild Container を実行し、9.3 を確認する。
 5. pi と Claude Code の trust を再承認し、Codex は初回起動時にプロジェクトの trust を承認する。
 
````

- [ ] **Step 5: テストが通ることを確かめる**

```bash
cd "$W"
bash tests/scripts/test-docs.bash
bash .devcontainer/run-tests.bash | tail -n 1
```

Expected: PASS。最後は `PASS: 24 test(s)`。

- [ ] **Step 6: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add README.md tests/scripts/test-docs.bash docs/integration.md docs/resoloop-fork-workflow.md \
  docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md \
  docs/superpowers/plans/2026-09-26-redesign-phase0-1-safety-and-hygiene.md
git commit -m "docs: add the root README and align the integration steps and spec notes

README.md explains the layout, the Dev Container, how agents are started,
new-world.sh, the ResoLoop lock and the tests. docs/integration.md now covers
what happens before the pull request, the pre-merge cleanup, the refreshed
conflict count and the checks after a rebuild. The spec, the fork workflow
doc and the phase 0-1 plan are aligned with what was implemented.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 2: 最終検証・取り込み・PR（controller）

- [ ] 1. 全体の検証を行う。

```bash
cd "$W"
git status --short | wc -l                                             # 0
bash .devcontainer/run-tests.bash | tail -n 1                          # PASS: 24 test(s)
bash scripts/check-layout.sh | tail -n 3                               # ok: resoloop lock (...) / ok: mounts match ... / PASS: check-layout
uv run pytest -q 2>&1 | tail -n 1                                      # failed が無いこと（passed と 1 skipped だけ）
for P in MyResoniteProject akichi slum02; do (cd "$P" && uv run pytest -q 2>&1 | tail -n 1); done   # 52 / 66 / 215 passed
bash .devcontainer/verify-resonite-tooling.bash; echo $?               # 0
bash scripts/resoloop-fork.sh status                                   # installed / checkout とも matches the lock
git ls-files -i -c --exclude-standard                                  # pipeline.json の 1 行だけ
```

- [ ] 2. CI 相当の確認（D-36）: `path_without` で resoloop・dotnet・blender・各エージェントの CLI を外した PATH で `bash .devcontainer/run-tests.bash` が通る。`git ls-remote --tags` で `actions/checkout` の `v7`、`astral-sh/setup-uv` の `v10.2.0`、`gitleaks/gitleaks-action` の `v3` が実在する。gitleaks 8.30.1 を `GITLEAKS_CONFIG=.gitleaks.toml gitleaks detect --redact --exit-code=2 --log-opts="--no-merges --first-parent <main との merge-base>^..HEAD"` で実行し、`no leaks found`。
- [ ] 3. 最上位モデルのレビュアーに、フェーズ 6 の範囲（本計画書のコミットの親..HEAD）のレビューを依頼し、指摘は修正ラウンドで直す。
- [ ] 4. 最新の `feat/slum02-slum` を取り込む（D-32）。`git -C "$W" merge --no-ff feat/slum02-slum -m "Merge branch 'feat/slum02-slum' into chore/repo-redesign"`（trailer 付き）。衝突したら取り込みを中止し（`git merge --abort`）、原因を台帳に記録して、衝突の解決を 1 つの修正ラウンドとして実装担当に任せる。取り込んだ後に手順 1 と 2 を繰り返す。
- [ ] 5. 統合手順の一覧を読み取りだけで作り直し（メイン作業ツリーで `git ls-tree` と `git ls-files` だけを使う。`fetch` はしない）、件数が 68 件のままであることを確かめる。変わっていれば、件数と内訳を直す修正を実装担当に任せる。
- [ ] 6. fast-forward を確かめてから、`git push origin chore/repo-redesign` を実行する。`main` を `git fetch . feat/slum02-slum:main` で fast-forward し（`main` がどの worktree でも checkout されていないことを先に確かめる）、`git push origin main` を実行する。
- [ ] 7. `gh pr create --base main --head chore/repo-redesign` で PR を 1 本開く。説明には、目的、フェーズごとの変更、各フェーズの判断事項と台帳の裁定の一覧、据え置いた Minor、マージの前後に利用者が行うこと（`docs/integration.md`）、Rebuild 後の確認、GitHub Actions が課金の設定で開始されなかったこと（D-36）を書く。
- [ ] 8. 台帳の最後に `PHASE 6 COMPLETE.` を書き、agent-handoff で引き継ぎ書を作る。

---

## 持ち越し（PR の後）

| ID | 内容 |
| --- | --- |
| N-27 | GitHub Actions の 4 ジョブの成功を、課金の設定を直した後に確かめる（D-36） |
| N-17、N-18、N-25 | Rebuild 後の実機確認（`docs/integration.md` の「Rebuild 後に確かめること」） |
| P-2 | tokyo-nova 系のブランチを新しい `main` に rebase した後、`.git/info/exclude` の `/private/` の行を消す（D-35） |
| N-28、N-29 | D-33・D-34 のとおり、必要になったときに見直す |
| 据え置き（フェーズ 3） | 前回の引き継ぎ書の PH3-S1 |
| 据え置き（フェーズ 4） | mounts_compare のループ内の再計算、check-layout のケース 54 の対称性と壊れた devcontainer.json の二重報告、verify のモックが 1 行だけ、test-readme の grep の名前の無エスケープ、識別子の allowlist がパスを限らないこと（最終レビューの M7）、update() が Codex の有無ではなく npm の有無で判定すること（M8） |
| 据え置き（フェーズ 5） | pi-model-name のテストが `PI_MODEL_SCRIPT` の行を文字列で照合すること、simplify-in-subagent のテストが見出しの文字列で本文を分けること、repo-cleanup の「push を済ませてから」が既に一致していた場合も含むこと、AGENTS.md の「リポジトリのルート基準」と「リポジトリルート基準」の表記の揺れ、new-world.sh の冒頭の終了コードの説明に AGENTS.md を戻す場合（終了コード 3）を足していないこと、名残の検査が `:` を含むパスを想定しないこと（どれもフェーズ 5 の最終レビューが「待てる」と判断した） |
