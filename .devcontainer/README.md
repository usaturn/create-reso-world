# 個人開発環境

このディレクトリには、resoloop と Blender を使うワークスペース向けの
Dev Container 設定とエージェント用ツールのセットアップを置く。

`postCreateCommand` は `/bin/bash .devcontainer/install_beforehand.bash` である。
`.devcontainer/` を変更した場合は Dev Containers: Rebuild Container を実行する。
導入するツールと、その mount・シェル設定の対応は「導入ツール一覧」の表にまとめる。
`devcontainer.json`、`initialize.bash`、`install_beforehand.bash`、`zshrc.txt` はこの表に従う。
Herdr の復元手順は `.devcontainer/docs/herdr-session-cwd-restore.md` を参照する。

`cleanup-workspace.bash` はレビュー用の一時ディレクトリを、安全条件を確かめてから掃除する。
手動で確認するときは `WORKSPACE_CLEANUP_DRY_RUN=1 bash .devcontainer/cleanup-workspace.bash` を使う。
掃除先は `WORKSPACE_CLEANUP_TMP_ROOT`、定期実行の状態保存先は
`WORKSPACE_CLEANUP_STATE_DIR` で変更できる。

## 導入ツール一覧

各ツールの導入方法、bind mount するホスト側のパス、ホスト側で先に作るパス（`initialize.bash`）、
`zshrc.txt` の関数と alias、`update()` の項目の対応である。mount と `initialize.bash` の列は
`.devcontainer/test-readme.bash` がそれぞれのファイルと突き合わせる。

<!-- tool-table:start -->
| ツール | 導入方法 | mount | initialize.bash の mkdir | zshrc の関数 | update() の項目 |
| --- | --- | --- | --- | --- | --- |
| Claude Code | installer（`claude.ai/install.sh`）。プラグインは `.claude/settings.json` の `enabledPlugins` と同じ 5 つ | `~/.claude`、`~/.claude.json` | `~/.claude`、`~/.claude.json`（touch） | `ccd`（alias）、`ccda`、`ccdd`、`ccddg`、`ccdu` | `claude update` |
| Codex | `npm install -g @openai/codex@latest` | `~/.codex` | `~/.codex` | `cod` | `npm install -g @openai/codex@latest` |
| pi | `npm install -g` で本体、`pi install` で拡張。ランチャー 9 本を `~/.local/bin` に置く | `~/.pi` | `~/.pi` | — | `pi update`、`pi update --extensions` |
| Cursor | installer（`cursor.com/install`） | `~/.cursor`、`~/.local/share/cursor-agent` | `~/.cursor`、`~/.local/share/cursor-agent` | `cur`（alias） | `agent update` |
| Devin | installer（`cli.devin.ai/install.sh`） | `~/.local/share/devin`、`~/.config/devin` | `~/.local/share/devin`、`~/.config/devin` | `dev`（alias） | `devin update`、`devin plugins update superpowers` |
| dsh | `npm install -g @deepseek-ai/dsh@0.1.5-rc.1`（版を固定） | `~/.dsh` | `~/.dsh` | — | —（版を固定しているので更新しない） |
| gh | Dev Container Feature（github-cli） | `~/.config/gh` | `~/.config/gh` | — | — |
| grok / gcloud / glab / bun | 未導入（参照だけ残す） | `~/.grok`、`~/.config/gcloud`、`~/.config/glab-cli` | `~/.grok`、`~/.config/gcloud`、`~/.config/glab-cli` | `genv`（gcloud）、`buni`（bun） | `grok update` |
| 秘密情報 | — | `~/.config/create-reso-world` | `~/.config/create-reso-world`（mode 700） | env ファイルがあれば読み込む | — |
<!-- tool-table:end -->

未導入のツールを呼ぶ関数（`cod`、`genv`、`buni`）は、コマンドが無ければ理由を表示して 127 を返す。
`update()` は無いツールの項目を飛ばし、飛ばした項目を表示する。

## 秘密情報

API トークンなどの秘密情報は、ホストの `~/.config/create-reso-world/env` に置き、リポジトリには置かない。
このディレクトリは Dev Container に bind mount され（`initialize.bash` がホスト側に mode 700 で作る）、
`zshrc.txt` がシェルの起動時に `env` を読み込んで、書いた変数をすべて export する。ファイルが無ければ何もしない。

```bash
# ホスト側で一度だけ作る
mkdir -p ~/.config/create-reso-world && chmod 700 ~/.config/create-reso-world
touch ~/.config/create-reso-world/env && chmod 600 ~/.config/create-reso-world/env
```

書式は `KEY=VALUE` の 1 行 1 変数である（zsh が読むので、空白や記号を含む値は引用符で囲む）。
対象は `DEEPINFRA_TOKEN`、`COMMANDCODE_API_KEY`、`OPENCODE_API_KEY`、`MAAS_ANTHROPIC_TOKEN`、`CONTEXT7_API_KEY` などで、
書き換えたら新しいシェルを開く。

## テストの実行

リポジトリのルートで次を実行する。CI（`.github/workflows/ci.yml`）も同じコマンドを実行する。

```bash
bash .devcontainer/run-tests.bash          # .devcontainer/test-*.bash と tests/scripts/*.bash（CI の devcontainer-tests）
bash scripts/check-layout.sh               # リポジトリのレイアウト（CI の layout。resoloop が無ければ skills sync の検査を skip）
uv run pytest tests/skills .agents/skills  # スキルのテスト（CI の skill-tests）
(cd slum02 && uv run pytest)               # 各プロジェクトのテスト（MyResoniteProject・akichi・slum02 で同じ）
```

テストは一時ディレクトリの `HOME` と、モックの resoloop・dotnet・Blender を使うので、実環境を変えない。
1 本だけ実行するときは `bash .devcontainer/run-tests.bash <テストのパス>` のように渡す。
CI の gitleaks ジョブは `.gitleaks.toml`（既定の規則に、resoloop のマニフェストが持つ識別子の除外を足したもの）で
秘密情報の混入を検査する。CI では Blender によるワールドのビルドは行わない。

## Resonite ワールド開発ツール

Dev Container の作成時に .NET 10 SDK と Blender を導入し、ResoLoop を
`.devcontainer/resoloop.lock` が指定する版で導入する。nuget モードでは
NuGet の公開版を `dotnet tool` で導入する。fork モードでは
`scripts/resoloop-fork.sh install` が fork を `external/resoloop` に取得してビルドするため、
ネットワークと数分の時間を要する。版の変え方と fork の運用は `docs/resoloop-fork-workflow.md` を参照する。
Blender は画面を開かずに実行する。Resonite 本体と ResoniteLink は
Windows ホスト側で準備する。接続確認の `resoloop doctor`、
Blender の GUI、ホスト側のネットワーク設定はこのセットアップの対象外とする。

コンテナの resoloop から ResoniteLink に届くことが前提である。WSL2 の mirrored networking
（`.wslconfig` の `networkingMode=mirrored`）でホストの localhost を共有するか、
`resoloop discover` で ResoniteLink の告知を確かめ、`--url ws://<ホスト>:<ポート>` または
環境変数 `RESONITE_LINK_URL` で接続先を指定する。
ProtoFlux 用の flux-sdk はこの環境の対象外で、導入しない。

導入を確認するにはコンテナ内で次を実行する。

```bash
dotnet --list-sdks
resoloop --version
bash .devcontainer/verify-resonite-tooling.bash
bash scripts/resoloop-fork.sh status
```

ResoLoop の公式要件には Windows 10/11 が記載されている。Linux で
CLI が動作しない場合は `postCreateCommand` を失敗とし、成功扱いにはしない。

## エージェントの読み込みの制約

プロジェクト（`slum02/` など）を cwd にしてエージェントを起動したとき、次の 2 つはスキルの一部が見えない。

- Cursor は workspace 配下の `.agents/skills` しか読まないため、ルートの共有スキルが見えない。
  プロジェクトの resonite-* スキルは見える
- dsh は git のルートの `.agents/skills` しか読まないため、プロジェクトの resonite-* スキルが見えない。
  ルートの共有スキルは見える

Codex はルートとプロジェクトの `AGENTS.md` を直接読むため、`~/.codex/config.toml` で
`CLAUDE.md` を指示ファイルとして読ませる設定（`project_doc_fallback_filenames`）は不要である。
既に設定してあっても害は無い。

## Herdr サイドバーの設定移行

`install_beforehand.bash` は `~/.config/herdr/config.toml` が存在しないときだけ
`.devcontainer/herdr.toml` をコピーする。既に config を持っている環境では、
`.devcontainer/herdr.toml` の変更は自動では反映されない。

反映するには次を実行する。

```bash
cp ~/.config/herdr/config.toml ~/.config/herdr/config.toml.bak
cp .devcontainer/herdr.toml ~/.config/herdr/config.toml
herdr config check
herdr server reload-config
```

`herdr config check` が `config: ok` を返さない場合は適用せず、バックアップへ戻す。
個別に手を入れた設定がある場合は、`.devcontainer/herdr.toml` と既存 config の
差分を既存 config へ移す。

各エージェントは PATH 上の `herdr-agent-task` でタスク名を投稿する。
使い方は `.agents/skills/herdr-agent-task/SKILL.md` を参照する。

## エージェント向けツールの導入

`install_beforehand.bash` は Claude Code のプラグインと各種エージェント用 CLI を
導入する。Dev Container を使う限り手動実行は不要で、リビルド時も自動で再実行される。

Dev Container を使わないローカル環境のみ、以下を手動で順に実行する。

1. `claude plugin marketplace add dashed/claude-marketplace`
2. `claude plugin install example-skills@anthropic-agent-skills`
3. `claude plugin install superpowers@claude-plugins-official`
4. `claude plugin install feature-dev@claude-plugins-official`
5. `claude plugin install web-quality-skills@addy-web-quality-skills`
6. `claude plugin install ripgrep@alberto-marketplace`
7. `npm install -g @openai/codex@latest`
8. `mkdir -p ~/.pi/agent && cp .devcontainer/pi-models.json ~/.pi/agent/models.json`
9. `mkdir -p ~/.local/bin && install -m 0755 .devcontainer/pigo ~/.local/bin/pigo`
10. `install -m 0755 .devcontainer/pigod ~/.local/bin/pigod`
11. `install -m 0755 .devcontainer/pigou ~/.local/bin/pigou`
12. `install -m 0755 .devcontainer/piccg ~/.local/bin/piccg`
13. `install -m 0755 .devcontainer/piccd ~/.local/bin/piccd`
14. `install -m 0755 .devcontainer/piga ~/.local/bin/piga`
15. `install -m 0755 .devcontainer/pigs ~/.local/bin/pigs`
16. `install -m 0755 .devcontainer/pigl ~/.local/bin/pigl`
17. `install -m 0755 .devcontainer/pixg ~/.local/bin/pixg`
18. `zsh .devcontainer/setup_pi_superagents.zsh`

プラグインの有効化は `.claude/settings.json` の `extraKnownMarketplaces` と
`enabledPlugins` で行う。設定の反映には Claude Code の再起動が必要である。

## pi のモデル定義とランチャー

`~/.pi` は `devcontainer.json` で bind mount している。認証情報
（`~/.pi/agent/auth.json`）とモデル定義（`~/.pi/agent/models.json`）が
ホスト側に残るため、リビルド後に `.devcontainer/setup_pi.zsh`、
`.devcontainer/setup_pi_opencode_go.zsh`、`.devcontainer/setup_pi_commandcode_goat.zsh`
を実行し直す必要はない。

`install_beforehand.bash` は次のものを配置する。挙動が異なるのは、
models.json だけが bind mount の内側で、他が外側にあるためである。

- `.devcontainer/pi-models.json` → `~/.pi/agent/models.json`。
  bind mount 側を正とし、ファイルが**無い場合のみ**配置する。毎回上書きすると、
  ホスト側で加えたモデル定義の変更がリビルドで失われる
- `.devcontainer/pigo` → `~/.local/bin/pigo`。`~/.local/bin` は bind mount の
  対象外でリビルドのたびに失われるため、毎回上書きで配置する
- `.devcontainer/pigod` → `~/.local/bin/pigod`。pigo と同じ理由で毎回上書き
- `.devcontainer/pigou` → `~/.local/bin/pigou`。pigo と同じ理由で毎回上書き
- `.devcontainer/piccg` → `~/.local/bin/piccg`。pigo と同じ理由で毎回上書き
- `.devcontainer/piccd` → `~/.local/bin/piccd`。pigo と同じ理由で毎回上書き
- `.devcontainer/piga`・`pigs`・`pigl` → `~/.local/bin/`。同様に毎回上書き
- `.devcontainer/pixg` → `~/.local/bin/pixg`。同様に毎回上書き
- `.devcontainer/pi-superagents/<launcher>.json` → `~/.pi/agent/extensions/subagent.d/<launcher>/config.json`、
  `.devcontainer/pi-superagents-exec.zsh` → `~/.local/bin/pi-superagents-exec.zsh`。
  `install_beforehand.bash` は `setup_pi_superagents.zsh` を呼んでこの 2 種を配置する
  （詳細は後述の「pi-superagents のランチャー別 model tier」を参照）
- `.devcontainer/setup_pi_tool_display.py` は
  `~/.pi/agent/extensions/pi-tool-display/config.json` の Bash override だけを
  `false` にする。既存設定の他の項目は保持する

`~/.local/bin` への PATH は `zshrc.txt` が通すため、別途の設定は不要である。

### モデル定義の正

独自のモデル定義は `.devcontainer/pi-models.json` を単一の情報源とする。
`install_beforehand.bash` も 3 つの setup スクリプトも、定義を埋め込まずこの
ファイルから読む。定義を変更するときはこのファイルを編集してコミットする。
`openai-codex` の GPT-6 モデルと `xai` の Grok 4.7 は Pi の組み込みカタログを
使うため、このファイルには追加しない。

`pigo` は pi を `opencode-go` プロバイダの `muse-spark-1.3-contributor` で
起動するラッパーである。このモデルは pi の組み込みカタログ
（`~/.pi/agent/models-store.json`）に無いため `pi-models.json` で定義する。
定義には `baseUrl`（`https://opencode.ai/zen/go/v1`）が必須で、省略すると
リクエストが opencode-go のエンドポイントに解決されず 404 になる。
また `reasoning.effort` に `max` は指定できない（`none` / `minimal` / `low` /
`medium` / `high` / `xhigh` のみ）ため、`thinkingLevelMap` で `max` を `xhigh` に
対応付けている。

`pigod` は同じ `opencode-go` プロバイダを、既定モデル `deepseek-v4.1-flash` で
起動するラッパーである。`pigo` と違い `pi-models.json` には何も足していない。
`deepseek-v4.1-flash` は pi のモデルカタログ（`~/.pi/agent/models-store.json`）
に `baseUrl`（`https://opencode.ai/zen/go/v1`）付きで存在するため、
`--provider opencode-go` の指定だけでエンドポイントに解決される。カタログは
`pi update --models` で更新されるので、写しを `pi-models.json` に置かずに追随
できる。

カタログは pi.dev 側で更新されるため、モデル ID が改名されることがある。
ID は表示名と一致しないので、ランチャーの ID は必ず `pi --list-models` で
確認する。2026-09-11 に `deepseek-flash` が `deepseek-v4.1-flash` へ改名され、
旧 ID を残していた `pigod` は次の警告を出したうえで `opencode-go` の既定モデル
（`kimi-k2.6`）の定義を複製したモデルで起動していた:

```console
Warning: Model "deepseek-flash" not found for provider "opencode-go". Using custom model id.
```

この状態でもリクエスト自体は通るため気づきにくいが、kimi-k2.6 の定義が
使われる結果、context window は 262,144（本来は 1,000,000）、max output は
65,536（本来は 384,000）になり、`supportsReasoningEffort` が false のため
`--thinking max` の `reasoning_effort` も送られない。
`.devcontainer/setup_pi_opencode_go.zsh` の手順 6 は各ランチャーのモデル ID を
`pi --list-models` で検証するので、この種の改名は setup の時点で失敗する。

ID と表示名が一致しないモデルなので注意する。カタログ上の表示名は
`DeepSeek V4.1 Flash` で、ID は `deepseek-v4.1-flash` である。
`deepseek-v4-flash`（表示名 `DeepSeek V4 Flash`、テキスト入力のみ）と
`deepseek-v4-pro` は別のモデルである。

`--thinking max` はこのモデルでも有効である。pi は `thinkingLevelMap` の
`max -> "max"` をそのまま `reasoning_effort` として送り、opencode-go はそれを
受理する。このエンドポイントが受け付ける `reasoning_effort` は `none` /
`minimal` / `low` / `medium` / `high` / `xhigh` / `max` の文字列だけで、数値は
受け付けない（`50` や `100` を送ると 400 になる）。許容値は不正値を送ったときに
エンドポイント自身が返す検証エラーで確認できる。

`pigou` は同じ `opencode-go` プロバイダを、既定モデル `union-alpha`（表示名
`Union Alpha Free`）で起動するラッパーである。Union Alpha Free は OpenCode が
期間限定で無料提供するステルスモデルで、context window は 262,144、
max output は 131,072、画像入力に対応する。

`union-alpha` は pi のモデルカタログに無いため、`pigo` と同じく定義は
`pi-models.json` 側にある。ただし api が異なり、このモデルは
`openai-completions` / `openai-responses` では 500 を返し、Anthropic 互換の
`https://opencode.ai/zen/go/v1/messages` だけで応答する。そのため定義の
`api` は `anthropic-messages` で、`baseUrl` は `/v1` を付けない
`https://opencode.ai/zen/go` である（Anthropic SDK が `/v1/messages` を補う）。
また Go エンドポイントは `x-opencode-session` ヘッダを必須とするが、pi は
provider が `opencode-go` のモデルへ `x-opencode-session` と
`x-opencode-client` を自動で付与するため、ランチャー側での対応は不要である。

`union-alpha` は `thinking` パラメータを受理するが reasoning ブロックを
返さないため `reasoning: false` としている。`--thinking max` は他ランチャーとの
統一のため残しており、実装上は送られない。無料枠の提供は期間限定なので、
提供終了後は `pi-models.json` の定義とこのランチャーを外す。

`piccg` は Muse Spark 1.3 を Command Code GOAT 経由
（`commandcode` プロバイダ、既定モデル `meta/muse-spark-1.3`）で
起動するラッパーである。`meta/muse-spark-1.3-contributor` も定義済みで、
対話中の `/model`（または Ctrl+L）や Ctrl+P で切り替えできる。commandcode は pi の built-in provider では
ない（`opencode-go` と異なる）ため、deepinfra と同じく provider を完全定義
する: `baseUrl`（`https://api.commandcode.ai/provider/v1`）、`apiKey`
（`$COMMANDCODE_API_KEY` を実行時に環境変数から解決）、`api`
（`openai-completions`）、`authHeader`（Bearer 認証）。auth.json は使わない。
`thinkingLevelMap` は opencode-go 版の定義を踏襲し、`pigo` と同じく
`--thinking max` で起動する。GOAT プランはサブスクリプション制で、
リクエスト上限は 5 時間 $14・週 $35・月 $70 の使用量までである。

`piccd` は同じ `commandcode` プロバイダを共有し、既定モデルだけを
`deepseek/deepseek-v4.1-flash` に替えたラッパーである。`--models` はこの
1 件だけなので、Ctrl+P の切替候補も DeepSeek のみになる。reasoning は
`low` / `medium` / `high` / `xhigh` / `max` を受け付ける一方 `minimal` は
拒否するため、`thinkingLevelMap` は `minimal` を `low` に寄せ、他は恒等に
対応付けている。`max` をそのまま送れるので、piccg のような `xhigh` への
丸めは不要である。画像入力には対応せず `input` は `["text"]` としている
（画像は別モデル `deepseek/deepseek-v4-flash-vision-exp` が担う）。

既存の `~/.pi/agent/models.json` がある環境では、初回だけ
`zsh .devcontainer/setup_pi_commandcode_goat.zsh` を実行して `commandcode`
プロバイダを反映する必要がある。`install_beforehand.bash` は `piccg` と
`piccd` を毎回配置する一方 models.json は既存ファイルを上書きしないため、
この一度の実行を省くと `piccg` が pi の `Unknown provider "commandcode"` で
落ちる（`piccg` 自身がこれを検出して setup スクリプトの実行を案内する）。

`piccd` は provider の有無だけでなくモデルの有無も見る。commandcode の
プロバイダ定義はあるが DeepSeek のモデル定義だけが無い環境（piccg を一度
実行済みの環境がこれに当たる）では、pi が
`No models matching "deepseek/deepseek-v4.1-flash"` で落ちるためである。
`piccd` はこの場合も setup スクリプトの実行を案内する。

### ChatGPT Pro の GPT-6 ランチャー

| launcher | Provider / Model |
|---|---|
| `piga` | `openai-codex/gpt-6-astra` |
| `pigs` | `openai-codex/gpt-6-sol` |
| `pigl` | `openai-codex/gpt-6-luna` |

3 つとも ChatGPT Pro サブスクリプションの Codex OAuth 認証を使う。
`OPENAI_API_KEY` は不要で、OpenAI API のキー課金用 provider には接続しない。
初回だけ素の `pi` を起動して `/login openai-codex` を実行し、ログインする。
OAuth 情報は `~/.pi/agent/auth.json` に保存される。`~/.pi` は Dev Container に bind mount
されているため、リビルド後もログイン状態を保持する。認証は対話操作が必要で、
`postCreateCommand` から自動ログインしない。未認証のままランチャーを起動した
場合は、このログイン手順を表示して終了する。

GPT-6 Sol / Luna のため Pi 0.87.1 以上が必要。利用前に `pi --version` を確認し、
ログイン後に各モデルが `openai-codex` 行にあることを確認する。

```bash
pi --version
pi --list-models gpt-6-astra
pi --list-models gpt-6-sol
pi --list-models gpt-6-luna
```

モデル行が無い場合は Pi を更新する。`pi --list-models` は利用可能なモデルを
表示するため、未認証時には Pi がモデル定義を持っていても `openai-codex` 行は
表示されない。3 ランチャーは `--thinking xhigh` で起動する。子 Pi の
`cheap` / `balanced` / `max` tier はランチャーごとに GPT-6 Luna / Sol / Astra
を割り当てる（下表を参照）。ログイン済みの環境では、次のテストでも Pi の版と
3 モデルを検証できる。

```bash
PI_CODEX_LIVE_CHECK=1 bash .devcontainer/test-pi-openai-codex.bash
```

### SuperGrok / X Premium の Grok 4.7 ランチャー

| launcher | Provider / Model |
|---|---|
| `pixg` | `xai/grok-4.7` |

`pixg` の親 Pi と `balanced` / `max` tier は SuperGrok または X Premium
サブスクリプションの xAI OAuth 認証を使い、`cheap` tier の子 Pi は
OpenAI Codex OAuth 認証で GPT-6 Luna を使う。`XAI_API_KEY` は不要で、
xAI API のキー課金には接続しない。
初回だけ素の `pi` を起動して `/login xai` を実行し、
`Sign in with SuperGrok or X Premium` からログインした後、
`/login openai-codex` も実行する。両プロバイダの OAuth 情報は
`~/.pi/agent/auth.json` に保存される。`~/.pi` は Dev Container に bind mount
されているため、リビルド後もログイン状態を保持する。認証は対話操作が必要で、
`postCreateCommand` から自動ログインしない。いずれかが未認証なら、
`pixg` は xAI、OpenAI Codex の順に認証を確認し、最初に見つかった
未認証プロバイダのログイン手順だけを表示して起動前に終了する。

Grok 4.7 と GPT-6 Luna は Pi の組み込みカタログにあるため、`pi-models.json`
への定義追加は不要である。両方ログインした後、それぞれのモデルを確認する。

```bash
pi --list-models xai
pi --list-models gpt-6-luna
```

モデル行が無い場合は Pi を更新する。`pi --list-models` は利用可能なモデルを
表示するため、未認証時には Pi がモデル定義を持っていても該当する
プロバイダの行は表示されない。`pixg` は `--thinking xhigh` で起動する。
Grok 4.7 の thinking level は `low` / `medium` / `high` / `xhigh` で、
`xhigh` が実際の最大値である。子 Pi は `cheap` が
`openai-codex/gpt-6-luna` の `xhigh`、`balanced` が `xai/grok-4.7` の
`high`、`max` が `xai/grok-4.7` の `xhigh` を使う。未認証時に別モデルへ
自動フォールバックはしない。

### pi-distill の分離（Main / Distillation）

リポジトリ既定では Main は起動時に選んだモデルを使い、Distillation だけを
`deepinfra-distill/openai/gpt-oss-20b` へ送る。`zshrc.txt` で
`PI_DISTILL_MODEL` と `PI_DISTILL_ERROR_RETRY_COUNT=0` を設定しており、認証エラーや
provider エラーなどの非タイムアウト失敗は再試行しない。タイムアウト再試行
（`PI_DISTILL_TIMEOUT_RETRY_COUNT`）は変更していない。

Distillation 専用の `deepinfra-distill` provider は通常利用の `deepinfra` から分離しており、
`reasoning: false` と `reasoning_effort: "none"` で Distillation に不要な reasoning token を
最小化する。実測上は `reasoning_content` が残るため、reasoning の完全停止は保証しない。

このため `pigo`（Main は OpenCode Go）を使う場合も、Distillation を成功させる
には `DEEPINFRA_TOKEN` が必要である。未設定でも Main は利用でき、Distillation
の失敗は pi-distill の fail-open により元のツール出力を保持する。

`~/.pi/agent/extensions/pi-distill/config.json` に `model` または
`errorRetryCount` がある場合、その値が環境変数より優先される。`model` が空文字の
場合は Main モデルを使い、DeepInfra へは送らない。`/config:distill` の UI は
スラッシュを 1 つしか受け付けないため、`deepinfra-distill/openai/gpt-oss-20b`
を UI から入力すると検証エラーになる。その値を設定するときは config.json を
直接編集する。`/config:distill` で保存した利用者設定は意図的な上書きとして尊重し、
セットアップから作成・上書き・削除しない。

#### Bash tool のセッション環境変数

`pi-distill` と同時に読み込まれる `pi-extensions-tool-display` の Bash override
では、Pi 標準 Bash tool にセッション情報が渡らず、LLM が呼ぶ Bash tool 内の
`PI_PROVIDER`、`PI_MODEL`、`PI_SESSION_ID`、`PI_REASONING_LEVEL` が空になる。
`install_beforehand.bash` は `pi-distill` のインストール後に
`.devcontainer/setup_pi_tool_display.py` を実行し、`registerToolOverrides.bash` だけを
`false` にする。これにより Pi 標準 Bash tool が実行を担当し、`pi-distill` の
tool result 圧縮は続く。Bash 専用の tool-display 表示は使えなくなる。

既存環境へ反映するときは、リポジトリのルートで次を実行し、Pi で `/reload` する。

```bash
uv run --no-project .devcontainer/setup_pi_tool_display.py
```

スクリプトは `PI_CODING_AGENT_DIR` を指定している場合、その agent directory 内の
設定を変更する。既存 JSON が壊れている場合は上書きせずエラーにする。
確認時は `!` コマンドではなく、LLM に Bash tool で次を実行させる。

```bash
printf 'provider=<%s> model=<%s> session=<%s> reasoning=<%s>\n' \
  "$PI_PROVIDER" "$PI_MODEL" "$PI_SESSION_ID" "$PI_REASONING_LEVEL"
```

`/model` でモデルを切り替えて再実行すると provider / model が更新され、同じ
session ID が維持される。長い Bash 出力の後に `/distill:stats` で圧縮実績を確認する。

既存環境では `zsh .devcontainer/setup_pi.zsh` を一度実行し、`deepinfra` と
`deepinfra-distill` を `~/.pi/agent/models.json` へ同期する
（`install_beforehand.bash` は既存ファイルを上書きしないため）。

### setup スクリプトを使う場面

`.devcontainer/setup_pi.zsh`（deepinfra / deepinfra-distill）、`.devcontainer/setup_pi_opencode_go.zsh`
（opencode-go）、`.devcontainer/setup_pi_commandcode_goat.zsh`（commandcode）は、
リビルドのたびに実行するものではない。次の場面で使う。

- API キーをローテーションしたとき（`setup_pi_opencode_go.zsh` が
  `auth.json` を書き換える。commandcode は環境変数参照なので
  キーのローテーションで setup スクリプトの実行は不要）
- ホスト側の `~/.pi` を作り直したとき
- `pi-models.json` を編集し、既存の `~/.pi/agent/models.json` へ反映したいとき
  （`install_beforehand.bash` は既存ファイルを上書きしないため）

いずれも冪等で、`providers` のうち対象プロバイダのエントリだけを置き換える。
`setup_pi_opencode_go.zsh` は `.devcontainer/pigo`・`.devcontainer/pigod`・
`.devcontainer/pigou` を、`setup_pi_commandcode_goat.zsh` は
`.devcontainer/piccg` と `.devcontainer/piccd` をそのまま配置するため、
実行してもランチャの内容は `install_beforehand.bash` の配置結果と一致する。

commandcode の 2 つのランチャを `setup_pi_commandcode_goat.zsh` が同居して
受け持つのは、両者が同じ `providers.commandcode` エントリを共有するためで
ある。スクリプトを分けると 2 本が同じエントリを全置換し合い、片方だけを
実行した時点で他方のモデル定義が `models.json` から消える。

### API トークン

`OPENCODE_API_KEY`、`DEEPINFRA_TOKEN`、`COMMANDCODE_API_KEY` は、「秘密情報」の節の
`~/.config/create-reso-world/env` に書けばシェルの起動時に export される。書かない場合は、
必要なときに手動で export する。

- `OPENCODE_API_KEY` は `pigo`・`pigod`・`pigou` の実行には不要である。bind mount した
  `auth.json` に資格情報が残るため、pi はそこから読む
  （`pi auth check --provider opencode-go` が `ready` を返す）。
  `setup_pi_opencode_go.zsh` でキーを更新するときだけ必要になる
- `DEEPINFRA_TOKEN` は `models.json` の `apiKey` が `$DEEPINFRA_TOKEN` を
  参照するため、deepinfra を使うシェルで export しておく必要がある。
  `pigo` / `pigod` / `pigou`（Main は OpenCode Go）を使う場合も、Distillation は
  DeepInfra へ送るため成功には `DEEPINFRA_TOKEN` が必要である
- `COMMANDCODE_API_KEY` は `DEEPINFRA_TOKEN` と同じ方式である。`models.json`
  の `apiKey` が `$COMMANDCODE_API_KEY` を参照するため、`piccg` と `piccd` を
  使うシェルで export しておく必要がある。未設定のまま実行すると
  ランチャがエラーメッセージを出して終了する。キーは
  `https://commandcode.ai/settings/keys` で作成する

### pi-superagents のランチャー別 model tier

`@teelicht/pi-superagents` は Superpowers の Plan を Pi 自身の子プロセスで実行する拡張で、子 Pi のモデルを `cheap` / `balanced` / `max` の 3 tier で選ぶ。tier の定義は拡張が `~/.pi/agent/extensions/subagent/config.json` から読むが、このパスは拡張のソースに直接書かれており、環境変数による切り替えができない。

そのためランチャーは、自分専用の設定ディレクトリを `bwrap` の mount namespace でこの共有パスへ重ねて Pi を起動する。

```
~/.pi/agent/extensions/subagent.d/pigo/config.json  →  ~/.pi/agent/extensions/subagent/config.json
```

`HOME` は変えないので git / ssh の設定の見え方には影響せず、共有ファイルを書き換えないので複数のランチャーを同時に起動しても設定が混線しない。子 Pi は namespace を継承するため、親子で同じ tier を見る。

ただし `bwrap` は `no_new_privs` を立てるため、ランチャー配下では `sudo` / `su` が使えない。sudo が要る作業は、ランチャーを通さない素の `pi` か別のターミナルで行う。

| launcher | cheap | balanced | max |
|---|---|---|---|
| `pigo` | `opencode-go/muse-spark-1.3-contributor` | `opencode-go/muse-spark-1.3-contributor` | `opencode-go/deepseek-v4.1-flash` |
| `pigod` | `opencode-go/muse-spark-1.3-contributor` | `opencode-go/deepseek-v4.1-flash` | `opencode-go/deepseek-v4.1-flash` |
| `pigou` | `opencode-go/union-alpha` | `opencode-go/union-alpha` | `opencode-go/union-alpha` |
| `piccg` | `commandcode/meta/muse-spark-1.3-contributor` | `commandcode/meta/muse-spark-1.3-contributor` | `commandcode/deepseek/deepseek-v4.1-flash` |
| `piccd` | `commandcode/meta/muse-spark-1.3-contributor` | `commandcode/deepseek/deepseek-v4.1-flash` | `commandcode/deepseek/deepseek-v4.1-flash` |
| `piga` | `openai-codex/gpt-6-luna` | `openai-codex/gpt-6-sol` | `openai-codex/gpt-6-astra` |
| `pigs` | `openai-codex/gpt-6-luna` | `openai-codex/gpt-6-sol` | `openai-codex/gpt-6-sol` |
| `pigl` | `openai-codex/gpt-6-luna` | `openai-codex/gpt-6-sol` | `openai-codex/gpt-6-sol` |
| `pixg` | `openai-codex/gpt-6-luna` | `xai/grok-4.7` | `xai/grok-4.7` |

`piga` / `pigs` の子 Pi は `cheap` / `balanced` が `xhigh`、`max` が `max`、
`pigl` の子 Pi は全 tier が `xhigh`。`pixg` の子 Pi は Luna の `cheap` と
Grok の `max` が `xhigh`、Grok の `balanced` が `high`。
tier を変更するときは、リポジトリの `.devcontainer/pi-superagents/<launcher>.json` を編集してから次を実行する。`install_beforehand.bash` は既存の設定を保持するため、rebuild だけでは反映されない。

```bash
zsh .devcontainer/setup_pi_superagents.zsh
```

`bwrap` が無い、またはランチャー用の設定が無い場合、ランチャーは起動せずに案内を出す。共有設定へ暗黙にフォールバックすると tier が警告なく混線するため。

#### Superpowers スキルの探索パス

pi-superagents v1.14.3 以降は、git で導入したパッケージの `package.json` にある
`pi.skills` を探索するため、Superpowers の探索パスを手動登録する必要はない。
[upstream の修正 #72](https://github.com/teelicht/pi-superagents/pull/72) は
[v1.14.3](https://github.com/teelicht/pi-superagents/releases/tag/v1.14.3) に含まれる。

##### 既存環境の更新

古い環境では、回避設定を整理する前に pi-superagents を v1.14.3 以降へ更新する。
`pi --version` は Pi 本体の版なので、拡張の版は別に確認する。
`pi list` で `npm:@teelicht/pi-superagents` の登録先・配置先を確認する。

```bash
pi --version
pi list
PI_SUPERAGENTS_ROOT="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/npm/node_modules/@teelicht/pi-superagents"
node -e 'const p = JSON.parse(require("node:fs").readFileSync(process.argv[1], "utf8")); console.log(p.name, p.version)' "$PI_SUPERAGENTS_ROOT/package.json"
```

このパスは標準のユーザー配置を想定している。project/local 配置を利用している場合は、
`pi list` が示した対象の配置先を `PI_SUPERAGENTS_ROOT` に指定する。
期待する出力は `@teelicht/pi-superagents 1.14.3` またはそれ以降の版。
未更新のユーザー配置は、[Pi の package 管理](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md)に従い、対象を指定して更新する。

```bash
pi update npm:@teelicht/pi-superagents
```

版指定で古い npm パッケージを固定している場合は、通常の更新では pin が進まない。
その場合は `pi install npm:@teelicht/pi-superagents@1.14.3` で確認済み基準版へ
指定を変更できる。既に v1.14.3 以降なら下げる必要はない。更新後に同じ版確認を行う。

次に、旧エントリを追加していたセットアップを撤去した、現在のリポジトリのセットアップへ更新してから、
下の任意整理に進む。
新しい `.devcontainer/setup_pi_superagents.zsh` は `~/.pi/agent/settings.json` を
作成・変更しない。旧セットアップを残したままエントリだけ削除すると、再実行で追加される。

##### 旧エントリの任意整理

既存の `git/github.com/obra/superpowers/skills` は残してもよい。
v1.14.3 の隔離検証では、自動探索と同じ絶対パスに解決され、探索リストで重複排除された。
整理したい場合だけ `~/.pi/agent/settings.json` の `skills` 配列からこの要素を削除する。
他の skills、`packages`、`theme` などは保持し、設定全体を置き換えない。
自動削除の移行処理は行わない。

##### 検証範囲

移行元リポジトリで行った隔離検証では、
pi-superagents 1.14.3 / Pi loader 0.85.1 / Superpowers 6.4.1 について、
旧エントリあり・なしと `includeProject` true・false の4条件で、
`using-superpowers`、`brainstorming`、`writing-plans`、
`subagent-driven-development`、`executing-plans` の解決と探索パスの重複排除を確認した。
これは探索 API の検証であり、実 trust 設定の変更や対話 Pi の `/sp-*` 実行確認ではない。

セットアップの設定非変更・ランチャー配置などの回帰テストは、リポジトリのルートで実行する。

```bash
bash .devcontainer/test-pi-superagents.bash
bash .devcontainer/test-pi-openai-codex.bash
```

## DeepSeek Harness（dsh）

`install_beforehand.bash` は [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)
（`dsh`）を `@deepseek-ai/dsh@0.1.5-rc.1` に固定して導入し、直後の `dsh --version` が
指定版を返さなければ postCreate を失敗させる。既存の `pigo` / `pigod` /
`pigou` / `piccg` / `piccd` と `~/.pi` の設定には影響しない。

`dsh` の plugin 管理は PATH 上の `pnpm` を直接 spawn する。`pnpmVersion: "none"` は
pnpm を導入しない指定のため、Node feature で plugin 0.10.6 との組み合わせを
隔離検証した `12.4.1` を明示導入している。

`~/.dsh` は `devcontainer.json` で bind mount している。設定、plugin、credentials は
ホスト側に残るため、リビルド後も `dsh web` の設定と Command Code plugin を
そのまま使える。Web UI は `forwardPorts` の `3080`（dsh web の既定ポート）で
ホストから開ける。

### 初期設定

設定ファイルは 2 つある。それぞれ存在しないときだけ `.devcontainer/` の雛形を
コピーする。既に設定がある環境では上書きしないため、リポジトリ側の雛形を更新しても
リビルドでは反映されない。反映する場合はバックアップしてから手動でコピーする。

- `~/.dsh/settings.yaml` ← `.devcontainer/dsh-settings.yaml`。provider の設定
- `~/.dsh/cordis.patch.yml` ← `.devcontainer/dsh-cordis.patch.yml`。plugin の
  有効・無効。home レベルの patch 層は全 profile に効く

```bash
cp ~/.dsh/settings.yaml ~/.dsh/settings.yaml.bak
cp .devcontainer/dsh-settings.yaml ~/.dsh/settings.yaml
cp ~/.dsh/cordis.patch.yml ~/.dsh/cordis.patch.yml.bak
cp .devcontainer/dsh-cordis.patch.yml ~/.dsh/cordis.patch.yml
```

設定は 2 つの provider を有効にする。

- `deepseek-official/deepseek-v4.1-flash`。`llm-deepseek` を OpenCode Go の
  OpenAI-compatible endpoint `https://opencode.ai/zen/go/v1` へ向けて使う
- `commandcode/deepseek/deepseek-v4.1-flash`。Command Code plugin
  `@mars-sea/dsh-commandcode-provider@0.10.6` を web profile に導入して使う

reasoning effort `max` をリポジトリ設定で固定するのは OpenCode Go 経路だけである。
`agent-default-model` の既定の選択（`deepseek-official/deepseek-v4.1-flash`）と
`llm-deepseek` に `reasoningEffort: max` を書いている。Command Code plugin には
effort の設定項目が無く、リクエストに渡された値だけを使うため、Command Code の
モデルを選んだセッションの effort は UI 側の選択で決まる。

Command Code plugin の Web Search は `webSearch: false` で無効化する。

DeepSeek 独自の `dsh_plugin_packages` は `plugin-package-inventory-deepseek` を
無効化して送らないようにしている。この plugin は settings の section を登録せず、
`settings.yaml` に書いても無視されるため、無効化は `~/.dsh/cordis.patch.yml` の
patch 層で行う。`install_beforehand.bash` は `dsh --profile web --dump-config` で
実際に `enabled: false` になっていることを確認し、なっていなければ postCreate を
失敗させる。

### API トークン

API key はリポジトリにも `~/.dsh/settings.yaml` にも保存しない。設定は
環境変数名（`OPENCODE_API_KEY` / `COMMANDCODE_API_KEY`）だけを参照する。
`dsh web` を使うシェルで export しておく（`pigo` / `piccd` と同じ値を使う）。
「秘密情報」の節の `~/.config/create-reso-world/env` に書けば、シェルの起動時に export される。

Dev Container を使わないローカル環境では、`pnpm` を用意したうえで次の順に
手動で導入する。既に `~/.dsh/` 側にファイルがある場合はコピーしない。

```bash
npm install -g @deepseek-ai/dsh@0.1.5-rc.1
mkdir -p ~/.dsh
[ -f ~/.dsh/settings.yaml ] || cp .devcontainer/dsh-settings.yaml ~/.dsh/settings.yaml
[ -f ~/.dsh/cordis.patch.yml ] || cp .devcontainer/dsh-cordis.patch.yml ~/.dsh/cordis.patch.yml
dsh plugin --profile web add @mars-sea/dsh-commandcode-provider@0.10.6
```

### 検証

Dev Containers: Rebuild Container の後に次を実行する。

```bash
dsh --version                     # 0.1.5-rc.1 と表示される
dsh --profile web --dump-config   # llm-deepseek と llm-commandcode が見える
dsh --profile web --dump-config | grep -A4 'plugin-package-inventory-deepseek'
                                  # config の enabled: false が見える
dsh web --no-open                 # Web UI が port 3080 で待ち受ける
```

`dsh web --no-open` は終了しないため、確認後は Ctrl-C で止める。API key を
含むログを残さないこと。
