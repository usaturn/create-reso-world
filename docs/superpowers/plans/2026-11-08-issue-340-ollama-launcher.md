# Issue #340 Ollama Cloud ランチャー（ccdol）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `zshrc.txt` に `claude-ollama` / `ccdol` を足し、Claude Code を Ollama Cloud の `deepseek-v4.1-flash:1017` で起動できるようにする。

**Architecture:** 既存の `ccdd` と同じ形の zsh 関数を足し、共通の `cc_launcher_unsets` に `OLLAMA_API_KEY` を加える。テストは既存の `test-herdr-migration.bash` のランチャーのテストを広げ、キーの検査のテストを 1 件足す。README に起動・確認・制約の節を足す。

**Tech Stack:** zsh（`zshrc.txt`）、bash のテスト（偽の `claude` を PATH の先頭に置く）、Markdown

**Spec:** `docs/superpowers/specs/2026-11-08-issue-340-ollama-launcher-design.md`

- 状態: `draft`（issue-to-pr の run。内容の承認ではない）

## Global Constraints

- 接続先は `ANTHROPIC_BASE_URL="https://ollama.com"`。ローカルの Ollama は使わない
- 認証は `ANTHROPIC_AUTH_TOKEN="$OLLAMA_API_KEY"`。`ANTHROPIC_API_KEY` は子に渡さない（共通の unset で外したまま、代入しない）
- 4 つの tier（`ANTHROPIC_DEFAULT_FABLE_MODEL`・`_OPUS_`・`_SONNET_`・`_HAIKU_`）すべてに `deepseek-v4.1-flash:1017[1m]`
- `CLAUDE_CODE_EFFORT_LEVEL=max`、`CLAUDE_CODE_MAX_OUTPUT_TOKENS=65536`、`ENABLE_CLAUDEAI_MCP_SERVERS=false`
- 起動は `claude --model opus "${opts[@]}" "$@"`。`ccdol` だけが `--dangerously-skip-permissions` を付け、`claude-ollama` は付けない
- `OLLAMA_API_KEY` が未設定・空・空白だけなら、値を表示せずに標準エラーへ固定の文を出し、`return 1` で `claude` を起動しない。`${X:?}`・`[[ -z $X ]]` は空白を通すので使わない
- テストは「テストの採用基準」（ルートの `AGENTS.md`）に従う。足すのは S と既存の F∩S の更新だけ。model ID・effort・出力上限・README の文言を照合するテストは足さない
- テストは実 key・課金 API を使わない。偽の値は `fake-ollama` のような名前にする（秘密情報の検査に当たらない値）
- 文書は AGENTS.md の「日本語表現」に従う

## 受け入れ基準

Spec の「受け入れ条件と防御範囲」を基準とする。Task の brief とレビューの brief には、この節をそのまま写す。

- **動作環境:** Ubuntu 26.04 LTS の Dev Container。テストは `zsh -f` で `.devcontainer/zshrc.txt` を読み、偽の `claude`（PATH の先頭）が受け取った環境変数と argv を記録する。実 API の確認は、Herdr の pane の対話 zsh（利用者の `~/.zshrc` が `OLLAMA_API_KEY` を export している）に worktree の `zshrc.txt` から取り出した `cc_launcher_unsets` と `ccdol` を読み込み、Claude Code 2.1.319 で行う
- **実入力:**
  - キー: 偽の値 `fake-ollama`、空白 1 文字 `' '`、空、未設定（テストは空白 1 文字を使う。空白を除いて空かで判定するので、空・未設定・タブ・改行だけの値も同じ経路で止まる）
  - 親シェルの汚染: `cc_launcher_unsets` の各変数を `POLLUTED_<名前>` で export した状態
  - 引数: `probe`（テスト）、空白と改行を含むプロンプト（例: `$'line one\nline two  with  spaces'`）と `-p`（統合の確認）
- **防御範囲:**
  - 対象: `ccdol`・`claude-ollama` の送り先 `https://ollama.com`、`ANTHROPIC_AUTH_TOKEN` への key の受け渡しと `ANTHROPIC_API_KEY` の不在、省略フラグは `ccdol` だけ、MCP の無効化、空白だけの key での停止（`claude` を起動しない・非 0）、`ccdd`・`ccddg`・`ccdu`・`ccdol` の子への `cc_launcher_unsets` の変数（`OLLAMA_API_KEY` を含む）の漏れの防止
  - 正しく通る反例: 偽の key `fake-ollama` では `ccdol`・`claude-ollama` が `claude` を起動し、`ANTHROPIC_AUTH_TOKEN=fake-ollama` になる。`claude-ollama` は省略フラグを付けない
  - 対象外: `settings.json` での接続先の切り替え、Ollama の CLI・daemon、agent-runner への登録、Pi 向けのランチャー、1M に近い長さの会話

## 要件の対応（実装前の照合）

| Spec の条件 | 担当 | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1. `/status` の表示 | Task 3（司令塔） | `Anthropic base URL: https://ollama.com`、`Model: opus (deepseek-v4.1-flash:1017[1m])`、`Auth token: ANTHROPIC_AUTH_TOKEN` | Herdr の pane で `ccdol` を対話で起動して `/status` を読む |
| 2. key が無いときの停止 | Task 1 | 非 0、偽の `claude` が起動しない、標準エラーに値が出ない | `test_ollama_launcher_requires_key`。空白だけを止めない書き方（`[[ -z $OLLAMA_API_KEY ]]`）に一時的に変えると失敗することも確かめる |
| 3. 子への漏れの防止 | Task 1 | 4 つの子の環境に `POLLUTED_` が無く、`OLLAMA_API_KEY=` が無い。`ccdol` の子は `ANTHROPIC_AUTH_TOKEN=fake-ollama` | `test_cc_launcher_env_unsets`（`expected_unsets` の完全一致を含む） |
| 4. 引数の受け渡し | Task 3（司令塔） | 偽の `claude` の argv の末尾が、渡した引数と 1 対 1 で同じ | 一時的な確認（コミットしない）と、実 API の `-p` の実行 |
| 5. 固定値のテストを足さない | Task 1・Task 2 のレビュー | 足したテストが S・F∩S だけ | 差分のレビュー |
| 6. 既存の検査 | Task 3（司令塔） | 3 つのコマンドが終了コード 0 | `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` |
| 7. 実 API の確認 | Task 3（司令塔） | 応答の成功、stream-json の部分メッセージ、thinking のブロック、Read・Bash の結果の後の応答、サブエージェントの起動 | 実 API の `-p` を 1 回（stream-json） |
| README の更新 | Task 2 | Spec の決定記録の「README」の節と項目がそろう | 差分のレビュー、Markdown の表と参照の目視 |

共有する条件: `cc_launcher_unsets` の一覧（`zshrc.txt`）と `expected_unsets`（テスト）は同じ集合で、Task 1 の中で一緒に変える。README（Task 2）の値は Task 1 の関数と同じでなければならず、Task 3 の統合の確認で司令塔が照合する。

## Review Focus

テストで固定しないが、使う人が出会いやすい入力。どれも「テストの採用基準」で新しいテストに当たらないので、下の担当で確かめる。

- 空白・改行を含むプロンプト: 分割・欠落せずに 1 つの引数として届く（Task 3 の一時的な確認）
- タブ・改行だけの `OLLAMA_API_KEY`: `[[:space:]]` で除くので空白と同じく止まる（Task 1 の Step 7 の一時的な確認）
- 利用者が追加で `--model sonnet` などを渡す: ランチャーの既定の引数の後に渡り、4 つの tier が同じモデルなので接続先は変わらない（Task 3 の一時的な確認で argv の順序を見る）
- 親シェルの `OLLAMA_API_KEY`: `ccdol` を実行した後も親シェルの値は変わらない（`env` で子だけに設定するので、既存の `ccdd` の確認と同じ形。Task 3 の一時的な確認）
- `settings.json` の `env` に `ANTHROPIC_*` がある環境: シェルの値より優先される（README の案内だけ。Task 3 の `/status` で、この環境に無いことも見る）

---

### Task 1: `ccdol` ランチャーと認証情報の守り（zshrc とテスト）

**Files:**
- Modify: `.devcontainer/zshrc.txt`（`cc_launcher_unsets` のコメントと配列、`claude-deepinfra-glm ccddg` の直後に `claude-ollama ccdol` を追加）
- Test: `.devcontainer/test-herdr-migration.bash`（`test_cc_launcher_env_unsets`・`test_cc_launcher_destination_and_exit_status` の変更、`test_ollama_launcher_requires_key` の追加）

**テストの要否:** 要る。資格情報の送り先・子への漏れ・空白の key での claude.ai の認証情報の送信は、壊れてもエラーにならない S。`expected_unsets` は既存の F∩S の更新。model ID などの固定値はテストしない。

**Interfaces:**
- Consumes: 既存の `cc_launcher_unsets`、`run_zshrc_code`、`make_stub_home`、`make_claude_probe`、`assert_contains`、`assert_absent`
- Produces: zsh 関数 `claude-ollama` / `ccdol`（引数はそのまま `claude` に渡す。key が無ければ終了コード 1）。Task 2 の README はこの関数の値を説明する

- [ ] **Step 1: `test_cc_launcher_env_unsets` を変える（失敗するテスト）**

  - コメントのランチャー名を `ccdd / ccddg / ccdu / ccdol` にする
  - `expected_unsets` の `DEEPINFRA_TOKEN` の次に `OLLAMA_API_KEY` を足す
  - `env_args` に `OLLAMA_API_KEY=fake-ollama` を足し、`POLLUTED_` を入れない `case` の入力元の key に `OLLAMA_API_KEY` を足す
  - 2 つの `for fn in ccdd ccddg ccdu` を `for fn in ccdd ccddg ccdu ccdol` にし、`source_key` の一覧に `OLLAMA_API_KEY` を足す
  - 最後の裏付けに `assert_contains "${dump_dir}/ccdol.log" '^ANTHROPIC_AUTH_TOKEN=fake-ollama$'` を足す

- [ ] **Step 2: `test_cc_launcher_destination_and_exit_status` を変える（失敗するテスト）**

  - 対象を `ccdd ccddg ccdu ccdol claude-deepinfra claude-deepinfra-glm claude-opencode-union claude-ollama` にし、`run_zshrc_code` に `OLLAMA_API_KEY=fake-ollama` を足す
  - Python の照合を次の意味にする（`ollama = name in ("ccdol", "claude-ollama")`）

    ```python
    if name in ("ccdd", "ccddg", "ccdu", "ccdol"):
        assert skip in argv[:-1], (name, argv)
    else:
        assert skip not in argv, (name, argv)
    # ollama: BASE_URL == "https://ollama.com", AUTH_TOKEN == "fake-ollama", API_KEY is None
    # union / deepinfra: 既存のまま
    assert env["ENABLE_CLAUDEAI_MCP_SERVERS"] == "false"
    ```

  - 上のコメント（F∩S の説明）のランチャー名に `ccdol`・`claude-ollama` を足し、送る資格情報の例に `OLLAMA_API_KEY` を足す

- [ ] **Step 3: `test_ollama_launcher_requires_key` を足す（失敗するテスト）**

  `test_cc_launcher_destination_and_exit_status` の後に置き、末尾の実行の並びの `test_cc_launcher_destination_and_exit_status` の次で呼ぶ。中身（移植元と同じ）:

  ```bash
  # S: ccdol は OLLAMA_API_KEY が無いとき、子 claude を起動せずに失敗する。
  # Claude Code は ANTHROPIC_AUTH_TOKEN が空か空白だけだと、保存済みの claude.ai の OAuth トークンを
  # 接続先へ送る。このガードが外れても起動は成功し、claude.ai の認証情報が ollama.com に送られる。
  # 入力は空白だけの 1 件にする。空だけを止める書き方（[[ -z ... ]]・${X:?}）は空白を通すので、
  # この 1 件で空・未設定を止め損ねる誤りも分かる。正しい key で起動する例は送り先のテストにある。
  test_ollama_launcher_requires_key() {
      local test_home="${TEST_ROOT}/home-ollama-key"
      make_stub_home "$test_home"
      local log="${TEST_ROOT}/ollama-key-claude.log"
      : > "$log"
      printf '%s\n' '#!/bin/sh' 'echo started >> "$HERDR_TEST_CLAUDE_DUMP"' > "$test_home/bin/claude"
      chmod +x "$test_home/bin/claude"

      local rc=0
      run_zshrc_code "$test_home" \
          'source "$ZSHRC_TEMPLATE" >/dev/null 2>&1; ccdol probe' \
          HERDR_TEST_CLAUDE_DUMP="$log" OLLAMA_API_KEY=' ' 2>/dev/null || rc=$?
      [ "$rc" -ne 0 ] || fail 'ccdol must fail when OLLAMA_API_KEY is blank'
      [ ! -s "$log" ] || fail 'ccdol must not start claude when OLLAMA_API_KEY is blank'
  }
  ```

- [ ] **Step 4: テストが失敗することを確かめる**

  Run: `bash .devcontainer/test-herdr-migration.bash`
  Expected: 非 0。`cc_launcher_unsets must match expected_unsets exactly` で止まる（`OLLAMA_API_KEY` が配列に無い）

- [ ] **Step 5: `zshrc.txt` を変える**

  - `cc_launcher_unsets` の上のコメントのランチャー名を `ccdd / ccddg / ccdu / ccdol` にし、配列の `-u DEEPINFRA_TOKEN` の次に `-u OLLAMA_API_KEY` を足す
  - `claude-deepinfra-glm ccddg` の関数の直後（`ccdu` の説明のコメントの前）に次を足す（値は Global Constraints のとおり）

    ```zsh
    # Ollama Cloud の DeepSeek-V4.1-Flash-1017 で Claude Code を起動する（#340、移植元 agent-workspace#852）。
    # [1m] は Claude Code に 1M のコンテキストとして扱わせる印で、Ollama へ送る model ID からは外れる。
    # 付けないと未知のモデルとして 200K と見なす。変数ごとに読むので 4 つの tier すべてに付ける。
    function claude-ollama ccdol () {
      local model='deepseek-v4.1-flash:1017[1m]'
      local -a opts
      [[ $funcstack[1] == ccdol ]] && opts=(--dangerously-skip-permissions)
      # Claude Code は ANTHROPIC_AUTH_TOKEN が空か空白だけだと、保存済みの claude.ai の
      # OAuth トークンを接続先へ送る。空白を除いて空なら claude を起動しない（値は表示しない）。
      if [[ -z ${${OLLAMA_API_KEY:-}//[[:space:]]/} ]]; then
        print -u2 -- "${funcstack[1]}: OLLAMA_API_KEY is not set or empty; create a key at https://ollama.com/settings/keys and export it in this shell"
        return 1
      fi

      env "${cc_launcher_unsets[@]}" \
        ANTHROPIC_BASE_URL="https://ollama.com" \
        ANTHROPIC_AUTH_TOKEN="$OLLAMA_API_KEY" \
        ANTHROPIC_DEFAULT_FABLE_MODEL="$model" \
        ANTHROPIC_DEFAULT_OPUS_MODEL="$model" \
        ANTHROPIC_DEFAULT_SONNET_MODEL="$model" \
        ANTHROPIC_DEFAULT_HAIKU_MODEL="$model" \
        ENABLE_CLAUDEAI_MCP_SERVERS=false \
        CLAUDE_CODE_EFFORT_LEVEL=max \
        CLAUDE_CODE_MAX_OUTPUT_TOKENS=65536 \
        claude --model opus "${opts[@]}" "$@"
    }
    ```

- [ ] **Step 6: テストが通ることを確かめる**

  Run: `bash .devcontainer/test-herdr-migration.bash`
  Expected: 終了コード 0、最後の行が `PASS: herdr Dev Container migration`

  Run: `zsh -n .devcontainer/zshrc.txt && bash -n .devcontainer/test-herdr-migration.bash`
  Expected: 終了コード 0

- [ ] **Step 7: キーの検査のテストが弱い書き方を捕まえることを一時的に確かめる（コミットしない）**

  - `zshrc.txt` の `[[ -z ${${OLLAMA_API_KEY:-}//[[:space:]]/} ]]` を一時的に `[[ -z $OLLAMA_API_KEY ]]` に変えて `bash .devcontainer/test-herdr-migration.bash` を実行し、`ccdol must not start claude when OLLAMA_API_KEY is blank` で非 0 になることを確かめる
  - 元に戻し、`git diff` でその行が Step 5 のとおりであることを確かめてから、同じテストが終了コード 0 になることを確かめる
  - `test_ollama_launcher_requires_key` の入力 `OLLAMA_API_KEY=' '` を一時的に `OLLAMA_API_KEY=$'\t\n'` に変えて同じテストが終了コード 0 になることを確かめ、元に戻す
  - 実 HOME・実 PATH で `zshrc.txt` 全体を `source` しない（読み込み時に `workspace_periodic_cleanup` と `herdrstart` が動く）。`zshrc.txt` を読む確認は、テストの `run_zshrc_code`（偽の HOME・PATH）を通す

- [ ] **Step 8: Commit**

  ```bash
  git add .devcontainer/zshrc.txt .devcontainer/test-herdr-migration.bash
  git commit -m "feat(devcontainer): add claude-ollama / ccdol launcher for Ollama Cloud (#340)"
  ```

### Task 2: README の更新

**Files:**
- Modify: `.devcontainer/README.md`

**テストの要否:** 要らない。文書の文言は「テストの採用基準」の F。差分のレビューと、表・節の参照の目視で確かめる。

**Interfaces:**
- Consumes: Task 1 の `claude-ollama` / `ccdol` の値（Global Constraints のとおり）
- Produces: README の節 `### Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）`（ほかの節から「Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）」の名前で参照する）

- [ ] **Step 1: 一覧と数を更新する**

  - 「導入ツール一覧」の Claude Code の行の起動名に `ccdol` を足す（`ccdd`、`ccddg`、`ccdu`、`ccdol`）
  - 「Claude Code の起動と更新」の第三者プロバイダの表に次の行を足す: `claude-ollama` / `ccdol` | Ollama Cloud（`https://ollama.com`） | `deepseek-v4.1-flash:1017[1m]` | `deepseek-v4.1-flash:1017[1m]` | `OLLAMA_API_KEY`
  - 表の後の段落に、Ollama Cloud は 4 つの tier すべてに同じモデルを割り当てることと、詳しくは「Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）」にあることを足す
  - 「3 つのプロバイダ関数」を「4 つのプロバイダ関数」にする

- [ ] **Step 2: 「API トークン」節に `OLLAMA_API_KEY` を足す**

  `DEEPINFRA_TOKEN` の項目の後に足す。内容: Claude Code の `ccdol`・`claude-ollama` だけが読む。「秘密情報」の env ファイルには書かず、使うシェルで export する。子の `claude` には `ANTHROPIC_AUTH_TOKEN` としてだけ渡し、`ccdd`・`ccddg`・`ccdu` の子には渡さない。未設定・空・空白だけなら、値を表示せずにエラーを出して起動を止める。キーは `https://ollama.com/settings/keys` で作る。詳しくは「Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）」。「秘密情報」の節の env ファイルの例の変数一覧には足さない

- [ ] **Step 3: 「Claude Code の起動と更新」の直後（`## 非対話エージェントのランナー（agent-runner）` の前）に `### Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）` を足す**

  下位の見出しは `####`。移植元（usaturn/agent-workspace PR #855 の README の「Ollama Cloud の DeepSeek V4.1 Flash 1017 で Claude Code を起動する（#852）」）を、本リポジトリの書き方に合わせて取り込む。次の内容をすべて含め、ほかは足さない（移植元の「動作の確認」の節は写さない）。

  1. 導入: `claude-ollama` / `ccdol` は接続先を Ollama Cloud の Anthropic 互換 API に切り替えて起動する（#340、移植元 usaturn/agent-workspace#852）。ローカルの Ollama は使わず `https://ollama.com` に直接つなぐ。`ccdol` だけが `--dangerously-skip-permissions` を付ける。後ろの引数（`-p` やプロンプト）はそのまま `claude` に渡す
  2. 値の表: 接続先、認証（Bearer。cloud endpoint は `x-api-key` だけでは受け付けない。`ANTHROPIC_API_KEY` は子に渡さない）、model ID（4 つの tier すべてに `deepseek-v4.1-flash:1017[1m]`）、effort `max`、出力上限 65,536、`ENABLE_CLAUDEAI_MCP_SERVERS` が `false`、API キーの作成先 `https://ollama.com/settings/keys`
  3. model ID の選び方: 版を固定した `:1017` を使う。無印の `deepseek-v4.1-flash` は別の digest を指しうる。`:cloud`・`:1017-cloud` は Ollama の CLI・アプリ向けの名前なので直接接続では使わない
  4. `#### 起動`: 使うシェルで `export OLLAMA_API_KEY="..."` してから `ccdol`。既存のコンテナは rebuild するか、「Claude Code の起動と更新」の手順で `~/.zshrc` に反映する。key が未設定・空・空白だけなら値を表示せずにエラーを出して `claude` を起動しない（終了コード 1）。理由（Claude Code は `ANTHROPIC_AUTH_TOKEN` が空か空白だけだと、保存済みの claude.ai の OAuth トークンを接続先へ送る）
  5. `#### 接続先の確認`: `/status` で `Anthropic base URL: https://ollama.com`、`Model: opus (deepseek-v4.1-flash:1017[1m])`、`Auth token: ANTHROPIC_AUTH_TOKEN` を確かめる。`~/.claude/settings.json` やプロジェクトの `.claude/settings.json`・`.claude/settings.local.json` の `env` に `ANTHROPIC_BASE_URL`・`ANTHROPIC_AUTH_TOKEN`・`ANTHROPIC_DEFAULT_*_MODEL` などがあるとシェルの値より優先されるので、`/status` が違うときはまずそこを見る
  6. `#### 1M のコンテキスト`: コンテキスト長は 1,048,576。Claude Code は知らないモデル名を 200K と見なすので 4 つの tier すべてに `[1m]` を付ける。`[1m]` は 1M として扱う印で、Ollama へ送る model ID からは外れる。`/status`・`/context`・起動画面に付く `[1m]` はこの印。変数ごとに読まれるので、1 つでも外すとその tier だけ 200K。`/context` は 1M を分母にする（例: `37k/1m tokens`）。自動の compact は 1M に近づいたときに起きる。prompt caching が無いので会話が長いほど毎回の入力が大きくなる。早めに compact したいときは `CLAUDE_CODE_AUTO_COMPACT_WINDOW` を前に付けて起動する（例: `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000 ccdol`）
  7. `#### effort と出力上限`: effort は `max`。Ollama はモデルのメタデータにある名前（このモデルは `low`・`high`・`max`）ならそのまま、無い名前はモデルの既定（`high`）にする。`/effort` で `medium`・`xhigh` などに変えると `high` として扱われる。65,536 は運用上の上限でサービスの最大値ではない（移植元が実 API で受け付けられると確かめた値）。指定しないと Claude Code は 32,000 を送るが、`max` では thinking も上限に数えるので長い出力が途中で切れうる
  8. `#### 対応していない機能`: `/v1/messages/count_tokens`（Claude Code は 404 を受けて推定に切り替えるので、`/context` などのトークン数は推定値）、prompt caching（`cache_control`。拒否されないが効かない）、`tool_choice`・`metadata`・Batches API・citations・PDF の `document` ブロック・URL で指定した画像（Base64 は使える）・ストリーミング中の `error` イベント（エラーは HTTP のステータスで返る）、thinking の `budget_tokens`（受け付けるが上限として効かない）。Ollama の Claude Code 連携の手順は、WebSearch などのサーバー側のツールや細かいツールの制御に完全には対応していないとしている。`-p` で起動すると標準エラーに `[claude-code:unrecognized_model] {"model":"deepseek-v4.1-flash:1017[1m]",...}` が 1 行出るが、知らないモデル名を使ったことの通知で、応答は成功する

- [ ] **Step 4: 確かめる**

  Run: `git diff --stat` と `git diff .devcontainer/README.md`
  Expected: README だけが変わり、上の 3 つの Step の箇所だけが変わる。表の列数が既存の行とそろう。節の参照名「Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）」が新しい見出しと一致する

  Run: `bash scripts/check-layout.sh`
  Expected: 終了コード 0

- [ ] **Step 5: Commit**

  ```bash
  git add .devcontainer/README.md
  git commit -m "docs(devcontainer): document ccdol launcher for Ollama Cloud (#340)"
  ```

### Task 3: 統合の確認（司令塔）

**Files:** 変更しない（記録は `PARENT_ROOT` の `tmp/agents/` のセッションディレクトリ）

**テストの要否:** 要らない（新しいテストを書かない）。受け入れ条件 1・4・6・7 を、実行と実 API の確認で確かめる。

- [ ] **Step 1:** README の値（Task 2）と `zshrc.txt` の関数（Task 1）を照合する（URL、認証の変数、model ID、effort、出力上限、MCP、省略フラグ、終了コード）
- [ ] **Step 2:** 引数の受け渡しを一時的に確かめる。テストと同じく偽の HOME・PATH の `zsh -f` で `zshrc.txt` を読み、偽の `claude`（argv を JSON で出す）を PATH の先頭に置き、`ccdol -p $'line one\nline two  with  spaces' --model sonnet` の argv の末尾が `-p`・そのままの文字列・`--model`・`sonnet` の 4 つで、ランチャーの既定の引数（`--model opus`・`--dangerously-skip-permissions`）の後にあることを見る。実行後に親シェルの `OLLAMA_API_KEY` が変わっていないことも見る
- [ ] **Step 3:** 既存の検査を同期実行する: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。終了コードとログのパスを記録する
- [ ] **Step 4:** 実 API の `-p` を 1 回実行する。Herdr の新しい pane（`--no-focus`）で、一時ディレクトリ（無害なファイル `note.txt` だけを置く）を cwd にし、`zshrc.txt` から `typeset -a cc_launcher_unsets=(`〜`)` と `claude-ollama ccdol` の関数だけを取り出したファイルを読み込んでから（`zshrc.txt` 全体は読まない。読み込み時に `workspace_periodic_cleanup` と `herdrstart` が動く）、`ccdol -p --output-format stream-json --verbose --include-partial-messages '<Read で note.txt を読み、Bash で wc -l note.txt を実行し、サブエージェント（Agent ツール）に note.txt の 1 行目を答えさせ、結果をまとめる依頼>'` を実行する。標準出力（JSONL）と標準エラーをファイルに残し、`stream_event` の部分メッセージ、thinking のブロック、`tool_use`（Read・Bash・Agent）とその `tool_result` の後の assistant の応答、`result` の成功、標準エラーの `unrecognized_model` の通知を確かめる。一時的なエラーのときだけ 1 回やり直す
- [ ] **Step 5:** 同じ pane で `ccdol` を対話で起動し、`/status` の表示を読んでから終了する（プロンプトは送らない）。pane は自分で作ったものだけを閉じる
- [ ] **Step 6:** 結果を PR 本文に書く。確かめられなかった項目があれば、その旨と確認手順を書き、PR の Issue の指定を `Refs #340` にする

## 実行方式

`implement_task.py check --implement claude-code_sonnet_default` が `self: false`、担当 `claude-code_sonnet_default`、`fallback` は空を返したので、issue-to-pr の 4 章の「Task の実装を runner の担当に依頼する」に従い、`superpowers:subagent-driven-development` の形で Task 1・Task 2 を 1 つずつ順に runner の担当に依頼する（並行しない。同じ worktree に続けて取り込むため）。Task 3 は Herdr の pane・実 API を使うので司令塔が行う。各 Task の後に司令塔が Task のレビューを行い、最後にブランチ全体のレビューを行う。

SDD の作業領域は `PARENT_ROOT/tmp/agents/issue-340.exiarxw6/sdd/2026-11-08-issue-340-ollama-launcher/`（ledger は `progress.md`）。依頼の出力先は `agent_tmp.py mkdir issue-340-implement` で作るセッションディレクトリの下に、依頼ごとに作る。

## 実行予算

- Issue 全体の能動時間の予算: 420 分（ledger `PARENT_ROOT/tmp/agents/issue-340.exiarxw6/budget.jsonl`）。根拠: Task は 3 つ（うち runner の依頼 2 つ）で変更は小さいが、`--merge` のループ（サイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 30 分）＝ 最大 225 分）を含む
- phase の目安: 準備・Spec・Plan 45 分、Task 1 30 分、Task 2 30 分、Task 3 40 分、PR 15 分、ループ 225 分まで
- worker: runner の `implement` の役割の期限 90 分（runner が強制する）。司令塔は `run_in_background` の完了通知で待ち、無進捗の打ち切りは runner の期限に任せる
- 再試行の上限: 同じ失敗の signature は 1 回まで。`retry`・`rejected` の依頼し直しは Task ごとに 1 回まで（依頼は最大 2 回）。Task のレビューの指摘の修正の依頼は Task ごとに 2 回まで。実 API の一時的なエラーは 1 回だけやり直す。`failed` はやり直さずに止まる
- checkpoint: 各 phase の境界、予算の 50%（210 分）・100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補: README は Issue が挙げる項目に絞る（既に絞ってある）。実 API の確認が通らないときは、未確認として確認手順を PR に書き `Refs #340` にする（縮小）。runner の担当が止まったときは、自分で引き取らずに止まって報告する（担当の変更は利用者が決める）

## contingency（代替策）

- Task 1 の Step 4 の RED が想定と違う（例: 別の理由で失敗する、失敗しない）: 原因を確かめ、仕様の意味を保つ最小の修正なら ledger に残して続ける。テストの意味が変わるなら止まる
- zsh の `${${OLLAMA_API_KEY:-}//[[:space:]]/}` が想定どおりに動かない: 同じ意味（空白を除いて空なら止める）の別の zsh の書き方に変え、ledger に残す。空だけを止める書き方には変えない
- `run-tests.bash` が変更と無関係に失敗する: base（`25b7b5a0`）のベースラインのログ（`PARENT_ROOT/tmp/agents/issue-340.exiarxw6/baseline/`）と比べ、base でも同じなら既存の失敗として PR に書く。変更による失敗なら `systematic-debugging` で直す
- 実 API で 404・モデルが見つからない: model ID の変更は仕様の意味を変えるので直さず、未確認として PR に書き `Refs #340` にする
- `/status` が想定と違う: `settings.json` の `env` を確かめる。`zshrc.txt` の関数の誤りなら Task 1 の担当に修正を依頼する
- runner の依頼が `failed`、再試行の上限に達した `retry`・`rejected`: その Task で止まり、後の Task・PR に進まない

## 完了

状態は `draft` のまま（issue-to-pr の run。内容の承認ではない）。検証の結果は、最後の commit の後に実行して PR 本文に書く。

### 実行の経緯

| 対象 | 担当・依頼の回数 | commit | レビュー |
| --- | --- | --- | --- |
| Task 1 | `claude-code_sonnet_default`（観測したモデル `claude-sonnet-5-5`）。2 回（1 回目は `rejected`、2 回目に取り込み） | `b8808e86` | Spec ✅・Approved（Minor 3 件は持ち越し） |
| Task 2 | 同じ担当。1 回＋レビューの指摘の修正 1 回 | `96e03a7c`、`c19b460a` | Important 1 件 → 修正 1 回目で解消 |
| ブランチ全体のレビュー | 同じ担当に修正を 1 回依頼 | `4a474c60` | With fixes（Important 1 件・Minor 3 件）→ 再レビューで解消。新しい Minor 1 件は持ち越し |
| Task 3 | 司令塔 | なし | — |

- Task 1 の 1 回目は、runner の実行中に別のセッションが別の worktree（`.worktrees/tools-photo-offset-docs`）に commit したため `outside_changes` で `rejected` になった。担当の変更は許可した 2 ファイルだけだったので、上限内で 1 回だけ依頼し直した
- Task 1 の Step 7 の弱いガードへの変異では、テストは `ccdol must fail when OLLAMA_API_KEY is blank` で止まった（偽の claude が 0 で終わるので、Plan が書いた `must not start claude` より先の文で止まる）。どちらの文でも合格とする裁定を事前に記録した
- Task 2 のレビューで、「秘密情報」節が `MESHY_API_KEY` 以外のトークンを env ファイルに置くよう定めたままだと `OLLAMA_API_KEY` の案内と食い違うと分かった。Task 2 の Step 4 の範囲の制限を裁定で広げ、「秘密情報」節の例外の文と「API トークン」節の冒頭も直した（Spec の決定記録「キーの置き場所の案内」に反映）
- ブランチ全体のレビューで、起動例の `export OLLAMA_API_KEY="..."` が key を端末と pane のスクロールバックに残すと分かった。`MESHY_API_KEY` と同じ非表示入力（`read -rs`）にした（同上）。あわせて、「API トークン」節の冒頭の読み違い、prompt caching の因果の説明、第三者プロバイダの表の前置き（Ollama の採否の記録先）を直した

### Task 3（統合の確認）

- Step 1: README の値と関数の値（URL、認証の変数、4 つの tier の model ID、effort、出力上限、MCP、省略フラグ、終了コード 1）は一致した（Task 2 のレビューとブランチ全体のレビューで照合）
- Step 2: 偽の claude で、`ccdol -p $'line one\nline two  with  spaces' --model sonnet` の argv は `--model opus --dangerously-skip-permissions -p <1 つの引数> --model sonnet` だった。親シェルの `OLLAMA_API_KEY` は変わらず、子には残らなかった
- Step 4: 実 API の `-p` を 1 回（やり直しなし）。成功（4 turns）。stream-json の部分メッセージ（`thinking_delta`・`text_delta`）、thinking のブロック、Read・Bash・Agent の結果を受けた継続、サブエージェントの中の Read を確かめた。応答の model は `deepseek-v4.1-flash:1017`（`[1m]` は送られていない）。標準エラーに `unrecognized_model` の通知が 1 行出た
- Step 5: 対話の `/status` は `Auth token: ANTHROPIC_AUTH_TOKEN`、`Anthropic base URL: https://ollama.com`、`Model: opus (deepseek-v4.1-flash:1017[1m])` だった

### PR #342 のレビュー修正

- PR の 1 回目のレビュー（gpt-6.1-sol の M-1）で、ガードの `[[:space:]]` が NBSP・BOM・U+202F（C ロケールでは U+3000・U+2028 も）を除かず、Claude Code が trim で空とみなすキーで claude を起動すると分かった。ガードを `[[ ${OLLAMA_API_KEY:-} != *[A-Za-z0-9]* ]]`（ASCII の英数字を 1 文字も含まなければ起動しない）に、テストの入力を `$' \xc2\xa0\xef\xbb\xbf'` に変えた（`0665a44d`）。上の Task 1 のガード・テストの入力・エラー文は、実行したときの版である。経緯は `docs/superpowers/specs/2026-11-08-issue-340-ollama-launcher-review-fixes-design.md`

### 持ち越し（マージの後に再調査する候補）

- 既存の `ccdd`・`ccddg` の `${DEEPINFRA_TOKEN:?…}` と、`ccdu` の `:-` の連鎖は、空白だけの値を通す（この Issue の範囲の外。`ccdol` と同じ種類の損害のおそれ）
- README の起動例のコードフェンスが `bash` のまま（例は zsh の構文。`ccdol` は zsh の関数）
- README の文言の小さな点（「変数ごとに読まれるので」の主語、Ollama の連携の手順の文、長い行の改行の位置）
