# Issue #408: プロバイダ切替ランチャーのセッションで ANTHROPIC_AUTH_TOKEN から各プロバイダの key を補い、Ollama の runner agent を追加する

## 管理・実行許可

- 状態: `draft`（`issue-to-pr` スキルによる実行許可で進行。内容の承認（`approved`）にはせず、確認用コピー `scripts/superpowers-review-copy.sh` は作らない）
- 対象 Issue: `usaturn/create-reso-world#408`（https://github.com/usaturn/create-reso-world/issues/408）
  - タイトル: `プロバイダ切替ランチャーのセッションで ANTHROPIC_AUTH_TOKEN から各プロバイダの key を補い、Ollama の runner agent を追加する（agent-workspace #927 の問題範囲を全て取り込む）`
- 利用者の指示（原文引用）:
  ```text
  /issue-to-pr #408 --merge
  --design-review claude-code_opus_default
  --spec-review pi_opencode-go_deepseek4-flash_max
  --implement pi_opencode-go_deepseek4-flash_max
  --assign implement=pi_opencode-go_deepseek4-flash_max
  --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default
  途中でメインがマージされたら、追随して作業を止めずに続行してください。
  ```
- 許可された範囲:
  - 通常の設計判断は推奨案を選び、Spec 作成・コミット → 設計レビュー（`claude-code_opus_default`）→ Spec レビュー（`pi_opencode-go_deepseek4-flash_max`）→ Plan 作成・コミット → 指定された実装担当（`pi_opencode-go_deepseek4-flash_max`）への Task ごとの依頼とレビュー → ローカル検証および実機観測 → 秘密検査後の push・PR 作成 → PR 修正ループ（`--merge`、`finalize.py` によるマージと関連 Issue の記録更新）まで継続する。
  - **base 前進時の追随委任**: 利用者の明示指示「途中でメインがマージされたら、追随して作業を止めずに続行してください。」により、`recheck_bases` で `origin/main` の前進を検出した場合は停止せず、実行中の `agent_runner` が無ければ push 前は `git -C "$CODE_ROOT" rebase <new_sha>`、push 後は `git -C "$CODE_ROOT" merge --no-edit <new_sha>`（force push は行わない）で追随し、`$SESSION/code-base.json` の `sha` を更新して更新後のツリーで検証を再実行してから続行する。
- 作業ディレクトリとリポジトリ境界:
  - `PARENT_ROOT`: `/workspaces/reso-world`（`origin`: `https://github.com/usaturn/create-reso-world.git`）
  - `TARGET_REPO`: `usaturn/create-reso-world`（`DOCS_SEPARATE=false`。Spec・Plan・実装コードは同一 worktree・同一 PR に含める）
  - `CODE_ROOT` / `DOC_ROOT`: `/workspaces/reso-world/.worktrees/issue-408-launcher-key-derivation`（ブランチ `feat/issue-408-launcher-key-derivation`）
  - 捕捉した base: `repo="usaturn/create-reso-world"`、`remote="origin"`、`branch="main"`、`ref="refs/heads/main"`、`sha="c3a8e113c3af010fac94820266b93e107d6dbfaf"`（要求 base 無し）
  - セッション領域: `/workspaces/reso-world/tmp/agents/issue-408.kwkykzl6`
- 事前検査（Step 2 `check`）の記録:
  - `loop.py check-options`:
    - `options`: `max_cycles = 3`（既定の適用）、`template = "/workspaces/reso-world/.devcontainer/agent-runner.toml"`（既定の適用）、`config = null`（既定の適用）
    - `assignments.inspect`: `agents = ["devin_swe2_max", "pi_opencode-go_deepseek4-flash_max", "claude-code_opus_default"]`（利用者の `--assign` 指定）、`fallback = []`（個人設定 `/home/vscode/.config/agent-runner/config.toml` で保持）
    - `assignments["fix.implement"]`: `agents = ["pi_opencode-go_deepseek4-flash_max"]`（利用者の `--assign` 指定）、`fallback = []`
    - `assignments["fix.self-review"]`: `agents = ["self"]`（雛形の既定の適用）、`fallback = []`
    - `assignments["fix.fix-check"]`: `agents = ["self"]`（雛形の既定の適用）、`fallback = []`
    - 備考: 現在の司令塔セッションは Antigravity CLI（`agy`、モデル `Gemini 4 Carbon (Medium)`）で動作している。`PARENT_ROOT` の `loop.py start` は `--controller-runtime` の選択肢を `claude-code`・`devin`・`pi`・`codex`・`cursor` に限定しているため、PR 作成後の `loop.py start` 実行時点で別のランタイム名を偽装せず実際のランタイム名を渡す。`loop.py start` が終了コード 2 で拒否した場合は、`issue-to-pr` の想定された停止（ペイン名を維持）として作成済み PR の URL と再開手順を報告する。
  - `implement_task.py check --implement pi_opencode-go_deepseek4-flash_max`:
    - `agents = ["pi_opencode-go_deepseek4-flash_max"]`（利用者の `--implement` 指定）、`fallback = []`（個人設定で保持）、`self = false`
  - `review_design.py check --design-review claude-code_opus_default`:
    - `agents = ["claude-code_opus_default"]`（利用者の `--design-review` 指定）、`fallback = []`（個人設定で保持）、`self = false`
  - `review_spec.py check --spec-review pi_opencode-go_deepseek4-flash_max`:
    - `agents = ["pi_opencode-go_deepseek4-flash_max"]`（利用者の `--spec-review` 指定）、`fallback = []`（個人設定で保持）、`self = false`
- 先行条件・所有関係の確認（コメント `#issuecomment-6806157671`・`#issuecomment-6816243774`）:
  - 親 Issue・Sub Issues 無し（ボード外の follow-up）。#401（PR #405 マージ済み・CLOSED）、#347（CLOSED）、#359（PR #381 マージ済み）はいずれも先行条件を満たす。
  - Ollama の runner agent 2 件と `claude-ollama-exec` の取り込み（移植元 `usaturn/agent-workspace#860`）は #365 から本 Issue へ移管済みであり、#365 は本 Issue の完了後に直列化されている。
  - PR #405 が残した文書の食い違い 3 か所と、#401 から引き継いだ実機確認の残件（DeepInfra の wrapper 経由／wrapper 無しの比較、および通常シェルからの `claude-code_alibaba_opus_max`）を本 Issue の範囲に含める。

## 意図と防ぐ損害（S）

プロバイダ切替ランチャー（`ccda`・`ccdol`・`ccdd` / `ccddg`・`ccdgo`）が起動した Claude Code セッションでは、`cc_launcher_unsets` により親シェルの `MAAS_ANTHROPIC_TOKEN`・`OLLAMA_API_KEY`・`DEEPINFRA_TOKEN`・`OPENCODE_API_KEY` などが外され、動作中プロバイダの key だけが `ANTHROPIC_AUTH_TOKEN` として渡され、接続先が `ANTHROPIC_BASE_URL` に固定される。

本リポジトリは `MAAS_ANTHROPIC_TOKEN`・`OLLAMA_API_KEY` をどのファイルにも書かない方針（#397・#340）を採っており、また `~/.config/create-reso-world/env` が存在しないマシンでは `DEEPINFRA_TOKEN` などもファイルから補えない。そのため、ランチャー起動セッションから `tools/agent_runner/with_keys.py` 経由でランナーを起動してもプロバイダの key が届かず、環境変数の key を必要とする担当の起動が失敗する（移植元 `usaturn/agent-workspace#927` と同じ問題範囲）。

本変更では次の 2 点を同時に満たし、#927 の問題範囲を全て解決する。

1. `tools/agent_runner/with_keys.py` に、`ANTHROPIC_BASE_URL` の完全一致で識別したランチャーの `ANTHROPIC_AUTH_TOKEN` から、対応するプロバイダの key 1 変数だけを補う導出を導入する。
2. 移植元 `usaturn/agent-workspace#860` から `.devcontainer/claude-ollama-exec` と Ollama の runner agent 2 件（`claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max`）を取り込み、配置処理と文書を揃える。

守るべき「気付けない損害（S）」は次の 5 点である。

1. **異プロバイダへの誤導出（秘密情報の誤送信）**: `ANTHROPIC_BASE_URL` を確認せず、または部分一致・複数変数への展開で `ANTHROPIC_AUTH_TOKEN` を補うと、あるプロバイダの API key が別プロバイダのエンドポイントへ送られる。
2. **既存環境変数の上書き（意図しないアカウントでの課金・送信）**: 通常のシェル等で明示的に設定された非空の環境変数を `ANTHROPIC_AUTH_TOKEN` や env ファイルの値で上書きすると、エラーにならないまま別アカウントの key で外部通信が行われる。
3. **空白のみの key の通過（保存済み OAuth トークンの第三者送信・空白 key による優先順位の崩れ）**: `claude-ollama-exec` で ASCII 英数字を含まない空白（NBSP・BOM・全角空白を含む）の `OLLAMA_API_KEY` を通すと、Claude Code が `ANTHROPIC_AUTH_TOKEN` を trim して空とみなし、保存済みの `claude.ai` OAuth トークンを `https://ollama.com` へ送る。また `with_keys.py` が空白のみの `ANTHROPIC_AUTH_TOKEN` を導出すると、非空判定しか持たない後段（`pidid` や `pigod` の環境変数参照）に空白のみの値を渡してしまう。
4. **秘密値のログ・標準エラー・ファイルへの露出**: `MAAS_ANTHROPIC_TOKEN`・`OLLAMA_API_KEY` をファイルに保存したり、`with_keys.py` や `claude-ollama-exec` の標準エラー出力、ランナーの `result.json`・ログに key の実値を出したりすると秘密情報が残る。
5. **親環境の認証情報の残留**: `claude-ollama-exec` が親環境の `ANTHROPIC_API_KEY`・`CLAUDE_CODE_OAUTH_TOKEN`・`OLLAMA_API_KEY` 等を外さずに `claude` を起動すると、意図しない認証ヘッダーや環境変数が子プロセスやツール実行へ漏れる。

## 対象・対象外（編集禁止範囲）

### 追加・変更するファイル

- 変更: `tools/agent_runner/with_keys.py`（4 ランチャー分の URL 完全一致による `ANTHROPIC_AUTH_TOKEN` からの導出）
- 変更: `tools/agent_runner/tests/test_with_keys.py`（既存の代表テスト 1 件の拡張）
- 新規: `.devcontainer/claude-ollama-exec`（実行権限 `0755`、Ollama Cloud 向け Claude Code 起動ラッパー）
- 変更: `.devcontainer/install_beforehand.bash`（`claude-ollama-exec` の `~/.local/bin` への配置）
- 変更: `.devcontainer/agent-runner.toml`（`claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` の追加、および Alibaba 2 agent のコメント更新）
- 変更: `.devcontainer/test-herdr-migration.bash`（`test_ollama_exec_requires_key` の追加）
- 変更: `.devcontainer/README.md`（導出規則・プロバイダ別 key 解決表・Ollama runner agent・PR #405 が残した食い違い 3 か所・`auth.json` 注記の更新）
- 新規: 本 Spec（`docs/superpowers/specs/2026-11-12-issue-408-launcher-key-derivation-design.md`）および対応 Plan（`docs/superpowers/plans/2026-11-12-issue-408-launcher-key-derivation.md`）

### 対象外・編集禁止

- `MAAS_ANTHROPIC_TOKEN`・`OLLAMA_API_KEY` をファイルに置く方針変更、セッション引き継ぎファイルの作成、`keys.env`・`~/.zshrc` の読み取り。
- `.devcontainer/zshrc.txt` の変更（`cc_launcher_unsets` の変更や、`ccdol` 等のランチャー関数の意味・構造の変更は行わない。`ccdol` の薄いラッパー化を採らない理由は「決定記録 D4」を参照）。
- `tools/agent_runner` 本体（`runner.py`・`config.py`・`cli.py`・各 adapter・既存 agent の `env` allowlist・`[workflows]` の既定割り当て）の変更。
- `~/.pi/agent/auth.json`・`~/.pi/agent/models.json`・`~/.config/create-reso-world/env`・利用者個人の設定ファイルの変更。
- CommandCode の実 API 検証（サービス終了のため理論上のカバーのみ）、および `auth.json`・HOME 配下ログインで解決する既存担当（`pi_openai-codex_*`・`claude-code_opus_default`・`pi_opencode-go_*`・`pi_xai_*`・`pi_google-vertex_*`・`cursor_*`・`devin_*`）の個別実機試行の追加（`#issuecomment-6816243774`）。
- 過去の `docs/superpowers/` 文書や `.agents/skills/` 配下の既存スキルの変更。

## 詳細仕様

### 1. `tools/agent_runner/with_keys.py` の導出仕様

#### 1.1 マッピングと一致条件

モジュール定数として、ランチャーが設定する `ANTHROPIC_BASE_URL` から導出先の環境変数名への不変マッピング `_LAUNCHER_BASE_URL_KEYS` を定義する。

| `ANTHROPIC_BASE_URL`（完全一致） | 導出する環境変数名 | 対応ランチャー |
| --- | --- | --- |
| `https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic` | `MAAS_ANTHROPIC_TOKEN` | `ccda` / `claude-alibaba` |
| `https://ollama.com` | `OLLAMA_API_KEY` | `ccdol` / `claude-ollama` |
| `https://api.deepinfra.com/anthropic` | `DEEPINFRA_TOKEN` | `ccdd` / `ccddg` / `claude-deepinfra*` |
| `https://opencode.ai/zen/go` | `OPENCODE_API_KEY` | `ccdgo` / `claude-opencode-go` |

- **完全一致**: `environ.get("ANTHROPIC_BASE_URL", "")` をそのまま辞書検索する。前後の空白除去・末尾 `/` の正規化・大文字小文字の無視・前方一致・部分一致は一切行わない。未設定・空・一覧に無い URL では何も導出しない。
- **単一変数・クロス導出禁止**: 一致した URL に対応する 1 つの変数名だけを候補とする。他のプロバイダの変数は一切補わない。
- **`COMMANDCODE_API_KEY` の非導出**: `COMMANDCODE_API_KEY` を `ANTHROPIC_AUTH_TOKEN` に渡すランチャーは存在しない（Pi の `piccd` 専用）ため、`_LAUNCHER_BASE_URL_KEYS` に含めず、env ファイル経路のみで扱う。
- **`needed_names` による制限の維持**: 導出先の変数名が `names`（実効設定の全 `agent.env` の和集合から `HOME`・`PATH`・`GIT_*` を除いた集合）に含まれない場合は補わない。本 Issue で `claude-code_ollama_*` を雛形に追加することで、既定の雛形では `OLLAMA_API_KEY` が `needed_names` に入る。
- **導出元トークンの妥当性ガード**: `auth_token = environ.get("ANTHROPIC_AUTH_TOKEN", "")` が ASCII 英数字を 1 文字以上含む（`re.search(r"[A-Za-z0-9]", auth_token) is not None`）ときだけ補う。未設定・空、または ASCII 空白・NBSP（U+00A0）・BOM（U+FEFF）・全角空白（U+3000）など ASCII 英数字を含まない値では補わない。これにより、ASCII 英数字ガードを持たない後段（`pidid` や `pigod`）にも空白のみの値が渡らない。

#### 1.2 OpenCode Go の key 妥当性の確認結果

Issue の「エージェントに任せる事項」にある「`ccdgo` が選択した key（`OPENCODE_GO_CLAUDE_API_KEY` 由来の場合を含む）が pi の `OPENCODE_API_KEY` フォールバックとして妥当か」をリポジトリ内の実装・仕様で確認した。

- `.devcontainer/zshrc.txt`（226〜256 行）および `.devcontainer/README.md`（931〜940 行、#368）のとおり、`ccdgo` は OpenCode Go サブスクリプション向けに OpenCode Console で発行した API キーを `OPENCODE_GO_CLAUDE_API_KEY` → `OPENCODE_API_KEY` → `OPENCODE_GO_API_KEY` の順で選び、`https://opencode.ai/zen/go`（Anthropic 互換エンドポイント）へ送る。`OPENCODE_GO_CLAUDE_API_KEY` は Claude Code 用に別変数を分けたい場合のための本リポジトリ固有の変数名であり、キー種別自体は同じ OpenCode Console の API キーである。
- `scripts/setup_pi_opencode_go.zsh`（16〜24 行）および `.devcontainer/pigod`（35〜53 行）、`.devcontainer/README.md`（2331・2337 行）のとおり、Pi の組み込み `opencode-go` プロバイダ（`https://opencode.ai/zen/go/v1`）は `~/.pi/agent/auth.json` の保存済み `api_key` を第一経路として使い、`auth.json` に無い場合の環境変数フォールバックとして同じ OpenCode Console の API キーを `OPENCODE_API_KEY` から読む。
- したがって、`ANTHROPIC_BASE_URL == "https://opencode.ai/zen/go"` のセッションで `OPENCODE_API_KEY` が未設定・空のときに `ANTHROPIC_AUTH_TOKEN` から `OPENCODE_API_KEY` を補うことは妥当である。

#### 1.3 解決順序・既存値の保持・標準エラー出力

`tools/agent_runner/with_keys.py` の実在関数 `fill_environment(environ, names, source)` と `parse_assignments(text, names)` をベースに、解決順序を次の 3 段階とする。`fill_environment` の戻り値は `(environment, derived, filled, skipped)`（`tuple[dict[str, str], list[str], list[str], list[str]]`）とする。あわせて同ファイルのモジュール docstring（7〜12 行付近）および `fill_environment` の docstring（135〜140 行付近）も、読み元が「今の環境 → ランチャー環境の導出 → `~/.config/create-reso-world/env`」の 3 段階であること・戻り値 4 要素に合わせて更新する。

1. **今の環境（`environ`）**: `pending = {name for name in names if not environment.get(name)}` とし、既に非空文字列が入っている名前は `pending` に入れず元の値を保持する。空白のみの非空値が既に設定されている場合も上書きしない（後段の key ガードで意図どおり停止させ、黙って別アカウントの key に差し替えない）。
2. **ランチャー環境の導出（`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`）**: `pending` が空でなければ、`_LAUNCHER_BASE_URL_KEYS.get(environment.get("ANTHROPIC_BASE_URL", ""))` を引き、得られた名前 `derived_name` が `pending` に含まれ、かつ `environment.get("ANTHROPIC_AUTH_TOKEN", "")` が `[A-Za-z0-9]` を含む場合に、`environment[derived_name] = auth_token` を設定して `pending.remove(derived_name)` し、`derived = [derived_name]` に記録する。`main()` では標準エラーへ次の 1 行を出力する（key の値やトークン長は一切含めない）。
   ```text
   with_keys: filled <NAME> from launcher environment (ANTHROPIC_BASE_URL)
   ```
   ランチャー導出を env ファイルより先に置く理由は、例えば `ccdgo` セッションで親シェルが `OPENCODE_GO_CLAUDE_API_KEY` を選んでいた場合や、`ccdd` セッションで親シェルが env ファイルとは別の `DEEPINFRA_TOKEN` を一時 export していた場合に、現在起動中のランチャーセッションが実際に使っている認証情報と一致させるためである。
3. **env ファイル（`~/.config/create-reso-world/env`）**: 段階 2 の後に `not pending` となった場合は `source` を読まずに `(environment, derived, [], [])` を返す。`pending` が残っている場合のみ、従来どおり `source` を UTF-8 で読み、`parse_assignments(text, pending)` に **残りの `pending` だけ**を渡して解析する（`names` 全体は渡さない）。これにより、今の環境で既に設定済みの変数や段階 2 で導出済みの変数については、env ファイルに同名の行や解析不能な代入行があっても上書きされず、不要な `skipped` 警告も出ない。`main()` の標準エラー出力は `_report_derived(derived)` → `_report_skipped(skipped, source)` → `_report_filled(filled, source)` の順とし、既存の出力形式（`with_keys: cannot read <path>`、`with_keys: skipped <NAME> (unparsable assignment in <path>)`、`with_keys: filled <NAMES> from <path>`）を維持する。

### 2. Ollama の runner agent と `claude-ollama-exec` の取り込み（移植元 #860）

#### 2.1 `.devcontainer/claude-ollama-exec`

`.devcontainer/claude-alibaba-exec` と同型の構造で `.devcontainer/claude-ollama-exec`（mode `0755`）を新設する。

- 先頭は `#!/bin/bash -p`、`set -euo pipefail`。
- モデル変数は将来の tier 別変更に備えて 4 変数に分けて定義し、値は `.devcontainer/zshrc.txt` の `ccdol` と同じ `deepseek-v4.1-flash:1017[1m]` に揃える。
  - `fable='deepseek-v4.1-flash:1017[1m]'`
  - `opus='deepseek-v4.1-flash:1017[1m]'`
  - `sonnet='deepseek-v4.1-flash:1017[1m]'`
  - `haiku='deepseek-v4.1-flash:1017[1m]'`
- key ガード: `shopt -s globasciiranges` のうえで `key="${OLLAMA_API_KEY-}"` を検査し、`[[ $key != *[A-Za-z0-9]* ]]` なら値を出さずに標準エラーへ次を出して `exit 1` する（`claude` は起動しない）。
  ```text
  claude-ollama-exec: OLLAMA_API_KEY is not set, empty, or has no letters or digits; export an Ollama API key before starting agent-runner
  ```
- 子プロセスの起動: `.devcontainer/zshrc.txt` の `cc_launcher_unsets`（47 変数）から、このスクリプト自身が直後に設定する `ANTHROPIC_AUTH_TOKEN` を除いた **`.devcontainer/claude-alibaba-exec`（45〜90 行）と完全に同一の 46 個の `-u` 指定**（`ANTHROPIC_API_KEY`・`DEEPINFRA_TOKEN`・`OLLAMA_API_KEY`・`COMMANDCODE_API_KEY`・`OPENCODE_GO_CLAUDE_API_KEY`・`OPENCODE_API_KEY`・`OPENCODE_GO_API_KEY`・`MAAS_ANTHROPIC_TOKEN`・`ANTHROPIC_AWS_API_KEY`・`ANTHROPIC_FOUNDRY_API_KEY`・`ANTHROPIC_FOUNDRY_AUTH_TOKEN`・`ANTHROPIC_IDENTITY_TOKEN`・`ANTHROPIC_IDENTITY_TOKEN_FILE`・`ANTHROPIC_CUSTOM_HEADERS`・`ANTHROPIC_MODEL`・`ANTHROPIC_DEFAULT_MODEL`・`ANTHROPIC_SMALL_FAST_MODEL`・`ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION`・`ANTHROPIC_CUSTOM_MODEL_OPTION`・`ANTHROPIC_CUSTOM_MODEL_OPTION_NAME`・`ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION`・`ANTHROPIC_CUSTOM_MODEL_OPTION_SUPPORTED_CAPABILITIES`・`CLAUDE_CODE_OAUTH_TOKEN`・`CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR`・`CLAUDE_CODE_OAUTH_REFRESH_TOKEN`・`CLAUDE_CODE_SESSION_ACCESS_TOKEN`・`CLAUDE_CODE_HFI_BEARER_TOKEN`・`CLAUDE_CODE_CLIENT_KEY`・`CLAUDE_CODE_CLIENT_KEY_PASSPHRASE`・`CLAUDE_CODE_GATEWAY_TOKEN`・`CLAUDE_CODE_GATEWAY_TOKEN_FILE_DESCRIPTOR`・`CLAUDE_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR`・`CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR`・`CLAUDE_CODE_USE_BEDROCK`・`CLAUDE_CODE_USE_FOUNDRY`・`CLAUDE_CODE_USE_GATEWAY`・`CLAUDE_CODE_USE_ANTHROPIC_AWS`・`CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD`・`CLAUDE_CODE_USE_MANTLE`・`CLAUDE_CODE_USE_VERTEX`・`CLAUDE_CODE_MAX_CONTEXT_TOKENS`・`CLAUDE_CODE_SUBAGENT_MODEL`・`CLAUDE_CODE_SUBAGENT_MODEL_FORCE`・`CLAUDE_CODE_AUTO_MODE_MODEL`・`CLAUDE_CODE_BG_CLASSIFIER_MODEL`・`ANTHROPIC_BETAS`）を付けた `exec env` で次を設定して `claude "$@"` を起動する。
  - `ANTHROPIC_BASE_URL=https://ollama.com`
  - `ANTHROPIC_AUTH_TOKEN="$key"`（Bearer 認証のみ。`ANTHROPIC_API_KEY` と `OLLAMA_API_KEY` は子に渡さない）
  - `ANTHROPIC_DEFAULT_FABLE_MODEL="$fable"`
  - `ANTHROPIC_DEFAULT_OPUS_MODEL="$opus"`
  - `ANTHROPIC_DEFAULT_SONNET_MODEL="$sonnet"`
  - `ANTHROPIC_DEFAULT_HAIKU_MODEL="$haiku"`
  - `ENABLE_CLAUDEAI_MCP_SERVERS=false`
  - `CLAUDE_CODE_EFFORT_LEVEL=max`
  - `CLAUDE_CODE_MAX_OUTPUT_TOKENS=65536`
- `--model` と `--dangerously-skip-permissions` は `claude-code` adapter 側が引数として渡すため、`claude-ollama-exec` 内ではハードコードしない。
- `.devcontainer/zshrc.txt` の `ccdol` 自体は変更せず独立した関数のまま維持し（#401 の `ccda` と `claude-alibaba-exec` の関係に揃える）、`claude-ollama-exec` のコメントに `zshrc.txt` の `ccdol` と設定を揃える旨を明記する。

#### 2.2 `.devcontainer/install_beforehand.bash`

- `Placing the launchers (...)` の `step` 表示とコメントに `claude-ollama-exec` を加え、`claude-alibaba-exec` の直後に次を追加する。
  ```bash
  if ! install -m 0755 .devcontainer/claude-ollama-exec "${HOME}/.local/bin/claude-ollama-exec"; then
      fail "Failed to place claude-ollama-exec."
  fi
  ```

#### 2.3 `.devcontainer/agent-runner.toml`

- `[agents.claude-code_alibaba_opus_max]` の直後（`[workflows.review]` の前）に次の 2 agent を追加する。既定の `[workflows]` 割り当ては変更しない。
  ```toml
  [agents.claude-code_ollama_opus_max]
  runtime = "claude-code"
  command = ["claude-ollama-exec"]
  model = "opus"
  model_key = "deepseek-v4.1-flash"
  provider = "ollama"
  effort = "max"
  env = ["HOME", "PATH", "OLLAMA_API_KEY"]

  [agents.claude-code_ollama_sonnet_max]
  runtime = "claude-code"
  command = ["claude-ollama-exec"]
  model = "sonnet"
  model_key = "deepseek-v4.1-flash"
  provider = "ollama"
  effort = "max"
  env = ["HOME", "PATH", "OLLAMA_API_KEY"]
  ```
- 直前のコメントに次を記載する。
  - `claude-ollama-exec`（`.devcontainer/claude-ollama-exec`、Rebuild で `~/.local/bin` に配置）で Ollama Cloud（`https://ollama.com`）につなぎ、モデルの対応は `zshrc.txt` の `ccdol`（4 つの tier すべて `deepseek-v4.1-flash:1017[1m]`）と揃えること。
  - `OLLAMA_API_KEY` はファイルに書かず、通常のシェルでは export して使い、`ccdol` 起動セッションからは `with_keys.py` が `ANTHROPIC_BASE_URL` の一致で `ANTHROPIC_AUTH_TOKEN` から補うこと（他プロバイダのランチャーセッションからは補われず、`claude-ollama-exec` の key ガードで止まること）。
  - 同一モデル比較（`duplicate_model`）: `model_key = "deepseek-v4.1-flash"` により既存の DeepSeek V4.1 Flash 系 3 agent（`pi_commandcode_deepseek4-flash_max`・`pi_opencode-go_deepseek4-flash_max`・`pi_deepinfra_deepseek4-flash_high`）および Ollama の 2 agent 同士は同じ役割に並べられない。加えて `opus` 側は `claude-code_opus_default`・`claude-code_alibaba_opus_max` と、`sonnet` 側は `claude-code_sonnet_xhigh` と `model` が一致するため同じ役割に並べられない。将来 tier ごとに別モデルへ変えた場合は `model_key` も別値にすること。
- あわせて `[agents.pi_alibaba_qwen4-max_max]`（177〜188 行）および `[agents.claude-code_alibaba_opus_max]`（206〜209 行）のコメントを更新し、PR #405 が残した食い違い（「ランチャー起動セッションの中には key が無く、その中から runner を起動しても届かない」）を解消する。具体的には、`ccda` セッションから `with_keys.py` 経由でランナーを起動する場合は `ANTHROPIC_BASE_URL` の一致により `ANTHROPIC_AUTH_TOKEN` から `MAAS_ANTHROPIC_TOKEN` が補われること、それ以外のランチャー（`ccdd`・`ccddg`・`ccdgo`・`ccdol`）のセッションや `with_keys.py` を通さない直接起動では届かず key ガードで終了コード 1 で止まることを書く。

### 3. `.devcontainer/README.md` の更新仕様

`.devcontainer/` 配下にはワークスペースの絶対パスを書かない（`test-readme.bash` の不変条件）。以下の箇所を一貫して更新する。

1. **「既存環境の更新」・「エージェント向けツールの導入」・「install_beforehand.bash の配置一覧」**:
   - postCreate が `~/.local/bin` に置く一覧（91 行付近）と、rebuild しない場合の手動 `install -m 0755` 案内（128〜129 行付近）に `claude-ollama-exec`（未配置だと `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` が `launch_failed` になること）を加える。
   - 「エージェント向けツールの導入」の番号付き手順（763〜765 行）の `21. install -m 0755 .devcontainer/claude-alibaba-exec ...` の次に `22. install -m 0755 .devcontainer/claude-ollama-exec ~/.local/bin/claude-ollama-exec` を追加し、後続を `23`・`24` に繰り下げ、128 行付近の番号参照（`21`・`22`）を揃える。
   - `install_beforehand.bash` が配置するものの詳細一覧（1606〜1617 行）で、`claude-alibaba-exec` の直後に `- .devcontainer/claude-ollama-exec → ~/.local/bin/claude-ollama-exec。同様に毎回上書き` を追加する。
2. **「Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）」節（912 行付近）**:
   - `#397` の Alibaba 節にならい、`#### agent-runner から使う` 小節を追加する。
   - 雛形の `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` の設定表（`command`・`model`・`model_key`・`provider`・`effort`・`env`）、Rebuild 前の `~/.local/bin/claude-ollama-exec` 手動配置、通常シェルで `OLLAMA_API_KEY` を export して `with_keys.py` 経由で起動する例、`ccdol` セッションでは `with_keys.py` が `ANTHROPIC_AUTH_TOKEN` から `OLLAMA_API_KEY` を補うこと（他ランチャーセッションからは補われないこと）、`claude-ollama-exec` の英数字 key ガードと Bearer のみ送信、および `duplicate_model` で同じ役割に並べられない組み合わせを記載する。
3. **Alibaba 関連の 3 か所の食い違い解消（`#issuecomment-6806157671`）と `#397` 節の更新**:
   - 1234〜1237 行（`#397` の `claude-code_alibaba_opus_max` 説明）: 通常シェルでの export に加え、`ccda` 起動セッションからは `with_keys.py` が `ANTHROPIC_BASE_URL` の一致で `ANTHROPIC_AUTH_TOKEN` から `MAAS_ANTHROPIC_TOKEN` を補うこと、他プロバイダのランチャーセッションからは補われないことに更新する。
   - 1310〜1314 行（`#397` 内の `#402` 説明）、1442〜1455 行（`agent の命名と同一モデルの比較` 内の `pi_alibaba_qwen4-max_max` 説明と起動例。起動例も `with_keys.py` 経由に揃える）、1892〜1903 行（`#402` の `piaq` 節）の 3 か所にある「`with_keys.py` で補う経路も無い」を解消する。具体的には、対話の `piaq` をランチャーセッションの中で直接呼ぶ場合は引き続き `MAAS_ANTHROPIC_TOKEN` が無く終了コード 1 で止まる一方、`ccda` セッションから `with_keys.py` 経由で agent-runner の `pi_alibaba_qwen4-max_max` を起動する場合は `ANTHROPIC_AUTH_TOKEN` から補われる（`ccda` 以外のランチャーセッションからは補われない）と区別して記述する。
   - `agent の命名と同一モデルの比較` 節（1427〜1441 行付近）で、#305 以降の追加 agent の説明と矛盾しない形で、Claude Code 用の exec を使う雛形 agent（#401 の `claude-code_alibaba_opus_max` と #408 の `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max`）への案内を補う。
4. **「API トークン」節の各変数説明（2224〜2248 行）と「ランチャー起動セッションから runner を使う（#401・#408）」小節（2260〜2345 行）**:
   - 直前の各変数の箇条書き（2224〜2248 行）にある古い記述もあわせて更新する:
     - `DEEPINFRA_TOKEN`（2224〜2230 行）: `ccdd`・`ccddg` 起動セッションから `with_keys.py` 経由でランナーを起動するときは `ANTHROPIC_AUTH_TOKEN` から補われることを補記する。
     - `OLLAMA_API_KEY`（2231〜2236 行）: 「`ccdol`・`claude-ollama` だけが読む」「どの agent の `env` にも無いので、wrapper では補えない」を改め、agent-runner の `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` が呼ぶ `claude-ollama-exec` も読むこと、env ファイルには置かないが `ccdol` セッションからは `with_keys.py` が `ANTHROPIC_AUTH_TOKEN` から補うこと（他ランチャーセッションからは補われないこと）に更新する。
     - `MAAS_ANTHROPIC_TOKEN`（2237〜2248 行）: 2241 行の「補う名前には入るが、env ファイルに置かない方針なので、通常は補われない」を改め、env ファイルには置かないが `ccda` セッションからは `with_keys.py` が `ANTHROPIC_AUTH_TOKEN` から補うこと（他ランチャーセッションからは補われないこと）に更新する。
   - 小節見出し・本文（2260〜2345 行）を #408 の一般化に合わせて更新する。
   - 「補う条件」「読み元と順序」「出力」を次のとおり更新する:
     - 順序: `今の環境（非空）` → `ランチャー環境の導出（ANTHROPIC_BASE_URL の完全一致かつ ANTHROPIC_AUTH_TOKEN が ASCII 英数字を含むとき、対応する 1 変数のみ）` → `~/.config/create-reso-world/env`。
     - 4 ランチャーの `ANTHROPIC_BASE_URL` と補う変数名の対応表、完全一致・クロス導出禁止・空白のみ非導出・既存値非上書きの規則、`COMMANDCODE_API_KEY` は導出元ランチャーが無く env ファイル経路のみであること、Vertex の `GOOGLE_*` は `cc_launcher_unsets` の対象外のためランチャー起動セッションでも親シェルの値が残ること。
     - 標準エラー出力: ランチャー環境から補ったときは `with_keys: filled <NAME> from launcher environment (ANTHROPIC_BASE_URL)` を 1 行出し、値は出さないこと。導出済みの変数は env ファイルの解析対象（`pending`）から外れるため、env ファイルに同名の行があっても上書きも `skipped` 表示もしないこと。
   - 小節内の古くなった記述（「`MAAS_ANTHROPIC_TOKEN` は通常は補われない」「`OLLAMA_API_KEY` はどの agent の `env` にも無いので wrapper では補えない」「雛形に Ollama の runner agent は無い」、2319〜2323 行・2343 行）を現行仕様に置き換える。
   - プロバイダごとの key 解決経路の表（2328〜2342 行）を次のとおり更新する:
     - `DEEPINFRA_TOKEN`: 今の環境、`ccdd` / `ccddg` セッションの導出、または env ファイル（`pi_deepinfra_deepseek4-flash_high`）
     - `OPENCODE_API_KEY`: 今の環境、`ccdgo` セッションの導出、または env ファイル（`pi_opencode-go_deepseek4-flash_max`・`pi_opencode-go_glm5-flash_max`・`pi_openai-codex_gpt6-sol_xhigh`。ただし `opencode-go` の第一経路は下の `auth.json`）
     - `COMMANDCODE_API_KEY`: 今の環境、または env ファイルのみ（導出元ランチャー無し。契約停止中）
     - `GOOGLE_*`: 今の環境（`cc_launcher_unsets` 対象外のためランチャーセッションでも残る）、または env ファイル
     - `MAAS_ANTHROPIC_TOKEN`: 今の環境、または `ccda` セッションの導出（env ファイルに置かない方針。対象は `pi_alibaba_qwen4-max_max`・`claude-code_alibaba_opus_max` — PR #405 で抜けていた `pi_alibaba_qwen4-max_max` を追加）
     - `OLLAMA_API_KEY`: 今の環境、または `ccdol` セッションの導出（env ファイルに置かない方針。対象は `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max`）
     - `~/.pi/agent/auth.json` および HOME 配下のログインの各行は維持し、`#issuecomment-6816243774` の訂正に従い、`auth.json` について根拠のない実機起動確認済みの表現を書かない（#401 で確認したのは `auth.json` の存在と `HOME` の引き継ぎである）。

## テスト計画（AGENTS.md「テストの採用基準」）

追加・変更する自動テストは、壊れてもエラーにならずに損害が残る **S（気付けない損害）**（および安全境界を守る **F∩S**）の代表各 1 件に限定し、F（文書・設定・モデル一覧の固定値照合）・L（構文エラーや `check-layout.sh` で気付けるもの）・D（同じ守りの別ケース分割）は書かない。テスト内の偽トークン文字列は Gitleaks の誤検知を避けるため実行時に連結して組み立てる。

1. **`tools/agent_runner/tests/test_with_keys.py`（既存の代表テスト `test_wrapper_fills_missing_allowlisted_names_only` の拡張、新設関数 0 件）**:
   - `#issuecomment-6816243774` の指示どおり、テスト関数は新設せず実在する代表テスト `test_wrapper_fills_missing_allowlisted_names_only`（実雛形 `.devcontainer/agent-runner.toml` と存在しない `AGENT_RUNNER_CONFIG` を使用）を拡張する。
   - 既存 fixture の守り（`COMMANDCODE_API_KEY` は env ファイルから補われる、`OPENCODE_API_KEY` は `child_env` の既存値を保ち env ファイルで上書きしない、`MESHY_API_KEY` は allowlist 外のため子に渡さない、`DEEPINFRA_TOKEN` は解析不能な `$(touch ...)` 再代入があるため前の行の literal も含めて補わず実行もしない）をすべて維持する。
   - 同じ関数内で次の陽性・陰性の対照を追加確認する:
     - **サブプロセス実行での陽性対照と異プロバイダ陰性対照**: `child_env` に `ANTHROPIC_BASE_URL="https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic"` と有効な偽トークン `ANTHROPIC_AUTH_TOKEN=fake_f` を追加して `WRAPPER` を実行する。`MAAS_ANTHROPIC_TOKEN == fake_f` が導出される一方、雛形の `claude-code_ollama_*` 追加で allowlist に入った `OLLAMA_API_KEY` は `ccda` の URL からは導出されない（`"OLLAMA_API_KEY" not in environment`）。残りの未設定変数 `COMMANDCODE_API_KEY` は引き続き env ファイルから補われ、`DEEPINFRA_TOKEN` の解析不能行は引き続き拒否される。標準エラーに `with_keys: filled MAAS_ANTHROPIC_TOKEN from launcher environment (ANTHROPIC_BASE_URL)` が出て、すべての偽トークン実値（`fake_f` を含む）が `completed.stderr` に含まれないことを確かめる。
     - **`fill_environment` 直接呼び出しによる境界対照（同じテスト関数内）**: 実雛形の `needed_names(TEMPLATE, None)` を使い、(a) 未登録・部分一致 URL（例: `https://ollama.com/v1`）で env ファイル不在のときは `COMMANDCODE_API_KEY` を含め 1 変数も導出されないこと、(b) 登録済み URL（`https://ollama.com`）でも ASCII 英数字を含まない空白（`" \u00a0\ufeff\u3000"`）の `ANTHROPIC_AUTH_TOKEN` では `OLLAMA_API_KEY` が導出されないこと、(c) `ccda` の URL でも `MAAS_ANTHROPIC_TOKEN` が既に `environ` にあるときは上書きされないこと、(d) `ccdgo` の URL（`https://opencode.ai/zen/go`）で `OPENCODE_API_KEY` が `environ` に未設定かつ env ファイルに別の `OPENCODE_API_KEY`（および解析不能な再代入行）があるときは、ランチャーの `ANTHROPIC_AUTH_TOKEN` が採用されて env ファイルで上書きされず `skipped` にも入らないことを確かめる。
2. **`.devcontainer/test-herdr-migration.bash`（`test_ollama_exec_requires_key` の追加、代表 1 件）**:
   - `claude-ollama-exec` は `claude-alibaba-exec` とは別の独立したスクリプトであるため、`#issuecomment-6816243774` に従い `test_alibaba_exec_requires_key` と同型の代表テスト `test_ollama_exec_requires_key` を 1 件追加し、`main()` から呼ぶ。
   - **拒否側（S）**: 隔離 HOME・`env -i`（locale 非継承）・stub `claude` の環境で、`OLLAMA_API_KEY=$' \xc2\xa0\xef\xbb\xbf\xe3\x80\x80'`（ASCII 空白・NBSP・BOM・全角空白）かつ親に `ANTHROPIC_API_KEY`・`CLAUDE_CODE_OAUTH_TOKEN` があるとき、非 0 で終了し stub `claude` が一度も起動しないこと（保存済み OAuth トークンの `ollama.com` への送信防止）。
   - **陽性対照と全 `cc_launcher_unsets` 隔離確認（S・F∩S）**: 同じ環境で、`extract_cc_launcher_unsets "$ZSHRC_TEMPLATE"` から取得した全変数（`OLLAMA_API_KEY` 自身を除く 46 変数）に `POLLUTED_<変数名>` を与え、`OLLAMA_API_KEY=fake-ollama` を渡して実行したとき、終了コード 0 で stub `claude` が起動し、`ANTHROPIC_BASE_URL=https://ollama.com` と `ANTHROPIC_AUTH_TOKEN=fake-ollama` が届き、子の環境ダンプに `POLLUTED_` も `^OLLAMA_API_KEY=` も一切残らないこと（`cc_launcher_unsets` との `-u` 集合の一致を実行で検証する）。

## 受け入れ条件・検証計画

### 1. ローカル自動検証・静的検査・構造確認

- `uv run --project "$PARENT_ROOT" --locked pytest tools/agent_runner/tests/test_with_keys.py`
- `bash .devcontainer/test-herdr-migration.bash`
- `bash .devcontainer/test-readme.bash`
- `bash .devcontainer/test-install-beforehand.bash`
- `uv run --project "$PARENT_ROOT" --locked python -m tools.agent_runner --template "$CODE_ROOT/.devcontainer/agent-runner.toml" check` および `list`（加えて、`claude-code_ollama_opus_max` と既存 DeepSeek V4.1 Flash agent や `claude-code_ollama_sonnet_max` を同一役割に並べた一時検証で `duplicate_model` 拒否を確認する。コミットしない）
- 最終コミット後のリポジトリ全体検証（`git status --porcelain` が空の状態で実行し、`$SESSION` にログと `checks.json` を保存）:
  - `bash .devcontainer/run-tests.bash`
  - `bash scripts/check-layout.sh`
  - `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools`

### 2. 反例のローカル実行確認（課金 API を呼ばない偽 CLI・隔離環境）

`$SESSION` 配下の一時ディレクトリと偽 CLI を使い、次を実行証拠として確認する（コミットしない）:

- 4 つのランチャー URL それぞれで対応する 1 変数だけが導出され、他プロバイダの変数や `COMMANDCODE_API_KEY` が補われないこと（`ccdgo` → `OPENCODE_API_KEY` の偽 CLI 確認を含む）。
- `ANTHROPIC_BASE_URL` 未設定・未知 URL・前方一致 URL、および `ANTHROPIC_AUTH_TOKEN` 未設定・空・空白のみでは何も導出されないこと。
- 既存の環境変数値が `ANTHROPIC_AUTH_TOKEN` で上書きされないこと。
- 導出した key は `agent.env` にその変数名を持つ担当の子にだけ渡り、別プロバイダの担当の子には渡らないこと。
- `with_keys.py` の stderr、ランナーのログ・`result.json`・標準出力要約に偽トークンの実値が 1 件も出ないこと。

### 3. 実機観測（マージ前の確認範囲と、マージ後の Rebuild 後確認範囲の区分）

Issue 本文の最終的な動作環境は「Rebuild 後の Dev Container」であり、実機観測は「各 agent 1 回ずつ、PR マージ前 1 回・マージ後 1 回」と定められている（`#issuecomment-6816243774`）。一方、稼働中の Dev Container セッション内からは自身の Rebuild（`postCreateCommand` による `~/.local/bin/claude-ollama-exec` 配置）を実行できず、マージ前に共有の `~/.local/bin`・`~/.pi`・`~/.config/create-reso-world/env` を直接書き換えることも安全境界に反する。そのため、マージ前とマージ後の確認範囲を次のとおり明確に分ける。

#### マージ前にこの run で確認する範囲（各 agent 最大 1 回）

親シェルに既存の `MAAS_ANTHROPIC_TOKEN`・`OLLAMA_API_KEY`・`DEEPINFRA_TOKEN` と、配置済みの `~/.local/bin/{piaq,pidid,claude-alibaba-exec}` を使う。実ランチャー関数（`.devcontainer/zshrc.txt` の `ccda`・`ccdol`・`ccdd`）が構築する子環境をそのまま通すため、外側の `claude` 呼び出しだけを `$SESSION` 内の一時 shim で受けて元の `PATH` に戻し、`with_keys.py -- python -m tools.agent_runner ... run` を実行する（外側 Claude Code の二重課金を避けつつ、実ランチャーの `cc_launcher_unsets`・`ANTHROPIC_BASE_URL`・`ANTHROPIC_AUTH_TOKEN` 設定を忠実に通す）。Rebuild 前のため `claude-ollama-exec` だけは `$SESSION` 内の一時ディレクトリに `install -m 0755` で置いてその試行の `PATH` に加え、`claude-ollama-exec` 本体と Ollama Cloud 実 API・導出経路を検証する。

1. **`ccda` セッション環境 + wrapper（手当てなし）→ `pi_alibaba_qwen4-max_max`**（1 回）: `state == "success"`、`identity` が `qwen4-max-preview` / `alibaba` / `max` と実測されること。
2. **`ccda` セッション環境 + wrapper（手当てなし）→ `claude-code_alibaba_opus_max`**（1 回）: `state == "success"`、`identity.model` が `qwen4-max-preview` 系と実測されること。
3. **通常のシェル（`MAAS_ANTHROPIC_TOKEN` export 済み、`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` 無し）+ wrapper → `claude-code_alibaba_opus_max`**（1 回、`#issuecomment-6816243774` で限定された対象）: 従来どおり `state == "success"` で動くこと。
4. **`ccdol` セッション環境 + wrapper（手当てなし、一時 `PATH` に `claude-ollama-exec`）→ `claude-code_ollama_opus_max`**（1 回）: `state == "success"`、`identity` に Ollama の `deepseek-v4.1-flash` 系モデルが実測されること（`sonnet` 側は同じ exec・同じモデルのため実機追加なし）。
5. **`ccdd` セッション環境 → `pi_deepinfra_deepseek4-flash_high`**（`#issuecomment-6816243774` で統合された #401 残件）:
   - **wrapper 無し比較**（失敗経路確認、API 課金なし）: `DEEPINFRA_TOKEN` が外れているため `pidid` の key ガードで即座に失敗すること。
   - **wrapper 経由（手当てなし）**（1 回）: 導出した `DEEPINFRA_TOKEN` で `state == "success"`、`identity` に DeepSeek V4.1 Flash 系 / `deepinfra` が実測されること。
6. **秘密値の非露出確認**: 上記すべての出力ディレクトリ（`result.json`・`stdout.log`・`stderr.log`・wrapper の stderr）に対して、環境中の実 key 値との一致が 0 件であることをプログラムで検査し、値自体は表示せず一致件数（0 件）だけを `$SESSION` と PR 本文に記録する。

#### マージ後（Rebuild 後の Dev Container）に残る確認項目

- Dev Container の Rebuild により `install_beforehand.bash` が `~/.local/bin/claude-ollama-exec`（権限 `0755`）を標準 `PATH` 上へ配置すること（一時 `PATH` 無しでの解決）。
- Rebuild 後のコンテナで、実際の `ccda`・`ccdol`・`ccdd`（または `ccddg`）の起動セッションおよび key を export した通常のシェルから、上記の同じ実機観測を 1 回ずつ行って Issue #408 に記録すること（完了後に #401 もその記録を参照して閉じる）。
- このマージ後確認が受け入れ条件に残るため、PR 本文は `Closes #408` ではなく **`Refs #408`** とし、run の最後に PR URL と上記マージ後確認項目を Issue #408 にコメントする。

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | `with_keys.py` の優先順を `今の環境（非空） → ランチャー導出（ANTHROPIC_BASE_URL 完全一致） → env ファイル` にし、段階 3 の `parse_assignments` には未解決の `pending` だけを渡す | `今の環境 → env ファイル → ランチャー導出` にする / `names` 全体を `parse_assignments` に渡す | 動作中ランチャーセッションが選んだ key と一致させ、既に解決済みの変数に対する不要な `skipped` 警告や上書きを防ぐため | Issue「エージェントに任せる事項」（順序の決定）。既存環境変数を上書きする場合は停止 |
| D2 | `with_keys.py` の導出時にも `ANTHROPIC_AUTH_TOKEN` が ASCII 英数字（`[A-Za-z0-9]`）を 1 文字以上含むことを要求する | 非空（`bool(auth_token)`）だけで導出し、各 exec のガードに任せる | `claude-alibaba-exec`・`claude-ollama-exec`・`piaq` には英数字ガードがあるが、`pidid` と `pigod` の環境変数参照には ASCII 英数字ガードが無い。導出側でも同じ英数字条件を課すことで、空白・NBSP・BOM のみの `ANTHROPIC_AUTH_TOKEN` がどの担当にも渡らない | Issue「エージェントに任せる事項」（値の妥当性判定の共有） |
| D3 | `ccdgo`（`https://opencode.ai/zen/go`）から `OPENCODE_API_KEY` への導出を有効にする | OpenCode Go の導出を見送る | `zshrc.txt`・`README.md`（#368）・`setup_pi_opencode_go.zsh`・`pigod` により、`ccdgo` の 3 変数と Pi `opencode-go` の `OPENCODE_API_KEY` はどちらも同じ OpenCode Console の API キーであることを確認できたため。第一経路の `auth.json` は不変 | Issue「エージェントに任せる事項」（妥当性確認） |
| D4 | `zshrc.txt` の `ccdol` は変更せず、独立した `.devcontainer/claude-ollama-exec`（`claude-alibaba-exec` と同一の 46 個の `-u` 指定）を新設してモデル・環境変数を揃える | `ccdol` を `claude-ollama-exec` を呼ぶ薄いラッパーに書き換える（移植元 #860 の形） | Rebuild 前のコンテナや隔離 HOME のシェルテストでは `~/.local/bin/claude-ollama-exec` が未配置であり、`ccdol` から呼ぶと Rebuild 前の `zshrc.txt` 反映で `ccdol` が壊れる。`#401` の `ccda` と `claude-alibaba-exec` の構成に揃える方が安全で変更範囲も最小になる | Issue「エージェントに任せる事項」（`ccdol` の薄いラッパー化の採否） |
| D5 | ランチャー導出時の標準エラー出力を `with_keys: filled <NAME> from launcher environment (ANTHROPIC_BASE_URL)` とし、env ファイル由来の行と分ける | env ファイルと同じ行に混ぜる / 何も出さない | 値を一切出さずに「どの変数がランチャー環境から補われたか」を診断可能にし、ファイルパス由来の `from <path>` と明確に区別できるため | Issue「エージェントに任せる事項」（stderr の文言） |
| D6 | `test_with_keys.py` は実在の `test_wrapper_fills_missing_allowlisted_names_only` を拡張し、`test-herdr-migration.bash` に全 `cc_launcher_unsets` 隔離を含む `test_ollama_exec_requires_key` を 1 件追加する | 条件ごとに個別テスト関数を新設する / モデル名や README の固定値テストを足す | `AGENTS.md`「テストの採用基準」（S・F∩S の代表 1 件、F・L・D 禁止）および `#issuecomment-6816243774` の明示指示に従うため | `AGENTS.md` と Issue コメントの基準。反するテストはコミットしない |
| D7 | 設計レビューは `claude-code_opus_default`、Spec レビューと Task 実装は `pi_opencode-go_deepseek4-flash_max`、PR ループは `inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default`・`fix.implement=pi_opencode-go_deepseek4-flash_max`・`max_cycles=3`（既定）で実行する | `self` による代行や別モデルへの切り替え | Step 2 の各 `check` で全担当が `self=false`・`fallback=[]` と確定済み。担当失敗時に `self` で引き取らない規則を守る | 利用者の明示オプション。担当の失敗・停止未確認・`wrong_approach` / `blocking` 等は停止 |
| D8 | `origin/main` の前進を検出した場合は push 前に `rebase`、push 後に `merge --no-edit` で追随し、再検証後に `code-base.json` を更新して続行する | base 移動で即停止する / 再検証なしで SHA だけ書き換える | 利用者が「途中でメインがマージされたら、追随して作業を止めずに続行してください。」と明示委任しているため。実行中の runner がある間は完了を待ってから追随し、force push と無検証更新は行わない | 利用者の明示委任。コンフリクトが仕様変更を伴う場合は停止 |

### 設計レビュー記録

- 1 回目（外部 runner `review_design.py`）:
  - `review_dir`: `/workspaces/reso-world/tmp/agents/issue-408.kwkykzl6/2026-11-12-issue-408-launcher-key-derivation-design.design-review/review-1`
  - `review_id`: `ba4a149581844aec97695d209e0debfe`
  - reviewed `spec_sha256`: `243243fd3c901220cade5bd6897d2b7b22a2283d7a190c998c36dea867305baa`
  - `requested_agent` / `actual_agent`: `claude-code_opus_default` / `claude-code_opus_default`（`fallback` 未使用）
  - `identity`: `model="claude-opus-5-5"`, `provider=null`, `effort=null`, `cli_version="2.1.322"`, `session_id="af4f954b-51a7-41f4-b66c-6a0e1b466e99"`
  - `elapsed_seconds`: `28.16`
  - `verdict`: `sound`（`concerns: 0`、`questions_for_user: 0`、`incomplete: 0`）
  - `outside_changes`: `[]`
  - `unprotected_changes`: 既存の prunable な一時 worktree 登録 6 件（`/tmp/pr-review-376-*` 4 件、`/tmp/review-fix-planning.*` 2 件。本 run の保護対象外）
  - 採否: 指摘 0 件のため `decisions: []`

### Spec レビュー記録

- 1 回目（外部 runner `review_spec.py`）:
  - `review_dir`: `/workspaces/reso-world/tmp/agents/issue-408.kwkykzl6/2026-11-12-issue-408-launcher-key-derivation-design.spec-review/review-1`
  - `review_id`: `1d3afbede0ec4d7e846ca8b4d6f9c3dd`
  - reviewed `spec_sha256`: `01e415072a9c838d98f67875a466eb0f763e3db4d411eac646b4e05a65d8cda2`
  - `requested_agent` / `actual_agent`: `pi_opencode-go_deepseek4-flash_max` / `pi_opencode-go_deepseek4-flash_max`（`fallback` 未使用）
  - `identity`: `model="deepseek-v4.1-flash"`, `provider="opencode-go"`, `effort="max"`, `cli_version=null`, `session_id="01a1cedb-db6e-743e-a53e-f837d24e3789"`
  - `elapsed_seconds`: `1269.46`
  - `outside_changes`: `[]`
  - `unprotected_changes`: 既存の prunable な一時 worktree 6 件および並行セッションの他 Issue worktree 3 件（`.worktrees/issue-378-rebase-base`・`.worktrees/issue-390-review-cleanup`・`tmp/agents/issue-378.pu_as9oz/...`。いずれも本 run の保護対象外）
  - 採否（5 件すべて `adopt`、`important` 2 件採用のため再レビュー実施）:
    - `S1`（`important`, `adopt`）: `2.1 .devcontainer/claude-ollama-exec` の `-u` 一覧を `claude-alibaba-exec` と同一の 46 個（`cc_launcher_unsets` 47 個から `ANTHROPIC_AUTH_TOKEN` を除いた全変数）に修正し、`test_ollama_exec_requires_key` で `extract_cc_launcher_unsets` の全変数汚染が子に残らないことを実行確認する仕様へ更新。
    - `S2`（`important`, `adopt`）: `テスト計画 1` の関数名を実在の `test_wrapper_fills_missing_allowlisted_names_only`（実雛形使用）に修正し、既存の `COMMANDCODE_API_KEY`（env ファイル補充）・`DEEPINFRA_TOKEN`（解析不能行スキップ）等を維持したまま導出の陽性・陰性対照を追加する形に整理。
    - `S3`（`minor`, `adopt`）: `1.3` の関数名を実在の `fill_environment`・`parse_assignments` に合わせ、段階 3 の `parse_assignments` に未解決の `pending` だけを渡して解決済み変数の不要な `skipped` 警告を出さない仕様に明確化。
    - `S4`（`minor`, `adopt`）: `3. .devcontainer/README.md` の更新範囲に 2224〜2248 行（API トークン節の各変数の箇条書きにある `OLLAMA_API_KEY`・`MAAS_ANTHROPIC_TOKEN`・`DEEPINFRA_TOKEN` の旧記述）を追加。
    - `S5`（`minor`, `adopt`）: `受け入れ条件・検証計画 3` で、稼働中コンテナからは Rebuild できないためマージ前は一時 `PATH` で `claude-ollama-exec` 本体と実 API を確認し、Rebuild による `~/.local/bin` 配置と対話セッションからの再確認をマージ後確認項目（`Refs #408`）とすることを区分して明記。
- 2 回目（再レビュー、外部 runner `review_spec.py`）:
  - `review_dir`: `/workspaces/reso-world/tmp/agents/issue-408.kwkykzl6/2026-11-12-issue-408-launcher-key-derivation-design.spec-review/review-2`
  - `review_id`: `a2903333105e4623a69367a983679621`
  - reviewed `spec_sha256`: `503382e88b4abd86831807754c4f82fe8e7b82fdc0a2988c8c289a04d8922a77`
  - `requested_agent` / `actual_agent`: `pi_opencode-go_deepseek4-flash_max` / `pi_opencode-go_deepseek4-flash_max`（`fallback` 未使用）
  - `identity`: `model="deepseek-v4.1-flash"`, `provider="opencode-go"`, `effort="max"`, `cli_version=null`, `session_id="01a1cf04-db77-776d-9364-a40bfcca7d6f"`
  - `elapsed_seconds`: `1145.72`
  - `outside_changes`: `[]`
  - `unprotected_changes`: 既存の prunable な一時 worktree 6 件および並行セッションの他 Issue worktree 2 件（`.worktrees/issue-378-rebase-base`・`tmp/agents/issue-378.pu_as9oz/...`。いずれも本 run の保護対象外）
  - 採否（`minor` 2 件すべて `adopt`、`important` 0 件のため Plan 作成へ進行）:
    - `S1`（`minor`, `adopt`）: `3. .devcontainer/README.md` の更新仕様 1 に `install_beforehand.bash` の配置一覧（1606〜1617 行）への `claude-ollama-exec` 追加を明記。
    - `S2`（`minor`, `adopt`）: `1.3 解決順序・既存値の保持・標準エラー出力` に `tools/agent_runner/with_keys.py` のモジュール docstring および `fill_environment` の docstring を 3 段階の解決順序・戻り値 4 要素に合わせて更新することを明記。
