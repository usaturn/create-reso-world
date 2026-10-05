# create-reso-world

[resoloop](https://github.com/orange3134/resoloop) と Blender で Resonite のワールドを作るための開発環境（Dev Container）と、
ワールドのプロジェクトをまとめたリポジトリ。コーディングエージェント（Claude Code、Codex、pi、Cursor、Devin）で
作業する前提で、共通の規約とスキルをリポジトリに置いている。

## 構成

```
.
├── AGENTS.md                  共通規約の正本（CLAUDE.md は @AGENTS.md を読み込む）
├── .agents/skills/            共有スキルの正本（.claude/skills/ はここへの symlink）
├── .devcontainer/             Dev Container の設定、導入スクリプト、テスト（詳細は .devcontainer/README.md）
├── scripts/                   new-world.sh（プロジェクトの作成）、resoloop-fork.sh（fork の運用）、check-layout.sh（レイアウト検査）
├── templates/world-project/   プロジェクトの雛形
├── docs/                      設計と計画（docs/superpowers/）、fork の運用、統合手順、pi と Claude Code の設定の移植の記録
├── tests/                     スクリプトのテスト（tests/scripts/）とスキルのテスト（tests/skills/）
└── MyResoniteProject/ akichi/ slum02/   ワールドのプロジェクト（resoloop のプロジェクト）
```

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

エージェントは、作業するプロジェクト（例: `slum02/`）を cwd にして起動する。共通の規約はルートの `AGENTS.md`、
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
bash scripts/new-world.sh <name>            # resoloop init の後に雛形（CLAUDE.md、pyproject.toml、symlink など）を適用する
bash scripts/new-world.sh --apply <name>    # 既存のプロジェクトに、雛形の足りない分だけを適用する
```

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

## 変更の流れ

- 変更は作業ブランチで行い、`main` へは PR で入れる。並行作業には `.worktrees/` 配下の worktree を使う（git の追跡対象外）。
- PR を出す前に、下の「テスト」をすべて通す。CI（`.github/workflows/ci.yml`）も push と PR のたびに同じ検査を行う。
- 設計と実装計画は、対象のリポジトリにかかわらず `docs/superpowers/` に置く。運用は `docs/superpowers/README.md` にある。ローカルの下書きは `docs_draft/`（git の追跡対象外）に置く。

## テスト

```bash
bash .devcontainer/run-tests.bash          # Dev Container とスクリプトのテスト
bash scripts/check-layout.sh               # リポジトリのレイアウト
uv run pytest tests/skills .agents/skills  # スキルのテスト
(cd slum02 && uv run pytest)               # 各プロジェクトのテスト
```

## 対象外

リポジトリの公開と LICENSE の選定、Git LFS、flux-sdk の導入、Rebuild を伴う確認の自動化は対象外である。
Rebuild 後の確認は、ユーザが `docs/integration.md` の手順で行う。pi と Claude Code の設定の移植（Issue #17）で確かめる項目と
記録は、`docs/` にある移植の比較表（Issue #22）の「rebuild での確認」にある。
