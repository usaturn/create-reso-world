# Issue #401: ランチャー起動セッションから agent-runner へ key を届ける wrapper と Alibaba の runner agent

## 管理・実行許可

- 状態: `draft`（issue-to-pr の実行許可で進めている。内容の承認は得ていない）
- 対象: https://github.com/usaturn/create-reso-world/issues/401
- 利用者の指示（2026-11-11）: `/issue-to-pr #401 --merge --spec-review devin_swe2_max --design-review pi_openai-codex_gpt6-sol_xhigh --implement devin_swe2_max --assign implement=devin_swe2_max --assign inspect=pi_xai_grok4_xhigh,pi_openai-codex_gpt6-sol_xhigh`
- 許可範囲: 通常の設計判断を推奨案で決めること、指定した担当による設計レビュー・Spec レビュー・Task の実装、ローカルの検証、commit、検査の後の push、PR の作成、PR 修正ループの `finalize.py` によるマージ。利用者の env ファイル・個人設定・資格情報・他者の作業は変更しない
- コード/文書: 同じ worktree・同じ PR（`DOCS_SEPARATE=false`）。base: `usaturn/create-reso-world`、`origin`、`refs/heads/main`、`65b7800c82101f102d3549830a864ddce4127474`。親 Issue・要求 base・未完了の依存・競合する PR・予約は、確認の時点で無し
- 移植元: usaturn/agent-workspace#927、PR #929（マージコミット `c5afca3ff4bef84e21feeb2fc3bd447b6f482209`）。前提の #923 は本リポジトリの #397（PR #399）で取り込み済み

## 意図

プロバイダ切替ランチャー（`ccdd`・`ccddg`・`ccdol`・`ccdgo`・`ccda`）は `cc_launcher_unsets` で親シェルの key を外して Claude Code を起動する。そのセッションの Bash から agent-runner を起動すると、runner は自分の起動時の環境（`/proc/self/environ`）から `agent.env` の名前を子へ渡すので、外れた key は子に届かず、`pi_deepinfra_deepseek4-flash_high` などが認証エラーで止まる。runner を起動する前に、runner の agent が使う名前だけを `~/.config/create-reso-world/env` から補って exec し直す wrapper を足し、runner を起動するスキルの手順をその wrapper 経由にする。

あわせて、Alibaba Cloud Model Studio の Token Plan の runner agent（`claude-code_alibaba_opus_max` と、それが呼ぶ `.devcontainer/claude-alibaba-exec`）を足す。

守る損害は次の 3 つ。

1. wrapper が補いすぎる: agent の `env` に無い名前（`MESHY_API_KEY` など）が runner に入る、今の環境にある key を env ファイルの別の値で上書きして別のアカウントで外部へ要求を送る。どちらもエラーにならない
2. key の値が wrapper の stderr・runner のログ・結果に出る
3. `claude-alibaba-exec` が空・空白だけの key で `claude` を起動し、保存済みの claude.ai の OAuth トークンを `maas.aliyuncs.com` へ送る

## 目標・目標にしないこと

- 目標: ランチャー起動セッションから wrapper 経由で起動した runner の子に、env ファイルにある `agent.env` の key が届く。通常のシェルからの起動は今と同じに動く（補うものが無いだけ）。`MAAS_ANTHROPIC_TOKEN` を export した通常のシェルから `claude-code_alibaba_opus_max` が使える
- 目標にしないこと（Issue の「対象外」のとおり）: 移植元の `keys.env` と `~/.zshrc` の読み取り、`OLLAMA_API_KEY`・`MAAS_ANTHROPIC_TOKEN` をファイルに置く方針の変更、Ollama の runner agent、ステータスライン、`cc_launcher_unsets` とランチャー関数の変更、runner 本体の環境の組み立てと per-agent env allowlist の変更、pi の `auth.json` と各 adapter の key の扱い、移植元 #926
- 失敗とみなすこと: wrapper を通すと通常のシェルからの起動が変わる（今の環境の値が変わる、補わない名前が増える）。key がどこにも無いのに runner が黙って成功する

## wrapper の仕様（`tools/agent_runner/with_keys.py`）

- 起動の形: `python <PARENT_ROOT>/tools/agent_runner/with_keys.py -- <command> [args...]`。`uv run --project "$PARENT_ROOT" --locked` の中で実行し、`--` の後ろの `python` は uv の環境の python になる。リポジトリのルートを `sys.path` に足してから `tools.agent_runner.config` を import する（helper は任意の cwd から呼ばれるため）
- 引数: `--` が無い、または `--` の後ろが空なら、usage を stderr に出して終了コード 2
- 補う名前: runner の実効設定（wrapper と同じ checkout の `.devcontainer/agent-runner.toml` と、`resolve_config_path()` が返す個人設定。個人設定のファイルが無ければ雛形だけ）を `load_config` で読み、全 agent の `env` の和集合から `HOME`・`PATH` と `GIT_` で始まる名前を除いたもの。設定を読めない（`ConfigError`）ときは、分類名だけを stderr に出して終了コード 2。helper に `--template`・`--config` で別の設定を渡しても wrapper はそれを読まない（その設定だけにある名前は補わない）
- 補う条件: 今の環境に無いか、値が空の名前だけ。今の環境に値があれば、env ファイルに別の値があっても上書きしない
- 読み元: 今の環境 → `~/.config/create-reso-world/env`（`Path.home()` 基準）の順だけ。ファイルが無ければ何もしない。開けない・UTF-8 で読めないときは、パスだけを stderr に出して補わずに続ける
- 解析: shell として実行しない。1 行ずつ静的に読む。受け付ける行は `NAME=VALUE` と `export NAME=VALUE`（env ファイルは `set -a` で読まれるので `export` の有無を問わない）。値は、`$`・`` ` ``・`\` を含まない二重引用符の文字列、単一引用符の文字列、空白・引用符・`$`・`` ` ``・`\`・`;`・`|`・`&`・`<`・`>`・`(`・`)` を含まない裸の語のどれか。引用は外す。後ろには空白と `#` のコメントだけを付けられる。同じ名前が複数あれば最後の行を使う（`source` と同じ）。値が空の行では補わない
- 使わなかった行: 無視する（停止しない）。決定記録の D3
- 出力: 補った名前と読み元のパスだけを stderr に 1 行で出す（例: `with_keys: filled DEEPINFRA_TOKEN, OPENCODE_API_KEY from /home/vscode/.config/create-reso-world/env`）。値は出さない。補うものが無ければ何も出さない
- 起動: 補った環境で `os.execvpe` する。key が見つからない名前は補わずに起動し、agent の exec が今と同じエラーで失敗する

## runner を起動する経路の変更

runner を起動するコマンドを `uv run --project "$PARENT_ROOT" --locked python "$PARENT_ROOT/tools/agent_runner/with_keys.py" -- python <helper> ...` の形にし、各箇所の直後に「`with_keys.py` は、ランチャー起動セッションでも runner に key を届ける wrapper である（`.devcontainer/README.md` の「API トークン」節）」の 1 文を足す。

| 箇所 | 対象 |
| --- | --- |
| `.agents/skills/issue-to-pr/SKILL.md` | `review_design.py review` のコマンド、Spec レビューの段落（`review_spec.py review` も同じ wrapper を通すと書く）、`implement_task.py run` のコマンド |
| `.agents/skills/pr-review-fix-loop/scripts/loop.py` | `command("review", ...)` が返す `next` を wrapper 経由にする（他の subcommand は runner を起動しないので変えない） |
| `.agents/skills/review-fix-planning/references/execution.md` | `run_roles.py --phase implement`・`--phase self-review` の 2 つ |
| `.agents/skills/review-verify/references/fix-check.md` | `dispatch.py`（起動の行。`accept` は runner を起動しないので変えない）。Issue は review-verify の `SKILL.md` と書いているが、本リポジトリでは起動のコマンドがこの参照文書にある |
| `.agents/monitoring-runtimes.md` | 「agent-runner の同期実行と停止確認」の CLI の例 |
| `.devcontainer/README.md` | agent-runner の節の `run` の例 |

## Alibaba の runner agent

### `.devcontainer/claude-alibaba-exec`

移植元のものを元にする。

- `#!/bin/bash -p` と、その理由のコメント（継承した `BASH_ENV`・`ENV`・`BASH_FUNC_*` を読まない）
- キーの確認: `ccda` と同じく、`MAAS_ANTHROPIC_TOKEN` が ASCII の英数字を 1 文字も含まなければ、値を表示せずに固定文を stderr に出して `exit 1`。判定は `[[ $key == *[A-Za-z0-9]* ]]` とし、範囲を文字コードで比べるよう `shopt -s globasciiranges` を明示する（runner の子は `LANG`・`LC_*` を引き継がないので、locale に依らない書き方にする）。移植元の `LC_ALL=C` の `[[:graph:]]` は取り込まない
- 子の環境: `env -u MAAS_ANTHROPIC_TOKEN` で外し、`ANTHROPIC_BASE_URL=https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic`、`ANTHROPIC_AUTH_TOKEN="$key"`（`ANTHROPIC_API_KEY` は渡さない）、fable・opus を `qwen4-max-preview`、sonnet・haiku を `qwen3.8-flash`（`[1m]` なし）、`ENABLE_CLAUDEAI_MCP_SERVERS=false`、`CLAUDE_CODE_EFFORT_LEVEL=max`、`CLAUDE_CODE_MAX_OUTPUT_TOKENS=65536` を足して `claude "$@"` を exec する。値は `zshrc.txt` の `ccda` と揃え、片方を変えるときはもう片方も変えるとコメントに書く
- 実行権限 0755

### `.devcontainer/agent-runner.toml`

`[agents.claude-code_alibaba_opus_max]`（`runtime = "claude-code"`・`command = ["claude-alibaba-exec"]`・`model = "opus"`・`model_key = "qwen4-max-preview"`・`provider = "alibaba"`・`effort = "max"`・`env = ["HOME", "PATH", "MAAS_ANTHROPIC_TOKEN"]`）を `pi_deepinfra_deepseek4-flash_high` の後に足す。役割には既定で割り当てない。前のコメントに、呼ぶ exec、モデルの対応を `ccda` と揃えること、`model` が `opus` なので `claude-code_opus_default` と同じ役割に並べられないことを書く。

### `.devcontainer/install_beforehand.bash`

「Placing the launchers」の段の見出しに `claude-alibaba-exec` を足し、`pigema` の後に `install -m 0755 .devcontainer/claude-alibaba-exec "${HOME}/.local/bin/claude-alibaba-exec"`（失敗は `fail`）を足す。

## テスト

AGENTS.md の「テストの採用基準」で S（と F∩S）に当たるものだけを、各代表 1 件で足す。

1. `tools/agent_runner/tests/test_with_keys.py`（S）: 1 件のテスト。一時 HOME に env ファイルを置き、`AGENT_RUNNER_CONFIG` を一時ディレクトリの存在しないパスにして（利用者の個人設定を読まない）、wrapper を subprocess で起動し、子の環境を JSON で返させる。入力と確かめること:
   - env ファイルの `DEEPINFRA_TOKEN`（雛形の `pi_deepinfra_deepseek4-flash_high` の `env`）が、今の環境に無いとき子に届く
   - 今の環境に値がある `OPENCODE_API_KEY` は、env ファイルの別の値で上書きされない（別のアカウントの key で外部へ要求を送る失敗はエラーにならない）
   - どの agent の `env` にも無い `MESHY_API_KEY` は、env ファイルにあっても子に届かない
   - `$(...)` を含む行は実行も採用もされない（同じ名前の literal の行の後に置き、literal の値が残り、目印のファイルが作られない）
   - stderr に値が出ない
   偽の値は実行時に組み立てる（gitleaks の検出を避ける。AGENTS.md の「push の前の秘密情報の検査」）
2. `.devcontainer/test-herdr-migration.bash` の `test_alibaba_exec_requires_key`（S と F∩S）: `install_beforehand.bash` と同じくテスト用 HOME の `~/.local/bin` に置き、`env -i`（locale を渡さない）で直接起動する。`MAAS_ANTHROPIC_TOKEN=$' \xc2\xa0\xef\xbb\xbf\xe3\x80\x80'`（ASCII の空白・NBSP・BOM・全角空白）では非 0 で終わり、stub の `claude` が起動しない。通る例として、偽の有効な key では stub が起動し、`ANTHROPIC_AUTH_TOKEN` がその値で、`ANTHROPIC_API_KEY` と `MAAS_ANTHROPIC_TOKEN` が無く、`ANTHROPIC_BASE_URL` が `maas.aliyuncs.com` の接続先であることを確かめる。損害（ガードが外れても起動は成功し、claude.ai の認証情報が `maas.aliyuncs.com` に送られる）をコメントに書く。末尾の実行の一覧に足す

テストにしないもの: `loop.py` の `command("review")` の形（wrapper が無ければ起動のエラー、通らなければ agent が今と同じ認証エラーで止まる。L）、wrapper の usage と設定の読み込みの失敗（終了コード 2 とメッセージ。L）、SKILL.md・参照文書・README の文言（F）、agent-runner.toml の値（`check` が検証する。モデルは実機の `identity.model` で確かめる）、install の行（Rebuild で `launch_failed` として現れる。L）。

## ドキュメント（`.devcontainer/README.md`）

- 「API トークン」節に「ランチャー起動セッションから runner を使う（#401）」の小節を足す: 理由（`cc_launcher_unsets`）、起動の例、補う名前・条件・読み元と順序・解析の規則・使わなかった行の扱い・出力・起動、プロバイダごとの key の解決経路の表（今の環境・env ファイル・`~/.pi/agent/auth.json`・HOME 配下のログイン）。`OLLAMA_API_KEY`・`MAAS_ANTHROPIC_TOKEN` はファイルに置かないので wrapper では補えないこと、その場合は key を export した通常のシェルから runner を起動すること
- 「非対話エージェントのランナー（agent-runner）」節: `run` の例を wrapper 経由にし、ランチャー起動セッションからの使い方を 1 段落で書いて上の小節を指す
- 「Alibaba Cloud Model Studio の Token Plan で Claude Code を起動する（#397）」節: runner agent（`claude-code_alibaba_opus_max`）の表・起動の例・Rebuild が要ること（Rebuild 前は `launch_failed`）・同じ役割に並べられない組み合わせを足す
- 配置の一覧（手動の手順と、`~/.local/bin` に置くもの）に `claude-alibaba-exec` を足す

## 受け入れ基準

- 動作環境: Rebuild 後の Dev Container。プロバイダ切替ランチャーで起動した Claude Code セッションの Bash と、ランチャーを通さない通常のシェル。雛形と個人設定
- 実入力: そのセッションから wrapper 経由で行う短いプロンプトの runner 依頼（`inspect` 役割など）。env ファイルの実際の形（`KEY=VALUE`、`export` あり・なし、引用あり・なし、コメント行、空行、`$` の展開を含む行）
- 防御範囲（対象）: 上の「テスト」の 2 件と、Issue の受け入れ条件の実機の観測
- 防御範囲（対象にしない反例）: key がどこにも無いときの起動（今と同じエラーで失敗する）、ランチャー起動セッションからの Alibaba・Ollama の key の補い、`pi_commandcode_*`・xai・Google Vertex・cursor・devin・codex の個別の起動確認、他のランチャーの子への key の漏れ（`test-herdr-migration.bash` の既存の検査が引き続き通る）
- ローカルの完了条件: `bash .devcontainer/run-tests.bash`、agent_runner とスキルのテスト（`uv run --locked pytest tools/agent_runner .agents/skills`）、`bash scripts/check-layout.sh`、`uv run --locked python -m tools.agent_runner check` が通る。fake の HOME で wrapper を手で実行し、補った名前の 1 行だけが出て値が出ないことを確かめる

## マージの後に確かめる項目

この checkout では、実機の観測の前提がそろわない（このセッションはランチャー起動セッションではなく、`~/.config/create-reso-world/env` も無い。`claude-alibaba-exec` は Rebuild で `~/.local/bin` に入る）。次の観測はマージの後、Rebuild した環境で行い、PR 本文と Issue のコメントに残す。このため PR は `Refs #401` にする。

- ランチャー起動セッションから wrapper 経由で、OpenAI（`pi_openai-codex_gpt6-sol_xhigh`）・Anthropic（`claude-code_opus_default`）・DeepInfra（`pi_deepinfra_deepseek4-flash_high`）・OpenCode Go（`pi_opencode-go_deepseek4-flash_max`）の 4 attempt が起動し結果が返る。wrapper なしの DeepInfra は今と同じエラーで止まる（各 1 回）
- `MAAS_ANTHROPIC_TOKEN` を export した通常のシェルから `claude-code_alibaba_opus_max` が起動し、`identity.model` が `qwen4-max-preview` 系になる（1 回）
- 保存物（wrapper の stderr・runner のログ・`result.json`・summary）に key の値が無い

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | 読み元は今の環境 → `~/.config/create-reso-world/env` だけ | 移植元の `keys.env`・`~/.zshrc` | Issue の決定済み事項（2026-11-11 の利用者の回答） | 利用者の決定 |
| D2 | 補う名前は雛形 + 個人設定の全 agent の `env` の和集合（`HOME`・`PATH`・`GIT_*` を除く）。helper の `--template`・`--config` は読まない | 起動する agent の `env` だけを補う | runner の割り当て・fallback は helper の中で決まり、wrapper からは分からない。どの agent に渡すかは runner の per-agent allowlist が決めるので、和集合でも子に渡る範囲は今と同じ | Issue の指定 |
| D3 | 解析で使わなかった行は無視する | 停止する | env ファイルは zsh が `set -a; source` で読む一般の秘密情報のファイルで、runner に関係ない行（展開を使う値など）があっても正しい。止めると runner が使えなくなる。読めなかった key は補われず、agent が今と同じ認証エラーで止まるので、黙って成功しない | Issue の委任（wrapper の細部） |
| D4 | CLI は `python <PARENT_ROOT>/tools/agent_runner/with_keys.py -- <command>`、`sys.path` にルートを足す | `python -m tools.agent_runner.with_keys` | helper は任意の cwd から呼ばれ、`-m` はリポジトリのルートを cwd にする必要がある。移植元と同じ形 | Issue の委任 |
| D5 | 個人設定のパスは runner と同じ `resolve_config_path()` | 固定の `~/.config/agent-runner/config.toml` | `AGENT_RUNNER_CONFIG`・`XDG_CONFIG_HOME` を設定した利用者でも runner と同じ設定になる | Issue の委任 |
| D6 | pr-review の `review_run.py` は wrapper 経由にしない | 同じ扱いにする | `review_run.py` は runner を起動しない（runner の子と `after_run` が呼ぶ）。runner を起動するのは `loop.py review`・`run_roles.py`・`dispatch.py`・issue-to-pr の helper と CLI だけ | Issue の委任（移植元に無い経路） |
| D7 | review-verify は `references/fix-check.md` の `dispatch.py` の起動を変える | Issue の文言どおり `SKILL.md` | 本リポジトリでは起動のコマンドが `references/fix-check.md` にあり、`SKILL.md` に起動のコマンドが無い | Issue の委任 |
| D8 | `AGENTS.md` の「エージェント運用」の runner の起動の一文は変えない | wrapper を書き足す | 起動手順は `.agents/monitoring-runtimes.md` と各スキルが受け持ち、`AGENTS.md` はそこを指している。Issue の対象一覧にも無い | 推奨案で決定 |
| D9 | `claude-alibaba-exec` のガードは `[[ $key == *[A-Za-z0-9]* ]]` と `shopt -s globasciiranges` | 移植元の `LC_ALL=C` の `[[:graph:]]` | Issue の指定（`ccda` と同じ判定）。`globasciiranges` を明示して、範囲の比較が locale に依らないことをコードで示す | Issue の指定 |
| D10 | 実機の観測はマージの後に行い、PR は `Refs #401` | マージの前に行う | このセッションはランチャー起動セッションではなく、env ファイルも無く、`claude-alibaba-exec` は Rebuild で入る。前提を作るには利用者の env ファイルや HOME を変える必要があり、許可範囲の外 | issue-to-pr の「マージの後でなければ確かめられない項目」 |
| D11 | テストは with_keys の 1 件と alibaba-exec の 1 件（通る例を含む） | 移植元と同じ（通る例なし） | AGENTS.md の D の規則（拒否のテストに通る例を残す）と、上書きしないことの守り | テストの採用基準 |

## 割り当て（2 章の検査の結果）

- Task の実装: `devin_swe2_max`（`--implement` の明示。`fallback` は無し。`self` は false）
- 設計レビュー: `pi_openai-codex_gpt6-sol_xhigh`（`--design-review` の明示。`fallback` は無し）
- Spec レビュー: `devin_swe2_max`（`--spec-review` の明示。`fallback` は無し）。Spec レビューがあるので builder check は行わない
- PR 修正ループ（`check-options`）: `max_cycles` 3（既定の適用）、`inspect` = `pi_xai_grok4_xhigh`・`pi_openai-codex_gpt6-sol_xhigh`（利用者の指定）、fix の `implement` = `devin_swe2_max`（利用者の指定）、`self-review`・`fix-check` = `self`（雛形の既定の適用）

## builder に任せること

- wrapper の関数の分け方と型、正規表現の書き方
- README の小節の文章と表の行の並び
- テストの補助関数の形
