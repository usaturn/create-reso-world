# create-reso-world 再設計 フェーズ 4（Dev Container と CI）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dev Container の設定一式（mount、postCreate、zsh と starship の設定、掃除スクリプト、README）を仕様 7 章のとおりに整え、`.devcontainer/run-tests.bash` と GitHub Actions の CI（仕様 9.2 節）で検証できるようにする。あわせて、フェーズ 3 までに持ち越した P-4・N-1・N-6・N-8・N-11・N-19〜N-22 を片付ける。

**Architecture:** `devcontainer.json` の mounts、`initialize.bash` が作るパス、postCreate が書き込み可能にするディレクトリ、README の導入ツール一覧は、`.devcontainer/mounts.bash` の関数で突き合わせる（テストと `scripts/check-layout.sh` の両方が使う）。未導入のツールに触れる zsh の関数は、先にコマンドの有無を確かめる。テストはすべてモックと一時 `HOME` で動き、`.devcontainer/run-tests.bash` が `.devcontainer/test-*.bash` と `tests/scripts/*.bash` をまとめて実行する。CI はこのスクリプト、check-layout、スキルのテスト、gitleaks の 4 ジョブで構成する。

**Tech Stack:** bash（`set -euo pipefail`、既存のテストと同じ書き方）、zsh、git、Dev Container（`devcontainer.json` は JSONC）、starship、GitHub Actions（`actions/checkout@v7`、`astral-sh/setup-uv@v10`、`gitleaks/gitleaks-action@v3`）、gitleaks 8.30、uv / pytest / PyYAML（CI 定義の検査）

**Spec:** `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md`（4.1 節の pi 用スクリプトの移動、7 章、9.1 節のマウント検査、9.2 節、10 章のフェーズ 4）。前フェーズの計画は `docs/superpowers/plans/2026-09-27-redesign-phase3-resoloop-lock-and-fork.md`。

## 判断事項（2026-09-27、controller の裁定）

2026-09-27 にユーザが「PR を出すまで止めないでください」と指示した。これを、フェーズ 4〜6 の計画の承認をフェーズごとに待たず、controller の裁定で進めてよいという指示として扱う。裁定はこの表と SDD の台帳に残し、PR の説明にも一覧で載せる。計画の作成時に、scratchpad に作業用の複製を作って全 Task のコードとテストを実行し、通ることを確かめた。各テストが対象の修正を検出することは、実装をわざと壊すミューテーションで確かめた。あわせて、resoloop・dotnet・Blender・各エージェントの CLI を PATH から外した CI 相当の環境で、テスト一式が通ることも確かめた。gitleaks は既定の規則だと履歴に 968 件の誤検出が出ることを実測し、除外の設定を試してから載せた。

| ID | 事項 | 本計画の内容 | 理由 |
| --- | --- | --- | --- |
| D-9 | 計画の承認 | ユーザの上記の指示により、controller の裁定で承認して実行する | 指示の趣旨はフェーズ 6 の PR まで止まらずに進むこと。引き継ぎ書の禁止事項（force push、main の直接変更など）は引き続き守る |
| D-10 | `remoteEnv.PATH` の書き方 | 仕様 7.2 の `${containerEnv:HOME}` ではなく、既存の mounts と同じく `/home/vscode/.local/bin`・`/home/vscode/bin`・`/home/vscode/.dotnet/tools` を直接書く | `${containerEnv:...}` はコンテナの既存の環境変数を読むが、このコンテナの PID 1 は root で動いている。そのため `HOME` が `/root` に解決されるおそれがあり、資料からも確定できなかった。mounts の target も `/home/vscode` を直接書いている |
| D-11 | `run-tests.bash` の対象 | `.devcontainer/test-*.bash` に加えて `tests/scripts/*.bash` も実行する。CI の devcontainer-tests ジョブはこれを実行する（N-1） | 仕様 11 章の成功条件（clone 直後に `run-tests.bash` が通る）がスクリプトのテストも含むようにする。仕様 8.2 の review-fix-planning の検証ゲートも 1 コマンドで済む |
| D-12 | CI の skill-tests ジョブ | 仕様 9.2 のとおり `uv run pytest tests/skills .agents/skills` を今入れる。フェーズ 5 で既知の 34 件の失敗を直すまで、このジョブは失敗する | 除外の設定を足すと、外し忘れたときに失敗を隠す。PR はフェーズ 6 まで開かない |
| D-13 | gitleaks の設定 | ルートに `.gitleaks.toml` を置き、既定の規則はそのまま使う。resoloop のマニフェストが持つ識別子（`"key": "mat_material_Slum02_rubber_d4d07289"` など）だけを generic-api-key の対象から外す | 既定の規則だけでは履歴で 968 件の誤検出が出て、ワールドを作るたびに CI が失敗する。形式の決まったトークンは専用の規則で引き続き検出され、無作為な文字列の値も検出されることを試した |
| D-14 | 移行元リポジトリの Issue 番号 | 仕様 7.2 が挙げる README と cleanup に加えて、`.devcontainer` 配下のすべてのファイルから外す。他のプロジェクトの PR へのリンク（pi-superagents #72 など）は残す | 番号の指す先がこのリポジトリに無い。README のテストが `.devcontainer` 全体で検査する |
| D-15 | README の旧節 | 「npm への一本化と既存環境の移行」（yarn 時代のコンテナの移行手順）と「Codex で `CLAUDE.md` を指示ファイルとして読む」を削除する。代わりに「エージェントの読み込みの制約」節を置き、Cursor と dsh の制約（仕様 5.1）と、Codex の設定が不要になったこと（仕様 5.5）を書く | 前者の移行元のコンテナはこのリポジトリには無い。後者は仕様 7.2 の指示 |
| D-16 | ペルソナ節の sha256 の固定（N-11） | 固定を残し、失敗したときに新しいハッシュと更新の手順を表示する | ペルソナ節は利用者が書く部分で、エージェントが変えないことを CI でも守る。利用者が意図して変えたときだけ値を更新する |
| D-17 | 秘密情報の読み込み | `~/.config/create-reso-world/env` を `set -a` の下で読み、書いた変数をすべて export する（`KEY=VALUE` の書式）。`initialize.bash` はディレクトリを mode 700 にする | トークンを使うのはランチャーや子プロセスなので export が要る。ホスト側で本人以外が読めないようにする |
| D-18 | 書き込み可能にするディレクトリ | postCreate の `ensure_user_writable_dir` の一覧に、ディレクトリの mount をすべて並べる（`~/.codex`、`~/.grok`、`~/.config/create-reso-world` を足す） | Docker が root 所有で作った mount の target に書けないと、後続のステップが失敗する。テストで mounts と突き合わせる |
| D-19 | CI の実行環境 | `ubuntu-latest` に apt で `zsh`・`ripgrep`・`bubblewrap` を入れ、uv は `astral-sh/setup-uv@v10` で入れる。gitleaks の PR へのコメントは切る（`permissions: contents: read` のまま） | テストが使うのはこの 3 つ（bubblewrap はコマンドの有無を見るだけで、実際には起動しない）。コメントには書き込み権限が要る |
| D-20 | mounts の読み方 | 行単位で読む。`devcontainer.json` は 1 行に 1 つの `"source=${localEnv:HOME}/<rel>,target=/home/vscode/<rel>,..."`、`initialize.bash` は `"${HOME}/<rel>"` だけを書いた行（`mounts.bash` の冒頭に明記）。check-layout の検査 9 は 3 つのファイルを index から読む（D-6 と同じ） | JSONC をそのまま読む道具を増やさない。書式から外れた書き方は検査が差分として報告する |

仕様 10 章のフェーズ 4 の完了条件（`run-tests.bash` の全通過）は Task 11 で確認する。コンテナの Rebuild を伴う確認（`remoteEnv.PATH`、秘密情報の mount、`initialize.bash` がホストで作るディレクトリ）は、仕様 9.3 の実機確認に回す（持ち越し N-25）。

## Global Constraints

- 変数: `M=/workspaces/reso-world`（メイン作業ツリー。ブランチ feat/slum02-slum で、別セッションが slum02 を編集中）、`W=/workspaces/reso-world/.worktrees/repo-redesign`（作業用 worktree。ブランチ chore/repo-redesign）。各ステップのコマンドは `export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign` を実行してから、特記が無ければ `cd "$W"` で実行する。
- メイン作業ツリー `$M` では読み取りだけを行う。追跡ファイルの編集、`git add` / `commit` / `checkout` / `stash` / `reset` / `clean` / `fetch`、ファイルの移動・削除をしない。
- 変更のコミットはすべて `$W` で行う。コミットメッセージの末尾に、コミットするエージェント自身のモデル名の trailer を付ける（例: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`）。
- `git add` には明示したパスだけを渡す。`$W` で `git add -A` / `git add .` を使わない（テストが作る一時リポジトリの中は除く）。
- `git push --force` 系を使わない。push は Task 11 で controller が `git push origin chore/repo-redesign`（fast-forward を確かめてから）だけ行う。`main`・`feat/*`・`wip/*` を push・rebase・削除しない。PR を開かない（フェーズ 6）。
- Python は uv で実行する（`uv run ...`、`uv run --no-project ...`）。`python3` を直接呼ばない（既存のテストと zsh のヘルパーが中で使うものは除く）。
- 説明・文書・コミットの日本語で「契約」「原子的」「製品」「着地」を使わない。
- 触らないもの: TRPG 本文（`private/trpg/`、`tmp/` の `ATS.txt`・`BTD.txt`・`TNX.txt`）、`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json`、`.pi/APPEND_SYSTEM.md`（特に `## Response Persona` 以降）、`.git/info/exclude`、`.mcp.json`、スキルの本文（`.agents/skills/`。フェーズ 5）、ルートの README（フェーズ 6）。
- **実環境を変えるコマンドを実行しない。** `dotnet tool install` / `update` / `uninstall`、`install_beforehand.bash`、モックを使わない `install_resoloop.bash`、実ロックに対する `scripts/resoloop-fork.sh sync|build|test|install`、実際の `HOME` での `initialize.bash`、実際の `~/.zshrc` への追記は行わない。テストは必ず一時ディレクトリの `HOME`、モックのコマンド、ローカルの一時リポジトリで行う。
- 既存プロジェクトのディレクトリの中で `resoloop init` や `resoloop skills sync --update` を実行しない。`resoloop skills sync` は `--check` だけ使う。
- テストの書き方: `コマンド | grep -q` は、出力の最終行を照合するときにだけ使う。途中の行を照合するときは、出力をファイルか変数に取ってから `grep` する（`pipefail` の下では `grep -q` が早く終わると上流が SIGPIPE で 141 になる）。パイプの途中の `grep` が一致なしで失敗すると `set -e` で黙って終わるので、失敗を許すところは `|| true` を付ける。
- ルートの pytest の既知の失敗: `pi-model-name/tests/test_pi_model_name_contract.py` の 27 件と `repository-ownership/tests/test_public_release_guidance.py` の 7 件の計 34 件（どちらもフェーズ 5 で扱う）。各 Task の最後に次を実行し、何も表示されないことを確認する。

```bash
cd "$W" && uv run pytest -q -rf 2>&1 | grep '^FAILED' \
  | grep -v -e 'pi-model-name/tests/test_pi_model_name_contract.py' \
            -e 'repository-ownership/tests/test_public_release_guidance.py' || true
```

- 各 Task の後に次も通る: `for t in .devcontainer/test-*.bash tests/scripts/*.bash; do bash "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done`（Task 2 からはすべて PASS。Task 1 の時点では `test-herdr-migration.bash` だけが既知の FAIL。Task 9 からは `bash .devcontainer/run-tests.bash` で同じことを行う）、`bash scripts/check-layout.sh`（最終行が `PASS: check-layout`）、`git ls-files -i -c --exclude-standard`（`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json` の 1 行だけ）。
- 各 Task の差分は `git diff` の形式で載せてある。Markdown から保存して `git apply` で当ててもよい。その場合、`devcontainer.json` と `test-check-layout.bash` のヒアドキュメントのインデントはタブなので崩さない。手で書き写すときも同じ結果にする。
- フェーズ 4 の範囲外（持ち越し節を参照）に手を出さない。

## Review Focus

- mount のソースがまだ無いホストでの初回作成と Rebuild: `initialize.bash` はすべてのソースを作り、ファイルの mount（`~/.claude.json`）は通常ファイルのままで、中身を消さない。秘密情報のディレクトリは mode 700。何度実行しても同じ結果になる（Task 3 のケース 3）。
- grok・gcloud・bun・Codex などを入れていない利用者のシェル: 読み込みで `command not found` を出さない。`update()` は無いツールを飛ばして 0 を返す。`buni` は bun が無ければ `node_modules` を消さずに止まる（Task 4 のケース 1〜4）。
- リポジトリの所有者がテストを実行するユーザと違う checkout（CI のコンテナや Dev Container の bind mount）: git の設定を隔離したテストでも、このリポジトリを読める（Task 8。所有者を変えた複製での確認は Task 11 の手順 4）。
- 衝突の解決中や、オブジェクトが壊れた index に対する check-layout: 終了コード 128 で黙って止まらず、1 で原因を示す（Task 6 のケース 51・52）。
- resoloop・dotnet・Blender・各エージェントの CLI が無い CI のランナー: `run-tests.bash` はモックだけで通り、apt で足すのは zsh・ripgrep・bubblewrap だけで済む（Task 9 と Task 11 の手順 3）。

## 実行前の準備（controller）

- [ ] 1. 計画作成時点で worktree はクリーンで、HEAD は `eca7a5e` だった。本計画書をコミットする（`docs: add redesign phase 4 implementation plan`）。
- [ ] 2. SDD の作業ディレクトリと台帳を作る（`bash <sdd-skill>/scripts/sdd-workspace <この計画のパス>`）。
- [ ] 3. フェーズ 3 の SDD 作業ディレクトリ `$W/.superpowers/sdd/2026-09-27-redesign-phase3-resoloop-lock-and-fork/` を削除する。保留事項は本計画の Task と「持ち越し」節に転記済み（PH3-R5）。

---

### Task 1: pi 用スクリプトを `.devcontainer/` へ移す（仕様 4.1、7.2 のパスの修正）

`scripts/` に残っている Dev Container の構築専用のスクリプト 5 本を `.devcontainer/` に移し、参照するファイルのパスを直す。スクリプトの中身の変更は、自分の位置からリポジトリや `.devcontainer` を求める行だけにする。

**Files:**
- Move: `scripts/setup_pi.zsh`、`scripts/setup_pi_commandcode_goat.zsh`、`scripts/setup_pi_opencode_go.zsh`、`scripts/setup_pi_superagents.zsh`、`scripts/setup_pi_tool_display.py` → `.devcontainer/`（mode はそのまま。`.zsh` は 100755、`.py` は 100644）
- Modify: `.devcontainer/setup_pi.zsh:13`、`.devcontainer/setup_pi_commandcode_goat.zsh:60`、`.devcontainer/setup_pi_opencode_go.zsh:39,51`（自分の位置からのパス）
- Modify（`scripts/setup_pi` を `.devcontainer/setup_pi` に置き換えるだけ）: `.devcontainer/install_beforehand.bash`、`.devcontainer/pi-superagents-exec.zsh`、ランチャー 9 本（`piccd`、`piccg`、`piga`、`pigl`、`pigo`、`pigod`、`pigou`、`pigs`、`pixg`）、`.devcontainer/setup_pi_superagents.zsh`、`.devcontainer/README.md`
- Test: `.devcontainer/test-pi-openai-codex.bash`、`.devcontainer/test-pi-superagents.bash`（同じ置き換え）

**Interfaces:**
- Produces: 以降の Task は `.devcontainer/setup_pi_tool_display.py` と `.devcontainer/setup_pi_superagents.zsh` のパスを使う。

- [ ] **Step 1: テストの参照先を新しい位置に変え、失敗することを確かめる**

```bash
cd "$W"
sed -i 's#scripts/setup_pi#.devcontainer/setup_pi#g' .devcontainer/test-pi-openai-codex.bash .devcontainer/test-pi-superagents.bash
bash .devcontainer/test-pi-openai-codex.bash; echo "exit=$?"
```

Expected: FAIL（`pi-superagents setup failed: ... .devcontainer/setup_pi_superagents.zsh: No such file or directory` の類）。exit は 0 以外。

- [ ] **Step 2: 5 本を移し、参照を直す**

```bash
cd "$W"
for f in setup_pi.zsh setup_pi_commandcode_goat.zsh setup_pi_opencode_go.zsh setup_pi_superagents.zsh setup_pi_tool_display.py; do
  git mv "scripts/$f" ".devcontainer/$f"
done
git grep -l 'scripts/setup_pi' -- .devcontainer | xargs sed -i 's#scripts/setup_pi#.devcontainer/setup_pi#g'
sed -i 's#"${0:A:h}/../.devcontainer/pi-models.json"#"${0:A:h}/pi-models.json"#' \
  .devcontainer/setup_pi.zsh .devcontainer/setup_pi_opencode_go.zsh
sed -i 's#^readonly DEVCONTAINER_DIR="${0:A:h}/../.devcontainer"#readonly DEVCONTAINER_DIR="${0:A:h}"#' .devcontainer/setup_pi_commandcode_goat.zsh
sed -i 's#^readonly LAUNCHER_DIR="${0:A:h}/../.devcontainer"#readonly LAUNCHER_DIR="${0:A:h}"#' .devcontainer/setup_pi_opencode_go.zsh
git grep -n 'scripts/setup_pi\|/\.\./\.devcontainer' -- . ':!docs/superpowers'
```

Expected: 最後の `git grep` は何も表示しない。`setup_pi_superagents.zsh` の `REPO_ROOT="${0:A:h}/.."` は移動後もリポジトリのルートを指すので変えない。変更の全体は次のとおり（`git diff --stat -M` で 19 ファイル、41 行の追加と 41 行の削除）。

```diff
diff --git a/.devcontainer/install_beforehand.bash b/.devcontainer/install_beforehand.bash
index 786e4e8..438f6f9 100755
--- a/.devcontainer/install_beforehand.bash
+++ b/.devcontainer/install_beforehand.bash
@@ -296,7 +296,7 @@ for extension in \
         fail "Failed to install the pi extension ${extension}."
     fi
 done
-if ! python3 scripts/setup_pi_tool_display.py; then
+if ! python3 .devcontainer/setup_pi_tool_display.py; then
     fail "Failed to disable the pi tool-display Bash override."
 fi
 
@@ -349,8 +349,8 @@ fi
 step "Writing the pi-superagents launcher configs"
 # pi-superagents のランチャー別 model tier 設定を配置する。既存の config は
 # 保持する。tier 表を変更したときは、リポジトリのルートで
-# zsh scripts/setup_pi_superagents.zsh を実行して反映する。
-if ! zsh scripts/setup_pi_superagents.zsh --if-absent; then
+# zsh .devcontainer/setup_pi_superagents.zsh を実行して反映する。
+if ! zsh .devcontainer/setup_pi_superagents.zsh --if-absent; then
     fail "Failed to set up pi-superagents launcher configs."
 fi
 
diff --git a/scripts/setup_pi.zsh b/.devcontainer/setup_pi.zsh
similarity index 98%
rename from scripts/setup_pi.zsh
rename to .devcontainer/setup_pi.zsh
index 1d692df..29ab893 100755
--- a/scripts/setup_pi.zsh
+++ b/.devcontainer/setup_pi.zsh
@@ -10,7 +10,7 @@ MODELS_JSON="${PI_DIR}/models.json"
 
 # モデル定義の正は .devcontainer/pi-models.json とする。
 # ここに定義を埋め込むと install_beforehand.bash が配置する内容とずれる。
-MODELS_SOURCE="${0:A:h}/../.devcontainer/pi-models.json"
+MODELS_SOURCE="${0:A:h}/pi-models.json"
 
 echo "=== Pi + DeepInfra setup ==="
 
diff --git a/scripts/setup_pi_commandcode_goat.zsh b/.devcontainer/setup_pi_commandcode_goat.zsh
similarity index 99%
rename from scripts/setup_pi_commandcode_goat.zsh
rename to .devcontainer/setup_pi_commandcode_goat.zsh
index c80fb15..0d1724b 100755
--- a/scripts/setup_pi_commandcode_goat.zsh
+++ b/.devcontainer/setup_pi_commandcode_goat.zsh
@@ -57,7 +57,7 @@ readonly MODELS_JSON="${PI_DIR}/models.json"
 # The model definition and the launchers are kept in the repository so
 # that install_beforehand.bash and this script cannot drift apart.
 #
-readonly DEVCONTAINER_DIR="${0:A:h}/../.devcontainer"
+readonly DEVCONTAINER_DIR="${0:A:h}"
 readonly MODELS_SOURCE="${DEVCONTAINER_DIR}/pi-models.json"
 
 readonly BIN_DIR="${HOME}/.local/bin"
diff --git a/scripts/setup_pi_opencode_go.zsh b/.devcontainer/setup_pi_opencode_go.zsh
similarity index 99%
rename from scripts/setup_pi_opencode_go.zsh
rename to .devcontainer/setup_pi_opencode_go.zsh
index e7e60d4..b13eb45 100755
--- a/scripts/setup_pi_opencode_go.zsh
+++ b/.devcontainer/setup_pi_opencode_go.zsh
@@ -36,7 +36,7 @@ readonly MODELS_JSON="${PI_DIR}/models.json"
 # The model definition is kept in the repository so that
 # install_beforehand.bash and this script cannot drift apart.
 #
-readonly MODELS_SOURCE="${0:A:h}/../.devcontainer/pi-models.json"
+readonly MODELS_SOURCE="${0:A:h}/pi-models.json"
 
 #
 # Launchers placed by this script, as parallel arrays: each launcher is
@@ -48,7 +48,7 @@ readonly MODELS_SOURCE="${0:A:h}/../.devcontainer/pi-models.json"
 #
 readonly LAUNCHER_NAMES=(pigo pigod pigou)
 readonly LAUNCHER_MODELS=("${MODEL}" "deepseek-v4.1-flash" "union-alpha")
-readonly LAUNCHER_DIR="${0:A:h}/../.devcontainer"
+readonly LAUNCHER_DIR="${0:A:h}"
 
 readonly BIN_DIR="${HOME}/.local/bin"
 
diff --git a/scripts/setup_pi_superagents.zsh b/.devcontainer/setup_pi_superagents.zsh
similarity index 95%
rename from scripts/setup_pi_superagents.zsh
rename to .devcontainer/setup_pi_superagents.zsh
index 5d8fe22..0830334 100755
--- a/scripts/setup_pi_superagents.zsh
+++ b/.devcontainer/setup_pi_superagents.zsh
@@ -18,8 +18,8 @@ set -euo pipefail
 # config は更新されない。
 #
 # 使い方:
-#   zsh scripts/setup_pi_superagents.zsh              置き直す（既存はバックアップ）
-#   zsh scripts/setup_pi_superagents.zsh --if-absent  無いものだけ置く
+#   zsh .devcontainer/setup_pi_superagents.zsh              置き直す（既存はバックアップ）
+#   zsh .devcontainer/setup_pi_superagents.zsh --if-absent  無いものだけ置く
 #
 
 readonly REPO_ROOT="${0:A:h}/.."
```

- [ ] **Step 3: テストが通ることを確かめる**

```bash
cd "$W"
bash .devcontainer/test-pi-openai-codex.bash && bash .devcontainer/test-pi-superagents.bash
git ls-files -s .devcontainer/setup_pi* | awk '{print $1, $4}'
```

Expected: 2 本とも PASS。mode は `.zsh` の 4 本が 100755、`setup_pi_tool_display.py` が 100644。

- [ ] **Step 4: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う（この時点では `test-herdr-migration.bash` だけが既知の FAIL）。

```bash
cd "$W"
git add scripts .devcontainer/setup_pi.zsh .devcontainer/setup_pi_commandcode_goat.zsh .devcontainer/setup_pi_opencode_go.zsh \
  .devcontainer/setup_pi_superagents.zsh .devcontainer/setup_pi_tool_display.py .devcontainer/install_beforehand.bash \
  .devcontainer/pi-superagents-exec.zsh .devcontainer/piccd .devcontainer/piccg .devcontainer/piga .devcontainer/pigl \
  .devcontainer/pigo .devcontainer/pigod .devcontainer/pigou .devcontainer/pigs .devcontainer/pixg .devcontainer/README.md \
  .devcontainer/test-pi-openai-codex.bash .devcontainer/test-pi-superagents.bash
git commit -m "chore(devcontainer): move the pi setup scripts next to the launchers

They only run while building the Dev Container, so they now live in
.devcontainer/ (spec 4.1). Paths computed from the script location and every
caller, message and test are updated.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 2: postCreate の導入手順と Claude Code のプラグイン（仕様 7.1・7.2、持ち越し N-6）

`install_beforehand.bash` に Codex の導入と Claude Code のプラグイン 2 つ（superpowers、feature-dev）を足し、uv の導入を pi の設定より前に移す。重複した `apt update` と `PATH` の export を消し、`setup_pi_tool_display.py` を `uv run` で実行する。`.claude/settings.json` の `enabledPlugins` に feature-dev を足して、導入一覧と同じ集合にする。gitleaks はコンテナに入れない方針なので、`test-herdr-migration.bash` の gitleaks の検査を消す。

**Files:**
- Create: `.devcontainer/test-install-beforehand.bash`（mode 100755）
- Modify: `.devcontainer/install_beforehand.bash`、`.claude/settings.json`、`.devcontainer/README.md`（手動導入の手順と `setup_pi_tool_display.py` の実行例の 2 か所）、`.devcontainer/test-herdr-migration.bash`（gitleaks の検査と Issue 番号）

**Interfaces:**
- Produces: `readonly STEP_TOTAL=25`。ステップ名 `Installing Codex` と `Installing uv`（`Installing pi` より前）。Task 3 は同じファイルの `ensure_user_writable_dir` の一覧を変える。

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-install-beforehand.bash` を次の内容で作り、`chmod +x` する。

```bash
#!/bin/bash
# postCreate（.devcontainer/install_beforehand.bash）の導入手順が仕様 7.1・7.2 節のとおりであることを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
installer="$root/.devcontainer/install_beforehand.bash"
settings="$root/.claude/settings.json"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# first_line PATTERN: install_beforehand.bash で PATTERN（grep -E）に一致する最初の行番号。無ければ失敗
first_line() {
  local n
  n="$(grep -m 1 -nE -- "$1" "$installer" | cut -d: -f1 || true)"
  [ -n "$n" ] || fail "install_beforehand.bash lacks: $1"
  printf '%s\n' "$n"
}
# commands PATTERN: コメント行を除いて PATTERN（grep -E）に一致する行数
commands() {
  local body
  body="$(grep -vE '^[[:space:]]*#' "$installer")"
  grep -cE -- "$1" <<<"$body" || true
}

bash -n "$installer"

# 1. Claude Code のプラグインは .claude/settings.json の enabledPlugins と同じ集合を導入する（仕様 7.1）
installed="$(sed -n '/^for plugin in \\$/,/; do$/p' "$installer" | sed -n 's/^[[:space:]]*\([^[:space:];\\]*@[^[:space:];\\]*\).*/\1/p' | LC_ALL=C sort)"
enabled="$(uv run --no-project python - "$settings" <<'PY' | LC_ALL=C sort
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    plugins = json.load(handle)["enabledPlugins"]
for name, enabled in plugins.items():
    if enabled is True:
        print(name)
PY
)"
[ -n "$installed" ] || fail 'no plugin list found in install_beforehand.bash'
[ "$installed" = "$enabled" ] || fail "plugins installed by install_beforehand.bash differ from enabledPlugins:
installed:
$installed
enabled:
$enabled"
for p in superpowers@claude-plugins-official feature-dev@claude-plugins-official; do
  grep -qxF "$p" <<<"$installed" || fail "$p is not installed"
done

# 2. Codex は npm で導入し、PATH に載ったことを確かめる（仕様 7.1・7.2）
codex_step="$(first_line '^step "Installing Codex"$')"
[ "$(first_line '^if ! npm install -g @openai/codex@latest; then$')" -gt "$codex_step" ] || fail 'npm install of Codex is not in its step'
first_line 'command -v codex' >/dev/null

# 3. uv は pi の設定より前に導入し、setup_pi_tool_display.py は uv run で実行する（仕様 7.2）
uv_step="$(first_line '^step "Installing uv"$')"
[ "$uv_step" -lt "$(first_line '^step "Installing pi"$')" ] || fail 'uv must be installed before pi'
[ "$uv_step" -lt "$(first_line 'uv run ')" ] || fail 'uv must be installed before the first uv run'
first_line '^if ! uv run --no-project \.devcontainer/setup_pi_tool_display\.py; then$' >/dev/null
[ "$(commands 'python3')" -eq 0 ] || fail 'install_beforehand.bash must not run python3 directly'

# 4. 重複していた apt update と ~/.local/bin の PATH の export は 1 回だけ（仕様 7.2）
[ "$(commands 'sudo apt update')" -eq 1 ] || fail 'apt update must run exactly once'
[ "$(commands '^export PATH="\$\{HOME\}/\.local/bin:\$\{PATH\}"$')" -eq 1 ] || fail '~/.local/bin must be exported exactly once'

# 5. 移行元リポジトリの Issue 番号をコメントに残さない
if grep -nE '#[0-9]{3}\b' "$installer"; then fail 'install_beforehand.bash still refers to old issue numbers'; fi

printf 'PASS: postCreate installs the tools listed in spec 7.1\n'
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && bash .devcontainer/test-install-beforehand.bash
```

Expected: `FAIL: plugins installed by install_beforehand.bash differ from enabledPlugins:` で終了コード 1。

- [ ] **Step 3: postCreate とプラグインの一覧を直す**

次の差分を当てる。`README.md` は手動導入の手順（プラグインと Codex）と、`setup_pi_tool_display.py` の実行例だけを変える。

````diff
diff --git a/.claude/settings.json b/.claude/settings.json
index 8ce5291..b6f2c54 100644
--- a/.claude/settings.json
+++ b/.claude/settings.json
@@ -8,6 +8,7 @@
   "enabledPlugins": {
     "example-skills@anthropic-agent-skills": true,
     "superpowers@claude-plugins-official": true,
+    "feature-dev@claude-plugins-official": true,
     "web-quality-skills@addy-web-quality-skills": true,
     "ripgrep@alberto-marketplace": true
   },
diff --git a/.devcontainer/README.md b/.devcontainer/README.md
index ff22cca..a37fbb1 100644
--- a/.devcontainer/README.md
+++ b/.devcontainer/README.md
@@ -109,19 +109,22 @@ Dev Container を使わないローカル環境のみ、以下を手動で順に
 
 1. `claude plugin marketplace add dashed/claude-marketplace`
 2. `claude plugin install example-skills@anthropic-agent-skills`
-3. `claude plugin install web-quality-skills@addy-web-quality-skills`
-4. `claude plugin install ripgrep@alberto-marketplace`
-5. `mkdir -p ~/.pi/agent && cp .devcontainer/pi-models.json ~/.pi/agent/models.json`
-6. `mkdir -p ~/.local/bin && install -m 0755 .devcontainer/pigo ~/.local/bin/pigo`
-7. `install -m 0755 .devcontainer/pigod ~/.local/bin/pigod`
-8. `install -m 0755 .devcontainer/pigou ~/.local/bin/pigou`
-9. `install -m 0755 .devcontainer/piccg ~/.local/bin/piccg`
-10. `install -m 0755 .devcontainer/piccd ~/.local/bin/piccd`
-11. `install -m 0755 .devcontainer/piga ~/.local/bin/piga`
-12. `install -m 0755 .devcontainer/pigs ~/.local/bin/pigs`
-13. `install -m 0755 .devcontainer/pigl ~/.local/bin/pigl`
-14. `install -m 0755 .devcontainer/pixg ~/.local/bin/pixg`
-15. `zsh .devcontainer/setup_pi_superagents.zsh`
+3. `claude plugin install superpowers@claude-plugins-official`
+4. `claude plugin install feature-dev@claude-plugins-official`
+5. `claude plugin install web-quality-skills@addy-web-quality-skills`
+6. `claude plugin install ripgrep@alberto-marketplace`
+7. `npm install -g @openai/codex@latest`
+8. `mkdir -p ~/.pi/agent && cp .devcontainer/pi-models.json ~/.pi/agent/models.json`
+9. `mkdir -p ~/.local/bin && install -m 0755 .devcontainer/pigo ~/.local/bin/pigo`
+10. `install -m 0755 .devcontainer/pigod ~/.local/bin/pigod`
+11. `install -m 0755 .devcontainer/pigou ~/.local/bin/pigou`
+12. `install -m 0755 .devcontainer/piccg ~/.local/bin/piccg`
+13. `install -m 0755 .devcontainer/piccd ~/.local/bin/piccd`
+14. `install -m 0755 .devcontainer/piga ~/.local/bin/piga`
+15. `install -m 0755 .devcontainer/pigs ~/.local/bin/pigs`
+16. `install -m 0755 .devcontainer/pigl ~/.local/bin/pigl`
+17. `install -m 0755 .devcontainer/pixg ~/.local/bin/pixg`
+18. `zsh .devcontainer/setup_pi_superagents.zsh`
 
 プラグインの有効化は `.claude/settings.json` の `extraKnownMarketplaces` と
 `enabledPlugins` で行う。設定の反映には Claude Code の再起動が必要である。
@@ -376,7 +379,7 @@ tool result 圧縮は続く。Bash 専用の tool-display 表示は使えなく
 既存環境へ反映するときは、リポジトリのルートで次を実行し、Pi で `/reload` する。
 
 ```bash
-python3 .devcontainer/setup_pi_tool_display.py
+uv run --no-project .devcontainer/setup_pi_tool_display.py
 ```
 
 スクリプトは `PI_CODING_AGENT_DIR` を指定している場合、その agent directory 内の
diff --git a/.devcontainer/install_beforehand.bash b/.devcontainer/install_beforehand.bash
index 438f6f9..1f83d61 100755
--- a/.devcontainer/install_beforehand.bash
+++ b/.devcontainer/install_beforehand.bash
@@ -11,7 +11,7 @@ readonly DSH_COMMANDCODE_PROVIDER_VERSION="0.10.6"
 # 打ち切る（2026-09-13 のリビルド中断インシデント）。継続してよい処理
 # （workspace cleanup）だけを明示的に続行させるため、スクリプト全体には set -e を
 # 付けない。
-readonly STEP_TOTAL=24
+readonly STEP_TOTAL=25
 STEP_NUMBER=0
 
 step() {
@@ -53,7 +53,7 @@ step "Ensuring user-writable directories under ~"
 # bind mount target の中間ディレクトリ（~/.local/share 等）と target 自体は、
 # Docker が root 所有で作る・ホスト側に root 所有のまま残ることがある。
 # 以降の全ステップが $HOME 配下へ書き込むため、最初に親から順に書き込み可能を
-# 保証する（#296）。~/.claude.json はファイル mount のため対象外。
+# 保証する。~/.claude.json はファイル mount のため対象外。
 for dir in \
     "${HOME}/.local" \
     "${HOME}/.local/share" \
@@ -83,9 +83,6 @@ if ! sudo apt update; then
 fi
 
 step "Installing the base packages"
-if ! sudo apt update; then
-    fail "apt update failed before installing the base packages."
-fi
 if ! sudo apt install -y vim tig ripgrep fzf bubblewrap libglib2.0-0t64 blender; then
     fail "apt install of the base packages failed."
 fi
@@ -128,8 +125,11 @@ step "Installing the Claude Code plugins"
 if ! claude plugin marketplace add dashed/claude-marketplace; then
     fail "Failed to add the dashed/claude-marketplace marketplace."
 fi
+# 一覧は .claude/settings.json の enabledPlugins と同じにする（.devcontainer/test-install-beforehand.bash が検査する）
 for plugin in \
     example-skills@anthropic-agent-skills \
+    superpowers@claude-plugins-official \
+    feature-dev@claude-plugins-official \
     web-quality-skills@addy-web-quality-skills \
     ripgrep@alberto-marketplace; do
     if ! claude plugin install "$plugin"; then
@@ -137,6 +137,28 @@ for plugin in \
     fi
 done
 
+step "Installing Codex"
+# Codex CLI は npm で導入し、zshrc.txt の update() も同じ npm で更新する。npm は Node feature が PATH に置く
+if ! npm install -g @openai/codex@latest; then
+    fail "Codex installation failed."
+fi
+if ! command -v codex >/dev/null 2>&1; then
+    fail "Codex installation completed without placing codex on PATH."
+fi
+
+step "Installing uv"
+# pi の設定ステップ（setup_pi_tool_display.py）が uv run を使うため、pi より前に導入する。
+# uv は ~/.local/bin に入り、この PATH は Claude Code の導入直後に通してある
+if ! (
+    set -o pipefail
+    curl -LsSf https://astral.sh/uv/install.sh | sh
+); then
+    fail "uv installation failed."
+fi
+if ! command -v uv >/dev/null 2>&1; then
+    fail "uv installation completed without placing uv on PATH."
+fi
+
 step "Installing the Cursor CLI"
 # ~/.local/share/cursor-agent は devcontainer.json で bind mount している。ホスト側に
 # 存在しない場合は Docker が root 所有で作成するため、所有権を直す（~/.pi と同じ対応）。
@@ -230,7 +252,7 @@ install_pi_extensions() {
     #    pi が管理する npm マニフェストも見る。一覧が綺麗でもマニフェストに残って
     #    いると、`pi update --extensions`（zsh の update() が実行する）で node_modules
     #    ごと再構築されて復活し、subagent ツール名が @teelicht/pi-superagents と
-    #    衝突して pigo / pigod が起動できなくなる（#289）。
+    #    衝突して pigo / pigod が起動できなくなる。
     legacy_listed=0
     case "$before" in
     *"npm:pi-subagents"*) legacy_listed=1 ;;
@@ -296,7 +318,7 @@ for extension in \
         fail "Failed to install the pi extension ${extension}."
     fi
 done
-if ! python3 .devcontainer/setup_pi_tool_display.py; then
+if ! uv run --no-project .devcontainer/setup_pi_tool_display.py; then
     fail "Failed to disable the pi tool-display Bash override."
 fi
 
@@ -355,7 +377,7 @@ if ! zsh .devcontainer/setup_pi_superagents.zsh --if-absent; then
 fi
 
 step "Installing DeepSeek Harness"
-# DeepSeek Harness（dsh）は pi と並行して使う（#282）。dsh の plugin 管理は PATH 上の
+# DeepSeek Harness（dsh）は pi と並行して使う。dsh の plugin 管理は PATH 上の
 # pnpm を直接 spawn するため、devcontainer.json の Node feature で pnpm を明示導入
 # している（pnpmVersion "none" は導入省略）。
 install_deepseek_harness() {
@@ -435,14 +457,6 @@ if ! npx -y skills add vercel-labs/skills@find-skills -g -y -a claude-code -a pi
     fail "Failed to install the find-skills skill."
 fi
 
-step "Installing uv"
-if ! (
-    set -o pipefail
-    curl -LsSf https://astral.sh/uv/install.sh | sh
-); then
-    fail "uv installation failed."
-fi
-
 step "Installing Starship"
 if ! (
     set -o pipefail
@@ -460,7 +474,7 @@ fi
 step "Placing the Herdr helper scripts in ~/bin"
 # herdrstart は PATH 上の herdr-status-updater（拡張子なし）を呼ぶ。
 # 各エージェントは PATH 上の herdr-agent-task（拡張子なし）を呼ぶ。
-# zshrc.txt がシェル起動のたびに間引いて呼ぶための実体も ~/bin に置く（#146）。
+# zshrc.txt がシェル起動のたびに間引いて呼ぶための実体も ~/bin に置く。
 # if ! ( set -e; ... ) では条件式の内側で errexit が無効になるため、関数内の || return 1 で失敗を伝える。
 place_herdr_helpers() {
     mkdir -p "${HOME}/bin" || return 1
@@ -480,13 +494,9 @@ place_herdr_helpers() {
 if ! place_herdr_helpers; then
     fail "Failed to place the Herdr helper scripts in ~/bin."
 fi
-if ! mkdir -p "${HOME}/.local/bin"; then
-    fail "Failed to create ~/.local/bin."
-fi
-export PATH="${HOME}/.local/bin:${PATH}"
 
 step "Cleaning up stale workspace debris"
-# コンテナ作成時点のディスクを圧迫する使い捨て debris を掃除する（#146。詳細は
+# コンテナ作成時点のディスクを圧迫する使い捨て debris を掃除する（詳細は
 # cleanup-workspace.bash を参照）。定期的な再発防止は zshrc.txt 側の間引き実行が
 # 担う。失敗しても以降の必須処理は続ける（唯一の意図的なベストエフォート）。
 if ! bash .devcontainer/cleanup-workspace.bash; then
diff --git a/.devcontainer/test-herdr-migration.bash b/.devcontainer/test-herdr-migration.bash
index 72379e5..da99c7a 100755
--- a/.devcontainer/test-herdr-migration.bash
+++ b/.devcontainer/test-herdr-migration.bash
@@ -180,7 +180,7 @@ test_config_and_syntax() {
     # herdrstart が herdr セッション内で no-op になるガード
     assert_contains "$ZSHRC_TEMPLATE" 'HERDR_ENV'
 
-    # tmux 撤去後の再混入防止（#305）。assert_absent は -i 付きのため TMUX も検出する
+    # tmux 撤去後の再混入防止。assert_absent は -i 付きのため TMUX も検出する
     assert_absent "$ZSHRC_TEMPLATE" 'tmux'
     local removed
     for removed in tmux.conf tmux-git-status.bash tmux-url-copy.zsh; do
@@ -216,7 +216,7 @@ test_launch_and_guards() {
     # herdrstart 経路では updater を起動しないこと（precmd 経路は存在しない）
     [ ! -s "$test_home/herdr.log.upd" ] || fail 'HERDR_ENV herdrstart updater guard'
 
-    # tmux 撤去後（#305）は TMUX が立っていても herdrstart は進行する
+    # tmux 撤去後は TMUX が立っていても herdrstart は進行する
     : > "$test_home/herdr.log"
     : > "$test_home/herdr.log.upd"
     run_zshrc_tty "$test_home" TMUX=/tmp/tmux-test
@@ -473,8 +473,6 @@ test_installer_wiring() {
     assert_before "$installer" 'https://astral\.sh/uv/install\.sh' 'https://herdr\.dev/install\.sh'
     assert_before "$installer" 'Installing Starship' 'https://herdr\.dev/install\.sh'
     assert_absent "$installer" 'bun\.com'
-    assert_before "$installer" 'if ! install_pinned_gitleaks; then' \
-        'cat \.devcontainer/zshrc\.txt >>\$\{HOME\}/\.zshrc'
     assert_absent "$installer" 'headroom'
     assert_before "$installer" 'cat \.devcontainer/zshrc\.txt >>\$\{HOME\}/\.zshrc' \
         'Installing Herdr'
@@ -497,7 +495,7 @@ test_installer_wiring() {
     assert_contains "$installer" 'herdr-agent-task\.bash'
     assert_contains "$installer" 'cp \.devcontainer/herdr-agent-task\.bash "\$\{HOME\}/bin/herdr-agent-task"'
 
-    # tmux 撤去後の再混入防止（#305）: apt 行・cp・コメントを含め全体で検査
+    # tmux 撤去後の再混入防止: apt 行・cp・コメントを含め全体で検査
     assert_absent "$installer" 'tmux'
 }
 
````

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
bash .devcontainer/test-install-beforehand.bash
bash .devcontainer/test-herdr-migration.bash
bash .devcontainer/test-verify-resonite-tooling.bash   # STEP_TOTAL とステップ数の一致を見る
```

Expected: 3 本とも PASS。`test-herdr-migration.bash` はこの Task から PASS になる。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う（すべて PASS）。

```bash
cd "$W"
git add .devcontainer/test-install-beforehand.bash .devcontainer/install_beforehand.bash .claude/settings.json \
  .devcontainer/README.md .devcontainer/test-herdr-migration.bash
git commit -m "feat(devcontainer): install Codex and the plugins listed in .claude/settings.json

postCreate now installs Codex with npm, installs uv before the pi setup that
runs through uv run, and installs the same Claude Code plugins that
.claude/settings.json enables (superpowers and feature-dev added). The
duplicate apt update and PATH export are removed, and the herdr test no longer
expects gitleaks in the container (CI runs it instead).

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 3: mounts・`initialize.bash`・書き込み可能化の一致（仕様 7.1・7.2）

`devcontainer.json` の mounts のソースを、`initialize.bash` がすべて作るようにする（既存 13 個と秘密情報 1 個）。コンテナ名、`remoteEnv.PATH`、秘密情報の mount を仕様どおりにし、postCreate が書き込み可能にするディレクトリを mounts とそろえる。突き合わせる関数は `.devcontainer/mounts.bash` に置き、Task 6 の check-layout と Task 10 の README のテストも使う。

**Files:**
- Create: `.devcontainer/mounts.bash`（source して使う関数集。mode 100755）
- Create: `.devcontainer/test-initialize-mounts.bash`（mode 100755）
- Modify: `.devcontainer/initialize.bash`（全体を置き換える）、`.devcontainer/devcontainer.json`、`.devcontainer/install_beforehand.bash`（`ensure_user_writable_dir` の一覧）、`.devcontainer/test-resonite-feature.bash`（PATH の期待値）

**Interfaces:**
- Produces（`source "$root/.devcontainer/mounts.bash"` で読み込む）:
  - `mounts_from_devcontainer DEVCONTAINER_JSON` — mounts を `<rel><TAB><target>` で 1 行ずつ出力する（`<rel>` は `~/` からの相対パス）。ファイルが無ければ 1
  - `mounts_from_initialize INITIALIZE_BASH` — `"${HOME}/<rel>"` だけを書いた行の `<rel>` を 1 行ずつ出力する。ファイルが無ければ 1
  - `mounts_compare DEVCONTAINER_JSON INITIALIZE_BASH` — 食い違いを `mounts: ...` の 1 件 1 行で出力する。文言: `mounts: ~/<rel> is mounted by devcontainer.json but not created by initialize.bash`、`mounts: ~/<rel> is created by initialize.bash but not mounted by devcontainer.json`、`mounts: ~/<rel> is mounted at <target>, expected /home/vscode/<rel>`、`mounts: <file> not found`、`mounts: no mounts found in <file>`。一致すれば何も出力せず 0、それ以外は 1

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-initialize-mounts.bash` を次の内容で作り、`chmod +x` する。`test-resonite-feature.bash` の PATH の期待値も変える。

```bash
#!/bin/bash
# devcontainer.json の mounts・initialize.bash・postCreate の書き込み可能化が一致することを検査する。仕様 7.1・7.2・9.1 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config="$root/.devcontainer/devcontainer.json"
init="$root/.devcontainer/initialize.bash"
installer="$root/.devcontainer/install_beforehand.bash"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# shellcheck source=mounts.bash
source "$root/.devcontainer/mounts.bash"

# 1. mounts のソースと initialize.bash が作るパスは同じ集合（仕様 7.2・9.1）
if ! out="$(mounts_compare "$config" "$init")"; then fail "mounts and initialize.bash differ:
$out"; fi

# 2. mounts は仕様 7.1 の表の 14 個（既存 13 ＋秘密情報）
expected='.claude
.claude.json
.codex
.config/create-reso-world
.config/devin
.config/gcloud
.config/gh
.config/glab-cli
.cursor
.dsh
.grok
.local/share/cursor-agent
.local/share/devin
.pi'
actual="$(mounts_from_devcontainer "$config" | cut -f1 | LC_ALL=C sort)"
[ "$actual" = "$expected" ] || fail "unexpected mounts:
$actual"

# 3. initialize.bash は一時 HOME にすべてのソースを作り、2 回目も成功する。~/.claude.json は通常ファイルで、
#    既存の中身を消さない。秘密情報のディレクトリは本人だけが読める
home="$tmp/home"
mkdir -p "$home"
HOME="$home" bash "$init"
printf '{"keep": true}\n' > "$home/.claude.json"
HOME="$home" bash "$init"
while IFS= read -r rel; do
  if [ "$rel" = .claude.json ]; then
    [ -f "$home/$rel" ] || fail "initialize.bash did not create the file ~/$rel"
  else
    [ -d "$home/$rel" ] || fail "initialize.bash did not create the directory ~/$rel"
  fi
done <<<"$expected"
[ "$(cat "$home/.claude.json")" = '{"keep": true}' ] || fail 'initialize.bash changed ~/.claude.json'
[ "$(stat -c %a "$home/.config/create-reso-world")" = 700 ] || fail '~/.config/create-reso-world must be mode 700'

# 4. postCreate はディレクトリの mount をすべて書き込み可能にする（ファイルの ~/.claude.json は除く）
writable="$(sed -n '/^step "Ensuring user-writable directories under ~"$/,/; do$/p' "$installer")"
while IFS= read -r rel; do
  [ "$rel" = .claude.json ] && continue
  grep -qF "\"\${HOME}/$rel\"" <<<"$writable" || fail "install_beforehand.bash does not make ~/$rel writable"
done <<<"$expected"

# 5. コンテナ名と、ユーザ単位のツールの PATH（仕様 7.2）
grep -qF '"name": "create-reso-world",' "$config" || fail 'devcontainer.json name must be create-reso-world'
grep -qF '"PATH": "${containerEnv:PATH}:/home/vscode/.local/bin:/home/vscode/bin:/home/vscode/.dotnet/tools"' "$config" \
  || fail 'remoteEnv.PATH must add ~/.local/bin, ~/bin and ~/.dotnet/tools'

# 6. 食い違いの検出: 片方にしか無いパスと、target が違う mount を報告して 1 を返す
cp "$config" "$tmp/extra.json"
sed -i 's|^\(\t\t"source=${localEnv:HOME}/.pi,target=/home/vscode/.pi,type=bind,consistency=cached",\)$|\1\n\t\t"source=${localEnv:HOME}/.extra,target=/home/vscode/.extra,type=bind,consistency=cached",|' "$tmp/extra.json"
if out="$(mounts_compare "$tmp/extra.json" "$init")"; then fail 'accepted a mount that initialize.bash does not create'; fi
grep -qxF 'mounts: ~/.extra is mounted by devcontainer.json but not created by initialize.bash' <<<"$out" || fail "unexpected report: $out"
sed 's|^  "${HOME}/.grok" \\$|  "${HOME}/.grok" \\\n  "${HOME}/.unmounted" \\|' "$init" > "$tmp/extra-init.bash"
if out="$(mounts_compare "$config" "$tmp/extra-init.bash")"; then fail 'accepted a path that is not mounted'; fi
grep -qxF 'mounts: ~/.unmounted is created by initialize.bash but not mounted by devcontainer.json' <<<"$out" || fail "unexpected report: $out"
sed 's|target=/home/vscode/.dsh,|target=/root/.dsh,|' "$config" > "$tmp/target.json"
if out="$(mounts_compare "$tmp/target.json" "$init")"; then fail 'accepted a mount with an unexpected target'; fi
grep -qxF 'mounts: ~/.dsh is mounted at /root/.dsh, expected /home/vscode/.dsh' <<<"$out" || fail "unexpected report: $out"
# // でコメントアウトした mount と、パス以外も書いた行（chmod など）は数えない
sed 's|^\t\t"source=${localEnv:HOME}/.codex,|\t\t// "source=${localEnv:HOME}/.codex,|' "$config" > "$tmp/commented.json"
if out="$(mounts_compare "$tmp/commented.json" "$init")"; then fail 'counted a commented-out mount'; fi
grep -qxF 'mounts: ~/.codex is created by initialize.bash but not mounted by devcontainer.json' <<<"$out" || fail "unexpected report: $out"
printf 'chmod 700 "${HOME}/.chmod-only"\n' | cat "$init" - > "$tmp/chmod-init.bash"
mounts_compare "$config" "$tmp/chmod-init.bash" >/dev/null || fail 'counted a path on a chmod line'
if out="$(mounts_compare "$tmp/missing.json" "$init")"; then fail 'accepted a missing devcontainer.json'; fi

printf 'PASS: mounts, initialize.bash and postCreate agree\n'
```

```diff
diff --git a/.devcontainer/test-resonite-feature.bash b/.devcontainer/test-resonite-feature.bash
index 1901312..74b41c3 100755
--- a/.devcontainer/test-resonite-feature.bash
+++ b/.devcontainer/test-resonite-feature.bash
@@ -5,6 +5,6 @@ config="$root/.devcontainer/devcontainer.json"
 installer="$root/.devcontainer/install_beforehand.bash"
 grep -qF '"ghcr.io/devcontainers/features/dotnet:2"' "$config"
 grep -A 2 -F '"ghcr.io/devcontainers/features/dotnet:2"' "$config" | grep -qF '"version": "10.0"'
-grep -qF '"PATH": "${containerEnv:PATH}:/home/vscode/.dotnet/tools"' "$config"
+grep -qF '"PATH": "${containerEnv:PATH}:/home/vscode/.local/bin:/home/vscode/bin:/home/vscode/.dotnet/tools"' "$config"
 grep -qE 'sudo apt install -y .*blender' "$installer"
 printf 'PASS: .NET 10 Feature and Blender package configured\n'
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W"
bash .devcontainer/test-initialize-mounts.bash; echo "exit=$?"
bash .devcontainer/test-resonite-feature.bash; echo "exit=$?"
```

Expected: 1 本目は `.devcontainer/mounts.bash: No such file or directory` で終了コード 1。2 本目は何も表示せずに終了コード 1（`grep -qF` の不一致）。

- [ ] **Step 3: 関数集を作る**

`.devcontainer/mounts.bash` を次の内容で作り、`chmod +x` する。

```bash
#!/bin/bash
# devcontainer.json の mounts と initialize.bash が作るパスを突き合わせる関数集（source して使う）。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 7.1・7.2・9.1 節
# 使うのは .devcontainer/test-initialize-mounts.bash と scripts/check-layout.sh。
# 書式の前提（行単位で読む）:
#   devcontainer.json: 1 行に 1 つ "source=${localEnv:HOME}/<rel>,target=/home/vscode/<rel>,type=bind,..."。// で始まる行は読まない
#   initialize.bash:   作るパスを 1 行に 1 つ "${HOME}/<rel>" だけ書く（mkdir -p と touch の引数。行末の \ は可）

# mounts_from_devcontainer DEVCONTAINER_JSON
# mounts を "<rel><TAB><target>" で 1 行ずつ出力する（<rel> はソースの ~/ からの相対パス）。ファイルが無ければ 1
mounts_from_devcontainer() {
  local json="$1" line
  local re='"source=\$\{localEnv:HOME\}/([^,"]+),target=([^,"]+),type=bind[^"]*"'
  [ -f "$json" ] || return 1
  while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*// ]] && continue
    [[ "$line" =~ $re ]] && printf '%s\t%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
  done < "$json"
  return 0
}

# mounts_from_initialize INITIALIZE_BASH
# initialize.bash が作るパス（"${HOME}/<rel>" だけを書いた行）を <rel> で 1 行ずつ出力する。ファイルが無ければ 1
mounts_from_initialize() {
  local file="$1" line
  local re='^[[:space:]]*"\$\{HOME\}/([^"]+)"[[:space:]]*\\?$'
  [ -f "$file" ] || return 1
  while IFS= read -r line; do
    [[ "$line" =~ $re ]] && printf '%s\n' "${BASH_REMATCH[1]}"
  done < "$file"
  return 0
}

# mounts_compare DEVCONTAINER_JSON INITIALIZE_BASH
# mounts のソースの集合と initialize.bash が作るパスの集合を比べ、食い違いを 1 件 1 行で出力する。
# target が /home/vscode/<rel> でない mount も食い違いとして出力する。一致すれば何も出力せず 0、それ以外は 1
mounts_compare() {
  local json="$1" init="$2" pairs created rel target bad=0
  pairs="$(mounts_from_devcontainer "$json")" || { printf 'mounts: %s not found\n' "$json"; return 1; }
  created="$(mounts_from_initialize "$init")" || { printf 'mounts: %s not found\n' "$init"; return 1; }
  [ -n "$pairs" ] || { printf 'mounts: no mounts found in %s\n' "$json"; return 1; }
  while IFS=$'\t' read -r rel target; do
    if [ "$target" != "/home/vscode/$rel" ]; then
      printf 'mounts: ~/%s is mounted at %s, expected /home/vscode/%s\n' "$rel" "$target" "$rel"
      bad=1
    fi
    grep -qxF -- "$rel" <<<"$created" && continue
    printf 'mounts: ~/%s is mounted by devcontainer.json but not created by initialize.bash\n' "$rel"
    bad=1
  done <<<"$pairs"
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    grep -qxF -- "$rel" <<<"$(cut -f1 <<<"$pairs")" && continue
    printf 'mounts: ~/%s is created by initialize.bash but not mounted by devcontainer.json\n' "$rel"
    bad=1
  done <<<"$created"
  return "$bad"
}
```

- [ ] **Step 4: `initialize.bash` を置き換える**

```bash
#!/bin/bash
# ホスト側で、devcontainer.json の mounts のソースを先に作る（initializeCommand）。
# 無いソースは Docker が root 所有のディレクトリとして作るため、ファイルの mount（~/.claude.json）が
# ディレクトリになったり、コンテナから書き込めなくなったりする。
# 一覧は devcontainer.json の mounts と 1 対 1 にする（.devcontainer/test-initialize-mounts.bash と
# scripts/check-layout.sh が .devcontainer/mounts.bash で突き合わせる）。1 行に 1 つ "${HOME}/<パス>" と書く。
set -e

mkdir -p \
  "${HOME}/.codex" \
  "${HOME}/.claude" \
  "${HOME}/.grok" \
  "${HOME}/.pi" \
  "${HOME}/.dsh" \
  "${HOME}/.local/share/devin" \
  "${HOME}/.config/devin" \
  "${HOME}/.local/share/cursor-agent" \
  "${HOME}/.config/gh" \
  "${HOME}/.cursor" \
  "${HOME}/.config/glab-cli" \
  "${HOME}/.config/gcloud" \
  "${HOME}/.config/create-reso-world"

touch \
  "${HOME}/.claude.json"

# 秘密情報（env）を置くディレクトリは本人だけが読めるようにする
chmod 700 "${HOME}/.config/create-reso-world"
```

- [ ] **Step 5: `devcontainer.json` と postCreate を直す**

`devcontainer.json` の変更は、コンテナ名、秘密情報の mount、`remoteEnv.PATH`、Issue 番号を外したコメントの 3 行だけにする（インデントはタブ）。

```diff
diff --git a/.devcontainer/devcontainer.json b/.devcontainer/devcontainer.json
index a447ed3..401a4f5 100644
--- a/.devcontainer/devcontainer.json
+++ b/.devcontainer/devcontainer.json
@@ -1,7 +1,7 @@
 // For format details, see https://aka.ms/devcontainer.json. For config options, see the
 // README at: https://github.com/devcontainers/templates/tree/main/src/ubuntu
 {
-	"name": "Ubuntu",
+	"name": "create-reso-world",
 	"mounts": [
 		"source=${localEnv:HOME}/.codex,target=/home/vscode/.codex,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.claude,target=/home/vscode/.claude,type=bind,consistency=cached",
@@ -15,7 +15,9 @@
 		"source=${localEnv:HOME}/.config/gh,target=/home/vscode/.config/gh,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.cursor,target=/home/vscode/.cursor,type=bind,consistency=cached",
 		"source=${localEnv:HOME}/.config/glab-cli,target=/home/vscode/.config/glab-cli,type=bind,consistency=cached",
-		"source=${localEnv:HOME}/.config/gcloud,target=/home/vscode/.config/gcloud,type=bind,consistency=cached"
+		"source=${localEnv:HOME}/.config/gcloud,target=/home/vscode/.config/gcloud,type=bind,consistency=cached",
+		// 秘密情報（API トークンなど）。zshrc.txt が env を存在時だけ読み込む
+		"source=${localEnv:HOME}/.config/create-reso-world,target=/home/vscode/.config/create-reso-world,type=bind,consistency=cached"
 	],
     // 既定の loginInteractiveShell は ~/.zshrc を読むため herdrstart が走り、
     // herdr を起動したままハングする。残留シェルが herdr サーバを
@@ -26,7 +28,9 @@
         "SHELL": "/usr/bin/zsh"
     },
     "remoteEnv": {
-        "PATH": "${containerEnv:PATH}:/home/vscode/.dotnet/tools"
+        // ユーザ単位で導入するツール（claude・uv など、herdr の補助スクリプト、dotnet tool）。mounts と同じく
+        // /home/vscode を直接書く
+        "PATH": "${containerEnv:PATH}:/home/vscode/.local/bin:/home/vscode/bin:/home/vscode/.dotnet/tools"
     },
 	"initializeCommand": "/bin/bash .devcontainer/initialize.bash",
 	// Or use a Dockerfile or Docker Compose file. More info: https://containers.dev/guide/dockerfile
@@ -49,11 +53,11 @@
 		},
 		"ghcr.io/devcontainers/features/node:2": {
 		"nodeGypDependencies": true,
-		// #147: リポジトリのタスク・CLI 導入は npm に一本化した。yarn を apt 経由で
+		// リポジトリのタスク・CLI 導入は npm に一本化した。yarn を apt 経由で
 		// 常駐インストールする必要はなく、既定 (false) の corepack 経由に戻す。
 		"installYarnUsingApt": false,
 		"version": "24",
-		// #282: dsh plugin は PATH 上の pnpm を直接 spawn する。pnpmVersion "none" は
+		// dsh plugin は PATH 上の pnpm を直接 spawn する。pnpmVersion "none" は
 		// 導入省略のため、plugin 0.10.6 との組み合わせを隔離検証した 12.4.1 を明示する。
 		"pnpmVersion": "12.4.1",
 		"nvmVersion": "latest"
@@ -65,7 +69,7 @@
 
 	// Use 'forwardPorts' to make a list of ports inside the container available locally.
 	// "forwardPorts": [],
-	// #282: 3080 は dsh web の既定ポート。
+	// 3080 は dsh web の既定ポート。
 	"forwardPorts": [8000, 3080],
 
 	// Use 'postCreateCommand' to run commands after the container is created.
diff --git a/.devcontainer/install_beforehand.bash b/.devcontainer/install_beforehand.bash
index 1f83d61..fba4f9b 100755
--- a/.devcontainer/install_beforehand.bash
+++ b/.devcontainer/install_beforehand.bash
@@ -53,7 +53,8 @@ step "Ensuring user-writable directories under ~"
 # bind mount target の中間ディレクトリ（~/.local/share 等）と target 自体は、
 # Docker が root 所有で作る・ホスト側に root 所有のまま残ることがある。
 # 以降の全ステップが $HOME 配下へ書き込むため、最初に親から順に書き込み可能を
-# 保証する。~/.claude.json はファイル mount のため対象外。
+# 保証する。~/.claude.json はファイル mount のため対象外。ディレクトリの mount はすべてここに並べる
+# （.devcontainer/test-initialize-mounts.bash が devcontainer.json の mounts と突き合わせる）。
 for dir in \
     "${HOME}/.local" \
     "${HOME}/.local/share" \
@@ -65,7 +66,10 @@ for dir in \
     "${HOME}/.config/gh" \
     "${HOME}/.config/glab-cli" \
     "${HOME}/.config/gcloud" \
+    "${HOME}/.config/create-reso-world" \
+    "${HOME}/.codex" \
     "${HOME}/.claude" \
+    "${HOME}/.grok" \
     "${HOME}/.pi" \
     "${HOME}/.dsh" \
     "${HOME}/.cursor"; do
```

- [ ] **Step 6: テストが通ることを確かめる**

```bash
cd "$W"
bash .devcontainer/test-initialize-mounts.bash && bash .devcontainer/test-resonite-feature.bash
bash .devcontainer/test-resoloop-lock.bash   # additionalVersions の読み取りが devcontainer.json の変更後も通る
```

Expected: 3 本とも PASS。

- [ ] **Step 7: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .devcontainer/mounts.bash .devcontainer/test-initialize-mounts.bash .devcontainer/initialize.bash \
  .devcontainer/devcontainer.json .devcontainer/install_beforehand.bash .devcontainer/test-resonite-feature.bash
git commit -m "feat(devcontainer): create every mount source and add the secrets mount

initialize.bash now creates all 14 mount sources on the host (the file mount
~/.claude.json stays a file) and keeps ~/.config/create-reso-world private.
devcontainer.json is renamed to create-reso-world, mounts that directory and
adds ~/.local/bin and ~/bin to remoteEnv.PATH. postCreate makes every
directory mount writable. .devcontainer/mounts.bash compares the three lists
and is shared with the tests and check-layout.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 4: zsh の設定と starship（仕様 7.2）

`zshrc.txt` の `cod`・`genv`・`buni` と `update()` の各項目を、コマンドの有無で保護する。`BUN_INSTALL` を `$HOME` 基準にし、秘密情報の `env` を存在するときだけ読み込む。starship の `custom.uv_python` は、カレントディレクトリから上へ最寄りの `.venv/pyvenv.cfg` を探す（プロジェクトごとに `.venv` があるため）。

**Files:**
- Create: `.devcontainer/test-shell-tools.bash`（mode 100755）
- Modify: `.devcontainer/zshrc.txt`、`.devcontainer/starship.toml`

**Interfaces:**
- Produces: zsh の関数 `require_command NAME`（無ければ `<呼び出し元の関数>: NAME not found` を表示して 127）と `update_if_present TOOL COMMAND...`（無ければ `update: TOOL not found; skipped: COMMAND...` を表示して実行しない）。Task 10 の README の表は `update()` の各項目と、`ccd`・`ccda`・`ccdd`・`ccddg`・`ccdu`・`cod`・`cur`・`dev`・`genv`・`buni` の定義を zshrc.txt から探す。

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-shell-tools.bash` を次の内容で作り、`chmod +x` する。

```bash
#!/bin/bash
# zshrc.txt の未導入ツールの保護・秘密情報の読み込みと、starship.toml の custom.uv_python を検査する。仕様 7.1・7.2 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
zshrc="$root/.devcontainer/zshrc.txt"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# 一時 HOME と、スタブ（$tmp/bin）と基本コマンド（$tmp/sys）だけの PATH で zshrc.txt を読み込み、$1 の zsh コードを
# 実行する。標準出力は $tmp/out、標準エラーは $tmp/err に残し、終了コードを返す。スタブを置かなかったツールは
# 「未導入」になる（非 TTY なので herdrstart は何もしない）
run_zsh() {
  local code=0
  env -i HOME="$tmp/home" PATH="$tmp/bin:$tmp/sys" TMP_LOG="$tmp/calls" ZSHRC="$zshrc" \
    /usr/bin/zsh -f -c 'source "$ZSHRC"; '"$1" </dev/null >"$tmp/out" 2>"$tmp/err" || code=$?
  return "$code"
}
# stub NAME: 呼び出しを $tmp/calls に記録するだけのコマンドを置く
stub() {
  printf '#!/bin/bash\nprintf "%%s\\n" "%s $*" >> "$TMP_LOG"\n' "$1" > "$tmp/bin/$1"
  chmod +x "$tmp/bin/$1"
}
mkdir -p "$tmp/home" "$tmp/bin" "$tmp/sys"
for c in cat chmod date dirname ls mkdir mv rm rmdir touch; do   # compinit などが使う基本コマンド
  ln -s "$(command -v "$c")" "$tmp/sys/$c"
done
printf '#!/bin/bash\n' > "$tmp/bin/starship"   # zshrc.txt の eval "$(starship init zsh)" は何もしない
chmod +x "$tmp/bin/starship"
: > "$tmp/calls"

zsh -n "$zshrc"

# 1. どのツールも無くても読み込みは成功し、command not found を出さない
run_zsh 'true' || fail "sourcing zshrc.txt failed: $(cat "$tmp/err")"
if grep -F 'command not found' "$tmp/err"; then fail 'zshrc.txt ran a missing command while loading'; fi

# 2. update() は無いツールを飛ばして 0 を返し、飛ばした項目を表示する
run_zsh 'update' || fail "update failed without any tool: $(cat "$tmp/err")"
for tool in claude npm grok pi agent devin; do
  grep -qF "update: $tool not found; skipped" "$tmp/err" || fail "update did not report the missing $tool"
done
if grep -F 'command not found' "$tmp/err"; then fail 'update ran a missing command'; fi

# 3. update() はあるツールだけを更新する
stub claude && stub npm && stub pi
: > "$tmp/calls"
run_zsh 'update' || fail "update failed: $(cat "$tmp/err")"
expected='claude update
npm install -g @openai/codex@latest
pi update
pi update --extensions'
[ "$(cat "$tmp/calls")" = "$expected" ] || fail "update ran: $(cat "$tmp/calls")"
grep -qF 'update: devin not found; skipped: devin plugins update superpowers' "$tmp/err" || fail 'update did not skip devin'
rm "$tmp/bin/claude" "$tmp/bin/npm" "$tmp/bin/pi"

# 4. cod・genv・buni は、ツールが無ければ理由を示して 127 を返す。buni は node_modules を消さない
mkdir -p "$tmp/home/work/node_modules"
for call in 'cod:codex' 'genv:gcloud' 'buni:bun'; do
  fn="${call%%:*}" tool="${call#*:}" code=0
  run_zsh "cd \"\$HOME/work\" && $fn" || code=$?
  [ "$code" -eq 127 ] || fail "$fn returned $code without $tool"
  grep -qxF "$fn: $tool not found" "$tmp/err" || fail "$fn did not report the missing $tool: $(cat "$tmp/err")"
done
[ -d "$tmp/home/work/node_modules" ] || fail 'buni removed node_modules although bun is missing'
stub gcloud
code=0
run_zsh 'genv' || code=$?
[ "$code" -eq 127 ] && grep -qxF 'genv: fzf not found' "$tmp/err" || fail 'genv must also require fzf'
rm "$tmp/bin/gcloud"

# 5. bun の場所は $HOME 基準で、/home/vscode を書かない
run_zsh 'print -r -- "$BUN_INSTALL"' || fail 'BUN_INSTALL'
[ "$(cat "$tmp/out")" = "$tmp/home/.bun" ] || fail "BUN_INSTALL is $(cat "$tmp/out")"
if grep -nF '/home/vscode' "$zshrc"; then fail 'zshrc.txt must not hard-code /home/vscode'; fi

# 6. 秘密情報の env はあるときだけ読み込み、書いた変数を export する
mkdir -p "$tmp/home/.config/create-reso-world"
printf 'EXAMPLE_TOKEN=secret-value\n' > "$tmp/home/.config/create-reso-world/env"
run_zsh '[[ ${(t)EXAMPLE_TOKEN} == *export* ]] && print -r -- "$EXAMPLE_TOKEN"' || fail "the secrets env was not exported: $(cat "$tmp/err")"
[ "$(cat "$tmp/out")" = secret-value ] || fail 'EXAMPLE_TOKEN value'
rm "$tmp/home/.config/create-reso-world/env"
run_zsh 'true' || fail 'loading without the secrets env failed'
[ ! -s "$tmp/err" ] || fail "loading without the secrets env printed: $(cat "$tmp/err")"

# 7. starship の custom.uv_python は、カレントディレクトリから上へ最寄りの .venv/pyvenv.cfg を探す
uv run --no-project python - "$root/.devcontainer/starship.toml" "$tmp" <<'PY'
import pathlib
import sys
import tomllib

module = tomllib.load(open(sys.argv[1], "rb"))["custom"]["uv_python"]
out = pathlib.Path(sys.argv[2])
(out / "uv_python_command.sh").write_text(module["command"] + "\n")
(out / "uv_python_when.sh").write_text(module["when"] + "\n")
PY
mkdir -p "$tmp/ws/proj/.venv" "$tmp/ws/proj/sub/dir" "$tmp/ws/other"
printf 'home = /usr/bin\nversion_info = 3.12.7\n' > "$tmp/ws/proj/.venv/pyvenv.cfg"
for dir in "$tmp/ws/proj" "$tmp/ws/proj/sub/dir"; do
  (cd "$dir" && bash --noprofile --norc "$tmp/uv_python_when.sh") || fail "uv_python hidden in $dir"
  [ "$(cd "$dir" && bash --noprofile --norc "$tmp/uv_python_command.sh")" = 3.12.7 ] || fail "uv_python version in $dir"
done
if (cd "$tmp/ws/other" && bash --noprofile --norc "$tmp/uv_python_when.sh"); then fail 'uv_python shown without a .venv'; fi

printf 'PASS: shell setup guards missing tools and finds the nearest .venv\n'
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && bash .devcontainer/test-shell-tools.bash
```

Expected: `FAIL: update failed without any tool: update:1: command not found: claude` で終了コード 1。

- [ ] **Step 3: zshrc.txt と starship.toml を直す**

```diff
diff --git a/.devcontainer/starship.toml b/.devcontainer/starship.toml
index 85c2b31..f9d59c2 100644
--- a/.devcontainer/starship.toml
+++ b/.devcontainer/starship.toml
@@ -26,9 +26,10 @@ disabled = true
 disabled = true
 
 [custom.uv_python]
-description = "uv 管理の Python バージョン（.venv/pyvenv.cfg の version_info）"
-command = "awk -F' = ' '/^version_info/ {print $2}' \"$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.venv/pyvenv.cfg\""
-when = "test -f \"$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.venv/pyvenv.cfg\""
+# プロジェクト（slum02/ など）ごとに .venv を持つため、カレントディレクトリから上へ最寄りの .venv/pyvenv.cfg を探す
+description = "uv 管理の Python バージョン（最寄りの .venv/pyvenv.cfg の version_info）"
+command = '''d="$PWD"; while [ ! -f "$d/.venv/pyvenv.cfg" ]; do [ "$d" != / ] || exit 0; d="$(dirname "$d")"; done; awk -F' = ' '/^version_info/ {print $2}' "$d/.venv/pyvenv.cfg"'''
+when = '''d="$PWD"; while [ ! -f "$d/.venv/pyvenv.cfg" ]; do [ "$d" != / ] || exit 1; d="$(dirname "$d")"; done'''
 shell = ["bash", "--noprofile", "--norc"]
 symbol = "🐍 "
 style = "bold yellow"
diff --git a/.devcontainer/zshrc.txt b/.devcontainer/zshrc.txt
index 1709865..bba6854 100644
--- a/.devcontainer/zshrc.txt
+++ b/.devcontainer/zshrc.txt
@@ -20,8 +20,18 @@ setopt no_beep
 # プロンプトが表示されるたびにプロンプト文字列を評価、置換する
 setopt prompt_subst
 
+# 未導入のツール（grok・gcloud・glab・bun など）を呼ぶ関数は、先にコマンドの有無を確かめる。
+# 無ければ理由を表示して 127 を返す（仕様 7.1）
+function require_command(){
+    command -v "$1" >/dev/null 2>&1 && return 0
+    print -u2 "$funcstack[2]: $1 not found"
+    return 127
+}
+
 # for Google Cloud
 function genv(){
+        require_command gcloud || return
+        require_command fzf || return
         GOOGLE_CLOUD_SDK_CONFIG=$(gcloud config configurations list  --format="value(name)" | fzf)
         gcloud config configurations activate ${GOOGLE_CLOUD_SDK_CONFIG}
 }
@@ -201,6 +211,7 @@ function claude-opencode-union ccdu () {
 }
 
 function cod(){
+    require_command codex || return
     if [[ -z "$CONTEXT7_API_KEY" ]]; then
         read -rs "CONTEXT7_API_KEY?Context7 API key: "
         export CONTEXT7_API_KEY
@@ -209,17 +220,26 @@ function cod(){
     codex --dangerously-bypass-approvals-and-sandbox "$@"
 }
 
-# bun completions
-[ -s "/home/vscode/.bun/_bun" ] && source "/home/vscode/.bun/_bun"
 # bun
 export BUN_INSTALL="$HOME/.bun"
 export PATH="$BUN_INSTALL/bin:$PATH"
+# bun completions
+[ -s "$BUN_INSTALL/_bun" ] && source "$BUN_INSTALL/_bun"
 function buni(){
+    require_command bun || return
     ls -ld node_modules && rm -rf node_modules
     bun install
     bun run test
 }
 
+# 秘密情報（API トークンなど）は bind mount した ~/.config/create-reso-world/env に KEY=VALUE で置く。
+# ファイルがあるときだけ読み込み、書いた変数はすべて export する
+if [ -f "$HOME/.config/create-reso-world/env" ]; then
+    set -a
+    source "$HOME/.config/create-reso-world/env"
+    set +a
+fi
+
 export EDITOR=code
 export LANG=ja_JP.utf8
 # pi-distill / pi-extensions-i18n は ja 未対応で既定が zh-CN のため、中国語表示を避けて英語化する。
@@ -399,19 +419,30 @@ function herdrstart(){
     herdr
 }
 
+# update() の 1 項目。$1 のコマンドが無ければ、残りを実行せずに飛ばしたことを表示する
+function update_if_present(){
+    local tool="$1"
+    shift
+    if command -v "$tool" >/dev/null 2>&1; then
+        "$@"
+    else
+        print -u2 "update: $tool not found; skipped: $*"
+    fi
+}
+
 function update(){
-    claude update
-    npm install -g @openai/codex@latest
-    grok update
-    pi update
-    pi update --extensions
-    agent update
-    devin update
-    devin plugins update superpowers
+    update_if_present claude claude update
+    update_if_present npm npm install -g @openai/codex@latest
+    update_if_present grok grok update
+    update_if_present pi pi update
+    update_if_present pi pi update --extensions
+    update_if_present agent agent update
+    update_if_present devin devin update
+    update_if_present devin devin plugins update superpowers
 }
 
 
-# ディスクを圧迫する使い捨て debris を間引いて掃除する（#146。詳細は
+# ディスクを圧迫する使い捨て debris を間引いて掃除する（詳細は
 # cleanup-workspace.bash を参照）。
 # 新しいシェルを開くたびに毎回実行すると重複起動になるため、
 # 24 時間 (86400 秒) に 1 回へ間引く。手動での定期実行を要求しない。
```

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
bash .devcontainer/test-shell-tools.bash && bash .devcontainer/test-herdr-migration.bash
STARSHIP_CONFIG="$W/.devcontainer/starship.toml" starship print-config custom.uv_python >/dev/null && echo starship-ok   # starship がある環境だけ
```

Expected: 2 本とも PASS。starship があれば設定を読めて `starship-ok` と表示する。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .devcontainer/test-shell-tools.bash .devcontainer/zshrc.txt .devcontainer/starship.toml
git commit -m "feat(devcontainer): guard shell helpers for tools that are not installed

cod, genv and buni now stop with a message when their tool is missing (buni
no longer deletes node_modules first), update() skips missing tools, bun paths
follow \$HOME, and ~/.config/create-reso-world/env is loaded and exported when
present. The starship Python module finds the nearest .venv above the current
directory, since every project has its own.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 5: 掃除スクリプトから移行元の名残を外す（仕様 7.2）

`cleanup-workspace.bash` から、`MAATLOG_CLEANUP_*` の互換、yarn キャッシュの掃除、`verify.sh` への言及、移行元の Issue 番号を外す。Task 2〜4 で触らない `.devcontainer` のファイル（dsh の雛形 2 つと `test-pi-superagents.bash` のコメント）の Issue 番号もここで外す（D-14）。

**Files:**
- Modify: `.devcontainer/cleanup-workspace.bash`、`.devcontainer/dsh-cordis.patch.yml`（1 行目）、`.devcontainer/dsh-settings.yaml`（1 行目）、`.devcontainer/test-pi-superagents.bash`（コメント 3 行）
- Test: `.devcontainer/test-cleanup-workspace.bash`（全体を置き換える）

**Interfaces:**
- Produces: 環境変数は `WORKSPACE_CLEANUP_TMP_ROOT`、`WORKSPACE_CLEANUP_MIN_AGE_DAYS`、`WORKSPACE_CLEANUP_DRY_RUN` の 3 つだけ（既定は `/tmp`、`1`、`0`）。

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-cleanup-workspace.bash` を次の内容に置き換える。

```bash
#!/bin/bash
# .devcontainer/cleanup-workspace.bash の設定と dry-run を、一時ディレクトリだけを対象に検査する。仕様 7.2 節
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/.devcontainer/cleanup-workspace.bash"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf -- "$TEST_ROOT"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

mkdir -p "$TEST_ROOT/current/pr-review-42-abandoned" "$TEST_ROOT/legacy/pr-review-7-abandoned" "$TEST_ROOT/home/.cache/yarn"

# 1. dry-run は WORKSPACE_CLEANUP_TMP_ROOT の対象を表示するだけで、何も消さない
output="$(
    HOME="$TEST_ROOT/home" \
    WORKSPACE_CLEANUP_TMP_ROOT="$TEST_ROOT/current" \
    WORKSPACE_CLEANUP_DRY_RUN=1 \
    WORKSPACE_CLEANUP_MIN_AGE_DAYS=0 \
    bash "$SCRIPT"
)"
[[ "$output" == *"dry-run: would remove pr-review debris: $TEST_ROOT/current/pr-review-42-abandoned"* ]] \
    || fail "dry-run did not report the review directory under WORKSPACE_CLEANUP_TMP_ROOT
$output"
[ -d "$TEST_ROOT/current/pr-review-42-abandoned" ] || fail 'dry-run removed a review directory'

# 2. 移行元の MAATLOG_CLEANUP_* は読まない。yarn キャッシュは掃除の対象にしない
output="$(
    HOME="$TEST_ROOT/home" \
    MAATLOG_CLEANUP_TMP_ROOT="$TEST_ROOT/legacy" \
    WORKSPACE_CLEANUP_TMP_ROOT="$TEST_ROOT/current" \
    WORKSPACE_CLEANUP_DRY_RUN=1 \
    WORKSPACE_CLEANUP_MIN_AGE_DAYS=0 \
    bash "$SCRIPT"
)"
[[ "$output" != *"$TEST_ROOT/legacy"* ]] || fail "MAATLOG_CLEANUP_TMP_ROOT was honoured
$output"
[[ "$output" != *yarn* ]] || fail "the cleanup still handles the yarn cache
$output"
[ -d "$TEST_ROOT/home/.cache/yarn" ] || fail 'the cleanup removed the yarn cache'

# 3. 設定の既定値: 変数を渡さなければ /tmp、1 日、dry-run なし。移行元の変数は既定値を変えない
config="$(
    env -u WORKSPACE_CLEANUP_TMP_ROOT -u WORKSPACE_CLEANUP_DRY_RUN -u WORKSPACE_CLEANUP_MIN_AGE_DAYS \
    MAATLOG_CLEANUP_TMP_ROOT="$TEST_ROOT/legacy" MAATLOG_CLEANUP_DRY_RUN=1 MAATLOG_CLEANUP_MIN_AGE_DAYS=0 \
    bash -c '
        source <(sed -n "/^readonly TMP_ROOT=/,/^readonly DRY_RUN=/p" "$1")
        printf "%s|%s|%s" "$TMP_ROOT" "$MIN_AGE_DAYS" "$DRY_RUN"
    ' _ "$SCRIPT"
)"
[ "$config" = '/tmp|1|0' ] || fail "unexpected default configuration: $config"

# 4. 移行元リポジトリの名残（MAATLOG_CLEANUP_*、yarn、verify.sh、Issue 番号）を残さない
if grep -nE 'MAATLOG|yarn|verify\.sh|#[0-9]{3}\b' "$SCRIPT"; then
    fail 'cleanup-workspace.bash still refers to the migration source'
fi

printf 'PASS: workspace cleanup uses only WORKSPACE_CLEANUP_* and keeps the dry-run safe\n'
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && bash .devcontainer/test-cleanup-workspace.bash
```

Expected: `FAIL: the cleanup still handles the yarn cache` で終了コード 1。

- [ ] **Step 3: スクリプトとコメントを直す**

```diff
diff --git a/.devcontainer/cleanup-workspace.bash b/.devcontainer/cleanup-workspace.bash
index 968f284..a04019c 100755
--- a/.devcontainer/cleanup-workspace.bash
+++ b/.devcontainer/cleanup-workspace.bash
@@ -2,10 +2,10 @@
 #
 # .devcontainer/cleanup-workspace.bash
 #
-# ディスクを圧迫する使い捨て debris を安全に掃除する（Issue #146）。
+# ディスクを圧迫する使い捨て debris を安全に掃除する。
 #   - /tmp/pr-review-* の残骸（pr-review スキルが `worktree` サブディレクトリに
-#     git worktree を作る。PR #159 以降は save 成功時に worktree・session state を
-#     自動削除するが、異常終了や cleanup 失敗時には残るため掃除は引き続き必要。
+#     git worktree を作る。save 成功時には worktree・session state を
+#     自動削除するが、異常終了や cleanup 失敗時には残るため掃除は必要。
 #     残骸の大半は「登録されたままの worktree」で、単純な rm -rf は git 側の
 #     worktree 登録と不整合を起こすため使えない。なお loose なセッション状態
 #     ファイルは pr-review 側の削除対象に含まれないため、ディレクトリの有無と
@@ -15,9 +15,8 @@
 #     行うが、異常終了時には残るため本スクリプトが安全網として pr-review と同じ
 #     安全条件で掃除する。公式 mktemp のドット区切り（review-fix-planning.*）のみ対象。
 #     ハイフン区切りの歴史的残骸（-wt / -head.txt 等）は対象外で手動対応）
-#   - yarn キャッシュ（#147 で npm に一本化したため不要）
 #
-# 安全条件（Issue #152 共有仕様 §4。すべて AND で判断する）:
+# 安全条件（すべて AND で判断する）:
 #   - 未コミット変更のある git 作業ツリーを含むものは削除しない
 #   - 使用中（プロセスの cwd）と判定できるものは削除しない
 #   - 経過日数のみを削除条件にしない
@@ -32,28 +31,23 @@
 #   - loose なセッション状態ファイル（pr-review-<PR>-*.patch / *session.env /
 #     pr-review-<PR>.diff 等、/tmp 直下に置かれるもの）は、ディレクトリの
 #     削除有無とは無関係に、実行のたびに独立したパスで TMP_ROOT 全体を
-#     走査して片付ける（このディレクトリ削除への従属が Issue #146 の
-#     再発を招いていたため、本ブランチで分離した）。同じ PR 番号の
+#     走査して片付ける（ディレクトリ削除に従属させると、ディレクトリを
+#     自分で消す pr-review の残したファイルが二度と片付かないため）。同じ PR 番号の
 #     pr-review-<PR>-* ディレクトリが他に 1 つも残っていない場合に限り、
 #     ディレクトリと同じ MIN_AGE_DAYS を満たすものだけ削除する。1 つでも
 #     残っていれば、他インスタンスがまだ参照し得るため一切触らない
 #
-# verify.sh のログ rotation はこのスクリプトの対象外（#150 の責務）。
-#
 # 環境変数（既定値はコンテナの実運用、テストでは差し替える）:
 #   WORKSPACE_CLEANUP_TMP_ROOT       pr-review-* / review-fix-planning.* を探すルート（既定 /tmp）
 #   WORKSPACE_CLEANUP_MIN_AGE_DAYS   最終更新からの最小経過日数。0 以下で無効化（既定 1）
-#   WORKSPACE_CLEANUP_YARN_CACHE_DIR yarn キャッシュのパス（既定 $HOME/.cache/yarn）
 #   WORKSPACE_CLEANUP_DRY_RUN        1 で実際には削除・git worktree remove をせず
 #                                  対象だけ表示する（既定 0）
-# 旧 MAATLOG_CLEANUP_* は安全のため代替として受け付け、新しい名前を優先する。
 
 set -u
 
-readonly TMP_ROOT="${WORKSPACE_CLEANUP_TMP_ROOT:-${MAATLOG_CLEANUP_TMP_ROOT:-/tmp}}"
-readonly MIN_AGE_DAYS="${WORKSPACE_CLEANUP_MIN_AGE_DAYS:-${MAATLOG_CLEANUP_MIN_AGE_DAYS:-1}}"
-readonly YARN_CACHE_DIR="${WORKSPACE_CLEANUP_YARN_CACHE_DIR:-${MAATLOG_CLEANUP_YARN_CACHE_DIR:-${HOME:-/root}/.cache/yarn}}"
-readonly DRY_RUN="${WORKSPACE_CLEANUP_DRY_RUN:-${MAATLOG_CLEANUP_DRY_RUN:-0}}"
+readonly TMP_ROOT="${WORKSPACE_CLEANUP_TMP_ROOT:-/tmp}"
+readonly MIN_AGE_DAYS="${WORKSPACE_CLEANUP_MIN_AGE_DAYS:-1}"
+readonly DRY_RUN="${WORKSPACE_CLEANUP_DRY_RUN:-0}"
 
 # cleanup_pr_review_dirs が削除した（dry-run では削除するとみなした）ディレクトリ。
 # loose ファイルの掃除は「同じ PR 番号のディレクトリがもう残っていないか」で
@@ -200,7 +194,7 @@ _contains() {
 # （pr-review-<PR>-diff.patch、pr-review-<PR>-session.env、pr-review-<PR>.diff 等）
 # を片付ける。
 #
-# PR #159 以降、pr-review スキルは save 成功時に自身の worktree・セッション
+# pr-review スキルは save 成功時に自身の worktree・セッション
 # ディレクトリを削除する。そのため「ディレクトリを削除したとき」を契機にすると
 # loose ファイルには二度と掃除が来ない。ディレクトリの有無と独立に走らせる。
 #
@@ -317,30 +311,11 @@ cleanup_review_fix_planning_dirs() {
     cleanup_tmp_dirs "review-fix-planning" "" "${TMP_ROOT}"/review-fix-planning.*
 }
 
-cleanup_yarn_cache() {
-    if [ -d "$YARN_CACHE_DIR" ]; then
-        local size
-        size="$(du -sh "$YARN_CACHE_DIR" 2>/dev/null | cut -f1)"
-        if [ "$DRY_RUN" = "1" ]; then
-            echo "dry-run: would remove yarn cache: ${YARN_CACHE_DIR} (${size:-unknown size})"
-            return 0
-        fi
-        if rm -rf -- "$YARN_CACHE_DIR"; then
-            echo "removed yarn cache: ${YARN_CACHE_DIR} (${size:-unknown size})"
-        else
-            echo "failed to remove yarn cache: ${YARN_CACHE_DIR}" >&2
-        fi
-    else
-        echo "yarn cache cleanup: nothing to remove at ${YARN_CACHE_DIR}"
-    fi
-}
-
 main() {
     echo "=== workspace cleanup: $(date -u +%Y-%m-%dT%H:%M:%SZ) (root=${TMP_ROOT}) ==="
     cleanup_pr_review_dirs
     cleanup_orphaned_pr_session_files
     cleanup_review_fix_planning_dirs
-    cleanup_yarn_cache
 }
 
 main "$@"
diff --git a/.devcontainer/dsh-cordis.patch.yml b/.devcontainer/dsh-cordis.patch.yml
index c8cc7f3..179b8d3 100644
--- a/.devcontainer/dsh-cordis.patch.yml
+++ b/.devcontainer/dsh-cordis.patch.yml
@@ -1,4 +1,4 @@
-# Dev Container の初回起動時に ~/.dsh/cordis.patch.yml へコピーされる雛形（#282）。
+# Dev Container の初回起動時に ~/.dsh/cordis.patch.yml へコピーされる雛形。
 # home レベルの patch 層は各 profile の cordis.patch.yml の後に適用されるため、
 # web と headless の両方に効く。
 #
diff --git a/.devcontainer/dsh-settings.yaml b/.devcontainer/dsh-settings.yaml
index 378bcd1..da41686 100644
--- a/.devcontainer/dsh-settings.yaml
+++ b/.devcontainer/dsh-settings.yaml
@@ -1,4 +1,4 @@
-# Dev Container の初回起動時に ~/.dsh/settings.yaml へコピーされる雛形（#282）。
+# Dev Container の初回起動時に ~/.dsh/settings.yaml へコピーされる雛形。
 # API key の値は保存せず、環境変数名だけを参照する。
 llm-deepseek:
   apiKeyEnv: OPENCODE_API_KEY
diff --git a/.devcontainer/test-pi-superagents.bash b/.devcontainer/test-pi-superagents.bash
index 10d65be..60ebc45 100755
--- a/.devcontainer/test-pi-superagents.bash
+++ b/.devcontainer/test-pi-superagents.bash
@@ -888,7 +888,7 @@ test_install_script_drops_pi_subagents() {
         && fail "install_beforehand.bash must not install npm:pi-subagents"
     grep -q 'pi remove npm:pi-subagents' "$INSTALL_SCRIPT" \
         || fail "install_beforehand.bash must remove npm:pi-subagents"
-    # 一覧（settings）だけでなく、pi が管理する npm マニフェストも見る（#289）。
+    # 一覧（settings）だけでなく、pi が管理する npm マニフェストも見る。
     grep -q 'package-lock.json' "$INSTALL_SCRIPT" \
         || fail "install_beforehand.bash must inspect the managed npm manifests"
     return 0
@@ -956,7 +956,7 @@ case "$cmd" in
             mv "${state}.tmp" "$state"
         fi
         # 実物の pi remove は、settings に未登録でも管理マニフェストの記載は掃除し、
-        # 「No matching package found」で exit 1 を返す。この差が #289 の論点なので、
+        # 「No matching package found」で exit 1 を返す。この差が論点なので、
         # fake でも同じ振る舞いを再現する。
         if [ -n "${PI_FAKE_NPM_DIR:-}" ]; then
             for manifest in "${PI_FAKE_NPM_DIR}/package.json" "${PI_FAKE_NPM_DIR}/package-lock.json"; do
@@ -1059,7 +1059,7 @@ test_install_skips_remove_when_old_absent() {
 test_install_removes_stale_manifest_residue() {
     # settings の一覧が綺麗でも、pi が管理する npm マニフェストに旧拡張が残っていれば
     # 削除を呼ぶ。残っていると `pi update --extensions`（zsh の update()）で
-    # node_modules ごと復活し、subagent ツール名の衝突で pigo / pigod が起動できない（#289）。
+    # node_modules ごと復活し、subagent ツール名の衝突で pigo / pigod が起動できない。
     rm -f "$FAKE_STATE" "$FAKE_LOG"
     local npm_dir="${TEST_ROOT}/fake-home/.pi/agent/npm"
     mkdir -p "$npm_dir"
```

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
bash .devcontainer/test-cleanup-workspace.bash && bash .devcontainer/test-pi-superagents.bash
git grep -nE '#[0-9]{3}\b' -- .devcontainer ':!.devcontainer/README.md'
```

Expected: 2 本とも PASS。最後の `git grep` は何も表示しない（README の Issue 番号は Task 10 で外す）。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .devcontainer/cleanup-workspace.bash .devcontainer/test-cleanup-workspace.bash .devcontainer/dsh-cordis.patch.yml \
  .devcontainer/dsh-settings.yaml .devcontainer/test-pi-superagents.bash
git commit -m "chore(devcontainer): drop the migration-source leftovers from the cleanup script

The cleanup no longer reads MAATLOG_CLEANUP_*, no longer removes the yarn
cache (npm is the only installer) and no longer mentions verify.sh or issue
numbers of the repository this environment came from.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 6: check-layout のマウント検査と頑健化（仕様 9.1、持ち越し N-8・N-19）

check-layout に検査 9（mounts と `initialize.bash` の一致）を足す。検査 8 と同じく 3 つのファイル（`mounts.bash`、`initialize.bash`、`devcontainer.json`）を index から取り出し、`mounts_compare` で突き合わせる。あわせて N-19 の頑健化を行う。

- `git ls-files -s -z` の 1 レコードの分解を `split_record` にまとめる（4 か所）
- `index_entry` はステージ 0 のエントリだけを返す。衝突の解決中のファイルは「unresolved merge conflicts」と報告する
- 検査 4 と検査 8 の `git cat-file` の失敗を、終了コード 128 で止まらずに FAIL として報告する
- 検査 8・9 の欠けているファイルをまとめて報告する（`extract_devcontainer_files`）
- 検査 3 のコメントに `.git/info/exclude` を足し、ヘッダーの index から読む検査の一覧に 9 を足す
- テスト: ケース 41b の PASS 行の確認、index から読むことの確認を devcontainer.json と読み込み関数にも広げる、nuget モードの `expects`、作業ツリーにだけある devcontainer.json の skip

**Files:**
- Modify: `scripts/check-layout.sh`
- Test: `tests/scripts/test-check-layout.bash`

**Interfaces:**
- Consumes: Task 3 の `mounts_compare`（index から取り出した `mounts.bash` を source して使う）
- Produces: 新しい出力: `ok: mounts match .devcontainer/initialize.bash`、`skip: .devcontainer/devcontainer.json is not tracked (mount check)`、`FAIL: <mounts_compare の各行>`、`FAIL: .devcontainer/<name> has unresolved merge conflicts`、`FAIL: cannot read .devcontainer/<name> from the index`、`FAIL: cannot read the target of <prefix>.claude/skills/<name> from the index`

- [ ] **Step 1: 失敗するテストを書く**

`tests/scripts/test-check-layout.bash` に次の差分を当てる。`lock_repo` は mount の関数集・`initialize.bash`・mounts 付きの `devcontainer.json` も持つようにする（ヒアドキュメントの JSON のインデントはタブ）。

```diff
diff --git a/tests/scripts/test-check-layout.bash b/tests/scripts/test-check-layout.bash
index 11e3084..a3910de 100755
--- a/tests/scripts/test-check-layout.bash
+++ b/tests/scripts/test-check-layout.bash
@@ -331,20 +331,36 @@ commit_paths "$tmp/p41b" .agents .claude
 rm "$tmp/p41b/.agents/skills/foo/SKILL.md"
 bash "$checker" --root "$tmp/p41b" > "$tmp/p41b.out" 2>&1 || true
 if grep -qF 'empty tracked file:' "$tmp/p41b.out"; then printf 'FAIL: a file deleted only from the worktree was reported as empty\n' >&2; exit 1; fi
+grep -qF 'ok: skill trees hold no retired or empty tracked files' "$tmp/p41b.out" || { cat "$tmp/p41b.out" >&2; printf 'FAIL: case 41b did not run the hygiene check to the end\n' >&2; exit 1; }
+grep -qF 'PASS: check-layout' "$tmp/p41b.out" || { cat "$tmp/p41b.out" >&2; printf 'FAIL: case 41b did not pass\n' >&2; exit 1; }
 
 # 42. core.symlinks=false の checkout（symlink が通常ファイルになる）でも通過する
 git clone -q -c core.symlinks=false "$tmp/proj-ok" "$tmp/nosymlinks"
 [ -f "$tmp/nosymlinks/demo/.pi" ] && [ ! -L "$tmp/nosymlinks/demo/.pi" ] || { printf 'FAIL: core.symlinks=false did not take effect\n' >&2; exit 1; }
 bash "$checker" --root "$tmp/nosymlinks" | grep -qF 'PASS: check-layout'
 
-# .devcontainer に devcontainer.json・ロック・読み込み関数を持つ一時リポジトリを作る。ロックの SDK は 10.0.201
+# .devcontainer に devcontainer.json・ロック・読み込み関数・mount の関数集・initialize.bash を持つ一時リポジトリを作る。
+# ロックの SDK は 10.0.201。mounts は ~/.claude と ~/.claude.json の 2 つ
 lock_repo() {
   local r="$1"
   new_repo "$r"
   mkdir -p "$r/.devcontainer"
-  cp "$root/.devcontainer/resoloop-lock.bash" "$r/.devcontainer/resoloop-lock.bash"
-  printf '{\n\t"features": {\n\t\t"ghcr.io/devcontainers/features/dotnet:2": {\n\t\t\t"version": "10.0",\n\t\t\t"additionalVersions": "10.0.201"\n\t\t}\n\t}\n}\n' \
-    > "$r/.devcontainer/devcontainer.json"
+  cp "$root/.devcontainer/resoloop-lock.bash" "$root/.devcontainer/mounts.bash" "$r/.devcontainer/"
+  cat > "$r/.devcontainer/devcontainer.json" <<'EOF'
+{
+	"mounts": [
+		"source=${localEnv:HOME}/.claude,target=/home/vscode/.claude,type=bind,consistency=cached",
+		"source=${localEnv:HOME}/.claude.json,target=/home/vscode/.claude.json,type=bind,consistency=cached"
+	],
+	"features": {
+		"ghcr.io/devcontainers/features/dotnet:2": {
+			"version": "10.0",
+			"additionalVersions": "10.0.201"
+		}
+	}
+}
+EOF
+  printf '#!/bin/bash\nmkdir -p \\\n  "${HOME}/.claude"\ntouch \\\n  "${HOME}/.claude.json"\n' > "$r/.devcontainer/initialize.bash"
   cat > "$r/.devcontainer/resoloop.lock" <<'EOF'
 RESOLOOP_MODE=fork
 RESOLOOP_NUGET_VERSION=1.2.3-preview.4
@@ -363,9 +379,11 @@ EOF
 lock_repo "$tmp/lock-ok"
 bash "$checker" --root "$tmp/lock-ok" > "$tmp/lock-ok.out"
 grep -qF 'ok: resoloop lock (mode fork, expects 1.2.3-preview.4.pr1.test)' "$tmp/lock-ok.out"
+grep -qF 'ok: mounts match .devcontainer/initialize.bash' "$tmp/lock-ok.out"
 grep -qF 'PASS: check-layout' "$tmp/lock-ok.out"
 bash "$checker" --root "$tmp/clean" > "$tmp/lock-skip.out"
 grep -qF 'skip: .devcontainer/devcontainer.json is not tracked (resoloop lock check)' "$tmp/lock-skip.out"
+grep -qF 'skip: .devcontainer/devcontainer.json is not tracked (mount check)' "$tmp/lock-skip.out"
 
 # 44. devcontainer.json があるのにロックか読み込み関数が無ければ失敗する
 lock_repo "$tmp/lock-missing" && git -C "$tmp/lock-missing" rm -q .devcontainer/resoloop.lock && git -C "$tmp/lock-missing" commit -q -m rm
@@ -382,14 +400,73 @@ lock_repo "$tmp/lock-sdk" && sed -i 's/"additionalVersions": "10.0.201"/"additio
   && commit_paths "$tmp/lock-sdk" .devcontainer
 expect_fail_with "$tmp/lock-sdk" 'RESOLOOP_FORK_SDK 10.0.201 is not in additionalVersions of .devcontainer/devcontainer.json'
 
-# 47. ロックも index の内容で判定する（作業ツリーだけ壊れていても通過する）
+# 47. ロックも index の内容で判定する（作業ツリーのロック・読み込み関数・devcontainer.json が壊れていても通過する）
 lock_repo "$tmp/lock-worktree"
 printf 'broken\n' > "$tmp/lock-worktree/.devcontainer/resoloop.lock"
+printf 'resoloop_lock_load() { return 1; }\n' > "$tmp/lock-worktree/.devcontainer/resoloop-lock.bash"
+sed -i 's/"additionalVersions": "10.0.201"/"additionalVersions": "10.0.100"/' "$tmp/lock-worktree/.devcontainer/devcontainer.json"
 bash "$checker" --root "$tmp/lock-worktree" > "$tmp/lock-worktree.out"
 grep -qF 'ok: resoloop lock (' "$tmp/lock-worktree.out"
 
-# 48. このリポジトリのロックも検査される
+# 48. このリポジトリのロックと mounts も検査される
 bash "$checker" > "$tmp/self.out"
 grep -qF 'ok: resoloop lock (' "$tmp/self.out"
+grep -qF 'ok: mounts match .devcontainer/initialize.bash' "$tmp/self.out"
+
+# 49. nuget モードの期待版は RESOLOOP_NUGET_VERSION。devcontainer.json が作業ツリーにあっても追跡していなければ skip
+lock_repo "$tmp/lock-nuget" && sed -i 's/^RESOLOOP_MODE=fork$/RESOLOOP_MODE=nuget/' "$tmp/lock-nuget/.devcontainer/resoloop.lock" \
+  && commit_paths "$tmp/lock-nuget" .devcontainer
+bash "$checker" --root "$tmp/lock-nuget" > "$tmp/lock-nuget.out"
+grep -qF 'ok: resoloop lock (mode nuget, expects 1.2.3-preview.4)' "$tmp/lock-nuget.out"
+lock_repo "$tmp/lock-untracked" && git -C "$tmp/lock-untracked" rm -q --cached .devcontainer/devcontainer.json \
+  && git -C "$tmp/lock-untracked" commit -q -m untrack
+[ -f "$tmp/lock-untracked/.devcontainer/devcontainer.json" ] || { printf 'FAIL: case 49 lost the untracked file\n' >&2; exit 1; }
+bash "$checker" --root "$tmp/lock-untracked" > "$tmp/lock-untracked.out"
+grep -qF 'skip: .devcontainer/devcontainer.json is not tracked (resoloop lock check)' "$tmp/lock-untracked.out"
+grep -qF 'skip: .devcontainer/devcontainer.json is not tracked (mount check)' "$tmp/lock-untracked.out"
+
+# 50. 足りない追跡ファイルはまとめて報告する
+lock_repo "$tmp/lock-missing2" && git -C "$tmp/lock-missing2" rm -q .devcontainer/resoloop.lock .devcontainer/resoloop-lock.bash \
+  && git -C "$tmp/lock-missing2" commit -q -m rm
+expect_fail_with "$tmp/lock-missing2" 'missing tracked file .devcontainer/resoloop.lock'
+grep -qF 'missing tracked file .devcontainer/resoloop-lock.bash' "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; printf 'FAIL: only the first missing file was reported\n' >&2; exit 1; }
+
+# 51. 衝突の解決中（ステージ 0 に無い）のロックは、終了コード 1 で解決を促す（128 で止まらない）
+lock_repo "$tmp/lock-conflict"
+git -C "$tmp/lock-conflict" checkout -q -b other
+sed -i 's|^RESOLOOP_FORK_REF=.*|RESOLOOP_FORK_REF=fix/other|' "$tmp/lock-conflict/.devcontainer/resoloop.lock" && commit_paths "$tmp/lock-conflict" .devcontainer
+git -C "$tmp/lock-conflict" checkout -q -
+sed -i 's|^RESOLOOP_FORK_REF=.*|RESOLOOP_FORK_REF=fix/mine|' "$tmp/lock-conflict/.devcontainer/resoloop.lock" && commit_paths "$tmp/lock-conflict" .devcontainer
+if git -C "$tmp/lock-conflict" merge -q other >/dev/null 2>&1; then printf 'FAIL: case 51 merged without a conflict\n' >&2; exit 1; fi
+expect_fail_with "$tmp/lock-conflict" '.devcontainer/resoloop.lock has unresolved merge conflicts'
+
+# 52. index から読めない blob（壊れたオブジェクト）は、終了コード 1 の FAIL として報告する
+remove_object() {  # $1=リポジトリ、$2=パス。index にある blob のオブジェクトファイルを消す
+  local oid
+  oid="$(git -C "$1" rev-parse ":$2")"
+  rm -f "$1/.git/objects/${oid:0:2}/${oid:2}"
+}
+lock_repo "$tmp/lock-corrupt" && remove_object "$tmp/lock-corrupt" .devcontainer/resoloop.lock
+expect_fail_with "$tmp/lock-corrupt" 'cannot read .devcontainer/resoloop.lock from the index'
+skill_repo "$tmp/link-corrupt"
+ln -s ../../.agents/skills/foo "$tmp/link-corrupt/.claude/skills/foo"
+commit_paths "$tmp/link-corrupt" .agents .claude
+remove_object "$tmp/link-corrupt" .claude/skills/foo
+expect_fail_with "$tmp/link-corrupt" 'cannot read the target of .claude/skills/foo from the index'
+
+# 53. mounts のソースと initialize.bash が作るパスが違えば失敗し、食い違いを示す
+lock_repo "$tmp/mount-diff" && sed -i 's|^  "${HOME}/.claude"$|  "${HOME}/.claude" \\\n  "${HOME}/.codex"|' "$tmp/mount-diff/.devcontainer/initialize.bash" \
+  && commit_paths "$tmp/mount-diff" .devcontainer
+expect_fail_with "$tmp/mount-diff" 'mounts: ~/.codex is created by initialize.bash but not mounted by devcontainer.json'
+lock_repo "$tmp/mount-missing" && git -C "$tmp/mount-missing" rm -q .devcontainer/initialize.bash .devcontainer/mounts.bash \
+  && git -C "$tmp/mount-missing" commit -q -m rm
+expect_fail_with "$tmp/mount-missing" 'missing tracked file .devcontainer/mounts.bash'
+grep -qF 'missing tracked file .devcontainer/initialize.bash' "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; printf 'FAIL: missing initialize.bash was not reported\n' >&2; exit 1; }
+
+# 54. mounts も index の内容で判定する（作業ツリーの initialize.bash だけが違っても通過する）
+lock_repo "$tmp/mount-worktree"
+printf '#!/bin/bash\n' > "$tmp/mount-worktree/.devcontainer/initialize.bash"
+bash "$checker" --root "$tmp/mount-worktree" > "$tmp/mount-worktree.out"
+grep -qF 'ok: mounts match .devcontainer/initialize.bash' "$tmp/mount-worktree.out"
 
 printf 'PASS: check-layout script behaves as specified\n'
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && bash tests/scripts/test-check-layout.bash; echo "exit=$?"
```

Expected: 何も表示せずに終了コード 1（ケース 43 の `grep -qF 'ok: mounts match .devcontainer/initialize.bash'` の不一致）。`bash -x` で実行すると、最後に実行した行がこの `grep` であることが分かる。

- [ ] **Step 3: check-layout を直す**

```diff
diff --git a/scripts/check-layout.sh b/scripts/check-layout.sh
index b8da96e..87ce985 100755
--- a/scripts/check-layout.sh
+++ b/scripts/check-layout.sh
@@ -1,7 +1,7 @@
 #!/bin/bash
 # リポジトリのレイアウト検査。仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 9.1 節
 # 使い方: scripts/check-layout.sh [--root DIR]
-# 追跡の有無と mode、symlink の行き先、ファイルの中身は git の index から読む（検査 1・4・5・6・8）。これらの結果は
+# 追跡の有無と mode、symlink の行き先、ファイルの中身は git の index（ステージ 0）から読む（検査 1・4・5・6・8・9）。これらの結果は
 # 作業ツリーの未ステージの変更で変わらず、core.symlinks=false の checkout（symlink が通常ファイルになる）でも同じになる。
 # 例外として次の 3 つは作業ツリーを読む: 検査 2（追跡中の symlink が解決できるか）、検査 3（ignore 規則は作業ツリーの
 # .gitignore と .git/info/exclude から git が読む）、検査 7（resoloop が作業ツリーのプロジェクトを読む）。
@@ -43,15 +43,26 @@ trap 'rm -rf "$tmp_dir"' EXIT
 tmp_list="$tmp_dir/list"
 empty_blob="$(git hash-object -t blob --stdin </dev/null)"
 
-# index（ステージ 0）にあるパスと完全に一致するエントリを "mode oid" で出力する。無ければ 1。
-# パスはワイルドカードとして解釈しない。git ls-files はディレクトリの前方一致でも列挙するので、パスの一致を確かめる
+# git ls-files -s -z の 1 レコード（"<mode> <oid> <stage>\t<path>"）を rec_mode・rec_oid・rec_stage・rec_path に分ける
+rec_mode="" rec_oid="" rec_stage="" rec_path=""
+split_record() {
+  local meta="${1%%$'\t'*}"
+  rec_path="${1#*$'\t'}"
+  rec_mode="${meta%% *}"
+  meta="${meta#* }"
+  rec_oid="${meta%% *}"
+  rec_stage="${meta#* }"
+}
+
+# index のステージ 0 にあるパスと完全に一致するエントリを "mode oid" で出力する。無ければ 1（衝突の解決中で
+# ステージ 1〜3 にしか無いパスも 1）。パスはワイルドカードとして解釈しない。git ls-files はディレクトリの
+# 前方一致でも列挙するので、パスの一致を確かめる
 index_entry() {
-  local want="$1" record meta fields
+  local want="$1" record
   while IFS= read -r -d '' record; do
-    [ "${record#*$'\t'}" = "$want" ] || continue
-    meta="${record%%$'\t'*}"
-    fields="${meta#* }"
-    printf '%s %s\n' "${meta%% *}" "${fields%% *}"
+    split_record "$record"
+    [ "$rec_path" = "$want" ] && [ "$rec_stage" = 0 ] || continue
+    printf '%s %s\n' "$rec_mode" "$rec_oid"
     return 0
   done < <(git ls-files -s -z -- ":(literal)$want")
   return 1
@@ -81,13 +92,11 @@ check_symlinks_resolve() {
     fail "git ls-files -s failed"
     return
   fi
-  local broken=() record meta path mode
+  local broken=() record
   while IFS= read -r -d '' record; do
-    meta="${record%%$'\t'*}"
-    path="${record#*$'\t'}"
-    mode="${meta%% *}"
-    [ "$mode" = 120000 ] || continue
-    [ -e "$path" ] || broken+=("$path")
+    split_record "$record"
+    [ "$rec_mode" = 120000 ] || continue
+    [ -e "$rec_path" ] || broken+=("$rec_path")
   done < "$tmp_list"
   if [ ${#broken[@]} -gt 0 ]; then
     fail "dangling tracked symlinks: ${broken[*]}"
@@ -96,7 +105,7 @@ check_symlinks_resolve() {
   fi
 }
 
-# 3. 追跡中かつ ignore 対象は既知の例外だけ（ignore 規則は作業ツリーの .gitignore から読まれる）
+# 3. 追跡中かつ ignore 対象は既知の例外だけ（ignore 規則は作業ツリーの .gitignore と .git/info/exclude から読まれる）
 check_tracked_ignored() {
   local allow='MyResoniteProject/.resoloop/tokyo-nova/pipeline.json'
   if ! git -c core.excludesFile=/dev/null ls-files -z -i -c --exclude-standard > "$tmp_list"; then
@@ -124,7 +133,7 @@ check_skill_links() {
   local prefix="$1"
   local agents="${prefix}.agents/skills/" claude="${prefix}.claude/skills/"
   local -A dirs=() links=()
-  local problems=() names=() path record meta fields mode oid rest name target
+  local problems=() names=() path record rest name target
   if ! git ls-files -z -- "${prefix}.agents/skills" > "$tmp_list"; then
     fail "git ls-files failed for ${agents}"
     return
@@ -139,24 +148,23 @@ check_skill_links() {
     return
   fi
   while IFS= read -r -d '' record; do
-    meta="${record%%$'\t'*}"
-    path="${record#*$'\t'}"
-    mode="${meta%% *}"
-    fields="${meta#* }"
-    oid="${fields%% *}"
-    if [ "$path" = "${claude%/}" ]; then
+    split_record "$record"
+    if [ "$rec_path" = "${claude%/}" ]; then
       problems+=("${claude%/} must be a directory, not a symlink")
       continue
     fi
-    rest="${path#"$claude"}"
+    rest="${rec_path#"$claude"}"
     name="${rest%%/*}"
     [ -z "${links[$name]+x}" ] || continue
     links["$name"]=1
-    if [ "$mode" != 120000 ] || [ "$rest" != "$name" ]; then
+    if [ "$rec_mode" != 120000 ] || [ "$rest" != "$name" ]; then
       problems+=("${claude}${name} is not a symlink")
       continue
     fi
-    target="$(git cat-file blob "$oid")"
+    if ! target="$(git cat-file blob "$rec_oid" 2>/dev/null)"; then
+      problems+=("cannot read the target of ${claude}${name} from the index")
+      continue
+    fi
     [ "$target" = "../../.agents/skills/$name" ] || problems+=("${claude}${name} has unexpected target ${target:-<none>}")
     [ -n "${dirs[$name]+x}" ] || problems+=("${claude}${name} has no matching ${agents}${name}")
   done < "$tmp_list"
@@ -176,7 +184,7 @@ check_skill_links() {
 
 # 5. 旧 .devin/skills を追跡していない。スキル配下に 0 バイトの追跡ファイルが無い（仕様 5.5・8.1・11 章）
 check_skill_hygiene() {
-  local hits=() record meta fields path mode re='(^|/)\.(agents|claude)/skills/'
+  local hits=() record re='(^|/)\.(agents|claude)/skills/'
   if ! git ls-files -z -- .devin/skills > "$tmp_list"; then
     fail "git ls-files failed for .devin/skills"
     return
@@ -187,13 +195,10 @@ check_skill_hygiene() {
     return
   fi
   while IFS= read -r -d '' record; do
-    meta="${record%%$'\t'*}"
-    path="${record#*$'\t'}"
-    mode="${meta%% *}"
-    fields="${meta#* }"
-    [ "$mode" != 120000 ] || continue
-    [[ "$path" =~ $re ]] || continue
-    [ "${fields%% *}" != "$empty_blob" ] || hits+=("empty tracked file: $path")
+    split_record "$record"
+    [ "$rec_mode" != 120000 ] || continue
+    [[ "$rec_path" =~ $re ]] || continue
+    [ "$rec_oid" != "$empty_blob" ] || hits+=("empty tracked file: $rec_path")
   done < "$tmp_list"
   if [ ${#hits[@]} -gt 0 ]; then
     local h
@@ -276,28 +281,41 @@ check_resoloop_skills() {
   done
 }
 
+# .devcontainer/ の NAME... を index から DEST に書き出す（検査 8・9 が使う）。無いものと読めないものは
+# 1 件ずつ FAIL にし、1 つでもあれば 1 を返す
+extract_devcontainer_files() {
+  local dest="$1" name entry bad=0
+  shift
+  mkdir -p "$dest"
+  for name in "$@"; do
+    if ! entry="$(index_entry ".devcontainer/$name")"; then
+      if [ -n "$(git ls-files -u -- ":(literal).devcontainer/$name")" ]; then
+        fail ".devcontainer/$name has unresolved merge conflicts"
+      else
+        fail "missing tracked file .devcontainer/$name"
+      fi
+      bad=1
+    elif ! git cat-file blob "${entry#* }" > "$dest/$name" 2>/dev/null; then
+      fail "cannot read .devcontainer/$name from the index"
+      bad=1
+    fi
+  done
+  return "$bad"
+}
+
 # 8. ResoLoop のロック（仕様 6.1・9.1）。.devcontainer/devcontainer.json を追跡しているリポジトリだけが対象。
 # ロック・読み込み関数・devcontainer.json を index から取り出し、読み込み関数（.devcontainer/resoloop-lock.bash）で検証する
 check_resoloop_lock() {
-  local f out d="$tmp_dir/lock"
+  local out line d="$tmp_dir/lock"
   if ! index_entry .devcontainer/devcontainer.json >/dev/null; then
     printf 'skip: .devcontainer/devcontainer.json is not tracked (resoloop lock check)\n'
     return
   fi
-  for f in resoloop.lock resoloop-lock.bash; do
-    if ! index_entry ".devcontainer/$f" >/dev/null; then
-      fail "missing tracked file .devcontainer/$f"
-      return
-    fi
-  done
-  mkdir -p "$d"
-  for f in resoloop.lock resoloop-lock.bash devcontainer.json; do
-    git cat-file blob ":.devcontainer/$f" > "$d/$f"
-  done
+  extract_devcontainer_files "$d" resoloop.lock resoloop-lock.bash devcontainer.json || return 0
   if out="$(validate_lock "$d" 2>&1)"; then
     ok "resoloop lock ($out)"
   else
-    while IFS= read -r f; do fail "$f"; done <<<"$out"
+    while IFS= read -r line; do fail "$line"; done <<<"$out"
   fi
 }
 
@@ -313,6 +331,30 @@ validate_lock() (
   printf 'mode %s, expects %s' "$RESOLOOP_MODE" "$RESOLOOP_EXPECTED_VERSION"
 )
 
+# 9. devcontainer.json の mounts のソースと initialize.bash が作るパスが一致する（仕様 7.2・9.1）。
+# .devcontainer/devcontainer.json を追跡しているリポジトリだけが対象。3 つのファイルを index から取り出し、
+# .devcontainer/mounts.bash の mounts_compare で突き合わせる
+check_mounts() {
+  local out line d="$tmp_dir/mounts"
+  if ! index_entry .devcontainer/devcontainer.json >/dev/null; then
+    printf 'skip: .devcontainer/devcontainer.json is not tracked (mount check)\n'
+    return
+  fi
+  extract_devcontainer_files "$d" mounts.bash initialize.bash devcontainer.json || return 0
+  if out="$(compare_mounts "$d" 2>&1)"; then
+    ok "mounts match .devcontainer/initialize.bash"
+  else
+    while IFS= read -r line; do fail "$line"; done <<<"$out"
+  fi
+}
+
+# 比較はサブシェルで行い、mounts.bash の関数を check-layout に持ち込まない
+compare_mounts() (
+  # shellcheck source=/dev/null
+  source "$1/mounts.bash"
+  mounts_compare "$1/devcontainer.json" "$1/initialize.bash"
+)
+
 check_forbidden_tracked
 check_symlinks_resolve
 check_tracked_ignored
@@ -322,6 +364,7 @@ collect_projects
 for p in ${projects[@]+"${projects[@]}"}; do check_project "$p"; done
 check_resoloop_skills
 check_resoloop_lock
+check_mounts
 
 if [ "$failures" -gt 0 ]; then
   printf 'FAIL: check-layout (%d failure(s))\n' "$failures" >&2
```

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
bash tests/scripts/test-check-layout.bash
bash scripts/check-layout.sh | tail -n 3
```

Expected: テストは PASS。check-layout は `ok: resoloop lock (mode fork, expects 0.1.0-preview.14.pr1.20260925)`、`ok: mounts match .devcontainer/initialize.bash`、`PASS: check-layout` で終わる。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add scripts/check-layout.sh tests/scripts/test-check-layout.bash
git commit -m "feat(check-layout): compare the mounts with initialize.bash and harden index reads

Check 9 reads devcontainer.json, initialize.bash and mounts.bash from the index
and reports every difference between the mount sources and the paths
initialize.bash creates. Index reads now use stage 0 only, report unresolved
merge conflicts and unreadable blobs as failures instead of exiting with 128,
report every missing .devcontainer file at once, and share one record parser.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 7: fork スクリプトと verify の持ち越し（N-20・N-21）

`scripts/resoloop-fork.sh` は、相対パスの `RESOLOOP_FORK_CHECKOUT` を呼び出し時の cwd を基準に絶対パスにする（`realpath -ms`。symlink は解決しない）。status は、checkout が無いときと自前の checkout でないときにも `remotes:` の行を出し、後者には対処も示す。`verify-resonite-tooling.bash` は `dotnet --list-sdks` の出力を変数に取ってから探す（SIGPIPE を避ける）。テストの抜け（sync の remote 不一致、install の build / pack、`.git` の有無、checkout の fetch、sync の fast-forward と分岐したローカル main、status の DIFFERS / unknown、fork モードの導入済み判定の後の shim の改変、行末のコメント付きの `additionalVersions`）を埋める。

`resoloop_lock_sdk_declared` の 1 行前提（N-21 の後半）は、Task 3 の `devcontainer.json` の改訂が `additionalVersions` の行を変えないため、そのままにする。行末のコメントを読み飛ばすことをテストで固定し、コメントに「キーと値は同じ行に書く前提」と残す。

**Files:**
- Modify: `scripts/resoloop-fork.sh`、`.devcontainer/verify-resonite-tooling.bash`
- Test: `tests/scripts/test-resoloop-fork.bash`（モックの `dotnet tool list` の失敗と、ケース 23〜29）、`.devcontainer/test-install-resoloop.bash`（ケース 7 の shim の改変）、`.devcontainer/test-resoloop-lock.bash`（ケース 6 の行末のコメント）

**Interfaces:**
- Produces: status の新しい行 `remotes: unknown (no checkout)`。自前の checkout でないときの行は `checkout: <dir> exists but is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-fork.sh clone`。

- [ ] **Step 1: 失敗するテストを書く**

```diff
diff --git a/.devcontainer/test-install-resoloop.bash b/.devcontainer/test-install-resoloop.bash
index 0f0c66d..1c58882 100755
--- a/.devcontainer/test-install-resoloop.bash
+++ b/.devcontainer/test-install-resoloop.bash
@@ -132,6 +132,10 @@ if grep -q '^tool ' "$DOTNET_CALLS"; then fail 'fork mode ran dotnet tool itself
 : > "$DOTNET_CALLS"
 expect_ok '1.2.3-preview.4.pr1.test is already installed'
 [ ! -s "$DOTNET_CALLS" ] || fail 'fork mode rebuilt an installed version'
+# 導入済みと判定しても --version は照合する（shim が別の版を返せば失敗する）
+printf '#!/bin/bash\nprintf "0.0.1\\n"\n' > "$HOME/.dotnet/tools/resoloop"
+expect_fail 'resoloop --version reports 0.0.1, but'
+[ ! -s "$DOTNET_CALLS" ] || fail 'fork mode rebuilt an installed version after the check failed'
 reset
 expect_fail 'building and installing the fork failed' FORK_FAIL=1
 
diff --git a/.devcontainer/test-resoloop-lock.bash b/.devcontainer/test-resoloop-lock.bash
index 02866bb..57c3bf7 100755
--- a/.devcontainer/test-resoloop-lock.bash
+++ b/.devcontainer/test-resoloop-lock.bash
@@ -81,6 +81,9 @@ printf '{\n  // "additionalVersions": "10.0.201"\n  "a": { "version": "10.0" }\n
 if resoloop_lock_sdk_declared "$tmp/comment.json" 10.0.201; then fail 'counted a commented-out line'; fi
 if resoloop_lock_sdk_declared "$tmp/list.json" 10.0.2; then fail 'matched a version prefix'; fi
 if resoloop_lock_sdk_declared "$tmp/none.json" 10.0.201; then fail 'accepted a missing devcontainer.json'; fi
+# 値の後ろの // コメントは読み飛ばす（キーと値は同じ行に書く前提。devcontainer.json を改訂したときに見直す）
+printf '{\n  "a": {\n    "additionalVersions": "10.0.201" // fork の SDK\n  }\n}\n' > "$tmp/trailing.json"
+resoloop_lock_sdk_declared "$tmp/trailing.json" 10.0.201 || fail 'a trailing comment hid the SDK'
 
 # 7. resoloop --version の出力から版を取り出す
 [ "$(resoloop_version_of $'0.1.0-preview.14\n')" = 0.1.0-preview.14 ] || fail 'plain version'
diff --git a/tests/scripts/test-resoloop-fork.bash b/tests/scripts/test-resoloop-fork.bash
index e25884f..c30cecb 100755
--- a/tests/scripts/test-resoloop-fork.bash
+++ b/tests/scripts/test-resoloop-fork.bash
@@ -64,6 +64,7 @@ case "$1" in
   tool)
     case "$2" in
       list)
+        [ "${MOCK_LIST_FAIL:-0}" = 0 ] || exit 1
         printf 'Package Id      Version      Commands\n'
         [ ! -s "$MOCK_STATE" ] || printf 'resoloop      %s      resoloop\n' "$(cat "$MOCK_STATE")" ;;
       install|update)
@@ -268,4 +269,75 @@ chmod +x "$HOME/.dotnet/tools/resoloop"
 printf '0.1.0-preview.14.pr1.test\n' > "$MOCK_STATE"
 MOCK_SDKS='10.0.401 [/usr/share/dotnet/sdk]' expect_exit 0 'is already installed' install
 
+# 23. 相対パスの RESOLOOP_FORK_CHECKOUT は呼び出し時の cwd を基準に絶対パスにする。install は build と pack を
+#     checkout の中で実行し、--add-source にも絶対パスを渡す
+mkdir -p "$tmp/work"
+printf '0.0.1\n' > "$MOCK_STATE"
+: > "$MOCK_LOG"
+(cd "$tmp/work" && RESOLOOP_FORK_CHECKOUT=external/resoloop expect_exit 0 'ok: resoloop --version is 0.1.0-preview.14.pr1.test' install)
+grep -qF "cloned: $co" "$tmp/out.txt" || fail 'install did not clone into the absolute path'
+grep -qxF "dotnet build ResoLoop.slnx -c Release --nologo (cwd=$co)" "$MOCK_LOG" || fail 'install did not build'
+grep -qxF "dotnet pack src/RLoop.Cli/RLoop.Cli.csproj -c Release --nologo -o artifacts/fork -p:PackageVersion=0.1.0-preview.14.pr1.test -p:Version=0.1.0-preview.14.pr1.test (cwd=$co)" "$MOCK_LOG" \
+  || fail 'install did not pack'
+grep -qxF "dotnet tool update --global ResoLoop --add-source $co/artifacts/fork --version 0.1.0-preview.14.pr1.test --allow-downgrade (cwd=$repo_root)" "$MOCK_LOG" \
+  || fail 'install passed a relative --add-source'
+(cd "$tmp/work" && RESOLOOP_FORK_CHECKOUT=external/resoloop expect_exit 0 "checkout: $co at $fix_commit (detached, clean, matches the lock)" status)
+
+# 24. status は導入済み版と checkout の食い違いを DIFFERS、導入済み版を読めないときは unknown と表示する
+git -C "$co" checkout -q main
+main_head="$(git -C "$co" rev-parse HEAD)"
+printf '0.0.1\n' > "$MOCK_STATE"
+expect_exit 0 "checkout: $co at $main_head (main, clean, DIFFERS from the lock)" status
+grep -qF 'installed version: 0.0.1 (DIFFERS from the lock)' "$tmp/out.txt" || fail 'status did not flag the installed version'
+MOCK_LIST_FAIL=1 expect_exit 0 'installed version: unknown (dotnet tool list --global failed)' status
+
+# 25. 末尾の .git の有無だけが違う URL も同じとみなす
+git -C "$co" remote set-url origin "$tmp/origin"
+expect_exit 0 'is already cloned' clone
+git -C "$co" remote set-url origin "$tmp/origin.git"
+
+# 26. remote が食い違っていれば、sync は fetch も push もせずに 1
+git -C "$co" remote set-url upstream "$tmp/origin.git"
+origin_before="$(git -C "$tmp/origin.git" rev-parse main)"
+expect_exit 1 'has unexpected remotes' sync
+grep -qF "remote upstream is $tmp/origin.git (expected $tmp/upstream.git)" "$tmp/out.txt" || fail 'sync did not name the mismatching remote'
+[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$origin_before" ] || fail 'sync pushed despite mismatching remotes'
+git -C "$co" remote set-url upstream "$tmp/upstream.git"
+
+# 27. main を checkout 中でも、きれいなローカル main は sync が fast-forward する。上流に無いコミットを持つローカル
+#     main は動かさずに 1（origin への push は済ませる）
+git -C "$tmp/seed" checkout -q main
+printf 'v4\n' >> "$tmp/seed/file.txt"
+git -C "$tmp/seed" commit -q -am v4
+git -C "$tmp/seed" push -q "$tmp/upstream.git" main
+v4="$(git -C "$tmp/seed" rev-parse HEAD)"
+expect_exit 0 "updated: local main -> $v4" sync
+[ "$(git -C "$co" rev-parse HEAD)" = "$v4" ] && [ "$(git -C "$co" symbolic-ref --short HEAD)" = main ] || fail 'sync did not fast-forward the checked-out main'
+[ -z "$(git -C "$co" status --porcelain --untracked-files=no)" ] || fail 'sync left changes to tracked files'
+printf 'local\n' >> "$co/file.txt" && git -C "$co" commit -q -am local
+local_main="$(git -C "$co" rev-parse main)"
+printf 'v5\n' >> "$tmp/seed/file.txt"
+git -C "$tmp/seed" commit -q -am v5
+git -C "$tmp/seed" push -q "$tmp/upstream.git" main
+v5="$(git -C "$tmp/seed" rev-parse HEAD)"
+expect_exit 1 'local main has commits that upstream/main lacks' sync
+[ "$(git -C "$tmp/origin.git" rev-parse main)" = "$v5" ] || fail 'sync did not push origin main'
+[ "$(git -C "$co" rev-parse main)" = "$local_main" ] || fail 'sync moved a diverged local main'
+
+# 28. origin に後から push されたコミットも、checkout は fetch してから取り出す
+git -C "$tmp/seed" checkout -q fix/x
+printf 'fix2\n' >> "$tmp/seed/file.txt"
+git -C "$tmp/seed" commit -q -am fix2
+git -C "$tmp/seed" push -q "$tmp/origin.git" fix/x
+fix2="$(git -C "$tmp/seed" rev-parse HEAD)"
+if git -C "$co" cat-file -e "$fix2^{commit}" 2>/dev/null; then fail 'case 28 needs a commit the checkout has not fetched'; fi
+write_lock fork "$fix2"
+expect_exit 0 "checked out: $co at $fix2 (detached)" checkout
+write_lock fork
+
+# 29. checkout が無い・自前の checkout でないときも、status は remotes の行を出す。後者は対処も示す
+RESOLOOP_FORK_CHECKOUT="$tmp/work/none" expect_exit 0 'remotes: unknown (no checkout)' status
+RESOLOOP_FORK_CHECKOUT="$tmp/outer/external/resoloop" expect_exit 0 'is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-fork.sh clone' status
+grep -qF 'remotes: unknown (no checkout)' "$tmp/out.txt" || fail 'status lacks the remotes line for a directory that is not a checkout'
+
 printf 'PASS: resoloop-fork script behaves as specified\n'
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W"
bash tests/scripts/test-resoloop-fork.bash; echo "exit=$?"
bash .devcontainer/test-install-resoloop.bash && bash .devcontainer/test-resoloop-lock.bash
```

Expected: 1 本目は `FAIL: install did not clone into the absolute path` で終了コード 1。残りの 2 本は既存の挙動を固定するテストの追加なので、この時点で PASS する。

- [ ] **Step 3: スクリプトを直す**

```diff
diff --git a/.devcontainer/verify-resonite-tooling.bash b/.devcontainer/verify-resonite-tooling.bash
index 485a5ab..3930a5c 100755
--- a/.devcontainer/verify-resonite-tooling.bash
+++ b/.devcontainer/verify-resonite-tooling.bash
@@ -6,7 +6,8 @@ lock="${RESOLOOP_LOCK_FILE:-$root/.devcontainer/resoloop.lock}"
 # shellcheck source=resoloop-lock.bash
 source "$root/.devcontainer/resoloop-lock.bash"
 
-if ! dotnet --list-sdks | grep -qE '^10\.'; then
+# 一覧を変数に取ってから探す（pipefail の下で grep -q が dotnet を SIGPIPE で止めないように）
+if ! sdks="$(dotnet --list-sdks </dev/null)" || ! grep -qE '^10\.' <<<"$sdks"; then
     echo 'Toolchain verification: .NET 10 SDK is unavailable.' >&2
     exit 1
 fi
diff --git a/scripts/resoloop-fork.sh b/scripts/resoloop-fork.sh
index cd4f7af..339ce20 100755
--- a/scripts/resoloop-fork.sh
+++ b/scripts/resoloop-fork.sh
@@ -34,7 +34,9 @@ esac
 
 root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 lock="${RESOLOOP_LOCK_FILE:-$root/.devcontainer/resoloop.lock}"
-dir="${RESOLOOP_FORK_CHECKOUT:-$root/external/resoloop}"
+# 相対パスの RESOLOOP_FORK_CHECKOUT は呼び出し時の cwd を基準に絶対パスにする（install は $root に cd してから
+# --add-source を渡すため）。symlink は解決しない
+dir="$(realpath -ms -- "${RESOLOOP_FORK_CHECKOUT:-$root/external/resoloop}")"
 # shellcheck source=../.devcontainer/resoloop-lock.bash
 source "$root/.devcontainer/resoloop-lock.bash"
 resoloop_lock_load "$lock" || die 3 "fix $lock first"
@@ -52,9 +54,11 @@ is_checkout() {  # $dir がそれ自体 git の checkout のルートなら 0（
   [ "$(cd "$top" && pwd -P)" = "$(cd "$dir" && pwd -P)" ]
 }
 
+not_a_checkout="exists but is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-fork.sh clone"
+
 require_checkout() {
   [ -e "$dir" ] || [ -L "$dir" ] || die 3 "$dir is missing; run scripts/resoloop-fork.sh clone"
-  is_checkout || die 1 "$dir exists but is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-fork.sh clone"
+  is_checkout || die 1 "$dir $not_a_checkout"
 }
 
 check_remotes() {  # origin と upstream をロックと比べ、食い違いを 1 件 1 行で出力する。食い違いがあれば 1
@@ -86,7 +90,7 @@ dirty() {  # 追跡ファイルに未コミットの変更があれば 0（未
 
 do_clone() {
   if [ -e "$dir" ] || [ -L "$dir" ]; then
-    is_checkout || die 1 "$dir exists but is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-fork.sh clone"
+    is_checkout || die 1 "$dir $not_a_checkout"
     require_remotes
     printf 'ok: %s is already cloned (origin and upstream match the lock)\n' "$dir"
     return
@@ -222,10 +226,12 @@ do_status() {
   printf 'lock commit: %s (%s)\n' "$RESOLOOP_FORK_COMMIT" "$RESOLOOP_FORK_REF"
   if [ ! -e "$dir" ] && [ ! -L "$dir" ]; then
     printf 'checkout: %s is missing (run scripts/resoloop-fork.sh clone)\n' "$dir"
+    printf 'remotes: unknown (no checkout)\n'
     return
   fi
   if ! is_checkout; then
-    printf 'checkout: %s exists but is not a git checkout of its own\n' "$dir"
+    printf 'checkout: %s %s\n' "$dir" "$not_a_checkout"
+    printf 'remotes: unknown (no checkout)\n'
     return
   fi
   head="$(git -C "$dir" rev-parse -q --verify HEAD || printf 'none')"
```

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
bash tests/scripts/test-resoloop-fork.bash && bash .devcontainer/test-verify-resonite-tooling.bash
bash .devcontainer/verify-resonite-tooling.bash; echo "exit=$?"   # 実環境の読み取りだけの確認
bash scripts/resoloop-fork.sh status                              # 読み取りだけ
```

Expected: 2 本とも PASS。verify は 0。status は `installed version: 0.1.0-preview.14.pr1.20260925 (matches the lock)` と `remotes: origin and upstream match the lock` を含む（`$W/external/resoloop` は clone 済み）。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add scripts/resoloop-fork.sh .devcontainer/verify-resonite-tooling.bash tests/scripts/test-resoloop-fork.bash \
  .devcontainer/test-install-resoloop.bash .devcontainer/test-resoloop-lock.bash
git commit -m "fix(resoloop): resolve a relative fork checkout and fill the fork test gaps

A relative RESOLOOP_FORK_CHECKOUT is made absolute from the caller's directory,
so install no longer passes a relative --add-source after changing to the
repository root. status prints a remotes line and the remedy when there is no
checkout of its own. The toolchain check reads the SDK list before matching it.
Tests now cover sync with mismatching remotes, fast-forwarding a checked-out
main, a diverged local main, fetching before checkout, and the status lines.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 8: テストの git 設定の隔離と PATH（持ち越し P-4・N-11・N-22）

git の設定を隔離する 4 本のテスト（`test-check-layout`、`test-gitignore`、`test-new-world`、`test-resoloop-fork`）は、グローバル設定の `safe.directory` も外してしまう。そこで、このリポジトリのパスをコマンドスコープの `safe.directory` として渡す。`GIT_CONFIG_COUNT` の環境変数で渡した値が効くことは、root 所有のリポジトリで確かめた（git 2.55）。

`/usr/local/bin:/usr/bin:/bin` に resoloop や uv が無いことを前提にした「縮小 PATH」は、「指定したコマンドだけが無い PATH」を作る補助関数 `path_without` に置き換える。これで、コマンドの置き場所が違う CI のランナーでも同じ条件になる。ペルソナ節の sha256 の固定は残し、失敗の表示に更新の手順を足す（D-16）。new-world のテストに、途中のディレクトリがディレクトリへの symlink の場合と、ケース 23・26・27 の無変更の確認を足す（N-22）。

**Files:**
- Create: `tests/scripts/lib/path.bash`（source して使う補助。mode 100644。`tests/scripts/*.bash` の glob に入らない場所に置く）
- Test: `tests/scripts/test-check-layout.bash`、`tests/scripts/test-gitignore.bash`、`tests/scripts/test-new-world.bash`、`tests/scripts/test-resoloop-fork.bash`、`tests/scripts/test-instructions.bash`

**Interfaces:**
- Produces: `path_without DIR NAME...` — 今の PATH にあるコマンドのうち NAME... 以外を DIR に symlink で並べ、DIR を出力する（`PATH="$(path_without "$tmp/x" resoloop)"` のように使う）。Task 11 の CI 相当の確認も使う。

この Task はテストだけを変える。先に失敗するテストを書く手順は無く、各ステップで既存のテストが通り続けることを確かめる。

- [ ] **Step 1: 補助関数を作る**

`tests/scripts/lib/path.bash` を次の内容で作る（実行権は付けない）。

```bash
#!/bin/bash
# tests/scripts のテストが source して使う補助関数。
# path_without DIR NAME...
#   今の PATH にあるコマンドのうち NAME... 以外を DIR に symlink で並べ、DIR を出力する。「NAME... だけが無い PATH」を、
#   コマンドの置き場所が違う環境（CI のランナーなど）でも同じように作るために使う（PATH="$(path_without ...)"）
path_without() {
  local dir="$1" entry file name skip x
  local -a entries=()
  shift
  mkdir -p "$dir"
  IFS=: read -r -a entries <<<"$PATH"
  for entry in "${entries[@]}"; do
    [ -d "$entry" ] || continue
    for file in "$entry"/*; do
      name="${file##*/}"
      [ -x "$file" ] && [ ! -d "$file" ] || continue
      [ ! -e "$dir/$name" ] && [ ! -L "$dir/$name" ] || continue   # PATH の先にあるものを優先する
      skip=0
      for x in "$@"; do [ "$name" != "$x" ] || skip=1; done
      [ "$skip" = 1 ] || ln -s "$file" "$dir/$name"
    done
  done
  printf '%s\n' "$dir"
}
```

- [ ] **Step 2: 4 本のテストの隔離と PATH を直す**

```diff
diff --git a/tests/scripts/test-check-layout.bash b/tests/scripts/test-check-layout.bash
index a3910de..335d438 100755
--- a/tests/scripts/test-check-layout.bash
+++ b/tests/scripts/test-check-layout.bash
@@ -1,11 +1,16 @@
 #!/bin/bash
 # scripts/check-layout.sh が通過・失敗を正しく判定することを一時リポジトリで検査する
 set -euo pipefail
+root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
 # GIT_CONFIG_GLOBAL=/dev/null だけでは XDG 既定の ~/.config/git/ignore が働いてしまうため、
-# core.excludesFile も無効化し、システム設定も外してユーザの git 設定から隔離する
+# core.excludesFile も無効化し、システム設定も外してユーザの git 設定から隔離する。
+# グローバル設定の safe.directory も外れるので、このリポジトリだけは所有者が違っても（CI のコンテナや
+# Dev Container の bind mount）読めるようにしておく
 export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
-export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null
-root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
+export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
+  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$root"
+# shellcheck source=lib/path.bash
+source "$root/tests/scripts/lib/path.bash"
 checker="$root/scripts/check-layout.sh"
 tmp="$(mktemp -d)"
 trap 'rm -rf "$tmp"' EXIT
@@ -213,10 +218,11 @@ grep -qF 'ok: resoloop skills sync --check (demo)' "$tmp/proj-ok.out"
 grep -qF 'PASS: check-layout' "$tmp/proj-ok.out"
 
 # 22. resoloop が無い環境（CI）では skip を表示して通過する
-if PATH=/usr/local/bin:/usr/bin:/bin command -v resoloop >/dev/null 2>&1; then
-  printf 'FAIL: resoloop visible on the reduced PATH\n' >&2; exit 1
+no_resoloop="$(path_without "$tmp/no-resoloop" resoloop)"
+if PATH="$no_resoloop" command -v resoloop >/dev/null 2>&1; then
+  printf 'FAIL: resoloop visible on the PATH without resoloop\n' >&2; exit 1
 fi
-PATH=/usr/local/bin:/usr/bin:/bin bash "$checker" --root "$tmp/proj-ok" > "$tmp/proj-skip.out"
+PATH="$no_resoloop" bash "$checker" --root "$tmp/proj-ok" > "$tmp/proj-skip.out"
 grep -qF 'skip: resoloop not found (skills sync check)' "$tmp/proj-skip.out"
 grep -qF 'PASS: check-layout' "$tmp/proj-skip.out"
 
diff --git a/tests/scripts/test-gitignore.bash b/tests/scripts/test-gitignore.bash
index 21f05f2..9093511 100755
--- a/tests/scripts/test-gitignore.bash
+++ b/tests/scripts/test-gitignore.bash
@@ -1,11 +1,14 @@
 #!/bin/bash
 # ルート .gitignore が仕様 4.4 の追跡方針どおりに働くことを検査する
 set -euo pipefail
+root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
 # GIT_CONFIG_GLOBAL=/dev/null だけでは XDG 既定の ~/.config/git/ignore が働いてしまうため、
-# core.excludesFile も無効化し、システム設定も外してユーザの git 設定から隔離する
+# core.excludesFile も無効化し、システム設定も外してユーザの git 設定から隔離する。
+# グローバル設定の safe.directory も外れるので、このリポジトリだけは所有者が違っても（CI のコンテナや
+# Dev Container の bind mount）読めるようにしておく
 export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
-export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null
-root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
+export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
+  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$root"
 cd "$root"
 
 expect_ignored() {
diff --git a/tests/scripts/test-instructions.bash b/tests/scripts/test-instructions.bash
index 5dc0119..0bc94ec 100755
--- a/tests/scripts/test-instructions.bash
+++ b/tests/scripts/test-instructions.bash
@@ -56,8 +56,11 @@ lacks .pi/APPEND_SYSTEM.md '@.agents/skills/'
 for s in '/skill:agent-handoff' 'async: false' 'herdr-agent-task' 'pi-model-name' 'simplify-in-subagent' 'MODEL_NAME'; do
   has .pi/APPEND_SYSTEM.md "$s"
 done
-# ペルソナ節（## Response Persona 以降）は 1 バイトも変えない
+# ペルソナ節（## Response Persona 以降）は利用者が書く部分で、エージェントは 1 バイトも変えない。
+# 利用者が意図して変えたときは、失敗の表示にある新しいハッシュで expected_persona を更新する
+expected_persona=906d9d2570a9662427a95609efcc29454a5f46f1591352f8b264b996895e2995
 persona="$(sed -n '/^## Response Persona/,$p' .pi/APPEND_SYSTEM.md | sha256sum | cut -d' ' -f1)"
-[ "$persona" = 906d9d2570a9662427a95609efcc29454a5f46f1591352f8b264b996895e2995 ] || fail 'persona section changed'
+[ "$persona" = "$expected_persona" ] \
+  || fail "persona section changed (sha256 $persona); if the change is intended, update expected_persona in tests/scripts/test-instructions.bash"
 
 printf 'PASS: root instruction files follow spec 5.2 and 5.3\n'
diff --git a/tests/scripts/test-new-world.bash b/tests/scripts/test-new-world.bash
index f8ce21c..f6a5035 100755
--- a/tests/scripts/test-new-world.bash
+++ b/tests/scripts/test-new-world.bash
@@ -1,9 +1,14 @@
 #!/bin/bash
 # scripts/new-world.sh の作成・適用・冪等性・食い違いの検出を、一時リポジトリとモックの resoloop / uv で検査する
 set -euo pipefail
-export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
-export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null
 repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
+# ユーザの git 設定から隔離する（システム・グローバル設定と core.excludesFile を外す）。グローバル設定の
+# safe.directory も外れるので、このリポジトリだけは所有者が違っても読めるようにしておく
+export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
+export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
+  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$repo_root"
+# shellcheck source=lib/path.bash
+source "$repo_root/tests/scripts/lib/path.bash"
 script="$repo_root/scripts/new-world.sh"
 tmp="$(cd "$(mktemp -d)" && pwd -P)"
 trap 'rm -rf "$tmp"' EXIT
@@ -127,8 +132,9 @@ expect_exit 3 'not a resoloop project' "$tmp/r9" --apply --no-sync plain
 
 # 10. resoloop が無ければ新規作成は 3
 new_root "$tmp/r10"
-if PATH=/usr/local/bin:/usr/bin:/bin command -v resoloop >/dev/null 2>&1; then fail 'resoloop visible on the reduced PATH'; fi
-PATH=/usr/local/bin:/usr/bin:/bin expect_exit 3 'resoloop not found' "$tmp/r10" --no-sync demo
+no_resoloop="$(path_without "$tmp/no-resoloop" resoloop)"
+if PATH="$no_resoloop" command -v resoloop >/dev/null 2>&1; then fail 'resoloop visible on the PATH without resoloop'; fi
+PATH="$no_resoloop" expect_exit 3 'resoloop not found' "$tmp/r10" --no-sync demo
 
 # 11. 同期ありでは uv sync をプロジェクトで実行し、resoloop skills sync --check を呼ぶ
 new_root "$tmp/r11"
@@ -166,9 +172,10 @@ PATH="$tmp/uv-fail:$PATH" expect_exit 3 'already applied' "$tmp/r14" demo
 new_root "$tmp/r15"
 mkdir -p "$tmp/resoloop-only"
 cp "$tmp/mockbin/resoloop" "$tmp/resoloop-only/resoloop"
-if PATH=/usr/bin:/bin command -v uv >/dev/null 2>&1; then fail 'uv visible on the reduced PATH'; fi
+no_uv="$(path_without "$tmp/no-uv" uv resoloop)"
+if PATH="$no_uv" command -v uv >/dev/null 2>&1; then fail 'uv visible on the PATH without uv'; fi
 : > "$MOCK_LOG"
-PATH="$tmp/resoloop-only:/usr/bin:/bin" expect_exit 3 'uv not found' "$tmp/r15" demo
+PATH="$tmp/resoloop-only:$no_uv" expect_exit 3 'uv not found' "$tmp/r15" demo
 [ ! -e "$tmp/r15/demo" ] || fail 'created the project although uv is missing'
 [ ! -s "$MOCK_LOG" ] || fail 'ran resoloop although uv is missing'
 
@@ -241,7 +248,9 @@ expect_exit 1 'CONFLICT: .claude is not a directory' "$tmp/r22" --apply --no-syn
 new_root "$tmp/r23"
 run "$tmp/r23" --no-sync demo >/dev/null
 ln -s ../../.agents/skills/.old "$tmp/r23/demo/.claude/skills/.old"
+before="$(snapshot "$tmp/r23/demo")"
 expect_exit 1 'CONFLICT: .claude/skills/.old has no matching .agents/skills/.old' "$tmp/r23" --apply --no-sync demo
+[ "$before" = "$(snapshot "$tmp/r23/demo")" ] || fail 'case 23 changed files'
 
 # 24. AGENTS.md が symlink なら追記せずに 1（リンク先を書き換えない、N-16）
 new_root "$tmp/r24"
@@ -265,13 +274,17 @@ grep -qF 'CONFLICT: CLAUDE.md differs from templates/world-project/CLAUDE.md' "$
 new_root "$tmp/r26"
 run "$tmp/r26" --no-sync demo >/dev/null
 rm "$tmp/r26/demo/.pi" && ln -s ../other "$tmp/r26/demo/.pi"
+before="$(snapshot "$tmp/r26/demo")"
 expect_exit 1 'CONFLICT: .pi points to ../other, expected ../.pi' "$tmp/r26" --apply --no-sync demo
+[ "$before" = "$(snapshot "$tmp/r26/demo")" ] || fail 'case 26 changed files'
 
 # 27. 行き先が存在しないことになる symlink は 1（N-16）
 new_root "$tmp/r27"
 run "$tmp/r27" --no-sync demo >/dev/null
 rm "$tmp/r27/demo/.claude/settings.json" "$tmp/r27/.claude/settings.json"
+before="$(snapshot "$tmp/r27/demo")"
 expect_exit 1 'CONFLICT: .claude/settings.json would point to missing ../../.claude/settings.json' "$tmp/r27" --apply --no-sync demo
+[ "$before" = "$(snapshot "$tmp/r27/demo")" ] || fail 'case 27 changed files'
 
 # 28. ルートの .claude/settings.json が無ければ、新規作成は resoloop init を呼ばず何も作らずに 3（N-16）
 new_root "$tmp/r28"
@@ -288,4 +301,15 @@ mkdir -p "$tmp/r29/demo/.agents/skills/a|b" && printf -- '---\nname: ab\n---\n'
 expect_exit 0 'DONE: demo' "$tmp/r29" --apply --no-sync demo
 [ "$(readlink "$tmp/r29/demo/.claude/skills/a|b")" = '../../.agents/skills/a|b' ] || fail 'link for a name containing |'
 
+# 30. 途中のディレクトリがディレクトリへの symlink でも 1 を返し、リンク先にも手元にも書かない（N-16）
+new_root "$tmp/r30"
+run "$tmp/r30" --no-sync demo >/dev/null
+mv "$tmp/r30/demo/.claude" "$tmp/r30/claude-elsewhere" && ln -s ../claude-elsewhere "$tmp/r30/demo/.claude"
+rm "$tmp/r30/claude-elsewhere/settings.json"
+before="$(snapshot "$tmp/r30/demo")"
+before_target="$(snapshot "$tmp/r30/claude-elsewhere")"
+expect_exit 1 'CONFLICT: .claude is not a directory' "$tmp/r30" --apply --no-sync demo
+[ "$before" = "$(snapshot "$tmp/r30/demo")" ] || fail 'case 30 changed files'
+[ "$before_target" = "$(snapshot "$tmp/r30/claude-elsewhere")" ] || fail 'case 30 wrote through the .claude symlink'
+
 printf 'PASS: new-world script behaves as specified\n'
diff --git a/tests/scripts/test-resoloop-fork.bash b/tests/scripts/test-resoloop-fork.bash
index c30cecb..668c16b 100755
--- a/tests/scripts/test-resoloop-fork.bash
+++ b/tests/scripts/test-resoloop-fork.bash
@@ -1,10 +1,13 @@
 #!/bin/bash
 # scripts/resoloop-fork.sh を、ローカルの bare リポジトリとモックの dotnet で検査する（ネットワークと実 SDK を使わない）
 set -euo pipefail
+repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
+# ユーザの git 設定から隔離する（システム・グローバル設定と core.excludesFile を外す）。グローバル設定の
+# safe.directory も外れるので、このリポジトリだけは所有者が違っても読めるようにしておく
 export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
-export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null
+export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
+  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$repo_root"
 export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com
-repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
 script="$repo_root/scripts/resoloop-fork.sh"
 tmp="$(cd "$(mktemp -d)" && pwd -P)"
 trap 'rm -rf "$tmp"' EXIT
```

- [ ] **Step 3: テストが通り、追加したケースが検出力を持つことを確かめる**

```bash
cd "$W"
for t in tests/scripts/*.bash; do bash "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done
# ケース 30 は、new-world.sh の parent_ok が symlink を見なくなると失敗する（確認したら元に戻す）
cp scripts/new-world.sh /tmp/new-world.sh.bak
sed -i 's/    if \[ -L "\$proj\/\$parent" \] || { \[ -e "\$proj\/\$parent" \] && \[ ! -d "\$proj\/\$parent" \]; }; then/    if { [ -e "$proj\/$parent" ] \&\& [ ! -d "$proj\/$parent" ]; }; then/' scripts/new-world.sh
bash tests/scripts/test-new-world.bash >/dev/null 2>&1 && echo 'UNEXPECTED PASS' || echo 'case 30 detects it'
cp /tmp/new-world.sh.bak scripts/new-world.sh && git diff --quiet -- scripts/new-world.sh && echo restored
```

Expected: 6 本とも PASS。続いて `case 30 detects it` と `restored` を表示する。

- [ ] **Step 4: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add tests/scripts/lib/path.bash tests/scripts/test-check-layout.bash tests/scripts/test-gitignore.bash \
  tests/scripts/test-new-world.bash tests/scripts/test-resoloop-fork.bash tests/scripts/test-instructions.bash
git commit -m "test: keep the repository readable under isolated git config and portable PATHs

Tests that isolate git config now pass safe.directory for the repository in
the command scope, so they work when the checkout belongs to another user (CI
containers, bind mounts). The reduced PATHs that assumed where resoloop and uv
live are replaced by path_without, which drops only the named commands. The
persona hash check explains how to update it, and new-world gains a symlinked
parent case and no-change checks for cases 23, 26 and 27.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 9: `run-tests.bash` と CI（仕様 7.2・9.2、持ち越し N-1）

`.devcontainer/run-tests.bash` で `.devcontainer/test-*.bash` と `tests/scripts/*.bash` をまとめて実行する（D-11）。`.github/workflows/ci.yml` に仕様 9.2 の 4 ジョブを置き、`.gitleaks.toml` で resoloop のマニフェストの識別子を gitleaks の誤検出から外す（D-13）。実行権（仕様 7.2）は git の index 上で検査する。

**Files:**
- Create: `.devcontainer/run-tests.bash`（mode 100755）、`.devcontainer/test-run-tests.bash`（mode 100755）
- Create: `.github/workflows/ci.yml`、`.gitleaks.toml`
- Create: `tests/scripts/test-ci.bash`（mode 100755）、`tests/scripts/test-file-modes.bash`（mode 100755）

**Interfaces:**
- Produces: `bash .devcontainer/run-tests.bash [--list | テストのパス...]` — 引数なしで全テストを実行する。各テストについて `PASS <path> (<秒>s)` か `FAIL <path> (<秒>s)` を表示し、FAIL のときはそのテストの出力を 4 桁の字下げで続けて示す。最後に `PASS: <n> test(s)`（終了コード 0）か `FAIL: <k> of <n> test(s) failed: <paths>`（終了コード 1）を表示する。`--list` は実行するテストのパスだけを表示する。

- [ ] **Step 1: 失敗するテストを書く**

3 本を次の内容で作り、`chmod +x` する。

`.devcontainer/test-run-tests.bash`:

```bash
#!/bin/bash
# .devcontainer/run-tests.bash の対象と結果の伝え方を検査する。仕様 7.2・9.2 節
# （自分自身も対象に含まれるので、ここでは引数でテストを渡すか --list だけを使い、全体の実行はしない）
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runner="$root/.devcontainer/run-tests.bash"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# 1. 既定の対象は .devcontainer/test-*.bash と tests/scripts/*.bash のすべてで、補助の tests/scripts/lib は含まない
listed="$(bash "$runner" --list)"
expected="$(cd "$root" && printf '%s\n' .devcontainer/test-*.bash tests/scripts/*.bash)"
[ "$listed" = "$expected" ] || fail "unexpected test list:
$listed"
grep -qxF .devcontainer/test-run-tests.bash <<<"$listed" || fail 'the list lacks this test'
grep -qxF tests/scripts/test-check-layout.bash <<<"$listed" || fail 'the list lacks tests/scripts'
if grep -qF tests/scripts/lib/ <<<"$listed"; then fail 'the list includes a helper under tests/scripts/lib'; fi

# 2. 失敗したテストがあれば 1 を返し、そのテストの出力を字下げして示す。成功したテストの出力は出さない
printf '#!/bin/bash\necho quiet-output\n' > "$tmp/pass.bash"
printf '#!/bin/bash\necho broken-detail\nexit 3\n' > "$tmp/fail.bash"
code=0
bash "$runner" "$tmp/pass.bash" "$tmp/fail.bash" > "$tmp/out" 2>&1 || code=$?
[ "$code" -eq 1 ] || fail "expected exit 1, got $code"
grep -qE "^PASS $tmp/pass\.bash \([0-9]+s\)$" "$tmp/out" || fail 'no PASS line'
grep -qE "^FAIL $tmp/fail\.bash \([0-9]+s\)$" "$tmp/out" || fail 'no FAIL line'
grep -qxF '    broken-detail' "$tmp/out" || fail 'the failing output was not shown'
if grep -qF quiet-output "$tmp/out"; then fail 'the passing output was shown'; fi
grep -qxF "FAIL: 1 of 2 test(s) failed: $tmp/fail.bash" "$tmp/out" || fail 'no summary line'

# 3. すべて通れば 0 を返し、件数を示す
bash "$runner" "$tmp/pass.bash" "$tmp/pass.bash" > "$tmp/out" 2>&1 || fail 'a passing run returned non-zero'
[ "$(tail -n 1 "$tmp/out")" = 'PASS: 2 test(s)' ] || fail "unexpected summary: $(tail -n 1 "$tmp/out")"

printf 'PASS: run-tests.bash runs every test and reports failures\n'
```

`tests/scripts/test-ci.bash`:

```bash
#!/bin/bash
# CI の定義（.github/workflows/ci.yml）と gitleaks の設定（.gitleaks.toml）が仕様 9.2 節のとおりであることを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

uv run python - <<'PY'
import re
import tomllib

import yaml

ci = yaml.safe_load(open(".github/workflows/ci.yml", encoding="utf-8"))
# PyYAML は on: を真偽値の True として読む
triggers = ci.get("on", ci.get(True))
assert set(triggers) == {"push", "pull_request"}, triggers
jobs = ci["jobs"]
assert set(jobs) == {"devcontainer-tests", "layout", "skill-tests", "gitleaks"}, sorted(jobs)


def runs(job):
    return [step["run"] for step in jobs[job]["steps"] if "run" in step]


def uses(job):
    return [step["uses"] for step in jobs[job]["steps"] if "uses" in step]


assert "bash .devcontainer/run-tests.bash" in runs("devcontainer-tests"), runs("devcontainer-tests")
assert any(all(p in r for p in ("zsh", "ripgrep", "bubblewrap")) for r in runs("devcontainer-tests")), "zsh, ripgrep and bubblewrap are needed by the tests"
assert any(u.startswith("astral-sh/setup-uv@") for u in uses("devcontainer-tests"))
assert runs("layout") == ["bash scripts/check-layout.sh"], runs("layout")
assert not any("resoloop" in u for u in uses("layout")), "layout runs without resoloop"
assert runs("skill-tests") == ["uv run pytest tests/skills .agents/skills"], runs("skill-tests")
assert any(u.startswith("astral-sh/setup-uv@") for u in uses("skill-tests"))
steps = jobs["gitleaks"]["steps"]
checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout@"))
assert checkout["with"]["fetch-depth"] == 0, checkout
leaks = next(s for s in steps if s.get("uses", "").startswith("gitleaks/gitleaks-action@"))
assert leaks["env"]["GITLEAKS_CONFIG"] == ".gitleaks.toml", leaks
for job in jobs.values():
    assert job["runs-on"] == "ubuntu-latest"
    assert "blender" not in str(job).lower(), "CI does not build worlds with Blender"

config = tomllib.load(open(".gitleaks.toml", "rb"))
assert config["extend"]["useDefault"] is True, config
(allow,) = config["allowlists"]
assert allow["targetRules"] == ["generic-api-key"] and allow["regexTarget"] == "match", allow
(pattern,) = allow["regexes"]
for identifier in ('key":"mat_material_Slum02_rubber_d4d07289"', 'key": "mesh_junk-pile-01__corrugated_1a2b3c4d"'):
    assert re.search(pattern, identifier), identifier
for secret in ('key": "Zx9Qm2Lp8Rt4Vw6Yb1Nc3Kd5Hf7Jg0Ss"', 'api_key": "mat_material_x"'):
    assert not re.search(pattern, secret), secret
PY

printf 'PASS: CI workflow and gitleaks config follow spec 9.2\n'
```

`tests/scripts/test-file-modes.bash`:

```bash
#!/bin/bash
# 実行するスクリプトが git の index 上で実行可能（100755）であることを検査する。仕様 7.2 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# 対象: .devcontainer 配下の *.bash と *.zsh、pi のランチャー 9 本、scripts/*.sh、テスト（tests/scripts/*.bash）
launchers='piccd piccg piga pigl pigo pigod pigou pigs pixg'
checked=0 bad=()
while IFS= read -r -d '' record; do
  meta="${record%%$'\t'*}" path="${record#*$'\t'}"
  case "$path" in
    .devcontainer/*.bash | .devcontainer/*.zsh | scripts/*.sh | tests/scripts/*.bash) ;;
    .devcontainer/*)
      name="${path#.devcontainer/}"
      case " $launchers " in *" $name "*) ;; *) continue ;; esac ;;
    *) continue ;;
  esac
  case "$path" in tests/scripts/lib/*) continue ;; esac   # source して使う補助
  checked=$((checked + 1))
  [ "${meta%% *}" = 100755 ] || bad+=("$path (${meta%% *})")
done < <(git ls-files -s -z -- .devcontainer scripts tests/scripts)
[ ${#bad[@]} -eq 0 ] || fail "not executable in the index: ${bad[*]}"
for name in $launchers; do
  git ls-files --error-unmatch ".devcontainer/$name" >/dev/null 2>&1 || fail "launcher .devcontainer/$name is not tracked"
done
[ "$checked" -gt 30 ] || fail "too few files checked ($checked)"

printf 'PASS: %d scripts are executable in the index\n' "$checked"
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W"
bash .devcontainer/test-run-tests.bash; echo "exit=$?"
bash tests/scripts/test-ci.bash; echo "exit=$?"
bash tests/scripts/test-file-modes.bash
```

Expected: 1 本目は `.devcontainer/run-tests.bash: No such file or directory` で終了コード 127。2 本目は `FileNotFoundError: ... '.github/workflows/ci.yml'` で終了コード 1。3 本目は既存の実行権を固定するテストなので、この時点で PASS する（`PASS: <n> scripts are executable in the index`）。

- [ ] **Step 3: 実行スクリプト・CI・gitleaks の設定を作る**

`.devcontainer/run-tests.bash`（`chmod +x` する）:

```bash
#!/bin/bash
# Dev Container とリポジトリのスクリプトのテストを一括で実行する。仕様 7.2・9.2 節（CI の devcontainer-tests ジョブ）
# 使い方: bash .devcontainer/run-tests.bash [--list | テストのパス...]
#   引数なし: .devcontainer/test-*.bash と tests/scripts/*.bash をすべて実行する
#   --list:   実行するテストを表示するだけ
# 1 本ずつ実行して PASS / FAIL と所要秒数を表示し、失敗したテストは出力を字下げして続けて示す。1 本でも失敗すれば 1
set -uo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root" || exit 1

if [ $# -eq 0 ] || [ "$1" = --list ]; then
  tests=(.devcontainer/test-*.bash tests/scripts/*.bash)
else
  tests=("$@")
fi
if [ "${1:-}" = --list ]; then
  printf '%s\n' "${tests[@]}"
  exit 0
fi

log="$(mktemp)"
trap 'rm -f -- "$log"' EXIT
failed=()
for t in "${tests[@]}"; do
  start=$SECONDS
  if bash "$t" > "$log" 2>&1; then
    printf 'PASS %s (%ds)\n' "$t" $((SECONDS - start))
  else
    printf 'FAIL %s (%ds)\n' "$t" $((SECONDS - start))
    sed 's/^/    /' "$log"
    failed+=("$t")
  fi
done
if [ ${#failed[@]} -gt 0 ]; then
  printf 'FAIL: %d of %d test(s) failed: %s\n' "${#failed[@]}" "${#tests[@]}" "${failed[*]}"
  exit 1
fi
printf 'PASS: %d test(s)\n' "${#tests[@]}"
```

`.github/workflows/ci.yml`:

```yaml
# CI（仕様 9.2 節）。Blender でのワールドのビルドは実行しない。resoloop も入れない（check-layout は skip を表示する）
name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  devcontainer-tests:
    # .devcontainer/test-*.bash と tests/scripts/*.bash（モックの resoloop・dotnet・blender を使う）
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10
      - name: Install the shells and tools the tests use
        run: |
          sudo apt-get update
          sudo apt-get install -y zsh ripgrep bubblewrap
      - run: bash .devcontainer/run-tests.bash

  layout:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: bash scripts/check-layout.sh

  skill-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10
      - run: uv run pytest tests/skills .agents/skills

  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v3
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_CONFIG: .gitleaks.toml
          # PR へのコメントには書き込み権限が要る。結果はジョブの成否とサマリーで見る
          GITLEAKS_ENABLE_COMMENTS: false
```

`.gitleaks.toml`:

```toml
# gitleaks の設定（CI の gitleaks ジョブと、手元で gitleaks を実行するとき）。既定の規則をそのまま使い、
# resoloop のマニフェストが持つ識別子（"key": "mat_material_Slum02_rubber_d4d07289" など）を
# generic-api-key の検出から外すことだけを足す。形式の決まったトークン（ghp_・sk-ant- など）は専用の規則で検出される
[extend]
useDefault = true

[[allowlists]]
description = "resoloop manifest keys are identifiers, not secrets"
targetRules = ["generic-api-key"]
regexTarget = "match"
regexes = ['''^key"\s*:\s*"[A-Za-z][A-Za-z0-9]*(?:[_.:/-]+[A-Za-z0-9]+)+"$''']
```

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
bash .devcontainer/test-run-tests.bash && bash tests/scripts/test-ci.bash && bash tests/scripts/test-file-modes.bash
bash .devcontainer/run-tests.bash | tail -n 1
```

Expected: 3 本とも PASS。最後は `PASS: 22 test(s)`（Task 10 の README のテストを足すと 23 本になる）。gitleaks がある環境なら `gitleaks git --no-banner --config .gitleaks.toml .` が `no leaks found` を返す（controller が Task 11 で scratchpad の gitleaks を使って確かめる）。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う（ここからは `bash .devcontainer/run-tests.bash` を使う）。

```bash
cd "$W"
git add .devcontainer/run-tests.bash .devcontainer/test-run-tests.bash .github/workflows/ci.yml .gitleaks.toml \
  tests/scripts/test-ci.bash tests/scripts/test-file-modes.bash
git commit -m "ci: run the Dev Container and script tests, check-layout, skill tests and gitleaks

.devcontainer/run-tests.bash runs every .devcontainer/test-*.bash and
tests/scripts/*.bash and shows the output of failing tests. The workflow runs
it on push and pull_request together with check-layout (without resoloop), the
skill tests and gitleaks. .gitleaks.toml keeps the default rules and only
excludes resoloop manifest keys, which are identifiers.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 10: `.devcontainer/README.md` と herdr の文書（仕様 7.1・7.2）

README に仕様 7.1 の導入ツール一覧の表を置き、テストで各ファイルと突き合わせる。仕様 7.2 の README の項目（ResoniteLink への到達の前提、秘密情報の置き場、Cursor と dsh の制約、flux-sdk が対象外であること、テストの実行手順）を書き、移行元の Issue 番号とリンク、旧節を外す（D-14、D-15）。herdr の文書から「`.devcontainer` が symlink」の記述を外し、パスを `/workspaces/<repo>` に一般化する。

**Files:**
- Create: `.devcontainer/test-readme.bash`（mode 100755）
- Modify: `.devcontainer/README.md`、`.devcontainer/docs/herdr-session-cwd-restore.md`

**Interfaces:**
- Consumes: Task 3 の `mounts_from_devcontainer` と `mounts_from_initialize`、Task 4 の zshrc.txt の関数と `update()`
- Produces: README の表は `<!-- tool-table:start -->` と `<!-- tool-table:end -->` の間に置く。列は「ツール / 導入方法 / mount / initialize.bash の mkdir / zshrc の関数 / update() の項目」。

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-readme.bash` を次の内容で作り、`chmod +x` する。

```bash
#!/bin/bash
# .devcontainer/README.md の導入ツール一覧（仕様 7.1）が各ファイルと一致し、仕様 7.2 の記述を持つことを検査する。
# あわせて .devcontainer 配下に移行元リポジトリの名残（maatlog、Issue 番号、固定のワークスペースパス）が無いことを確かめる
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readme="$root/.devcontainer/README.md"
zshrc="$root/.devcontainer/zshrc.txt"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# shellcheck source=mounts.bash
source "$root/.devcontainer/mounts.bash"

# column N: 表の N 列目（1 始まり）を行ごとに出力する
table="$(sed -n '/^<!-- tool-table:start -->$/,/^<!-- tool-table:end -->$/p' "$readme" | { grep '^| ' || true; } | tail -n +3)"
[ -n "$table" ] || fail 'README lacks the tool table between the tool-table markers'
column() { awk -F' [|] ' -v n="$1" '{ sub(/^[|] /, ""); sub(/ [|]$/, ""); print $n }' <<<"$table"; }
# ticks: 標準入力の `...` の中身を 1 行ずつ出力する
ticks() { grep -o '`[^`]*`' | tr -d '`' || true; }

# 1. 仕様 7.1 の行がそろっている
for tool in 'Claude Code' Codex pi Cursor Devin dsh gh 'grok / gcloud / glab / bun' 秘密情報; do
  column 1 | grep -qxF "$tool" || fail "tool table lacks the row for $tool"
done

# 2. mount の列は devcontainer.json の mounts、initialize.bash の列は initialize.bash が作るパスと同じ集合
mounted="$(mounts_from_devcontainer "$root/.devcontainer/devcontainer.json" | cut -f1 | sed 's|^|~/|' | LC_ALL=C sort)"
[ "$(column 3 | ticks | LC_ALL=C sort)" = "$mounted" ] || fail "the mount column differs from devcontainer.json:
$(column 3 | ticks | LC_ALL=C sort)"
created="$(mounts_from_initialize "$root/.devcontainer/initialize.bash" | sed 's|^|~/|' | LC_ALL=C sort)"
[ "$(column 4 | ticks | LC_ALL=C sort)" = "$created" ] || fail "the initialize.bash column differs from initialize.bash:
$(column 4 | ticks | LC_ALL=C sort)"

# 3. zshrc の列の関数と alias は zshrc.txt にあり、update() の列の項目は update() が実行する
while IFS= read -r name; do
  grep -qE "^(function ([a-z-]+ )*${name} ?\(\)|alias ${name}=)" "$zshrc" || fail "zshrc.txt lacks $name listed in the tool table"
done < <(column 5 | ticks)
update_body="$(sed -n '/^function update(){$/,/^}$/p' "$zshrc")"
while IFS= read -r item; do
  grep -qF -- "$item" <<<"$update_body" || fail "update() lacks '$item' listed in the tool table"
done < <(column 6 | ticks)

# 4. 仕様 7.2 の記述: ResoniteLink への到達、秘密情報の置き場、Cursor と dsh の制約、flux-sdk、テストの実行
for s in 'networkingMode=mirrored' 'resoloop discover' 'RESONITE_LINK_URL' '~/.config/create-reso-world/env' \
  '## エージェントの読み込みの制約' 'Cursor は' 'dsh は' 'flux-sdk' 'bash .devcontainer/run-tests.bash' \
  'bash scripts/check-layout.sh' 'uv run pytest tests/skills .agents/skills' '.devcontainer/resoloop.lock'; do
  grep -qF -- "$s" "$readme" || fail "README lacks: $s"
done
if grep -nE '^project_doc_fallback_filenames' "$readme"; then fail 'README still tells Codex users to add project_doc_fallback_filenames'; fi

# 5. .devcontainer 配下に移行元の名残を残さない（このテスト自身と、旧変数を無視することを確かめる cleanup のテストは除く）
cd "$root"
self=':!.devcontainer/test-readme.bash'
if git grep -n -i maatlog -- .devcontainer "$self" ':!.devcontainer/test-cleanup-workspace.bash'; then fail '.devcontainer refers to maatlog'; fi
if git grep -nE '#[0-9]{3}\b' -- .devcontainer "$self"; then fail '.devcontainer refers to issue numbers of the migration source'; fi
if git grep -nF '/workspaces/reso-world' -- .devcontainer "$self"; then fail '.devcontainer hard-codes the workspace path'; fi
if git grep -n 'symlink' -- .devcontainer/docs/herdr-session-cwd-restore.md; then fail 'the herdr doc still describes .devcontainer as a symlink'; fi

printf 'PASS: README tool table matches the Dev Container files\n'
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && bash .devcontainer/test-readme.bash
```

Expected: `FAIL: README lacks the tool table between the tool-table markers` で終了コード 1。

- [ ] **Step 3: README と herdr の文書を直す**

````diff
diff --git a/.devcontainer/README.md b/.devcontainer/README.md
index a37fbb1..14c12ed 100644
--- a/.devcontainer/README.md
+++ b/.devcontainer/README.md
@@ -5,14 +5,69 @@ Dev Container 設定とエージェント用ツールのセットアップを置
 
 `postCreateCommand` は `/bin/bash .devcontainer/install_beforehand.bash` である。
 `.devcontainer/` を変更した場合は Dev Containers: Rebuild Container を実行する。
+導入するツールと、その mount・シェル設定の対応は「導入ツール一覧」の表にまとめる。
+`devcontainer.json`、`initialize.bash`、`install_beforehand.bash`、`zshrc.txt` はこの表に従う。
 Herdr の復元手順は `.devcontainer/docs/herdr-session-cwd-restore.md` を参照する。
 
 `cleanup-workspace.bash` はレビュー用の一時ディレクトリを安全条件を確認して掃除する。
 手動で確認するときは `WORKSPACE_CLEANUP_DRY_RUN=1 bash .devcontainer/cleanup-workspace.bash` を使う。
 掃除先は `WORKSPACE_CLEANUP_TMP_ROOT`、定期実行の状態保存先は
-`WORKSPACE_CLEANUP_STATE_DIR` で変更できる。清掃スクリプトは旧
-`MAATLOG_CLEANUP_*` も安全のため代替として受け付けるが、新しい名前が優先される。
-定期実行の状態保存先は新しい名前に移行する。
+`WORKSPACE_CLEANUP_STATE_DIR` で変更できる。
+
+## 導入ツール一覧
+
+各ツールの導入方法、bind mount するホスト側のパス、ホスト側で先に作るパス（`initialize.bash`）、
+`zshrc.txt` の関数と alias、`update()` の項目の対応である。mount と `initialize.bash` の列は
+`.devcontainer/test-readme.bash` がそれぞれのファイルと突き合わせる。
+
+<!-- tool-table:start -->
+| ツール | 導入方法 | mount | initialize.bash の mkdir | zshrc の関数 | update() の項目 |
+| --- | --- | --- | --- | --- | --- |
+| Claude Code | installer（`claude.ai/install.sh`）。プラグインは `.claude/settings.json` の `enabledPlugins` と同じ 5 つ | `~/.claude`、`~/.claude.json` | `~/.claude`、`~/.claude.json`（touch） | `ccd`（alias）、`ccda`、`ccdd`、`ccddg`、`ccdu` | `claude update` |
+| Codex | `npm install -g @openai/codex@latest` | `~/.codex` | `~/.codex` | `cod` | `npm install -g @openai/codex@latest` |
+| pi | `npm install -g` で本体、`pi install` で拡張。ランチャー 9 本を `~/.local/bin` に置く | `~/.pi` | `~/.pi` | — | `pi update`、`pi update --extensions` |
+| Cursor | installer（`cursor.com/install`） | `~/.cursor`、`~/.local/share/cursor-agent` | `~/.cursor`、`~/.local/share/cursor-agent` | `cur`（alias） | `agent update` |
+| Devin | installer（`cli.devin.ai/install.sh`） | `~/.local/share/devin`、`~/.config/devin` | `~/.local/share/devin`、`~/.config/devin` | `dev`（alias） | `devin update`、`devin plugins update superpowers` |
+| dsh | `npm install -g @deepseek-ai/dsh@0.1.5-rc.1`（版を固定） | `~/.dsh` | `~/.dsh` | — | —（版を固定しているので更新しない） |
+| gh | Dev Container Feature（github-cli） | `~/.config/gh` | `~/.config/gh` | — | — |
+| grok / gcloud / glab / bun | 未導入（参照だけ残す） | `~/.grok`、`~/.config/gcloud`、`~/.config/glab-cli` | `~/.grok`、`~/.config/gcloud`、`~/.config/glab-cli` | `genv`（gcloud）、`buni`（bun） | `grok update` |
+| 秘密情報 | — | `~/.config/create-reso-world` | `~/.config/create-reso-world`（mode 700） | env ファイルがあれば読み込む | — |
+<!-- tool-table:end -->
+
+未導入のツールを呼ぶ関数（`cod`、`genv`、`buni`）は、コマンドが無ければ理由を表示して 127 を返す。
+`update()` は無いツールの項目を飛ばし、飛ばした項目を表示する。
+
+## 秘密情報
+
+API トークンなどの秘密情報は、ホストの `~/.config/create-reso-world/env` に置き、リポジトリには置かない。
+このディレクトリは Dev Container に bind mount され（`initialize.bash` がホスト側に mode 700 で作る）、
+`zshrc.txt` がシェルの起動時に `env` を読み込んで、書いた変数をすべて export する。ファイルが無ければ何もしない。
+
+```bash
+# ホスト側で一度だけ作る
+mkdir -p ~/.config/create-reso-world && chmod 700 ~/.config/create-reso-world
+touch ~/.config/create-reso-world/env && chmod 600 ~/.config/create-reso-world/env
+```
+
+書式は `KEY=VALUE` の 1 行 1 変数である（zsh が読むので、空白や記号を含む値は引用符で囲む）。
+対象は `DEEPINFRA_TOKEN`、`COMMANDCODE_API_KEY`、`OPENCODE_API_KEY`、`MAAS_ANTHROPIC_TOKEN`、`CONTEXT7_API_KEY` などで、
+書き換えたら新しいシェルを開く。
+
+## テストの実行
+
+リポジトリのルートで次を実行する。CI（`.github/workflows/ci.yml`）も同じコマンドを実行する。
+
+```bash
+bash .devcontainer/run-tests.bash          # .devcontainer/test-*.bash と tests/scripts/*.bash（CI の devcontainer-tests）
+bash scripts/check-layout.sh               # リポジトリのレイアウト（CI の layout。resoloop が無ければ skills sync の検査を skip）
+uv run pytest tests/skills .agents/skills  # スキルのテスト（CI の skill-tests）
+(cd slum02 && uv run pytest)               # 各プロジェクトのテスト（MyResoniteProject・akichi・slum02 で同じ）
+```
+
+テストは一時ディレクトリの `HOME` と、モックの resoloop・dotnet・Blender を使うので、実環境を変えない。
+1 本だけ実行するときは `bash .devcontainer/run-tests.bash <テストのパス>` のように渡す。
+CI の gitleaks ジョブは `.gitleaks.toml`（既定の規則に、resoloop のマニフェストが持つ識別子の除外を足したもの）で
+秘密情報の混入を検査する。CI では Blender によるワールドのビルドは行わない。
 
 ## Resonite ワールド開発ツール
 
@@ -24,6 +79,12 @@ Blender は画面を開かずに実行する。Resonite 本体と ResoniteLink 
 Windows ホスト側で準備する。接続確認の `resoloop doctor`、
 Blender の GUI、ホスト側のネットワーク設定はこのセットアップの対象外とする。
 
+コンテナの resoloop から ResoniteLink に届くことが前提である。WSL2 の mirrored networking
+（`.wslconfig` の `networkingMode=mirrored`）でホストの localhost を共有するか、
+`resoloop discover` で ResoniteLink の告知を確かめ、`--url ws://<ホスト>:<ポート>` または
+環境変数 `RESONITE_LINK_URL` で接続先を指定する。
+ProtoFlux 用の flux-sdk はこの環境の対象外で、導入しない。
+
 導入を確認するにはコンテナ内で次を実行する。
 
 ```bash
@@ -36,47 +97,18 @@ bash scripts/resoloop-fork.sh status
 ResoLoop の公式要件には Windows 10/11 が記載されている。Linux で
 CLI が動作しない場合は `postCreateCommand` を失敗とし、成功扱いにはしない。
 
-## npm への一本化（#147）と既存環境の移行
-
-リポジトリのタスクおよび Codex CLI の導入・更新は npm に一本化した
-（`npm install -g @openai/codex@latest`）。yarn は使わない。`devcontainer.json`
-の Node feature も `installYarnUsingApt` を既定の `false`（corepack 経由）に戻し、
-apt 経由での yarn 常駐インストールをやめた。`npm prefix -g` の `bin`（nvm feature が
-入れる Node の `bin`）は既定で PATH 上にあるため、Codex CLI 用に PATH を追加設定
-する必要はない。
+## エージェントの読み込みの制約
 
-この変更は `$HOME` を再作成する Rebuild Container で完全に反映される
-(`$HOME` は `devcontainer.json` の `mounts` で明示している一部のディレクトリのみ
-ホスト側と共有し、それ以外は再作成のたびに作り直される)。**Rebuild していない
-既存のコンテナ**では、旧 `install_beforehand.bash` / `zshrc.txt` の内容が
-`~/.zshrc` に焼き込まれたままのため、以下のいずれかで手動移行する。
+プロジェクト（`slum02/` など）を cwd にしてエージェントを起動したとき、次の 2 つはスキルの一部が見えない。
 
-1. 推奨: Dev Containers: Rebuild Container を実行する。
-2. リビルドしない場合は、次を手動で実行する。
-
-   ```bash
-   npm install -g @openai/codex@latest
-   rm -f ~/.yarn/bin/codex   # yarn 経由の古い codex シンボリックリンクを削除する
-   ```
-
-   合わせて `~/.zshrc` 内の yarn 関連 PATH 設定と `update()` 内の
-   `yarn global add @openai/codex@latest` を、最新の `.devcontainer/zshrc.txt`
-   の内容に置き換える（またはシェルを再作成する）。
-
-## Codex で `CLAUDE.md` を指示ファイルとして読む
-
-Codex は標準では `CLAUDE.md` を自動で読まない。
-`~/.codex/config.toml` の最初の `[projects...]` などのテーブルより前に、次のトップレベル設定を追加する。
-既存の設定は残し、同じキーがある場合はその配列に `CLAUDE.md` を加える。
-
-```toml
-project_doc_fallback_filenames = ["CLAUDE.md"]
-```
+- Cursor は workspace 配下の `.agents/skills` しか読まないため、ルートの共有スキルが見えない。
+  プロジェクトの resonite-* スキルは見える
+- dsh は git のルートの `.agents/skills` しか読まないため、プロジェクトの resonite-* スキルが見えない。
+  ルートの共有スキルは見える
 
-保存後に Codex を再起動し、新しいセッションで「読み込んだ指示ファイルを列挙して」と尋ね、リポジトリ直下の `CLAUDE.md` が含まれることを確認する。
-同じディレクトリに `AGENTS.override.md` または `AGENTS.md` がある場合はそちらが優先される。
-この設定は Dev Container に bind mount された `~/.codex` に保存される。
-詳しくは [Codex の指示ファイルの説明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)を参照する。
+Codex はルートとプロジェクトの `AGENTS.md` を直接読むため、`~/.codex/config.toml` で
+`CLAUDE.md` を指示ファイルとして読ませる設定（`project_doc_fallback_filenames`）は不要である。
+既に設定してあっても害は無い。
 
 ## Herdr サイドバーの設定移行
 
@@ -345,7 +377,7 @@ Grok 4.7 の thinking level は `low` / `medium` / `high` / `xhigh` で、
 ### pi-distill の分離（Main / Distillation）
 
 リポジトリ既定では Main は起動時に選んだモデルを使い、Distillation だけを
-`deepinfra-distill/openai/gpt-oss-20b` へ送る（#247）。`zshrc.txt` で
+`deepinfra-distill/openai/gpt-oss-20b` へ送る。`zshrc.txt` で
 `PI_DISTILL_MODEL` と `PI_DISTILL_ERROR_RETRY_COUNT=0` を設定しており、認証エラーや
 provider エラーなどの非タイムアウト失敗は再試行しない。タイムアウト再試行
 （`PI_DISTILL_TIMEOUT_RETRY_COUNT`）は変更していない。
@@ -424,7 +456,8 @@ commandcode の 2 つのランチャを `setup_pi_commandcode_goat.zsh` が同
 
 ### API トークン
 
-`OPENCODE_API_KEY`、`DEEPINFRA_TOKEN`、`COMMANDCODE_API_KEY` は永続化せず、
+`OPENCODE_API_KEY`、`DEEPINFRA_TOKEN`、`COMMANDCODE_API_KEY` は、「秘密情報」の節の
+`~/.config/create-reso-world/env` に書けばシェルの起動時に export される。書かない場合は、
 必要なときに手動で export する。
 
 - `OPENCODE_API_KEY` は `pigo`・`pigod`・`pigou` の実行には不要である。bind mount した
@@ -511,7 +544,8 @@ pi update npm:@teelicht/pi-superagents
 その場合は `pi install npm:@teelicht/pi-superagents@1.14.3` で確認済み基準版へ
 指定を変更できる。既に v1.14.3 以降なら下げる必要はない。更新後に同じ版確認を行う。
 
-次に、#408 の撤去変更を含むリポジトリのセットアップへ更新してから、下の任意整理に進む。
+次に、旧エントリを追加していたセットアップを撤去した、現在のリポジトリのセットアップへ更新してから、
+下の任意整理に進む。
 新しい `.devcontainer/setup_pi_superagents.zsh` は `~/.pi/agent/settings.json` を
 作成・変更しない。旧セットアップを残したままエントリだけ削除すると、再実行で追加される。
 
@@ -525,7 +559,7 @@ v1.14.3 の隔離検証では、自動探索と同じ絶対パスに解決され
 
 ##### 検証範囲
 
-[移行元リポジトリの隔離検証 #409](https://github.com/usaturn/maatlog-poc/issues/409#issuecomment-5773449902)では、
+移行元リポジトリで行った隔離検証では、
 pi-superagents 1.14.3 / Pi loader 0.85.1 / Superpowers 6.4.1 について、
 旧エントリあり・なしと `includeProject` true・false の4条件で、
 `using-superpowers`、`brainstorming`、`writing-plans`、
@@ -539,7 +573,7 @@ bash .devcontainer/test-pi-superagents.bash
 bash .devcontainer/test-pi-openai-codex.bash
 ```
 
-## DeepSeek Harness（dsh）（#282）
+## DeepSeek Harness（dsh）
 
 `install_beforehand.bash` は [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)
 （`dsh`）を `@deepseek-ai/dsh@0.1.5-rc.1` に固定して導入し、直後の `dsh --version` が
@@ -599,6 +633,7 @@ patch 層で行う。`install_beforehand.bash` は `dsh --profile web --dump-con
 API key はリポジトリにも `~/.dsh/settings.yaml` にも保存しない。設定は
 環境変数名（`OPENCODE_API_KEY` / `COMMANDCODE_API_KEY`）だけを参照する。
 `dsh web` を使うシェルで export しておく（`pigo` / `piccd` と同じ値を使う）。
+「秘密情報」の節の `~/.config/create-reso-world/env` に書けば、シェルの起動時に export される。
 
 Dev Container を使わないローカル環境では、`pnpm` を用意したうえで次の順に
 手動で導入する。既に `~/.dsh/` 側にファイルがある場合はコピーしない。
diff --git a/.devcontainer/docs/herdr-session-cwd-restore.md b/.devcontainer/docs/herdr-session-cwd-restore.md
index d25202f..bf8eb95 100644
--- a/.devcontainer/docs/herdr-session-cwd-restore.md
+++ b/.devcontainer/docs/herdr-session-cwd-restore.md
@@ -2,7 +2,7 @@
 
 ## 背景
 
-Dev Container を Reopen したあと、ターミナルの作業ディレクトリが `/workspaces/reso-world`
+Dev Container を Reopen したあと、ターミナルの作業ディレクトリが `/workspaces/<repo>`
 ではなく `/home/vscode` になる。`.devcontainer/zshrc.txt` の `herdrstart` は
 `cd -- "$workspace_dir"` を実行しているにもかかわらず、その結果がペインに反映されない。
 
@@ -14,7 +14,7 @@ herdr はセッション復元時、`~/.config/herdr/session.json` に保存済
 サーバログ（`~/.config/herdr/herdr-server.log`）の再現例（cwd はこの環境のパスに置換）:
 
 ```
-herdr::server::headless: restored session already has workspaces; ignoring startup cwd cwd=/workspaces/reso-world
+herdr::server::headless: restored session already has workspaces; ignoring startup cwd cwd=/workspaces/<repo>
 ```
 
 `herdrstart` の `cd` が効くのは、herdr サーバが**新規**セッションを作る初回だけである
@@ -45,8 +45,8 @@ startup workspace が `/home/vscode` となり `session.json` を汚染する。
 
 | 保存されていた cwd | `new_cwd` | 復元後のペイン cwd |
 | --- | --- | --- |
-| `/home/vscode` | `/workspaces/reso-world` | `/home/vscode` |
-| `/workspaces/reso-world/.worktrees/example-worktree` | `/workspaces/reso-world` | `/workspaces/reso-world/.worktrees/example-worktree` |
+| `/home/vscode` | `/workspaces/<repo>` | `/home/vscode` |
+| `/workspaces/<repo>/.worktrees/example-worktree` | `/workspaces/<repo>` | `/workspaces/<repo>/.worktrees/example-worktree` |
 
 `new_cwd` が効くのは復元ではない新規ペイン・タブ・ワークスペース作成時のみで、目的を
 達成しない。
@@ -84,14 +84,14 @@ startup workspace が `/home/vscode` となり `session.json` を汚染する。
 各 workspace の `identity_cwd` と各 pane の `cwd` を検査する。
 
 - **保持**: `$HERDR_WORKSPACE_ROOT`（既定 `/workspaces`）配下に実在するディレクトリ。
-  `/workspaces/reso-world/.worktrees/...` はここで保持される
+  `/workspaces/<repo>/.worktrees/...` はここで保持される
 - **是正**: それ以外（`/home/vscode`、削除済み worktree など）は引数で受け取った
   ワークスペースディレクトリへ書き換える
 
 配下判定は `os.path.realpath()` で両者を解決したうえで `os.path.commonpath()` を用いる。
 文字列の前方一致では `/workspaces-old` のような兄弟ディレクトリを誤って配下と判定するため。
-`realpath` を挟むのは、ワークスペース直下がシンボリックリンクである構成
-（本リポジトリの `.devcontainer` など）でも安定して判定するため。
+`realpath` を挟むのは、ワークスペースやその配下にシンボリックリンクを含む構成でも
+安定して判定するため。
 
 複数の workspace が是正対象に該当する場合、修復先を既に `identity_cwd` に持つ
 エントリが存在するときは 2 件目以降を書き換えない（pane を含むエントリ全体を
@@ -158,7 +158,7 @@ status が厳密に `running: false` と確認できた場合だけ修復する
 分離セッション（`herdr --session <name>` と `HERDR_CONFIG_PATH`）を使えば、稼働中の
 セッションを壊さずに検証できる。
 
-1. `session.json` に `/home/vscode` を仕込み、復元ペインが `/workspaces/reso-world` に
+1. `session.json` に `/home/vscode` を仕込み、復元ペインが `/workspaces/<repo>` に
    なること
 2. `session.json` に worktree パスを仕込み、**保持される**こと（退行防止）
 3. サーバ稼働中は `session.json` が書き換わらないこと
````

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
bash .devcontainer/test-readme.bash
bash .devcontainer/run-tests.bash | tail -n 1
```

Expected: PASS。最後は `PASS: 23 test(s)`。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .devcontainer/test-readme.bash .devcontainer/README.md .devcontainer/docs/herdr-session-cwd-restore.md
git commit -m "docs(devcontainer): add the tool table and the setup notes of spec 7

The README lists every tool with its installer, mounts, host directories,
shell helpers and update() items, and a test compares the table with the
Dev Container files. It also documents the ResoniteLink prerequisite, the
secrets file, the Cursor and dsh limits, and how to run the tests. Issue
numbers and links of the migration source are removed.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 11: 一括検証・push・最終レビュー（controller）

- [ ] 1. 全体の検証を行う（すべて期待どおりであること）。

```bash
cd "$W"
git status --short | wc -l                                             # 0
bash .devcontainer/run-tests.bash | tail -n 1                          # PASS: 23 test(s)
bash scripts/check-layout.sh | tail -n 3                               # ok: resoloop lock (...) / ok: mounts match .devcontainer/initialize.bash / PASS: check-layout
uv run pytest -q 2>&1 | tail -n 1                                      # 34 failed, 192 passed, 1 skipped（フェーズ 5 の既知分）
for P in MyResoniteProject akichi slum02; do (cd "$P" && uv run pytest -q 2>&1 | tail -n 1); done   # 52 / 66 / 215 passed
bash .devcontainer/verify-resonite-tooling.bash; echo $?               # 0
bash scripts/resoloop-fork.sh status                                   # installed / checkout とも matches the lock
git ls-files -i -c --exclude-standard                                  # pipeline.json の 1 行だけ
git -C "$M" status --short | grep -c '^?? private/'                    # 0
```

- [ ] 2. gitleaks を scratchpad に置いた実行ファイルで確かめる（`gitleaks git --no-banner --config .gitleaks.toml "$W"` と `gitleaks dir ...` が `no leaks found`）。
- [ ] 3. CI 相当の PATH（`path_without` で resoloop・dotnet・blender・claude・codex・pi・devin・agent・herdr・starship・bun・gcloud・grok・glab・gh・fzf・pnpm を外したもの）で `bash .devcontainer/run-tests.bash` がすべて PASS する。
- [ ] 4. root 所有の複製（`sudo -n` が使える場合だけ）で `tests/scripts/test-gitignore.bash` と `test-check-layout.bash` が PASS する（P-4 の確認）。使えなければ省略し、台帳に記録する。
- [ ] 5. fast-forward を確かめてから `git push origin chore/repo-redesign` を実行する。push した直後の GitHub Actions の実行を `gh run list --branch chore/repo-redesign` で確かめる。skill-tests だけが既知の失敗（D-12）で、ほかの 3 ジョブが成功することを期待する。結果は台帳に記録する。gh が使えないときは記録だけにする。
- [ ] 6. 最上位モデルのレビュアーに `MERGE_BASE..HEAD`（`MERGE_BASE` は `eca7a5e`）のレビューを依頼し、指摘は修正ラウンドで直す。完了後、台帳の最後に `PHASE 4 COMPLETE.` を書く。フェーズ 5 の計画に進む（D-9）。

---

## 持ち越し（フェーズ 5〜6）

前回の引き継ぎ書と本計画で見つかった保留事項。本計画では着手しない。フェーズ 4 の項目（P-4、N-1、N-6、N-8、N-11、N-19〜N-22）は本計画の Task 1〜10 で扱う。

| ID | フェーズ | 内容 |
| --- | --- | --- |
| N-2 | 5 | 統合したスキルに残る maatlog・`public/`・`verify.sh`・`docs_draft/superpowers/` の記述の書き直し（仕様 8.2）。repository-ownership の削除（スキル、テスト、`.cursor/rules/repository-ownership.mdc`、`.claude/skills/repository-ownership` の symlink）。pi-model-name の 27 件の失敗 |
| N-13 | 5 | `AGENTS.md` の冒頭に「本文のパスはリポジトリルート基準」を 1 文足す |
| N-14 | 5 | スキル書き直し（N-2）で個別に直す項目: pr-review の手順 5 の追跡指示、「短縮・一般化しない」、手順 1 の重複表現、contract テストの強化（`--model-name` の `create` 行、委譲制限、allowed-tools）。agent-handoff の概要の文言と evals の q2。repo-cleanup の gitignore ディレクトリの削除規則と allowed-tools。simplify-in-subagent の Examples |
| N-23 | 5 | new-world.sh: リンク切れの symlink の `AGENTS.md` が「run resoloop init first」（exit 3）の案内になる。既存プロジェクトで init を勧めない文言にする |
| N-26 | 5 | CI の skill-tests ジョブは、フェーズ 5 で既知の 34 件の失敗を直すまで失敗する（D-12）。フェーズ 5 の完了条件で成功を確かめる |
| N-3 | 6 | ルート README に書くこと: Codex の trust、cursor-agent の MCP 承認、Devin の単一表示、Cursor と dsh のスキル可視性、pi-superagents の組み込み定義は追跡しない（D-1）。`.devcontainer/README.md` の該当節（エージェントの読み込みの制約、秘密情報、テストの実行）へのリンクで済むものは重複させない |
| N-4 | 6 | マージ直前に統合手順の衝突一覧を再実行し、件数を最新にする |
| N-12 | 6 | integration.md: sp-implementer.md の比較先、項目 2 の 3 ブロックは同じシェルで、項目 3・5 の根拠への参照 |
| N-17 | 6 | 仕様 9.3 の実機確認に、Devin で simplify-in-subagent を呼んだときにサブエージェントが edit / exec を持つかを含める |
| N-18 | 6 | 仕様 9.3 の実機確認に、Rebuild の postCreate で fork のビルドと導入が通ること（SDK 10.0.201、build / pack の引数、`--version` の一致）を含める。GitHub への `sync` の push 認証も未確認 |
| N-24 | 6 | 文書の整合: 仕様 6.4 と運用文書の修正の流れの順序に注記、運用文書の環境変数の説明を揃える、仕様 9.1 の `*/SKILL.md` を D-7 の定義に合わせる（P-7 と一緒に）。仕様 7.2 の `${containerEnv:HOME}` を D-10 に合わせて注記する |
| N-25 | 6 | 仕様 9.3 の実機確認に、Rebuild 後の `remoteEnv.PATH`（`/home/vscode/.local/bin`・`/home/vscode/bin`）、`~/.config/create-reso-world` の mount と `env` の読み込み、`initialize.bash` がホストに mode 700 で作ることを含める |
| N-27 | 6 | PR の前に、GitHub Actions の実行結果（`actions/checkout@v7`、`setup-uv@v10`、`gitleaks-action@v3` の組み合わせ）を確かめる。Task 11 で確かめられなかった場合は必ず行う |
| P-1、P-2、P-3、P-7、M-5 | 6 | integration.md と仕様 10.1 の退避手順、`.git/info/exclude` の `/private/` の削除、フェーズ 0・1 計画書の注記、仕様 4.4 の表記、main の再 ff は `git fetch . feat/slum02-slum:main` |

据え置き（PH3-S1。直すのは必要になったときだけ）は前回の引き継ぎ書のとおり。
