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
| pi | `npm install -g` で本体、`pi install` で拡張。ランチャー 11 本を `~/.local/bin` に置く | `~/.pi` | `~/.pi` | — | `pi update`、`pi update --extensions` |
| Cursor | installer（`cursor.com/install`） | `~/.cursor`、`~/.config/cursor`、`~/.local/share/cursor-agent` | `~/.cursor`、`~/.config/cursor`、`~/.local/share/cursor-agent` | `cur`、`curo`（alias） | `agent update` |
| Devin | installer（`cli.devin.ai/install.sh`） | `~/.local/share/devin`、`~/.config/devin` | `~/.local/share/devin`、`~/.config/devin` | `dev`、`devs`、`devo`（alias） | `devin update`、`devin plugins update superpowers` |
| Meshy CLI | `install_meshy.bash`（公式 npm `meshy-cli@0.4.0`、無認証 version / help） | — | — | — | — |
| Context7 CLI（ctx7） | `install_ctx7.bash`（npm の `ctx7` を `CTX7_CLI_VERSION` に固定して入れ、`ctx7 --version` を確かめる。「Context7 CLI（ctx7）」の節） | — | — | — | — |
| Gitleaks | `install_gitleaks.bash`（release の tar.gz を固定した SHA-256 で確かめて `~/.local/bin` に置く。版は CI の gitleaks ジョブと同じ） | — | — | — | — |
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
   - pi の旧拡張の撤去と、settings の `-builtin:mcp` の除去。Plannotator は導入・保持する。context7-pi は導入しないが、
     共有の `~/.pi` の登録は消さない（「pi の旧拡張・MCP 設定の移行」）
   - Context7 CLI（`ctx7`）を固定した版で導入する（「Context7 CLI（ctx7）」）
   - 11 本の pi ランチャーと共通ヘルパの配置。ヘルパは pi を `--tui-mode regular` で起動する
     （「pi の TUI モードと Herdr のスクロール履歴」）
   - Claude Code の alias（`ccd`・`ccdo`・`ccds`）とプロバイダ関数を含むシェル設定の配置
     （「Claude Code の起動と更新」）
   - dsh と Grok Build を導入せず、mount もしない。`PI_DISTILL_*` と `PI_EXTENSIONS_LOCALE` を export しない
4. rebuild では変わらないものを反映する。
   - ランチャー別の tier: `--if-absent` を付けずに `zsh scripts/setup_pi_superagents.zsh` を実行する。
     変更のある設定はバックアップされる（「pi-superagents のランチャー別 model tier」）
   - pi の project trust: まだ承認していなければ、リポジトリのルートで素の `pi` を起動して承認する。
     承認の後に `.pi/settings.json`・`.pi/mcp.json`・`.pi/APPEND_SYSTEM.md`（pi 固有の指示）と
     プロジェクトのスキル（`.agents/skills`）が読まれる
     （「組み込み MCP と廃止した拡張」）
   - `~/.pi/agent/models.json` に残る `deepinfra-distill` は自動では消さない。不要なら定義を確かめてから削除する
5. 確かめる項目と、rebuild 前の状態の記録は、ルートの `README.md` の「対象外」が案内する移植の記録にある。

rebuild しない場合は、3 の代わりに次を行う。dsh は rebuild するまでコンテナに残る。

- pi の旧拡張の撤去と共有拡張の導入: 「pi の旧拡張・MCP 設定の移行」の手動コマンド
- 廃止した環境変数: 「組み込み MCP と廃止した拡張」の `unset` と、`~/.zshrc` の export 行の削除。
  2 で `env` から消した `MAAS_ANTHROPIC_TOKEN` も、使用中のシェルでは `unset MAAS_ANTHROPIC_TOKEN` で外す
- pi のランチャーと共通ヘルパ: 「エージェント向けツールの導入」の 9〜19 の `install -m 0755` で 11 本を置き直す。
  同じ節の 8 の `models.json` のコピーは既存の定義を上書きするので行わない。共通ヘルパは、4 で実行する
  `zsh scripts/setup_pi_superagents.zsh` が更新する
- Claude Code のランチャー: 「Claude Code の起動と更新」の `~/.zshrc` への反映。古い `~/.zshrc` に残る
  `ccda`（`claude-alibaba`）の関数と、`update()` の Grok Build の行も削除する

## テストの実行

リポジトリのルートで次を実行する。CI（`.github/workflows/ci.yml`）も同じコマンドを実行する。

```bash
bash .devcontainer/run-tests.bash                          # .devcontainer/test-*.bash と tests/scripts/*.bash（CI の devcontainer-tests）
bash scripts/check-layout.sh                               # リポジトリのレイアウト（CI の layout。resoloop が無ければ skills sync の検査を skip）
uv run pytest tests/skills .agents/skills .agents/scripts  # スキルと .agents/scripts のテスト（CI の skill-tests）
(cd worlds/<name> && uv run pytest)                        # 各ローカルプロジェクトのテスト（追跡対象外なので CI では実行しない）
```

テストは一時ディレクトリの `HOME` と、モックの resoloop・dotnet・Blender を使うので、実環境を変えない。
1 本だけ実行するときは `bash .devcontainer/run-tests.bash <テストのパス>` のように渡す。
CI の gitleaks ジョブは `.gitleaks.toml`（既定の規則に、resoloop のマニフェストが持つ識別子の除外を足したもの）で
秘密情報の混入を検査する。private の CI は止めているので、push の前に手元で `scripts/scan-before-push.sh` を実行する
（ルートの `AGENTS.md` の「push の前の秘密情報の検査」）。この Gitleaks は postCreate が `install_gitleaks.bash` で入れる。
rebuild せずに入れるときも `bash .devcontainer/install_gitleaks.bash` を実行する。`tests/scripts/test-scan-before-push.bash` も
この gitleaks を使い、無ければ失敗する。CI では Blender によるワールドのビルドは行わない。

## uv の Python 実行環境

uv が使う Python を、システムの `/usr/bin/python3`（3.14）にそろえる。Blender もこの Python で動く。
uv は既定では、uv 管理の Python をシステムの Python より優先する。古い版を一度入れると、上位に `.venv` が無い場所
（`/tmp` の worktree など）の `uv run --no-project python` や、新しく作る `.venv` がその版を選ぶ。必要な版が無いときは、
断りなくダウンロードする。これを防ぐため、`devcontainer.json` の `containerEnv` に次を設定している（#122）。

```json
"UV_PYTHON_PREFERENCE": "system",
"UV_PYTHON_DOWNLOADS": "manual"
```

- `system`: uv 管理の Python があっても、システムの Python を先に選ぶ
- `manual`: 必要な版が見つからないとき、`uv run` などはダウンロードせずに失敗する。`uv python install` を明示したときだけ入る

`containerEnv` なので、cwd に関係なく、Herdr のペインや各エージェントを含むコンテナ内のプロセスに同じ設定が渡る。
`~/.config/uv/uv.toml`・`install_beforehand.bash`・`zshrc.txt`・プロジェクトの `pyproject.toml` には重複して置かない。
Dev Container の外の Python の選択は変えない。

版番号を強制する仕組みではない。`--python`・`UV_PYTHON` による版の明示、有効な仮想環境（`VIRTUAL_ENV`）、既存の `.venv` には効かず、
導入済みの古い版は `--python` で引き続き使える。ルートと雛形の `requires-python`（`>=3.12`）は変えていない。
uv の仕様は [Python versions](https://docs.astral.sh/uv/concepts/python-versions/) にある。

Blender とワールドのプロジェクトへの影響は次のとおり。

- Blender と `blenderExecutable` のラッパー（`.resoloop/blender-system-python`、#60・#68）は uv の Python の探索を使わないので、変わらない
- 既存の `.venv` は作り直されず、作ったときの Python を使い続ける。参照先の interpreter が消えた `.venv` は、次の `uv run` が
  `Ignoring existing virtual environment linked to non-existent Python interpreter` と表示して、システムの Python で作り直す。
  uv 管理の Python（`~/.local/share/uv`）は mount していないので rebuild で消え、それで作った `.venv` はこの作り直しになる

### 既存コンテナの移行

1. uv 管理の Python を参照する `.venv` を確かめる。リポジトリのルートで次を実行し、`home` が `~/.local/share/uv/python/` を指すものが対象になる。

   ```bash
   find . -maxdepth 4 -path '*/.venv/pyvenv.cfg' -exec grep -H '^home' {} +
   ```

   対象の `.venv` は、rebuild の後の最初の `uv run`（`uv run pytest` など）でシステムの Python に作り直される。
   その `.venv` で動いている処理は先に終える。`uv pip install` などで手で入れたパッケージは作り直しで消えるので、要るものは `pyproject.toml` の依存に書く。
2. **Dev Containers: Rebuild Container を実行する。** `containerEnv` はコンテナの作成時に反映されるので、ファイルの保存や
   エージェントの再起動だけでは既存のコンテナに効かない。uv 管理の Python とキャッシュは rebuild で消えるので、
   rebuild の前の `uv python uninstall` は要らない。rebuild の後に Herdr とエージェントを起動し直す。
3. Herdr のペインで起動したエージェントのシェルで次を実行する。上位に `.venv` が無い一時ディレクトリで、通常の実行が 3.14 以上になり、
   未導入の 3.12 の明示指定が `No interpreter found` と、ダウンロードが `manual` である旨を表示して失敗することを確かめる。

   ```bash
   (
       set -eu
       CHECK_DIR="$(mktemp -d)"
       trap 'rm -rf -- "${CHECK_DIR:?}"' EXIT
       cd -- "$CHECK_DIR"
       printf 'preference=%s downloads=%s\n' "${UV_PYTHON_PREFERENCE-}" "${UV_PYTHON_DOWNLOADS-}"
       uv run --no-project python -c 'import sys; print(sys.version); assert sys.version_info >= (3, 14)'
       if uv run --no-project --python 3.12 python -c 'import sys; print(sys.version)'; then
           printf 'Unexpected: Python 3.12 is still available\n' >&2
           exit 1
       fi
   )
   ```

   続けて、Blender とワールドのプロジェクトが今までどおり動くことを確かめる。

   ```bash
   bash .devcontainer/verify-resonite-tooling.bash
   (cd worlds/<name> && uv run pytest)
   ```

   通常の実行が古い版なら、`UV_PYTHON`・`VIRTUAL_ENV`・PATH と `.venv` の参照先を確かめる。3.12 の明示指定が成功するなら、
   探索先にまだ 3.12 がある。同じ環境変数を渡した子シェルでの確認は、rebuild と新しいペインでの確認の代わりにならない。

### 旧版で互換性を確かめる場合

`uv python install` をそのまま使うと、uv 管理の Python が `~/.local/share/uv` に残り、`~/.local/bin` に `python3.X` も置かれる。
`~/.local/bin` の `python3.X` は Blender を壊すことがあるので使わない（`docs/meshy-resoloop.md`）。古い版が要るときに限り、
一時ディレクトリに interpreter とキャッシュを隔離する。次は 3.12 の例で、`--no-bin` で `~/.local/bin` に実行ファイルを置かず、
終了時（失敗時を含む）に一時ディレクトリを消す。`--with` でパッケージを足すときも、同じ `UV_CACHE_DIR` を使う。

```bash
(
    set -eu
    PYTHON_CHECK_DIR="$(mktemp -d)"
    trap 'rm -rf -- "${PYTHON_CHECK_DIR:?}"' EXIT
    cd -- "$PYTHON_CHECK_DIR"
    env -u UV_PYTHON -u VIRTUAL_ENV \
        UV_PYTHON_INSTALL_DIR="$PYTHON_CHECK_DIR/python" \
        UV_CACHE_DIR="$PYTHON_CHECK_DIR/cache" \
        UV_PYTHON_DOWNLOADS=manual \
        uv python install --no-bin 3.12
    env -u UV_PYTHON -u VIRTUAL_ENV \
        UV_PYTHON_INSTALL_DIR="$PYTHON_CHECK_DIR/python" \
        UV_CACHE_DIR="$PYTHON_CHECK_DIR/cache" \
        UV_PYTHON_DOWNLOADS=manual \
        uv run --no-project --python 3.12 python -c 'import sys; print(sys.version)'
)
```

これらの変数を普段のシェルで export しない。古い版でリポジトリのスクリプトやワールドのビルドを実行しない。

## Resonite ワールド開発ツール

Dev Container の作成時に .NET 10 SDK、Blender、glTF import / export 用の `python3-numpy`、open3d が読む `libegl1`・`libgl1` を導入し、ResoLoop は NuGet の最新の公開版を
`.devcontainer/install_resoloop.bash`（`dotnet tool update --global ResoLoop --prerelease --allow-downgrade`）で導入する。
続けて、各プロジェクトの `resoloop skills sync --check` の結果を `.devcontainer/report-resoloop-skills.bash` で表示する
（差分があっても postCreate は失敗しない）。rebuild せずに最新へ上げるときも `bash .devcontainer/install_resoloop.bash` を実行する。
fork のビルドを一時的に使う方法は `docs/resoloop-fork-workflow.md` を参照する。
Blender は画面を開かずに実行する。Resonite 本体と ResoniteLink は
Windows ホスト側で準備する。接続確認の `resoloop doctor`、
Blender の GUI、ホスト側のネットワーク設定はこのセットアップの対象外とする。

`libegl1`・`libgl1` は、Meshy の物の UV の展開（UVAtlas）に使う open3d のためのものである。open3d は CPU だけで使うときも、
import のときに `libEGL.so.1`・`libGL.so.1` を読み、無いと `ImportError` で止まる。open3d 本体は Dev Container の全体には入れず、使う側が uv で入れる。
rebuild の後は `uv run --no-project --with open3d==0.20.0 python -c "import open3d"` で確かめられる（open3d と依存の 59 パッケージを取得し、展開すると 1 GB を超える）。
GPU（CUDA）と open3d の表示機能は対象外とする。

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

### Windows の Resonite へのテクスチャ取り込み（WSL）

Windows の Resonite は、コンテナのパス（`/workspaces/...`）を開けない。そのままだと `resoloop apply` のテクスチャ取り込みが
`ASSET_IMPORT_FAILED` か `REQUEST_TIMEOUT` で止まる（usaturn/resoloop#12）。WSL のときは、`initialize.bash` が
`.devcontainer/resonite-screenshots.env` に `RESOLOOP_HOST_PATH_MAP`（`/workspaces/<フォルダ名>=\\wsl.localhost\<ディストリビューション名>\<リポジトリの WSL パス>`）を書き、
`--env-file` でコンテナに渡す。設定は不要で、rebuild で反映される。

- `hostPathMap` を読めるのは、usaturn/resoloop の PR #16 を含む ResoLoop だけ。上流にマージされるまでは、公開版では無視される。
  それまでは `scripts/resoloop-fork.sh install origin/main` で fork のビルドを入れる
- WSL 以外（`WSL_DISTRO_NAME` が空）と、Windows 側のドライブ上（`/mnt/...`）のリポジトリでは書かない

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

## Context7 CLI（ctx7）

Context7 のドキュメントの取得は、`ctx7` CLI と `find-docs` スキル（`.agents/skills/find-docs`）で行う。Claude Code・Pi・Codex は同じ `find-docs` を読む。Context7 の MCP Server（`npx -y @upstash/context7-mcp`）と Pi の Context7 拡張（`npm:@upstash/context7-pi`）は使わない（#162）。2026-10-18 に別のリポジトリの Dev Container で、npx の一時展開物（`~/.npm/_npx`）の欠けから Context7 の MCP Server が Pi・Claude Code とも起動できなくなったため、npx と MCP Server に頼らない形にした。

### 導入

- postCreate は `bash .devcontainer/install_ctx7.bash` で、`ctx7` を `CTX7_CLI_VERSION` の版に固定して `npm install -g` し、PATH 上の `ctx7 --version` が一致することを確かめる。導入の失敗・PATH に無い・版の不一致は、postCreate の失敗として止まる。版は `install_ctx7.bash` にだけ書く
- 実体は npm のグローバルの `node_modules`（`$(npm root -g)/ctx7`）に入る。`~/.npm/_npx` の一時展開物は使わない
- `ctx7 setup` は実行しない。ctx7 0.8.0 の `ctx7 setup` は、`~/.claude`・`~/.claude.json`・`~/.codex/config.toml`・`~/.codex/AGENTS.md`・`~/.agents/skills` などに MCP 設定やスキルを書き込む。その多くはホストから bind mount した共有の場所で、ホストや他のコンテナにも影響する。生成するスキルは `find-docs` とも重複する
- zsh の `update` では更新しない

### 更新

1. `npm view ctx7 version engines` で新しい版と、必要な Node.js の版を確かめる
2. `.devcontainer/install_ctx7.bash` の `CTX7_CLI_VERSION` を変える
3. `bash .devcontainer/install_ctx7.bash` を実行して入れ替える（Rebuild Container でもよい）。PATH 上の `ctx7` は、入れ替えるまで古い版のままである
4. 下の「動作確認」が通ることを確かめ、PR で取り込む

`ctx7` は新しい版があると、対話的な端末で `Update available` と表示し、`ctx7 upgrade` や `npm install -g ctx7@latest` を勧める。この案内には従わず、上の手順で版を変える。

### MCP と Pi の拡張からの移行

リポジトリの設定から、次を外した。

- `.mcp.json`（Claude Code）と `.pi/mcp.json`（Pi）の `context7`。`google-dev-knowledge` は残す
- `.cursor/mcp.json`（`context7` だけだった）と `.codex/config.toml`（`context7_stdio` だけだった）。どちらもファイルごと消した
- `install_beforehand.bash` が導入する Pi の拡張の一覧の `npm:@upstash/context7-pi`

リポジトリの外の Context7 の設定は、セットアップでは変えない。外すかどうかは利用者が決める。

| 設定 | 場所 | 外し方 |
|---|---|---|
| Claude Code のユーザースコープの MCP | `~/.claude.json` の `mcpServers` | `claude mcp remove context7 -s user` |
| Codex のユーザー設定の MCP | `~/.codex/config.toml` の `mcp_servers.context7` | その表を消す |
| claude.ai の Context7 コネクタ（`mcp__claude_ai_Context7__*`） | claude.ai のアカウントの設定 | claude.ai のコネクタの設定で外す。アカウント単位の設定で、他のプロジェクトにも効く |
| Pi の Context7 拡張 | 共有の `~/.pi/agent/settings.json` | 外さない（次の節） |

マージの後、親の checkout を `origin/main` に更新するまでは、その下の worktree で起動した Claude Code にも `context7` が残る。Claude Code は祖先にある親の checkout の `.mcp.json` も読むためである。

### Pi の Context7 拡張をプロジェクト単位で止める

`npm:@upstash/context7-pi` は、`~/.pi` を共有する他のリポジトリ（usaturn/agent-workspace など）のセットアップが入れ続ける。`pi remove` で消すと、それらのリポジトリの Pi からも Context7 が外れ、次のセットアップでまた入る。このリポジトリでは共有の `~/.pi` を変えず、`.pi/settings.json` の `packages` に次の項目を置いて、プロジェクト単位で読み込みを止める。ワールドは `.pi` の symlink で同じ設定を読む。

```json
{
  "source": "npm:@upstash/context7-pi",
  "autoload": false,
  "extensions": ["!**"],
  "skills": ["!**"],
  "prompts": ["!**"],
  "themes": ["!**"]
}
```

- `autoload: false` を付けた project の項目は、ユーザー設定の同じパッケージに対する差分として働く（Pi に同梱の `docs/packages.md` の「Understand scope and identity」）。`"!**"` で、拡張（`resolve-library-id`・`query-docs` のツール）、スキル（`context7-docs`）、プロンプト（`/c7-docs`）を読み込まない
- 空配列（`"extensions": []` など）では止まらない。Pi 1.3.0 は差分の空配列を「変更なし」として扱い、ユーザー設定のとおりにすべて読み込む（2026-10-18 に確認）
- project の設定なので、`+builtin:mcp` と同じく project trust を前提とする
- ユーザー設定に `npm:@upstash/context7-pi` が無いと、差分の土台が無いため、Pi は project の `.pi/npm` に context7-pi を導入する（読み込みはしない）。すべてのリポジトリが移行して共有の `~/.pi` から context7-pi を外すときは、`.pi/settings.json` のこの項目も外す
- `install_beforehand.bash` の撤去の処理（「pi-lens の撤去」などの `remove_pi_*`）には加えない。他のリポジトリが使い続けるため

読み込んでいないことは、モデルを呼ばずに RPC モードで確かめられる。trust 済みの親の checkout で実行する。trust していない worktree では `--approve` を付ける。

```bash
printf '{"type":"get_commands"}\n' | pi --mode rpc --no-session --no-mcp --offline | grep -oE 'c7-docs|skill:context7-docs' || echo "context7-pi is not loaded"
```

### 認証

- 環境変数 `CONTEXT7_API_KEY` を基本とする。「秘密情報」の節の `~/.config/create-reso-world/env` に書けば、シェルの起動時に export される。`ctx7` はこの変数があれば、`ctx7 login` の認証情報より優先して使う。キーの値をリポジトリ・Issue・PR・ログに書かない
- `cod` は、`CONTEXT7_API_KEY` が無いと入力を求める。Codex から `ctx7` を呼ぶときにも使う
- `ctx7 login` の認証情報は `~/.config/context7/credentials.json`（`XDG_CONFIG_HOME` が絶対パスならその下）に保存される。`~/.config/context7` は bind mount していないので、Rebuild で消える
- `ctx7 whoami` は `ctx7 login` の状態だけを表示する。`CONTEXT7_API_KEY` を使っていても `Not logged in.` と出る
- 認証なしでも使えるが、レート制限が低い。quota を超えると `Monthly quota reached` などで失敗する
- `ctx7` は利用状況のテレメトリを Context7 に送る。止めるときは `CTX7_TELEMETRY_DISABLED=1` を export する（`env` に書いてもよい）

### 動作確認

```bash
command -v ctx7
readlink -f "$(command -v ctx7)"   # $(npm root -g)/ctx7/dist/index.js（~/.npm/_npx ではない）
ctx7 --version                     # install_ctx7.bash の CTX7_CLI_VERSION と一致する
if [ -n "${CONTEXT7_API_KEY:-}" ]; then echo "CONTEXT7_API_KEY: set"; else echo "CONTEXT7_API_KEY: not set"; fi
ctx7 library react "How to clean up useEffect with async operations"
ctx7 docs /react/react "useEffect cleanup"
```

加えて、Claude Code・Pi で `find-docs` を使った取得を試す。Claude Code の `/mcp`・`claude mcp list` と Pi の `pi mcp list` に Context7 が無く、`google-dev-knowledge` が接続できることを確かめる。

### トラブルシュート

| 症状 | 対応 |
|---|---|
| `ctx7: command not found` | Rebuild Container するか、`bash .devcontainer/install_ctx7.bash` を実行する。`npx ctx7` で代えない |
| postCreate が `[install_ctx7] ERROR: ... is version ...` で止まる | `command -v ctx7` で、PATH の前のほうに別の `ctx7` が無いかを確かめる |
| `⚠ Library has been redirected` と出て終了コード 1 | 表示された新しい ID でやり直す（例: `/facebook/react` → `/react/react`） |
| `Monthly quota reached`・`quota exceeded` | `CONTEXT7_API_KEY` を設定するか、`ctx7 login` を実行する |
| `Update available` と表示される | 従わない。「更新」の手順で版を変える |
| `context7` が MCP の一覧に残る、`Failed to reconnect` になる | 古い設定を読んでいる。親の checkout を `origin/main` に更新し、エージェントを起動し直す。リポジトリの外の設定（「MCP と Pi の拡張からの移行」の表）も確かめる |
| このリポジトリの Pi に `resolve-library-id`・`/c7-docs` が出る | project trust を確かめる。`.pi/settings.json` の項目が空配列になっていないかを確かめる |

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
11. `install -m 0755 .devcontainer/piccg ~/.local/bin/piccg`
12. `install -m 0755 .devcontainer/piccd ~/.local/bin/piccd`
13. `install -m 0755 .devcontainer/piga ~/.local/bin/piga`
14. `install -m 0755 .devcontainer/pigs ~/.local/bin/pigs`
15. `install -m 0755 .devcontainer/pigl ~/.local/bin/pigl`
16. `install -m 0755 .devcontainer/pixg ~/.local/bin/pixg`
17. `install -m 0755 .devcontainer/pigemf ~/.local/bin/pigemf`
18. `install -m 0755 .devcontainer/pigemp ~/.local/bin/pigemp`
19. `install -m 0755 .devcontainer/pigema ~/.local/bin/pigema`
20. `zsh scripts/setup_pi_superagents.zsh`
21. `bash .devcontainer/install_ctx7.bash`

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

Issue #125 で agent-workspace の導入手順にそろえた。`pi-mcp-adapter`・`pi-distill`・
単独登録の `pi-extensions-tool-display` / `pi-extensions-i18n`・`pi-lens` は撤去し、
`@plannotator/pi-extension` は導入・保持する。`@upstash/context7-pi` は #162 で導入をやめた。
他のリポジトリが使うので共有 `~/.pi` の登録は消さず、このリポジトリでは読み込まない（「Context7 CLI（ctx7）」）。
組み込み MCP のため settings の `-builtin:mcp` だけを取り除き、他の設定は保持する。
撤去に失敗して登録や npm マニフェストが残った場合は、理由を表示して postCreate を止める。

Pi の導入・拡張更新より前に `.devcontainer/pi-provider-setup.py` が settings を検査する。
`settings.json` が symlink・hard link・特殊ファイル、または不正な JSON / 必要な配列構造なら、
共有先を変更したりリンクを切断したりせず、その Pi 節を止める。保存先の共有方法を確認し、
通常ファイルを使う配置へ利用者が調整してから再実行する。MCP 撤去の直前と cleanup 時も同じ
検査を行い、通常ファイルの mode と他の設定を保持する。I/O 障害では未使用 staging を掃除するが、
それ以前に完了した npm / Pi 操作全体の巻き戻しや同時更新との排他は保証しない。

旧独自 cleanup / JSON helper と撤去前の自動バックアップは廃止した。古いバックアップや
MCP の状態ファイル、利用者のモデルと認証は自動削除しない。共有 `~/.pi` を使う全コンテナの
Pi を終了してから rebuild する。ほかのコンテナも context7-pi / Plannotator を保持する版にそろえる。

rebuild しない場合、利用者が Pi を止めて次を実行する。`pi remove` が未登録を理由に
終了コード1を返す場合は `pi list` と npm マニフェストで撤去対象の不在を確かめる。
`-builtin:mcp` が残っていれば settings の該当要素だけを手で取り除く。

```bash
pi remove npm:pi-mcp-adapter
pi remove npm:pi-distill
pi remove npm:pi-extensions-tool-display
pi remove npm:pi-extensions-i18n
pi remove npm:pi-lens
pi install --approve npm:@plannotator/pi-extension
```

`pigou` と新規モデル雛形の `union-alpha` は廃止した。既存の `~/.local/bin/pigou` や
利用者の `models.json` は自動では消さない。不要な旧ファイルとモデルは利用者が内容を確認して
整理する。`ccdu`（Claude Code）は対象外なので変更しない。

## pi のモデル定義とランチャー

`~/.pi` は `devcontainer.json` で bind mount している。認証情報
（`~/.pi/agent/auth.json`）とモデル定義（`~/.pi/agent/models.json`）が
ホスト側に残るため、リビルド後に `scripts/setup_pi.zsh`、
`scripts/setup_pi_opencode_go.zsh`、`scripts/setup_pi_commandcode_goat.zsh`
を実行し直す必要はない。

`install_beforehand.bash` は次のものを配置する。挙動が異なるのは、
models.json だけが bind mount の内側で、他が外側にあるためである。

- `.devcontainer/pi-models.json` → `~/.pi/agent/models.json`。
  bind mount 側を正とし、ファイルが**無い場合のみ**配置する。毎回上書きすると、
  ホスト側で加えたモデル定義の変更がリビルドで失われる
- `.devcontainer/pigo` → `~/.local/bin/pigo`。`~/.local/bin` は bind mount の
  対象外でリビルドのたびに失われるため、毎回上書きで配置する
- `.devcontainer/pigod` → `~/.local/bin/pigod`。pigo と同じ理由で毎回上書き
- `.devcontainer/piccg` → `~/.local/bin/piccg`。pigo と同じ理由で毎回上書き
- `.devcontainer/piccd` → `~/.local/bin/piccd`。pigo と同じ理由で毎回上書き
- `.devcontainer/piga`・`pigs`・`pigl` → `~/.local/bin/`。同様に毎回上書き
- `.devcontainer/pixg` → `~/.local/bin/pixg`。同様に毎回上書き
- `.devcontainer/pigemf`・`pigemp`・`pigema` → `~/.local/bin/`。同様に毎回上書き
- `.devcontainer/pi-superagents/<launcher>.json` → `~/.pi/agent/extensions/subagent.d/<launcher>/config.json`、
  `.devcontainer/pi-superagents-exec.zsh` → `~/.local/bin/pi-superagents-exec.zsh`。
  `install_beforehand.bash` は `setup_pi_superagents.zsh` を呼んでこの 2 種を配置する
  （詳細は後述の「pi-superagents のランチャー別 model tier」を参照）

`~/.local/bin` への PATH は `zshrc.txt` が通すため、別途の設定は不要である。

### Plannotator のブラウザーレビュー

[Plannotator](https://plannotator.ai/) は、日本語を含む Markdown の Plan を
ブラウザーで確認・注釈し、Pi へ承認／修正要求を返すために使う。
Pi では `npm:@plannotator/pi-extension` 拡張だけでよく、既存の Node.js 24 で動く。
Plannotator CLI や Bun の追加導入は不要である。

コンテナ作成／リビルド時は、`install_beforehand.bash` の既存の Pi 拡張導入処理が
この拡張も登録する。`devcontainer.json` は `PLANNOTATOR_REMOTE=0` だけを設定し、
`PLANNOTATOR_PORT` と Plannotator 用の `forwardPorts` は設定しない。拡張はレビューごとに
`127.0.0.1` の空いているポートを選ぶ（Plannotator のローカルモードの既定）。
既存の 8000、`~/.pi` の bind mount、認証・モデル・他のパッケージ設定、
pi-superagents のランチャー別設定は保持する。

反映作業は利用者が行う。推奨手順は **Dev Containers: Rebuild Container** を実行し、
作成／リビルド後に Pi（使っているランチャー）を起動し直すことである。
設定ファイルの保存や Pi の再起動だけでは、既存コンテナ全体に `containerEnv` は
反映されない。

リビルドしない既存環境では、利用者が次を実行する。環境変数はこの起動だけに渡す。
普段のランチャーを使う場合は、末尾の `pi` をその実行ファイル名（例: `pigs`）に置き換える。
起動済みの Pi は終了し、拡張を導入した後に起動し直す。

```bash
pi install --approve npm:@plannotator/pi-extension
env -u PLANNOTATOR_PORT PLANNOTATOR_REMOTE=0 pi
```

レビューの手順は次のとおり。

1. 通常の Plan 確認時に pi-superagents の `superpowers_plan_review` ツールでレビューを依頼する。
   受付時点ではレビュー待ちであり、まだ承認されたわけではない。
2. Pi の端末に表示されるレビュー URL（`http://localhost:<ポート>/...`）を確認する。
   ポートはレビューごとに変わる。
3. Windows のブラウザーでレビュー URL を開く。WSL の mirrored モードでは、Windows と
   host network のコンテナが `localhost` で互いに届く。開けないときは、VS Code の **Ports**
   画面でそのポートの転送先アドレス（Local Address）を開く（自動で転送されていなければ追加する）。
   その場合も、レビュー URL のパスとクエリを付ける。
4. ブラウザーで Plan を確認し、承認または注釈付きの修正要求を返す。
   承認は Pi 側へ戻り、修正要求は Plan の見直しと再レビューに使われる。

画面が出ないときは、pi-superagents の `usePlannotator` が `false` に上書きされて
いないか確認する。ランチャー利用時は、共通設定に加え、実際に使う
`~/.pi/agent/extensions/subagent.d/<launcher>/config.json` も確認する。
変更する場合は必要なキーだけを調整し、既存の model tier や他の設定は残す。

このリポジトリは `--network=host` を使うため、移植元の remote mode（`0.0.0.0` に bind）を
使わない。`PLANNOTATOR_REMOTE=0` で `127.0.0.1` だけに bind する。移植元の固定範囲
（`PLANNOTATOR_PORT=19432-19441`）と、その範囲の `forwardPorts` も使わない。
WSL の mirrored モードでは、Windows 側で使われているポートを Linux 側から bind できない
（`.wslconfig` の `ignoredPorts` の説明）。VS Code の転送は Windows 側で待ち受けるため、
このコンテナや他のコンテナ（agent-workspace など）のウィンドウが転送しているポートを
Plannotator は使えず、範囲内のすべてが転送されていると起動できない（`Port selection ... exhausted`）。
`PLANNOTATOR_PORT` を指定するときは、どのウィンドウも転送していないポートを選び、
そのポートを `forwardPorts` に載せない。
Docker の公開ポート、外部共有・トンネルは追加しない。
レビュー URL を外部へ共有しない。ブラウザーの自動起動は保証しないため、
Windows の実ブラウザーでの閲覧と承認／修正要求の往復は利用者が手動で確認する。

### モデル定義の管理

独自のモデル定義は `.devcontainer/pi-models.json` を単一の情報源とする。
`install_beforehand.bash` も 3 つの setup スクリプトも、定義を埋め込まずこの
ファイルから読む。定義を変更するときはこのファイルを編集してコミットする。
`openai-codex` の GPT-6 モデル、`xai` の Grok 4.7、`google-vertex` の
Gemini 3.8 Flash / Gemini 3.1 Pro Preview は Pi の組み込みカタログを使うため、
このファイルには追加しない。

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
ID は表示名と一致しないので、OpenCode Go ランチャーの ID は `pi --list-models` で
確認する。Vertex ランチャーは認証を調べない bundled catalog の確認を使う（後述）。
2026-09-11 に `deepseek-flash` が `deepseek-v4.1-flash` へ改名され、
旧 ID を残していた `pigod` は次の警告を出したうえで `opencode-go` の既定モデル
（`kimi-k2.6`）の定義を複製したモデルで起動していた:

```console
Warning: Model "deepseek-flash" not found for provider "opencode-go". Using custom model id.
```

この状態でもリクエスト自体は通るため気づきにくいが、kimi-k2.6 の定義が
使われる結果、context window は 262,144（本来は 1,000,000）、max output は
65,536（本来は 384,000）になり、`supportsReasoningEffort` が false のため
`--thinking max` の `reasoning_effort` も送られない。
`scripts/setup_pi_opencode_go.zsh` の手順 6 は各ランチャーのモデル ID を
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
`zsh scripts/setup_pi_commandcode_goat.zsh` を実行して `commandcode`
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
`auth.json` に書いた api_key または `OPENCODE_API_KEY` で解決され、`pixg` と
同じく起動前の確認は行わない。`auth.json` に資格情報が無い環境では `cheap`
tier の子 Pi が provider 認証エラーになるため、必要なら `OPENCODE_API_KEY` を
設定して `zsh scripts/setup_pi_opencode_go.zsh` を実行する。

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
`cheap` / `balanced` / `max` tier はランチャーごとに GPT-6 Luna / GPT-6.1
Sol / GPT-6 Astra を割り当てる（`pigs` の `cheap` だけは OpenCode Go の
`deepseek-v4.1-flash`。下表を参照）。ログイン済みの環境では、次のテストでも、ランチャーと
tier が使う `openai-codex` のモデルが Pi の一覧にあることを確認できる。

```bash
PI_CODEX_LIVE_CHECK=1 bash .devcontainer/test-pi-openai-codex.bash
bash .devcontainer/test-pi-migrations.bash
```

### SuperGrok / X Premium の Grok 4.7 ランチャー

| launcher | Provider / Model |
|---|---|
| `pixg` | `xai/grok-4.7` |

`pixg` の親 Pi と `max` tier は SuperGrok または X Premium
サブスクリプションの xAI OAuth 認証を使い、`cheap` / `balanced` tier の
子 Pi は OpenCode Go の `deepseek-v4.1-flash` を使う。`XAI_API_KEY` は
不要で、xAI API のキー課金には接続しない。
初回だけ素の `pi` を起動して `/login xai` を実行し、
`Sign in with SuperGrok or X Premium` からログインする。OAuth 情報は
`~/.pi/agent/auth.json` に保存される。`~/.pi` は Dev Container に bind mount
されているため、リビルド後もログイン状態を保持する。認証は対話操作が必要で、
`postCreateCommand` から自動ログインしない。xAI が未認証なら、
`pixg` はログイン手順を表示して起動前に終了する。
子 Pi が使う OpenCode Go の資格情報は `setup_pi_opencode_go.zsh` が
`auth.json` に書いた api_key を共有し、`pigo` / `pigod` と同じく起動前の
確認は行わない。

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

### Vertex AI の Gemini ランチャー（agent-workspace #578・#680）

| launcher | Provider / Model | thinking |
|---|---|---|
| `pigemf` | `google-vertex/gemini-3.8-flash` | `high` |
| `pigemp` | `google-vertex/gemini-3.1-pro-preview` | `high` |
| `pigema` | `google-vertex/gemini-4-argon` | `high` |

3 ランチャーとも Pi の native Google Vertex AI adapter と Application Default
Credentials（ADC）を使う。Gemini API 用の `google` provider ではない。
3 モデルとも Pi 1.3.0 の bundled catalog にあり、独自のモデル定義は追加しない。
thinking level はどれも `low` / `medium` / `high` で、`high` が実際の最大値である。

対応する location と課金の方式はモデルによって異なる（Google の公式情報、2026-10-15 更新）。

- `gemini-3.8-flash`・`gemini-3.1-pro-preview`:
  [Flex PayGo 対応モデル一覧](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/flex-paygo)
  で `global` endpoint の対象
- `gemini-4-argon`:
  [モデルのページ](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/4-argon)
  で GA。location は `global` と multi-region の `us`・`eu`、課金の方式は
  Standard PayGo・Priority PayGo・Provisioned Throughput。Flex PayGo の一覧には載っていない

location を変更する場合は、利用するモデルの対応先を確認する。
`gemini-4-argon` の単価は、Pi 1.3.0 の catalog で 1M トークンあたり input $2・output $10 と、
`gemini-3.8-flash`（input $0.75・output $3.75）より高い。Pi のシステムプロンプトだけで
入力が約 1 万トークンあるため、agent-workspace #680 の起票時の実測では 1 回の呼び出しで約 $0.02 かかった。

起動時の環境変数は次の順で決める（空文字も未設定として扱う）。

- project: `GOOGLE_CLOUD_PROJECT` → `GCLOUD_PROJECT` → `hobby-372711`
- location: `GOOGLE_CLOUD_LOCATION` → `global`
- ADC パス: 非空の `GOOGLE_APPLICATION_CREDENTIALS` →
  `auth.json` の `google-vertex.env.GOOGLE_APPLICATION_CREDENTIALS`。
  どちらも無ければ Pi に通常の ADC 解決を任せる。他の環境変数はそのまま引き継ぐ
- `GOOGLE_CLOUD_API_KEY` だけをランチャーのプロセスツリーから外す。
  呼び出し元のシェル、素の `pi`、他のランチャーには影響しない

ADC は利用者が事前に用意する。ランチャーは credential ファイルの存在・有効性を
確認せず、ログイン、gcloud の実行、トークンの取得・保存を行わない。
ADC が無い状態でも Pi まで起動し、認証の解決とエラー表示は Pi に任せる。
Pi の `/login google-vertex` で保存したサービスアカウントの ADC パスも利用する。
保存済みパスは同じ snapshot から取り出して、このプロセスツリーの環境へ渡す。
パスをコマンドとして実行したり、資格情報ファイルを調べたりはしない。
必要なら使うシェルで project / location や別の ADC パスを指定する。
明示した非空の ADC パスが優先され、保存済み project / location は引き継がない。

```bash
export GOOGLE_CLOUD_PROJECT=your-project
export GOOGLE_CLOUD_LOCATION=global
# サービスアカウントの ADC ファイルを使う場合だけ指定する:
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
pigemf
pigemp --session 'session with spaces.jsonl'
pigema
```

環境変数の API key を外すだけでは、Pi が優先する `auth.json` の保存済み key や
`models.json` の `apiKey` が使われ得る。そのため、この 3 ランチャーだけは、
起動時に `auth.json` を設定として解析し、全 provider の `type: "oauth"` の entry を
除外する。他 provider の非 OAuth entry は保持し、`google-vertex` を
`{type: "api_key", key: "gcp-vertex-credentials"}` に置き換えた読み取り専用の overlay を、
既存の bwrap namespace 内へ重ねる。保存済み Vertex env から残すのは ADC パスだけで、
marker entry の `env` に保持する。この文字列は key / token ではなく、Pi native adapter が
API key として送信せず ADC を使うための marker である。marker の key 分岐では saved env が
SDK に渡らないため、ADC パスは前述の実効環境へも渡す。
`!command` などの保存済み Vertex key は実行しない。
既存の `auth.json` を上書きせず、内容や overlay をログ・argv・namespace 外のディスクへ
出さない。`auth.json` が未作成の場合だけ、mount 先として空の JSON オブジェクト `{}` を
mode `0600` で作る。同時起動時も既存ファイルは置き換えず、資格情報は書き込まない。
解析に失敗した場合は秘密を含まない案内で起動を止める。

子 Pi も同じ namespace と overlay を継承する。auth の重ね先は
`PI_CODING_AGENT_DIR`（`~/` と相対パスも対応）に従い、子の cwd が変わっても
同じ場所を読むようプロセス内で絶対パスにする。tier config の重ね先は、
拡張の読み先である HOME 基準の共有パスのままである。

**読み取り専用 overlay の注意:** Pi は起動時やモデル切替時にも OAuth を更新する。
読み取り専用の snapshot では更新後の token を保存できず、refresh token が差し替わると
元の認証が使えなくなる可能性があるため、期限内の OAuth entry も含めて除外する。
この 3 ランチャー内では保存済み OAuth credential を使えない。それを使う provider は
素の `pi` または既存の対応ランチャーで利用する。`auth.json` は全 provider で読み取り専用
なので、`/login`・`/logout` も素の `pi` で行う。
重ねるのは `auth.json` だけで、settings・sessions とそれらの lock は通常の保存先を使う。
初回の設定・会話も永続化し、素の `pi` や別ランチャーとの
設定更新は同じ lock を使う。これは認証先の既定を選ぶ仕組みであり、sandbox ではない。
追加引数はそのまま渡す
ため、明示的な `--api-key`・provider 変更や拡張による認証の変更までは禁止しない。

起動前には npm でインストールした Pi の実体にある bundled catalog を、
**メタデータだけ**読んで必要な exact ID を確認する。`pi --list-models` や
availability API は認証を確認するため、このガードでは使わない。古い Pi、catalog の
配置変更、必要な ID の欠落では起動を止め、fuzzy match や別モデルのメタデータを
複製するフォールバックを防ぐ。catalog の cache や独自定義で欠落を補わず、Pi 本体を
更新する。dry-run は argv だけを表示し、auth の読み取りや作成を行わない。
確かめる ID は、親 Pi のモデルと、そのランチャーの tier が使う Vertex のモデルである
（例: `pigema` は `gemini-4-argon` と `cheap` の `gemini-3.8-flash`）。

Vertex ランチャーの一覧と確かめる ID は、`pi-superagents-exec.zsh` の
`pi_google_vertex_models` だけで定義する。auth の overlay・catalog の確認・ADC の受け渡しは、
この一覧に載ったランチャーにだけ適用される。Vertex ランチャーを足すときは、ランチャー本体と
tier の設定に加えてこの一覧に登録し、確かめる ID を tier に合わせる。

コンテナ作成／リビルド時は実行ファイルを毎回配置する。リビルドしない既存環境では、
更新済みの親リポジトリのルートで次を実行する。認証設定やモデル定義は変更しない。

```bash
mkdir -p ~/.local/bin
install -m 0755 .devcontainer/pigemf ~/.local/bin/pigemf
install -m 0755 .devcontainer/pigemp ~/.local/bin/pigemp
install -m 0755 .devcontainer/pigema ~/.local/bin/pigema
zsh scripts/setup_pi_superagents.zsh --if-absent
```

`--if-absent` は共有 config と既存ランチャーの tier を保持し、新規 tier を配置する。
新規ランチャーの tier を後からリポジトリの定義に揃えたい場合は、下の更新手順を使う。

### 組み込み MCP と廃止した拡張

`.pi/settings.json` の `+builtin:mcp` で pi の組み込み MCP を有効にする。
`.pi/mcp.json` は Google Developer Knowledge の HTTP サーバーを設定する（Context7 は MCP では使わない。
「Context7 CLI（ctx7）」）。利用者は `GOOGLE_DEV_KNOWLEDGE_API_KEY` を設定し、pi の
project trust を許可してから使う。キーが無い場合、pi は接続せずに、キーを解決できないというこのサーバのエラーを
起動後に1回通知するが、他の機能は使える。プロジェクトの定義は同名の利用者設定より優先されるため、利用者設定では無効化できない。
`/mcp` で無効化すると追跡対象の `.pi/mcp.json` が書き換わるため、その変更はコミットしない。
各ワールドはプロジェクト直下の `.pi` symlink から同じ設定を読む（`worlds/<name>` は `../../.pi`、従来位置は `../.pi`）。
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

### pi-distill の撤去（agent-workspace #508）

pi-distill（ツール出力の Distillation）は廃止した。インストール対象から外す
だけでは bind mount 側の登録が残るため、`install_beforehand.bash` はリビルド時に
`pi remove npm:pi-distill` で既存環境の登録と pi 管理の npm マニフェストも
掃除する。`pi-extensions-tool-display` / `pi-extensions-i18n` が単独登録されて
いる環境でも同じステップで外す。

リビルドしない既存環境では、次を実行して登録を消し、`~/.zshrc` に残った
`PI_DISTILL_*` と `PI_EXTENSIONS_LOCALE` の export を手で取り除く。

```bash
pi remove npm:pi-distill
```

`~/.pi/agent/extensions/pi-distill/` と `~/.pi/agent/extensions/pi-tool-display/`
の設定ディレクトリ、および `~/.pi/agent/models.json` の `deepinfra-distill`
ブロックは、参照されなくなった不活性な残骸として残る。消す場合は利用者側で
削除する。手動選択用の `deepinfra` provider は残してある。

### pi-lens の撤去（agent-workspace #684）

pi-lens（書き込み直後の lint・整形と、`lens_diagnostics` などのツール）は廃止した。
移植元で得ているものに比べて、整形による差分の混入、1 リクエストあたり
約 3,000 トークンと起動時間の増加、agent-workspace #655 の回避策の保守の負担が大きいためである。
インストール対象から外すだけでは bind mount 側の登録が残るため、
`install_beforehand.bash` はリビルド時に `pi remove npm:pi-lens` で既存環境の登録と
pi 管理の npm マニフェストも掃除する。撤去後も一覧かマニフェストに残っていれば、
理由を出して Dev Container の作成を止める。

`~/.pi` はホストと bind mount で共有しており、ほかのコンテナ（agent-workspace・xrift-poc）も
同じ登録を使う。撤去はそれらのコンテナからも pi-lens を外す。`pi remove` は共有の
`~/.pi/agent/npm/node_modules/pi-lens` を消すので、ほかのコンテナで動いている Pi を
止めてからリビルドする。ほかのリポジトリのインストーラが `npm:pi-lens` を入れたままだと、
そのコンテナを作り直したときに再登録される（usaturn/xrift-poc#16・
usaturn/create-reso-world#117 で導入をやめる）。

リビルドしない既存環境では、ほかのコンテナの Pi を止めてから次を実行する。

```bash
pi remove npm:pi-lens
```

コンテナ内の `~/.pi-lens`（pi-lens が取得した管理ツールとログ）は bind mount の
対象外で、リビルドで消える。既存の worktree や `/tmp` の下に残った
`.pi-lens-probe-home/` は、もう ignore しないので未追跡ファイルとして見える。
中身が pi-lens のログだけであることを確かめてから削除する。

### setup スクリプトを使う場面

`scripts/setup_pi.zsh`（deepinfra）、`scripts/setup_pi_opencode_go.zsh`
（opencode-go）、`scripts/setup_pi_commandcode_goat.zsh`（commandcode）は、
リビルドのたびに実行するものではない。次の場面で使う。

- API キーをローテーションしたとき（`setup_pi_opencode_go.zsh` が
  `auth.json` を書き換える。commandcode は環境変数参照なので
  キーのローテーションで setup スクリプトの実行は不要）
- ホスト側の `~/.pi` を作り直したとき
- `pi-models.json` を編集し、既存の `~/.pi/agent/models.json` へ反映したいとき
  （`install_beforehand.bash` は既存ファイルを上書きしないため）

いずれも冪等で、`providers` のうち対象プロバイダのエントリだけを置き換える。
3本は `.devcontainer/pi-provider-setup.py` で入力と保存先を先に検証する。
`PI_CODING_AGENT_DIR` の `~`・`~/` は HOME へ展開し、相対パスは実行時の cwd が基準になる。
UTF-8 BOM 付きの models/auth も読める。models の既存 mode と他 provider は保持し、新規は `0600`、
auth は `0600` にする。models の変更時だけ、元のバイト列と mode を一意なバックアップに残す。
symlink・hard link・特殊ファイルの保存先は、共有先の変更やリンク切断を避けるため、何も更新せず拒否する。
その場合は共有方法と保存先を利用者が確認し、通常ファイルを使う設定にしてから再実行する。
不正入力は auth・バックアップ・ランチャー・外部 Pi コマンドを変更する前に拒否する。
I/O 障害では途中まで書いたファイルを置かず非0で終わるが、完了したファイルの置換と models のバックアップは
残り得る。複数ファイル全体の取り消しや同時更新の排他は行わないため、Pi と他の setup を止めて実行する。
`setup_pi_opencode_go.zsh` は `.devcontainer/pigo` と `.devcontainer/pigod` を、
`setup_pi_commandcode_goat.zsh` は
`.devcontainer/piccg` と `.devcontainer/piccd` をそのまま配置するため、
実行してもランチャの内容は `install_beforehand.bash` の配置結果と一致する。
この2本は互換な共通ヘルパも一緒に更新し、既存のランチャー別 tier 設定は変更しない。

commandcode の 2 つのランチャを `setup_pi_commandcode_goat.zsh` が同居して
受け持つのは、両者が同じ `providers.commandcode` エントリを共有するためで
ある。スクリプトを分けると 2 本が同じエントリを全置換し合い、片方だけを
実行した時点で他方のモデル定義が `models.json` から消える。

### API トークン

Meshy の `MESHY_API_KEY` はここには含めない。ファイルを作らない非表示入力の手順は「Meshy CLI と生成物の受け渡し」にある。

次の変数は、「秘密情報」の節の `~/.config/create-reso-world/env` に書けばシェルの起動時に
export される。書かない場合は、必要なときに手動で export する。

- `OPENCODE_API_KEY` は `pigo`・`pigod` と、`pigs`・`pixg` の OpenCode Go の tier の
  子 Pi の実行には不要である。bind mount した `auth.json` に資格情報が残るため、pi はそこから読む
  （`pi auth check --provider opencode-go` が `ready` を返す）。
  `setup_pi_opencode_go.zsh` でキーを更新するときと、`auth.json` に資格情報が無い環境で
  pi の OpenCode Go を使うときに必要になる
- `OPENCODE_GO_API_KEY` は旧名である。OpenCode Go を使う `pigo`・`pigod`・`pigs`・`pixg` は、
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
- `CONTEXT7_API_KEY` は、共有の `find-docs` スキルが使う Context7 CLI（`ctx7`）が読む（「Context7 CLI（ctx7）」）。
  未設定のまま `cod` を起動すると、入力を求める（Codex から `ctx7` を呼ぶときにも使う）。無くても動くが、レート制限が低くなる

### pi の TUI モードと Herdr のスクロール履歴

Pi 1.0.0 から、対話 TUI の既定モードは `fullscreen` になった。このモードは
代替画面を使って会話履歴を Pi 内で管理するため、Herdr の通常のスクロール履歴に
過去の出力が残らず、コピーモードでさかのぼれない。

このリポジトリが管理する `pigo`・`pigod`・`piccg`・`piccd`・`piga`・
`pigs`・`pigl`・`pixg`・`pigemf`・`pigemp`・`pigema` は、共通ヘルパ `pi-superagents-exec.zsh` から
`pi --tui-mode regular` を起動する。regular は通常画面と端末のスクロール履歴を
使うため、画面高を超えた出力も Herdr のコピーモードで読める。
ユーザー／プロジェクトの `settings.json` は書き換えず、起動引数で指定する。
provider・model・thinking・認証確認・ランチャー別設定の分離は従来どおりで、
`--resume`・`--session`・メッセージなどの追加引数もそのまま転送する。

Dev Container の初期化／リビルドでは `install_beforehand.bash` が全ラッパーを
配置し、`setup_pi_superagents.zsh --if-absent` が共通ヘルパを更新する。
リビルドしない既存環境では、更新済みの親リポジトリのルートで次を実行し、
ラッパーを起動し直す。

```bash
zsh scripts/setup_pi_superagents.zsh --if-absent
```

`--if-absent` は既存のランチャー別 tier 設定を保持するが、共通ヘルパは毎回
更新する。各 provider の setup スクリプトが配置するラッパーも同じヘルパを使う。
この指定はラッパーの既定値なので、追加引数に `--tui-mode fullscreen` を指定した
場合はその指定が優先される。素の `pi` の既定モードには影響しない。

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
| `piccg` | `commandcode/meta/muse-spark-1.3-contributor` | `commandcode/meta/muse-spark-1.3-contributor` | `commandcode/deepseek/deepseek-v4.1-flash` |
| `piccd` | `commandcode/meta/muse-spark-1.3-contributor` | `commandcode/deepseek/deepseek-v4.1-flash` | `commandcode/deepseek/deepseek-v4.1-flash` |
| `piga` | `openai-codex/gpt-6-luna` | `openai-codex/gpt-6.1-sol` | `openai-codex/gpt-6-astra` |
| `pigs` | `opencode-go/deepseek-v4.1-flash` | `openai-codex/gpt-6.1-sol` | `openai-codex/gpt-6.1-sol` |
| `pigl` | `openai-codex/gpt-6-luna` | `openai-codex/gpt-6.1-sol` | `openai-codex/gpt-6.1-sol` |
| `pixg` | `opencode-go/deepseek-v4.1-flash` | `opencode-go/deepseek-v4.1-flash` | `xai/grok-4.7` |
| `pigemf` | `google-vertex/gemini-3.8-flash` | `google-vertex/gemini-3.8-flash` | `google-vertex/gemini-3.8-flash` |
| `pigemp` | `google-vertex/gemini-3.8-flash` | `google-vertex/gemini-3.1-pro-preview` | `google-vertex/gemini-3.1-pro-preview` |
| `pigema` | `google-vertex/gemini-3.8-flash` | `google-vertex/gemini-4-argon` | `google-vertex/gemini-4-argon` |

`piga` の子 Pi は `cheap` / `balanced` が `xhigh`、`max` が `max`。
`pigs` の子 Pi は `cheap` が `max`、`balanced` が `xhigh`、`max` が `max`。
`pigl` の子 Pi は全 tier が `xhigh`。`pixg` の子 Pi は DeepSeek の
`cheap` / `balanced` が `max`、Grok の `max` が `xhigh`。
`pigemf`・`pigemp`・`pigema` は全 tier が `high`。`pigema` は Gemini 4 Argon の単価が高いため、
軽い子タスクの `cheap` だけを Gemini 3.8 Flash にしている。
tier を変更するときは、リポジトリの `.devcontainer/pi-superagents/<launcher>.json` を編集してから次を実行する。`install_beforehand.bash` は既存の設定を保持するため、rebuild だけでは反映されない。

```bash
zsh scripts/setup_pi_superagents.zsh
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

次に、agent-workspace #408 の撤去変更を含むリポジトリのセットアップへ更新してから、下の任意整理に進む。
新しい `scripts/setup_pi_superagents.zsh` は `~/.pi/agent/settings.json` を
作成・変更しない。旧セットアップを残したままエントリだけ削除すると、再実行で追加される。

##### 旧エントリの任意整理

既存の `git/github.com/obra/superpowers/skills` は残してもよい。
v1.14.3 の隔離検証では、自動探索と同じ絶対パスに解決され、探索リストで重複排除された。
整理したい場合だけ `~/.pi/agent/settings.json` の `skills` 配列からこの要素を削除する。
他の skills、`packages`、`theme` などは保持し、設定全体を置き換えない。
自動削除の移行処理は行わない。

##### 検証範囲

[隔離検証 #409](https://github.com/usaturn/agent-workspace/issues/409#issuecomment-5773449902)では、
pi-superagents 1.14.3 / Pi loader 0.85.1 / Superpowers 6.4.1 について、
旧エントリあり・なしと `includeProject` true・false の4条件で、
`using-superpowers`、`brainstorming`、`writing-plans`、
`subagent-driven-development`、`executing-plans` の解決と探索パスの重複排除を確認した。
これは探索 API の検証であり、実 trust 設定の変更や対話 Pi の `/sp-*` 実行確認ではない。

セットアップの設定非変更・ランチャー配置などの回帰テストは、
`bash .devcontainer/run-tests.bash` から実行する。MCP 移行・Vertex の pytest は
`.devcontainer/test-pi-migrations.bash` が uv 経由で実行する。
単独で実行する場合は、リポジトリのルートで次を実行する。

```bash
bash .devcontainer/test-pi-superagents.bash
bash .devcontainer/test-pi-openai-codex.bash
bash .devcontainer/test-pi-migrations.bash
```
