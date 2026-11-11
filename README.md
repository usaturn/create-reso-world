# create-reso-world

Resonite 向けのワールド・ツールの作成、Blender などを使ったモデルの作成、VR 環境に関するツールやモデルの開発のための開発環境（Dev Container）。
どれも基本的に Resonite が関与する（例: Resonite 側からツールやモデルを取り込んで変換する）。主に [resoloop](https://github.com/orange3134/resoloop) と Blender を使う。
コーディングエージェント（Claude Code、Codex、pi、Cursor、Devin）で作業する前提で、共通の規約とスキルをリポジトリに置いている。
ワールドのプロジェクトはローカルの作業物であり、このリポジトリでは追跡しない（issue #57）。
新しく開発を始めるときは、[docs/new-development.md](docs/new-development.md) から開発の種類ごとの手順に進む。

## 構成

```
.
├── AGENTS.md                  共通規約（CLAUDE.md は @AGENTS.md を読み込む）
├── .agents/                   共有スキル（skills/。.claude/skills/ はここへの symlink）、補助スクリプト（scripts/）、監視・実行予算・レビューの手引き
├── .pi/                       pi の設定（プロジェクトを trust すると読まれる。下の「エージェントで作業する」）
├── .devcontainer/             Dev Container の設定、導入スクリプト、テスト（詳細は .devcontainer/README.md）
├── .github/workflows/ci.yml   CI の定義（GitHub Actions を無効にしているので動かない。下の「変更の流れ」）
├── scripts/                   new-world.sh（プロジェクトの作成）、resoloop-fork.sh（fork の運用）、meshy.py（生成・変換）、check-layout.sh（レイアウト検査）
│                              resoloop-meshy.sh（Meshy プラグインの checkout）、scan-before-push.sh（push の前の秘密情報の検査）、
│                              superpowers-review-copy.sh（Spec・Plan の確認用コピー）、setup_pi*.zsh（pi の設定）
├── tools/                     external_tools（登録済み外部ツールの共通 resolver・取得 CLI）、agent_runner（別のエージェントの非対話の起動と結果の回収）、
│                              devenv_migration（pi の設定の移行のテスト）、test_support（共有のテストの fixture）、
│                              review_eval（レビュー記録の私有の保存先への収集。既定は無効。tools/review_eval/README.rst）
├── external-tools.toml        通常ツールの登録候補（運用には常設親への採用が必要）
├── templates/world-project/   プロジェクトの雛形
├── docs/                      新規開発の入口（new-development.md）、設計と計画（superpowers/）、fork・Meshy プラグイン・外部ツールの運用、
│                              Meshy の素材、AR 広告と agent-runner の手引き、統合手順、ワールドの記録（worlds/）、設定の移植の記録
├── tests/                     スクリプトのテスト（tests/scripts/）、スキルのテスト（tests/skills/）、テストの fixture（tests/fixtures/）
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
   bash .devcontainer/verify-ca-trust.bash
   ```

   `verify-ca-trust.bash` は、侵害された eMudhra の中間CA を各クライアントが信頼していないかを、外部の確認用ホストへの接続で確かめる（Issue #291）。
   判定の読み方と、ホスト側（Windows・WSL2・ブラウザ・Electron のアプリ）の更新は、`.devcontainer/README.md` の
   「トラストストアの確認（eMudhra 中間CA の侵害）」にある。

コンテナの resoloop から Windows ホストの ResoniteLink に届くことが前提である（WSL2 の mirrored networking など）。
導入するツールの一覧、mount、ResoniteLink への接続は `.devcontainer/README.md` にまとめてある。

## エージェントで作業する

エージェントは、作業するプロジェクト（例: `worlds/slum02/`）を cwd にして起動する。共通の規約はルートの `AGENTS.md`、
プロジェクト固有の規約はプロジェクトの `AGENTS.md` にあり、どちらも読み込まれる。

初回や設定の変更後に、次の点に注意する。

- Context7: どのエージェントも MCP ではなく、`find-docs` スキルから Context7 CLI（`ctx7`。postCreate が npm の最新版を入れる）を使う。
  導入・更新・認証と、リポジトリの外に残る Context7 の設定の扱いは `.devcontainer/README.md` の「Context7 CLI（ctx7）」にある。
- Devin: `.claude/skills` の symlink 経由で同じスキルが見えても、一覧には 1 回だけ表示される（`.devin/config.json` は置かない）。
- Cursor: スキルの一部が見えない。詳細は `.devcontainer/README.md` の「エージェントの読み込みの制約」。
- pi: プロジェクトを信頼（trust）すると、`.pi/settings.json`（組み込み MCP の有効化と、共有の `~/.pi` にある Context7 拡張の読み込みの停止）と
  `.pi/mcp.json`（Google Developer Knowledge の MCP サーバー）、`.pi/APPEND_SYSTEM.md`（pi 固有の指示）、プロジェクトのスキル（`.agents/skills`）が読まれる。ワールドはプロジェクト直下の `.pi` symlink（ルートへの相対パスはプロジェクトの深さに応じる）から同じ設定を読む。キーと挙動は `.devcontainer/README.md` の「API トークン」と
  「組み込み MCP と廃止した拡張」にある。
- pi-superagents: 組み込みと同じ定義（`sp-*.md`）は追跡しない。独自に変えた `.agents/sp-implementer.md` だけを追跡する。
- issue-to-pr: 設計レビューと Spec レビューは、`--design-review AGENT` / `--spec-review AGENT` を明示した run だけで行う。無指定では起動しない。Plan の実装の既定は `self`（#391）で司令塔が自分で実行し、`--implement AGENT` か個人設定で担当を選び直せる。レビュー修正（`fix.implement`）の既定も `self`（main の #377）で司令塔が自分で実行する。個人設定に旧名 `claude-code_sonnet_default` があれば手動で置き換える（#353）。詳細は `.devcontainer/README.md` の「Spec・設計レビューの opt-in と既定担当（#353）」にある。

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

ProtoFlux 用の flux-sdk も postCreate で導入するが、ResoLoop と違って、ResoLoop が検証している版に固定する
（`.devcontainer/install_flux_sdk.bash`。版と確認方法は `.devcontainer/README.md` の「ProtoFlux 用の flux-sdk」）。

上流に未取り込みの修正を一時的に使うときは、`bash scripts/resoloop-fork.sh install <fork のブランチ>` で fork（usaturn/resoloop）の
ビルドを導入する。次の rebuild か、上の 1 行で最新の公開版に戻る。fork の checkout は `external/resoloop`（git の追跡対象外）に置く。
fork の使い方と上流への PR の流れは `docs/resoloop-fork-workflow.md` にある。

## 登録済み外部ツール

通常ツールは `external-tools.toml` と共通 CLI で管理する。登録の採用・取得・repo 自身の規約での検証・CI の実設定照合・
手動マージ・失敗 staging の扱いは [docs/external-tools-workflow.md](docs/external-tools-workflow.md) にある。
通常のツール追加は台帳と対象 repo の `AGENTS.md` / `README.md` で行い、個別の取得スクリプトやスキル内の一覧は増やさない。

共通機構を含む source checkout での読取例:

```bash
uv run --no-project python -m tools.external_tools list
uv run --no-project python -m tools.external_tools show emission-editor
uv run --no-project python -m tools.external_tools check emission-editor
```

運用に使うのは常設親の detached HEAD に採用された blob だけ。**この branch に候補があるだけでは採用済みではない。**
親への採用前は不在・未採用として停止する。check の成功もローカル identity の確認だけで、GitHub 作成・公開・CI 設定・
実機準備の完了を示さない。登録自体は clone・実装・公開等の実行許可ではなく、通常ツールのマージは手動で行う。

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
- PR を出す前に、下の「テスト」をすべて通す。このリポジトリは公開しているが GitHub Actions を無効にしているので、CI（`.github/workflows/ci.yml`）は動かず、ローカルの実行だけが検査になる（`AGENTS.md` の「GitHub Actions」）。
- push の前に `scripts/scan-before-push.sh` で秘密情報を検査する（`AGENTS.md` の「push の前の秘密情報の検査」）。
- 設計と実装計画（Spec・Plan）の置き場所は `AGENTS.md` の「Spec・Plan の保存と公開」に、運用は `docs/superpowers/README.md` にある。ローカルの下書きは `docs_draft/`（git の追跡対象外）に置く。

## テスト

```bash
bash .devcontainer/run-tests.bash                                # Dev Container とスクリプトのテスト
bash scripts/check-layout.sh                                     # リポジトリのレイアウトとローカルプロジェクトの雛形
uv run pytest tests/skills .agents/skills .agents/scripts tools  # スキル・.agents/scripts・tools（agent_runner など）のテスト
(cd worlds/<name> && uv run pytest)                              # 各ローカルプロジェクトのテスト（追跡対象外なので CI では実行しない）
```

## 対象外

LICENSE の選定、Git LFS、Rebuild を伴う確認の自動化は対象外である。リポジトリは公開済みだが、LICENSE はまだ選んでいない。
Rebuild 後の確認は、ユーザが `docs/integration.md` の手順で行う。pi と Claude Code の設定の移植（Issue #17）で確かめる項目と
記録は、`docs/` にある移植の比較表（Issue #22）の「rebuild での確認」にある。
