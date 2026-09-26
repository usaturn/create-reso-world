# create-reso-world 環境再設計 設計仕様

作成日: 2026-09-26
対象リポジトリ: `/workspaces/reso-world`（push 先 https://github.com/usaturn/create-reso-world）
関連: `docs/superpowers/specs/2026-09-24-resonite-devcontainer-tooling-design.md`（ResoLoop の版方針は本仕様が置き換える）

## 1. 背景と目的

このリポジトリは、Dev Container 上で resoloop と Blender を使い Resonite のワールドを作る開発環境であり、複数のコーディングエージェント（Claude Code、Codex、pi、Cursor、Devin、dsh）の設定を同居させている。resoloop のプロジェクト（`MyResoniteProject/`、`akichi/`、`slum02/`）はリポジトリ直下に置き、エージェントはそのプロジェクトディレクトリを cwd にして起動する運用が望ましい。

2026-09-26 の調査（6 系統の読み取り調査と批評）で、次の構造的な不具合が確認された。

- Claude Code をプロジェクト cwd で起動すると、ルート `CLAUDE.md` の存在によりプロジェクトの `AGENTS.md`（resoloop の安全ルール）が読まれない。
- スキルの探索範囲がエージェントごとに異なり、ルート `.claude/skills` は `MyResoniteProject/.agents/skills` への未追跡 symlink で成り立っている。同名スキルが `.agents` / `.claude` / `.devin` に別内容で存在し、0 バイトのヘルパースクリプトも追跡されている。
- pi の `.pi/APPEND_SYSTEM.md` と Claude Code の `.claude/settings.json` は cwd 直下しか読まれず、プロジェクト cwd では無効。
- resoloop の fork ビルド（Blender 5 UV 修正入り）は手作業で導入されており、コンテナ再作成で公開版に戻る。fork の global.json が要求する SDK 10.0.201 がコンテナに無い。
- 移行元リポジトリ（maatlog）由来の設定・スキル・スクリプト・文書が多数残り、pr-review 系スキルは resoloop の PR を扱えない。
- push 前の危険物: TRPG ルールブック本文 3 ファイルが未追跡かつ非 ignore、`.claude/settings.local.json` が追跡済み、`devcontainer-lock.json` が ignore、README と LICENSE が無い。`.gitignore` は別プロジェクトのテンプレのまま。
- 3 プロジェクトで resoloop 生成物の追跡状況と `AGENTS.md` の文面が揃っていない。

本仕様は、これらを「プロジェクトを cwd にしてエージェントを起動する」前提で解消し、usaturn/create-reso-world へ push できる状態にするための設計を定める。

## 2. 決定事項（ユーザ承認済み）

| 項目 | 決定 |
| --- | --- |
| リポジトリの範囲 | モノレポ。環境定義と 3 つのワールドプロジェクトを同一リポジトリで追跡する |
| 公開範囲と履歴 | 当面 private。履歴はそのまま push し、author メールは書き換えない。LICENSE は今回追加しない |
| 対象エージェント | Claude Code、Codex、pi、Cursor、Devin、dsh をすべて対象にする。grok、gcloud、glab、bun は未導入だが参照を残し、未導入でも壊れないようにする |
| ワークフロー系スキル | pr-review、review-fix-planning、repo-cleanup-after-merge、simplify-in-subagent、pi-model-name、planning-parallel-issues、rst-writer、find-docs をこのリポジトリ向けに書き直して残す。repository-ownership は削除する |
| 実現方針 | 正本の一元化とプロジェクト雛形（ルート `.agents/skills` を唯一の正本、ルート `AGENTS.md` を共通規約の正本） |
| pi のペルソナ | リポジトリの `.pi/APPEND_SYSTEM.md` に残し、各プロジェクトから `.pi -> ../.pi` の symlink で参照する |
| ResoLoop の版 | ロックファイルで管理し、既定は fork モード（現在導入済みのビルドを固定） |
| 秘密情報 | `~/.config/create-reso-world` を mount に追加し、zshrc が `env` を存在時だけ読み込む |
| 作業場所 | worktree `/.worktrees/repo-redesign`、ブランチ `chore/repo-redesign`。作業ツリー（別セッションが slum02 を編集中）には触れない |
| フェーズ 0 | `main` を feat/slum02-slum の HEAD に fast-forward してから分岐扱いにする。tokyo-nova の未コミット 12 ファイルは作業ツリーに触れずに `wip/tokyo-nova-refinement` へ退避コミットして push する |

## 3. 対象外

- リポジトリの公開化、LICENSE の選定、author メールの書き換え
- ローカルディレクトリ名 `/workspaces/reso-world` の変更（pi と Claude Code の trust がパスに紐づくため別作業）
- `tmp/` にある resoloop の旧 checkout 3 件と blender-skills ステージングの削除（手順を文書化するにとどめる）
- `MyResoniteProject/.resoloop/tokyo-nova/`（約 589 MB）と `content/tokyo-nova/city/export-static`・`export-refinement`（約 209 MB）の削除。ignore で追跡を防ぐだけにし、要否はユーザが判断する
- flux-sdk の導入（README で対象外と明記）
- resoloop 上流への PR 作成（候補は文書に記録する）
- Git LFS の導入（clone サイズが問題になった時点で再検討）
- コンテナの Rebuild による実機確認（コンテナ内からは実行できないため、統合手順書に従いユーザが実施する）

## 4. リポジトリ構成

### 4.1 ルート

```
/workspaces/reso-world
├── AGENTS.md                        共通規約の正本（ツール非依存・日本語）
├── CLAUDE.md                        `@AGENTS.md` と Claude Code 固有の注記だけ
├── README.md                        新規: 目的、Dev Container 起動、プロジェクト作成、ResoLoop 版管理、fork/PR 手順
├── .gitignore                       本リポジトリ専用に全面改訂（4.4）
├── pyproject.toml                   最小構成: pytest と pyyaml の dev 依存のみ。workspace 定義は持たない
├── .agents/
│   ├── skills/<name>/               共有スキルの唯一の正本（ワークフロー系＋Blender 系）
│   └── monitoring-runtimes.md
├── .claude/
│   ├── settings.json                共有設定（ルート起動時に有効。プロジェクトへは symlink で配布）
│   ├── skills/<name> -> ../../.agents/skills/<name>     追跡する相対 symlink
│   └── settings.local.json          追跡解除して ignore
├── .devin/                          skills/ は撤去（Devin は .agents/skills を直接読む）。必要なら config.json のみ
├── .cursor/rules/shell-env-hygiene.mdc   repository-ownership.mdc は削除
├── .cursor/mcp.json                 context7
├── .codex/config.toml               context7（`[mcp_servers.context7]`）
├── .pi/APPEND_SYSTEM.md             pi 固有の規約とペルソナ
├── .mcp.json                        Claude Code 用（現状維持）
├── .pi-lens.json                    `$schema` を外し、生成物ディレクトリを ignore に追加
├── .devcontainer/                   5 章のとおり整合。resoloop.lock を追加
├── scripts/
│   ├── new-world.sh                 `resoloop init` と雛形の適用（4.3）
│   ├── resoloop-fork.sh             fork の取得・ビルド・導入（6 章）
│   └── check-layout.sh              レイアウト検査（8 章）
├── templates/world-project/         プロジェクト雛形
├── docs/                            追跡する文書（superpowers の spec/plan、resoloop-fork-workflow.md、integration.md）
├── docs_draft/                      ignore。ローカル下書き専用
├── external/                        ignore。resoloop fork の checkout
├── private/                         ignore。TRPG 本文などローカル資料
├── tmp/, reviews/, .worktrees/      ignore
├── .github/workflows/ci.yml         8 章の CI
└── MyResoniteProject/ akichi/ slum02/   4.2 の標準レイアウト
```

`tools/` と、呼び出し元の無い `scripts/add_pi_skills_setting.py`・`poke_claude_onboarding.py`・`unpoke_claude_onboarding.py` は削除する。pi 用の `scripts/setup_pi*.zsh` と `setup_pi_tool_display.py` は Dev Container 構築専用なので `.devcontainer/` に移す。

### 4.2 プロジェクトの標準レイアウト

```
<project>/
├── AGENTS.md                        resoloop 生成（preview.14 文面に統一）＋末尾に「## このプロジェクト固有」節
├── CLAUDE.md                        `@AGENTS.md` の 1 行
├── .agents/skills/resonite-*        resoloop 同梱スキル（追跡）
├── .agents/skills/.resoloop-bundled.json   同梱スキルのロック（追跡）
├── .claude/skills/<name> -> ../../.agents/skills/<name>   `.agents/skills` の各ディレクトリと 1:1（追跡 symlink）
├── .claude/settings.json -> ../../.claude/settings.json   追跡 symlink
├── .pi -> ../.pi                    追跡 symlink
├── .resoloop.json                   追跡
├── .resoloop/.gitignore             `state/` `flux-state/` `cache/`（追跡）。それ以外の .resoloop 配下は ignore
├── flux/                            resoloop 生成（追跡。build/ .protograph/ *.brson は flux/.gitignore で除外）
├── content/ modeling/ tests/ artifacts/ assets/
├── pyproject.toml, uv.lock          3 プロジェクト同型（MyResoniteProject にも追加）
└── tmp/, .venv/, .uv-cache/, .pytest_cache/, .ruff_cache/   ignore
```

「このプロジェクト固有」節には、テスト実行コマンド（`uv run pytest`）、ワールド名と ownership、state ファイルの位置を書く。resoloop は既存の `AGENTS.md` を上書きしないため、resoloop の版が上がって文面が変わった場合は手動で先頭部分を差し替える。

Blender 系スキル（arjun988/blender-skills 派生の 10 スキルと references）は `MyResoniteProject` と `akichi` のコピーをやめ、ルート `.agents/skills` に 1 部だけ置く。共有の `references/`（LICENSE、出所記録、設計メモ 3 件）は 7 本の SKILL.md が `../references/` で参照しているため `.agents/skills/references/` のまま残し、ルート `.claude/skills/references` の symlink も維持する（SKILL.md を持たないディレクトリは各エージェントのスキル探索で無視される）。`tests/test_skill_packages.py` はルート `tests/skills/` へ移し、パス定数を新しい位置に合わせる。

`MyResoniteProject/.agents/sp-*.md`（pi-superagents のエージェント定義、未追跡）は cwd 直下の `.agents/*.md` からしか読まれない。ルート `.agents/` に移して追跡し、各プロジェクトの `.agents/<name>.md -> ../../.agents/<name>.md` symlink を雛形に含める。

### 4.3 雛形と作成スクリプト

`templates/world-project/` には次を置く。

- `CLAUDE.md`（`@AGENTS.md`）
- `pyproject.toml`（`{{name}}` を置換）
- `AGENTS.local.md`（「このプロジェクト固有」節のひな形）
- `resoloop-gitignore`（`.resoloop/.gitignore` の内容）

`scripts/new-world.sh <name>` は次を行う。

1. 名前の検証（英数字・ハイフン・アンダースコア）と、既存ディレクトリの有無で `init` か `apply` かを判定する。`--apply` で既存プロジェクトにも適用できる。
2. 新規なら `resoloop init <name>` を実行する。
3. `CLAUDE.md`、`pyproject.toml`、`AGENTS.md` の固有節、`.resoloop/.gitignore` の `cache/` を、無いものだけ作成・追記する。
4. `.claude/skills/<name>`、`.claude/settings.json`、`.pi`、`.agents/sp-*.md` の symlink を作る。`.claude/skills` は `.agents/skills` の実ディレクトリと 1:1 になるよう不足分を追加し、行き先の無いリンクを報告する。
5. `uv sync` を実行し、`resoloop skills sync --check` の結果を表示する。
6. 冪等であること。既存ファイルは上書きせず、差分があれば報告して終了コード非 0 で止まる。

既存 3 プロジェクトには `--apply` で同じ手順を適用し、`AGENTS.md` の先頭部分は preview.14 の文面（slum02 と同じ）に手動で揃える。

### 4.4 `.gitignore` と追跡方針

ルート `.gitignore` は次の項目だけで構成し、テンプレ由来の広いパターン（`images/`、`lib/`、`build/`、`dist/`、`site/`、`util/`、`Output/`、`*.pdf`、`*.zip`、`*.mp3`、`*.spec`、`*.manifest`、`trpg_*` など）は削除する。

- Python と uv: `__pycache__/`、`*.py[cod]`、`.venv/`、`.uv-cache/`、`.pytest_cache/`、`.ruff_cache/`、`.coverage`、`.coverage.*`
- Blender: `*.blend1`、`*.blend2`、`*.blend@`
- 編集の残骸: `*.orig`、`*.rej`、`*.bak`、`*.log`
- resoloop: `**/.resoloop/**` と `!**/.resoloop/.gitignore`（state、flux-state、cache、作業物をすべて除外）、`**/flux/build/`、`**/flux/.protograph/`、`*.brson`
- ローカル専用ディレクトリ: `tmp/`、`docs_draft/`、`/reviews/`、`/external/`、`/private/`、`/.worktrees/`、`/.claude/worktrees/`、`/.superpowers/`、`/.restructure-backup/`、`/MyResoniteProject/content/tokyo-nova/city/export-static/`、`/MyResoniteProject/content/tokyo-nova/city/export-refinement/`
- 個人設定: `**/.claude/settings.local.json`、`**/.devin/mcp_config.local.json`、`.env`、`.env.*`、`.secrets/`
- Node（npx などが作る）: `node_modules/`

途中に `/` を含むパターンはリポジトリルート基準で固定されるため、`slum02/` や `akichi/` などプロジェクト配下にも届かせるには `**/` を前置している。末尾だけに `/` がある `tmp/` と `docs_draft/` は、どの階層のディレクトリにも一致するので 1 行で足りる（フェーズ 6 で実際の `.gitignore` に表記を揃えた）。

`devcontainer-lock.json` は追跡に戻す。`.claude/settings.local.json` は `git rm --cached` で追跡を外す。`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json`（セッション記録）は `tests/tokyo_nova/test_task1_fix_regressions.py` が証跡ファイルとして参照しており、tokyo-nova の進行中作業と競合するため今回は移動しない。追跡済みのまま `**/.resoloop/**` の ignore 規則の既知の例外として `scripts/check-layout.sh` の許可リストに載せ、tokyo-nova 側の作業で `artifacts/` へ移す候補として記録する。`MyResoniteProject/docs_draft/` の強制追加済み 2 件は `docs/worlds/tokyo-nova/` へ移す。`slum02/.gitignore` はルートに吸収して削除する。

TRPG 本文（`MyResoniteProject/ATS.txt`、`BTD.txt`、`TNX.txt`）は `private/trpg/` へ移す。`tokyo_nova_resoloop_world_prompt.md` は添付ファイル名に触れるだけで本文の記述は変更しない。`tmp/` の同一コピーは触らない。

## 5. 指示ファイルとスキルの配置

### 5.1 エージェント別の到達性（プロジェクト cwd 起動時）

| エージェント | 共通規約 | プロジェクト AGENTS.md | 共有スキル | resonite-* スキル | MCP |
| --- | --- | --- | --- | --- | --- |
| Claude Code | ルート CLAUDE.md（祖先探索） | プロジェクト CLAUDE.md の import | ルート `.claude/skills` | プロジェクト `.claude/skills` | `.mcp.json`（git ルート） |
| Codex | ルート AGENTS.md | 直接 | ルート `.agents/skills` | プロジェクト `.agents/skills` | `.codex/config.toml` |
| pi | ルート AGENTS.md | 直接 | ルート `.agents/skills` | プロジェクト `.agents/skills` | 拡張の設定（現状維持） |
| Devin | ルート AGENTS.md | 直接 | ルート `.agents/skills` | プロジェクト `.agents/skills` | `.mcp.json` 互換読込 |
| Cursor | 祖先の AGENTS.md | 直接 | 不可視（workspace 配下のみ） | プロジェクト `.agents/skills` | `.cursor/mcp.json` |
| dsh | ルート AGENTS.md | 直接 | ルート `.agents/skills` | 不可視（git ルートのみ） | 未設定（現状維持） |

Cursor と dsh の「不可視」は README に制約として明記する。Codex が初回に求める trust の承認手順も README に書く。

### 5.2 ルート AGENTS.md

現在の `CLAUDE.md` の内容を土台に、ツール非依存の表現へ書き直す。節は次のとおり。

1. リポジトリ概要
2. 基本方針（曖昧なら質問、設計を決めてから実装、Python は uv 必須。例外として Dev Container のブートストラップと zsh ヘルパーは python3 を使ってよい）
3. resoloop 注意（1 オブジェクト 1 メッシュ、長大タスクの分割、区切りでの handoff）
4. 日本語表現
5. ファイルとドラフト（`docs_draft/` はローカル下書きで ignore、残す文書は `docs/` に置く。ユーザから依頼された文書は `docs_draft/` に Markdown で作成する）
6. プロジェクト運用（プロジェクトを cwd にして起動する、`scripts/new-world.sh` で作る、各プロジェクトのテストは `uv run pytest`、`resoloop skills sync --check` の確認）
7. リポジトリ境界（5.4 の表）
8. ResoLoop の版管理（`.devcontainer/resoloop.lock` を正とし、更新は明示操作）
9. エージェント運用と SDD 実行運用（monitoring-long-tasks の参照はスキル名で行い、`.agents/monitoring-runtimes.md` はリポジトリルート基準と明記）
10. 環境
11. 最新ドキュメントの取得（Context7 は find-docs スキルを正本とし、1 件 3 回までの制限だけをここに残す）

### 5.3 CLAUDE.md と `.pi/APPEND_SYSTEM.md`

- ルート `CLAUDE.md`: 1 行目に `@AGENTS.md`。続けて「Claude Code 固有」節に AskUserQuestion の利用、`TaskOutput(block=true)` の扱い、スキルが `.claude/skills` の symlink 経由であることを書く。
- プロジェクト `CLAUDE.md`: `@AGENTS.md` のみ。
- `.pi/APPEND_SYSTEM.md`: 「CLAUDE.md を遵守」を「AGENTS.md を遵守」に改め、共通規約と重複する節（resoloop 注意）を削除、存在しない `docs_draft/subagent-launch-verification-20260906.rst` への参照を削除、subagent の同期起動規約、herdr-agent-task の呼び出し、pr-review 用の MODEL_NAME 手順、ペルソナを残す。

### 5.4 リポジトリ境界

| PR や作業対象の owner/repo | 作業ルート | 検証 |
| --- | --- | --- |
| usaturn/create-reso-world（このリポジトリの origin） | `git rev-parse --show-toplevel` | origin の URL が一致すること |
| usaturn/resoloop または orange3134/resoloop | `<toplevel>/external/resoloop` | `origin` が usaturn/resoloop、`upstream` が orange3134/resoloop であること。無ければ `scripts/resoloop-fork.sh clone` を案内して停止 |
| それ以外 | 推測せず停止 | — |

### 5.5 各エージェントの設定ファイル

- `.claude/settings.json`: 現行の env とプラグイン一覧を維持し、Dev Container の導入一覧と一致させる（5 章）。
- `.codex/config.toml`: `[mcp_servers.context7]` を定義する。Codex がルート規約を読むために必要だった `project_doc_fallback_filenames` の個人設定は不要になる旨を README に書く。
- `.cursor/mcp.json`: context7 を定義する。
- `.devin/`: `skills/` を削除する。Devin が `.claude/skills` の symlink 経由で同名スキルを二重掲示する場合は `.devin/config.json` で Claude 互換読込を無効化する（設定キーの存在は実装時に `devin --help` と公式文書で確認し、無ければ二重掲示を README に明記する）。
- `.pi-lens.json`: `$schema` を削除し、`**/tmp/**`、`**/.venv/**`、`**/artifacts/**`、`**/.resoloop/**`、`external/**`、`private/**` を ignore に追加する。

## 6. ResoLoop の版管理と fork 運用

### 6.1 ロックファイル

`.devcontainer/resoloop.lock`（KEY=VALUE、bash で `source` 可能）。

```
RESOLOOP_MODE=fork
RESOLOOP_NUGET_VERSION=0.1.0-preview.14
RESOLOOP_FORK_ORIGIN=https://github.com/usaturn/resoloop.git
RESOLOOP_FORK_UPSTREAM=https://github.com/orange3134/resoloop.git
RESOLOOP_FORK_REF=fix/blender5-uv-export
RESOLOOP_FORK_COMMIT=1ef4d18ca4010b2d5740b36af9c0c7a67785a1ca
RESOLOOP_FORK_PACKAGE_VERSION=0.1.0-preview.14.pr1.20260925
RESOLOOP_FORK_PR=https://github.com/orange3134/resoloop/pull/2
RESOLOOP_FORK_SDK=10.0.201
```

期待版は `nuget` モードなら `RESOLOOP_NUGET_VERSION`、`fork` モードなら `RESOLOOP_FORK_PACKAGE_VERSION`。

### 6.2 導入スクリプトの挙動

`.devcontainer/install_resoloop.bash`:

| 状態 | 動作 |
| --- | --- |
| 導入済み版 == 期待版 | 何もしない |
| `nuget` モード、未導入 | `dotnet tool install --global ResoLoop --version <期待版>` |
| `nuget` モード、別版 | `dotnet tool update --global ResoLoop --version <期待版> --allow-downgrade` |
| `fork` モード | `scripts/resoloop-fork.sh install` に委譲 |
| 導入後 `resoloop --version` が期待版と不一致 | エラー終了 |

`.devcontainer/verify-resonite-tooling.bash` は `resoloop --version` の出力が期待版と一致することを検査する。

### 6.3 fork スクリプト

`scripts/resoloop-fork.sh <subcommand>`:

- `clone`: `external/resoloop` に `origin`（fork）と `upstream` を持つ checkout を用意する。既にあれば remote URL を検証する。
- `sync`: `upstream` を fetch し、fork の `main` を `upstream/main` へ ff-only で追従させる（fork の main は上流のミラー専用）。
- `checkout`: `RESOLOOP_FORK_COMMIT` を detached で checkout する。
- `build`: 必要な SDK（`RESOLOOP_FORK_SDK`）が `dotnet --list-sdks` にあることを確認し、`dotnet build ResoLoop.slnx -c Release` と `dotnet pack src/RLoop.Cli/RLoop.Cli.csproj -c Release -o artifacts/fork -p:PackageVersion=<期待版> -p:Version=<期待版>` を実行する。
- `test`: `dotnet test ResoLoop.slnx`（明示実行のみ。postCreate では実行しない）。
- `install`: `clone`→`checkout`→`build` の後、`dotnet tool install|update --global ResoLoop --add-source artifacts/fork --version <期待版> --allow-downgrade` を実行し、`resoloop --version` を照合する。
- `status`: 導入済み版、ロックの期待版、checkout の HEAD、remote 構成を表示する。

SDK は `devcontainer.json` の dotnet Feature に `"additionalVersions": "10.0.201"` を追加して用意する。ロックの `RESOLOOP_FORK_SDK` と `devcontainer.json` の値が一致することをテストで検査する。

### 6.4 運用文書

`docs/resoloop-fork-workflow.md` に次を書く。

- checkout の位置（`external/resoloop`）と remote 構成、`/workspaces` 直下に置かない理由（root 所有のコンテナ内ディレクトリで再作成時に消える）
- 修正の流れ: `sync` → ブランチ作成 → 修正 → `test` → ロックのコミットを差し替えて `install` → fork へ push → 上流へ PR（運用文書では、ロックを差し替える前に fork へ push する。`install` の `checkout` は origin にあるコミットしか取り出せないため）
- fork 内 PR（usaturn/resoloop#1）はレビュー用としてマージしない。上流にマージ・リリースされたら `RESOLOOP_MODE=nuget` と `RESOLOOP_NUGET_VERSION` を更新する
- 上流への PR 候補: scaffold の `.resoloop/.gitignore` に `cache/` が無い、global.json の `rollForward` が `latestPatch` で SDK の feature band を跨げない
- `tmp/` の旧 checkout の整理手順（uv0-fix の未コミット草稿は patch として保存してから削除する）
- flux-sdk は対象外

## 7. Dev Container の整合

### 7.1 導入ツール一覧

`.devcontainer/README.md` に、ツールごとに「導入方法 / mount / initialize.bash の mkdir / zshrc の関数 / `update()` の項目」を持つ表を置き、各ファイルはこの表に従う。

| ツール | 導入 | mount | 備考 |
| --- | --- | --- | --- |
| Claude Code | installer | `~/.claude`, `~/.claude.json` | プラグインは `.claude/settings.json` と一致させる（superpowers、feature-dev を追加） |
| Codex | installer（`npm install -g @openai/codex@latest` を追加） | `~/.codex` | |
| pi | installer | `~/.pi` | 拡張と launcher は現状維持 |
| Cursor | installer | `~/.cursor`, `~/.local/share/cursor-agent` | |
| Devin | installer | `~/.local/share/devin`, `~/.config/devin` | |
| dsh | installer | `~/.dsh` | |
| gh | Feature | `~/.config/gh` | |
| grok / gcloud / glab / bun | 未導入 | `~/.grok`, `~/.config/gcloud`, `~/.config/glab-cli` | zshrc の関数は `command -v` で保護 |
| 秘密情報 | — | `~/.config/create-reso-world` | zshrc が `env` を存在時だけ `source` |

### 7.2 変更点

- `initialize.bash`: mount のソース 14 個（既存 13 ＋秘密情報）をすべて `mkdir -p` する。
- `devcontainer.json`: `name` を `create-reso-world`、`remoteEnv.PATH` に `${containerEnv:HOME}/.local/bin` と `${containerEnv:HOME}/bin` と `${containerEnv:HOME}/.dotnet/tools` を追加（実装では mounts と同じく `/home/vscode/...` を直接書いた。`${containerEnv:HOME}` が root の HOME に解決されるおそれがあるため。フェーズ 4 の D-10）、dotnet Feature に `additionalVersions`、秘密情報の mount を追加。`devcontainer-lock.json` を追跡する。
- `install_beforehand.bash`: Codex 導入ステップと Claude プラグイン（superpowers、feature-dev）を追加、uv の導入を pi 設定より前に移し `python3 scripts/setup_pi_tool_display.py` を `uv run` に置換、重複した `apt update` と `PATH` export を削除、pi 用スクリプトの移動に伴うパス修正、`STEP_TOTAL` の更新。
- `zshrc.txt`: `cod`、`genv`、`buni`、`update()` の各項目を `command -v` で保護。`BUN_INSTALL` は `$HOME` 基準。秘密情報 `env` の読み込みを追加。
- `starship.toml`: `custom.uv_python` は `$PWD` から上方向に最寄りの `.venv/pyvenv.cfg` を探す。
- `cleanup-workspace.bash` と `test-cleanup-workspace.bash`: `MAATLOG_CLEANUP_*` 互換、yarn キャッシュ掃除、`verify.sh` への言及、旧 Issue 番号を削除。
- `README.md`: maatlog へのリンクと Issue 番号を削除、パスを `/workspaces/<repo>` に一般化、Codex 用 fallback 手順を削除、ResoLoop ロック・fork 運用・ResoniteLink 到達前提（WSL2 の mirrored networking、または `resoloop discover` で URL を指定）・秘密情報の置き場・Cursor と dsh の制約・flux-sdk 対象外・テスト実行手順を追記。
- `docs/herdr-session-cwd-restore.md`: `.devcontainer` が symlink という記述を削除し、パスを一般化。
- 実行権: `.devcontainer` 配下の `*.bash`、`*.zsh`、pi ランチャー 9 本、`scripts/*.sh` を git index 上 100755 にする。
- テスト: `test-herdr-migration.bash` の gitleaks アサーションを削除（gitleaks はコンテナに入れず CI で実行）、`test-initialize-mounts.bash`（mkdir 集合と mounts 集合の一致）と `test-resoloop-lock.bash`（ロックの必須キー、SDK と `devcontainer.json` の一致、`install_resoloop.bash` の各モードをモックで検証）を追加、`test-install-resoloop.bash` をロック経由の期待値に更新、`run-tests.bash` で一括実行。

## 8. スキルの書き直し

### 8.1 配置

- 正本は `.agents/skills/<name>/SKILL.md`。`.claude/skills/<name>` は symlink、`.devin/skills` は削除。
- `.agents` 版と `.claude` 版で本文が分かれているスキル（agent-handoff、pr-review、review-fix-planning、repo-cleanup-after-merge、simplify-in-subagent）は日本語版を軸に 1 本へ統合する。英語版にしか無い手順は取り込む。Claude Code 用の `allowed-tools` は frontmatter に残す（Codex と pi が未知のキーを無視することを実装時にスキル一覧で確認する）。
- 0 バイトの `pr_review_workspace.py`（2 件）と `upsert_pr_comment.py` は symlink 化で解消する。

### 8.2 各スキルの変更

| スキル | 変更 |
| --- | --- |
| pr-review | 作業ルートの解決を 5.4 の表に置換。`verify.sh` 禁止条項は「重い一括検証を再実行しない」に一般化。レビュー保存先は対象リポジトリ直下の `reviews/` |
| review-fix-planning | `public/reviews/` 分岐を削除。Spec は `docs/superpowers/specs/`。実装後の検証は、環境変更なら `.devcontainer/run-tests.bash` と `scripts/check-layout.sh`、プロジェクト変更なら該当プロジェクトの `uv run pytest`。`allowed-tools` を合わせる |
| repo-cleanup-after-merge | submodule の段落と「ローカル main を作らない」規約を削除。`external/resoloop` の upstream 追従（`resoloop-fork.sh sync`）を追加 |
| simplify-in-subagent | ルーティング表を「このリポジトリ / resoloop fork」の 2 行に。Devin 版を統合 |
| pi-model-name | `cd public` の例を削除 |
| planning-parallel-issues | 対象を usaturn/create-reso-world の Issue に読み替え。evals の `verify.sh` を削除 |
| rst-writer | MaatLog プロファイルと fixture を削除し、このリポジトリ用プロファイル（出力先 `docs_draft/`、用語集照合なし、`uv run --with docutils --with rstcheck` による静的検査）に置換 |
| find-docs | Context7 CLI 手順の正本。AGENTS.md からは参照のみ |
| monitoring-long-tasks / monitoring-runtimes.md | `verify.sh` 固有の PID・ログ名手順を「ログパスを出力する任意の長時間コマンド」向けに一般化 |
| agent-handoff | Spec 置き場を `docs/superpowers/` に修正。handoff の置き場 `tmp/docs_draft/claude_handoffs/` は現状維持 |
| herdr-agent-task | パス参照を toplevel 基準に修正 |
| repository-ownership | スキル、テスト、Cursor ルールを削除 |

### 8.3 テスト

各スキルの contract テストを新しい文言に合わせて更新し、maatlog 前提のテストと fixture は削除する。ルート `pyproject.toml` の dev 依存（pytest、pyyaml）により `uv run pytest tests/skills .agents/skills` で一括実行できるようにする。

## 9. 検証

### 9.1 `scripts/check-layout.sh`

終了コード非 0 で失敗を報告する。CI と review-fix-planning の検証ゲートで使う。

- ルート: `.claude/skills/*` がすべて `.agents/skills` への解決可能な symlink であり、ファイルを 1 つ以上持つ `.agents/skills` 直下のディレクトリごとに対応する symlink があること（`references/` のように SKILL.md を持たない共有ディレクトリも含む。フェーズ 3 の D-7）
- 各プロジェクト（`.resoloop.json` を持つ直下ディレクトリ）: 4.2 の必須ファイルと symlink が存在し解決できること、`.claude/skills` が `.agents/skills` の実ディレクトリと 1:1 であること、`AGENTS.md` に固有節があること、`.resoloop/.gitignore` に `cache/` があること
- resoloop が使える環境では `resoloop skills sync --check` が各プロジェクトで成功すること（無い環境では skip と表示）
- 追跡ファイルに禁止パターンが無いこと（`ATS.txt`、`BTD.txt`、`TNX.txt`、`.claude/settings.local.json`、`*.blend1`、`*.orig`）
- `.devcontainer/resoloop.lock` の必須キーが揃い、`RESOLOOP_FORK_SDK` が `devcontainer.json` の `additionalVersions` に含まれること
- `initialize.bash` の mkdir 集合と `devcontainer.json` の mounts 集合が一致すること

### 9.2 CI

`.github/workflows/ci.yml`（push と pull_request）:

- `devcontainer-tests`: `bash .devcontainer/run-tests.bash`
- `layout`: `bash scripts/check-layout.sh`（resoloop 無しの環境）
- `skill-tests`: `uv run pytest tests/skills .agents/skills`
- `gitleaks`: gitleaks の公式 Action（設定は `.gitleaks.toml`。resoloop のマニフェストの識別子を誤検出から外し、`[[allowlists]]` を読める版を `GITLEAKS_VERSION` で固定する。フェーズ 4 の D-13）

ワールドのビルド（Blender）は CI で実行しない。

### 9.3 実機確認（ユーザが実施）

マージ後に Dev Containers: Rebuild Container を実行し、`bash .devcontainer/verify-resonite-tooling.bash`、`dotnet --list-sdks` に 10.0.201 があること、`resoloop --version` がロックと一致すること、`bash scripts/check-layout.sh`、各プロジェクトで `uv run pytest` を確認する。あわせて、postCreate の fork のビルドと導入、`remoteEnv.PATH`、秘密情報の mount と `env` の読み込み、Devin の simplify-in-subagent のサブエージェントのツール、GitHub Actions の 4 ジョブの成功を確かめる（手順は `docs/integration.md` の「Rebuild 後に確かめること」）。

## 10. 実装フェーズと統合

各フェーズを独立した実装計画にし、区切りで handoff できるようにする。

| フェーズ | 内容 | 完了条件 |
| --- | --- | --- |
| 0 安全確保 | `origin` 追加、`main` を feat/slum02-slum の HEAD へ ff、`main`・`feat/slum02-slum`・`feat/tokyo-nova-world`・`chore/repo-redesign` を push、tokyo-nova の未コミット 12 ファイルを別 worktree 経由で `wip/tokyo-nova-refinement` にコミットして push（作業ツリーは変更しない、layout.json の不整合はコミットメッセージに明記） | `git ls-remote` で 5 ブランチ確認 |
| 1 衛生 | `.gitignore` 改訂、settings.local.json 追跡解除、lock 追跡、TRPG 本文を `private/` へ、実行権、死んだスクリプトと `tools/` 削除、`.git/info/exclude` 整理、ルート `pyproject.toml`、`check-layout.sh` の骨組み | check-layout の禁止パターン検査が通る |
| 2 指示とスキル配置 | AGENTS.md / CLAUDE.md、`.agents/skills` の正本化と Blender 系の移動、`.claude` symlink、`.devin/skills` 撤去、`.cursor` / `.codex` / `.pi` / `.pi-lens.json`、雛形と `new-world.sh`、3 プロジェクトへの適用 | check-layout 全項目、`resoloop skills sync --check` ×3、各プロジェクト `uv run pytest` |
| 3 ResoLoop | ロック、`resoloop-fork.sh`、SDK、`install_resoloop.bash` / verify / テスト、`docs/resoloop-fork-workflow.md`、旧 spec への後継注記 | `test-install-resoloop.bash` と `test-resoloop-lock.bash`、`resoloop-fork.sh status` |
| 4 Dev Container | 7 章の全項目、`run-tests.bash`、CI | `run-tests.bash` 全通過 |
| 5 スキル書き直し | 8 章の全項目 | `uv run pytest tests/skills .agents/skills` 全通過 |
| 6 仕上げ | ルート README、`docs/integration.md`、最終検証、PR 作成 | 全検証の再実行、PR |

フェーズ 0 の `main` の ff は `git merge-base --is-ancestor main feat/slum02-slum` を確認してから `git branch -f main feat/slum02-slum` で行う。

### 10.1 統合手順（`docs/integration.md`）

1. `chore/repo-redesign` に最新の `feat/slum02-slum` を取り込み、`main` を再度 slum02 の HEAD へ ff（`git fetch . feat/slum02-slum:main`）してから PR を `main` に出す。取り込みは、push 済みのブランチを force push しないよう rebase ではなくマージで行う（フェーズ 6 の判断事項）。
2. マージ後、作業ツリー側で `git fetch origin` し、`feat/slum02-slum` を `origin/main` に rebase するか ff-merge する。
3. マージの前に、作業ツリーに残る `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` の未コミット変更を、フェーズ 2 で新設計に取り込み済みであることを確認したうえで `git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md` で破棄する。`.claude/settings.local.json` は `~/settings.local.json.bak` などへ退避してから `git checkout -- .claude/settings.local.json` で変更を戻し、マージ後に元の場所へ書き戻す（マージ後は ignore 対象になるので再追跡されない）。手順の詳細は `docs/integration.md`。
4. Dev Containers: Rebuild Container を実行し、9.3 を確認する。
5. pi と Claude Code の trust を再承認し、Codex は初回起動時にプロジェクトの trust を承認する。

## 11. 成功条件

- プロジェクトを cwd にして Claude Code、Codex、pi、Devin を起動したとき、共通規約とプロジェクトの `AGENTS.md`、共有スキルと resonite-* スキルがそれぞれ 5.1 の表どおりに読み込まれる。
- clone 直後のリポジトリで `scripts/check-layout.sh`、`.devcontainer/run-tests.bash`、`uv run pytest tests/skills .agents/skills` がすべて成功する。
- 追跡ファイルに maatlog、`public/` submodule、`scripts/ci/verify.sh` への参照が無い（evals の履歴的記録を除く）。
- `git ls-files` に TRPG 本文、`settings.local.json`、0 バイトのヘルパースクリプトが含まれない。
- Rebuild 後に `resoloop --version` がロックの期待版と一致し、Blender 5 UV 修正が保たれる。
- usaturn/create-reso-world に `main`（既定）と作業ブランチが push され、再設計の PR がマージ可能な状態になっている。

## 12. リスクと未確認事項

| 項目 | 扱い |
| --- | --- |
| Cursor がプロジェクト cwd から祖先の `.agents/skills` を読まない | 推定。README に制約として明記し、実装時に `cursor-agent` で実測できれば結果を反映する |
| Codex が trust 未承認のプロジェクトで `.agents/skills` を読むか | 初回起動時の trust 承認を README に書く |
| Devin が `.claude/skills` symlink を二重掲示する | `.devin/config.json` の設定キーを確認し、無ければ制約として明記する |
| `allowed-tools` frontmatter を Codex と pi が無視するか | フェーズ 2 でスキル一覧の表示を確認する |
| dotnet Feature の `additionalVersions` に `10.0.201` を指定した場合の実挙動 | 公式文書で `X.Y.Z` 形式を確認済み。Rebuild で実機確認する |
| `dotnet tool update --allow-downgrade` の実挙動 | モックのテストで契約を固定し、Rebuild で実機確認する |
| fork ビルドが postCreate で必要とするネットワークとビルド時間 | 既存の導入ステップも同様にネットワーク前提。失敗は fail-loud で止める |
| slum02 の別セッションとの競合 | 作業ツリーに触れず、統合時に rebase する |
