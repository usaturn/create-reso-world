# Issue #20 pi ランチャーとサブエージェントの tier の移植 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全 pi ランチャーを `--tui-mode regular` で起動し、`pigs`・`pixg` の tier・認証の確認・`OPENCODE_GO_API_KEY` の互換を移植元（maatlog-poc `1f2aadb`）に揃え、README とテストを合わせる。

**Architecture:** `--tui-mode regular` は 9 本のランチャーが共通で使う `pi_superagents_exec`（`.devcontainer/pi-superagents-exec.zsh`）に 1 か所だけ足す（Task 1）。`pigs`・`pixg` は tier の JSON とランチャー本体を直す（Task 2）。README の 3 節を直して TUI モードの節を新設し、ライブ確認の Pi の最小版を 0.99.1 にする（Task 3）。各 Task は、先にテストを変えて失敗を確かめ、次に実装を当てて通す。Task 4 で全体を検証し、PR を作る。

**Tech Stack:** zsh（ランチャーとヘルパ）、bash（テストは `set -euo pipefail`）、bubblewrap（fake の `bwrap` で置き換えて検査）、git（`git apply --index --3way`）、uv / pytest（スキルのテスト）、GitHub CLI（PR）

**Spec:** `docs/superpowers/specs/2026-10-04-issue-20-pi-launchers-design.md`（判断事項 D-1〜D-12、4 章の設計、7 章の受け入れ条件、9 章の比較表の行）。親 Issue は #17、この計画の Issue は #20。

## 実行方法

推奨は **Native**（`superpowers:executing-plans`）。3 つの Task は同じテストファイル（`test-pi-superagents.bash`・`test-pi-openai-codex.bash`）に順に積み重なり、各 Task のパッチは計画の作成時に使い捨ての複製で RED→GREEN を確かめてあるため、Task ごとにレビュー担当を立てる利点が小さい。利用者は「推奨案で進めて、途中で止めずに PR まで作成して」と指示しているので、この計画を作ったセッションが Native で続けて実行する（エージェントの判断）。

## Global Constraints

- 作業場所は worktree `/workspaces/reso-world/.worktrees/issue-20-pi-launchers`、ブランチは `feat/issue-20-pi-launchers`。各ステップは特記が無ければこの worktree のルートで実行する。worktree が無いホストでは、最新の `origin/main` から `git worktree add -b feat/issue-20-pi-launchers .worktrees/issue-20-pi-launchers origin/main` で作り、#20 のコメントから Spec とこの計画を復元してコミットしてから始める
- 着手前に `git fetch origin` を実行する。`origin/main` が `b2ea728` から進んでいれば `git merge --no-edit origin/main` で取り込む。rebase と force push はしない
- 編集してよいのは Spec 2 章で「変更する」としたファイルだけ。特に次は編集しない: `.devcontainer/install_beforehand.bash`・`pi-models.json`・`setup_pi.zsh`・`cleanup_pi_mcp.py`・`zshrc.txt`、3 本の setup スクリプト、`pigs`・`pixg` 以外のランチャー、`.agents/skills/**`・`.claude/skills/**`・`.pi/APPEND_SYSTEM.md`、ワールドのプロジェクト、`docs/superpowers/` の既存の文書、ホストの `~/.pi`
- パッチは `git apply --index --3way` で当てる。この計画のファイルからパッチを取り出すときは、ヒアドキュメントの区切り（`ISSUE20_T1_TEST` など）の間をそのまま使う。当たらない場合は、パッチを推測で直さず、Spec 4 章の記述どおりに手で編集し、その旨を作業報告に書く
- setup の案内のパスは `.devcontainer/` のまま（`scripts/` にしない）。`pigou` は削除しない
- テストの `grep -q` は here-string で受ける（PR #15 の SIGPIPE 対策）。`printf ... | grep -q` に戻さない
- コミットメッセージの末尾に、コミットするエージェント自身のモデル名の trailer を付ける（例: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`）
- `git add -A`・`git add .` を使わない。パッチは `--index` で stage される
- Python を使う場合は `uv run` を使い、`python3` を直接使わない（テストの中の既存の `python3` は `.devcontainer/` の例外として残す）
- 実認証とホストの `~/.pi` を使わない。テストは一時 HOME と fake の `bwrap` で行う。`PI_CODEX_LIVE_CHECK`・`PI_XAI_LIVE_CHECK` は設定しない
- `main` では、slum03 の resoloop スキルが未同期のため `bash scripts/check-layout.sh` と `tests/scripts/test-check-layout.bash` が失敗する。範囲外なので直さない。この 2 件以外が通ることを確かめる
- PR は `main` 向けに 1 本、本文に `Closes #20`。force push・`main` への直接の push・他のブランチの削除はしない
- 作業報告には、着手から完了までの所要時間と、Task ごとの内訳を書く（`AGENTS.md` の SDD 実行運用）

## Review Focus

- 利用者が追加引数に `--tui-mode fullscreen` を渡す: ランチャーの `--tui-mode regular` より後ろに並び、Pi の後勝ちの解析で fullscreen になる。Task 1 の `test_launchers_select_regular_and_forward_user_arguments` が「`--tui-mode regular` が先頭、利用者の引数が最後」の並びを全ランチャーで固定する
- セッション名やメッセージに空白を含む引数: dry-run の表示と実際の exec で argv が崩れない。Task 1 の `test_actual_and_dry_run_argv_match` と、Task 1 の全ランチャーの検査（`'session with spaces.jsonl'`・`'message with spaces'`）で固定する
- `OPENCODE_API_KEY` が空文字で、旧名の `OPENCODE_GO_API_KEY` だけに値がある: 子 Pi は旧名の値を受け取る。Task 2 の `test_opencode_key_reaches_child_process` の `':dummy-legacy:dummy-legacy'` の行で固定する
- rebuild しない既存環境で `setup_pi_superagents.zsh --if-absent` を再実行する: 利用者が編集した tier の設定を保持し、ヘルパだけを最新（`--tui-mode regular` 入り）にする。Task 1 の `test_setup_if_absent_preserves_user_edits` で固定する
- #18 のマージで `install_beforehand.bash` の手順の並びが変わる: install の検査の切り出しが壊れない。Task 1 の `test_install_places_all_launchers_with_regular_mode` は「Placing」と「Writing」以外の次の `step` で切るので、dsh の手順の有無に依存しない

## ファイルの対応

| ファイル | 変更 | Task |
| --- | --- | --- |
| `.devcontainer/pi-superagents-exec.zsh` | `pi --tui-mode regular "$@"` | 1 |
| `.devcontainer/pi-superagents/pigs.json` | cheap を `opencode-go/deepseek-v4.1-flash`（`max`）に | 2 |
| `.devcontainer/pi-superagents/pixg.json` | cheap・balanced を `opencode-go/deepseek-v4.1-flash`（`max`）に | 2 |
| `.devcontainer/pigs` | `OPENCODE_GO_API_KEY` の互換とコメント | 2 |
| `.devcontainer/pixg` | Codex OAuth の確認を削除、互換とコメント | 2 |
| `.devcontainer/README.md` | GPT-6・Grok 4.7・tier の節を更新し、TUI モードの節を新設 | 3 |
| `.devcontainer/test-pi-superagents.bash` | `--tui-mode`・argv の一致・全ランチャーの引数・ヘルパの更新（1）、tier・`pixg` の認証・互換の引き継ぎ（2）、README の検査（3） | 1・2・3 |
| `.devcontainer/test-pi-openai-codex.bash` | 期待する引数・全ランチャーの install の検査（1）、`pigs` の cheap の行の削除（2）、Pi 0.99.1（3） | 1・2・3 |

---

### Task 1: 全ランチャーを `--tui-mode regular` で起動する

**Files:**
- Modify: `.devcontainer/pi-superagents-exec.zsh`（`pi_superagents_exec` の `args_` 配列）
- Test: `.devcontainer/test-pi-superagents.bash`、`.devcontainer/test-pi-openai-codex.bash`

**Interfaces:**
- Consumes: `main` の `pi_superagents_exec <launcher> <pi の引数...>`（dry-run は argv を 1 行 1 要素で表示）
- Produces: dry-run と実際の exec の argv が `bwrap --dev-bind / / --die-with-parent --bind <launcher_dir> <shared_dir> -- pi --tui-mode regular <ランチャーの引数> <利用者の引数>` になる。テストの補助関数 `pi_args_of`（既存）と、新しい検査 `test_actual_and_dry_run_argv_match`・`test_launchers_select_regular_and_forward_user_arguments`・`test_install_places_all_launchers_with_regular_mode`。Task 2 は `test_launchers_select_regular_and_forward_user_arguments` を前提にする

- [ ] **Step 1: テストを変える**

`test-pi-superagents.bash` に、ヘルパの pi の引数の完全一致、実際の argv と dry-run の argv の一致、9 本すべての引数の並び、setup がヘルパを最新にすること（`--if-absent` でも）を足す。`test-pi-openai-codex.bash` の期待する引数に `--tui-mode regular` を足し、install の検査を 9 本とヘルパに広げる。

````bash
git apply --index --3way <<'ISSUE20_T1_TEST'
diff --git a/.devcontainer/test-pi-openai-codex.bash b/.devcontainer/test-pi-openai-codex.bash
index 0aad01f..6237823 100755
--- a/.devcontainer/test-pi-openai-codex.bash
+++ b/.devcontainer/test-pi-openai-codex.bash
@@ -66,7 +66,7 @@ test_launchers_select_models_and_forward_arguments() {
         output="$(env HOME="$home" PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
             zsh "${REPO_ROOT}/.devcontainer/${launcher}" --resume)"
         args="$(printf '%s\n' "$output" | awk 'seen { print } $0 == "pi" { seen = 1 }')"
-        expected="$(printf '%s\n' --provider openai-codex --model "$model" --thinking xhigh --resume)"
+        expected="$(printf '%s\n' --tui-mode regular --provider openai-codex --model "$model" --thinking xhigh --resume)"
         assert_eq "$args" "$expected" "${launcher} Pi arguments"
         # grep -q は一致した時点で終了するので、printf でパイプすると残りの行を書く側が SIGPIPE で落ちる
         grep -Fxq "${home}/.pi/agent/extensions/subagent.d/${launcher}" <<<"$output" \
@@ -89,7 +89,7 @@ test_launchers_accept_tilde_agent_dir() {
             pigs) model=gpt-6.1-sol ;;
             pigl) model=gpt-6-luna ;;
         esac
-        expected="$(printf '%s\n' --provider openai-codex --model "$model" --thinking xhigh --resume)"
+        expected="$(printf '%s\n' --tui-mode regular --provider openai-codex --model "$model" --thinking xhigh --resume)"
         for agent_dir in "${home}/.pi/agent" '~/.pi/agent' '~'; do
             output="$(env HOME="$home" PI_CODING_AGENT_DIR="$agent_dir" \
                 PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
@@ -122,19 +122,36 @@ test_missing_oauth_guides_login_without_requesting_api_key() {
     done
 }
 
-test_install_places_all_three_launchers() {
-    local home="${TEST_ROOT}/install" launcher
-    mkdir -p "$home"
+test_install_places_all_launchers_with_regular_mode() {
+    local home="${TEST_ROOT}/install" launcher output
+    local -a args
+    mkdir -p "${home}/.pi/agent"
+    printf '%s\n' '{"openai-codex":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999},"xai":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999}}' \
+        > "${home}/.pi/agent/auth.json"
+    cp "${REPO_ROOT}/.devcontainer/pi-models.json" "${home}/.pi/agent/models.json"
+    # ランチャーの配置と、ヘルパを置く pi-superagents の手順だけを切り出す。
+    # 終わりは「この 2 つ以外の次の step」にし、後続の手順の並びに依存しない。
     {
         printf '%s\n' 'step() { :; }' 'fail() { printf "%s\n" "$1" >&2; exit 1; }'
-        awk '/^step "Placing the launchers / { copy = 1 } /^step "Writing the pi-superagents / { copy = 0 } copy' \
-            "${REPO_ROOT}/.devcontainer/install_beforehand.bash"
+        awk '/^step "Placing the launchers / { copy = 1 }
+            /^step "/ && !/^step "(Placing the launchers |Writing the pi-superagents )/ { copy = 0 }
+            copy' "${REPO_ROOT}/.devcontainer/install_beforehand.bash"
     } | env HOME="$home" bash -e
+    cmp -s "${REPO_ROOT}/.devcontainer/pi-superagents-exec.zsh" "${home}/.local/bin/pi-superagents-exec.zsh" \
+        || fail "install must place the current helper"
 
-    for launcher in piga pigs pigl; do
+    for launcher in pigo pigod pigou piccg piccd piga pigs pigl pixg; do
         [ -x "${home}/.local/bin/${launcher}" ] || fail "install did not place executable ${launcher}"
         cmp -s "${REPO_ROOT}/.devcontainer/${launcher}" "${home}/.local/bin/${launcher}" \
             || fail "installed ${launcher} differs from the source"
+        output="$(env HOME="$home" PI_CODING_AGENT_DIR="${home}/.pi/agent" \
+            COMMANDCODE_API_KEY=dummy-for-dry-run OPENCODE_API_KEY=dummy-for-dry-run \
+            PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
+            zsh "${home}/.local/bin/${launcher}" --resume)"
+        mapfile -t args < <(awk 'seen { print } $0 == "pi" { seen = 1 }' <<<"$output")
+        assert_eq "${args[0]:-}" --tui-mode "installed ${launcher} tui option"
+        assert_eq "${args[1]:-}" regular "installed ${launcher} tui mode"
+        assert_eq "${args[${#args[@]}-1]}" --resume "installed ${launcher} user argument"
     done
 }
 
@@ -158,6 +175,6 @@ test_setup_places_independent_gpt6_tiers
 test_launchers_select_models_and_forward_arguments
 test_launchers_accept_tilde_agent_dir
 test_missing_oauth_guides_login_without_requesting_api_key
-test_install_places_all_three_launchers
+test_install_places_all_launchers_with_regular_mode
 test_live_openai_codex_models
 printf 'OK test-pi-openai-codex\n'
diff --git a/.devcontainer/test-pi-superagents.bash b/.devcontainer/test-pi-superagents.bash
index 79ac0e8..a395c74 100755
--- a/.devcontainer/test-pi-superagents.bash
+++ b/.devcontainer/test-pi-superagents.bash
@@ -86,6 +86,9 @@ test_dry_run_emits_bwrap_command() {
     assert_contains "$out" "pi" "pi command"
     assert_contains "$out" "--provider" "passthrough of pi args"
     assert_contains "$out" "muse-spark-1.3-contributor" "passthrough of pi args"
+    assert_eq "$(pi_args_of "$out")" \
+        "$(printf '%s\n' --tui-mode regular --provider opencode-go --model muse-spark-1.3-contributor)" \
+        "helper must select regular before forwarding pi args"
 }
 
 test_bind_target_ignores_pi_coding_agent_dir() {
@@ -184,6 +187,21 @@ test_dry_run_zero_execs_bwrap() {
     assert_contains "$log" "--provider" "=0 must pass user args to bwrap"
 }
 
+test_actual_and_dry_run_argv_match() {
+    # dry-run の表示と実際の exec が同じ argv 配列を使うことを、空白を含む引数で確かめる。
+    local home out expected
+    local -a command_args
+    home="$(make_home argv-match with-config)"
+    make_bwrap_shim
+    rm -f "$FAKE_BWRAP_LOG"
+    out="$(run_helper "$home" argv-match --session 'session with spaces.jsonl' -- 'message with spaces')"
+    mapfile -t command_args <<< "$out"
+    expected="$(printf 'bwrap invoked with %s args\n' "$((${#command_args[@]} - 1))"; \
+        printf '%s\n' "${command_args[@]:1}")"
+    run_helper_dry_run "$home" argv-match 0 --session 'session with spaces.jsonl' -- 'message with spaces'
+    assert_eq "$(<"$FAKE_BWRAP_LOG")" "$expected" "actual and dry-run must use identical argv"
+}
+
 CONFIG_DIR="${REPO_ROOT}/.devcontainer/pi-superagents"
 PI_MODELS="${REPO_ROOT}/.devcontainer/pi-models.json"
 
@@ -378,11 +396,37 @@ test_launchers_preserve_parent_model_selection() {
     assert_contains "$args" "xhigh" "pixg thinking"
 }
 
-test_launchers_forward_user_arguments() {
-    local home args
-    home="$(make_home pigo with-config)"
-    args="$(pi_args_of "$(run_launcher "$home" pigo --resume)")"
-    assert_contains "$args" "--resume" "user argument must reach pi"
+test_launchers_select_regular_and_forward_user_arguments() {
+    # 全ランチャーで、pi の引数が --tui-mode regular、ランチャーの指定、
+    # 利用者の引数の順に、空白を含む引数も崩さずに並ぶ。
+    local home launcher provider model thinking models args expected row
+    local -a rows=(
+        'pigo:opencode-go:muse-spark-1.3-contributor:max'
+        'pigod:opencode-go:deepseek-v4.1-flash:max'
+        'pigou:opencode-go:union-alpha:max'
+        'piccg:commandcode:meta/muse-spark-1.3:max:meta/muse-spark-1.3,meta/muse-spark-1.3-contributor'
+        'piccd:commandcode:deepseek/deepseek-v4.1-flash:max:deepseek/deepseek-v4.1-flash'
+        'piga:openai-codex:gpt-6-astra:xhigh'
+        'pigs:openai-codex:gpt-6.1-sol:xhigh'
+        'pigl:openai-codex:gpt-6-luna:xhigh'
+        'pixg:xai:grok-4.7:xhigh'
+    )
+    for row in "${rows[@]}"; do
+        IFS=: read -r launcher provider model thinking models <<< "$row"
+        home="$(make_home "$launcher" with-config)"
+        mkdir -p "${home}/.pi/agent"
+        printf '%s\n' '{"openai-codex":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999},"xai":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999}}' \
+            > "${home}/.pi/agent/auth.json"
+        args="$(pi_args_of "$(run_launcher "$home" "$launcher" --resume --session 'session with spaces.jsonl' -- 'message with spaces')")"
+        expected="$(
+            printf '%s\n' --tui-mode regular --provider "$provider" --model "$model"
+            if [ -n "$models" ]; then
+                printf '%s\n' --models "$models"
+            fi
+            printf '%s\n' --thinking "$thinking" --resume --session 'session with spaces.jsonl' -- 'message with spaces'
+        )"
+        assert_eq "$args" "$expected" "${launcher} regular mode and pi arguments"
+    done
 }
 
 test_pixg_oauth_guidance() {
@@ -598,7 +642,8 @@ test_setup_places_all_launcher_configs() {
             || fail "${launcher} config differs from the repository source"
     done
     [ -d "${home}/.pi/agent/extensions/subagent" ] || fail "setup did not create the shared dir"
-    [ -f "${home}/.local/bin/pi-superagents-exec.zsh" ] || fail "setup did not place the helper"
+    cmp -s "$HELPER" "${home}/.local/bin/pi-superagents-exec.zsh" \
+        || fail "setup must place the current helper"
 }
 
 test_setup_backs_up_modified_config() {
@@ -687,8 +732,12 @@ test_setup_if_absent_preserves_user_edits() {
     run_setup "$home" >/dev/null
     config="${home}/.pi/agent/extensions/subagent.d/piccd/config.json"
     printf '{"superagents":{"modelTiers":{"cheap":{"model":"x/y","thinking":"max"}}}}\n' > "$config"
+    # 既存環境の更新では --if-absent の再実行でヘルパ（--tui-mode など）を最新にする。
+    printf '# stale helper\n' > "${home}/.local/bin/pi-superagents-exec.zsh"
     run_setup "$home" --if-absent >/dev/null
     grep -q '"x/y"' "$config" || fail "--if-absent must not overwrite an existing config"
+    cmp -s "$HELPER" "${home}/.local/bin/pi-superagents-exec.zsh" \
+        || fail "--if-absent must refresh the helper while preserving configs"
 }
 
 test_setup_output_mentions_each_launcher() {
@@ -1191,6 +1240,7 @@ test_missing_config_fails_closed
 test_missing_bwrap_fails_closed
 test_dry_run_one_prints_argv_without_exec
 test_dry_run_zero_execs_bwrap
+test_actual_and_dry_run_argv_match
 test_tier_tables
 test_commandcode_models_are_defined_in_pi_models
 test_opencode_go_tiers_use_opencode_go
@@ -1199,7 +1249,7 @@ test_configs_are_minimal_partial_configs
 test_launcher_files_are_executable
 test_launchers_wrap_pi_with_their_own_config
 test_launchers_preserve_parent_model_selection
-test_launchers_forward_user_arguments
+test_launchers_select_regular_and_forward_user_arguments
 test_pixg_oauth_guidance
 test_commandcode_key_check_runs_before_launch
 test_launcher_missing_config_fails_closed
ISSUE20_T1_TEST
````

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash 2>&1 | grep -m1 FAIL; bash .devcontainer/test-pi-openai-codex.bash 2>&1 | grep -m1 FAIL`

Expected: `FAIL: helper must select regular before forwarding pi args: expected='--tui-mode` と `FAIL: piga Pi arguments: expected='--tui-mode` で始まる 2 行（ヘルパがまだ `--tui-mode regular` を付けないため）

- [ ] **Step 3: ヘルパに `--tui-mode regular` を足す**

````bash
git apply --index --3way <<'ISSUE20_T1_IMPL'
diff --git a/.devcontainer/pi-superagents-exec.zsh b/.devcontainer/pi-superagents-exec.zsh
index b6919a9..66cfa1d 100755
--- a/.devcontainer/pi-superagents-exec.zsh
+++ b/.devcontainer/pi-superagents-exec.zsh
@@ -135,7 +135,9 @@ pi_superagents_exec() {
         --die-with-parent
         --bind "${launcher_dir}" "${shared_dir}"
         --
-        pi "$@"
+        # Pi 1.0.0 の fullscreen 既定を避け、Herdr の通常のスクロール履歴を残す。
+        # 利用者の引数は後ろに並ぶので、--tui-mode fullscreen を渡せばそちらが勝つ。
+        pi --tui-mode regular "$@"
     )
 
     if [[ "${PI_SUPERAGENTS_LAUNCHER_DRY_RUN:-}" == "1" ]]; then
ISSUE20_T1_IMPL
````

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-pi-superagents.bash .devcontainer/test-pi-openai-codex.bash`

Expected: `PASS: 2 test(s)`

- [ ] **Step 5: コミットする**

```bash
git commit -m "feat(pi): start every launcher in regular TUI mode

Pi 1.0 defaults to fullscreen, which hides the output from Herdr's
scrollback. The shared helper now passes --tui-mode regular before the
launcher and user arguments, so all nine launchers keep the terminal
history and an explicit --tui-mode fullscreen still wins.

Refs #20

Co-Authored-By: <実行するエージェントのモデル名> <noreply@anthropic.com>"
```

---

### Task 2: `pigs`・`pixg` の tier・認証の確認・API キーの互換を揃える

**Files:**
- Modify: `.devcontainer/pi-superagents/pigs.json`、`.devcontainer/pi-superagents/pixg.json`、`.devcontainer/pigs`、`.devcontainer/pixg`
- Test: `.devcontainer/test-pi-superagents.bash`、`.devcontainer/test-pi-openai-codex.bash`

**Interfaces:**
- Consumes: Task 1 の `test_launchers_select_regular_and_forward_user_arguments`（`pixg` の行は xAI と Codex の両方の OAuth を置くので、この Task の後も通る）、既存の `write_xai_auth`・`run_launcher`・`CONFIG_DIR`
- Produces: `write_pixg_auth` を削除し、`pixg` の検査は `write_xai_auth` を使う。新しい検査 `test_opencode_key_reaches_child_process`。Task 3 の README の記述はこの Task の tier と認証を前提にする

- [ ] **Step 1: テストを変える**

tier 表の `pigs`・`pixg` の行を Spec 4.2 節に合わせる。`pixg` の検査は xAI OAuth だけで起動できることを確かめ、Codex OAuth を求めないことを確かめる。`pigs`・`pixg` を環境変数を表示する fake の `bwrap` で実際に起動し、`OPENCODE_API_KEY` の互換を確かめる検査を足す。`test-pi-openai-codex.bash` の Codex の tier の表から `pigs` の cheap を外す。

````bash
git apply --index --3way <<'ISSUE20_T2_TEST'
diff --git a/.devcontainer/test-pi-openai-codex.bash b/.devcontainer/test-pi-openai-codex.bash
index 6237823..f337fbc 100755
--- a/.devcontainer/test-pi-openai-codex.bash
+++ b/.devcontainer/test-pi-openai-codex.bash
@@ -23,7 +23,6 @@ test_setup_places_independent_gpt6_tiers() {
         "piga:cheap:gpt-6-luna:xhigh"
         "piga:balanced:gpt-6.1-sol:xhigh"
         "piga:max:gpt-6-astra:max"
-        "pigs:cheap:gpt-6-luna:xhigh"
         "pigs:balanced:gpt-6.1-sol:xhigh"
         "pigs:max:gpt-6.1-sol:max"
         "pigl:cheap:gpt-6-luna:xhigh"
diff --git a/.devcontainer/test-pi-superagents.bash b/.devcontainer/test-pi-superagents.bash
index a395c74..9eda79e 100755
--- a/.devcontainer/test-pi-superagents.bash
+++ b/.devcontainer/test-pi-superagents.bash
@@ -48,14 +48,6 @@ write_xai_auth() {
         > "${home}/.pi/agent/auth.json"
 }
 
-write_pixg_auth() {
-    local home="$1"
-    mkdir -p "${home}/.pi/agent"
-    printf '%s\n' \
-        '{"xai":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999},"openai-codex":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999}}' \
-        > "${home}/.pi/agent/auth.json"
-}
-
 # ヘルパを source して pi_superagents_exec を dry-run で呼ぶ。
 run_helper() {
     local home="$1" launcher="$2"; shift 2
@@ -232,9 +224,9 @@ test_tier_tables() {
         "piccg:commandcode/meta/muse-spark-1.3-contributor:commandcode/meta/muse-spark-1.3-contributor:commandcode/deepseek/deepseek-v4.1-flash:max:max:max"
         "piccd:commandcode/meta/muse-spark-1.3-contributor:commandcode/deepseek/deepseek-v4.1-flash:commandcode/deepseek/deepseek-v4.1-flash:max:max:max"
         "piga:openai-codex/gpt-6-luna:openai-codex/gpt-6.1-sol:openai-codex/gpt-6-astra:xhigh:xhigh:max"
-        "pigs:openai-codex/gpt-6-luna:openai-codex/gpt-6.1-sol:openai-codex/gpt-6.1-sol:xhigh:xhigh:max"
+        "pigs:opencode-go/deepseek-v4.1-flash:openai-codex/gpt-6.1-sol:openai-codex/gpt-6.1-sol:max:xhigh:max"
         "pigl:openai-codex/gpt-6-luna:openai-codex/gpt-6.1-sol:openai-codex/gpt-6.1-sol:xhigh:xhigh:xhigh"
-        "pixg:openai-codex/gpt-6-luna:xai/grok-4.7:xai/grok-4.7:xhigh:high:xhigh"
+        "pixg:opencode-go/deepseek-v4.1-flash:opencode-go/deepseek-v4.1-flash:xai/grok-4.7:max:max:xhigh"
     )
     local row
     for row in "${rows[@]}"; do
@@ -328,6 +320,52 @@ run_launcher() {
         zsh "${REPO_ROOT}/.devcontainer/${launcher}" "$@"
 }
 
+test_opencode_key_reaches_child_process() {
+    # pigs の cheap と pixg の cheap / balanced は opencode-go を使う。旧名の
+    # OPENCODE_GO_API_KEY から OPENCODE_API_KEY への互換が、ランチャーから
+    # exec された子プロセスまで届くことを確かめる。
+    local shim_dir="${TEST_ROOT}/opencode-key-bin"
+    local launcher home row primary legacy expected output
+    local -a key_env cases=(
+        '<unset>:dummy-legacy:dummy-legacy'
+        ':dummy-legacy:dummy-legacy'
+        'dummy-primary:dummy-legacy:dummy-primary'
+        '<unset>:<unset>:<unset>'
+    )
+    mkdir -p "$shim_dir"
+    # 実ランチャーから exec された bwrap の子で、export された値を観測する。
+    # 実際の mount namespace や Pi の API 呼び出しはこのテストには不要。
+    cat > "${shim_dir}/bwrap" <<'BWRAP_ENV_EOF'
+#!/bin/bash
+bash -c 'printf "%s\n" "${OPENCODE_API_KEY-<unset>}"'
+BWRAP_ENV_EOF
+    chmod +x "${shim_dir}/bwrap"
+
+    for launcher in pigs pixg; do
+        home="${TEST_ROOT}/${launcher}-opencode-key"
+        mkdir -p "${home}/.pi/agent/extensions/subagent.d/${launcher}"
+        cp "${CONFIG_DIR}/${launcher}.json" "${home}/.pi/agent/extensions/subagent.d/${launcher}/config.json"
+        printf '%s\n' '{"openai-codex":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999},"xai":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999}}' \
+            > "${home}/.pi/agent/auth.json"
+        for row in "${cases[@]}"; do
+            IFS=: read -r primary legacy expected <<< "$row"
+            key_env=(env -u OPENCODE_API_KEY -u OPENCODE_GO_API_KEY)
+            if [ "$primary" != '<unset>' ]; then
+                key_env+=("OPENCODE_API_KEY=$primary")
+            fi
+            if [ "$legacy" != '<unset>' ]; then
+                key_env+=("OPENCODE_GO_API_KEY=$legacy")
+            fi
+            output="$("${key_env[@]}" HOME="$home" \
+                PI_CODING_AGENT_DIR="${home}/.pi/agent" PATH="${shim_dir}:${PATH}" \
+                PI_SUPERAGENTS_LAUNCHER_DRY_RUN=0 \
+                "${ZSH_BIN}" "${REPO_ROOT}/.devcontainer/${launcher}")"
+            assert_eq "$output" "$expected" \
+                "${launcher} child key with primary='${primary}' legacy='${legacy}'"
+        done
+    done
+}
+
 # dry-run 出力から pi へ渡る引数だけを取り出す（"--" の次の "pi" より後ろ）。
 pi_args_of() {
     printf '%s\n' "$1" | awk 'seen { print } $0 == "pi" { seen = 1 }'
@@ -348,7 +386,7 @@ test_launchers_wrap_pi_with_their_own_config() {
     for launcher in pigo pigod pigou piccg piccd pixg; do
         home="$(make_home "$launcher" with-config)"
         if [ "$launcher" = pixg ]; then
-            write_pixg_auth "$home"
+            write_xai_auth "$home"
         fi
         out="$(run_launcher "$home" "$launcher")"
         assert_eq "$(printf '%s\n' "$out" | sed -n 1p)" "bwrap" "${launcher} argv[0]"
@@ -389,7 +427,7 @@ test_launchers_preserve_parent_model_selection() {
     assert_contains "$args" "deepseek/deepseek-v4.1-flash" "piccd model"
 
     home="$(make_home pixg with-config)"
-    write_pixg_auth "$home"
+    write_xai_auth "$home"
     args="$(pi_args_of "$(run_launcher "$home" pixg)")"
     assert_contains "$args" "xai" "pixg provider"
     assert_contains "$args" "grok-4.7" "pixg model"
@@ -461,19 +499,16 @@ test_pixg_oauth_guidance() {
     assert_eq "$status" "1" "pixg must exit 1 for non-oauth xai credentials"
     assert_contains "$out" "/login xai" "non-oauth credential must still guide to /login"
 
-    # xAI OAuth だけでは cheap tier の Luna に接続できないので、起動前に案内する。
+    # xAI OAuth があれば起動する。cheap / balanced tier の子 Pi が使う
+    # opencode-go の資格情報は auth.json の api_key または OPENCODE_API_KEY で
+    # 解決し、ランチャーは起動前に確認しない（pigo / pigod と同じ）。
+    # Codex OAuth は使わないので、無くても止まらない。
     write_xai_auth "$home"
-    set +e
     out="$(run_launcher "$home" pixg 2>&1)"
-    status=$?
-    set -e
-    assert_eq "$status" "1" "pixg must stop without Codex OAuth for Luna"
-    assert_contains "$out" "/login openai-codex" "must explain Codex OAuth login"
-
-    # 両プロバイダの OAuth があれば Grok 親を起動する。
-    write_pixg_auth "$home"
-    out="$(run_launcher "$home" pixg)"
-    assert_contains "$out" "grok-4.7" "valid xAI and Codex OAuth must reach argv"
+    assert_contains "$out" "grok-4.7" "valid xAI OAuth must reach argv"
+    case "$out" in
+        *'/login openai-codex'*) fail "pixg must not require Codex OAuth" ;;
+    esac
 
     # PI_CODING_AGENT_DIR の ~ 展開も共有ヘルパと同じ受理形にする。
     out="$(env HOME="$home" PI_CODING_AGENT_DIR='~/.pi/agent' \
@@ -1250,6 +1285,7 @@ test_launcher_files_are_executable
 test_launchers_wrap_pi_with_their_own_config
 test_launchers_preserve_parent_model_selection
 test_launchers_select_regular_and_forward_user_arguments
+test_opencode_key_reaches_child_process
 test_pixg_oauth_guidance
 test_commandcode_key_check_runs_before_launch
 test_launcher_missing_config_fails_closed
ISSUE20_T2_TEST
````

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash 2>&1 | grep -m1 FAIL`

Expected: `FAIL: pigs cheap: expected='opencode-go/deepseek-v4.1-flash' actual='openai-codex/gpt-6-luna'`（tier の JSON がまだ古いため。`test-pi-openai-codex.bash` は行を外しただけなので、この時点でも通る）

- [ ] **Step 3: tier の JSON とランチャーを直す**

`pigs.json`・`pixg.json` は移植元と同じ内容になる。`pigs` は Codex OAuth の確認を残して互換を足し、`pixg` は Codex OAuth の確認を外して互換を足す。

````bash
git apply --index --3way <<'ISSUE20_T2_IMPL'
diff --git a/.devcontainer/pi-superagents/pigs.json b/.devcontainer/pi-superagents/pigs.json
index 5746816..4142085 100644
--- a/.devcontainer/pi-superagents/pigs.json
+++ b/.devcontainer/pi-superagents/pigs.json
@@ -1,7 +1,7 @@
 {
   "superagents": {
     "modelTiers": {
-      "cheap": { "model": "openai-codex/gpt-6-luna", "thinking": "xhigh" },
+      "cheap": { "model": "opencode-go/deepseek-v4.1-flash", "thinking": "max" },
       "balanced": { "model": "openai-codex/gpt-6.1-sol", "thinking": "xhigh" },
       "max": { "model": "openai-codex/gpt-6.1-sol", "thinking": "max" }
     }
diff --git a/.devcontainer/pi-superagents/pixg.json b/.devcontainer/pi-superagents/pixg.json
index e7a5d78..74e25e5 100644
--- a/.devcontainer/pi-superagents/pixg.json
+++ b/.devcontainer/pi-superagents/pixg.json
@@ -1,8 +1,8 @@
 {
   "superagents": {
     "modelTiers": {
-      "cheap": { "model": "openai-codex/gpt-6-luna", "thinking": "xhigh" },
-      "balanced": { "model": "xai/grok-4.7", "thinking": "high" },
+      "cheap": { "model": "opencode-go/deepseek-v4.1-flash", "thinking": "max" },
+      "balanced": { "model": "opencode-go/deepseek-v4.1-flash", "thinking": "max" },
       "max": { "model": "xai/grok-4.7", "thinking": "xhigh" }
     }
   }
diff --git a/.devcontainer/pigs b/.devcontainer/pigs
index 7fec9c5..5518a1d 100755
--- a/.devcontainer/pigs
+++ b/.devcontainer/pigs
@@ -26,6 +26,20 @@ source "${PI_SUPERAGENTS_HELPER}"
 
 pi_openai_codex_require_oauth || exit 1
 
+#
+# Compatibility with the environment variable used by an older setup.
+#
+if [[ -z "${OPENCODE_API_KEY:-}" && -n "${OPENCODE_GO_API_KEY:-}" ]]; then
+    export OPENCODE_API_KEY="${OPENCODE_GO_API_KEY}"
+fi
+
+#
+# cheap tier の子 Pi は opencode-go/deepseek-v4.1-flash を使う。
+# opencode-go の資格情報は auth.json の api_key または OPENCODE_API_KEY で
+# 解決されるため、pigo / pigod / pixg と同じく起動前の認証チェックは
+# 行わない。親 Pi と balanced / max tier は openai-codex のままなので、
+# 上の Codex OAuth チェックは維持する。
+#
 pi_superagents_exec pigs \
     --provider openai-codex \
     --model gpt-6.1-sol \
diff --git a/.devcontainer/pixg b/.devcontainer/pixg
index 3e20449..fb5c9b9 100755
--- a/.devcontainer/pixg
+++ b/.devcontainer/pixg
@@ -25,8 +25,13 @@ fi
 source "${PI_SUPERAGENTS_HELPER}"
 
 pi_xai_require_oauth || exit 1
-# cheap tier の子 Pi は Codex の Luna を使うため、親の起動前に両方を確認する。
-pi_openai_codex_require_oauth || exit 1
+
+#
+# Compatibility with the environment variable used by an older setup.
+#
+if [[ -z "${OPENCODE_API_KEY:-}" && -n "${OPENCODE_GO_API_KEY:-}" ]]; then
+    export OPENCODE_API_KEY="${OPENCODE_GO_API_KEY}"
+fi
 
 #
 # xai は pi の built-in provider で、grok-4.7 も組み込みのモデルカタログに
@@ -36,6 +41,10 @@ pi_openai_codex_require_oauth || exit 1
 # grok-4.7 の thinking level は low / medium / high / xhigh で、他ランチャーの
 # max ではなく実際の最大値である xhigh を明示する。
 #
+# cheap / balanced tier の子 Pi は opencode-go/deepseek-v4.1-flash を使う。
+# opencode-go の資格情報は auth.json の api_key または OPENCODE_API_KEY で
+# 解決されるため、pigo / pigod と同じく起動前の認証チェックは行わない。
+#
 pi_superagents_exec pixg \
     --provider xai \
     --model grok-4.7 \
ISSUE20_T2_IMPL
````

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-pi-superagents.bash .devcontainer/test-pi-openai-codex.bash`

Expected: `PASS: 2 test(s)`

互換の検査が実際に効いていることも確かめる。`pigs` の互換の `if` ブロック（`OPENCODE_GO_API_KEY` を見る 3 行）だけを作業ツリーで一時的に消すと `FAIL: pigs child key with primary='<unset>' legacy='dummy-legacy': expected='dummy-legacy' actual='<unset>'` で失敗する。確かめたら `git restore .devcontainer/pigs` で stage 済みの内容（Step 3 のパッチは `--index` で stage されている）に戻し、`git diff --stat` が空であることを確かめる。`pixg` も同様に確かめる。

- [ ] **Step 5: コミットする**

```bash
git commit -m "feat(pi): move the pigs and pixg cheap tiers to OpenCode Go

Match maatlog-poc: pigs uses opencode-go/deepseek-v4.1-flash for its
cheap tier, and pixg uses it for cheap and balanced. pixg no longer
requires Codex OAuth, and both launchers pass a legacy
OPENCODE_GO_API_KEY on as OPENCODE_API_KEY to the child processes.

Refs #20

Co-Authored-By: <実行するエージェントのモデル名> <noreply@anthropic.com>"
```

---

### Task 3: README とライブ確認の Pi の最小版を合わせる

**Files:**
- Modify: `.devcontainer/README.md`（「ChatGPT Pro の GPT-6 ランチャー」「SuperGrok / X Premium の Grok 4.7 ランチャー」「pi-superagents のランチャー別 model tier」の節、新設の「pi の TUI モードと Herdr のスクロール履歴」の節）
- Test: `.devcontainer/test-pi-superagents.bash`（`test_readme_documents_the_mechanism`）、`.devcontainer/test-pi-openai-codex.bash`（`test_live_openai_codex_models`）

**Interfaces:**
- Consumes: Task 1 の `--tui-mode regular`、Task 2 の tier と認証
- Produces: README の新しい節「pi の TUI モードと Herdr のスクロール履歴」（#22 が README 全体を整えるときの入力）

- [ ] **Step 1: テストを変える**

README が `--tui-mode regular` を説明していることを確かめる検査を足す。ライブ確認（`PI_CODEX_LIVE_CHECK=1` のときだけ動く）の Pi の最小版を 0.99.1 にする（GPT-6.1 Sol は Pi 0.99.1 で追加された）。

````bash
git apply --index --3way <<'ISSUE20_T3_TEST'
diff --git a/.devcontainer/test-pi-openai-codex.bash b/.devcontainer/test-pi-openai-codex.bash
index f337fbc..a856297 100755
--- a/.devcontainer/test-pi-openai-codex.bash
+++ b/.devcontainer/test-pi-openai-codex.bash
@@ -159,8 +159,8 @@ test_live_openai_codex_models() {
 
     local version model output
     version="$(pi --version)" || fail "pi --version failed"
-    dpkg --compare-versions "$version" ge 0.87.1 \
-        || fail "Pi 0.87.1 or newer is required (installed: ${version})"
+    dpkg --compare-versions "$version" ge 0.99.1 \
+        || fail "Pi 0.99.1 or newer is required (installed: ${version})"
 
     for model in gpt-6-astra gpt-6.1-sol gpt-6-luna; do
         output="$(pi --list-models "$model")" || fail "pi --list-models ${model} failed"
diff --git a/.devcontainer/test-pi-superagents.bash b/.devcontainer/test-pi-superagents.bash
index 9eda79e..1afbee6 100755
--- a/.devcontainer/test-pi-superagents.bash
+++ b/.devcontainer/test-pi-superagents.bash
@@ -1262,6 +1262,8 @@ test_readme_documents_the_mechanism() {
         || fail "README must explain the bwrap bind"
     grep -q 'setup_pi_superagents.zsh' "$DEVCONTAINER_README" \
         || fail "README must document how to update tiers"
+    grep -qF -- '--tui-mode regular' "$DEVCONTAINER_README" \
+        || fail "README must explain why launchers start pi in regular TUI mode"
     for launcher in pigo pigod pigou piccg piccd piga pigs pigl pixg; do
         grep -q "$launcher" "$DEVCONTAINER_README" \
             || fail "README must list ${launcher}"
ISSUE20_T3_TEST
````

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash 2>&1 | grep -m1 FAIL`

Expected: `FAIL: README must explain why launchers start pi in regular TUI mode`

- [ ] **Step 3: README を直す**

`pigs` の cheap と `pixg` の認証・tier の説明を新しい構成にし、Pi の最小版を 0.99.1 にし、TUI モードの節（既存環境の更新手順を含む）を足し、tier の表と thinking の説明を直す。

````bash
git apply --index --3way <<'ISSUE20_T3_IMPL'
diff --git a/.devcontainer/README.md b/.devcontainer/README.md
index 8fbf82e..2fa829f 100644
--- a/.devcontainer/README.md
+++ b/.devcontainer/README.md
@@ -336,15 +336,22 @@ provider が `opencode-go` のモデルへ `x-opencode-session` と
 | `pigs` | `openai-codex/gpt-6.1-sol` |
 | `pigl` | `openai-codex/gpt-6-luna` |
 
-3 つとも ChatGPT Pro サブスクリプションの Codex OAuth 認証を使う。
+3 つとも親 Pi は ChatGPT Pro サブスクリプションの Codex OAuth 認証を使う。
 `OPENAI_API_KEY` は不要で、OpenAI API のキー課金用 provider には接続しない。
 初回だけ素の `pi` を起動して `/login openai-codex` を実行し、ログインする。
 OAuth 情報は `~/.pi/agent/auth.json` に保存される。`~/.pi` は Dev Container に bind mount
 されているため、リビルド後もログイン状態を保持する。認証は対話操作が必要で、
 `postCreateCommand` から自動ログインしない。未認証のままランチャーを起動した
 場合は、このログイン手順を表示して終了する。
-
-GPT-6.1 Sol / GPT-6 Luna のため Pi 0.87.1 以上が必要。利用前に `pi --version` を確認し、
+`pigs` の `cheap` tier の子 Pi は OpenCode Go の `deepseek-v4.1-flash` を
+使う。子 Pi が使う OpenCode Go の資格情報は `setup_pi_opencode_go.zsh` が
+`auth.json` に書いた api_key または `OPENCODE_API_KEY` で解決され、`pigo`・`pigod` と
+同じく起動前の確認は行わない。旧名の `OPENCODE_GO_API_KEY` だけが設定されている場合は、
+ランチャーが `OPENCODE_API_KEY` に引き継いでから起動する。`auth.json` に資格情報が無い環境では
+`cheap` tier の子 Pi が provider 認証エラーになるため、必要なら `OPENCODE_API_KEY` を
+設定して `zsh .devcontainer/setup_pi_opencode_go.zsh` を実行する。
+
+GPT-6.1 Sol のため Pi 0.99.1 以上が必要（GPT-6 Astra / Luna もこの版に含まれる）。利用前に `pi --version` を確認し、
 ログイン後に各モデルが `openai-codex` 行にあることを確認する。
 
 ```bash
@@ -358,7 +365,8 @@ pi --list-models gpt-6-luna
 表示するため、未認証時には Pi がモデル定義を持っていても `openai-codex` 行は
 表示されない。3 ランチャーは `--thinking xhigh` で起動する。子 Pi の
 `cheap` / `balanced` / `max` tier はランチャーごとに GPT-6 Luna / GPT-6.1 Sol /
-GPT-6 Astra を割り当てる（下表を参照）。ログイン済みの環境では、次のテストでも Pi の版と
+GPT-6 Astra を割り当てる（`pigs` の `cheap` だけは OpenCode Go の
+`deepseek-v4.1-flash`。後述の tier の表を参照）。ログイン済みの環境では、次のテストでも Pi の版と
 3 モデルを検証できる。
 
 ```bash
@@ -371,35 +379,36 @@ PI_CODEX_LIVE_CHECK=1 bash .devcontainer/test-pi-openai-codex.bash
 |---|---|
 | `pixg` | `xai/grok-4.7` |
 
-`pixg` の親 Pi と `balanced` / `max` tier は SuperGrok または X Premium
-サブスクリプションの xAI OAuth 認証を使い、`cheap` tier の子 Pi は
-OpenAI Codex OAuth 認証で GPT-6 Luna を使う。`XAI_API_KEY` は不要で、
-xAI API のキー課金には接続しない。
+`pixg` の親 Pi と `max` tier は SuperGrok または X Premium
+サブスクリプションの xAI OAuth 認証を使い、`cheap` / `balanced` tier の
+子 Pi は OpenCode Go の `deepseek-v4.1-flash` を使う。`XAI_API_KEY` は
+不要で、xAI API のキー課金には接続しない。OpenAI Codex の認証も使わない。
 初回だけ素の `pi` を起動して `/login xai` を実行し、
-`Sign in with SuperGrok or X Premium` からログインした後、
-`/login openai-codex` も実行する。両プロバイダの OAuth 情報は
+`Sign in with SuperGrok or X Premium` からログインする。OAuth 情報は
 `~/.pi/agent/auth.json` に保存される。`~/.pi` は Dev Container に bind mount
 されているため、リビルド後もログイン状態を保持する。認証は対話操作が必要で、
-`postCreateCommand` から自動ログインしない。いずれかが未認証なら、
-`pixg` は xAI、OpenAI Codex の順に認証を確認し、最初に見つかった
-未認証プロバイダのログイン手順だけを表示して起動前に終了する。
+`postCreateCommand` から自動ログインしない。xAI が未認証なら、
+`pixg` はログイン手順を表示して起動前に終了する。
+子 Pi が使う OpenCode Go の資格情報は `setup_pi_opencode_go.zsh` が
+`auth.json` に書いた api_key または `OPENCODE_API_KEY` で解決され、`pigo`・`pigod` と
+同じく起動前の確認は行わない。旧名の `OPENCODE_GO_API_KEY` の扱いは `pigs` と同じである。
 
-Grok 4.7 と GPT-6 Luna は Pi の組み込みカタログにあるため、`pi-models.json`
-への定義追加は不要である。両方ログインした後、それぞれのモデルを確認する。
+Grok 4.7 と DeepSeek V4.1 Flash は Pi の組み込みカタログにあるため、
+`pi-models.json` への定義追加は不要である。ログイン後にそれぞれのモデルを
+確認する。
 
 ```bash
 pi --list-models xai
-pi --list-models gpt-6-luna
+pi --list-models deepseek-v4.1-flash
 ```
 
 モデル行が無い場合は Pi を更新する。`pi --list-models` は利用可能なモデルを
 表示するため、未認証時には Pi がモデル定義を持っていても該当する
 プロバイダの行は表示されない。`pixg` は `--thinking xhigh` で起動する。
 Grok 4.7 の thinking level は `low` / `medium` / `high` / `xhigh` で、
-`xhigh` が実際の最大値である。子 Pi は `cheap` が
-`openai-codex/gpt-6-luna` の `xhigh`、`balanced` が `xai/grok-4.7` の
-`high`、`max` が `xai/grok-4.7` の `xhigh` を使う。未認証時に別モデルへ
-自動フォールバックはしない。
+`xhigh` が実際の最大値である。子 Pi は `cheap` / `balanced` が
+`opencode-go/deepseek-v4.1-flash` の `max`、`max` が `xai/grok-4.7` の
+`xhigh` を使う。未認証時に別モデルへ自動フォールバックはしない。
 
 ### pi-distill の分離（Main / Distillation）
 
@@ -501,6 +510,38 @@ commandcode の 2 つのランチャを `setup_pi_commandcode_goat.zsh` が同
   ランチャがエラーメッセージを出して終了する。キーは
   `https://commandcode.ai/settings/keys` で作成する
 
+### pi の TUI モードと Herdr のスクロール履歴
+
+Pi 1.0.0 から、対話 TUI の既定モードは `fullscreen` になった。このモードは
+代替画面を使って会話履歴を Pi 内で管理するため、Herdr の通常のスクロール履歴に
+過去の出力が残らず、コピーモードでさかのぼれない。
+
+このリポジトリが管理する `pigo`・`pigod`・`pigou`・`piccg`・`piccd`・`piga`・
+`pigs`・`pigl`・`pixg` は、共通ヘルパ `pi-superagents-exec.zsh` から
+`pi --tui-mode regular` を起動する。regular は通常画面と端末のスクロール履歴を
+使うため、画面高を超えた出力も Herdr のコピーモードで読める。
+利用者／プロジェクトの `settings.json` は書き換えず、起動引数で指定する。
+provider・model・thinking・認証確認・ランチャー別設定の分離は従来どおりで、
+`--resume`・`--session`・メッセージなどの追加引数もそのまま転送する。
+この指定はランチャーの既定値なので、追加引数に `--tui-mode fullscreen` を指定した
+場合はその指定が優先される。素の `pi` の既定モードには影響しない。
+
+Dev Container の初期化／リビルドでは `install_beforehand.bash` が全ランチャーを
+配置し、`setup_pi_superagents.zsh --if-absent` が共通ヘルパを更新する。
+`--if-absent` は既存のランチャー別 tier 設定を保持するが、共通ヘルパは毎回
+更新する。リビルドしない既存環境では、リポジトリのルートで次を実行してから
+ランチャーを起動し直す。
+
+```bash
+zsh .devcontainer/setup_pi_superagents.zsh --if-absent
+```
+
+`pigs`・`pixg` の tier の変更（後述）を既存環境に反映するには、`--if-absent` を付けずに
+`zsh .devcontainer/setup_pi_superagents.zsh` を実行する（変更のある設定はバックアップされる）。
+`pigs`・`pixg` の認証の確認の変更はランチャー自体にあり、リビルドで `~/.local/bin` に
+置き直される。リビルドしない場合は `install -m 0755 .devcontainer/pigs ~/.local/bin/pigs`
+（`pixg` も同様）で置き直す。
+
 ### pi-superagents のランチャー別 model tier
 
 `@teelicht/pi-superagents` は Superpowers の Plan を Pi 自身の子プロセスで実行する拡張で、子 Pi のモデルを `cheap` / `balanced` / `max` の 3 tier で選ぶ。tier の定義は拡張が `~/.pi/agent/extensions/subagent/config.json` から読むが、このパスは拡張のソースに直接書かれており、環境変数による切り替えができない。
@@ -523,13 +564,15 @@ commandcode の 2 つのランチャを `setup_pi_commandcode_goat.zsh` が同
 | `piccg` | `commandcode/meta/muse-spark-1.3-contributor` | `commandcode/meta/muse-spark-1.3-contributor` | `commandcode/deepseek/deepseek-v4.1-flash` |
 | `piccd` | `commandcode/meta/muse-spark-1.3-contributor` | `commandcode/deepseek/deepseek-v4.1-flash` | `commandcode/deepseek/deepseek-v4.1-flash` |
 | `piga` | `openai-codex/gpt-6-luna` | `openai-codex/gpt-6.1-sol` | `openai-codex/gpt-6-astra` |
-| `pigs` | `openai-codex/gpt-6-luna` | `openai-codex/gpt-6.1-sol` | `openai-codex/gpt-6.1-sol` |
+| `pigs` | `opencode-go/deepseek-v4.1-flash` | `openai-codex/gpt-6.1-sol` | `openai-codex/gpt-6.1-sol` |
 | `pigl` | `openai-codex/gpt-6-luna` | `openai-codex/gpt-6.1-sol` | `openai-codex/gpt-6.1-sol` |
-| `pixg` | `openai-codex/gpt-6-luna` | `xai/grok-4.7` | `xai/grok-4.7` |
+| `pixg` | `opencode-go/deepseek-v4.1-flash` | `opencode-go/deepseek-v4.1-flash` | `xai/grok-4.7` |
 
-`piga` / `pigs` の子 Pi は `cheap` / `balanced` が `xhigh`、`max` が `max`、
-`pigl` の子 Pi は全 tier が `xhigh`。`pixg` の子 Pi は Luna の `cheap` と
-Grok の `max` が `xhigh`、Grok の `balanced` が `high`。
+`pigo`・`pigod`・`pigou`・`piccg`・`piccd` の子 Pi は全 tier が `max`。
+`piga` の子 Pi は `cheap` / `balanced` が `xhigh`、`max` が `max`。
+`pigs` の子 Pi は `cheap` が `max`、`balanced` が `xhigh`、`max` が `max`。
+`pigl` の子 Pi は全 tier が `xhigh`。`pixg` の子 Pi は DeepSeek の
+`cheap` / `balanced` が `max`、Grok の `max` が `xhigh`。
 tier を変更するときは、リポジトリの `.devcontainer/pi-superagents/<launcher>.json` を編集してから次を実行する。`install_beforehand.bash` は既存の設定を保持するため、rebuild だけでは反映されない。
 
 ```bash
ISSUE20_T3_IMPL
````

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-pi-superagents.bash .devcontainer/test-pi-openai-codex.bash .devcontainer/test-readme.bash tests/scripts/test-docs.bash`

Expected: `PASS: 4 test(s)`

- [ ] **Step 5: コミットする**

```bash
git commit -m "docs(devcontainer): explain the regular TUI mode and the new pi tiers

Document why the launchers pass --tui-mode regular, how existing
environments pick up the helper and tier changes, the OpenCode Go
child tiers of pigs and pixg, and the Pi 0.99.1 floor for GPT-6.1 Sol.

Refs #20

Co-Authored-By: <実行するエージェントのモデル名> <noreply@anthropic.com>"
```

---

### Task 4: 全体を検証して PR を作る

**Files:**
- なし（検証、push、PR の作成、#20 への報告）

**Interfaces:**
- Consumes: Task 1〜3 のコミット
- Produces: `feat/issue-20-pi-launchers` → `main` の PR（本文に `Closes #20`）

- [ ] **Step 1: 全テストを実行する**

Run: `bash .devcontainer/run-tests.bash`

Expected: `FAIL: 1 of 25 test(s) failed: tests/scripts/test-check-layout.bash`（slum03 の resoloop スキルの未同期による既知の失敗だけ。`origin/main` を取り込んでテストの本数が変わっていれば、失敗が `tests/scripts/test-check-layout.bash` の 1 本だけであることを確かめる）

- [ ] **Step 2: 配置とスキルのテストを実行する**

Run: `bash scripts/check-layout.sh; uv run pytest -q tests/skills .agents/skills`

Expected: check-layout は `FAIL: resoloop skills sync --check failed for slum03` と `FAIL: check-layout (1 failure(s))` だけ。pytest は `267 passed, 1 skipped`（`origin/main` を取り込んで本数が変わっていれば、失敗が 0 件であること）

- [ ] **Step 3: 範囲外のファイルに差分が無いことを確かめる**

Run: `git diff --stat origin/main...HEAD`

Expected: 変更は `.devcontainer/pi-superagents-exec.zsh`・`.devcontainer/pi-superagents/pigs.json`・`.devcontainer/pi-superagents/pixg.json`・`.devcontainer/pigs`・`.devcontainer/pixg`・`.devcontainer/README.md`・`.devcontainer/test-pi-superagents.bash`・`.devcontainer/test-pi-openai-codex.bash`・この Spec・この計画の 10 ファイルだけ

Run: `git diff --exit-code origin/main...HEAD -- .devcontainer/install_beforehand.bash .devcontainer/setup_pi_superagents.zsh .devcontainer/setup_pi_opencode_go.zsh .devcontainer/setup_pi_commandcode_goat.zsh .devcontainer/pigo .devcontainer/pigod .devcontainer/pigou .devcontainer/piccg .devcontainer/piccd .devcontainer/piga .devcontainer/pigl .agents .claude`

Expected: 出力なし、終了コード 0

- [ ] **Step 4: 移植元との一致を確かめる**

移植元を一時ディレクトリに取得し（`gh repo clone usaturn/maatlog-poc <一時ディレクトリ> -- --filter=blob:none` の後に `git -C <一時ディレクトリ> checkout 1f2aadb`）、次を比較する。

- `pigs.json`・`pixg.json` は移植元と同一（`cmp` が 0）
- `pigs`・`pixg`・`pi-superagents-exec.zsh` の移植元との差分は、setup の案内のパス（`scripts/` と `.devcontainer/`）と、ヘルパのコメント 1 行（利用者の `--tui-mode` が勝つことの説明）だけ

- [ ] **Step 5: 自己レビューをする**

`git diff origin/main...HEAD` を読み、Spec 7 章の受け入れ条件を 1 つずつ照合する。Critical・Important の指摘があれば直してからコミットし、Step 1〜3 をやり直す。

- [ ] **Step 6: push して PR を作る**

```bash
git push -u origin feat/issue-20-pi-launchers
gh pr create --base main --head feat/issue-20-pi-launchers \
  --title "feat(pi): ランチャーを regular の TUI で起動し、pigs・pixg の tier を移植元に揃える（#20）" \
  --body-file <PR 本文のファイル>
```

PR 本文には、概要、変更点（Task 1〜3）、判断事項の要点（D-2・D-3・D-5・D-8・D-9）、検証結果（実際の出力）、既存環境への反映手順（Spec 4.6 節）、未検証の項目（rebuild と実認証は #22 と別枠）、`Closes #20` を書く。既存の PR があれば作らずに再利用する。

- [ ] **Step 7: #20 に作業報告を書く**

#20 のコメントに、`implementation: done`、PR の URL、コミット、検証結果、所要時間（Task ごとの内訳）、未検証の項目を書く。親 #17 の実行ボードは書き換えない（調整役の担当）。
