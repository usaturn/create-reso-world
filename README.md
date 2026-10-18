# create-reso-world

[resoloop](https://github.com/orange3134/resoloop) と Blender で Resonite のワールドを作るための開発環境（Dev Container）。
コーディングエージェント（Claude Code、Codex、pi、Cursor、Devin）で作業する前提で、共通の規約とスキルをリポジトリに置いている。
ワールドのプロジェクトはローカルの作業物であり、このリポジトリでは追跡しない（issue #57）。

## 構成

```
.
├── AGENTS.md                  共通規約の正本（CLAUDE.md は @AGENTS.md を読み込む）
├── .agents/skills/            共有スキルの正本（.claude/skills/ はここへの symlink）
├── .devcontainer/             Dev Container の設定、導入スクリプト、テスト（詳細は .devcontainer/README.md）
├── scripts/                   new-world.sh（プロジェクトの作成）、resoloop-fork.sh（fork の運用）、meshy.py（生成・変換）、check-layout.sh（レイアウト検査）
├── templates/world-project/   プロジェクトの雛形
├── docs/                      設計と計画（docs/superpowers/）、fork の運用、統合手順、pi と Claude Code の設定の移植の記録
├── tests/                     スクリプトのテスト（tests/scripts/）とスキルのテスト（tests/skills/）
└── worlds/<name>/             ワールドのプロジェクト（resoloop のプロジェクト。ローカル専用で git の追跡対象外）
```

追跡解除した従来位置の `MyResoniteProject/`・`akichi/`・`slum02/`・`slum03/` もローカルの作業物として使える
（git の追跡対象外）。ただし、別 checkout への追跡解除コミットの取り込みには、次の保全手順が必要である。
`git clean -fdx` は ignore 対象のワールドも削除するので使わない。大きなワールドデータを共有したい場合は、
別のリポジトリを作ってそちらで管理する。

## 追跡解除コミットを取り込む

通常の checkout は、変更の無い追跡ファイルも削除する。変更をコミット・stash してから取り込んでも、
ワールドの実ファイルは残らない。`git rm --cached` だけを先に行うと未追跡ファイルの削除ガードで停止し、
`--no-overwrite-ignore` も追跡中のファイルの削除は防がない。`repo-cleanup-after-merge` が対象領域の
追跡ファイルの削除で停止するのは、この変更を取り込んだ後の版だけである。エージェントは作業ツリーにあるスキルを読むので、
取り込む前の checkout では旧版が動き、clean な checkout の追跡ワールドを削除する。**初回移行を下の手順で終えるまで、
`repo-cleanup-after-merge`・`gitm`（`git checkout origin/main`）・通常の checkout/merge でその checkout を更新しない。**

1. `git fetch origin` 後、対象 checkout の `git status --short` を確認する。従来の4ディレクトリと `worlds/` の
   **5領域**を保全対象とし、領域外の変更は別途保全する。領域内に staged 変更があれば、先にその版を
   ローカルコミットへ保存する。未stageの変更は残したままでよい。
   制作プロセス・エージェントを止め、移行と同時にファイルや Git refs を書き換えない。
2. 以下を **対象 checkout のルートで、同じシェルで** 実行する。5領域のうち存在するディレクトリ全体
   （未コミット変更・未追跡・ignored ファイル・symlink を含む）を、Git の共通ディレクトリ
   （`git rev-parse --git-common-dir`。通常は main checkout の `.git`）の下に作る一意な `local-worlds-backup.*` へ移し、
   `--no-overwrite-ignore` で更新してから戻す。ここは checkout も worktree の削除も触れず、Dev Container の
   checkout の親（`/workspaces`）と違って書き込める。取り込み先に5領域の追跡ファイルが残る場合は実行しない。
   移動は同じファイルシステム内に限り、ファイルの内容・mode・hard link を保つ。履歴から戻せるよう旧 HEAD も保存する。

   ```bash
   set -e
   root="$(git rev-parse --show-toplevel)"
   target="$(git rev-parse 'origin/main^{commit}')"
   dirs=(MyResoniteProject akichi slum02 slum03 worlds)
   remaining="$(git ls-tree -r --name-only "$target" -- "${dirs[@]}")"
   [ -z "$remaining" ] || { printf '%s\n' '取り込み先にワールドの追跡ファイルが残っているため停止する。' >&2; exit 1; }
   git diff --cached --quiet -- "${dirs[@]}" || { printf '%s\n' 'ワールドの staged 版を先にローカルコミットへ保存する。' >&2; exit 1; }
   for name in "${dirs[@]}"; do
       [ ! -L "$root/$name" ] && { [ ! -e "$root/$name" ] || [ -d "$root/$name" ]; } || exit 1
   done
   backup_parent="$(git rev-parse --path-format=absolute --git-common-dir)"
   device="$(stat -c %d "$backup_parent")"
   for name in "${dirs[@]}"; do
       [ ! -d "$root/$name" ] || [ "$(stat -c %d "$root/$name")" = "$device" ] || exit 1
   done
   backup="$(mktemp -d "$backup_parent/local-worlds-backup.XXXXXX")"
   printf '保全先: %s\n' "$backup"
   git rev-parse HEAD > "$backup/before-head"
   for name in "${dirs[@]}"; do
       [ ! -d "$root/$name" ] || mv -T -- "$root/$name" "$backup/$name"
   done
   checkout_status=0
   git checkout --detach --no-overwrite-ignore "$target" || checkout_status=$?
   for name in "${dirs[@]}"; do
       if [ -d "$backup/$name" ]; then
           [ ! -e "$root/$name" ] && [ ! -L "$root/$name" ] || exit 1
           mv -T -- "$backup/$name" "$root/$name"
       fi
   done
   [ "$checkout_status" -eq 0 ] || exit "$checkout_status"
   [ "$(git rev-parse HEAD)" = "$target" ]
   git status --short
   ```

3. ワールドの内容とリンクを確認する。保全先と旧 HEAD の記録は確認が終わるまで残す。
   事前に保存した staged 版は旧 HEAD の履歴から別途取り出せる（管理外に移ったため index の staging は引き継がない）。
   どの段階で失敗しても `--force`・reset・clean・保全先の削除で回避しない。既に移したディレクトリは保全先
   （Git の共通ディレクトリの `local-worlds-backup.*`）に残っている。
   元の場所と保全先を確認し、戻す先が空いているものだけ `mv -T -- <保全先>/<name> <root>/<name>` で戻す。
   取り込み後は通常の `repo-cleanup-after-merge` を使える。

既に通常の checkout で消してしまった場合、取り込み前のコミットのファイルは
`git restore --source=<取り込み前> --worktree -- <dir>` で戻せる。ただし、未コミット・未追跡・ignored ファイルは
履歴では復元できない。先に現在残っているデータを別の場所へ保全し、既存ファイルを上書きしないこと。

## Dev Container を起動する

1. ホスト側に秘密情報の置き場を用意する（任意）。手順は `.devcontainer/README.md` の「秘密情報」にある。
2. VS Code の Dev Containers: Reopen in Container で開く。`initializeCommand` がホスト側に mount のソースを作り、
   `postCreateCommand`（`.devcontainer/install_beforehand.bash`）が各エージェントの CLI、uv、Blender、ResoLoop などを導入する。
   ResoLoop は NuGet の最新の公開版をネットワークから導入し、続けて各プロジェクトの同梱スキルの状態を表示する。
3. 導入を確かめる。

   ```bash
   bash .devcontainer/verify-resonite-tooling.bash
   bash scripts/resoloop-fork.sh status
   ```

コンテナの resoloop から Windows ホストの ResoniteLink に届くことが前提である（WSL2 の mirrored networking など）。
導入するツールの一覧、mount、ResoniteLink への接続は `.devcontainer/README.md` にまとめてある。

## エージェントで作業する

エージェントは、作業するプロジェクト（例: `worlds/slum02/`）を cwd にして起動する。共通の規約はルートの `AGENTS.md`、
プロジェクト固有の規約はプロジェクトの `AGENTS.md` にあり、どちらも読み込まれる。

初回や設定の変更後に、次の点に注意する。

- Codex: プロジェクトを信頼（trust）すると、`.codex/config.toml` の MCP サーバー（`context7_stdio`）が読まれる。初回の起動時に承認する。
  ユーザー設定の `context7` が HTTP 接続でも、stdio 接続の設定と混ざらないよう別名にしている。
  ユーザー側にも `context7` がある場合は、両方が独立したサーバーとして読み込まれる。ユーザー設定は変更しない。
- cursor-agent: `.cursor/mcp.json` の MCP サーバーは、初回に承認を求められる。
- Devin: `.claude/skills` の symlink 経由で同じスキルが見えても、一覧には 1 回だけ表示される（`.devin/config.json` は置かない）。
- Cursor: スキルの一部が見えない。詳細は `.devcontainer/README.md` の「エージェントの読み込みの制約」。
- pi: プロジェクトを信頼（trust）すると、`.pi/settings.json`（組み込み MCP の有効化）と `.pi/mcp.json`（Google Developer Knowledge の
  MCP サーバーと Context7）、`.pi/APPEND_SYSTEM.md`（pi 固有の指示）、プロジェクトのスキル（`.agents/skills`）が読まれる。ワールドはプロジェクト直下の `.pi` symlink（ルートへの相対パスはプロジェクトの深さに応じる）から同じ設定を読む。キーと挙動は `.devcontainer/README.md` の「API トークン」と
  「組み込み MCP と廃止した拡張」にある。
- pi-superagents: 組み込みと同じ定義（`sp-*.md`）は追跡しない。独自に変えた `.agents/sp-implementer.md` だけを追跡する。

## プロジェクトを作る

```bash
bash scripts/new-world.sh <name>            # worlds/<name>/ に resoloop init し、雛形（CLAUDE.md、pyproject.toml、symlink など）を適用する
bash scripts/new-world.sh --apply <name>    # 既存のプロジェクトに、雛形の足りない分だけを適用する
```

プロジェクトは `worlds/` の直下に作られ、git の追跡対象外のローカルの作業物になる。`--apply` は
`worlds/<name>/` と、追跡解除した従来位置（`MyResoniteProject/`・`akichi/`・`slum02/`・`slum03/`）の
プロジェクトの両方に使える。`worlds/` は実ディレクトリである必要がある（symlink にはできない。
プロジェクトからルートへの相対 symlink が symlink 先基準で解決されて届かなくなるため）。

新規作成・`--apply` には `jq` が必要（Dev Container の基本パッケージで導入する）。
プロジェクト直下の `.resoloop/blender-system-python` を実行可能な通常ファイルとして配置し、
`worlds/<name>/.resoloop.json` の `blenderExecutable` が未設定または null なら、
このラッパーの絶対パスを補う。ラッパーは PATH の
`*/.venv/bin` を除き、`VIRTUAL_ENV` を解除して `/usr/bin/blender` を起動するため、`uv run` 経由でも
Blender の Python がシステムの NumPy を使える。

カスタムの `blenderExecutable`（空文字を含む）は保持する。現在のラッパー値が設定済みの場合も JSON を再保存しない。
プロジェクト移動後の古い絶対パスは自動変更しないので、設定ファイルの `blenderExecutable` を
移動先の `.resoloop/blender-system-python` の絶対パスへ手動更新し、`bash scripts/new-world.sh --apply <name>` で
雛形の不足分を補う。

既存のファイルは上書きせず、食い違いがあれば報告して止まる。不正な JSON、ラッパーの内容差や symlink などの
競合があれば、雛形・JSON・実行権限は変更しない（新規作成で既に `resoloop init` が作ったものは残る）。
同じ内容で実行権限だけ無いラッパーは、競合が無い場合だけ実行可能にする。
プロジェクトのテストは、そのディレクトリで `uv run pytest` を実行する。
uv が無い環境では `--no-sync` で雛形だけを適用できるが、その場合は `uv.lock` がまだ無いので、uv を導入して `uv sync` するまで
`scripts/check-layout.sh` が `uv.lock` の欠落を報告する。

### ワールド以外のローカル構成を検査する

`scripts/check-layout.sh` は、作業領域直下の `worlds/<name>/.resoloop.json` を持つプロジェクトを、既定では標準ワールドとして検査する。
Meshy の原本置き場やアイテム用リポジトリなど、意図的に構成が違う場合だけ、リポジトリルートの
.check-layout-projects.json に用途を明示する。このローカル設定は git の追跡対象外。

```json
{
  "worlds/source-assets": "assets",
  "worlds/item-library": "items"
}
```

- `world`（未指定時の既定値）: 標準雛形・共有リンク・同梱スキルを検査する。
- `assets`: 最小の生成素材置き場。通常ファイルの `worlds/<name>/.resoloop.json` だけを要求し、同梱スキルの同期確認は行わない。
- `items`: 共通の雛形・リンク・スキルを検査するが、プロジェクトルートの `worlds/<name>/flux/resoloop.flux.json` の代わりに、実ディレクトリの `items/` を要求する。

どの用途でも、リポジトリ全体の追跡禁止・ignore・mount などの検査は省略しない。ファイルの不足から用途を自動判定することもない。
設定には `jq` が必要。不正な JSON、未知の用途、収集対象に無いパスは失敗として報告する。
キーは `worlds/<英数字で始まる英数字・_-の名前>`、または従来位置の4名だけで、glob・絶対パス・深い階層は指定できない。
設定ファイルは通常ファイルとし、symlink は使わない。`--root DIR` では DIR のリポジトリルートの設定を読む。

移動済みの `.venv` は interpreter が正常でも、`bin/pytest` などのshebangに古い絶対パスが残って起動できない場合がある。
Python の選択の問題と区別し、既存環境の再作成や古い位置への互換リンク追加を行う前に、起動スクリプトのパスを確認する。

## ResoLoop の版

ResoLoop は常に NuGet の最新の公開版（上流 orange3134/resoloop のリリース。今はプレリリースだけ）を使い、版を固定しない。
Dev Container を作るとき（postCreate）に最新を導入する。rebuild せずに最新へ上げるときは、次の 1 行を実行する
（中で `dotnet tool update --global ResoLoop --prerelease --allow-downgrade` を実行し、`resoloop --version` を照合する）。

```bash
bash .devcontainer/install_resoloop.bash
```

最新に追従するので、rebuild や上のコマンドのたびに resoloop の挙動が変わり得る。使っている版は `resoloop --version` で確かめる。
版が上がると、各プロジェクトの同梱スキル（`resonite-*`）にも更新が出る。postCreate と `scripts/check-layout.sh` は更新の有無を
表示するだけなので、`resoloop skills sync --check` で差分を見てから `--update` する（`AGENTS.md` の「プロジェクト運用」）。

上流に未取り込みの修正を一時的に使うときは、`bash scripts/resoloop-fork.sh install <fork のブランチ>` で fork（usaturn/resoloop）の
ビルドを導入する。次の rebuild か、上の 1 行で最新の公開版に戻る。fork の checkout は `external/resoloop`（git の追跡対象外）に置く。
fork の使い方と上流への PR の流れは `docs/resoloop-fork-workflow.md` にある。

## Meshy から小物を取り込む

公式 `meshy-cli` と `scripts/meshy.py` で text / local image から生成し、Blender の編集用データと ResoLoop bundle を作る。
有機的・曖昧な形や画像参考には Meshy、寸法・機械構造・厳密な低ポリ再現には Blender を使う。
postCreate は Meshy CLI の導入と無認証の version / help 確認だけを行い、API・課金・ワールド適用は行わない。

- 手順と全 CLI 例: [docs/meshy-resoloop.md](docs/meshy-resoloop.md)。キーは利用者が zsh で非表示入力し、環境変数だけで渡す。キー / env ファイルは作らない。
- 共有スキル: [.agents/skills/meshy-resoloop/SKILL.md](.agents/skills/meshy-resoloop/SKILL.md)（root の `.claude/skills` からも同じ実体）。
  新規・既存プロジェクトとも祖先のスキルを使う。見えないエージェントにはこの repository-relative パスを明示し、本文コピーや設定変更はしない。
- 対象・件数・予算・条件を承認してから `plan` → `submit` → `wait` → `download` → `convert`。
  text preview と refine は別 operation・計2件の課金操作。応答不明の送信は再送せず、journal と `list` / `attach` で復旧する。
- convert は culling 保持不可を既定で拒否する。`--allow-culling-change` はその損失だけの明示許可で、他の非対応素材を許可しない。
- Windows へ bundle 一式を渡し、確認済み URL / parent と共有 state 一つで `diff` → 承認 → `apply` → 再適用 / `test`。自動 live 操作はしない。

実 API・課金生成、標準 rebuild、Windows の texture 表示・無変更収束は **未検証**。実機受入 checklist は上記手順にある。PR は `Refs #50`（自動 close なし）。

## 変更の流れ

- 変更は作業ブランチで行い、`main` へは PR で入れる。並行作業には `.worktrees/` 配下の worktree を使う（git の追跡対象外）。
- PR を出す前に、下の「テスト」をすべて通す。CI（`.github/workflows/ci.yml`）も push と PR のたびに同じ検査を行う。
- 設計と実装計画は、対象のリポジトリにかかわらず `docs/superpowers/` に置く。運用は `docs/superpowers/README.md` にある。ローカルの下書きは `docs_draft/`（git の追跡対象外）に置く。

## テスト

```bash
bash .devcontainer/run-tests.bash                                # Dev Container とスクリプトのテスト
bash scripts/check-layout.sh                                     # リポジトリのレイアウトとローカルプロジェクトの雛形
uv run pytest tests/skills .agents/skills .agents/scripts tools  # スキル・.agents/scripts・tools（agent_runner など）のテスト
(cd worlds/<name> && uv run pytest)                              # 各ローカルプロジェクトのテスト（追跡対象外なので CI では実行しない）
```

## 対象外

リポジトリの公開と LICENSE の選定、Git LFS、flux-sdk の導入、Rebuild を伴う確認の自動化は対象外である。
Rebuild 後の確認は、ユーザが `docs/integration.md` の手順で行う。pi と Claude Code の設定の移植（Issue #17）で確かめる項目と
記録は、`docs/` にある移植の比較表（Issue #22）の「rebuild での確認」にある。
