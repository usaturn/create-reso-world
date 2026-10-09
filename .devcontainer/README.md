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
| Claude Code | installer（`claude.ai/install.sh`）。プラグインは `.claude/settings.json` の `enabledPlugins` と同じ 5 つ | `~/.claude`、`~/.claude.json` | `~/.claude`、`~/.claude.json`（touch） | `ccd`、`ccdo`、`ccds`（alias）、`ccdd`、`ccddg`、`ccdu` | `claude update` |
| Codex | `npm install -g @openai/codex@latest` | `~/.codex` | `~/.codex` | `cod` | `npm install -g @openai/codex@latest` |
| pi | `npm install -g` で本体、`pi install` で拡張。ランチャー 9 本を `~/.local/bin` に置く | `~/.pi` | `~/.pi` | — | `pi update`、`pi update --extensions` |
| Cursor | installer（`cursor.com/install`） | `~/.cursor`、`~/.config/cursor`、`~/.local/share/cursor-agent` | `~/.cursor`、`~/.config/cursor`、`~/.local/share/cursor-agent` | `cur`（alias） | `agent update` |
| Devin | installer（`cli.devin.ai/install.sh`） | `~/.local/share/devin`、`~/.config/devin` | `~/.local/share/devin`、`~/.config/devin` | `dev`（alias） | `devin update`、`devin plugins update superpowers` |
| Meshy CLI | `install_meshy.bash`（公式 npm `meshy-cli@0.4.0`、無認証 version / help） | — | — | — | — |
| gh | Dev Container Feature（github-cli） | `~/.config/gh` | `~/.config/gh` | — | — |
| gcloud / glab / bun | 未導入（参照だけ残す） | `~/.config/gcloud`、`~/.config/glab-cli` | `~/.config/gcloud`、`~/.config/glab-cli` | `genv`（gcloud）、`buni`（bun） | — |
| Resonite の写真フォルダ（任意） | WSL で Windows の Pictures/Resonite へのリンクを 1 回作る（「Resonite ワールド開発ツール」の節） | `~/.local/share/create-reso-world/resonite-screenshots`（読み取り専用） | `~/.local/share/create-reso-world/resonite-screenshots` | — | — |
| 秘密情報 | — | `~/.config/create-reso-world` | `~/.config/create-reso-world`（mode 700） | env ファイルがあれば読み込む | — |
<!-- tool-table:end -->

未導入のツールを呼ぶ関数（`cod`、`genv`、`buni`）は、コマンドが無ければ理由を表示して 127 を返す。
`update()` は無いツールの項目を飛ばし、飛ばした項目を表示する。

dsh と Grok Build（`grok`）は、リポジトリでは導入も mount もしない。Claude Code を Alibaba Cloud 経由で使う `ccda`（`claude-alibaba`）も置かない。ホストの `~/.dsh`・`~/.grok` は
Dev Container から見えなくなるだけで、削除しない。不要になったら利用者がホスト側で消す。
リビルドする前のコンテナには、導入済みの `dsh` が残る。

## 秘密情報

Meshy の `MESHY_API_KEY` は例外で、env / credentials ファイルへ保存せず、利用者が zsh で非表示入力して環境変数だけで渡す。手順は [Meshy → ResoLoop](../docs/meshy-resoloop.md)。

それ以外の API トークンなどの秘密情報は、ホストの `~/.config/create-reso-world/env` に置き、リポジトリには置かない。
このディレクトリは Dev Container に bind mount され（`initialize.bash` がホスト側に mode 700 で作る）、
`zshrc.txt` がシェルの起動時に `env` を読み込んで、書いた変数をすべて export する。ファイルが無ければ何もしない。

```bash
# ホスト側で一度だけ作る
mkdir -p ~/.config/create-reso-world && chmod 700 ~/.config/create-reso-world
touch ~/.config/create-reso-world/env && chmod 600 ~/.config/create-reso-world/env
```

書式は `KEY=VALUE` の 1 行 1 変数である（zsh が読むので、空白や記号を含む値は引用符で囲む）。
対象は `DEEPINFRA_TOKEN`、`COMMANDCODE_API_KEY`、`OPENCODE_API_KEY`、`CONTEXT7_API_KEY`、
`GOOGLE_DEV_KNOWLEDGE_API_KEY` などで、書き換えたら新しいシェルを開く。
変数ごとの用途と、無いときの挙動は「API トークン」の節にある。

撤去した `ccda` が使っていた `MAAS_ANTHROPIC_TOKEN` は、もう使わない。`env` に残っていれば削除する。
プロバイダ切替ランチャー（`ccdd` など）はこの変数を子プロセスから外さないため、残すと子プロセスにも渡る。

## 既存環境の更新

2026-10 に pi と Claude Code の設定を取り込み、pi のランチャー・拡張・MCP、Claude Code のランチャー、
除外したツール（dsh・Grok Build・`ccda`）の扱いが変わった。既存の環境には次の順に反映する。

1. ホストの作業ツリーを最新の `origin/main` に追従させる。rebuild は作業ツリーの `.devcontainer/` を使う。
2. ホストの `~/.config/create-reso-world/env` を見直す。`MAAS_ANTHROPIC_TOKEN` を削除し、
   Google Developer Knowledge の MCP を使う場合は `GOOGLE_DEV_KNOWLEDGE_API_KEY` を足す（「API トークン」）。
3. Dev Containers: Rebuild Container を実行する。postCreate が次を行う。
   - pi の旧拡張の撤去と、settings の `-builtin:mcp` の除去。変更が必要なときだけバックアップを作る
     （「pi の旧拡張・MCP 設定の移行」）
   - 9 本の pi ランチャーと共通ヘルパの配置。ヘルパは pi を `--tui-mode regular` で起動する
     （「pi の TUI モードと Herdr のスクロール履歴」）
   - Claude Code の alias（`ccd`・`ccdo`・`ccds`）とプロバイダ関数を含むシェル設定の配置
     （「Claude Code の起動と更新」）
   - dsh と Grok Build を導入せず、mount もしない。`PI_DISTILL_*` と `PI_EXTENSIONS_LOCALE` を export しない
4. rebuild では変わらないものを反映する。
   - ランチャー別の tier: `--if-absent` を付けずに `zsh .devcontainer/setup_pi_superagents.zsh` を実行する。
     変更のある設定はバックアップされる（「pi-superagents のランチャー別 model tier」）
   - pi の project trust: まだ承認していなければ、リポジトリのルートで素の `pi` を起動して承認する。
     承認の後に `.pi/settings.json`・`.pi/mcp.json`・`.pi/APPEND_SYSTEM.md`（pi 固有の指示）と
     プロジェクトのスキル（`.agents/skills`）が読まれる
     （「組み込み MCP と廃止した拡張」）
   - `~/.pi/agent/models.json` に残る `deepinfra-distill` は自動では消さない。不要なら定義を確かめてから削除する
5. 確かめる項目と、rebuild 前の状態の記録は、ルートの `README.md` の「対象外」が案内する移植の記録にある。

rebuild しない場合は、3 の代わりに次を行う。dsh は rebuild するまでコンテナに残る。

- pi の旧拡張の撤去: 「pi の旧拡張・MCP 設定の移行」の `uv run --no-project .devcontainer/cleanup_pi_mcp.py`
- 廃止した環境変数: 「組み込み MCP と廃止した拡張」の `unset` と、`~/.zshrc` の export 行の削除。
  2 で `env` から消した `MAAS_ANTHROPIC_TOKEN` も、使用中のシェルでは `unset MAAS_ANTHROPIC_TOKEN` で外す
- pi のランチャーと共通ヘルパ: 「エージェント向けツールの導入」の 9〜17 の `install -m 0755` で 9 本を置き直す。
  同じ節の 8 の `models.json` のコピーは既存の定義を上書きするので行わない。共通ヘルパは、4 で実行する
  `zsh .devcontainer/setup_pi_superagents.zsh` が更新する
- Claude Code のランチャー: 「Claude Code の起動と更新」の `~/.zshrc` への反映。古い `~/.zshrc` に残る
  `ccda`（`claude-alibaba`）の関数と、`update()` の Grok Build の行も削除する

## テストの実行

リポジトリのルートで次を実行する。CI（`.github/workflows/ci.yml`）も同じコマンドを実行する。

```bash
bash .devcontainer/run-tests.bash          # .devcontainer/test-*.bash と tests/scripts/*.bash（CI の devcontainer-tests）
bash scripts/check-layout.sh               # リポジトリのレイアウト（CI の layout。resoloop が無ければ skills sync の検査を skip）
uv run pytest tests/skills .agents/skills  # スキルのテスト（CI の skill-tests）
(cd worlds/<name> && uv run pytest)        # 各ローカルプロジェクトのテスト（追跡対象外なので CI では実行しない）
```

テストは一時ディレクトリの `HOME` と、モックの resoloop・dotnet・Blender を使うので、実環境を変えない。
1 本だけ実行するときは `bash .devcontainer/run-tests.bash <テストのパス>` のように渡す。
CI の gitleaks ジョブは `.gitleaks.toml`（既定の規則に、resoloop のマニフェストが持つ識別子の除外を足したもの）で
秘密情報の混入を検査する。CI では Blender によるワールドのビルドは行わない。

## Resonite ワールド開発ツール

Dev Container の作成時に .NET 10 SDK、Blender、glTF import / export 用の `python3-numpy` を導入し、ResoLoop は NuGet の最新の公開版を
`.devcontainer/install_resoloop.bash`（`dotnet tool update --global ResoLoop --prerelease --allow-downgrade`）で導入する。
続けて、各プロジェクトの `resoloop skills sync --check` の結果を `.devcontainer/report-resoloop-skills.bash` で表示する
（差分があっても postCreate は失敗しない）。rebuild せずに最新へ上げるときも `bash .devcontainer/install_resoloop.bash` を実行する。
fork のビルドを一時的に使う方法は `docs/resoloop-fork-workflow.md` を参照する。
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

### Resonite の写真フォルダ（任意）

Resonite は写真を Windows の Pictures の `Resonite` フォルダに保存する。そのままではコンテナの `resoloop capture` が写真を読めず、
`CAPTURE_EXPORT_DIR_UNREACHABLE` で止まる。WSL 側にリンクを 1 回作ると、コンテナの
`~/.local/share/create-reso-world/resonite-screenshots` に読み取り専用でマウントされる。あわせて `initialize.bash` が
`.devcontainer/resonite-screenshots.env` に `RESOLOOP_SCREENSHOTS_DIR` を書き、`runArgs` の `--env-file` でコンテナに渡す。

1. Windows の PowerShell で Pictures の場所を調べる。OneDrive にリダイレクトされていれば、その場所が表示される

   ```powershell
   [Environment]::GetFolderPath('MyPictures')
   ```

2. その下に `Resonite` フォルダが無ければ、Resonite で写真を 1 枚撮る
3. WSL のターミナル（コンテナの外）で、`initialize.bash` が作った空のディレクトリをリンクに置き換える。
   `C:\Users\<名前>\Pictures` は `/mnt/c/Users/<名前>/Pictures` になる

   ```bash
   rmdir ~/.local/share/create-reso-world/resonite-screenshots
   ln -s /mnt/c/Users/<名前>/Pictures/Resonite ~/.local/share/create-reso-world/resonite-screenshots
   ```

4. Dev Container を rebuild する

リンク先が無くなると、`initialize.bash` がリンク先を表示して止まる。`/mnt/c` が見えるか（WSL の automount）とフォルダがあるかを
確かめるか、リンクを消して空のディレクトリに戻す。リンクを作った・消した後は、どちらも rebuild が要る。

## Meshy CLI と生成物の受け渡し

postCreate は `bash .devcontainer/install_meshy.bash` で公式 `meshy-cli@0.4.0` を導入し、キーを外した version / help のみを確認する。
認証・残高・生成・download・Resonite への apply は自動実行しない。キーがなくてもセットアップを進められる。
Meshy の更新は検証済み版と wrapper の互換確認を伴う変更として扱う。ResoLoop は従来どおり NuGet の最新公開版を使い、実測 version を記録する。

[docs/meshy-resoloop.md](../docs/meshy-resoloop.md) に、zsh の非表示入力、課金承認、text preview / refine の別 operation、local image、復旧、convert の素材制限、Windows PowerShell での bundle / state handoff をまとめている。
キーはチャット・引数・ファイルへ残さない。export 後に同じシェルから起動した子だけに継承され、起動済み Herdr / VS Code / エージェントには後から届かない。
project の `content/generated/meshy/<operation>/` と `.resoloop/meshy-cli/operations/` を rebuild 後も残し、キーだけ再入力する。応答不明の submit は再送しない。

toolchain probe は headless Blender の `import bpy, numpy` を確認する。実 fixture / exporter は一時 wrapper で確認済みだが、現在の sudo は no-new-privileges により拒否される。
**標準 rebuild、実 API / 課金生成、Windows の texture 付き表示・無変更再適用は未検証**。一時 wrapper の成功を標準 rebuild の成功と扱わない。
受入 checklist を完了するまでは PR を `Refs #50` とし、Issue を自動 close しない。

新規・既存プロジェクトともルートの `.agents/skills/meshy-resoloop/SKILL.md` を共有する。
祖先スキルが見えないエージェントにはこの repository-relative パスを明示する。本文のコピー、project 側への追加リンク、エージェント設定の変更は不要。

## エージェントの読み込みの制約

プロジェクト（`worlds/<name>/` など）を cwd にしてエージェントを起動したとき、次のエージェントはスキルの一部が見えない。

- Cursor は workspace 配下の `.agents/skills` しか読まないため、ルートの共有スキルが見えない。
  プロジェクトの resonite-* スキルは見える

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

### Claude Code の起動と更新

`ccd` はモデルを指定せず、Claude Code 側の設定に従って起動する。
`ccdo` は `--model opus`、`ccds` は `--model sonnet` を付ける。
3 つとも `--dangerously-skip-permissions` を付けて起動し、追加の引数はそのまま渡す。

第三者プロバイダのランチャーは次の対応で起動する。比較基準と採否は
[Claude Code 移植の Spec](../docs/superpowers/specs/2026-10-04-issue-21-claude-code-design.md)
に記録している。実プロバイダへの接続検証は別途行う。

| 通常名 / 短い起動名 | 接続先 | 既定モデル（opus） | fable の割り当て | 認証に使う変数 |
| --- | --- | --- | --- | --- |
| `claude-deepinfra` / `ccdd` | DeepInfra | `deepseek-ai/DeepSeek-V4.1-Flash` | `zai-org/GLM-5.3` | `DEEPINFRA_TOKEN` |
| `claude-deepinfra-glm` / `ccddg` | DeepInfra | `zai-org/GLM-5.3-Flash` | `deepseek-ai/DeepSeek-V4.1-Flash` | `DEEPINFRA_TOKEN` |
| `claude-opencode-union` / `ccdu` | OpenCode Go | `union-alpha`（`--model union-alpha` で起動） | `union-alpha` | 下記の OpenCode キー |

DeepInfra の sonnet は `deepseek-ai/DeepSeek-V4-Flash-0731`、haiku は
`openai/gpt-oss-20b`。OpenCode のモデル割り当てとサブエージェントは `union-alpha` を使う。
OpenCode のキーは `OPENCODE_GO_CLAUDE_API_KEY`、`OPENCODE_API_KEY`、
`OPENCODE_GO_API_KEY` の順に、最初の空でない値を使う。キーがなければ起動を止める。

短い起動名だけが `--dangerously-skip-permissions` を付ける。
通常名は権限確認を省略せず起動する。追加の `--model` などは既定引数の後へ渡す。
共通の `cc_launcher_unsets` で親シェルの認証・プロバイダ切替・モデル固定の値を
子 CLI から取り除き、選んだ接続先の値だけを設定する。親シェルの値は変更しない。

既存コンテナでは、rebuild によって `.devcontainer/zshrc.txt` の更新を反映できる。
rebuild 前に反映する場合は、同ファイルの Claude alias・`cc_launcher_unsets`・
3 つのプロバイダ関数を既存の `~/.zshrc` の対応箇所に反映し、新しい zsh を開く。
Claude CLI 自体の更新は `claude update` を使う。`feature-dev` と `ccdu` は引き続き利用できる。

onboarding の書き換えスクリプトは導入・自動実行しない。`~/.claude.json` はファイルの
bind mount なので、移植元の一時ファイルから rename する方式はそのまま使えない。
初回設定は通常の Claude Code の手順で行い、個人の `.claude/settings.local.json` は移植しない。

## pi の旧拡張・MCP 設定の移行

ドキュメント取得は共有の `find-docs` スキル経由の CLI を標準とする。
`pi-mcp-adapter`、`@upstash/context7-pi`、`pi-distill`、単独登録の
`pi-extensions-tool-display` と `pi-extensions-i18n` は導入しない。
postCreate は拡張の導入前に既存の登録・pi 管理 npm マニフェストと、pi agent directory 内の
`mcp-cache.json`、`mcp-project-approvals.json`、`mcp-onboarding.json`、
`mcp-npx-cache.json` を整理する。
組み込み MCP も使う `mcp.json` と `mcp-auth.json` は、内容とリンクをそのまま保持する。
settings の `extensions` から `-builtin:mcp` だけを除き、他の拡張・独自モデル・認証は保持する。
旧拡張の残留がなくても、利用者が設定した `-builtin:mcp` は、成功する cleanup の実行ごと
（postCreate を含む）に除去する。ホストから共有する agent directory の設定変更なので、
同じ directory を使うホスト側や他の環境の pi にも反映される。
共有の MCP 設定・API キー・`find-docs`・`~/.npm` のキャッシュは変更しない。

変更前には `agent/migration-backups/pi-retired-*` に settings と存在する npm マニフェストの
元バイト列を保存し、保存先を表示する。各バックアップは固有名のディレクトリ（0700）に置く。
バックアップに失敗した場合は撤去しない。途中で pi remove が失敗した場合は、理由を出して
停止しバックアップを残す。復旧する場合は pi を終了し、表示されたディレクトリ内のファイルを
元の agent directory の同じ相対パスへ戻してから npm の状態を確認し、必要な拡張を再導入する。
バックアップは npm インストール実体を含まないため、node_modules の復旧には再導入が必要。
整理済みの再実行や空の初回環境ではバックアップ・settings を新設しない。

既存環境では pi と uv を導入済みの状態で、リポジトリのルートから次を実行する。

```bash
uv run --no-project .devcontainer/cleanup_pi_mcp.py
```

対象は `PI_CODING_AGENT_DIR`（未指定なら `~/.pi/agent`）。指定する場合は安全な絶対パスか
`~/...` を使う。削除対象4ファイルの symlink はリンクだけを削除し、設定・パッケージ保存先が
symlink や hard link の場合、読み取り・削除エラー時は停止する。
`npm/` 自体がない場合は npm を実行せず、対象拡張の登録だけを撤去する。
対象拡張の撤去が必要で `npm/` が存在するのに `npm/package.json` がない場合、または保持する npm 拡張の
登録がそのマニフェストに宣言されていない場合は、npm による巻き添え削除を防ぐため変更せず停止する。
対象のマニフェストを復旧してから再実行する。
settings と対象の全 npm マニフェストは、NaN・Infinity や JavaScript Number の有限範囲を
超える数値（巨大整数を含む）があれば、バックアップ・撤去・キャッシュ削除の前に停止する。
エラーに示されたファイルの数値を確認して修正し、再実行する。有効な Unicode エスケープは保持する。
`npm/npm-shrinkwrap.json` と `npm/package-lock.json` が両方あり、npm が無視する後者に
撤去対象が残る場合も変更せず停止する。表示された両 lockfile を利用者側で整合させてから再実行する。
cleanup は lockfile を自動削除しない。
実行中の pi は古い拡張や接続を保持し、状態ファイルを再作成する場合があるため、先に終了する。
整理後に起動し直す（セッションを継続する場合も `/reload` だけで不十分なら再起動する）。

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
| `pigs` | `openai-codex/gpt-6.1-sol` |
| `pigl` | `openai-codex/gpt-6-luna` |

3 つとも親 Pi は ChatGPT Pro サブスクリプションの Codex OAuth 認証を使う。
`OPENAI_API_KEY` は不要で、OpenAI API のキー課金用 provider には接続しない。
初回だけ素の `pi` を起動して `/login openai-codex` を実行し、ログインする。
OAuth 情報は `~/.pi/agent/auth.json` に保存される。`~/.pi` は Dev Container に bind mount
されているため、リビルド後もログイン状態を保持する。認証は対話操作が必要で、
`postCreateCommand` から自動ログインしない。未認証のままランチャーを起動した
場合は、このログイン手順を表示して終了する。
`pigs` の `cheap` tier の子 Pi は OpenCode Go の `deepseek-v4.1-flash` を
使う。子 Pi が使う OpenCode Go の資格情報は `setup_pi_opencode_go.zsh` が
`auth.json` に書いた api_key または `OPENCODE_API_KEY` で解決され、`pigo`・`pigod` と
同じく起動前の確認は行わない。旧名の `OPENCODE_GO_API_KEY` だけが設定されている場合は、
ランチャーが `OPENCODE_API_KEY` に引き継いでから起動する。`auth.json` に資格情報が無い環境では
`cheap` tier の子 Pi が provider 認証エラーになるため、必要なら `OPENCODE_API_KEY` を
設定して `zsh .devcontainer/setup_pi_opencode_go.zsh` を実行する。

GPT-6.1 Sol のため Pi 0.99.1 以上が必要（GPT-6 Astra / Luna もこの版に含まれる）。利用前に `pi --version` を確認し、
ログイン後に各モデルが `openai-codex` 行にあることを確認する。

```bash
pi --version
pi --list-models gpt-6-astra
pi --list-models gpt-6.1-sol
pi --list-models gpt-6-luna
```

モデル行が無い場合は Pi を更新する。`pi --list-models` は利用可能なモデルを
表示するため、未認証時には Pi がモデル定義を持っていても `openai-codex` 行は
表示されない。3 ランチャーは `--thinking xhigh` で起動する。子 Pi の
`cheap` / `balanced` / `max` tier はランチャーごとに GPT-6 Luna / GPT-6.1 Sol /
GPT-6 Astra を割り当てる（`pigs` の `cheap` だけは OpenCode Go の
`deepseek-v4.1-flash`。後述の tier の表を参照）。ログイン済みの環境では、次のテストでも Pi の版と
3 モデルを検証できる。

```bash
PI_CODEX_LIVE_CHECK=1 bash .devcontainer/test-pi-openai-codex.bash
```

### SuperGrok / X Premium の Grok 4.7 ランチャー

| launcher | Provider / Model |
|---|---|
| `pixg` | `xai/grok-4.7` |

`pixg` の親 Pi と `max` tier は SuperGrok または X Premium
サブスクリプションの xAI OAuth 認証を使い、`cheap` / `balanced` tier の
子 Pi は OpenCode Go の `deepseek-v4.1-flash` を使う。`XAI_API_KEY` は
不要で、xAI API のキー課金には接続しない。OpenAI Codex の認証も使わない。
初回だけ素の `pi` を起動して `/login xai` を実行し、
`Sign in with SuperGrok or X Premium` からログインする。OAuth 情報は
`~/.pi/agent/auth.json` に保存される。`~/.pi` は Dev Container に bind mount
されているため、リビルド後もログイン状態を保持する。認証は対話操作が必要で、
`postCreateCommand` から自動ログインしない。xAI が未認証なら、
`pixg` はログイン手順を表示して起動前に終了する。
子 Pi が使う OpenCode Go の資格情報は `setup_pi_opencode_go.zsh` が
`auth.json` に書いた api_key または `OPENCODE_API_KEY` で解決され、`pigo`・`pigod` と
同じく起動前の確認は行わない。旧名の `OPENCODE_GO_API_KEY` の扱いは `pigs` と同じである。

Grok 4.7 と DeepSeek V4.1 Flash は Pi の組み込みカタログにあるため、
`pi-models.json` への定義追加は不要である。ログイン後にそれぞれのモデルを
確認する。

```bash
pi --list-models xai
pi --list-models deepseek-v4.1-flash
```

モデル行が無い場合は Pi を更新する。`pi --list-models` は利用可能なモデルを
表示するため、未認証時には Pi がモデル定義を持っていても該当する
プロバイダの行は表示されない。`pixg` は `--thinking xhigh` で起動する。
Grok 4.7 の thinking level は `low` / `medium` / `high` / `xhigh` で、
`xhigh` が実際の最大値である。子 Pi は `cheap` / `balanced` が
`opencode-go/deepseek-v4.1-flash` の `max`、`max` が `xai/grok-4.7` の
`xhigh` を使う。未認証時に別モデルへ自動フォールバックはしない。

### 組み込み MCP と廃止した拡張

`.pi/settings.json` の `+builtin:mcp` で pi の組み込み MCP を有効にする。
`.pi/mcp.json` は Google Developer Knowledge の HTTP サーバだけを設定しており、
Context7 は含めない。利用者は `GOOGLE_DEV_KNOWLEDGE_API_KEY` を設定し、pi の
project trust を許可してから使う。キーが無い場合、pi は接続せずに、キーを解決できないというこのサーバのエラーを
起動後に1回通知するが、他の機能は使える。プロジェクトの定義は同名の利用者設定より優先されるため、利用者設定では無効化できない。
`/mcp` で無効化すると追跡対象の `.pi/mcp.json` が書き換わるため、その変更はコミットしない。
各ワールドの `.pi -> ../.pi` から同じ設定を読む。
グローバルの MCP 設定・認証も保持する。

pi-distill の出力圧縮と tool-display の調整は廃止した。既存の利用者が保存した
extension config は変更しない。環境変数の既定値の削除は Dev Container の rebuild 後に反映される。
rebuild 前の既存コンテナでは、`~/.zshrc` に残る `PI_DISTILL_*` と `PI_EXTENSIONS_LOCALE` の
export 行を削除する。利用中のシェルでは次を実行してから pi を再起動する。

```bash
unset PI_DISTILL_TIMEOUT_SECONDS PI_DISTILL_MODEL PI_DISTILL_ERROR_RETRY_COUNT PI_EXTENSIONS_LOCALE
```

新規モデル雛形と `setup_pi.zsh` は deepinfra-distill を登録しない。
既存 `models.json` に同名 provider があっても、独自モデルを保護するため削除しない。
リポジトリからは参照しないため、不要な場合は利用者がモデル定義を確認してから除去できる。

### setup スクリプトを使う場面

`.devcontainer/setup_pi.zsh`（deepinfra）、`.devcontainer/setup_pi_opencode_go.zsh`
（opencode-go）、`.devcontainer/setup_pi_commandcode_goat.zsh`（commandcode）は、
リビルドのたびに実行するものではない。次の場面で使う。

- API キーをローテーションしたとき（`setup_pi_opencode_go.zsh` が
  `auth.json` を書き換える。commandcode は環境変数参照なので
  キーのローテーションで setup スクリプトの実行は不要）
- ホスト側の `~/.pi` を作り直したとき
- `pi-models.json` を編集し、既存の `~/.pi/agent/models.json` へ反映したいとき
  （`install_beforehand.bash` は既存ファイルを上書きしないため）

いずれも冪等で、`providers` のうち対象プロバイダのエントリだけを置き換える。
3 つの setup は `PI_CODING_AGENT_DIR` の `~` と `~/` だけを HOME に展開する。
入力 JSON（`pi-models.json` と、setup が書くファイル）は、バックアップや変更の前に上記と同じ数値検査を行い、
モデル定義に `providers` があれば object であることも確かめる。
保存内容は最後まで Unicode エスケープ付きで生成してから
同じディレクトリの固有一時ファイルで元ファイルを置き換える。保存失敗時は元ファイルを残し、一時ファイルを掃除する。
置き換えると symlink や hard link の共有先が更新されなくなるため、setup が書く `models.json` と
`auth.json`（`setup_pi_opencode_go.zsh` のみ）が symlink、hard link、通常ファイル以外のいずれかなら、
書き込みが不要な実行でも、バックアップや変更の前に停止する。リンクを通常ファイルに置き換えてから再実行する。
検査するのはこの 2 ファイル自身で、agent directory がリンクでもファイルの置き換えでリンクは外れないため停止しない。
models.json は既存 mode を保持し、新規作成は 0600。モデルのバックアップは時刻に固有 suffix を
加えて同一秒の世代も上書きしない。auth.json は 0600 とし、平文認証を複製しないためバックアップを作らない。
`setup_pi_opencode_go.zsh` は `.devcontainer/pigo`・`.devcontainer/pigod`・
`.devcontainer/pigou` を、`setup_pi_commandcode_goat.zsh` は
`.devcontainer/piccg` と `.devcontainer/piccd` をそのまま配置するため、
実行してもランチャの内容は `install_beforehand.bash` の配置結果と一致する。

commandcode の 2 つのランチャを `setup_pi_commandcode_goat.zsh` が同居して
受け持つのは、両者が同じ `providers.commandcode` エントリを共有するためで
ある。スクリプトを分けると 2 本が同じエントリを全置換し合い、片方だけを
実行した時点で他方のモデル定義が `models.json` から消える。

### API トークン

Meshy の `MESHY_API_KEY` はここには含めない。ファイルを作らない非表示入力の手順は「Meshy CLI と生成物の受け渡し」にある。

次の変数は、「秘密情報」の節の `~/.config/create-reso-world/env` に書けばシェルの起動時に
export される。書かない場合は、必要なときに手動で export する。

- `OPENCODE_API_KEY` は `pigo`・`pigod`・`pigou` と、`pigs`・`pixg` の OpenCode Go の tier の
  子 Pi の実行には不要である。bind mount した `auth.json` に資格情報が残るため、pi はそこから読む
  （`pi auth check --provider opencode-go` が `ready` を返す）。
  `setup_pi_opencode_go.zsh` でキーを更新するときと、`auth.json` に資格情報が無い環境で
  pi の OpenCode Go を使うときに必要になる
- `OPENCODE_GO_API_KEY` は旧名である。OpenCode Go を使う `pigo`・`pigod`・`pigou`・`pigs`・`pixg` は、
  `OPENCODE_API_KEY` が空のときだけこの値を `OPENCODE_API_KEY` に引き継いでから起動する
- `ccdu`（Claude Code で OpenCode Go を使う）は `auth.json` を読まない。
  `OPENCODE_GO_CLAUDE_API_KEY`、`OPENCODE_API_KEY`、`OPENCODE_GO_API_KEY` の順に
  最初の空でない値を使い、どれも無ければ起動を止める
- `DEEPINFRA_TOKEN` は `models.json` の `apiKey` が `$DEEPINFRA_TOKEN` を
  参照するため、pi で deepinfra を使うシェルで export しておく必要がある。
  Claude Code の `ccdd`・`ccddg`（通常名は `claude-deepinfra`・`claude-deepinfra-glm`）も
  この変数を使い、無ければ起動を止める
- `COMMANDCODE_API_KEY` は `DEEPINFRA_TOKEN` と同じ方式である。`models.json`
  の `apiKey` が `$COMMANDCODE_API_KEY` を参照するため、`piccg` と `piccd` を
  使うシェルで export しておく必要がある。未設定のまま実行すると
  ランチャがエラーメッセージを出して終了する。キーは
  `https://commandcode.ai/settings/keys` で作成する
- `GOOGLE_DEV_KNOWLEDGE_API_KEY` は Google Developer Knowledge の MCP サーバーが使う。
  pi は `.pi/mcp.json`、Claude Code は `.mcp.json` のヘッダーでこの変数を参照する。
  無い場合の pi の挙動は「組み込み MCP と廃止した拡張」にある
- `CONTEXT7_API_KEY` は `.codex/config.toml` の `env_vars` で Codex の Context7 の MCP サーバー
  （`context7_stdio`）に渡す。未設定のまま `cod` を起動すると、入力を求める。
  共有の `find-docs` スキルが使う Context7 の CLI と、Claude Code（`.mcp.json`）・Cursor（`.cursor/mcp.json`）の
  Context7 の MCP サーバー（`@upstash/context7-mcp`）も、受け取った環境にこの変数があれば使う。無くても動くが、レート制限が低くなる

### pi の TUI モードと Herdr のスクロール履歴

Pi 1.0.0 から、対話 TUI の既定モードは `fullscreen` になった。このモードは
代替画面を使って会話履歴を Pi 内で管理するため、Herdr の通常のスクロール履歴に
過去の出力が残らず、コピーモードでさかのぼれない。

このリポジトリが管理する `pigo`・`pigod`・`pigou`・`piccg`・`piccd`・`piga`・
`pigs`・`pigl`・`pixg` は、共通ヘルパ `pi-superagents-exec.zsh` から
`pi --tui-mode regular` を起動する。regular は通常画面と端末のスクロール履歴を
使うため、画面高を超えた出力も Herdr のコピーモードで読める。
利用者／プロジェクトの `settings.json` は書き換えず、起動引数で指定する。
provider・model・thinking・認証確認・ランチャー別設定の分離は従来どおりで、
`--resume`・`--session`・メッセージなどの追加引数もそのまま転送する。
この指定はランチャーの既定値なので、追加引数に `--tui-mode fullscreen` を指定した
場合はその指定が優先される。素の `pi` の既定モードには影響しない。

Dev Container の初期化／リビルドでは `install_beforehand.bash` が全ランチャーを
配置し、`setup_pi_superagents.zsh --if-absent` が共通ヘルパを更新する。
`--if-absent` は既存のランチャー別 tier 設定を保持するが、共通ヘルパは毎回
更新する。リビルドしない既存環境では、リポジトリのルートで次を実行してから
ランチャーを起動し直す。

```bash
zsh .devcontainer/setup_pi_superagents.zsh --if-absent
```

`pigs`・`pixg` の tier の変更（後述）を既存環境に反映するには、`--if-absent` を付けずに
`zsh .devcontainer/setup_pi_superagents.zsh` を実行する（変更のある設定はバックアップされる）。
`pigs`・`pixg` の認証の確認の変更はランチャー自体にあり、リビルドで `~/.local/bin` に
置き直される。リビルドしない場合は `install -m 0755 .devcontainer/pigs ~/.local/bin/pigs`
（`pixg` も同様）で置き直す。

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
| `piga` | `openai-codex/gpt-6-luna` | `openai-codex/gpt-6.1-sol` | `openai-codex/gpt-6-astra` |
| `pigs` | `opencode-go/deepseek-v4.1-flash` | `openai-codex/gpt-6.1-sol` | `openai-codex/gpt-6.1-sol` |
| `pigl` | `openai-codex/gpt-6-luna` | `openai-codex/gpt-6.1-sol` | `openai-codex/gpt-6.1-sol` |
| `pixg` | `opencode-go/deepseek-v4.1-flash` | `opencode-go/deepseek-v4.1-flash` | `xai/grok-4.7` |

`pigo`・`pigod`・`pigou`・`piccg`・`piccd` の子 Pi は全 tier が `max`。
`piga` の子 Pi は `cheap` / `balanced` が `xhigh`、`max` が `max`。
`pigs` の子 Pi は `cheap` が `max`、`balanced` が `xhigh`、`max` が `max`。
`pigl` の子 Pi は全 tier が `xhigh`。`pixg` の子 Pi は DeepSeek の
`cheap` / `balanced` が `max`、Grok の `max` が `xhigh`。
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

##### pi-superagents の版の更新

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
