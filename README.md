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

追跡解除した従来位置の `MyResoniteProject/`・`akichi/`・`slum02/`・`slum03/` もローカルの作業物としてそのまま残る
（git の追跡対象外）。これらの checkout で追跡解除のコミットを取り込むときは、先にローカルの変更をコミットするか
別の場所へ退避してから取り込むこと（追跡ファイルは checkout で消え得るため）。`git clean -fdx` は ignore 対象の
ワールドも削除するので注意する。大きなワールドデータを共有したい場合は、別のリポジトリを作ってそちらで管理する。

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
  MCP サーバー）、`.pi/APPEND_SYSTEM.md`（pi 固有の指示）、プロジェクトのスキル（`.agents/skills`）が読まれる。ワールドは `.pi -> ../.pi` から同じ設定を読む。キーと挙動は `.devcontainer/README.md` の「API トークン」と
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

既存のファイルは上書きせず、食い違いがあれば報告して止まる。プロジェクトのテストは、そのディレクトリで `uv run pytest` を実行する。

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
bash .devcontainer/run-tests.bash          # Dev Container とスクリプトのテスト
bash scripts/check-layout.sh               # リポジトリのレイアウトとローカルプロジェクトの雛形
uv run pytest tests/skills .agents/skills  # スキルのテスト
(cd worlds/<name> && uv run pytest)        # 各ローカルプロジェクトのテスト（追跡対象外なので CI では実行しない）
```

## 対象外

リポジトリの公開と LICENSE の選定、Git LFS、flux-sdk の導入、Rebuild を伴う確認の自動化は対象外である。
Rebuild 後の確認は、ユーザが `docs/integration.md` の手順で行う。pi と Claude Code の設定の移植（Issue #17）で確かめる項目と
記録は、`docs/` にある移植の比較表（Issue #22）の「rebuild での確認」にある。
