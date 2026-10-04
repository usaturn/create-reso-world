# Issue #18 Grok Build・ccda・dsh の導線の撤去 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** リポジトリが管理する dsh・Grok Build・`ccda`（`claude-alibaba`）の導入・起動・マウント・ポート・更新・案内を撤去し、再び混入したらテストで検出できるようにする。

**Architecture:** 除外対象ごとに Task を分ける（Task 1: dsh、Task 2: Grok Build、Task 3: `ccda`、Task 4: ルートの文書）。各 Task では、先にテストを新方針に変えて失敗を確かめ、次に設定・スクリプト・文書を変えて通す。再混入の検出は既存のテスト（`test-initialize-mounts.bash`、`test-readme.bash`、`test-shell-tools.bash`、`test-herdr-migration.bash`、`tests/scripts/test-docs.bash`）に足し、新しいテストファイルは作らない。Task 5 で全体を検証する。

**Tech Stack:** bash（テストは `set -euo pipefail`）、zsh（`zshrc.txt`）、Dev Container（`devcontainer.json` は JSONC）、git（`git apply --3way`、`git grep -E`）、ripgrep（`test-herdr-migration.bash` の `assert_absent`）、uv / pytest（スキルのテスト）

**Spec:** `docs/superpowers/specs/2026-10-04-issue-18-remove-excluded-agents-design.md`（判断事項 D-1〜D-9、4 章の設計、7 章の受け入れ条件、9 章の比較表の行）。親 Issue は #17、この計画の Issue は #18。

## 実行方法

推奨は **Native**（`superpowers:executing-plans`）。4 つの Task は同じファイル群（`README.md`・`test-readme.bash`・`test-initialize-mounts.bash` など）に順に積み重なり、Task ごとの差分は計画の作成時に試作で検証済みのため、Task ごとにレビュー担当を立てる利点が小さい。実行方法は、実行を指示する利用者が決める。

## Global Constraints

- 作業場所は worktree `/workspaces/reso-world/.worktrees/issue-18-remove-excluded-agents`、ブランチは `feat/issue-18-remove-excluded-agents`。各ステップは特記が無ければ `cd /workspaces/reso-world/.worktrees/issue-18-remove-excluded-agents` で実行する。worktree が無いホストでは、最新の `origin/main` から `git worktree add -b feat/issue-18-remove-excluded-agents .worktrees/issue-18-remove-excluded-agents origin/main` で作り、#18 のコメントから Spec とこの計画を復元してコミットしてから始める
- 着手前に `git fetch origin` を実行する。`origin/main` が `9699e94` から進んでいれば `git merge --no-edit origin/main` で取り込む。rebase と force push はしない
- 編集してよいのは Spec 2 章の範囲だけ。特に次は編集しない: `.agents/skills/**`・`.claude/skills/**`・`.agents/monitoring-runtimes.md`、`.devcontainer/pixg`・`.devcontainer/pi-superagents/**`・`.devcontainer/pi-superagents-exec.zsh` などの pi の設定、`install_beforehand.bash` の pi・Claude Code の手順、`zshrc.txt` の pi の環境変数と Claude ランチャーの本体、ワールドのプロジェクト、`docs/superpowers/` の既存の文書、ホストの `~/.grok`・`~/.dsh`
- パッチは `git apply --index --3way` で当てる。当たらない場合は、パッチを推測で直さず、Spec 4 章の記述どおりに手で編集し、その旨を作業報告に書く
- コミットメッセージの末尾に、コミットするエージェント自身のモデル名の trailer を付ける（例: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`）
- `git add -A`・`git add .` を使わない。パッチは `--index` で stage され、削除は `git rm` で stage される
- Python を使う場合は `uv run` を使い、`python3` を直接使わない
- PR の作成と push は、利用者の実行指示に含まれる場合だけ Task 5 で行う。force push・`main` への直接の push・他のブランチの削除はしない
- `main`（`9699e94`）では、slum03 の resoloop スキルが未同期のため `bash scripts/check-layout.sh` と `tests/scripts/test-check-layout.bash` が失敗する。範囲外なので直さない。この 2 件以外が通ることを確かめる
- 作業報告には、着手から完了までの所要時間と、Task ごとの内訳を書く（`AGENTS.md` の SDD 実行運用）

## Review Focus

- 既存環境の `~/.config/create-reso-world/env` に `MAAS_ANTHROPIC_TOKEN` が残っている: README が削除を案内し、利用者が消せること。Task 3 の `test-readme.bash` の検査で固定する
- `install_beforehand.bash` の `STEP_TOTAL` と実際の `step` の数が食い違う: postCreate の進捗表示（`[n/25]`）が崩れる。`test-install-beforehand.bash` は #19 の担当なので、Task 1 と Task 5 の確認コマンドで数を照合する
- pi で xai / Grok を使う設定（`pixg`、pi-superagents の Grok の tier）を誤って変える、または除外の検査が Grok モデルの記述に反応する: `pixg` が使えなくなる。Task 2 と Task 5 で pi の設定が `origin/main` から変わっていないことを `git diff --exit-code` で確かめ、`test-pi-superagents.bash` を含む全体のテストを通す
- ホストの `~/.dsh`・`~/.grok` を消したり書き換えたりする処理が入る: 利用者のデータを失う。除外の検査（`HOME}/.dsh` などの形）に加え、Task 1・Task 2 の確認コマンドで `install_beforehand.bash` と `initialize.bash` に `.dsh`・`.grok` が残っていないことを確かめる
- pnpm を使うものが他にある: `pnpmVersion: "none"` で壊れる。Task 1 の確認コマンドで、追跡ファイルの pnpm の記述が `devcontainer.json` の 1 か所と過去の計画書だけであることを確かめる

## ファイルの対応

| ファイル | 変更 | Task |
| --- | --- | --- |
| `.devcontainer/devcontainer.json` | `~/.dsh`・`~/.grok` の mount、`3080`、pnpm の固定を撤去 | 1・2 |
| `.devcontainer/initialize.bash` | `~/.dsh`・`~/.grok` を撤去 | 1・2 |
| `.devcontainer/install_beforehand.bash` | dsh の定数と手順、書き込み確認リストの `.dsh`・`.grok` を撤去、`STEP_TOTAL` を 25 に | 1・2 |
| `.devcontainer/dsh-settings.yaml`・`.devcontainer/dsh-cordis.patch.yml` | 削除 | 1 |
| `.devcontainer/zshrc.txt` | `grok update` とコメント、`ccda` 関数と `MAAS_ANTHROPIC_TOKEN` を撤去 | 2・3 |
| `.devcontainer/README.md` | ツール表・制約・秘密情報・dsh の節を更新し、既存環境向けの注記を足す | 1・2・3 |
| `.devcontainer/docs/herdr-session-cwd-restore.md` | grok の例示を外す | 2 |
| `AGENTS.md`・`README.md` | 対象エージェントの一覧から dsh を外す | 4 |
| `.devcontainer/test-initialize-mounts.bash` | 期待する mount を 12 個にし、検出の例を `.pi` に | 1・2 |
| `.devcontainer/test-readme.bash` | ツール表の必須の行を更新し、除外の検査（節 6）と MAAS の案内の検査を足す | 1・2・3 |
| `.devcontainer/test-shell-tools.bash` | `update()` が grok を対象にしないことを確かめる | 2 |
| `.devcontainer/test-herdr-migration.bash` | `ccda` と `MAAS_ANTHROPIC_TOKEN` の検査を外し、再混入の検査を足す | 3 |
| `tests/scripts/test-docs.bash` | 「Cursor と dsh」を更新し、dsh が無いことを確かめる | 4 |

---

### Task 1: dsh を撤去する

**Files:**
- Modify: `.devcontainer/devcontainer.json`、`.devcontainer/initialize.bash`、`.devcontainer/install_beforehand.bash`、`.devcontainer/README.md`
- Delete: `.devcontainer/dsh-settings.yaml`、`.devcontainer/dsh-cordis.patch.yml`
- Test: `.devcontainer/test-initialize-mounts.bash`、`.devcontainer/test-readme.bash`

**Interfaces:**
- Consumes: `main` の状態（`STEP_TOTAL=26`、mount 14 個）
- Produces: `STEP_TOTAL=25`、mount 13 個（`.grok` は Task 2 で外す）。`test-readme.bash` の節 6 の変数 `excluded`（Task 2・3 が `excluded+=` で追記する）。`test-initialize-mounts.bash` の target の食い違いの検出は `.pi` を使う

- [ ] **Step 1: テストを新方針に変える**

`test-initialize-mounts.bash` の期待する mount から `.dsh` を外し、target の食い違いの検出の例を `.pi` に替える。`test-readme.bash` のツール表の必須の行と「dsh は」を外し、節 6 で `.devcontainer` に dsh の導入・mount・ポート・pnpm の固定が無いことを確かめる。

````bash
git apply --index --3way <<'ISSUE18_PATCH'
diff --git a/.devcontainer/test-initialize-mounts.bash b/.devcontainer/test-initialize-mounts.bash
index 12e2ccf817c8ac43b99525386c4899c67ef541f9..396de37d27f205acd889a374222ebf346c8d72cb 100755
--- a/.devcontainer/test-initialize-mounts.bash
+++ b/.devcontainer/test-initialize-mounts.bash
@@ -15,7 +15,7 @@ source "$root/.devcontainer/mounts.bash"
 if ! out="$(mounts_compare "$config" "$init")"; then fail "mounts and initialize.bash differ:
 $out"; fi
 
-# 2. mounts は仕様 7.1 の表の 14 個（既存 13 ＋秘密情報）
+# 2. mounts は仕様 7.1 の表の 14 個（既存 13 ＋秘密情報）から、撤去した dsh の ~/.dsh を除いた 13 個
 expected='.claude
 .claude.json
 .codex
@@ -25,7 +25,6 @@ expected='.claude
 .config/gh
 .config/glab-cli
 .cursor
-.dsh
 .grok
 .local/share/cursor-agent
 .local/share/devin
@@ -79,9 +78,9 @@ grep -qxF 'mounts: ~/.extra is mounted by devcontainer.json but not created by i
 sed 's|^  "${HOME}/.grok" \\$|  "${HOME}/.grok" \\\n  "${HOME}/.unmounted" \\|' "$init" > "$tmp/extra-init.bash"
 if out="$(mounts_compare "$config" "$tmp/extra-init.bash")"; then fail 'accepted a path that is not mounted'; fi
 grep -qxF 'mounts: ~/.unmounted is created by initialize.bash but not mounted by devcontainer.json' <<<"$out" || fail "unexpected report: $out"
-sed 's|target=/home/vscode/.dsh,|target=/root/.dsh,|' "$config" > "$tmp/target.json"
+sed 's|target=/home/vscode/.pi,|target=/root/.pi,|' "$config" > "$tmp/target.json"
 if out="$(mounts_compare "$tmp/target.json" "$init")"; then fail 'accepted a mount with an unexpected target'; fi
-grep -qxF 'mounts: ~/.dsh is mounted at /root/.dsh, expected /home/vscode/.dsh' <<<"$out" || fail "unexpected report: $out"
+grep -qxF 'mounts: ~/.pi is mounted at /root/.pi, expected /home/vscode/.pi' <<<"$out" || fail "unexpected report: $out"
 # // でコメントアウトした mount と、パス以外も書いた行（chmod など）は数えない
 sed 's|^\t\t"source=${localEnv:HOME}/.codex,|\t\t// "source=${localEnv:HOME}/.codex,|' "$config" > "$tmp/commented.json"
 if out="$(mounts_compare "$tmp/commented.json" "$init")"; then fail 'counted a commented-out mount'; fi
diff --git a/.devcontainer/test-readme.bash b/.devcontainer/test-readme.bash
index 2b550139fc4641c0ed65aacd7477ac0fb15f2881..1078c201bedec69c5fec9864696b0de23b10c894 100755
--- a/.devcontainer/test-readme.bash
+++ b/.devcontainer/test-readme.bash
@@ -17,7 +17,7 @@ column() { awk -F' [|] ' -v n="$1" '{ sub(/^[|] /, ""); sub(/ [|]$/, ""); print
 ticks() { grep -o '`[^`]*`' | tr -d '`' || true; }
 
 # 1. 仕様 7.1 の行がそろっている
-for tool in 'Claude Code' Codex pi Cursor Devin dsh gh 'grok / gcloud / glab / bun' 秘密情報; do
+for tool in 'Claude Code' Codex pi Cursor Devin gh 'grok / gcloud / glab / bun' 秘密情報; do
   column 1 | grep -qxF "$tool" || fail "tool table lacks the row for $tool"
 done
 
@@ -38,9 +38,9 @@ while IFS= read -r item; do
   grep -qF -- "$item" <<<"$update_body" || fail "update() lacks '$item' listed in the tool table"
 done < <(column 6 | ticks)
 
-# 4. 仕様 7.2 の記述: ResoniteLink への到達、秘密情報の置き場、Cursor と dsh の制約、flux-sdk、テストの実行
+# 4. 仕様 7.2 の記述: ResoniteLink への到達、秘密情報の置き場、Cursor の制約、flux-sdk、テストの実行
 for s in 'networkingMode=mirrored' 'resoloop discover' 'RESONITE_LINK_URL' '~/.config/create-reso-world/env' \
-  '## エージェントの読み込みの制約' 'Cursor は' 'dsh は' 'flux-sdk' 'bash .devcontainer/run-tests.bash' \
+  '## エージェントの読み込みの制約' 'Cursor は' 'flux-sdk' 'bash .devcontainer/run-tests.bash' \
   'bash scripts/check-layout.sh' 'uv run pytest tests/skills .agents/skills' '.devcontainer/resoloop.lock'; do
   grep -qF -- "$s" "$readme" || fail "README lacks: $s"
 done
@@ -54,4 +54,8 @@ if git grep -nE '#[0-9]{3}\b' -- .devcontainer "$self"; then fail '.devcontainer
 if git grep -nF '/workspaces/reso-world' -- .devcontainer "$self"; then fail '.devcontainer hard-codes the workspace path'; fi
 if git grep -n 'symlink' -- .devcontainer/docs/herdr-session-cwd-restore.md; then fail 'the herdr doc still describes .devcontainer as a symlink'; fi
 
+# 6. 除外したエージェントの導入・mount・起動を .devcontainer に戻さない（ホストに残るパスを案内する README の注記は対象外）
+excluded='@deepseek-ai/dsh|DeepSeek Harness|DSH_|dsh-settings|dsh-cordis|dsh (plugin|web|--)|HOME\}?/\.dsh|vscode/\.dsh|pnpmVersion": "[0-9]|3080'
+if git grep -n -E "$excluded" -- .devcontainer "$self"; then fail '.devcontainer still sets up an excluded agent'; fi
+
 printf 'PASS: README tool table matches the Dev Container files\n'
ISSUE18_PATCH
````

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-initialize-mounts.bash .devcontainer/test-readme.bash`

Expected: 2 本とも FAIL。`test-initialize-mounts.bash` は `FAIL: unexpected mounts:`、`test-readme.bash` は `FAIL: .devcontainer still sets up an excluded agent`（`git grep` が `install_beforehand.bash` の `DSH_VERSION` などの行を表示する）

- [ ] **Step 3: dsh を撤去する**

雛形 2 つを削除する。`install_beforehand.bash` から dsh の定数と手順「Installing DeepSeek Harness」を削除して `STEP_TOTAL` を 25 にし、書き込み確認リストから `.dsh` を外す。`devcontainer.json` から `.dsh` の mount を外し、`pnpmVersion` を `"none"`、`forwardPorts` を `[8000]` にする。`initialize.bash` から `.dsh` を外す。README のツール表の dsh の行、読み込みの制約の dsh の項目、「DeepSeek Harness（dsh）」の節を削除し、ツール表の後に既存環境向けの注記を足す。

````bash
git rm -q .devcontainer/dsh-settings.yaml .devcontainer/dsh-cordis.patch.yml
git apply --index --3way <<'ISSUE18_PATCH'
diff --git a/.devcontainer/README.md b/.devcontainer/README.md
index 8fbf82e9ce10cbea5e2db5fa718554fec694394a..554aba30fad7125f79a20b1f5ade3fe549a4dee2 100644
--- a/.devcontainer/README.md
+++ b/.devcontainer/README.md
@@ -28,7 +28,6 @@ Herdr の復元手順は `.devcontainer/docs/herdr-session-cwd-restore.md` を
 | pi | `npm install -g` で本体、`pi install` で拡張。ランチャー 9 本を `~/.local/bin` に置く | `~/.pi` | `~/.pi` | — | `pi update`、`pi update --extensions` |
 | Cursor | installer（`cursor.com/install`） | `~/.cursor`、`~/.local/share/cursor-agent` | `~/.cursor`、`~/.local/share/cursor-agent` | `cur`（alias） | `agent update` |
 | Devin | installer（`cli.devin.ai/install.sh`） | `~/.local/share/devin`、`~/.config/devin` | `~/.local/share/devin`、`~/.config/devin` | `dev`（alias） | `devin update`、`devin plugins update superpowers` |
-| dsh | `npm install -g @deepseek-ai/dsh@0.1.5-rc.1`（版を固定） | `~/.dsh` | `~/.dsh` | — | —（版を固定しているので更新しない） |
 | gh | Dev Container Feature（github-cli） | `~/.config/gh` | `~/.config/gh` | — | — |
 | grok / gcloud / glab / bun | 未導入（参照だけ残す） | `~/.grok`、`~/.config/gcloud`、`~/.config/glab-cli` | `~/.grok`、`~/.config/gcloud`、`~/.config/glab-cli` | `genv`（gcloud）、`buni`（bun） | `grok update` |
 | 秘密情報 | — | `~/.config/create-reso-world` | `~/.config/create-reso-world`（mode 700） | env ファイルがあれば読み込む | — |
@@ -37,6 +36,10 @@ Herdr の復元手順は `.devcontainer/docs/herdr-session-cwd-restore.md` を
 未導入のツールを呼ぶ関数（`cod`、`genv`、`buni`）は、コマンドが無ければ理由を表示して 127 を返す。
 `update()` は無いツールの項目を飛ばし、飛ばした項目を表示する。
 
+dsh は、リポジトリでは導入も mount もしない。ホストの `~/.dsh` は Dev Container から
+見えなくなるだけで、削除しない。不要になったら利用者がホスト側で消す。リビルドする前の
+コンテナには、導入済みの `dsh` が残る。
+
 ## 秘密情報
 
 API トークンなどの秘密情報は、ホストの `~/.config/create-reso-world/env` に置き、リポジトリには置かない。
@@ -100,12 +103,10 @@ CLI が動作しない場合は `postCreateCommand` を失敗とし、成功扱
 
 ## エージェントの読み込みの制約
 
-プロジェクト（`slum02/` など）を cwd にしてエージェントを起動したとき、次の 2 つはスキルの一部が見えない。
+プロジェクト（`slum02/` など）を cwd にしてエージェントを起動したとき、次のエージェントはスキルの一部が見えない。
 
 - Cursor は workspace 配下の `.agents/skills` しか読まないため、ルートの共有スキルが見えない。
   プロジェクトの resonite-* スキルは見える
-- dsh は git のルートの `.agents/skills` しか読まないため、プロジェクトの resonite-* スキルが見えない。
-  ルートの共有スキルは見える
 
 Codex はルートとプロジェクトの `AGENTS.md` を直接読むため、`~/.codex/config.toml` で
 `CLAUDE.md` を指示ファイルとして読ませる設定（`project_doc_fallback_filenames`）は不要である。
@@ -599,91 +600,3 @@ pi-superagents 1.14.3 / Pi loader 0.85.1 / Superpowers 6.4.1 について、
 bash .devcontainer/test-pi-superagents.bash
 bash .devcontainer/test-pi-openai-codex.bash
 ```
-
-## DeepSeek Harness（dsh）
-
-`install_beforehand.bash` は [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)
-（`dsh`）を `@deepseek-ai/dsh@0.1.5-rc.1` に固定して導入し、直後の `dsh --version` が
-指定版を返さなければ postCreate を失敗させる。既存の `pigo` / `pigod` /
-`pigou` / `piccg` / `piccd` と `~/.pi` の設定には影響しない。
-
-`dsh` の plugin 管理は PATH 上の `pnpm` を直接 spawn する。`pnpmVersion: "none"` は
-pnpm を導入しない指定のため、Node feature で plugin 0.10.6 との組み合わせを
-隔離検証した `12.4.1` を明示導入している。
-
-`~/.dsh` は `devcontainer.json` で bind mount している。設定、plugin、credentials は
-ホスト側に残るため、リビルド後も `dsh web` の設定と Command Code plugin を
-そのまま使える。Web UI は `forwardPorts` の `3080`（dsh web の既定ポート）で
-ホストから開ける。
-
-### 初期設定
-
-設定ファイルは 2 つある。それぞれ存在しないときだけ `.devcontainer/` の雛形を
-コピーする。既に設定がある環境では上書きしないため、リポジトリ側の雛形を更新しても
-リビルドでは反映されない。反映する場合はバックアップしてから手動でコピーする。
-
-- `~/.dsh/settings.yaml` ← `.devcontainer/dsh-settings.yaml`。provider の設定
-- `~/.dsh/cordis.patch.yml` ← `.devcontainer/dsh-cordis.patch.yml`。plugin の
-  有効・無効。home レベルの patch 層は全 profile に効く
-
-```bash
-cp ~/.dsh/settings.yaml ~/.dsh/settings.yaml.bak
-cp .devcontainer/dsh-settings.yaml ~/.dsh/settings.yaml
-cp ~/.dsh/cordis.patch.yml ~/.dsh/cordis.patch.yml.bak
-cp .devcontainer/dsh-cordis.patch.yml ~/.dsh/cordis.patch.yml
-```
-
-設定は 2 つの provider を有効にする。
-
-- `deepseek-official/deepseek-v4.1-flash`。`llm-deepseek` を OpenCode Go の
-  OpenAI-compatible endpoint `https://opencode.ai/zen/go/v1` へ向けて使う
-- `commandcode/deepseek/deepseek-v4.1-flash`。Command Code plugin
-  `@mars-sea/dsh-commandcode-provider@0.10.6` を web profile に導入して使う
-
-reasoning effort `max` をリポジトリ設定で固定するのは OpenCode Go 経路だけである。
-`agent-default-model` の既定の選択（`deepseek-official/deepseek-v4.1-flash`）と
-`llm-deepseek` に `reasoningEffort: max` を書いている。Command Code plugin には
-effort の設定項目が無く、リクエストに渡された値だけを使うため、Command Code の
-モデルを選んだセッションの effort は UI 側の選択で決まる。
-
-Command Code plugin の Web Search は `webSearch: false` で無効化する。
-
-DeepSeek 独自の `dsh_plugin_packages` は `plugin-package-inventory-deepseek` を
-無効化して送らないようにしている。この plugin は settings の section を登録せず、
-`settings.yaml` に書いても無視されるため、無効化は `~/.dsh/cordis.patch.yml` の
-patch 層で行う。`install_beforehand.bash` は `dsh --profile web --dump-config` で
-実際に `enabled: false` になっていることを確認し、なっていなければ postCreate を
-失敗させる。
-
-### API トークン
-
-API key はリポジトリにも `~/.dsh/settings.yaml` にも保存しない。設定は
-環境変数名（`OPENCODE_API_KEY` / `COMMANDCODE_API_KEY`）だけを参照する。
-`dsh web` を使うシェルで export しておく（`pigo` / `piccd` と同じ値を使う）。
-「秘密情報」の節の `~/.config/create-reso-world/env` に書けば、シェルの起動時に export される。
-
-Dev Container を使わないローカル環境では、`pnpm` を用意したうえで次の順に
-手動で導入する。既に `~/.dsh/` 側にファイルがある場合はコピーしない。
-
-```bash
-npm install -g @deepseek-ai/dsh@0.1.5-rc.1
-mkdir -p ~/.dsh
-[ -f ~/.dsh/settings.yaml ] || cp .devcontainer/dsh-settings.yaml ~/.dsh/settings.yaml
-[ -f ~/.dsh/cordis.patch.yml ] || cp .devcontainer/dsh-cordis.patch.yml ~/.dsh/cordis.patch.yml
-dsh plugin --profile web add @mars-sea/dsh-commandcode-provider@0.10.6
-```
-
-### 検証
-
-Dev Containers: Rebuild Container の後に次を実行する。
-
-```bash
-dsh --version                     # 0.1.5-rc.1 と表示される
-dsh --profile web --dump-config   # llm-deepseek と llm-commandcode が見える
-dsh --profile web --dump-config | grep -A4 'plugin-package-inventory-deepseek'
-                                  # config の enabled: false が見える
-dsh web --no-open                 # Web UI が port 3080 で待ち受ける
-```
-
-`dsh web --no-open` は終了しないため、確認後は Ctrl-C で止める。API key を
-含むログを残さないこと。
diff --git a/.devcontainer/devcontainer.json b/.devcontainer/devcontainer.json
index 401a4f59f3e5eef7726cadb2280f68468e287d96..f7ee5e9c62bf74bdb7b07d67528ce639090be4c5 100644
--- a/.devcontainer/devcontainer.json
+++ b/.devcontainer/devcontainer.json
@@ -8,7 +8,6 @@
 		"source=${localEnv:HOME}/.claude.json,target=/home/vscode/.claude.json,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.grok,target=/home/vscode/.grok,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.pi,target=/home/vscode/.pi,type=bind,consistency=cached",
-		"source=${localEnv:HOME}/.dsh,target=/home/vscode/.dsh,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.local/share/devin,target=/home/vscode/.local/share/devin,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.config/devin,target=/home/vscode/.config/devin,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.local/share/cursor-agent,target=/home/vscode/.local/share/cursor-agent,type=bind,consistency=cached",
@@ -57,9 +56,8 @@
 		// 常駐インストールする必要はなく、既定 (false) の corepack 経由に戻す。
 		"installYarnUsingApt": false,
 		"version": "24",
-		// dsh plugin は PATH 上の pnpm を直接 spawn する。pnpmVersion "none" は
-		// 導入省略のため、plugin 0.10.6 との組み合わせを隔離検証した 12.4.1 を明示する。
-		"pnpmVersion": "12.4.1",
+		// pnpm を使うツールは無いため導入しない（省略すると latest が入る）。
+		"pnpmVersion": "none",
 		"nvmVersion": "latest"
 		}
 	},
@@ -69,8 +67,7 @@
 
 	// Use 'forwardPorts' to make a list of ports inside the container available locally.
 	// "forwardPorts": [],
-	// 3080 は dsh web の既定ポート。
-	"forwardPorts": [8000, 3080],
+	"forwardPorts": [8000],
 
 	// Use 'postCreateCommand' to run commands after the container is created.
 	// "postCreateCommand": "uname -a",
diff --git a/.devcontainer/initialize.bash b/.devcontainer/initialize.bash
index 67132eb9a58676cc9c9ff1dd9947b0f9619223ea..7cac0eb0833f793cb7869acff8b53f6bebe9c00a 100755
--- a/.devcontainer/initialize.bash
+++ b/.devcontainer/initialize.bash
@@ -11,7 +11,6 @@ mkdir -p \
   "${HOME}/.claude" \
   "${HOME}/.grok" \
   "${HOME}/.pi" \
-  "${HOME}/.dsh" \
   "${HOME}/.local/share/devin" \
   "${HOME}/.config/devin" \
   "${HOME}/.local/share/cursor-agent" \
diff --git a/.devcontainer/install_beforehand.bash b/.devcontainer/install_beforehand.bash
index 097a38cec75a0016df637bfd3e4740cfe80d67bc..7b6c5b0035431ec93115ea9cd73b5a7cc51fbe24 100755
--- a/.devcontainer/install_beforehand.bash
+++ b/.devcontainer/install_beforehand.bash
@@ -2,16 +2,12 @@
 
 set -u
 
-# DeepSeek Harness
-readonly DSH_VERSION="0.1.5-rc.1"
-readonly DSH_COMMANDCODE_PROVIDER_VERSION="0.10.6"
-
 # postCreate の出力は、途中でコンテナが止まると残らない。どのステップまで進んだかを
 # 後から追えるよう、各ステップの開始を必ず1行で出し、失敗は ERROR 行を残して
 # 打ち切る（2026-09-13 のリビルド中断インシデント）。継続してよい処理
 # （workspace cleanup）だけを明示的に続行させるため、スクリプト全体には set -e を
 # 付けない。
-readonly STEP_TOTAL=26
+readonly STEP_TOTAL=25
 STEP_NUMBER=0
 
 step() {
@@ -71,7 +67,6 @@ for dir in \
     "${HOME}/.claude" \
     "${HOME}/.grok" \
     "${HOME}/.pi" \
-    "${HOME}/.dsh" \
     "${HOME}/.cursor"; do
     if ! ensure_user_writable_dir "$dir"; then
         fail "Failed to prepare writable directory: ${dir}"
@@ -384,79 +379,6 @@ if ! zsh .devcontainer/setup_pi_superagents.zsh --if-absent; then
     fail "Failed to set up pi-superagents launcher configs."
 fi
 
-step "Installing DeepSeek Harness"
-# DeepSeek Harness（dsh）は pi と並行して使う。dsh の plugin 管理は PATH 上の
-# pnpm を直接 spawn するため、devcontainer.json の Node feature で pnpm を明示導入
-# している（pnpmVersion "none" は導入省略）。
-install_deepseek_harness() {
-    echo "Installing DeepSeek Harness ${DSH_VERSION}..."
-    if ! npm install -g "@deepseek-ai/dsh@${DSH_VERSION}"; then
-        echo "DeepSeek Harness installation failed." >&2
-        exit 1
-    fi
-    if ! command -v dsh >/dev/null 2>&1; then
-        echo "DeepSeek Harness installation completed without placing dsh on PATH." >&2
-        exit 1
-    fi
-    # 想定と違う版が入ると Developer Preview の仕様差を踏むため fail-loud にする。
-    if ! dsh_version="$(dsh --version)"; then
-        echo "dsh --version failed." >&2
-        exit 1
-    fi
-    if [ "${dsh_version//[[:space:]]/}" != "${DSH_VERSION}" ]; then
-        echo "Unexpected dsh version: ${dsh_version} (expected ${DSH_VERSION})." >&2
-        exit 1
-    fi
-    # ~/.dsh は devcontainer.json で bind mount している。ホスト側に存在しない場合は
-    # Docker が root 所有で作成するため、以降の dsh が書き込めるよう所有権を直す。
-    ensure_user_writable_dir "${HOME}/.dsh" || {
-        echo "Failed to prepare writable directory: ${HOME}/.dsh." >&2
-        exit 1
-    }
-    # settings.yaml は bind mount 側を正とし、無い場合のみ雛形を配置する。
-    # 毎回上書きすると、Web UI や利用者が更新した設定がリビルドで失われる。
-    if [ ! -f "${HOME}/.dsh/settings.yaml" ]; then
-        if ! cp .devcontainer/dsh-settings.yaml "${HOME}/.dsh/settings.yaml"; then
-            echo "Failed to place dsh settings.yaml." >&2
-            exit 1
-        fi
-    fi
-    # cordis.patch.yml も settings.yaml と同じく無い場合のみ配置する。plugin の
-    # 無効化を settings.yaml に書いても効かないため、この patch 層に置く（理由は
-    # dsh-cordis.patch.yml のコメントを参照）。
-    if [ ! -f "${HOME}/.dsh/cordis.patch.yml" ]; then
-        if ! cp .devcontainer/dsh-cordis.patch.yml "${HOME}/.dsh/cordis.patch.yml"; then
-            echo "Failed to place dsh cordis.patch.yml." >&2
-            exit 1
-        fi
-    fi
-    # Command Code plugin は web profile にだけ導入する。plugin add は導入済みなら
-    # lockfile 一致で成功する（冪等）ため、rebuild のたびに実行して欠落を検出する。
-    if ! dsh plugin --profile web add "@mars-sea/dsh-commandcode-provider@${DSH_COMMANDCODE_PROVIDER_VERSION}"; then
-        echo "Failed to add the Command Code provider to the dsh web profile." >&2
-        exit 1
-    fi
-    # 既に別内容の cordis.patch.yml を持つ環境では無効化が入らない。効いていない
-    # 設定を silent に通すと「設定したつもり」を再生産するため、解決後の構成を見て
-    # fail-loud にする。
-    if ! dsh_config="$(dsh --profile web --dump-config)"; then
-        echo "dsh --profile web --dump-config failed." >&2
-        exit 1
-    fi
-    # 当該 entry のブロック内だけを見る。次の top-level entry（行頭の "- "）で
-    # 抜けるので、隣の plugin の enabled で通ってしまうことがない。
-    if ! printf '%s\n' "${dsh_config}" | awk '
-        /^- id: plugin-package-inventory-deepseek$/ { inside = 1; next }
-        inside && /^- / { inside = 0 }
-        inside && /^[[:space:]]+enabled: false$/ { found = 1 }
-        END { exit found ? 0 : 1 }
-    '; then
-        echo "dsh still enables plugin-package-inventory-deepseek; check ${HOME}/.dsh/cordis.patch.yml." >&2
-        exit 1
-    fi
-}
-install_deepseek_harness
-
 step "Installing the shared skills (herdr / find-skills)"
 if ! npx -y skills add herdrdev/herdr --skill herdr -g -y -a claude-code -a pi; then
     fail "Failed to install the herdr skill."
ISSUE18_PATCH
````

- [ ] **Step 4: テストが通ることを確かめる**

Run:

```bash
bash .devcontainer/run-tests.bash .devcontainer/test-initialize-mounts.bash .devcontainer/test-readme.bash \
  .devcontainer/test-install-beforehand.bash .devcontainer/test-herdr-migration.bash
bash -n .devcontainer/install_beforehand.bash && echo SYNTAX_OK
[ "$(grep -c '^step "' .devcontainer/install_beforehand.bash)" = "$(grep -oP '^readonly STEP_TOTAL=\K[0-9]+' .devcontainer/install_beforehand.bash)" ] && echo STEP_TOTAL_OK
bash -c 'source .devcontainer/mounts.bash && mounts_compare .devcontainer/devcontainer.json .devcontainer/initialize.bash' && echo MOUNTS_OK
git grep -n '\.dsh' -- .devcontainer/install_beforehand.bash .devcontainer/initialize.bash .devcontainer/devcontainer.json || echo NO_DSH_PATH
git grep -n -i pnpm -- ':!docs/superpowers'
```

Expected: `PASS: 4 test(s)`、`SYNTAX_OK`、`STEP_TOTAL_OK`、`MOUNTS_OK`、`NO_DSH_PATH`。最後のコマンドは `.devcontainer/devcontainer.json` の 2 行（コメントと `"pnpmVersion": "none",`）だけを表示する

- [ ] **Step 5: コミットする**

```bash
git status --short
git commit -m "chore(devcontainer): remove DeepSeek Harness (dsh)

dsh の導入手順と雛形、~/.dsh の mount、dsh web の 3080、dsh の plugin の
ための pnpm の固定を撤去する。ホストの ~/.dsh は削除しない。Issue #18。

Co-Authored-By: <コミットするエージェントのモデル名> <noreply@anthropic.com>"
```

Expected: `git status --short` は Step 1・3 のファイルだけを `M`・`D` で表示する。trailer はコミットするエージェント自身のモデル名に置き換える

### Task 2: Grok Build を撤去する

**Files:**
- Modify: `.devcontainer/devcontainer.json`、`.devcontainer/initialize.bash`、`.devcontainer/install_beforehand.bash`、`.devcontainer/zshrc.txt`、`.devcontainer/README.md`、`.devcontainer/docs/herdr-session-cwd-restore.md`
- Test: `.devcontainer/test-initialize-mounts.bash`、`.devcontainer/test-readme.bash`、`.devcontainer/test-shell-tools.bash`

**Interfaces:**
- Consumes: Task 1 の `test-readme.bash` の変数 `excluded` と、`.pi` を使う検出の例
- Produces: mount 12 個。`excluded` に Grok Build のパターンを追記した状態（Task 3 がさらに追記する）

- [ ] **Step 1: テストを新方針に変える**

`test-initialize-mounts.bash` の期待する mount から `.grok` を外し、`initialize.bash` の食い違いの検出の例を `.pi` に替える。`test-readme.bash` のツール表の行名を `gcloud / glab / bun` にし、`excluded` に Grok Build の導入・mount・更新のパターンを追記する。`test-shell-tools.bash` の期待するツールから grok を外し、`update()` が grok を対象にしないことを確かめる。

````bash
git apply --index --3way <<'ISSUE18_PATCH'
diff --git a/.devcontainer/test-initialize-mounts.bash b/.devcontainer/test-initialize-mounts.bash
index 396de37d27f205acd889a374222ebf346c8d72cb..f64da6c0daa025dff89cdc6f6a76bf42143a9e02 100755
--- a/.devcontainer/test-initialize-mounts.bash
+++ b/.devcontainer/test-initialize-mounts.bash
@@ -15,7 +15,7 @@ source "$root/.devcontainer/mounts.bash"
 if ! out="$(mounts_compare "$config" "$init")"; then fail "mounts and initialize.bash differ:
 $out"; fi
 
-# 2. mounts は仕様 7.1 の表の 14 個（既存 13 ＋秘密情報）から、撤去した dsh の ~/.dsh を除いた 13 個
+# 2. mounts は仕様 7.1 の表の 14 個（既存 13 ＋秘密情報）から、撤去した dsh と Grok Build の ~/.dsh・~/.grok を除いた 12 個
 expected='.claude
 .claude.json
 .codex
@@ -25,7 +25,6 @@ expected='.claude
 .config/gh
 .config/glab-cli
 .cursor
-.grok
 .local/share/cursor-agent
 .local/share/devin
 .pi'
@@ -75,7 +74,7 @@ cp "$config" "$tmp/extra.json"
 sed -i 's|^\(\t\t"source=${localEnv:HOME}/.pi,target=/home/vscode/.pi,type=bind,consistency=cached",\)$|\1\n\t\t"source=${localEnv:HOME}/.extra,target=/home/vscode/.extra,type=bind,consistency=cached",|' "$tmp/extra.json"
 if out="$(mounts_compare "$tmp/extra.json" "$init")"; then fail 'accepted a mount that initialize.bash does not create'; fi
 grep -qxF 'mounts: ~/.extra is mounted by devcontainer.json but not created by initialize.bash' <<<"$out" || fail "unexpected report: $out"
-sed 's|^  "${HOME}/.grok" \\$|  "${HOME}/.grok" \\\n  "${HOME}/.unmounted" \\|' "$init" > "$tmp/extra-init.bash"
+sed 's|^  "${HOME}/.pi" \\$|  "${HOME}/.pi" \\\n  "${HOME}/.unmounted" \\|' "$init" > "$tmp/extra-init.bash"
 if out="$(mounts_compare "$config" "$tmp/extra-init.bash")"; then fail 'accepted a path that is not mounted'; fi
 grep -qxF 'mounts: ~/.unmounted is created by initialize.bash but not mounted by devcontainer.json' <<<"$out" || fail "unexpected report: $out"
 sed 's|target=/home/vscode/.pi,|target=/root/.pi,|' "$config" > "$tmp/target.json"
diff --git a/.devcontainer/test-readme.bash b/.devcontainer/test-readme.bash
index 1078c201bedec69c5fec9864696b0de23b10c894..174f9ea353b17fe72369547bd0958a006d8df784 100755
--- a/.devcontainer/test-readme.bash
+++ b/.devcontainer/test-readme.bash
@@ -17,7 +17,7 @@ column() { awk -F' [|] ' -v n="$1" '{ sub(/^[|] /, ""); sub(/ [|]$/, ""); print
 ticks() { grep -o '`[^`]*`' | tr -d '`' || true; }
 
 # 1. 仕様 7.1 の行がそろっている
-for tool in 'Claude Code' Codex pi Cursor Devin gh 'grok / gcloud / glab / bun' 秘密情報; do
+for tool in 'Claude Code' Codex pi Cursor Devin gh 'gcloud / glab / bun' 秘密情報; do
   column 1 | grep -qxF "$tool" || fail "tool table lacks the row for $tool"
 done
 
@@ -56,6 +56,7 @@ if git grep -n 'symlink' -- .devcontainer/docs/herdr-session-cwd-restore.md; the
 
 # 6. 除外したエージェントの導入・mount・起動を .devcontainer に戻さない（ホストに残るパスを案内する README の注記は対象外）
 excluded='@deepseek-ai/dsh|DeepSeek Harness|DSH_|dsh-settings|dsh-cordis|dsh (plugin|web|--)|HOME\}?/\.dsh|vscode/\.dsh|pnpmVersion": "[0-9]|3080'
+excluded+='|x\.ai/cli|HOME\}?/\.grok|vscode/\.grok|grok update|-a grok'
 if git grep -n -E "$excluded" -- .devcontainer "$self"; then fail '.devcontainer still sets up an excluded agent'; fi
 
 printf 'PASS: README tool table matches the Dev Container files\n'
diff --git a/.devcontainer/test-shell-tools.bash b/.devcontainer/test-shell-tools.bash
index 8bb1ac75166b43066d0b545e0057a4c3dcabc80e..5c4ef14763d5c7f1fb53dd8b7cd3a08c790249af 100755
--- a/.devcontainer/test-shell-tools.bash
+++ b/.devcontainer/test-shell-tools.bash
@@ -37,9 +37,11 @@ if grep -F 'command not found' "$tmp/err"; then fail 'zshrc.txt ran a missing co
 
 # 2. update() は無いツールを飛ばして 0 を返し、飛ばした項目を表示する
 run_zsh 'update' || fail "update failed without any tool: $(cat "$tmp/err")"
-for tool in claude npm grok pi agent devin; do
+for tool in claude npm pi agent devin; do
   grep -qF "update: $tool not found; skipped" "$tmp/err" || fail "update did not report the missing $tool"
 done
+# 撤去した Grok Build（grok）は update() の対象にしない
+if grep -qF 'update: grok' "$tmp/err"; then fail 'update() still updates grok'; fi
 if grep -F 'command not found' "$tmp/err"; then fail 'update ran a missing command'; fi
 
 # 3. update() はあるツールだけを更新する
ISSUE18_PATCH
````

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-initialize-mounts.bash .devcontainer/test-readme.bash .devcontainer/test-shell-tools.bash`

Expected: 3 本とも FAIL。`FAIL: unexpected mounts:`、`FAIL: tool table lacks the row for gcloud / glab / bun`、`FAIL: update() still updates grok`

- [ ] **Step 3: Grok Build を撤去する**

`devcontainer.json`・`initialize.bash`・書き込み確認リストから `.grok` を外す。`zshrc.txt` の `update()` から `grok update` を、`require_command` のコメントから grok を外す。README のツール表の行を `gcloud / glab / bun` にして `~/.grok` と `grok update` を外し、注記に Grok Build を足す。Herdr の文書の PATH の例示から grok を外す。

````bash
git apply --index --3way <<'ISSUE18_PATCH'
diff --git a/.devcontainer/README.md b/.devcontainer/README.md
index 554aba30fad7125f79a20b1f5ade3fe549a4dee2..8a2f48058e69103e56f5b64cab0157f5e4a40587 100644
--- a/.devcontainer/README.md
+++ b/.devcontainer/README.md
@@ -29,16 +29,16 @@ Herdr の復元手順は `.devcontainer/docs/herdr-session-cwd-restore.md` を
 | Cursor | installer（`cursor.com/install`） | `~/.cursor`、`~/.local/share/cursor-agent` | `~/.cursor`、`~/.local/share/cursor-agent` | `cur`（alias） | `agent update` |
 | Devin | installer（`cli.devin.ai/install.sh`） | `~/.local/share/devin`、`~/.config/devin` | `~/.local/share/devin`、`~/.config/devin` | `dev`（alias） | `devin update`、`devin plugins update superpowers` |
 | gh | Dev Container Feature（github-cli） | `~/.config/gh` | `~/.config/gh` | — | — |
-| grok / gcloud / glab / bun | 未導入（参照だけ残す） | `~/.grok`、`~/.config/gcloud`、`~/.config/glab-cli` | `~/.grok`、`~/.config/gcloud`、`~/.config/glab-cli` | `genv`（gcloud）、`buni`（bun） | `grok update` |
+| gcloud / glab / bun | 未導入（参照だけ残す） | `~/.config/gcloud`、`~/.config/glab-cli` | `~/.config/gcloud`、`~/.config/glab-cli` | `genv`（gcloud）、`buni`（bun） | — |
 | 秘密情報 | — | `~/.config/create-reso-world` | `~/.config/create-reso-world`（mode 700） | env ファイルがあれば読み込む | — |
 <!-- tool-table:end -->
 
 未導入のツールを呼ぶ関数（`cod`、`genv`、`buni`）は、コマンドが無ければ理由を表示して 127 を返す。
 `update()` は無いツールの項目を飛ばし、飛ばした項目を表示する。
 
-dsh は、リポジトリでは導入も mount もしない。ホストの `~/.dsh` は Dev Container から
-見えなくなるだけで、削除しない。不要になったら利用者がホスト側で消す。リビルドする前の
-コンテナには、導入済みの `dsh` が残る。
+dsh と Grok Build（`grok`）は、リポジトリでは導入も mount もしない。ホストの `~/.dsh`・`~/.grok` は
+Dev Container から見えなくなるだけで、削除しない。不要になったら利用者がホスト側で消す。
+リビルドする前のコンテナには、導入済みの `dsh` が残る。
 
 ## 秘密情報
 
diff --git a/.devcontainer/devcontainer.json b/.devcontainer/devcontainer.json
index f7ee5e9c62bf74bdb7b07d67528ce639090be4c5..735dfa89c803871248eb0fc35660c510e5a47933 100644
--- a/.devcontainer/devcontainer.json
+++ b/.devcontainer/devcontainer.json
@@ -6,7 +6,6 @@
 		"source=${localEnv:HOME}/.codex,target=/home/vscode/.codex,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.claude,target=/home/vscode/.claude,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.claude.json,target=/home/vscode/.claude.json,type=bind,consistency=cached",
-		"source=${localEnv:HOME}/.grok,target=/home/vscode/.grok,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.pi,target=/home/vscode/.pi,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.local/share/devin,target=/home/vscode/.local/share/devin,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.config/devin,target=/home/vscode/.config/devin,type=bind,consistency=cached",
diff --git a/.devcontainer/docs/herdr-session-cwd-restore.md b/.devcontainer/docs/herdr-session-cwd-restore.md
index bf8eb957aaf96390fe5425e1f2bf8a449fedc141..7439fcf6a9ee6b57120d8299d58608b4736e74c9 100644
--- a/.devcontainer/docs/herdr-session-cwd-restore.md
+++ b/.devcontainer/docs/herdr-session-cwd-restore.md
@@ -120,7 +120,7 @@ Claude Code は `~/.claude/projects/<cwd スラグ>/` で会話履歴を管理
 `zsh -l`（非インタラクティブ）は `.zshrc` を読まないため `herdrstart` が走らない。
 プローブシェルの残留と、それによる `session.json` の汚染がなくなる。
 
-`.zshrc` にしか定義されていない PATH（bun、grok、opencode など）はプローブで採取できなく
+`.zshrc` にしか定義されていない PATH（bun、opencode など）はプローブで採取できなく
 なるが、現状はプローブが herdr でハングして何も採取できていないため悪化しない。
 
 ### 3. `.devcontainer/install_beforehand.bash` — 追記順序を直す
diff --git a/.devcontainer/initialize.bash b/.devcontainer/initialize.bash
index 7cac0eb0833f793cb7869acff8b53f6bebe9c00a..c54e2b28152e322b7e67cb616f4048e7f5bf6f2c 100755
--- a/.devcontainer/initialize.bash
+++ b/.devcontainer/initialize.bash
@@ -9,7 +9,6 @@ set -e
 mkdir -p \
   "${HOME}/.codex" \
   "${HOME}/.claude" \
-  "${HOME}/.grok" \
   "${HOME}/.pi" \
   "${HOME}/.local/share/devin" \
   "${HOME}/.config/devin" \
diff --git a/.devcontainer/install_beforehand.bash b/.devcontainer/install_beforehand.bash
index 7b6c5b0035431ec93115ea9cd73b5a7cc51fbe24..86c766463a83a5759cdf841b8d9f2867e7f4d520 100755
--- a/.devcontainer/install_beforehand.bash
+++ b/.devcontainer/install_beforehand.bash
@@ -65,7 +65,6 @@ for dir in \
     "${HOME}/.config/create-reso-world" \
     "${HOME}/.codex" \
     "${HOME}/.claude" \
-    "${HOME}/.grok" \
     "${HOME}/.pi" \
     "${HOME}/.cursor"; do
     if ! ensure_user_writable_dir "$dir"; then
diff --git a/.devcontainer/zshrc.txt b/.devcontainer/zshrc.txt
index 97ce3551343144502377a3903099597202217f86..092256ff96ab73d2f35767725242e5b3d318cb29 100644
--- a/.devcontainer/zshrc.txt
+++ b/.devcontainer/zshrc.txt
@@ -20,7 +20,7 @@ setopt no_beep
 # プロンプトが表示されるたびにプロンプト文字列を評価、置換する
 setopt prompt_subst
 
-# 未導入のツール（grok・gcloud・glab・bun など）を呼ぶ関数は、先にコマンドの有無を確かめる。
+# 未導入のツール（gcloud・glab・bun など）を呼ぶ関数は、先にコマンドの有無を確かめる。
 # 無ければ理由を表示して 127 を返す（仕様 7.1）
 function require_command(){
     command -v "$1" >/dev/null 2>&1 && return 0
@@ -433,7 +433,6 @@ function update_if_present(){
 function update(){
     update_if_present claude claude update
     update_if_present npm npm install -g @openai/codex@latest
-    update_if_present grok grok update
     update_if_present pi pi update
     update_if_present pi pi update --extensions
     update_if_present agent agent update
ISSUE18_PATCH
````

- [ ] **Step 4: テストが通ることを確かめる**

Run:

```bash
bash .devcontainer/run-tests.bash .devcontainer/test-initialize-mounts.bash .devcontainer/test-readme.bash \
  .devcontainer/test-shell-tools.bash .devcontainer/test-install-beforehand.bash .devcontainer/test-herdr-migration.bash
zsh -n .devcontainer/zshrc.txt && echo ZSH_OK
bash -c 'source .devcontainer/mounts.bash && mounts_compare .devcontainer/devcontainer.json .devcontainer/initialize.bash' && echo MOUNTS_OK
git grep -n '\.grok' -- .devcontainer/install_beforehand.bash .devcontainer/initialize.bash .devcontainer/devcontainer.json || echo NO_GROK_PATH
git diff --exit-code "$(git merge-base HEAD origin/main)" -- .devcontainer/pixg .devcontainer/pi-superagents .devcontainer/pi-superagents-exec.zsh && echo PI_GROK_UNCHANGED
```

Expected: `PASS: 5 test(s)`、`ZSH_OK`、`MOUNTS_OK`、`NO_GROK_PATH`、`PI_GROK_UNCHANGED`

- [ ] **Step 5: コミットする**

```bash
git status --short
git commit -m "chore(devcontainer): remove Grok Build references

~/.grok の mount と update() の grok update を撤去する。pi の xai / Grok の
設定（pixg など）は変えない。ホストの ~/.grok は削除しない。Issue #18。

Co-Authored-By: <コミットするエージェントのモデル名> <noreply@anthropic.com>"
```

Expected: `git status --short` は Step 1・3 のファイルだけを `M` で表示する

### Task 3: ccda を撤去する

**Files:**
- Modify: `.devcontainer/zshrc.txt`、`.devcontainer/README.md`
- Test: `.devcontainer/test-herdr-migration.bash`、`.devcontainer/test-readme.bash`

**Interfaces:**
- Consumes: Task 2 の `test-readme.bash` の変数 `excluded`
- Produces: `MAAS_ANTHROPIC_TOKEN` を外した `cc_launcher_unsets` と、それを基準にする `test-herdr-migration.bash` の `expected_unsets`（#21 が引き継ぐ）。共有リストを使う関数は `ccdd`・`ccddg`・`ccdu` の 3 つ

- [ ] **Step 1: テストを新方針に変える**

`test-herdr-migration.bash` の共有リストを使う関数の数を 3 にし、`expected_unsets`・テスト用の環境変数・検査するランチャーから `ccda` と `MAAS_ANTHROPIC_TOKEN` を外す。`zshrc.txt` に `claude-alibaba`・`ccda`・`MAAS_ANTHROPIC_TOKEN`・`maas.aliyuncs` が無いことを確かめる。`test-readme.bash` の `excluded` に `ccda` のパターンを追記し、README が `MAAS_ANTHROPIC_TOKEN` の削除を案内していることを確かめる。

````bash
git apply --index --3way <<'ISSUE18_PATCH'
diff --git a/.devcontainer/test-herdr-migration.bash b/.devcontainer/test-herdr-migration.bash
index a6d28f58012709a038dc7376fba72e5c7c0a003b..d674f132d83cab4a9757b7b0e69459ac460600f7 100755
--- a/.devcontainer/test-herdr-migration.bash
+++ b/.devcontainer/test-herdr-migration.bash
@@ -504,7 +504,7 @@ test_installer_wiring() {
     assert_absent "$installer" 'tmux'
 }
 
-# ccda / ccdd / ccddg / ccdu の env -u 共有リストが、親シェルで export された
+# ccdd / ccddg / ccdu の env -u 共有リストが、親シェルで export された
 # 主要な認証材料・プロバイダ切替・モデルピン留系の値を子 claude へ漏らさない
 # ことを検査する。対象範囲の正本は下の expected_unsets。
 # 共有配列ブロックから抽出した unset_vars は下の expected_unsets と集合比較する。
@@ -523,8 +523,10 @@ test_cc_launcher_env_unsets() {
     chmod +x "$test_home/bin/claude"
 
     assert_contains "$ZSHRC_TEMPLATE" 'typeset -a cc_launcher_unsets'
-    [ "$(rg -c -- 'env "\$\{cc_launcher_unsets\[@\]\}"' "$ZSHRC_TEMPLATE")" -ge 4 ] \
-        || fail 'cc_launcher_unsets must be shared by all 4 launcher functions'
+    [ "$(rg -c -- 'env "\$\{cc_launcher_unsets\[@\]\}"' "$ZSHRC_TEMPLATE")" -ge 3 ] \
+        || fail 'cc_launcher_unsets must be shared by all 3 launcher functions'
+    # 撤去した ccda（claude-alibaba）を戻さない
+    assert_absent "$ZSHRC_TEMPLATE" 'claude-alibaba|ccda|MAAS_ANTHROPIC_TOKEN|maas\.aliyuncs'
 
     local -a expected_unsets=(
         ANTHROPIC_API_KEY
@@ -569,7 +571,6 @@ test_cc_launcher_env_unsets() {
         CLAUDE_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR
         COMMANDCODE_API_KEY
         DEEPINFRA_TOKEN
-        MAAS_ANTHROPIC_TOKEN
         OPENCODE_API_KEY
         OPENCODE_GO_API_KEY
         OPENCODE_GO_CLAUDE_API_KEY
@@ -593,7 +594,6 @@ test_cc_launcher_env_unsets() {
         || fail 'cc_launcher_unsets extraction must ignore unrelated env -u entries'
 
     local -a env_args=(
-        MAAS_ANTHROPIC_TOKEN=fake-maas
         DEEPINFRA_TOKEN=fake-di
         # ccdu のキー解決チェーンをテスト値で固定する。空値は :- で未設定扱いとなり、
         # 親シェルの export が残っていても OPENCODE_API_KEY=fake-open へ必ず倒れる
@@ -604,7 +604,7 @@ test_cc_launcher_env_unsets() {
     local v
     for v in "${unset_vars[@]}"; do
         case "$v" in
-            DEEPINFRA_TOKEN | MAAS_ANTHROPIC_TOKEN | OPENCODE_API_KEY | \
+            DEEPINFRA_TOKEN | OPENCODE_API_KEY | \
                 OPENCODE_GO_API_KEY | OPENCODE_GO_CLAUDE_API_KEY)
                 continue
                 ;;
@@ -613,7 +613,7 @@ test_cc_launcher_env_unsets() {
     done
 
     local fn log
-    for fn in ccda ccdd ccddg ccdu; do
+    for fn in ccdd ccddg ccdu; do
         log="${dump_dir}/${fn}.log"
         : > "$log"
         run_zshrc_code "$test_home" \
@@ -626,18 +626,16 @@ test_cc_launcher_env_unsets() {
     # 入力元の資格情報は ANTHROPIC_* へ値を渡したあと、子 claude へ残さない。
     local source_key
     for source_key in \
-        MAAS_ANTHROPIC_TOKEN \
         DEEPINFRA_TOKEN \
         OPENCODE_GO_CLAUDE_API_KEY \
         OPENCODE_API_KEY \
         OPENCODE_GO_API_KEY; do
-        for fn in ccda ccdd ccddg ccdu; do
+        for fn in ccdd ccddg ccdu; do
             assert_absent "${dump_dir}/${fn}.log" "^${source_key}="
         done
     done
 
     # 各関数が実際に起動し、自身の割り当て値で子プロセスを呼んだことの裏付け
-    assert_contains "${dump_dir}/ccda.log" '^ANTHROPIC_AUTH_TOKEN=fake-maas$'
     assert_contains "${dump_dir}/ccdd.log" '^ANTHROPIC_AUTH_TOKEN=fake-di$'
     assert_contains "${dump_dir}/ccddg.log" '^ANTHROPIC_AUTH_TOKEN=fake-di$'
     assert_contains "${dump_dir}/ccdu.log" '^ANTHROPIC_API_KEY=fake-open$'
diff --git a/.devcontainer/test-readme.bash b/.devcontainer/test-readme.bash
index 174f9ea353b17fe72369547bd0958a006d8df784..d55f75f7ac01bce78461213036c5177b64ff9a90 100755
--- a/.devcontainer/test-readme.bash
+++ b/.devcontainer/test-readme.bash
@@ -57,6 +57,9 @@ if git grep -n 'symlink' -- .devcontainer/docs/herdr-session-cwd-restore.md; the
 # 6. 除外したエージェントの導入・mount・起動を .devcontainer に戻さない（ホストに残るパスを案内する README の注記は対象外）
 excluded='@deepseek-ai/dsh|DeepSeek Harness|DSH_|dsh-settings|dsh-cordis|dsh (plugin|web|--)|HOME\}?/\.dsh|vscode/\.dsh|pnpmVersion": "[0-9]|3080'
 excluded+='|x\.ai/cli|HOME\}?/\.grok|vscode/\.grok|grok update|-a grok'
+excluded+='|function claude-alibaba|ccda \(\)|-u MAAS_ANTHROPIC_TOKEN|maas\.aliyuncs'
 if git grep -n -E "$excluded" -- .devcontainer "$self"; then fail '.devcontainer still sets up an excluded agent'; fi
+# 撤去した ccda の MAAS_ANTHROPIC_TOKEN を env から消すよう案内する（残すとプロバイダ切替ランチャーの子プロセスに渡る）
+grep -qF '`MAAS_ANTHROPIC_TOKEN` は、もう使わない' "$readme" || fail 'README must tell users to remove MAAS_ANTHROPIC_TOKEN from env'
 
 printf 'PASS: README tool table matches the Dev Container files\n'
ISSUE18_PATCH
````

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-herdr-migration.bash .devcontainer/test-readme.bash`

Expected: 2 本とも FAIL。`test-herdr-migration.bash` は `.devcontainer/zshrc.txt must not contain claude-alibaba|ccda|MAAS_ANTHROPIC_TOKEN|maas\.aliyuncs`、`test-readme.bash` は `FAIL: .devcontainer still sets up an excluded agent`（`zshrc.txt` の `function claude-alibaba ccda ()` などを表示する）

- [ ] **Step 3: ccda を撤去する**

`zshrc.txt` から `claude-alibaba` / `ccda` 関数と `cc_launcher_unsets` の `-u MAAS_ANTHROPIC_TOKEN` を削除し、共有リストのコメントを 3 つのランチャーにする。README のツール表の Claude Code の行から `ccda` を外し、秘密情報の例から `MAAS_ANTHROPIC_TOKEN` を外して削除の案内を足し、注記に `ccda` を足す。

````bash
git apply --index --3way <<'ISSUE18_PATCH'
diff --git a/.devcontainer/README.md b/.devcontainer/README.md
index 8a2f48058e69103e56f5b64cab0157f5e4a40587..f3fa60071da830bac8f6ab3611eaf5277090089c 100644
--- a/.devcontainer/README.md
+++ b/.devcontainer/README.md
@@ -23,7 +23,7 @@ Herdr の復元手順は `.devcontainer/docs/herdr-session-cwd-restore.md` を
 <!-- tool-table:start -->
 | ツール | 導入方法 | mount | initialize.bash の mkdir | zshrc の関数 | update() の項目 |
 | --- | --- | --- | --- | --- | --- |
-| Claude Code | installer（`claude.ai/install.sh`）。プラグインは `.claude/settings.json` の `enabledPlugins` と同じ 5 つ | `~/.claude`、`~/.claude.json` | `~/.claude`、`~/.claude.json`（touch） | `ccd`（alias）、`ccda`、`ccdd`、`ccddg`、`ccdu` | `claude update` |
+| Claude Code | installer（`claude.ai/install.sh`）。プラグインは `.claude/settings.json` の `enabledPlugins` と同じ 5 つ | `~/.claude`、`~/.claude.json` | `~/.claude`、`~/.claude.json`（touch） | `ccd`（alias）、`ccdd`、`ccddg`、`ccdu` | `claude update` |
 | Codex | `npm install -g @openai/codex@latest` | `~/.codex` | `~/.codex` | `cod` | `npm install -g @openai/codex@latest` |
 | pi | `npm install -g` で本体、`pi install` で拡張。ランチャー 9 本を `~/.local/bin` に置く | `~/.pi` | `~/.pi` | — | `pi update`、`pi update --extensions` |
 | Cursor | installer（`cursor.com/install`） | `~/.cursor`、`~/.local/share/cursor-agent` | `~/.cursor`、`~/.local/share/cursor-agent` | `cur`（alias） | `agent update` |
@@ -36,7 +36,7 @@ Herdr の復元手順は `.devcontainer/docs/herdr-session-cwd-restore.md` を
 未導入のツールを呼ぶ関数（`cod`、`genv`、`buni`）は、コマンドが無ければ理由を表示して 127 を返す。
 `update()` は無いツールの項目を飛ばし、飛ばした項目を表示する。
 
-dsh と Grok Build（`grok`）は、リポジトリでは導入も mount もしない。ホストの `~/.dsh`・`~/.grok` は
+dsh と Grok Build（`grok`）は、リポジトリでは導入も mount もしない。Claude Code を Alibaba Cloud 経由で使う `ccda`（`claude-alibaba`）も置かない。ホストの `~/.dsh`・`~/.grok` は
 Dev Container から見えなくなるだけで、削除しない。不要になったら利用者がホスト側で消す。
 リビルドする前のコンテナには、導入済みの `dsh` が残る。
 
@@ -53,9 +53,12 @@ touch ~/.config/create-reso-world/env && chmod 600 ~/.config/create-reso-world/e
 ```
 
 書式は `KEY=VALUE` の 1 行 1 変数である（zsh が読むので、空白や記号を含む値は引用符で囲む）。
-対象は `DEEPINFRA_TOKEN`、`COMMANDCODE_API_KEY`、`OPENCODE_API_KEY`、`MAAS_ANTHROPIC_TOKEN`、`CONTEXT7_API_KEY` などで、
+対象は `DEEPINFRA_TOKEN`、`COMMANDCODE_API_KEY`、`OPENCODE_API_KEY`、`CONTEXT7_API_KEY` などで、
 書き換えたら新しいシェルを開く。
 
+撤去した `ccda` が使っていた `MAAS_ANTHROPIC_TOKEN` は、もう使わない。`env` に残っていれば削除する。
+プロバイダ切替ランチャー（`ccdd` など）はこの変数を子プロセスから外さないため、残すと子プロセスにも渡る。
+
 ## テストの実行
 
 リポジトリのルートで次を実行する。CI（`.github/workflows/ci.yml`）も同じコマンドを実行する。
diff --git a/.devcontainer/zshrc.txt b/.devcontainer/zshrc.txt
index 092256ff96ab73d2f35767725242e5b3d318cb29..41b51975fadfce4f578422cabdb1e52ea4b08d8a 100644
--- a/.devcontainer/zshrc.txt
+++ b/.devcontainer/zshrc.txt
@@ -63,7 +63,7 @@ alias ccd="claude --dangerously-skip-permissions --model opus"
 alias cur="agent --yolo"
 alias dev="devin --permission-mode dangerous"
 
-# プロバイダ切替ランチャー（ccda / ccdd / ccddg / ccdu）共通の env -u リスト。
+# プロバイダ切替ランチャー（ccdd / ccddg / ccdu）共通の env -u リスト。
 # 親シェルで export された主要な認証材料・プロバイダ切替・モデルピン留系の値が
 # 第三者プロバイダの子プロセスへ漏れるのを防ぐ。対象範囲の正本は
 # test-herdr-migration.bash の expected_unsets。関数側で代入する変数は
@@ -71,7 +71,6 @@ alias dev="devin --permission-mode dangerous"
 typeset -a cc_launcher_unsets=(
     -u ANTHROPIC_AUTH_TOKEN
     -u ANTHROPIC_API_KEY
-    -u MAAS_ANTHROPIC_TOKEN
     -u DEEPINFRA_TOKEN
     -u COMMANDCODE_API_KEY
     -u OPENCODE_GO_CLAUDE_API_KEY
@@ -117,24 +116,6 @@ typeset -a cc_launcher_unsets=(
     -u ANTHROPIC_BETAS
 )
 
-function claude-alibaba ccda () {
-  local flash=deepseek-v4-flash-0731
-  local -a opts
-  [[ $funcstack[1] == ccda ]] && opts=(--dangerously-skip-permissions)
-
-  env "${cc_launcher_unsets[@]}" \
-    ANTHROPIC_BASE_URL="https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic" \
-    ANTHROPIC_AUTH_TOKEN="${MAAS_ANTHROPIC_TOKEN:?MAAS_ANTHROPIC_TOKEN is not set}" \
-    ANTHROPIC_DEFAULT_FABLE_MODEL=qwen3.8-max \
-    ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-v4-pro-0813 \
-    ANTHROPIC_DEFAULT_SONNET_MODEL=${flash} \
-    ANTHROPIC_DEFAULT_HAIKU_MODEL=qwen3.8-flash \
-    ENABLE_CLAUDEAI_MCP_SERVERS=false \
-    CLAUDE_CODE_EFFORT_LEVEL=max \
-    CLAUDE_CODE_MAX_OUTPUT_TOKENS=65536 \
-    claude --model fable "${opts[@]}" "$@"
-}
-
 function claude-deepinfra ccdd () {
   local fable=deepseek-ai/DeepSeek-V4.1-Flash
   local opus=zai-org/GLM-5.3-Flash
ISSUE18_PATCH
````

- [ ] **Step 4: テストが通ることを確かめる**

Run:

```bash
bash .devcontainer/run-tests.bash .devcontainer/test-herdr-migration.bash .devcontainer/test-readme.bash .devcontainer/test-shell-tools.bash
zsh -n .devcontainer/zshrc.txt && echo ZSH_OK
```

Expected: `PASS: 3 test(s)`、`ZSH_OK`

- [ ] **Step 5: コミットする**

```bash
git status --short
git commit -m "chore(zsh): remove the ccda (claude-alibaba) launcher

ccda 関数と、共有の env -u リストの MAAS_ANTHROPIC_TOKEN を撤去する。
README で env からの削除を案内する。ccdd・ccddg・ccdu は変えない。Issue #18。

Co-Authored-By: <コミットするエージェントのモデル名> <noreply@anthropic.com>"
```

Expected: `git status --short` は Step 1・3 のファイルだけを `M` で表示する

### Task 4: ルートの文書から dsh を外す

**Files:**
- Modify: `AGENTS.md`、`README.md`
- Test: `tests/scripts/test-docs.bash`

**Interfaces:**
- Consumes: Task 1 で `.devcontainer/README.md` の「エージェントの読み込みの制約」を Cursor だけにした状態
- Produces: 対象エージェントの一覧（Claude Code、Codex、pi、Cursor、Devin）

- [ ] **Step 1: テストを新方針に変える**

`tests/scripts/test-docs.bash` の必須の記述「Cursor と dsh」を「Cursor: スキルの一部が見えない」にし、`AGENTS.md`・`README.md` に `dsh` が無いことを確かめる。

````bash
git apply --index --3way <<'ISSUE18_PATCH'
diff --git a/tests/scripts/test-docs.bash b/tests/scripts/test-docs.bash
index 4ebd8618c7f815156f6217a1a74c81e03d6d6b3b..0510f23233812b6d76ec98309409a16af41725fb 100755
--- a/tests/scripts/test-docs.bash
+++ b/tests/scripts/test-docs.bash
@@ -37,7 +37,9 @@ for section in 秘密情報 エージェントの読み込みの制約; do
 done
 
 # 3. N-3: エージェントごとに初回に要る操作と制約
-for s in 'trust' 'cursor-agent' '.devin/config.json' 'sp-*.md' 'Cursor と dsh'; do has README.md "$s"; done
+for s in 'trust' 'cursor-agent' '.devin/config.json' 'sp-*.md' 'Cursor: スキルの一部が見えない'; do has README.md "$s"; done
+# 撤去した dsh を対象エージェントに戻さない
+for f in AGENTS.md README.md; do lacks "$f" 'dsh'; done
 
 # 4. 統合手順: マージ前の片付け（P-1）、一覧の件数（N-4）、sp-implementer.md の比較先と同じシェル（N-12）、
 #    main の再 ff（M-5）、/private/ の行を消す時期（P-2）、Rebuild 後の確認（N-17・N-18・N-25・N-27）
ISSUE18_PATCH
````

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash tests/scripts/test-docs.bash`

Expected: `FAIL: README.md lacks: Cursor: スキルの一部が見えない`

- [ ] **Step 3: 一覧から dsh を外す**

`AGENTS.md` と `README.md` の対象エージェントの一覧から dsh を外し、`README.md` の「Cursor と dsh:」を「Cursor:」にする。

````bash
git apply --index --3way <<'ISSUE18_PATCH'
diff --git a/AGENTS.md b/AGENTS.md
index 704fe2e9b9e104df2a07dc7945d9061e720f053d..92f9bdbc898f9eba3fe5f8d7ce18582714dda4ee 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -1,6 +1,6 @@
 # create-reso-world 共通規約
 
-このリポジトリで作業するコーディングエージェント（Claude Code、Codex、pi、Cursor、Devin、dsh）の共通規約。Claude Code 固有の注意は `CLAUDE.md`、pi 固有の注意は `.pi/APPEND_SYSTEM.md` にある。ワールドのプロジェクトでは、この規約に加えてプロジェクト直下の `AGENTS.md` が適用される。
+このリポジトリで作業するコーディングエージェント（Claude Code、Codex、pi、Cursor、Devin）の共通規約。Claude Code 固有の注意は `CLAUDE.md`、pi 固有の注意は `.pi/APPEND_SYSTEM.md` にある。ワールドのプロジェクトでは、この規約に加えてプロジェクト直下の `AGENTS.md` が適用される。
 本文に書くパスは、プロジェクトを cwd にしている場合も含めて、特記が無ければリポジトリのルート基準である。
 
 ## リポジトリ概要
diff --git a/README.md b/README.md
index 4131576c1a6783a71042a066a53f473cae222da2..710f00015bff5b24f27d05887e692d434f7cf8fc 100644
--- a/README.md
+++ b/README.md
@@ -1,7 +1,7 @@
 # create-reso-world
 
 [resoloop](https://github.com/orange3134/resoloop) と Blender で Resonite のワールドを作るための開発環境（Dev Container）と、
-ワールドのプロジェクトをまとめたリポジトリ。コーディングエージェント（Claude Code、Codex、pi、Cursor、Devin、dsh）で
+ワールドのプロジェクトをまとめたリポジトリ。コーディングエージェント（Claude Code、Codex、pi、Cursor、Devin）で
 作業する前提で、共通の規約とスキルをリポジトリに置いている。
 
 ## 構成
@@ -44,7 +44,7 @@
 - Codex: プロジェクトを信頼（trust）すると、`.codex/config.toml` の MCP の設定（context7）が読まれる。初回の起動時に承認する。
 - cursor-agent: `.cursor/mcp.json` の MCP サーバーは、初回に承認を求められる。
 - Devin: `.claude/skills` の symlink 経由で同じスキルが見えても、一覧には 1 回だけ表示される（`.devin/config.json` は置かない）。
-- Cursor と dsh: スキルの一部が見えない。詳細は `.devcontainer/README.md` の「エージェントの読み込みの制約」。
+- Cursor: スキルの一部が見えない。詳細は `.devcontainer/README.md` の「エージェントの読み込みの制約」。
 - pi-superagents: 組み込みと同じ定義（`sp-*.md`）は追跡しない。独自に変えた `.agents/sp-implementer.md` だけを追跡する。
 
 ## プロジェクトを作る
ISSUE18_PATCH
````

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash tests/scripts/test-docs.bash`

Expected: `PASS: README and integration docs follow spec 4.1 and 10.1`

- [ ] **Step 5: コミットする**

```bash
git status --short
git commit -m "docs: drop dsh from the supported coding agents

AGENTS.md と README.md の対象エージェントの一覧から dsh を外す。Issue #18。

Co-Authored-By: <コミットするエージェントのモデル名> <noreply@anthropic.com>"
```

Expected: `git status --short` は Step 1・3 のファイルだけを `M` で表示する

### Task 5: 全体を検証して取り込む

**Files:**
- なし（検証と、指示がある場合の push・PR の作成だけ）

**Interfaces:**
- Consumes: Task 1〜4 のコミット
- Produces: #22 が使う比較表の行（Spec 9 章）と、#19・#21 が引き継ぐ `main` の状態

- [ ] **Step 1: 全体のテストを実行する**

Run:

```bash
bash scripts/check-layout.sh
bash .devcontainer/run-tests.bash
uv run pytest tests/skills .agents/skills
```

Expected: `check-layout` は `FAIL: resoloop skills sync --check failed for slum03` の 1 件だけで失敗する（`main` と同じ）。`run-tests.bash` は `FAIL: 1 of 25 test(s) failed: tests/scripts/test-check-layout.bash`（失敗の理由は slum03 の未同期）。pytest は `267 passed, 1 skipped`（`9699e94` を基準にした件数。`origin/main` を取り込んで件数が変わっても、失敗が 0 件であればよい）。着手時に slum03 の未同期が解消されていれば、3 つとも全件通る

- [ ] **Step 2: Review Focus を確かめる**

Run:

```bash
[ "$(grep -c '^step "' .devcontainer/install_beforehand.bash)" = "$(grep -oP '^readonly STEP_TOTAL=\K[0-9]+' .devcontainer/install_beforehand.bash)" ] && echo STEP_TOTAL_OK
git diff --exit-code "$(git merge-base HEAD origin/main)" -- .devcontainer/pixg .devcontainer/pi-superagents .devcontainer/pi-superagents-exec.zsh .agents .claude/skills && echo OUT_OF_SCOPE_UNCHANGED
git grep -n -i -E '\bdsh\b|\.dsh|deepseek harness|\.grok\b|grok update|x\.ai/cli|ccda|claude-alibaba|MAAS_ANTHROPIC|3080|pnpm' -- ':!.agents/skills' ':!docs/superpowers' ':!slum0*' ':!akichi' ':!MyResoniteProject'
```

Expected: `STEP_TOTAL_OK`、`OUT_OF_SCOPE_UNCHANGED`。最後のコマンドは、次の意図した記述だけを表示する: `.devcontainer/README.md` の注記（dsh・Grok Build・`ccda` を置かないこと、ホストのパス、`MAAS_ANTHROPIC_TOKEN` の削除の案内）、`.devcontainer/devcontainer.json` の pnpm のコメントと `"pnpmVersion": "none",`、`.devcontainer/test-herdr-migration.bash`・`test-initialize-mounts.bash`・`test-readme.bash`・`tests/scripts/test-docs.bash` の検査とコメント

- [ ] **Step 3: 取り込む**

利用者の実行指示に push と PR の作成が含まれる場合だけ行う。

```bash
git log --oneline origin/main..HEAD
git push -u origin feat/issue-18-remove-excluded-agents
gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-18-remove-excluded-agents \
  --title "chore: Grok Build・ccda・dsh の導線を撤去する（#18）" --body-file <PR 本文のファイル>
```

PR 本文には、`Closes #18`、変更の要約（Task 1〜4）、Spec と計画のパス、Step 1・2 の検証結果（既知の失敗を含む）、未検証の項目（Dev Container の rebuild は #22 で行う）を書く。末尾に、PR を作るエージェントの決まりに従った生成の記載を付ける。既存の PR があれば、新しく作らずに再利用する。

Expected: `git log` は Spec・計画のコミットと Task 1〜4 の 4 コミットを表示する。PR の URL が表示される

- [ ] **Step 4: 作業報告を書く**

#18 にコメントで、`implementation: done`（PR を作った場合は PR の URL）、検証結果、所要時間と Task ごとの内訳、未検証の項目を書く。#18 の close は PR のマージで行う（`Closes #18`）
