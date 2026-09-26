# create-reso-world

[resoloop](https://github.com/orange3134/resoloop) と Blender で Resonite のワールドを作るための開発環境（Dev Container）と、
ワールドのプロジェクトをまとめたリポジトリ。コーディングエージェント（Claude Code、Codex、pi、Cursor、Devin、dsh）で
作業する前提で、共通の規約とスキルをリポジトリに置いている。

## 構成

```
.
├── AGENTS.md                  共通規約の正本（CLAUDE.md は @AGENTS.md を読み込む）
├── .agents/skills/            共有スキルの正本（.claude/skills/ はここへの symlink）
├── .devcontainer/             Dev Container の設定、導入スクリプト、テスト（詳細は .devcontainer/README.md）
├── scripts/                   new-world.sh（プロジェクトの作成）、resoloop-fork.sh（fork の運用）、check-layout.sh（レイアウト検査）
├── templates/world-project/   プロジェクトの雛形
├── docs/                      設計と計画（docs/superpowers/）、fork の運用、統合手順
├── tests/                     スクリプトのテスト（tests/scripts/）とスキルのテスト（tests/skills/）
└── MyResoniteProject/ akichi/ slum02/   ワールドのプロジェクト（resoloop のプロジェクト）
```

## Dev Container を起動する

1. ホスト側に秘密情報の置き場を用意する（任意）。手順は `.devcontainer/README.md` の「秘密情報」にある。
2. VS Code の Dev Containers: Reopen in Container で開く。`initializeCommand` がホスト側に mount のソースを作り、
   `postCreateCommand`（`.devcontainer/install_beforehand.bash`）が各エージェントの CLI、uv、Blender、ResoLoop などを導入する。
   ResoLoop は `.devcontainer/resoloop.lock` が指定する fork をビルドするため、ネットワークと数分の時間を要する。
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

初回や設定の変更後に、次の操作が要る。

- Codex: プロジェクトを信頼（trust）すると、`.codex/config.toml` の MCP の設定（context7）が読まれる。初回の起動時に承認する。
- cursor-agent: `.cursor/mcp.json` の MCP サーバーは、初回に承認を求められる。
- Devin: `.claude/skills` の symlink 経由で同じスキルが見えても、一覧には 1 回だけ表示される（`.devin/config.json` は置かない）。
- Cursor と dsh: スキルの一部が見えない。詳細は `.devcontainer/README.md` の「エージェントの読み込みの制約」。
- pi-superagents: 組み込みと同じ定義（`sp-*.md`）は追跡しない。独自に変えた `.agents/sp-implementer.md` だけを追跡する。

## プロジェクトを作る

```bash
bash scripts/new-world.sh <name>            # resoloop init の後に雛形（CLAUDE.md、pyproject.toml、symlink など）を適用する
bash scripts/new-world.sh --apply <name>    # 既存のプロジェクトに、雛形の足りない分だけを適用する
```

既存のファイルは上書きせず、食い違いがあれば報告して止まる。プロジェクトのテストは、そのディレクトリで `uv run pytest` を実行する。

## ResoLoop の版

導入する ResoLoop の版は `.devcontainer/resoloop.lock` で決める。既定は fork モードで、Blender 5 の UV の修正を含む
fork（usaturn/resoloop）をビルドして導入する。上流（orange3134/resoloop）がリリースしたら nuget モードに戻す。
fork の checkout は `external/resoloop`（git の追跡対象外）に置く。版の変え方、fork の修正と上流への PR の流れは
`docs/resoloop-fork-workflow.md` にある。

## 変更の流れ

- 変更は作業ブランチで行い、`main` へは PR で入れる。並行作業には `.worktrees/` 配下の worktree を使う（git の追跡対象外）。
- PR を出す前に、下の「テスト」をすべて通す。CI（`.github/workflows/ci.yml`）も push と PR のたびに同じ検査を行う。
- 設計と実装計画は `docs/superpowers/` に置く。ローカルの下書きは `docs_draft/`（git の追跡対象外）に置く。

## テスト

```bash
bash .devcontainer/run-tests.bash          # Dev Container とスクリプトのテスト
bash scripts/check-layout.sh               # リポジトリのレイアウト
uv run pytest tests/skills .agents/skills  # スキルのテスト
(cd slum02 && uv run pytest)               # 各プロジェクトのテスト
```

## 対象外

リポジトリの公開と LICENSE の選定、Git LFS、flux-sdk の導入、Rebuild を伴う確認の自動化は対象外である。
Rebuild 後の確認は、ユーザが `docs/integration.md` の手順で行う。
